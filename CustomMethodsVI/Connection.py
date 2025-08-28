# [=[ Connections.py for various socket based classes ]=]

from __future__ import annotations

import asyncio
import flask
import flask_socketio
import os
import socketio
import sys
import threading
import time
import typing

from . import Exceptions
from . import Misc

__PRIVATE_IDS__ = ('connect', 'disconnect', 'error', 'join', 'leave')


class FlaskSocketioServer:
	"""
	Operations for socket-io server-side interface (Flask)
	"""

	def __init__(self, app: flask.Flask, **kwargs) -> None:
		"""
		Operations for socket-io server-side interface (Flask)
		- Constructor -
		:param app: The Flask application
		:raises InvalidArgumentException: If 'app' is not a flask.Flask instance
		"""

		Misc.raise_ifn(isinstance(app, flask.Flask), Exceptions.InvalidArgumentException(FlaskSocketioServer.__init__, 'app', type(app), (flask.Flask,)))

		self.__app__: flask.Flask = app
		self.__socket__: flask_socketio.SocketIO = flask_socketio.SocketIO(app, **kwargs)
		self.__spaces__: list[FlaskSocketioNamespace] = [FlaskSocketioNamespace(self, '/')]
		self.__state__: bool = False
		self.__async_listener__: threading.Thread | None = None
		self.__host__: str = ...
		self.__port__: int = ...

	def __enter__(self, app: flask.Flask) -> FlaskSocketioServer:
		return FlaskSocketioServer(app)

	def __exit__(self, e1, e2, e3, tb) -> None:
		self.close()

	def listen(self, host: str = '0.0.0.0', port: int = 443, **kwargs) -> None:
		"""
		Starts the server
		:param host: The IP address to listen to
		:param port: The port to listen to
		:param kwargs: Extra keyword arguments to pass into "flask_socketio.SocketIO.run"
		:raises IOError: If the server is already running
		:raises InvalidArgumentException: If 'host' is not a string
		:raises InvalidArgumentException: If 'port' is not a positive integer
		"""

		Misc.raise_ifn(isinstance(host, str), Exceptions.InvalidArgumentException(FlaskSocketioServer.listen, 'host', type(host), (str,)))
		Misc.raise_ifn(isinstance(port, int) and int(port) >= 0, Exceptions.InvalidArgumentException(FlaskSocketioServer.listen, 'port', type(port), (int,)))

		if self.__state__:
			raise IOError(f'Server already listening')

		for namespace in self.__spaces__:
			namespace.__prepare_socket__(self.__socket__)

		self.__state__ = True

		try:
			self.__host__ = str(host)
			self.__port__ = int(port)
			self.__socket__.run(self.__app__, host=host, port=port, **kwargs)
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
		:return: The new listening thread
		:raises IOError: If the server is already running
		:raises InvalidArgumentException: If 'host' is not a string
		:raises InvalidArgumentException: If 'port' is not a positive integer
		"""

		Misc.raise_ifn(isinstance(host, str), Exceptions.InvalidArgumentException(FlaskSocketioServer.listen, 'host', type(host), (str,)))
		Misc.raise_ifn(isinstance(port, int) and int(port) >= 0, Exceptions.InvalidArgumentException(FlaskSocketioServer.listen, 'port', type(port), (int,)))

		if self.__state__:
			raise IOError(f'Server already listening')

		self.__async_listener__: threading.Thread = threading.Thread(target=self.listen, args=(host, port), kwargs=kwargs)
		self.__async_listener__.start()
		return self.__async_listener__

	def close(self) -> None:
		"""
		Closes the server's listening thread and exits main thread
		"""

		if not self.__state__:
			return

		self.__state__ = False
		self.__socket__.stop()
		self.__async_listener__ = None

	def on(self, eid: str, func: typing.Callable = None) -> None | typing.Callable:
		"""
		Binds a callback to a socket event id
		:param eid: The event id to listen to
		:param func: The callback or None if used as a decorator
		:return: The binder if used as a decorator
		:raises InvalidArgumentException: If eid is not a string
		:raises InvalidArgumentException: If callback is not callable
		"""

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(FlaskSocketioServer.on, 'eid', type(eid), (str,)))
		eid = str(eid)

		if func is None:
			def binder(sub_func: typing.Callable):
				Misc.raise_ifn(callable(sub_func), Exceptions.InvalidArgumentException(FlaskSocketioServer.on, 'func', type(sub_func)))
				self.__spaces__[0].on(eid, sub_func)
			return binder
		else:
			Misc.raise_ifn(callable(func), Exceptions.InvalidArgumentException(FlaskSocketioServer.on, 'func', type(func)))
			self.__spaces__[0].on(eid, func)

	def of(self, namespace: str) -> FlaskSocketioNamespace:
		"""
		Creates a new namespace
		:param namespace: The namespace name
		:return: The new socketio namespace
		"""

		namespace: FlaskSocketioNamespace = FlaskSocketioNamespace(self, namespace)
		self.__spaces__.append(namespace)
		self.__state__ and namespace.__prepare_socket__(self.__socket__)
		return namespace

	def off(self, eid: str) -> None:
		"""
		Unbinds all listeners from an event
		:param eid: The event id to ignore
		"""

		self.__spaces__[0].off(eid)

	def emit(self, eid: str, *data, wl: tuple[str | FlaskSocketioSocket, ...] = (), bl: tuple[str | FlaskSocketioSocket, ...] = ()) -> None:
		"""
		Emits data across all namespaces
		:param eid: The event id to emit on
		:param data: The data to send
		:param wl: Sockets to whitelist
		:param bl: Sockets to blacklist
		"""

		for namespace in self.__spaces__:
			namespace.emit(eid, *data, wl=wl, bl=bl)

	@property
	def closed(self) -> bool:
		"""
		:return: Whether the server is closed
		"""

		return not self.__state__

	@property
	def host(self) -> typing.Optional[str]:
		"""
		:return: The host or None if not started
		"""

		return None if self.__host__ is None or self.__host__ is ... else str(self.__host__)

	@property
	def port(self) -> typing.Optional[int]:
		"""
		:return: The port or None if not started
		"""
		return None if self.__port__ is None or self.__port__ is ... else int(self.__port__)

	@property
	def socketio(self) -> flask_socketio.SocketIO:
		"""
		:return: The underlying flask_socket.SocketIO instance
		"""

		return self.__socket__

	@property
	def app(self) -> flask.Flask:
		"""
		:return: The underlying flask.Flask instance
		"""

		return self.__app__


class FlaskSocketioNamespace:
	"""
	Flask socketio namespace object
	"""

	def __init__(self, server: FlaskSocketioServer, namespace: str) -> None:
		"""
		Flask socketio namespace object
		- Constructor -
		SHOULD NOT BE CALLED DIRECTLY; USE 'FlaskSocketioServer.of'
		:param server: The socketio server
		:param namespace: The namespace name
		:raises InvalidArgumentException: If 'server' is not a FlaskSocketioServer instance
		:raises InvalidArgumentException: If 'namespace' is not a string
		"""

		Misc.raise_ifn(isinstance(server, FlaskSocketioServer), Exceptions.InvalidArgumentException(FlaskSocketioNamespace.__init__, 'server', type(server), (FlaskSocketioServer,)))
		Misc.raise_ifn(isinstance(namespace, str), Exceptions.InvalidArgumentException(FlaskSocketioNamespace.__init__, 'namespace', type(namespace), (str,)))

		self.__server__: FlaskSocketioServer = server
		self.__ready__: bool = False
		self.__namespace__: str = str(namespace)
		self.__events__: dict[str, typing.Callable] = {}
		self.__sockets__: dict[str, FlaskSocketioSocket] = {}
		self.__socket_events__: dict[str, dict[str, FlaskSocketioSocket]] = {}

	def __exec__(self, eid: str, *args, **kwargs) -> None:
		"""
		INTERNAL METHOD
		Executes all callbacks for a given event id
		:param eid: The event id to execute
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		"""

		if eid in self.__events__:
			self.__events__[eid](*args, **kwargs)

	def __prepare_socket__(self, flask_socket: flask_socketio.SocketIO) -> None:
		"""
		INTERNAL METHOD
		Prepares a flask socket for use
		:param flask_socket: The flask socket to prepare
		"""

		@flask_socket.on('connect', namespace=self.__namespace__)
		def on_connect(auth):
			sid = flask.request.sid
			socket = FlaskSocketioSocket(self.__server__, self, sid, auth, flask.request)
			self.__sockets__[sid] = socket
			self.__exec__('connect', socket)

		@flask_socket.on('disconnect', namespace=self.__namespace__)
		def on_disconnect():
			sid = flask.request.sid
			if sid in self.__sockets__:
				self.__sockets__[sid].__exec__('disconnect', self.__sockets__[sid].__is_disconnector__)
				self.__sockets__[sid].__connected__ = False
				del self.__sockets__[sid]

		self.__socket = flask_socket
		self.__ready__ = True

	def __bind_socket_event__(self, socket: FlaskSocketioSocket, eid: str) -> None:
		"""
		INTERNAL METHOD
		Binds a socket internally to an event
		:param socket: The socket to bind to
		:param eid: The event id
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

	def __unbind_socket_event__(self, socket: FlaskSocketioSocket, eid: str) -> None:
		"""
		INTERNAL METHOD
		Unbinds a socket internally to an event
		:param socket: The socket to unbind from
		:param eid: The event id
		"""

		if eid in self.__socket_events__ and socket in self.__socket_events__[eid]:
			del self.__socket_events__[eid][socket.uid]

			if len(self.__socket_events__[eid]) == 0:
				del self.__socket_events__[eid]

	def __emit_to_socket__(self, socket: FlaskSocketioSocket, eid: str, data: tuple = ()) -> None:
		"""
		INTERNAL METHOD
		Emits data to a socket
		:param socket: The socket to emit to
		:param eid: The event id
		:param data: The data to send
		"""

		self.__socket.emit(eid, data, to=socket.uid, namespace=self.__namespace__)

	def on(self, eid: str, func: typing.Callable = None) -> typing.Optional[typing.Callable]:
		"""
		Binds a callback to a socket event id
		:param eid: The event id to listen to
		:param func: The callback or None if used as a decorator
		:return: The binder if used as a decorator
		:raises InvalidArgumentException: If eid is not a string
		:raises InvalidArgumentException: If callback is not callable
		"""

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(FlaskSocketioNamespace.on, 'eid', type(eid), (str,)))
		eid = str(eid)

		if func is None:
			def binder(sub_func: typing.Callable):
				Misc.raise_ifn(callable(sub_func), Exceptions.InvalidArgumentException(FlaskSocketioNamespace.on, 'func', type(sub_func)))
				self.__events__[eid] = sub_func
			return binder
		else:
			Misc.raise_ifn(callable(func), Exceptions.InvalidArgumentException(FlaskSocketioNamespace.on, 'func', type(func)))
			self.__events__[eid] = func

	def off(self, eid: str) -> None:
		"""
		Unbinds all listeners from an event
		:param eid: The event id to ignore
		"""

		if eid in self.__events__:
			del self.__events__[eid]

	def emit(self, eid: str, *data, wl: tuple[str | FlaskSocketioSocket, ...] = (), bl: tuple[str | FlaskSocketioSocket, ...] = ()) -> None:
		"""
		Emits data across all sockets in this namespace
		If "wl" is not empty, all sockets in "wl" are considered
		If "wl" is empty and "bl" is not empty, all sockets not in "bl" are considered
		:param eid: The event id to emit on
		:param data: The data to send
		:param wl: Sockets to whitelist
		:param bl: Sockets to blacklist
		:raises InvalidArgumentException: If 'eid' is not a string
		"""

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(FlaskSocketioNamespace.emit, 'eid', type(eid), (str,)))
		wl: tuple[str, ...] = tuple(s.uid if isinstance(s, FlaskSocketioSocket) else str(s) for s in wl)
		bl: tuple[str, ...] = tuple(s.uid if isinstance(s, FlaskSocketioSocket) else str(s) for s in bl)

		if len(wl) > 0:
			sockets: tuple[str, ...] = tuple(s for s in self.__sockets__ if s in wl)
		elif len(bl) > 0:
			sockets: tuple[str, ...] = tuple(s for s in self.__sockets__ if s not in bl)
		else:
			sockets: tuple[str, ...] = tuple(self.__sockets__.keys())

		for sid in sockets:
			self.__socket.emit(eid, data, to=sid, namespace=self.__namespace__)

	def get_socket(self, uid: str) -> FlaskSocketioSocket | None:
		"""
		Gets a socket by ID
		:param uid: The socket ID
		:return: The socket or None if not found
		"""

		return self.__sockets__[uid] if uid in self.__sockets__ else None

	@property
	def ready(self) -> bool:
		"""
		:return: Whether this namespace is ready for IO
		"""

		return self.__ready__

	@property
	def sockets(self) -> tuple[FlaskSocketioSocket, ...]:
		"""
		:return: All sockets connected to this namespace
		"""

		return tuple(self.__sockets__.values())

	@property
	def server(self) -> FlaskSocketioServer:
		"""
		:return: The FlaskSocketioServer instance this namespace is bound to
		"""

		return self.__server__


