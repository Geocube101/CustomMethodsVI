from __future__ import annotations

import collections.abc
import multiprocessing
import multiprocessing.connection
import os
import sys
import threading
import time
import traceback
import typing

from .. import Exceptions
from .. import Misc


class Promise[T]:
	"""
	Standard promise class representing a value than can be resolved later
	"""

	def __init__(self):
		"""
		Standard promise class representing a value than can be resolved later
		- Constructor -
		"""

		self.__response__: tuple[bool, typing.Any] | None = None
		self.__callbacks__: list[collections.abc.Callable] = []

	def __await__(self) -> collections.abc.Iterator[None]:
		while not self.fulfilled():
			yield None

		return self.response(True)

	def fulfilled(self) -> bool:
		"""
		:return: Whether this promise is fulfilled
		"""

		return self.__response__ is not None

	def throw(self, err: BaseException) -> None:
		"""
		Resolves this promise with an error
		Any attempt to poll this promise on consumer side will raise that error
		:param err: The error to resolve with
		:raises IOError: If promise is already fulfilled
		:raises InvalidArgumentException: If 'err' is not an exception
		"""

		if self.__response__ is not None:
			raise IOError('Response already sent')
		else:
			Misc.raise_ifn(isinstance(err, BaseException), Exceptions.InvalidArgumentException(Promise.throw, 'err', type(err), (BaseException,)))
			self.__response__ = (False, err)

			for i, cb in enumerate(self.__callbacks__):
				try:
					cb(self)
				except Exception as e:
					sys.stderr.write(f'Error-{type(e).__name__} during Promise callback[{i}]:\n\t...\n{"".join(traceback.format_exception(e))}')
					sys.stderr.flush()

	def resolve(self, obj: T) -> None:
		"""
		Resolves this promise with a value
		Any attempt to poll this promise on consumer side will return that value
		:param obj: The response to resolve with
		:raises IOError: If promise is already fulfilled
		"""

		if self.__response__ is not None:
			raise IOError('Response already sent')
		else:
			self.__response__ = (True, obj)

			for i, cb in enumerate(self.__callbacks__):
				try:
					cb(self)
				except Exception as e:
					sys.stderr.write(f'Error-{type(e).__name__} during Promise callback[{i}]:\n\t...\n{"".join(traceback.format_exception(e))}')
					sys.stderr.flush()

	def wait(self, throw_err: bool = True, timeout: typing.Optional[float] = ...) -> T | BaseException:
		"""
		Blocks current thread until this promise is fulfilled
		Will raise an error if producer resolved with "throw"
		:param throw_err: If true, will throw error if promise erred
		:param timeout: The time in seconds to wait before throwing a timeout error if 'throw_err' else '...'
		:return: The response value or '...' if not fulfilled in time and 'throw_err' is False
		:raises TimeoutError: If timeout is specified, 'throw_err' is True, and promise not fulfilled before timeout
		"""

		Misc.raise_ifn(timeout is ... or timeout is None or isinstance(timeout, (float, int)), Exceptions.InvalidArgumentException(Promise.wait, 'timeout', type(timeout), (float, int)))
		timeout: typing.Optional[float] = None if timeout is None or timeout is ... else float(timeout)
		t1: float = time.perf_counter()

		while not self.fulfilled() and (timeout is None or time.perf_counter() - t1 < timeout):
			time.sleep(1e-6)

		if not (done := self.fulfilled()) and throw_err:
			raise TimeoutError('Promise timed out')

		return self.response(throw_err) if done else ...

	def then(self, callback: collections.abc.Callable[[Promise[T]], ...]) -> None:
		"""
		Binds a callback to execute once this promise is fulfilled
		Callback should be a callable accepting this promise as the first argument
		:param callback: The callback to bind
		:raises IOError: If promise already fulfilled
		:raises InvalidArgumentException: If callback is not callable
		"""

		Misc.raise_ifn(self.__response__ is None, IOError('Response already handled'))
		Misc.raise_ifn(callable(callback), Exceptions.InvalidArgumentException(Promise.then, 'callback', type(callback)))
		self.__callbacks__.append(callback)

	def response(self, throw_err: bool = True) -> T | BaseException:
		"""
		Polls this promise for a response
		:param throw_err: If true, throws the associated error (if producer used "throw") otherwise, the error is returned
		:return: The response value or the associated error
		:raises IOError: If promise is not fulfilled
		"""

		if self.__response__ is not None:
			state, msg = self.__response__

			if state or not throw_err:
				return msg
			else:
				raise msg
		else:
			raise IOError('No response received')

	def has_erred(self) -> bool | None:
		"""
		Checks if this promise was resolved with "throw"
		:return: None if promise is not fulfilled otherwise whether the promise has erred
		"""

		if self.__response__ is not None:
			state, _ = self.__response__
			return not state
		else:
			return None


