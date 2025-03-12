# [=[ Connections.py for various socket based classes ]=]

from __future__ import annotations

import asyncio
import os
import signal
import threading
import time

import socketio
import flask_socketio
import flask
import typing
import sys

__PRIVATE_IDS__ = ('connect', 'disconnect', 'error', 'join', 'leave')


class FlaskSocketioServer:
	"""
	[FlaskSocketioServer] - Operations for socket-io server-side interface (Flask)
	"""

	def __init__(self, app: flask.Flask, **kwargs) -> None:
		"""
		[FlaskSocketioServer] - Operations for socket-io server-side interface (Flask)
		- Constructor -
		:param app: The Flask application
		"""

		self.__app: flask.Flask = app
		self.__socket: flask_socketio.SocketIO = flask_socketio.SocketIO(app, **kwargs)
		self.__spaces: list[FlaskSocketioNamespace] = [FlaskSocketioNamespace(self, '/')]
		self.__state: bool = False
		self.__async_listener: threading.Thread | None = None
		self.__host: str = ...
		self.__port: int = ...

	def __enter__(self, app: flask.Flask) -> 'FlaskSocketioServer':
		return FlaskSocketioServer(app)

	def __exit__(self, e1, e2, e3, tb) -> None:
		self.close()

	def listen(self, host: str = '0.0.0.0', port: int = 443, **kwargs) -> None:
		"""
		Starts the server
		:param host: The IP address to listen to
		:param port: The port to listen to
		:param kwargs: Extra keyword arguments to pass into "flask_socketio.SocketIO.run"
		:return: (None)
		:raises IOError: If the server is already running
		"""

		if self.__state:
			raise IOError(f'Server already listening')

		for namespace in self.__spaces:
			namespace.__prepare_socket__(self.__socket)

		self.__state = True

		try:
			self.__host = host
			self.__port = port
			self.__socket.run(self.__app, host=host, port=port, **kwargs)
		except (KeyboardInterrupt, SystemExit):
			pass
		finally:
			self.close()

	def async_listen(self, host: str = '0.0.0.0', port: int = 443, **kwargs) -> threading.Thread:
		"""
		Starts the server on a separate threading.Thread
		:param host: The IP address to listen to
		:param port: The port to listen to
		:param kwargs: Extra keyword arguments to pass into "flask_socketio.SocketIO.run"
		:return: (threading.Thread) The new listening thread
		:raises IOError: If the server is already running
		"""

		if self.__state:
			raise IOError(f'Server already listening')

		self.__async_listener: threading.Thread = threading.Thread(target=self.listen, args=(host, port), kwargs=kwargs)
		self.__async_listener.start()
		return self.__async_listener

	def close(self) -> None:
		"""
		Closes the server's listening thread and exits main thread
		:return: (None)
		"""

		self.__state = False

		if self.__async_listener is None:
			sys.exit(0)
		else:
			os.kill(os.getpid(), signal.SIGINT)

	def on(self, eid: str, func: typing.Callable = None) -> 'None | typing.Callable':
		"""
		Binds a callback to a socket event id
		:param eid: (str) The event id to listen to
		:param func: (CALLABLE) The callback or None if used as a decorator
		:return: (None or CALLABLE)
		"""

		if func is None:
			def binder(sub_func: typing.Callable):
				self.__spaces[0].on(eid, sub_func)
			return binder
		else:
			self.__spaces[0].on(eid, func)

	def of(self, namespace: str) -> 'FlaskSocketioNamespace':
		"""
		Creates a new namespace
		:param namespace: (str) The namespace name
		:return: (FlaskSocketioNamespace) The new socketio namespace
		"""

		namespace: FlaskSocketioNamespace = FlaskSocketioNamespace(self, namespace)
		self.__spaces.append(namespace)
		self.__state and namespace.__prepare_socket__(self.__socket)
		return namespace

	def off(self, eid: str) -> None:
		"""
		Unbinds all listeners from an event
		:param eid: The event id to ignore
		:return: (None)
		"""

		self.__spaces[0].off(eid)

	def emit(self, eid: str, *data, wl: 'tuple[str | FlaskSocketioSocket, ...]' = (), bl: 'tuple[str | FlaskSocketioSocket, ...]' = ()) -> None:
		"""
		Emits data across all namespaces
		:param eid: The event id to emit on
		:param data: The data to send
		:param wl: Sockets to whitelist
		:param bl: Sockets to blacklist
		:return: (None)
		"""

		for namespace in self.__spaces:
			namespace.emit(eid, *data, wl=wl, bl=bl)

	@property
	def closed(self) -> bool:
		return not self.__state

	@property
	def host(self) -> str | None:
		return None if self.__host is None or self.__host is ... else str(self.__host)

	@property
	def port(self) -> int | None:
		return None if self.__port is None or self.__port is ... else int(self.__port)