class FlaskSocketioSocket:
	"""
	Flask socketio socket object
	"""

	def __init__(self, server: FlaskSocketioServer, namespace: FlaskSocketioNamespace, uid: str, auth, request: flask.Request):
		"""
		Flask socketio socket object
		- Constructor -
		SHOULD NOT BE CALLED DIRECTLY
		:param server: The socketio server
		:param namespace: The socketio namespace
		:param uid: This socket's UID
		:param auth: This socket's authentication info
		:param request: This socket's flask request
		:raises InvalidArgumentException: If 'server' is not a FlaskSocketioServer instance
		:raises InvalidArgumentException: If 'namespace' is not a FlaskSocketioNamespace instance
		:raises InvalidArgumentException: If 'uid' is not a string
		:raises InvalidArgumentException: If 'request' is not a flask.Request instance
		"""

		Misc.raise_ifn(isinstance(server, FlaskSocketioServer), Exceptions.InvalidArgumentException(FlaskSocketioSocket.__init__, 'server', type(server), (FlaskSocketioServer,)))
		Misc.raise_ifn(isinstance(namespace, FlaskSocketioNamespace), Exceptions.InvalidArgumentException(FlaskSocketioSocket.__init__, 'namespace', type(namespace), (FlaskSocketioNamespace,)))
		Misc.raise_ifn(isinstance(uid, str), Exceptions.InvalidArgumentException(FlaskSocketioSocket.__init__, 'uid', type(uid), (str,)))
		Misc.raise_ifn(isinstance(request, flask.Request), Exceptions.InvalidArgumentException(FlaskSocketioSocket.__init__, 'request', type(request), (flask.Request,)))

		self.__server__: FlaskSocketioServer = server
		self.__space__: FlaskSocketioNamespace = namespace
		self.__is_disconnector__: bool = False
		self.__uid__: str = uid
		self.__events__: dict[str, typing.Callable] = {}
		self.__auth__ = auth
		self.__connected__: bool = True
		self.__request__: flask.Request = request
		
	def __exec__(self, eid: str, *args, **kwargs) -> None:
		"""
		INTERNAL METHOD
		Executes all callbacks for a given event id
		:param eid: The event id to execute
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		"""

		if eid in self.__events__:
			self.__events__[eid](*args, **kwargs)

	def __bind_event__(self, eid: str, func: typing.Callable) -> None:
		"""
		INTERNAL EVENT
		Binds a callback to an event
		:param eid: The event id
		:param func: The callback
		:return:
		"""

		if callable(func):
			self.__events__[eid] = func

			if eid not in __PRIVATE_IDS__:
				self.__space__.__bind_socket_event__(self, eid)
		else:
			raise TypeError(f"Cannot bind non-callable object '{func}'")

	def on(self, eid: str, func: typing.Callable = None) -> None | typing.Callable:
		"""
		Binds a callback to a socket event id
		:param eid: The event id to listen to
		:param func: The callback or None if used as a decorator
		:return: The binder if used as a decorator
		:raises InvalidArgumentException: If eid is not a string
		:raises InvalidArgumentException: If callback is not callable
		"""

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(FlaskSocketioSocket.on, 'eid', type(eid), (str,)))
		eid = str(eid)

		if func is None:
			def binder(sub_func):
				Misc.raise_ifn(callable(sub_func), Exceptions.InvalidArgumentException(FlaskSocketioSocket.on, 'func', type(sub_func)))
				self.__bind_event__(eid, sub_func)
			return binder
		else:
			Misc.raise_ifn(callable(func), Exceptions.InvalidArgumentException(FlaskSocketioSocket.on, 'func', type(func)))
			self.__bind_event__(eid, func)

	def off(self, eid: str) -> None:
		"""
		Unbinds all listeners from an event
		:param eid: The event id to ignore
		:raises InvalidArgumentException: If eid is not a string
		"""

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(FlaskSocketioSocket.emit, 'eid', type(eid), (str,)))

		if (eid := str(eid)) in self.__events__:
			del self.__events__[eid]

			if eid not in __PRIVATE_IDS__:
				self.__space__.__unbind_socket_event__(self, eid)

	def emit(self, eid: str, *data) -> None:
		"""
		Emits data to client from this socket
		:param eid: The event id to emit on
		:param data: The data to send
		:raises InvalidArgumentException: If eid is not a string
		"""

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(FlaskSocketioSocket.emit, 'eid', type(eid), (str,)))
		self.__space__.__emit_to_socket__(self, str(eid), data)
	
	def disconnect(self) -> None:
		"""
		Disconnects this socket
		"""

		self.__is_disconnector__ = True
		self.__connected__ = False
		flask_socketio.disconnect(self.__uid__, self.__space__.__namespace__)

	@property
	def connected(self) -> bool:
		"""
		:return: Whether this socket is connected
		"""

		return self.__connected__

	@property
	def is_disconnector(self) -> bool:
		"""
		:return: Whether this socket disconnected itself from client
		"""

		return self.__is_disconnector__

	@property
	def uid(self) -> str:
		"""
		:return: This socket's UID
		"""

		return self.__uid__

	@property
	def auth(self):
		"""
		:return:  This socket's auth
		"""

		return self.__auth__

	@property
	def ip_address(self) -> str:
		"""
		:return: This socket's IP address
		"""

		return self.__request__.remote_addr

	@property
	def request(self) -> flask.request:
		"""
		:return: The flask request that created this socket
		"""

		return flask.request

	@property
	def server(self) -> FlaskSocketioServer:
		"""
		:return: The FlaskSocketioServer instance this socket is bound to
		"""

		return self.__server__

	@property
	def namespace(self) -> FlaskSocketioNamespace:
		"""
		:return: The FlaskSocketioNamespace instance this socket is bound to
		"""

		return self.__space__


