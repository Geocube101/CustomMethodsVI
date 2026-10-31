from __future__ import annotations

import collections.abc
import multiprocessing
import multiprocessing.connection
import multiprocessing.queues
import multiprocessing.reduction
import multiprocessing.resource_sharer
import multiprocessing.shared_memory
import psutil
import typing

from .. import Exceptions
from .. import Misc


class Thread:
	"""
	Class handling a single multiprocessing.Process each on specific cores
	"""

	def __init__(self, function: collections.abc.Callable, cores: collections.abc.Iterable[int], *args, **kwargs):
		"""
		Class handling a single multiprocessing.Process each on specific cores
		- Constructor -
		:param function: The function to call
		:param cores: The cores to run this process on
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		:raises InvalidArgumentException: If 'function' is not callable
		:raises InvalidArgumentException: If 'cores' is not iterable
		:raises ValueError: If any value in 'cores' is not a positive integer
		"""

		Misc.raise_ifn(callable(function), Exceptions.InvalidArgumentException(Thread.__init__, 'function', type(function)))
		Misc.raise_ifn(hasattr(cores, '__iter__'), Exceptions.InvalidArgumentException(Thread.__init__, 'cores', type(cores)))
		self.__cores__: tuple[int, ...] = tuple(cores)
		self.__callback__: collections.abc.Callable = function
		self.__args__: tuple[typing.Any, ...] = args
		self.__kwargs__: dict[str, typing.Any] = kwargs
		self.__proc__: typing.Optional[multiprocessing.Process] = None
		Misc.raise_ifn(all(isinstance(x, int) and int(x) > 0 for x in self.__cores__), ValueError('One or more affinity cores is not a positive integer'))

	def __await__(self) -> collections.abc.Iterator[None]:
		while self.__proc__.is_alive():
			yield

	def signal(self, sig: int) -> None:
		"""
		Sends a signal to the function process
		:param sig: The signal to send
		"""

		psutil.Process(self.__proc__.pid).send_signal(sig)

	def join(self, timeout: float = None) -> None:
		"""
		Blocks this thread until underlying process is complete
		:param timeout: The time (in seconds) to wait
		"""

		self.__proc__.join(timeout)

	def start(self, daemon: bool = True) -> int:
		"""
		Starts the underlying process and calls the function
		:param daemon: Whether to mark the process as a daemon
		:return: The underlying process ID
		"""

		self.__proc__ = multiprocessing.Process(target=self.__callback__, args=self.__args__, kwargs=self.__kwargs__, daemon=bool(daemon))
		self.__proc__.start()
		psutil.Process(self.__proc__.pid).cpu_affinity(list(self.__cores__))
		return self.__proc__.pid

	@property
	def is_alive(self) -> bool:
		"""
		:return: Whether the function process is alive
		"""

		return self.__proc__.is_alive()

	@property
	def core(self) -> tuple[int, ...]:
		"""
		:return: The current core this thread runs on
		"""

		return self.__cores__


class LogicalThread(Thread):
	"""
	Class handling a single multiprocessing.Process each on a single logical core
	Consecutive instances of this class will execute on the next core
	"""

	__next_core: int = 0

	def __init__(self, function: collections.abc.Callable, *args, **kwargs):
		"""
		Class handling a single multiprocessing.Process each on a single logical core
		Consecutive instances of this class will execute on the next core
		- Constructor -
		:param function: The function to call
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		:raises InvalidArgumentException: If 'function' is not callable
		:raises InvalidArgumentException: If 'cores' is not iterable
		:raises ValueError: If any value in 'cores' is not a positive integer
		"""

		super().__init__(function, (LogicalThread.__next_core,), *args, **kwargs)
		LogicalThread.__next_core = (LogicalThread.__next_core + 1) % psutil.cpu_count(True)


class PhysicalThread(Thread):
	"""
	Class handling a single multiprocessing.Process each on a single physical core
	Consecutive instances of this class will execute on the next core
	"""

	__next_core: int = 0

	def __init__(self, function: collections.abc.Callable, *args, **kwargs):
		"""
		Class handling a single multiprocessing.Process each on a single physical core
		Consecutive instances of this class will execute on the next core
		- Constructor -
		:param function: The function to call
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		:raises InvalidArgumentException: If 'function' is not callable
		:raises InvalidArgumentException: If 'cores' is not iterable
		:raises ValueError: If any value in 'cores' is not a positive integer
		"""

		super().__init__(function, (PhysicalThread.__next_core,), *args, **kwargs)
		PhysicalThread.__next_core = (PhysicalThread.__next_core + 1) % psutil.cpu_count(False)


__all__: list[str] = ['Thread', 'LogicalThread', 'PhysicalThread']