class FlaskSocketioNamespace:
	"""
	[FlaskSocketioNamespace] - Flask socketio namespace object
	"""

	def __init__(self, server: FlaskSocketioServer, namespace: str) -> None:
		"""
		[FlaskSocketioNamespace] - Flask socketio namespace object
		- Constructor -
		SHOULD NOT BE CALLED DIRECTLY; USE 'FlaskSocketioServer.of'
		:param server: (FlaskSocketioServer) The socketio server
		:param namespace: (str) The namespace name
		"""

		self.__server: FlaskSocketioServer = server
		self.__ready: bool = False
		self.__namespace__: str = namespace
		self.__events__: dict[str, typing.Callable] = {}
		self.__sockets__: dict[str, FlaskSocketioSocket] = {}
		self.__socket_events__: dict[str, dict[str, FlaskSocketioSocket]] = {}

	def __exec__(self, eid: str, *args, **kwargs) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Executes all callbacks for a given event id
		:param eid: The event id to execute
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		:return: (None)
		"""

		if eid in self.__events__:
			self.__events__[eid](*args, **kwargs)

	def __prepare_socket__(self, flask_socket: 'flask_socketio.SocketIO'):
		"""
		INTERNAL METHOD; DO NOT USE
		Prepares a flask socket for use
		:param flask_socket: The flask socket to prepare
		"""

		@flask_socket.on('connect', namespace=self.__namespace__)
		def on_connect(auth):
			sid = flask.request.sid
			socket = FlaskSocketioSocket(self.__server, self, sid, auth, flask.request.remote_addr)
			self.__sockets__[sid] = socket
			self.__exec__('connect', socket)

		@flask_socket.on('disconnect', namespace=self.__namespace__)
		def on_disconnect():
			sid = flask.request.sid
			if sid in self.__sockets__:
				self.__sockets__[sid].__exec__('disconnect', self.__sockets__[sid].__is_disconnector__)
				self.__sockets__[sid].connected = False
				del self.__sockets__[sid]

		self.__socket = flask_socket
		self.__ready = True

	def __bind_socket_event__(self, socket: 'FlaskSocketioSocket', eid: str) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Binds a socket internally to an event
		:param socket: The socket to bind to
		:param eid: The event id
		:return: (None)
		"""

		if eid in self.__socket_events__:
			self.__socket_events__[eid][socket.uid] = socket
		else:
			self.__socket_events__[eid] = {socket.uid: socket}

			@self.__socket.on(eid, namespace=self.__namespace__)
			def on_event(*data):
				sid = flask.request.sid
				if sid in self.__socket_events__[eid]:
					self.__socket_events__[eid][sid].__exec__(eid, *data)

	def __unbind_socket_event__(self, socket: 'FlaskSocketioSocket', eid: str) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Unbinds a socket internally to an event
		:param socket: The socket to unbind from
		:param eid: The event id
		:return: (None)
		"""

		if eid in self.__socket_events__ and socket in self.__socket_events__[eid]:
			del self.__socket_events__[eid][socket.uid]

			if len(self.__socket_events__[eid]) == 0:
				del self.__socket_events__[eid]

	def __emit_to_socket__(self, socket: 'FlaskSocketioSocket', eid: str, data: tuple = ()) -> None:
		"""
		Emits data to a socket
		:param socket: The socket to emit to
		:param eid: The event id
		:param data: The data to send
		:return: (None)
		"""

		self.__socket.emit(eid, data, to=socket.uid, namespace=self.__namespace__)

	def on(self, eid: str, func: typing.Callable = None) -> 'None | typing.Callable':
		"""
		Binds a callback to a socket event id
		:param eid: (str) The event id to listen to
		:param func: (CALLABLE) The callback or None if used as a decorator
		:return: (None or CALLABLE)
		"""

		if func is None:
			def binder(sub_func: typing.Callable):
				if callable(sub_func):
					self.__events__[eid] = sub_func
				else:
					raise TypeError(f"Cannot bind non-callable object '{sub_func}'")
			return binder
		elif callable(func):
			self.__events__[eid] = func
		else:
			raise TypeError(f"Cannot bind non-callable object '{func}'")

	def off(self, eid: str) -> None:
		"""
		Unbinds all listeners from an event
		:param eid: The event id to ignore
		:return: (None)
		"""

		if eid in self.__events__:
			del self.__events__[eid]

	def emit(self, eid: str, *data, wl: 'tuple[str | FlaskSocketioSocket, ...]' = (), bl: 'tuple[str | FlaskSocketioSocket, ...]' = ()) -> None:
		"""
		Emits data across all sockets in this namespace
		If "wl" is not empty, all sockets in "wl" are considered
		If "wl" is empty and "bl" is not empty, all sockets not in "bl" are considered
		:param eid: The event id to emit on
		:param data: The data to send
		:param wl: Sockets to whitelist
		:param bl: Sockets to blacklist
		:return: (None)
		"""

		wl: tuple[str, ...] = tuple(s.uid if type(s) is FlaskSocketioSocket else s for s in wl)
		bl: tuple[str, ...] = tuple(s.uid if type(s) is FlaskSocketioSocket else s for s in bl)

		if len(wl) > 0:
			sockets: tuple[str, ...] = tuple(s for s in self.__sockets__ if s in wl)
		elif len(bl) > 0:
			sockets: tuple[str, ...] = tuple(s for s in self.__sockets__ if s not in bl)
		else:
			sockets: tuple[str, ...] = tuple(self.__sockets__.keys())

		for sid in sockets:
			self.__socket.emit(eid, data, to=sid, namespace=self.__namespace__)

	@property
	def ready(self) -> bool:
		"""
		Gets if this namespace is ready for IO
		:return: Readiness
		"""

		return self.__ready


class FlaskSocketioSocket:
	"""
	[FlaskSocketioSocket] - Flask socketio socket object
	"""

	def __init__(self, server: FlaskSocketioServer, namespace: FlaskSocketioNamespace, uid: str, auth, ip: str):
		"""
		[FlaskSocketioSocket] - Flask socketio socket object
		- Constructor -
		SHOULD NOT BE CALLED DIRECTLY
		:param server: (FlaskSocketioServer) The socketio server
		:param namespace: (FlaskSocketioNamespace) The socketio namespace
		:param uid: (str) This socket's UID
		:param auth: This socket's authentication info
		:param ip: (str) This socket's IP address
		"""

		self.__server: FlaskSocketioServer = server
		self.__space: FlaskSocketioNamespace = namespace
		self.__is_disconnector__: bool = False
		self.__uid: str = uid
		self.__events__: dict[str, typing.Callable] = {}
		self.auth = auth
		self.connected: bool = True
		self.ip_address: str = str(ip)
		
	def __exec__(self, eid: str, *args, **kwargs) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Executes all callbacks for a given event id
		:param eid: The event id to execute
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		:return: (None)
		"""

		if eid in self.__events__:
			self.__events__[eid](*args, **kwargs)

	def __bind_event__(self, eid: str, func: typing.Callable) -> None:
		"""
		Binds a callback to an event
		:param eid: (str) The event id
		:param func: (CALLABLE) The callback
		:return:
		"""

		if callable(func):
			self.__events__[eid] = func

			if eid not in __PRIVATE_IDS__:
				self.__space.__bind_socket_event__(self, eid)
		else:
			raise TypeError(f"Cannot bind non-callable object '{func}'")

	def on(self, eid: str, func: typing.Callable = None) -> 'None | typing.Callable':
		"""
		Binds a callback to a socket event id
		:param eid: (str) The event id to listen to
		:param func: (CALLABLE) The callback or None if used as a decorator
		:return: (None or CALLABLE)
		"""

		if func is None:
			def binder(sub_func):
				self.__bind_event__(eid, sub_func)
			return binder
		else:
			self.__bind_event__(eid, func)

	def off(self, eid: str) -> None:
		"""
		Unbinds all listeners from an event
		:param eid: The event id to ignore
		:return: (None)
		"""

		if eid in self.__events__:
			del self.__events__[eid]

			if eid not in __PRIVATE_IDS__:
				self.__space.__unbind_socket_event__(self, eid)

	def emit(self, eid: str, *data) -> None:
		"""
		Emits data to client from this socket
		:param eid: The event id to emit on
		:param data: The data to send
		:return: (None)
		"""

		self.__space.__emit_to_socket__(self, eid, data)
	
	def disconnect(self) -> None:
		"""
		Disconnects this socket
		:return: (None)
		"""

		self.__is_disconnector__ = True
		self.connected = False
		flask_socketio.disconnect(self.__uid, self.__space.__namespace__)

	@property
	def uid(self) -> str:
		"""
		Gets the UID of this socket
		:return: UIDness
		"""

		return self.__uid