class SocketioClient:
	"""
	Operations for client-side socketio
	"""

	def __init__(self, host: str, namespace: str = '/') -> None:
		"""
		Operations for client-side socketio
		- Constructor -
		:param host: The server IP address/URL
		:param namespace: The namespace to connect to
		:raises InvalidArgumentException: If 'host' is not a string
		:raises InvalidArgumentException: If 'namespace' is not a string
		"""

		Misc.raise_ifn(isinstance(host, str), Exceptions.InvalidArgumentException(SocketioClient.__init__, 'host', type(host), (str,)))
		Misc.raise_ifn(isinstance(namespace, str), Exceptions.InvalidArgumentException(SocketioClient.__init__, 'namespace', type(namespace), (str,)))

		self.__host__: str = str(host).rstrip('/')
		self.__space__: str = str(namespace).rstrip('/')
		self.__is_disconnector__: bool = False
		self.__events__: dict[str, list[typing.Callable]] = {}
		self.__socket__: socketio.Client = socketio.Client()

	def __enter__(self) -> SocketioClient:
		return self

	def __exit__(self, e1, e2, e3, tb) -> None:
		self.__socket__.disconnect()

	def __mainloop__(self) -> None:
		"""
		INTERNAL METHOD
		Mainloop for event listening
		"""

		@self.__socket__.on('connect', namespace=self.__space__)
		def connection():
			while not self.__socket__.connected:
				pass
			self.__exec__('connect')

		@self.__socket__.on('disconnect', namespace=self.__space__)
		def disconnection():
			self.__exec__('disconnect', self.__is_disconnector__)

		@self.__socket__.on('error', namespace=self.__space__)
		def error():
			self.__exec__('error')

		self.__socket__.connect(self.__host__, namespaces=self.__space__)

	def __exec__(self, eid: str, *args, **kwargs) -> None:
		"""
		INTERNAL METHOD
		Executes all callbacks for a given event id
		:param eid: The event id to execute
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		"""

		if eid in self.__events__:
			for callback in self.__events__[eid]:
				if asyncio.iscoroutinefunction(self.__events__[eid]):
					asyncio.run(callback(*args, **kwargs))
				else:
					callback(*args, **kwargs)

	def on(self, eid: str, func: typing.Callable = None) -> None | typing.Callable:
		"""
		Binds a callback to a socket event id
		:param eid: The event id to listen to
		:param func: The callback or None if used as a decorator
		:return: The binder if used as a decorator
		:raises InvalidArgumentException: If eid is not a string
		:raises InvalidArgumentException: If callback is not callable
		"""

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(SocketioClient.on, 'eid', type(eid), (str,)))
		eid = str(eid)

		if func is None:
			def bind_event(callback: typing.Callable):
				if callable(callback):
					if eid not in self.__events__:
						self.__events__[eid] = [callback]

						@self.__socket__.on(eid, namespace=self.__space__)
						def handler(*args, **kwargs):
							self.__exec__(eid, *args, **kwargs)
					else:
						self.__events__[eid].append(callback)
				else:
					raise Exceptions.InvalidArgumentException(SocketioClient.on, 'func', type(callback))
			return bind_event
		elif callable(func):
			if eid not in self.__events__:
				self.__events__[eid] = [func]

				@self.__socket__.on(eid, namespace=self.__space__)
				def handler(*args, **kwargs):
					self.__exec__(eid, *args, **kwargs)
			else:
				self.__events__[eid].append(func)
		else:
			raise Exceptions.InvalidArgumentException(SocketioClient.on, 'func', type(func))

	def off(self, eid: str) -> None:
		"""
		Unbinds all listeners from an event
		:param eid: The event id to ignore
		:raises InvalidArgumentException: If eid is not a string
		"""

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(SocketioClient.emit, 'eid', type(eid), (str,)))

		if (eid := str(eid)) in self.__events__:
			del self.__socket__.handlers[self.__space__][eid]
			del self.__events__[eid]

	def emit(self, eid: str, *data) -> None:
		"""
		Emits data to client from this socket
		:param eid: The event id to emit on
		:param data: The data to send
		:raises InvalidArgumentException: If eid is not a string
		"""

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(SocketioClient.emit, 'eid', type(eid), (str,)))
		self.__socket__.emit(eid, data, namespace=self.__space__)

	def connect(self) -> None:
		"""
		Connects this socket to server
		Internal event listener is started and thread blocked until socket closed
		"""

		self.__is_disconnector__ = False
		self.__mainloop__()
		self.__socket__.wait()

	def async_connect(self) -> None:
		"""
		Connects this socket to server
		Internal event listener is started
		"""

		self.__is_disconnector__ = False
		self.__mainloop__()

	def disconnect(self) -> None:
		"""
		Disconnects this socket from server
		"""

		self.__is_disconnector__ = True
		self.__socket__.disconnect()

	@property
	def connected(self) -> bool:
		"""
		:return: Whether this socket is connected
		"""

		return self.__socket__.connected

	@property
	def is_disconnector(self) -> bool:
		"""
		:return: Whether this socket disconnected itself from server
		"""

		return self.__is_disconnector__

	@property
	def namespace(self) -> str:
		"""
		:return: The name of the connected namespace
		"""

		return self.__space__

	@property
	def socket(self) -> socketio.Client:
		"""
		:return: The underlying socketio.Client instance
		"""

		return self.__socket__


