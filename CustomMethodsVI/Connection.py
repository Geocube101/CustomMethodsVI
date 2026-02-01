# [=[ Connections.py for various socket based classes ]=]

from __future__ import annotations

import asyncio
import base64
import datetime
import flask
import flask_socketio
import ipaddress
import json
import os
import pickle
import re
import socketio
import sys
import threading
import time
import traceback
import typing
import uuid

from . import Concurrent
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
		self.__events__: dict[str, list[typing.Callable]] = {}
		self.__sockets__: dict[str, FlaskSocketioSocket] = {}
		self.__socket_events__: dict[str, dict[str, FlaskSocketioSocket]] = {}

	def __exec__(self, eid: str, *args, **kwargs) -> typing.Optional[tuple[typing.Any, ...]]:
		"""
		INTERNAL METHOD
		Executes all callbacks for a given event id
		:param eid: The event id to execute
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		"""

		if eid in self.__events__:
			responses: list[typing.Any] = []

			for callback in self.__events__[eid]:
				response: typing.Any

				if asyncio.iscoroutinefunction(callback):
					response = asyncio.run(callback(*args, **kwargs))
				else:
					response = callback(*args, **kwargs)

				responses.append(response)

			return tuple(responses)

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
			if (sid := flask.request.sid) in self.__sockets__:
				socket: FlaskSocketioSocket = self.__sockets__[sid]
				socket.__exec__('disconnect', socket.__is_disconnector__)
				socket.__connected__ = False
				del self.__sockets__[sid]

		@flask_socket.on('*', namespace=self.__namespace__)
		def catchall(event: str, *data) -> None:
			if (sid := flask.request.sid) in self.__sockets__ and event.startswith('roundtrip.'):
				eid: str = event.split('.')[1]
				socket: FlaskSocketioSocket = self.__sockets__[sid]
				response: typing.Optional[tuple[typing.Any, ...]] = socket.__exec__(eid, *data)
				socket.emit(event, *response)

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

	def __bind_callback__(self, eid: str, callback: typing.Callable) -> None:
		"""
		INTERNAL METHOD
		Binds a new callback for the specified event id
		:param eid: The event id to bind to
		:param callback: The callback to bind
		:raises AssertionError: If 'eid' is not a string or 'callback' is not callable
		"""

		assert isinstance(eid, str) and callable(callback)

		if eid not in self.__events__:
			self.__events__[eid] = [callback]
		else:
			self.__events__[eid].append(callback)

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
				self.__bind_callback__(eid, sub_func)
			return binder
		else:
			Misc.raise_ifn(callable(func), Exceptions.InvalidArgumentException(FlaskSocketioNamespace.on, 'func', type(func)))
			self.__bind_callback__(eid, func)

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
		self.__events__: dict[str, list[typing.Callable]] = {}
		self.__auth__ = auth
		self.__connected__: bool = True
		self.__request__: flask.Request = request
		
	def __exec__(self, eid: str, *args, **kwargs) -> typing.Optional[tuple[typing.Any, ...]]:
		"""
		INTERNAL METHOD
		Executes all callbacks for a given event id
		:param eid: The event id to execute
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		"""

		if eid in self.__events__:
			responses: list[typing.Any] = []

			for callback in self.__events__[eid]:
				response: typing.Any

				if asyncio.iscoroutinefunction(callback):
					response = asyncio.run(callback(*args, **kwargs))
				else:
					response = callback(*args, **kwargs)

				responses.append(response)

			return tuple(responses)

	def __bind_callback__(self, eid: str, callback: typing.Callable) -> None:
		"""
		INTERNAL METHOD
		Binds a new callback for the specified event id
		:param eid: The event id to bind to
		:param callback: The callback to bind
		:raises AssertionError: If 'eid' is not a string or 'callback' is not callable
		"""

		assert isinstance(eid, str) and callable(callback)

		if eid not in self.__events__:
			self.__events__[eid] = [callback]

			if eid not in __PRIVATE_IDS__:
				self.__space__.__bind_socket_event__(self, eid)

		else:
			self.__events__[eid].append(callback)

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
				self.__bind_callback__(eid, sub_func)
			return binder
		else:
			Misc.raise_ifn(callable(func), Exceptions.InvalidArgumentException(FlaskSocketioSocket.on, 'func', type(func)))
			self.__bind_callback__(eid, func)

	def off(self, eid: str, func: typing.Callable = None) -> None:
		"""
		Unbinds a specific listener from an event or all listeners if not specified
		:param eid: The event id to ignore
		:param func: The callback to remove or None for all callbacks
		:raises InvalidArgumentException: If eid is not a string
		"""

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(SocketioClient.emit, 'eid', type(eid), (str,)))
		contained: bool = (eid := str(eid)) in self.__events__

		if contained and func is not None and func in self.__events__[eid]:
			self.__events__[eid].remove(func)

			if len(self.__events__[eid]) == 0:
				del self.__events__[eid]

				if eid not in __PRIVATE_IDS__:
					self.__space__.__unbind_socket_event__(self, eid)

		elif contained and func is None:
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

	def emit_await_response[T](self, eid: str, *data) -> Concurrent.Promise[T]:
		"""
		Emits data to client and returns a promise holding the client's response
		:param eid: The event id to emit on
		:param data: The data to send
		:raises InvalidArgumentException: If eid is not a string
		:return: A promise holding the client's response. Response will be a tuple of all client event handler return values
		"""

		def __callback__(*response) -> None:
			self.off(eid, __callback__)
			promise.resolve(response)

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(SocketioClient.emit_await_response, 'eid', type(eid), (str,)))
		eid = f'roundtrip.{eid}.{uuid.uuid4()}'
		promise: Concurrent.Promise[T] = Concurrent.Promise()
		self.on(eid, __callback__)
		self.emit(eid, *data)
		return promise

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

		@self.__socket__.on('*', namespace=self.__space__)
		def catchall(event: str, *data) -> None:
			if event.startswith('roundtrip.'):
				eid: str = event.split('.')[1]
				response: typing.Optional[tuple[typing.Any, ...]] = self.__exec__(eid, *data)
				self.__socket__.emit(event, *response, namespace=self.__space__)

		self.__socket__.connect(self.__host__, namespaces=self.__space__)

	def __exec__(self, eid: str, *args, **kwargs) -> typing.Optional[tuple[typing.Any, ...]]:
		"""
		INTERNAL METHOD
		Executes all callbacks for a given event id
		:param eid: The event id to execute
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		"""

		if eid in self.__events__:
			responses: list[typing.Any] = []

			for callback in self.__events__[eid]:
				response: typing.Any

				if asyncio.iscoroutinefunction(callback):
					response = asyncio.run(callback(*args, **kwargs))
				else:
					response = callback(*args, **kwargs)

				responses.append(response)

			return tuple(responses)

	def __bind_callback__(self, eid: str, callback: typing.Callable) -> None:
		"""
		INTERNAL METHOD
		Binds a new callback for the specified event id
		:param eid: The event id to bind to
		:param callback: The callback to bind
		:raises AssertionError: If 'eid' is not a string or 'callback' is not callable
		"""

		assert isinstance(eid, str) and callable(callback)

		if eid not in self.__events__:
			self.__events__[eid] = [callback]

			@self.__socket__.on(eid, namespace=self.__space__)
			def handler(*args, **kwargs):
				self.__exec__(eid, *args, **kwargs)

		else:
			self.__events__[eid].append(callback)

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
					self.__bind_callback__(eid, callback)
				else:
					raise Exceptions.InvalidArgumentException(SocketioClient.on, 'func', type(callback))
			return bind_event
		elif callable(func):
			self.__bind_callback__(eid, func)
		else:
			raise Exceptions.InvalidArgumentException(SocketioClient.on, 'func', type(func))

	def off(self, eid: str, func: typing.Callable = None) -> None:
		"""
		Unbinds a specific listener from an event or all listeners if not specified
		:param eid: The event id to ignore
		:param func: The callback to remove or None for all callbacks
		:raises InvalidArgumentException: If eid is not a string
		"""

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(SocketioClient.emit, 'eid', type(eid), (str,)))
		contained: bool = (eid := str(eid)) in self.__events__

		if contained and func is not None and func in self.__events__[eid]:
			self.__events__[eid].remove(func)

			if len(self.__events__[eid]) == 0:
				del self.__socket__.handlers[self.__space__][eid]
				del self.__events__[eid]

		elif contained and func is None:
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

	def emit_await_response[T](self, eid: str, *data) -> Concurrent.Promise[T]:
		"""
		Emits data to server and returns a promise holding the server's response
		:param eid: The event id to emit on
		:param data: The data to send
		:raises InvalidArgumentException: If eid is not a string
		:return: A promise holding the server's response. Response will be a tuple of all server event handler return values
		"""

		def __callback__(*response) -> None:
			self.off(eid, __callback__)
			promise.resolve(response)

		Misc.raise_ifn(isinstance(eid, str), Exceptions.InvalidArgumentException(SocketioClient.emit_await_response, 'eid', type(eid), (str,)))
		eid = f'roundtrip.{eid}.{uuid.uuid4()}'
		promise: Concurrent.Promise[T] = Concurrent.Promise()
		self.on(eid, __callback__)
		self.emit(eid, *data)
		return promise

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