class SocketioClient:
	"""
	[SocketioClient] - Operations for client-side socketio
	"""

	def __init__(self, host: str, namespace: str = '/') -> None:
		"""
		[SocketioClient] - Operations for client-side socketio
		- Constructor -
		:param host: The server IP address/URL
		:param namespace: The namespace to connect to
		"""

		self.__host: str = host if host[-1] != '/' else host[0:-1]
		self.__space: str = namespace if namespace[0] == '/' else '/' + namespace
		self.__is_disconnector__: bool = False
		self.__events: dict[str, list[typing.Callable]] = {}
		self.__soc: socketio.Client = socketio.Client()

	def __enter__(self) -> 'SocketioClient':
		return self

	def __exit__(self, e1, e2, e3, tb) -> None:
		self.__soc.disconnect()

	def __mainloop__(self) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Mainloop for event listening
		:return:
		"""

		@self.__soc.on('connect', namespace=self.__space)
		def connection():
			while not self.__soc.connected:
				pass
			self.__exec__('connect')

		@self.__soc.on('disconnect', namespace=self.__space)
		def disconnection():
			self.__exec__('disconnect', self.__is_disconnector__)

		@self.__soc.on('error', namespace=self.__space)
		def error():
			self.__exec__('error')

		self.__soc.connect(self.__host, namespaces=self.__space)

	def __exec__(self, eid: str, *args, **kwargs) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Executes all callbacks for a given event id
		:param eid: The event id to execute
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		:return: (None)
		"""

		if eid in self.__events:
			for callback in self.__events[eid]:
				if asyncio.iscoroutinefunction(self.__events[eid]):
					asyncio.run(callback(*args, **kwargs))
				else:
					callback(*args, **kwargs)

	def on(self, eid: str, func: typing.Callable = None) -> 'None | typing.Callable':
		"""
		Binds a callback to a socket event id
		:param eid: (str) The event id to listen to
		:param func: (CALLABLE) The callback or None if used as a decorator
		:return: (None or CALLABLE)
		"""

		if func is None:
			def bind_event(callback: typing.Callable):
				if callable(callback):
					if eid not in self.__events:
						self.__events[eid] = [callback]

						@self.__soc.on(eid, namespace=self.__space)
						def handler(*args, **kwargs):
							self.__exec__(eid, *args, **kwargs)
					else:
						self.__events[eid].append(callback)
				else:
					raise TypeError('Cannot bind non-callable \'{}\''.format(callback))
			return bind_event
		elif callable(func):
			if eid not in self.__events:
				self.__events[eid] = [func]

				@self.__soc.on(eid, namespace=self.__space)
				def handler(*args, **kwargs):
					self.__exec__(eid, *args, **kwargs)
			else:
				self.__events[eid].append(func)

	def off(self, eid: str) -> None:
		"""
		Unbinds all listeners from an event
		:param eid: The event id to ignore
		:return: (None)
		"""

		if eid in self.__events:
			del self.__soc.handlers[self.__space][eid]
			del self.__events[eid]
		else:
			raise KeyError(f'No bound event found with trigger \'{eid}\'')

	def emit(self, eid: str, *data) -> None:
		"""
		Emits data to server from this socket
		:param eid: The event id to emit on
		:param data: The data to send
		:return: (None)
		"""

		self.__soc.emit(eid, data, namespace=self.__space)

	def connect(self) -> None:
		"""
		Connects this socket to server
		Internal event listener is started and thread blocked until socket closed
		:return: (None)
		"""

		self.__is_disconnector__ = False
		self.__mainloop__()
		self.__soc.wait()

	def async_connect(self) -> None:
		"""
		Connects this socket to server
		Internal event listener is started
		:return: (None)
		"""

		self.__is_disconnector__ = False
		self.__mainloop__()

	@property
	def connected(self) -> bool:
		"""
		Checks if this socket is connected
		:return: Connectedness
		"""

		return self.__soc.connected

	@property
	def namespace(self) -> str:
		"""
		Gets the name of the connected namespace
		:return: Namespace name
		"""

		return self.__space

	def disconnect(self) -> None:
		"""
		Disconnects this socket from server
		:return: (None)
		"""

		self.__is_disconnector__ = True
		self.__soc.disconnect()


