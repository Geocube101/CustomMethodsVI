from __future__ import annotations

import multiprocessing
import multiprocessing.connection
import os
import psutil
import signal
import sys
import threading
import time
import traceback
import typing

from . import Misc
from . import Exceptions
from . import Decorators


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
		self.__callbacks__: list[typing.Callable] = []

	def __await__(self):
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

	def then(self, callback: typing.Callable[[Promise[T]], None]) -> None:
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

	def __await__(self) -> typing.Iterator[None]:
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

	def then(self, callback: typing.Callable[[ConcurrentPromise[T]], None]) -> None:
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


class ThreadedFunction:
	"""
	Class handling function spawned on a separate threading.Thread
	"""

	def __init__(self, function: typing.Callable):
		"""
		Class handling function spawned on a separate threading.Thread
		- Constructor -
		:param function: A callable object
		:raises InvalidArgumentException: If 'function' is not callable
		"""

		Misc.raise_ifn(callable(function), Exceptions.InvalidArgumentException(ThreadedFunction.__init__, 'function', type(function)))
		self.__cb__: typing.Callable = function
		self.__thread__: typing.Optional[threading.Thread] = None

	def __wrapper__(self, promise: ThreadedPromise, *args: tuple, **kwargs: dict) -> None:
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

	def __call__(self, *args, **kwargs) -> ThreadedPromise:
		"""
		Calls the underlying function in a new threading.Thread
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		:return: A new ThreadedPromise
		"""

		promise = ThreadedPromise()
		self.__thread__ = threading.Thread(target=self.__wrapper__, args=(promise, *args), kwargs=kwargs)
		self.__thread__.start()
		return promise


class ConcurrentFunction:
	"""
	Class handling function spawned on a separate multiprocessing.Process
	"""

	def __init__(self, function: typing.Callable):
		"""
		Class handling function spawned on a separate multiprocessing.Process
		- Constructor -
		:param function: A callable object
		:raises InvalidArgumentException: If 'function' is not callable
		"""

		Misc.raise_ifn(callable(function), Exceptions.InvalidArgumentException(ThreadedFunction.__init__, 'function', type(function)))
		self.__cb__: typing.Callable = function
		self.__thread__: typing.Optional[multiprocessing.Process] = None

	@staticmethod
	def __wrapper__(promise: ConcurrentPromise, func: typing.Callable, *args: tuple, **kwargs: dict) -> None:
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

	def __call__(self, *args, **kwargs) -> ConcurrentPromise:
		"""
		Calls the underlying function in a new threading.Thread
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		:return: A new ConcurrentPromise
		"""

		promise = ConcurrentPromise()
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

	def is_running(self) -> bool:
		"""
		:return: Whether the function process is still running
		"""

		return self.__thread__ is not None and self.__thread__.is_alive()


class ThreadPool:
	"""
	Class for managing a pool of worker multiprocessing.Process processes
	"""

	@Decorators.Overload
	def __init__(self, function: typing.Callable, workers: int, *, synchronous_start: bool = True, daemon: bool = False):
		"""
		Class for managing a pool of worker multiprocessing.Process processes
		- Constructor -
		:param function: The function to pool
		:param workers: The number of workers
		:param synchronous_start: Whether to suspend all processes until creation is complete
		:param daemon: Whether to spawn processes as daemon
		:raises InvalidArgumentException: If 'function' is not callable
		:raises ValueError: If 'workers' is not an integer > 0
		"""

		Misc.raise_ifn(callable(function), Exceptions.InvalidArgumentException(ThreadPool.__init__, 'function', type(function)))
		Misc.raise_ifn(isinstance(workers, int) and (workers := int(workers)) > 0, ValueError('Number of workers must be a positive integer > 0'))

		self.__processes__: list[multiprocessing.Process] = []
		self.__function__: typing.Callable = function
		self.__workers__: int = int(workers)
		self.__synchronous_start__: bool = bool(synchronous_start)
		self.__daemon__: bool = bool(daemon)

	def __call__(self, *args, **kwargs) -> None:
		"""
		Starts the pool
		:param args: Positional arguments to call the function with
		:param kwargs: Keyword arguments to call the function with
		:raises ChildProcessError: If the pool is still running
		"""

		if any(x.is_alive() for x in self.__processes__):
			raise ChildProcessError('Thread pool already active')

		for _ in range(self.__workers__):
			process: multiprocessing.Process = multiprocessing.Process(target=self.__function__, args=args, kwargs=kwargs, daemon=self.__daemon__)
			process.start()

			if self.__synchronous_start__:
				psutil.Process(process.pid).suspend()

			self.__processes__.append(process)

		if self.__synchronous_start__:
			for worker in self.__processes__:
				psutil.Process(worker.pid).resume()

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

	def active_count(self) -> int:
		"""
		:return: The number of workers currently running
		"""

		count: int = 0

		for worker in self.__processes__:
			count += int(worker.is_alive())

		return count

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


class Thread:
	"""
	Class handling a single multiprocessing.Process each on specific cores
	"""

	def __init__(self, function: typing.Callable, cores: typing.Iterable[int], *args, **kwargs):
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
		self.__callback__: typing.Callable = function
		self.__args__: tuple[typing.Any, ...] = args
		self.__kwargs__: dict[str, typing.Any] = kwargs
		self.__proc__: typing.Optional[multiprocessing.Process] = None
		Misc.raise_ifn(all(isinstance(x, int) and int(x) > 0 for x in self.__cores__), ValueError('One or more affinity cores is not a positive integer'))

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

	def is_alive(self) -> bool:
		"""
		:return: Whether the function process is alive
		"""

		return self.__proc__.is_alive()

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

	def __init__(self, function: typing.Callable, *args, **kwargs):
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

	def __init__(self, function: typing.Callable, *args, **kwargs):
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