class FlaskServerAPI:
	"""
	Class wrapping generic functionality for flask API endpoints
	"""

	class APISessionInfo:
		"""
		Class holding API session information
		"""

		def __init__(self, ip: str | ipaddress.IPv4Address | ipaddress.IPv6Address, token: uuid.UUID, start_time: float | datetime.datetime):
			"""
			Class holding API session information
			- Constructor -
			:param ip: The client IP
			:param token: The session token
			:param start_time: The session start time
			"""

			self.__ip__: ipaddress.IPv4Address | ipaddress.IPv6Address = ip if isinstance(ip, (ipaddress.IPv4Address, ipaddress.IPv6Address)) else ipaddress.ip_address(str(ip))
			self.__token__: uuid.UUID = token
			self.__start__: datetime.datetime = datetime.datetime.fromtimestamp(start_time, datetime.timezone.utc) if isinstance(start_time, float) else start_time
			self.__state__: bool = True
			self.__duration__: float = -1
			self.__session_data__: dict[typing.Any, typing.Any] = {}

		def close(self) -> None:
			"""
			Closes this session
			Any further access by this client is denied
			"""

			self.__state__ = False

		@property
		def closed(self) -> bool:
			"""
			:return: This session's status
			"""

			if self.__duration__ != -1 and (datetime.datetime.now(datetime.timezone.utc) - self.__start__).total_seconds() > self.__duration__:
				self.__state__ = False

			return not self.__state__

		@property
		def duration(self) -> typing.Optional[float]:
			"""
			:return: This session's maximum duration in seconds or None if no duration is set
			"""

			return None if self.__duration__ == -1 else self.__duration__

		@duration.setter
		def duration(self, duration: typing.Optional[float]) -> None:
			"""
			Sets this session's duration
			:param duration: The duration in seconds or None to remove duration
			:raises ValueError: If 'duration' is not a float or negative
			"""

			if duration is None:
				self.__duration__ = -1
			elif isinstance(duration, float) and (duration := float(duration)) >= 0:
				self.__duration__ = float(duration)
			else:
				raise ValueError('Specified duration is invalid')

		@property
		def ip(self) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
			"""
			:return: This session's IP
			"""

			return self.__ip__

		@property
		def token(self) -> uuid.UUID:
			"""
			:return: This session's UUID token
			"""

			return self.__token__

		@property
		def start_time(self) -> datetime.datetime:
			"""
			:return: This session's start time
			"""

			return self.__start__

		@property
		def data(self) -> dict[typing.Any, typing.Any]:
			"""
			:return: Session data used to store persistent information
			"""

			return self.__session_data__

	__RESTRICTED_EIDS: tuple[str, ...] = ('connect', 'disconnect')

	@staticmethod
	def __parse_auth_token__(token: str) -> typing.Optional[uuid.UUID]:
		try:
			return uuid.UUID(int=int(token, 10)) if isinstance(token, str) and len(token := str(token)) > 0 else None
		except (ValueError, TypeError):
			return None
	
	def __init__(self, app: flask.Flask, route: str = '/api', *, requires_auth: bool = False):
		"""
		Class wrapping generic functionality for flask API endpoints\n
		- Constructor -
		:param app: The flask app
		:param route: The base api route
		:param requires_auth: Whether clients need authentication. If true, see 'FlaskServerAPI.connector' and 'FlaskServerAPI.disconnector' to control session authentication
		:raises InvalidArgumentException: If 'app' is not a Flask instance
		:raises InvalidArgumentException: If 'route' is not a string
		:raises InvalidArgumentException: If 'requires_auth' is not a boolean
		:raises ValueError: If 'route' is not alphanumeric or contains '\b', '\n', or '\t'
		"""

		Misc.raise_ifn(isinstance(app, flask.Flask), Exceptions.InvalidArgumentException(FlaskServerAPI.__init__, 'app', type(app), (flask.Flask,)))
		Misc.raise_ifn(isinstance(route, str), Exceptions.InvalidArgumentException(FlaskServerAPI.__init__, 'route', type(route), (str,)))
		Misc.raise_ifn(isinstance(requires_auth, bool), Exceptions.InvalidArgumentException(FlaskServerAPI.__init__, 'requires_auth', type(requires_auth), (bool,)))
		Misc.raise_if(not (route := str(route).strip('/\\')).isalnum() or any(x in ('\b', '\n', '\t') for x in route), ValueError('Route contains invalid characters'))

		super().__init__()
		self.__app__: flask.Flask = app
		self.__route__: str = f'/{route}'
		self.__sessions__: dict[uuid.UUID, FlaskServerAPI.APISessionInfo] = {}
		self.__callbacks__: dict[str, tuple[typing.Callable[[FlaskServerAPI.APISessionInfo, typing.Mapping[str, typing.Any]], typing.Mapping[str, typing.Any] | typing.Sequence[typing.Any]], bool]] = {}
		self.__auth__: bool = bool(requires_auth)
		self.__connector__: typing.Optional[typing.Callable[[FlaskServerAPI.APISessionInfo, typing.Mapping[str, typing.Any]], bool | int | typing.Mapping[str, typing.Any] | None] | tuple[bool | int, typing.Mapping[str, typing.Any]]] = None
		self.__disconnector__: typing.Optional[typing.Callable[[FlaskServerAPI.APISessionInfo, typing.Mapping[str, typing.Any]], typing.Mapping[str, typing.Any] | None]] = None
		self.__setup_auth_channels__()
		self.__app__.add_url_rule(f'{self.__route__}/<path:route>', view_func=self.__flask_route__, provide_automatic_options=False, methods=('POST',), endpoint=f'{self.__route__.replace('/', '_')}_flaskroute')
			
	def __setup_auth_channels__(self) -> None:
		"""
		INTERNAL METHOD\n
		Binds the flask routes used for connection and disconnection requests
		If the API does not have authentication enabled, this method does nothing
		"""

		if not self.__auth__:
			return
		
		@self.__app__.route(f'{self.__route__}/connect', methods=('POST',), endpoint=f'{self.__route__.replace('/', '_')}_connect')
		def connect():
			if flask.request.content_type != 'application/json':
				return flask.Response(response={'error': 'invalid-content-type'}, status=415, content_type='application/json')
			elif self.__connector__ is None:
				return flask.Response(json.dumps({'auth': 0}), content_type='application/json')

			token: uuid.UUID = self.__next_token__()
			session: FlaskServerAPI.APISessionInfo = FlaskServerAPI.APISessionInfo(flask.request.remote_addr, token, datetime.datetime.now(datetime.timezone.utc))
			response: typing.Mapping[str, typing.Any] | bool | int | None | tuple[bool | int, typing.Mapping[str, typing.Any]] = None

			try:
				response = self.__connector__(session, flask.request.json)
			except Exception as e:
				sys.stderr.write(''.join(traceback.format_exception(e)))
			
			if isinstance(response, (bool, int, tuple, typing.Mapping)):
				ok: bool | int
				res: bool | int | typing.Mapping[str, typing.Any]

				if isinstance(response, tuple):
					ok = (response := tuple(response))[0]
					res = response[1]
				elif isinstance(response, typing.Mapping):
					ok = True
					res = response
				else:
					ok = response
					res = response

				if (isinstance(ok, bool) and bool(ok)) or (isinstance(ok, int) and 200 <= int(ok) < 300):
					self.__sessions__[token] = session
					content: dict[str, typing.Any] = {'auth': str(token.int)}

					if isinstance(res, dict):
						content['body'] = res

					return flask.Response(json.dumps(content), content_type='application/json')
				else:
					return flask.Response(json.dumps({'auth': None}), status=200 if isinstance(ok, bool) and ok else int(ok), content_type='application/json')
			elif response is not None:
				raise TypeError('Unexpected response type from connector callback - Expected either a boolean, integer, JSON dictionary, or None')
			else:
				return flask.Response(json.dumps({'auth': None}), status=401, content_type='application/json')
		
		@self.__app__.route(f'{self.__route__}/disconnect', methods=('POST',), endpoint=f'{self.__route__.replace('/', '_')}_disconnect')
		def disconnect():
			if flask.request.content_type != 'application/json':
				return flask.Response(response=json.dumps({'error': 'invalid-content-type'}), status=415, content_type='application/json')
			elif (session := self.__sessions__.get(auth := FlaskServerAPI.__parse_auth_token__(flask.request.json.get('auth')))) is not None and not session.closed:
				del self.__sessions__[auth]
				response: dict[typing.Any] | None = None

				if self.__disconnector__ is not None:
					try:
						response = self.__disconnector__(session, flask.request.json)
					except Exception as e:
						sys.stderr.write(''.join(traceback.format_exception(e)))

				content: dict[str, typing.Any] = {} if response is None else response

				if not isinstance(content, dict):
					raise TypeError('Unexpected response type from disconnector callback - Expected either a JSON dictionary or None')

				return flask.Response(json.dumps(content), content_type='application/json')
			else:
				return flask.Response(response=json.dumps({'error': 'not-authenticated'}), status=401, content_type='application/json')

	def __flask_route__(self, route: str) -> flask.Response:
		"""
		INTERNAL METHOD\n
		Generic routing callback for flask API endpoints
		:param route: The base API route
		:return: The resulting callback response
		"""

		if route not in self.__callbacks__:
			return flask.Response(response=json.dumps({'error': 'no-api-endpoint'}), status=404, content_type='application/json')
		elif flask.request.content_type != 'application/json':
			return flask.Response(response=json.dumps({'error': 'invalid-content-type'}), status=415, content_type='application/json')
		elif (auth := FlaskServerAPI.__parse_auth_token__(flask.request.json.get('auth'))) is None and self.__auth__:
			return flask.Response(response=json.dumps({'error': 'not-authenticated'}), status=401, content_type='application/json')
		else:
			callback, requires_auth = self.__callbacks__[route]
			session: typing.Optional[FlaskServerAPI.APISessionInfo] = self.__sessions__.get(auth)

			if self.__auth__ and requires_auth and (session is None or session.closed):
				return flask.Response(response=json.dumps({'error': 'not-authenticated'}), status=401, content_type='application/json')

			try:
				response: typing.Mapping[str, typing.Any] | typing.Sequence[typing.Any] | int | None = callback(session, flask.request.json)

				if response is None or response is ...:
					return flask.Response(json.dumps({}), status=200, content_type='application/json')
				elif response is NotImplemented:
					return flask.Response(json.dumps({'error': 'NotImplemented'}), status=501, content_type='application/json')
				elif isinstance(response, int):
					return flask.Response(json.dumps({'error': 'NotImplemented'}), status=int(response), content_type='application/json')
				elif isinstance(response, (typing.Mapping, typing.Sequence)):
					return flask.Response(json.dumps(response), status=200, content_type='application/json')
				else:
					raise TypeError(f'Unexpected response type from API callback \'{route}\' - Expected either a JSON dictionary or None')

			except Exception as e:
				sys.stderr.write(''.join(traceback.format_exception(e)))
				return flask.Response(json.dumps({'error': 'An internal error has occurred'}), status=500, content_type='application/json')

	def __next_token__(self) -> uuid.UUID:
		"""
		INTERNAL METHOD
		:return: A new, unique session ID
		"""

		token: uuid.UUID = uuid.uuid4()

		while token in [session.token for session in self.__sessions__.values() if not session.closed]:
			token = uuid.uuid4()

		return token

	def add_session(self, session: FlaskServerAPI.APISessionInfo) -> None:
		"""
		Adds a session directly to this API's session list
		:param session: The unclosed session to add
		:raises InvalidArgumentException: If 'session' is not an APISessionInfo instance
		:raises RuntimeError: If 'session' is closed
		:raises RuntimeError: If this API doesn't support authentication
		:raises RuntimeError: If the session's token already exists
		"""

		Misc.raise_ifn(isinstance(session, FlaskServerAPI.APISessionInfo), Exceptions.InvalidArgumentException(FlaskServerAPI.add_session, 'session', type(session), (FlaskServerAPI.APISessionInfo,)))
		Misc.raise_if(session.closed, RuntimeError('Specified session is already closed'))
		Misc.raise_ifn(self.__auth__, RuntimeError('This API does not support authentication'))
		Misc.raise_if(session.token in [s.token for s in self.__sessions__.values() if not s.closed], RuntimeError('Session token already exists'))
		self.__sessions__[session.token] = session

	def close_session(self, token: uuid.UUID) -> None:
		"""
		Closes a session by uuid
		:param token: The session's UUID
		:raises InvalidArgumentException: If 'token' is not a UUID
		"""

		Misc.raise_ifn(isinstance(token, uuid.UUID), Exceptions.InvalidArgumentException(FlaskServerAPI.close_session, 'token', type(token), (uuid.UUID,)))

		if (session := self.__sessions__.pop(token, None)) is not None:
			session.close()

	def open_session(self, ip: str | ipaddress.IPv4Address | ipaddress.IPv6Address, start_time: typing.Optional[float | datetime.datetime] = ...) -> FlaskServerAPI.APISessionInfo:
		"""
		Opens a new client API session\n
		Sessions may only be explicitly opened if this API requires authentication
		:param ip: The session's IP
		:param start_time: The session's start time or current if unset
		:return: The new session's token
		:raises InvalidArgumentException: If 'ip' is not a string or ip address
		:raises InvalidArgumentException: If 'start_time' is not a float or datetime instance
		:raises ValueError: If 'ip' is a string and the length of 'ip' is 0
		:raises RuntimeError: If this API doesn't support authentication
		"""

		Misc.raise_ifn(isinstance(ip, (str, ipaddress.IPv4Address, ipaddress.IPv6Address)), Exceptions.InvalidArgumentException(FlaskServerAPI.open_session, 'ip', type(ip), (str, ipaddress.IPv4Address, ipaddress.IPv6Address)))
		Misc.raise_ifn(isinstance(start_time, (float, datetime.datetime)), Exceptions.InvalidArgumentException(FlaskServerAPI.open_session, 'start_time', type(start_time), (float, datetime.datetime, int)))
		Misc.raise_if(isinstance(ip, str) and len(ip := str(ip)) == 0, ValueError('Invalid session IP'))
		Misc.raise_ifn(self.__auth__, RuntimeError('This API does not support authentication'))
		token: uuid.UUID = self.__next_token__()
		session: FlaskServerAPI.APISessionInfo = FlaskServerAPI.APISessionInfo(ip, token, start_time)
		self.__sessions__[token] = session
		return session

	def get_sessions_by_ip(self, ip: str | ipaddress.IPv4Address | ipaddress.IPv6Address) -> list[FlaskServerAPI.APISessionInfo]:
		"""
		Gets all sessions with the specified IP
		:param ip: The target IP address
		:return: A list of matching client sessions
		:raises InvalidArgumentException: If 'ip' is not a string or ip address
		"""

		Misc.raise_ifn(isinstance(ip, (str, ipaddress.IPv4Address, ipaddress.IPv6Address)), Exceptions.InvalidArgumentException(FlaskServerAPI.get_sessions_by_ip, 'ip', type(ip), (str, ipaddress.IPv4Address, ipaddress.IPv6Address)))
		ip: ipaddress.IPv4Address | ipaddress.IPv6Address = ipaddress.ip_address(ip)
		return [session for session in self.__sessions__.values() if session.ip == ip]

	def get_session_by_token(self, token: uuid.UUID | int | str) -> typing.Optional[FlaskServerAPI.APISessionInfo]:
		"""
		Gets a session by IP
		:param token: The target token
		:return: The client session or None if not found
		:raises InvalidArgumentException: If 'token' is not an integer
		"""

		Misc.raise_ifn(isinstance(token, (uuid.UUID, int, str)), Exceptions.InvalidArgumentException(FlaskServerAPI.get_session_by_token, 'token', type(token), (uuid.UUID, int, str)))
		true_token: uuid.UUID = token if isinstance(token, uuid.UUID) else uuid.UUID(int=int(token), version=4)
		matches: tuple[FlaskServerAPI.APISessionInfo, ...] = tuple(session for session in self.__sessions__.values() if session.token == true_token)
		return matches[0] if len(matches) == 1 else None

	def endpoint(self, route: str, callback: typing.Optional[typing.Callable[[FlaskServerAPI.APISessionInfo, typing.Mapping[str, typing.Any]], typing.Mapping[str, typing.Any] | typing.Sequence[typing.Any]]] = ..., *, requires_auth: bool = True) -> typing.Optional[typing.Callable[[typing.Callable[[FlaskServerAPI.APISessionInfo, typing.Mapping[str, typing.Any]], typing.Mapping[str, typing.Any] | typing.Sequence[typing.Any]]], None]]:
		"""
		Binds a callback to the specified API endpoint
		:param route: The API endpoint
		:param callback: The callback
		:param requires_auth: Whether this endpoint requires an authenticated session
		:return: None or a binder if used as a decorator
		:raises InvalidArgumentException: If 'route' is not a string
		:raises InvalidArgumentException: If 'requires_auth' is not a boolean
		:raises ValueError: If 'route' is empty, already bound, contains invalid characters, or is a restricted event ID
		"""

		Misc.raise_ifn(isinstance(route, str), Exceptions.InvalidArgumentException(FlaskServerAPI.endpoint, 'route', type(route), (str,)))
		Misc.raise_ifn(isinstance(requires_auth, bool), Exceptions.InvalidArgumentException(FlaskServerAPI.endpoint, 'requires_auth', type(requires_auth), (bool,)))
		Misc.raise_if(len(route := str(route).strip('/\\')) == 0, ValueError('Route cannot be empty'))
		Misc.raise_if(re.fullmatch(r'^[\w\-_]+$', route) is None, ValueError('Route contains invalid characters'))

		if route in FlaskServerAPI.__RESTRICTED_EIDS:
			raise ValueError(f'Specified event ID \'{route}\' is restricted')

		if callback is None or callback is ...:
			def binder(func: typing.Callable[[FlaskServerAPI.APISessionInfo, typing.Mapping[str, typing.Any]], typing.Mapping[str, typing.Any] | typing.Sequence[typing.Any]]) -> None:
				self.endpoint(route, func, requires_auth=requires_auth)

			return binder
		elif callable(callback) and route in self.__callbacks__:
			raise ValueError('Specified API route is already bound')
		elif callable(callback):
			self.__callbacks__[route] = (callback, bool(requires_auth))
		else:
			raise ValueError('Callback is not callable')

	def connector(self, callback: typing.Optional[typing.Callable[[FlaskServerAPI.APISessionInfo, dict[str, typing.Any]], bool | int | typing.Mapping[str, typing.Any] | None] | tuple[bool | int, typing.Mapping[str, typing.Any]]] = None) -> typing.Optional[typing.Callable[[typing.Callable[[FlaskServerAPI.APISessionInfo, typing.Mapping[str, typing.Any]], bool | int | typing.Mapping[str, typing.Any] | None] | tuple[bool | int, typing.Mapping[str, typing.Any]]], None]]:
		"""
		Binds a callback to the connection event\n
		The callback bound may return the following:\n
		 * boolean 	- If true, the calling client will be authenticated until session close\n
		 * integer 	- If OK (200 - 299), the calling client will be authenticated until session close\n
		 * None		- Connection will be refused\n
		 * JSON		- Calling client will be authenticated and the returned JSON sent\n
		A callback may also return a tuple whose first element is a boolean or integer, and whose second element is the JSON
		:param callback: The callback to bind accepting the new session instance and the request JSON
		:return: None or a binder if used as a decorator
		:raises RuntimeError: If a connection callback was already assigned
		:raises RuntimeError: If this API doesn't support authentication
		:raises ValueError: If the specified callback is not callable
		"""

		if callback is None:
			def binder(func: typing.Callable[[FlaskServerAPI.APISessionInfo, typing.Mapping[str, typing.Any]], bool | int | typing.Mapping[str, typing.Any] | None]) -> None:
				self.connector(func)

			return binder
		elif self.__connector__ is not None:
			raise RuntimeError('A connection callback was already assigned')
		elif not self.__auth__:
			raise RuntimeError('This API does not support authentication')
		elif not callable(callback):
			raise ValueError('Specified callback is not callable')
		else:
			self.__connector__ = callback

	def disconnector(self, callback: typing.Optional[typing.Callable[[FlaskServerAPI.APISessionInfo, typing.Mapping[str, typing.Any]], bool | int | typing.Mapping[str, typing.Any] | None] | tuple[bool | int, typing.Mapping[str, typing.Any]]] = None) -> typing.Optional[typing.Callable[[typing.Callable[[FlaskServerAPI.APISessionInfo, typing.Mapping[str, typing.Any]], bool | int | typing.Mapping[str, typing.Any] | None] | tuple[bool | int, typing.Mapping[str, typing.Any]]], None]]:
		"""
		Binds a callback to the disconnection event\n
		The callback may return JSON to send to client on disconnect
		:param callback: The callback to bind accepting the request JSON
		:return: None or a binder if used as a decorator
		:raises RuntimeError: If a disconnection callback was already assigned
		:raises RuntimeError: If this API doesn't support authentication
		:raises ValueError: If the specified callback is not callable
		"""

		if callback is None:
			def binder(func: typing.Callable[[FlaskServerAPI.APISessionInfo, typing.Mapping[str, typing.Any]], bool | int | typing.Mapping[str, typing.Any] | None]) -> None:
				self.disconnector(func)

			return binder
		elif self.__disconnector__ is not None:
			raise RuntimeError('A disconnection callback was already assigned')
		elif not self.__auth__:
			raise RuntimeError('This API does not support authentication')
		elif not callable(callback):
			raise ValueError('Specified callback is not callable')
		else:
			self.__disconnector__ = callback

	def sessions(self) -> tuple[FlaskServerAPI.APISessionInfo, ...]:
		"""
		:return: A mapping of all session objects
		"""

		return tuple(session for session in self.__sessions__.values() if not session.closed)


if sys.platform == 'win32':
	import pywintypes

	import win32pipe
	import win32file
	import win32security
	import win32api

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
			except (IOError, AttributeError, pywintypes.error):
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