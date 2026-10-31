from __future__ import annotations

import collections.abc
import multiprocessing
import multiprocessing.connection
import multiprocessing.queues
import multiprocessing.reduction
import multiprocessing.resource_sharer
import multiprocessing.shared_memory
import os
import psutil
import signal
import threading
import time
import typing

from .. import Exceptions
from .. import Misc


class ThreadPool:
	"""
	Class for managing a pool of worker threading.Thread threads
	"""

	@staticmethod
	def __wrapper__(function: collections.abc.Callable, sync_event: typing.Optional[threading.Event], err_flag: threading.Event, args: tuple[typing.Any, ...], kwargs: dict[str, typing.Any]) -> None:
		while sync_event is not None and not sync_event.is_set():
			time.sleep(1e-6)

		err_flag.clear()

		try:
			function(*args, **kwargs)
		except (Exception, KeyboardInterrupt, SystemExit):
			err_flag.set()

	def __init__(self, function: collections.abc.Callable, workers: int, *, synchronous_start: bool = True, daemon: bool = False, supply_index: bool = False):
		"""
		Class for managing a pool of worker threading.Thread threads
		- Constructor -
		:param function: The function to pool
		:param workers: The number of workers
		:param synchronous_start: Whether to block all threads until creation is complete
		:param daemon: Whether to spawn processes as daemon
		:param supply_index: If true, the first argument is the worker's index within the pool
		:raises InvalidArgumentException: If 'function' is not callable
		:raises ValueError: If 'workers' is not an integer > 0
		"""

		Misc.raise_ifn(callable(function), Exceptions.InvalidArgumentException(ThreadPool.__init__, 'function', type(function)))
		Misc.raise_ifn(isinstance(workers, int) and (workers := int(workers)) > 0, ValueError('Number of workers must be a positive integer > 0'))

		self.__processes__: list[tuple[threading.Thread, threading.Event]] = []
		self.__function__: collections.abc.Callable = function
		self.__workers__: int = int(workers)
		self.__synchronous_start__: bool = bool(synchronous_start)
		self.__daemon__: bool = bool(daemon)
		self.__supply_index: bool = bool(supply_index)

	def __call__(self, *args, **kwargs) -> ThreadPool:
		"""
		Starts the pool
		:param args: Positional arguments to call the function with
		:param kwargs: Keyword arguments to call the function with
		:raises ChildProcessError: If the pool is still running
		:return: This pool
		"""

		if any(x[0].is_alive() for x in self.__processes__):
			raise ChildProcessError('Thread pool already active')

		event: threading.Event = threading.Event()
		event.clear()

		for i in range(self.__workers__):
			err_flag: threading.Event = threading.Event()
			pargs: tuple = (i, *args) if self.__supply_index else args
			process: threading.Thread = threading.Thread(target=ThreadPool.__wrapper__, args=(self.__function__, event if self.__synchronous_start__ else None, err_flag, pargs, kwargs), daemon=self.__daemon__)
			process.start()
			self.__processes__.append((process, err_flag))

		if self.__synchronous_start__:
			event.set()

		return self

	def __await__(self) -> collections.abc.Iterator[None]:
		while any(p[0].is_alive() for p in self.__processes__):
			yield

	def wait(self, timeout: float = None) -> None:
		"""
		Blocks the current thread until all workers are complete
		Waits at most 'timeout' seconds or infinitely if 'timeout' is None
		:param timeout: The number of seconds to wait or indefinitely if timeout is None
		"""

		t1 = time.perf_counter_ns()

		while (timeout is None or (time.perf_counter_ns() - t1) * 1e-9 < timeout) and any(p[0].is_alive() for p in self.__processes__):
			time.sleep(1e-7)

	def restart_closed(self, *args, **kwargs) -> int:
		"""
		Restarts all workers not currently running
		:param args: Positional arguments to call the function with
		:param kwargs: Keyword arguments to call the function with
		:return: The number of restarted threads
		"""

		count: int = 0

		for i, (worker, err_flag) in enumerate(self.__processes__):
			if not worker.is_alive():
				process: threading.Thread = threading.Thread(target=ThreadPool.__wrapper__, args=(self.__function__, None, err_flag, args, kwargs), daemon=self.__daemon__)
				process.start()
				self.__processes__[i] = (process, err_flag)
				count += 1

		return count

	def restart_failed(self, *args, **kwargs) -> int:
		"""
		Restarts all workers whose exit code is greater than 0; restarting all workers that failed without keyboard interrupt
		:param args: Positional arguments to call the function with
		:param kwargs: Keyword arguments to call the function with
		:return: The number of restarted threads
		"""

		count: int = 0

		for i, (worker, err_flag) in enumerate(self.__processes__):
			if not worker.is_alive() and err_flag.is_set():
				process: threading.Thread = threading.Thread(target=ThreadPool.__wrapper__, args=(self.__function__, None, err_flag, args, kwargs), daemon=self.__daemon__)
				process.start()
				self.__processes__[i] = (process, err_flag)
				count += 1

		return count

	def is_any_alive(self) -> bool:
		"""
		:return: Whether any workers are running
		"""

		return any(x[0].is_alive() for x in self.__processes__)

	@property
	def active_count(self) -> int:
		"""
		:return: The number of workers currently running
		"""

		return len([worker for worker in self.__processes__ if worker[0].is_alive()])

	@property
	def tids(self) -> tuple[int, ...]:
		"""
		:return: The respective native thread IDs for all worker threads
		"""

		return tuple(x[0].native_id for x in self.__processes__)