class ConcurrentPromise[T](Promise):
	"""
	Class handling single IPC event from ConcurrentFunction
	"""

	def __init__(self):
		"""
		Class handling single IPC event from ConcurrentFunction
		- Constructor -
		"""

		super().__init__()
		self.__pipes__: tuple[multiprocessing.connection.Connection, ...] = multiprocessing.Pipe(False)
		self.__src__: int = os.getpid()
		self.__poll_thread__: typing.Optional[threading.Thread] = None

	def __await__(self) -> collections.abc.Iterator[None]:
		while not self.fulfilled():
			yield

	def __poll_loop(self) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Started on a new thread to poll internal pipes for response
		"""

		self.wait()

		for i, cb in enumerate(self.__callbacks__):
			try:
				cb(self)
			except Exception as e:
				sys.stderr.write(f'Error-{type(e).__name__} during Promise callback[{i}]:\n\t...\n{"".join(traceback.format_exception(e))}')
				sys.stderr.flush()

	def fulfilled(self) -> bool:
		return self.__response__ is not None or self.__pipes__[0].poll()

	def throw(self, err: BaseException) -> None:
		"""
		Resolves this promise with an error
		Any attempt to poll this promise on consumer side will raise that error
		:param err: The error to resolve with
		:raises IOError: If promise is already fulfilled
		:raises InvalidArgumentException: If 'err' is not an exception
		:raises IOError: If thrown from consumer end
		"""

		if os.getpid() == self.__src__:
			raise IOError('Cannot send reply as consumer')
		elif self.__pipes__[1].closed:
			raise IOError('Response already sent')
		else:
			Misc.raise_ifn(isinstance(err, BaseException), Exceptions.InvalidArgumentException(ConcurrentPromise.throw, 'err', type(err), (BaseException,)))
			self.__pipes__[1].send((False, err))
			self.__pipes__[1].close()

	def resolve(self, obj: T) -> None:
		"""
		Resolves this promise with a value
		Any attempt to poll this promise on consumer side will return that value
		:param obj: The response to resolve with
		:raises IOError: If promise is already fulfilled
		:raises IOError: If resolved from consumer end
		"""

		if os.getpid() == self.__src__:
			raise IOError('Cannot send reply as consumer')
		elif self.__pipes__[1].closed:
			raise IOError('Response already sent')
		else:
			self.__pipes__[1].send((True, obj))
			self.__pipes__[1].close()

	def wait(self, throw_err: bool = True, timeout: typing.Optional[float] = ...) -> T | BaseException:
		"""
		Blocks current thread until this promise is fulfilled
		Will raise an error if producer resolved with "throw"
		:param throw_err: If true, will throw error if promise erred
		:param timeout: The time in seconds to wait before throwing a timeout error if 'throw_err' else '...'
		:return: The response value or '...' if not fulfilled in time and 'throw_err' is False
		:raises IOError: If polled from producer end
		:raises TimeoutError: If timeout is specified, 'throw_err' is True, and promise not fulfilled before timeout
		"""

		Misc.raise_ifn(timeout is ... or timeout is None or isinstance(timeout, (float, int)), Exceptions.InvalidArgumentException(Promise.wait, 'timeout', type(timeout), (float, int)))
		timeout: typing.Optional[float] = None if timeout is None or timeout is ... else float(timeout)
		t1: float = time.perf_counter()

		if os.getpid() == self.__src__:
			while not self.fulfilled() and (timeout is None or time.perf_counter() - t1 < timeout):
				time.sleep(1e-6)

			if not (done := self.fulfilled()) and throw_err:
				raise TimeoutError('Promise timed out')

			return self.response(throw_err) if done else ...
		else:
			raise IOError('Cannot poll reply as producer')

	def then(self, callback: collections.abc.Callable[[ConcurrentPromise[T]], None]) -> None:
		"""
		Binds a callback to execute once this promise is fulfilled
		Callback should be a callable accepting this promise as the first argument
		:param callback: The callback to bind
		:raises IOError: If promise already fulfilled
		:raises InvalidArgumentException: If callback is not callable
		:raises IOError: If polled from producer end
		"""

		Misc.raise_ifn(self.__response__ is None, IOError('Response already handled'))
		Misc.raise_ifn(callable(callback), Exceptions.InvalidArgumentException(ConcurrentPromise.then, 'callback', type(callback)))

		if os.getpid() != self.__src__:
			raise IOError('Cannot poll reply as producer')
		elif self.__poll_thread__ is None:
			self.__poll_thread__ = threading.Thread(target=self.__poll_loop)
			self.__poll_thread__.start()

		self.__callbacks__.append(callback)

	def response(self, throw_err: bool = True) -> T | BaseException:
		"""
		Polls this promise for a response
		:param throw_err: If true, throws the associated error (if producer used "throw") otherwise, the error is returned
		:return: The response value or the associated error
		:raises IOError: If promise is not fulfilled
		:raises IOError: If polled from producer end
		"""

		if os.getpid() == self.__src__:
			if self.__response__ is not None:
				state, msg = self.__response__

				if state or not throw_err:
					return msg
				else:
					raise msg

			elif self.__pipes__[0].poll():
				state, msg = self.__pipes__[0].recv()
				self.__response__ = (state, msg)
				self.__pipes__[0].close()

				if state or not throw_err:
					return msg
				else:
					raise msg
			else:
				raise IOError('No response received')
		else:
			raise IOError('Cannot poll reply as producer')

	def has_erred(self) -> bool | None:
		if self.__response__ is not None:
			state, _ = self.__response__
			return not state
		elif self.__pipes__[0].poll():
			state, msg = self.__pipes__[0].recv()
			self.__response__ = (state, msg)
			return not state
		else:
			return None


class ThreadedPromise[T](Promise):
	"""
	Class handling single ITC event from ThreadedFunction
	"""

	def __init__(self):
		"""
		Class handling single ITC event from ThreadedFunction
		- Constructor -
		"""

		super().__init__()
		self.__response__: typing.Optional[tuple[bool, typing.Any]] = None
		self.__src__: int = threading.current_thread().native_id

	def fulfilled(self) -> bool:
		return self.__response__ is not None

	def throw(self, err: BaseException) -> None:
		"""
		Resolves this promise with an error
		Any attempt to poll this promise on consumer side will raise that error
		:param err: The error to resolve with
		:raises IOError: If promise is already fulfilled
		:raises InvalidArgumentException: If 'err' is not an exception
		:raises IOError: If thrown from consumer end
		"""

		if threading.current_thread().native_id == self.__src__:
			raise IOError('Cannot send reply as consumer')
		elif self.__response__ is not None:
			raise IOError('Response already sent')
		else:
			Misc.raise_ifn(isinstance(err, BaseException), Exceptions.InvalidArgumentException(ThreadedPromise.throw, 'err', type(err), (BaseException,)))
			self.__response__ = (False, err)

			for i, cb in enumerate(self.__callbacks__):
				try:
					cb(self)
				except Exception as e:
					sys.stderr.write(f'Error-{type(e).__name__} during Promise callback[{i}]:\n\t...\n{"".join(traceback.format_exception(e))}')
					sys.stderr.flush()

	def resolve(self, obj: T) -> None:
		"""
		Resolves this promise with a value
		Any attempt to poll this promise on consumer side will return that value
		:param obj: The response to resolve with
		:raises IOError: If promise is already fulfilled
		:raises IOError: If resolved from consumer end
		"""

		if threading.current_thread().native_id == self.__src__:
			raise IOError('Cannot send reply as consumer')
		elif self.__response__ is not None:
			raise IOError('Response already sent')
		else:
			self.__response__ = (True, obj)

			for i, cb in enumerate(self.__callbacks__):
				try:
					cb(self)
				except Exception as e:
					sys.stderr.write(f'Error-{type(e).__name__} during Promise callback[{i}]:\n\t...\n{"".join(traceback.format_exception(e))}')
					sys.stderr.flush()

	def wait(self, throw_err: bool = True, timeout: typing.Optional[float] = ...) -> T | BaseException:
		"""
		Blocks current thread until this promise is fulfilled
		Will raise an error if producer resolved with "throw"
		:param throw_err: If true, will throw error if promise erred
		:param timeout: The time in seconds to wait before throwing a timeout error if 'throw_err' else '...'
		:return: The response value or '...' if not fulfilled in time and 'throw_err' is False
		:raises IOError: If polled from producer end
		:raises TimeoutError: If timeout is specified, 'throw_err' is True, and promise not fulfilled before timeout
		"""

		Misc.raise_ifn(timeout is ... or timeout is None or isinstance(timeout, (float, int)), Exceptions.InvalidArgumentException(Promise.wait, 'timeout', type(timeout), (float, int)))
		timeout: typing.Optional[float] = None if timeout is None or timeout is ... else float(timeout)
		t1: float = time.perf_counter()

		if threading.current_thread().native_id == self.__src__ or self.fulfilled():
			while not self.fulfilled() and (timeout is None or time.perf_counter() - t1 < timeout):
				time.sleep(1e-6)

			if not (done := self.fulfilled()) and throw_err:
				raise TimeoutError('Promise timed out')

			return self.response(throw_err) if done else ...
		else:
			raise IOError('Cannot poll reply as producer')

	def response(self, throw_err: bool = True) -> T | BaseException:
		"""
		Polls this promise for a response
		:param throw_err: If true, throws the associated error (if producer used "throw") otherwise, the error is returned
		:return: The response value or the associated error
		:raises IOError: If promise is not fulfilled
		:raises IOError: If polled from producer end
		"""

		if threading.current_thread().native_id == self.__src__ or self.fulfilled():
			if self.__response__ is not None:
				state, msg = self.__response__

				if state or not throw_err:
					return msg
				else:
					raise msg
			else:
				raise IOError('No response received')
		else:
			raise IOError('Cannot poll reply as producer')


__all__: list[str] = ['Promise', 'ConcurrentPromise', 'ThreadedPromise']