if sys.platform == 'win32':
	import base64
	import datetime
	import pickle
	import pywintypes

	import win32pipe
	import win32file
	import win32security
	import win32api

	from . import Exceptions

	class WinNamedPipe:
		"""
		A windows-only duplex named pipe implementation
		"""

		__PIPE_SECURITY__: win32security.SECURITY_ATTRIBUTES = win32security.SECURITY_ATTRIBUTES()
		__PIPE_SECURITY__.SECURITY_DESCRIPTOR = None
		__PIPE_SECURITY__.bInheritHandle = True
		__PIPE_BUFFER_SIZE__: int = 1024

		def __init__(self):
			"""
			A windows-only duplex named pipe implementation
			- Constructor -
			:raises IOError: If failed to create named pipe
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
			:param state: The pickled state
			:raises IOError: If failed to connect to named pipe
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
			:return: The pickle-able state
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
			:raises IOError: If the pipe is closed
			"""

			if self.closed:
				raise IOError('Pipe is closed')

			win32file.FlushFileBuffers(self.__conn__)

		def poll(self) -> int:
			"""
			Polls the number of bytes waiting in the buffer
			:return: The number of in-waiting bytes
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
			:return: The new pipe connection
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
			:param data: The object to write
			:return: This instance
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
			:param data: The bytes to write
			:return: This instance
			:raises IOError: If the pipe is closed or the write operation failed
			:raises InvalidArgumentException: If 'data' is not a bytes object or bytearray
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
			:return: The deserialized object
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
			:param n: The number of bytes to read or all data if less than 0
			:return: The read bytes
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
			:return: Whether this pipe connection is closed
			"""

			return not self.__open__

		@property
		def is_server(self) -> bool:
			"""
			:return: Whether this is the initial server pipe
			"""

			return self.__isserver__

	NamedPipe = WinNamedPipe