class ProcessPool:
	"""
	Class for managing a pool of worker multiprocessing.Process processes
	"""

	def __init__(self, function: collections.abc.Callable, workers: int, *, synchronous_start: bool = True, daemon: bool = False, supply_index: bool = False):
		"""
		Class for managing a pool of worker multiprocessing.Process processes
		- Constructor -
		:param function: The function to pool
		:param workers: The number of workers
		:param synchronous_start: Whether to suspend all processes until creation is complete
		:param daemon: Whether to spawn processes as daemon
		:param supply_index: If true, the first argument is the worker's index within the pool
		:raises InvalidArgumentException: If 'function' is not callable
		:raises ValueError: If 'workers' is not an integer > 0
		"""

		Misc.raise_ifn(callable(function), Exceptions.InvalidArgumentException(ThreadPool.__init__, 'function', type(function)))
		Misc.raise_ifn(isinstance(workers, int) and (workers := int(workers)) > 0, ValueError('Number of workers must be a positive integer > 0'))

		self.__processes__: list[multiprocessing.Process] = []
		self.__function__: collections.abc.Callable = function
		self.__workers__: int = int(workers)
		self.__synchronous_start__: bool = bool(synchronous_start)
		self.__daemon__: bool = bool(daemon)
		self.__supply_index: bool = bool(supply_index)

	def __call__(self, *args, **kwargs) -> ProcessPool:
		"""
		Starts the pool
		:param args: Positional arguments to call the function with
		:param kwargs: Keyword arguments to call the function with
		:raises ChildProcessError: If the pool is still running
		:return: This pool
		"""

		if any(x.is_alive() for x in self.__processes__):
			raise ChildProcessError('Process pool already active')

		for i in range(self.__workers__):
			pargs: tuple = (i, *args) if self.__supply_index else args
			process: multiprocessing.Process = multiprocessing.Process(target=self.__function__, args=pargs, kwargs=kwargs, daemon=self.__daemon__)
			process.start()

			if self.__synchronous_start__:
				psutil.Process(process.pid).suspend()

			self.__processes__.append(process)

		if self.__synchronous_start__:
			for worker in self.__processes__:
				psutil.Process(worker.pid).resume()

		return self

	def __await__(self) -> collections.abc.Iterator[None]:
		while any(p.is_alive() for p in self.__processes__):
			yield

	def wait(self, timeout: float = None) -> None:
		"""
		Blocks the current thread until all workers are complete
		Waits at most 'timeout' seconds or infinitely if 'timeout' is None
		:param timeout: The number of seconds to wait or indefinitely if timeout is None
		"""

		t1 = time.perf_counter_ns()

		while (timeout is None or (time.perf_counter_ns() - t1) * 1e-9 < timeout) and any(p.is_alive() for p in self.__processes__):
			time.sleep(1e-7)

	def kill(self) -> None:
		"""
		Kills all active workers in the pool
		"""

		for worker in self.__processes__:
			if worker.is_alive():
				worker.kill()

	def terminate(self) -> None:
		"""
		Terminates all active workers in the pool
		"""

		for worker in self.__processes__:
			if worker.is_alive():
				worker.terminate()

	def signal(self, sig: int) -> None:
		"""
		Sends an OS signal to all active workers
		:param sig: The signal to send
		"""

		for worker in self.__processes__:
			if worker.is_alive():
				os.kill(worker.pid, sig)

	def restart_closed(self, *args, **kwargs) -> int:
		"""
		Restarts all workers not currently running
		:param args: Positional arguments to call the function with
		:param kwargs: Keyword arguments to call the function with
		:return: The number of restarted processes
		"""

		count: int = 0

		for i, worker in enumerate(self.__processes__):
			if not worker.is_alive():
				process: multiprocessing.Process = multiprocessing.Process(target=self.__function__, args=args, kwargs=kwargs, daemon=self.__daemon__)
				process.start()
				worker.close()
				self.__processes__[i] = process
				count += 1

		return count

	def restart_failed(self, *args, **kwargs) -> int:
		"""
		Restarts all workers whose exit code is greater than 0; restarting all workers that failed without keyboard interrupt
		:param args: Positional arguments to call the function with
		:param kwargs: Keyword arguments to call the function with
		:return: The number of restarted processes
		"""

		count: int = 0

		for i, worker in enumerate(self.__processes__):
			if worker.exitcode is not None and worker.exitcode > 0:
				process: multiprocessing.Process = multiprocessing.Process(target=self.__function__, args=args, kwargs=kwargs, daemon=self.__daemon__)
				process.start()
				worker.close()
				self.__processes__[i] = process
				count += 1

		return count

	def restart_all(self, *args, __sigint_time: float = 3, **kwargs) -> int:
		"""
		Restarts all workers
		:param __sigint_time: The time (in seconds) to wait between SIGINT call and SIGKILL
		:param args: Positional arguments to call the function with
		:param kwargs: Keyword arguments to call the function with
		:return: The number of restarted processes
		"""

		count: int = 0

		for i, worker in enumerate(self.__processes__):
			if worker.is_alive():
				os.kill(worker.pid, signal.SIGINT)
				worker.join(__sigint_time)

				if worker.is_alive():
					worker.kill()

				worker.close()

			process: multiprocessing.Process = multiprocessing.Process(target=self.__function__, args=args, kwargs=kwargs, daemon=self.__daemon__)
			process.start()
			self.__processes__[i] = process
			count += 1

		return count

	def is_any_alive(self) -> bool:
		"""
		:return: Whether any workers are running
		"""

		return any(x.is_alive() for x in self.__processes__)

	@property
	def active_count(self) -> int:
		"""
		:return: The number of workers currently running
		"""

		return len([worker for worker in self.__processes__ if worker.is_alive()])

	@property
	def pids(self) -> tuple[int, ...]:
		"""
		:return: The respective pids for all worker processes
		"""

		return tuple(x.pid for x in self.__processes__)

	@property
	def exit_codes(self) -> tuple[int | None, ...]:
		"""
		Gets the respective exit codes for all worker processes
		Workers still running will have an exit code: 'None'
		:return: Worker exit codes
		"""

		return tuple(x.exitcode for x in self.__processes__)


__all__: list[str] = ['ThreadPool', 'ProcessPool']
