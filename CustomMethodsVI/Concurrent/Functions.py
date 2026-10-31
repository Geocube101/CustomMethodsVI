from __future__ import annotations

import collections.abc
import multiprocessing
import multiprocessing.connection
import multiprocessing.queues
import multiprocessing.reduction
import multiprocessing.resource_sharer
import multiprocessing.shared_memory
import psutil
import threading
import typing

from . import Promise

from .. import Exceptions
from .. import Misc


class ThreadedFunction[R]:
	"""
	Class handling function spawned on a separate threading.Thread
	"""

	def __init__(self, function: collections.abc.Callable[..., R]):
		"""
		Class handling function spawned on a separate threading.Thread
		- Constructor -
		:param function: A callable object
		:raises InvalidArgumentException: If 'function' is not callable
		"""

		Misc.raise_ifn(callable(function), Exceptions.InvalidArgumentException(ThreadedFunction.__init__, 'function', type(function)))
		self.__cb__: collections.abc.Callable = function
		self.__thread__: typing.Optional[threading.Thread] = None

	def __wrapper__(self, promise: Promise.ThreadedPromise[R], *args: tuple, **kwargs: dict) -> None:
		"""
		INTERNAL METHOD
		Calls the function, handling all errors, and responds to promise accordingly
		:param promise: The promise to respond to
		:param args: The function's positional arguments
		:param kwargs: The function's keyword arguments
		"""

		try:
			promise.resolve(self.__cb__(*args, **kwargs))
		except (KeyboardInterrupt, Exception) as err:
			promise.throw(err)

	def __call__(self, *args, **kwargs) -> Promise.ThreadedPromise[R]:
		"""
		Calls the underlying function in a new threading.Thread
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		:return: A new ThreadedPromise
		"""

		promise: Promise.ThreadedPromise[R] = Promise.ThreadedPromise()
		self.__thread__ = threading.Thread(target=self.__wrapper__, args=(promise, *args), kwargs=kwargs)
		self.__thread__.start()
		return promise


class ConcurrentFunction[R]:
	"""
	Class handling function spawned on a separate multiprocessing.Process
	"""

	def __init__(self, function: collections.abc.Callable[..., R]):
		"""
		Class handling function spawned on a separate multiprocessing.Process
		- Constructor -
		:param function: A callable object
		:raises InvalidArgumentException: If 'function' is not callable
		"""

		Misc.raise_ifn(callable(function), Exceptions.InvalidArgumentException(ThreadedFunction.__init__, 'function', type(function)))
		self.__cb__: collections.abc.Callable = function
		self.__thread__: typing.Optional[multiprocessing.Process] = None

	@staticmethod
	def __wrapper__(promise: Promise.ConcurrentPromise[R], func: collections.abc.Callable, *args: tuple, **kwargs: dict) -> None:
		"""
		INTERNAL METHOD
		Calls the function, handling all errors, and responds to promise accordingly
		:param promise: The promise to respond to
		:param func: The callable to call
		:param args: The function's positional arguments
		:param kwargs: The function's keyword arguments
		"""

		try:
			promise.resolve(func(*args, **kwargs))
		except (SystemExit, KeyboardInterrupt, Exception) as err:
			promise.throw(err)

	def __call__(self, *args, **kwargs) -> Promise.ConcurrentPromise[R]:
		"""
		Calls the underlying function in a new threading.Thread
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		:return: A new ConcurrentPromise
		"""

		promise: Promise.ConcurrentPromise[R] = Promise.ConcurrentPromise()
		self.__thread__ = multiprocessing.Process(target=self.__wrapper__, args=(promise, self.__cb__, *args), kwargs=kwargs)
		self.__thread__.start()
		return promise

	def suspend(self) -> None:
		"""
		Suspends the function process execution
		"""

		psutil.Process(self.__thread__.pid).suspend()

	def resume(self) -> None:
		"""
		Resumes the function process execution
		"""

		psutil.Process(self.__thread__.pid).resume()

	def kill(self) -> None:
		"""
		Kills the function process
		"""

		self.__thread__.kill()

	def join(self, timeout: typing.Optional[float] = None) -> None:
		"""
		If alive, blocks this thread until function process is complete
		:param timeout: The time (in seconds) to block or None to block indefinitely
		"""

		if self.__thread__.is_alive():
			self.__thread__.join(timeout)

	@property
	def is_running(self) -> bool:
		"""
		:return: Whether the function process is still running
		"""

		return self.__thread__ is not None and self.__thread__.is_alive()


__all__: list[str] = ['ThreadedFunction', 'ConcurrentFunction']