else:
	from . import FileSystem
	from . import Stream

	class UnixNamedPipe:
		"""
		A unix-only duplex named pipe implementation
		"""

		def __init__(self):
			"""
			A unix-only duplex named pipe implementation
			- Constructor -
			:raises IOError: If failed to create named pipe
			"""

			self.__pipename__: str = f'/tmp/pipe_{hex(id(self))}::{datetime.datetime.now(datetime.timezone.utc).timestamp()}'

			if os.path.exists(self.__pipename__):
				raise IOError(f'Failed to create named pipe - ALREADY_EXISTS')

			os.mkfifo(self.__pipename__)
			self.__conn__: Stream.FileStream = Stream.FileStream(self.__pipename__, 'rb+')
			self.__isserver__: bool = True
			self.__open__: bool = not self.__conn__.closed

			if self.__conn__.closed:
				raise IOError(f'Failed to create named pipe - PIPE_OPEN_FAIL')

		def __del__(self) -> None:
			try:
				if not self.closed:
					self.close()
			except (IOError, AttributeError):
				pass

		def __setstate__(self, state: dict[str, typing.Any]) -> None:
			"""
			Deserializing function for setting from pickled state
			:param state: The pickled state
			:raises IOError: If failed to connect named pipe
			"""

			self.__dict__.update(state)
			self.__conn__: Stream.FileStream = Stream.FileStream(self.__pipename__, 'rb+')
			self.__isserver__: bool = False

			if self.__conn__.closed:
				raise IOError(f'Failed to connect to named pipe - PIPE_OPEN_FAIL')

		def __getstate__(self) -> dict[str, typing.Any]:
			"""
			Serializing function for retrieving pickle safe state
			:return: The pickle-able state
			"""

			attributes: dict[str, typing.Any] = self.__dict__.copy()
			del attributes['__open__']
			return attributes

		def __repr__(self) -> str:
			return str(self)

		def __str__(self) -> str:
			return f'<UnixNamedPipe[{self.__pipename__}-{"SERVER" if self.__isserver__ else "CLIENT"}] @ {hex(id(self))}>'

		def close(self) -> None:
			"""
			Closes the pipe
			All in-writing information is lost
			:raises IOError: If the pipe is already closed
			"""

			if self.closed:
				raise IOError('Pipe already closed')
			elif self.__isserver__:
				self.__conn__.close()
				os.unlink(self.__pipename__)
			else:
				self.__conn__.close()

		def flush(self) -> None:
			"""
			Flushes all data into pipe
			Blocks until data is written and read
			:raises IOError: If the pipe is closed
			"""

			if self.closed:
				raise IOError('Pipe is closed')

			self.__conn__.flush()

		def poll(self) -> int:
			"""
			Polls the number of bytes waiting in the buffer
			:return: The number of in-waiting bytes
			:raises IOError: If the pipe is closed
			"""

			if self.closed:
				raise IOError('Pipe is closed')

			return FileSystem.File(self.__pipename__).statsize()

		def dup(self) -> UnixNamedPipe:
			"""
			Duplicates the pipe, returning a client-side pipe connection
			:return: The new pipe connection
			:raises IOError: If the pipe failed to connect
			"""

			pipe: UnixNamedPipe = type(self).__new__(type(self))
			pipe.__setstate__(self.__getstate__())
			return pipe

		def send(self, data: typing.Any) -> UnixNamedPipe:
			"""
			Sends an object over the pipe
			Objects are serialized before transmission
			To write raw binary data, see UnixNamedPipe::write
			:param data: The object to write
			:return: This instance
			:raises IOError: If the pipe is closed or the write operation failed
			"""

			if self.closed:
				raise IOError('Pipe is closed')

			serialized: bytes = base64.b64encode(pickle.dumps(data))
			payload: bytes = len(serialized).to_bytes(8, 'little', signed=False) + serialized
			self.__conn__.write(payload)
			return self

		def write(self, data: bytes | bytearray) -> UnixNamedPipe:
			"""
			Writes binary data to the pipe
			To send standard objects, see UnixNamedPipe::send
			:param data: The bytes to write
			:return: This instance
			:raises IOError: If the pipe is closed or the write operation failed
			:raises InvalidArgumentException: If 'data' is not a bytes object or bytearray
			"""

			if self.closed:
				raise IOError('Pipe is closed')
			elif not isinstance(data, (bytes, bytearray)):
				raise Exceptions.InvalidArgumentException(WinNamedPipe.write, 'data', type(data), (bytes, bytearray))

			data: bytes = bytes(data)

			if len(data) == 0:
				return self

			self.__conn__.write(data)
			return self

		def recv(self) -> typing.Any:
			"""
			Receives an object from the pipe
			Objects are deserialized before returning
			To read raw binary data, see UnixNamedPipe::read
			:return: The deserialized object
			:raises IOError: If the pipe is closed or the read operation failed
			"""

			if self.closed:
				raise IOError('Pipe is closed')

			while (poll := self.poll()) < 8:
				if poll <= -1:
					raise BrokenPipeError('The pipe is invalid')

				time.sleep(1e-6)

			payload_length_b: bytes = self.__conn__.read(8)
			payload_length: int = int.from_bytes(payload_length_b, 'little', signed=False)

			while (poll := self.poll()) < payload_length:
				if poll <= -1:
					raise BrokenPipeError('The pipe is invalid')

				time.sleep(1e-6)

			payload: bytes = self.__conn__.read(payload_length)
			return pickle.loads(base64.b64decode(payload))

		def read(self, n: int = -1) -> bytes:
			"""
			Reads binary data from the pipe
			To read standard objects, see UnixNamedPipe::recv
			:param n: The number of bytes to read or all data if less than 0
			:return: The read bytes
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

			payload: bytes = self.__conn__.read(length)
			return payload

		@property
		def closed(self) -> bool:
			"""
			:return: Whether this pipe connection is closed
			"""

			return self.__conn__.closed

		@property
		def is_server(self) -> bool:
			"""
			:return: Whether this is the initial server pipe
			"""

			return self.__isserver__

	NamedPipe = UnixNamedPipe