if sys.platform == 'win32':
	import base64
	import builtins
	import ctypes.wintypes
	import datetime
	import pickle
	import pywintypes

	import win32pipe
	import win32file
	import win32security
	import win32api

	import CustomMethodsVI.Exceptions as Exceptions

	class WinNamedPipe:
		"""
		[WinNamedPipe] - A windows-only duplex named pipe implementation
		"""

		__PIPE_SECURITY__: win32security.SECURITY_ATTRIBUTES = win32security.SECURITY_ATTRIBUTES()
		__PIPE_SECURITY__.SECURITY_DESCRIPTOR = None
		__PIPE_SECURITY__.bInheritHandle = True
		__PIPE_BUFFER_SIZE__: int = 1024

		def __init__(self):
			"""
			[WinNamedPipe] - A windows-only duplex named pipe implementation
			- Constructor -
			"""

			self.__pipename__: str = f'\\\\.\\pipe\\{hex(id(self))}::{datetime.datetime.now(datetime.timezone.utc).timestamp()}'
			self.__conn__: int = win32pipe.CreateNamedPipe(self.__pipename__, win32pipe.PIPE_ACCESS_DUPLEX | win32pipe.FILE_FLAG_FIRST_PIPE_INSTANCE, win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE, win32pipe.PIPE_UNLIMITED_INSTANCES, WinNamedPipe.__PIPE_BUFFER_SIZE__, WinNamedPipe.__PIPE_BUFFER_SIZE__, 0, WinNamedPipe.__PIPE_SECURITY__).Detach()
			self.__isserver__: bool = True
			self.__open__: bool = self.__conn__ != win32file.INVALID_HANDLE_VALUE

			if self.__conn__ == win32file.INVALID_HANDLE_VALUE:
				raise IOError(f'Failed to create named pipe - ERROR_{win32api.GetLastError()}')

		def __del__(self) -> None:
			try:
				if not self.closed:
					self.close()
			except (IOError, AttributeError):
				pass

		def __setstate__(self, state: dict[str, typing.Any]) -> None:
			"""
			Deserializing function for setting from pickled state
			:param state: (dict[str, ANY]) The pickled state
			:return: (None)
			"""

			isserver: bool = state['__isserver__']
			self.__dict__.update(state)
			self.__conn__: int = state['__conn__'] if not isserver else win32file.CreateFile(self.__pipename__, win32file.GENERIC_READ | win32file.GENERIC_WRITE, win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE, WinNamedPipe.__PIPE_SECURITY__, win32file.OPEN_EXISTING, win32file.FILE_ATTRIBUTE_NORMAL, None).Detach()
			self.__isserver__: bool = False
			self.__open__: bool = self.__conn__ != win32file.INVALID_HANDLE_VALUE

			if self.__conn__ == win32file.INVALID_HANDLE_VALUE:
				raise IOError(f'Failed to connect to named pipe - ERROR_{win32api.GetLastError()}')

		def __getstate__(self) -> dict[str, typing.Any]:
			"""
			Serializing function for retrieving pickle safe state
			:return: (dict[str, ANY]) The pickle-able state
			"""

			attributes: dict[str, typing.Any] = self.__dict__.copy()
			del attributes['__open__']
			return attributes

		def __repr__(self) -> str:
			return str(self)

		def __str__(self) -> str:
			return f'<WinNamedPipe[{self.__pipename__}-{"SERVER" if self.__isserver__ else "CLIENT"}] @ {hex(id(self))}>'

		def close(self) -> None:
			"""
			Closes the pipe
			All in-writing information is lost
			:return: (None)
			:raises IOError: If the pipe is already closed
			"""

			if self.closed:
				raise IOError('Pipe already closed')
			elif self.__isserver__:
				win32pipe.DisconnectNamedPipe(self.__conn__)
				win32file.CloseHandle(self.__conn__)
				self.__open__ = False
			else:
				win32file.CloseHandle(self.__conn__)
				self.__open__ = False

		def flush(self) -> None:
			"""
			Flushes all data into pipe
			Blocks until data is written and read
			:return: (None)
			:raises IOError: If the pipe is closed
			"""

			if self.closed:
				raise IOError('Pipe is closed')

			win32file.FlushFileBuffers(self.__conn__)

		def poll(self) -> int:
			"""
			Polls the number of bytes waiting in the buffer
			:return: (int) The number of in-waiting bytes
			:raises IOError: If the pipe is closed
			"""

			if self.closed:
				raise IOError('Pipe is closed')

			try:
				return win32pipe.PeekNamedPipe(self.__conn__, WinNamedPipe.__PIPE_BUFFER_SIZE__)[1]
			except pywintypes.error as e:
				return -1 if e.winerror == 6 else 0

		def dup(self) -> WinNamedPipe:
			"""
			Duplicates the pipe, returning a client-side pipe connection
			:return: (WinNamedPipe) The new pipe connection
			:raises IOError: If the pipe failed to connect
			"""

			pipe: WinNamedPipe = type(self).__new__(type(self))
			pipe.__setstate__(self.__getstate__())
			return pipe

		def send(self, data: typing.Any) -> WinNamedPipe:
			"""
			Sends an object over the pipe
			Objects are serialized before transmission
			To write raw binary data, see WinNamedPipe::write
			:param data: (ANY) The object to write
			:return: (WinNamedPipe) This instance
			:raises IOError: If the pipe is closed or the write operation failed
			"""

			if self.closed:
				raise IOError('Pipe is closed')

			serialized: bytes = base64.b64encode(pickle.dumps(data))
			payload: bytes = len(serialized).to_bytes(8, 'little', signed=False) + serialized

			if win32file.WriteFile(self.__conn__, payload) == 0:
				raise IOError(f'Failed to write data - ERROR_{win32api.GetLastError()}')

			return self

		def write(self, data: bytes | bytearray) -> WinNamedPipe:
			"""
			Writes binary data to the pipe
			To send standard objects, see WinNamedPipe::send
			:param data: (bytes | bytearray) The bytes to write
			:return: (WinNamedPipe) This instance
			:raises IOError: If the pipe is closed or the write operation failed
			"""

			if self.closed:
				raise IOError('Pipe is closed')
			elif not isinstance(data, (bytes, bytearray)):
				raise Exceptions.InvalidArgumentException(WinNamedPipe.write, 'data', type(data), (bytes, bytearray))

			data: bytes = bytes(data)

			if len(data) == 0:
				return self

			if win32file.WriteFile(self.__conn__, data) == 0:
				raise IOError(f'Failed to write data - ERROR_{win32api.GetLastError()}')

			return self

		def recv(self) -> typing.Any:
			"""
			Receives an object from the pipe
			Objects are deserialized before returning
			To read raw binary data, see WinNamedPipe::read
			:return: (ANY) The deserialized object
			:raises IOError: If the pipe is closed or the read operation failed
			"""

			if self.closed:
				raise IOError('Pipe is closed')

			while (poll := self.poll()) < 8:
				if poll <= -1:
					raise BrokenPipeError('The pipe is invalid')

				time.sleep(1e-6)

			err: int
			payload_length_b: bytes
			err, payload_length_b = win32file.ReadFile(self.__conn__, 8)

			if err != 0:
				raise IOError('Failed to read data from pipe')

			payload_length: int = int.from_bytes(payload_length_b, 'little', signed=False)

			while (poll := self.poll()) < payload_length:
				if poll <= -1:
					raise BrokenPipeError('The pipe is invalid')

				time.sleep(1e-6)

			payload: bytes
			err, payload = win32file.ReadFile(self.__conn__, payload_length)

			if err != 0:
				raise IOError('Failed to read data from pipe')

			return pickle.loads(base64.b64decode(payload))

		def read(self, n: int = -1) -> bytes:
			"""
			Reads binary data from the pipe
			To read standard objects, see WinNamedPipe::recv
			:param n: (int) The number of bytes to read or all data if less than 0
			:return: (bytes) The read bytes
			:raises IOError: If the pipe is closed or the read operation failed
			"""

			if self.closed:
				raise IOError('Pipe is closed')

			length: int = self.poll() if n < 0 else n

			if length == 0:
				return b''

			while (poll := self.poll()) < length:
				if poll <= -1:
					raise BrokenPipeError('The pipe is invalid')

				time.sleep(1e-6)

			err: int
			payload: bytes
			err, payload = win32file.ReadFile(self.__conn__, length)

			if err != 0:
				raise IOError('Failed to read data from pipe')
			else:
				return payload

		@property
		def closed(self) -> bool:
			"""
			Returns if this pipe connection is closed
			:return: (bool) Closedness
			"""

			return not self.__open__

		@property
		def is_server(self) -> bool:
			return self.__isserver__
