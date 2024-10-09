from __future__ import annotations

import os
import signal
import sys
import threading
import multiprocessing
import multiprocessing.connection
import time
import traceback
import psutil
import typing

import CustomMethodsVI.Misc
import CustomMethodsVI.Exceptions
import CustomMethodsVI.Decorators
import CustomMethodsVI.Synchronization


PROMISE_T = typing.TypeVar('PROMISE_T', bound='Promise')
CONCURRENT_PROMISE_T = typing.TypeVar('CONCURRENT_PROMISE_T', bound='ConcurrentPromise')


class Promise:
	"""
	[Promise] - Standard promise class
	"""

	def __init__(self):
		"""
		[Promise] - Standard promise class
		- Constructor -
		"""

		self.__response__: tuple[bool, typing.Any] | None = None
		self.__callbacks__: list[typing.Callable, ...] = []

	def fulfilled(self) -> bool:
		"""
		Checks whether this promise is fulfilled
		:return: (bool) Fulfilledness
		"""

		return self.__response__ is not None

	def throw(self, err: BaseException) -> None:
		"""
		Resolves this promise with an error
		Any attempt to poll this promise on consumer side will raise that error
		:param err: (extends BaseException) The error to resolve with
		:return: (None)
		:raises IOError: If promise is already fulfilled
		"""

		if self.__response__ is not None:
			raise IOError('Response already sent')
		else:
			CustomMethodsVI.Misc.raise_ifn(isinstance(err, BaseException), CustomMethodsVI.Exceptions.InvalidArgumentException(Promise.throw, 'err', type(err)))
			self.__response__ = (False, err)

			for i, cb in enumerate(self.__callbacks__):
				try:
					cb(self)
				except Exception as e:
					sys.stderr.write(f'Error-{type(e).__name__} during Promise callback[{i}]:\n\t...\n{"".join(traceback.format_exception(e))}')
					sys.stderr.flush()

	def resolve(self, obj: typing.Any) -> None:
		"""
		Resolves this promise with a value
		Any attempt to poll this promise on consumer side will return that value
		:param obj: (ANY) The response to resolve with
		:return: (None)
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

	def wait(self, throw_err: bool = True) -> typing.Any:
		"""
		Blocks current thread until this promise is fulfilled
		Will raise an error if producer resolved with "throw"
		:return: (ANY) The response value
		"""

		while self.__response__ is None:
			time.sleep(1e-6)

		return self.response(throw_err)

	def then(self, callback: typing.Callable[[PROMISE_T], None]) -> None:
		"""
		Binds a callback to execute once this promise is fulfilled
		Callback should be a callable accepting this promise as the first argument
		:param callback: (CALLABLE) The callback to bind
		:return: (None)
		:raises AssertionError: If promise already fulfilled
		"""

		assert self.__response__ is None, 'Response already handled'
		CustomMethodsVI.Misc.raise_ifn(callable(callback), CustomMethodsVI.Exceptions.InvalidArgumentException(Promise.then, 'callback', type(callback)))
		self.__callbacks__.append(callback)

	def response(self, throw_err: bool = True) -> typing.Any:
		"""
		Polls this promise for a response
		:param throw_err: If true, throws the associated error (if producer used "throw") otherwise, the error is returned
		:return: (ANY) The response value or the associated error
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
		Returns None if promise is not fulfilled
		:return: (bool or None) Erredness
		"""

		if self.__response__ is not None:
			state, _ = self.__response__
			return not state
		else:
			return None


class ConcurrentPromise(Promise):
	"""
	[ConcurrentPromise(Promise)] - Class handling single IPC event from ConcurrentFunction
	"""

	def __init__(self):
		"""
		[ConcurrentPromise(Promise)] - Class handling single IPC event from ConcurrentFunction
		- Constructor -
		"""

		super().__init__()
		self.__pipes__: tuple[multiprocessing.connection.Connection, ...] = multiprocessing.Pipe(False)
		self.__src__: int = os.getpid()
		self.__poll_thread__: threading.Thread | None = None

	def __poll_loop(self) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Started on a new thread to poll internal pipes for response
		:return: (None)
		"""

		self.wait()

		for i, cb in enumerate(self.__callbacks__):
			try:
				cb(self)
			except Exception as e:
				sys.stderr.write(f'Error-{type(e).__name__} during Promise callback[{i}]:\n\t...\n{"".join(traceback.format_exception(e))}')
				sys.stderr.flush()

	def fulfilled(self) -> bool:
		"""
		Checks whether this promise is fulfilled
		:return: (bool) Fulfilledness
		"""

		return self.__response__ is not None or self.__pipes__[0].poll()

	def throw(self, err: BaseException) -> None:
		"""
		Resolves this promise with an error
		Any attempt to poll this promise on consumer side will raise that error
		:param err: (extends BaseException) The error to resolve with
		:return: (None)
		:raises IOError: If promise is already fulfilled or this process is consumer
		"""

		if os.getpid() == self.__src__:
			raise IOError('Cannot send reply as consumer')
		elif self.__pipes__[1].closed:
			raise IOError('Response already sent')
		else:
			CustomMethodsVI.Misc.raise_ifn(isinstance(err, BaseException), CustomMethodsVI.Exceptions.InvalidArgumentException(ConcurrentPromise.throw, 'err', type(err)))
			self.__pipes__[1].send((False, err))
			self.__pipes__[1].close()

	def resolve(self, obj: typing.Any) -> None:
		"""
		Resolves this promise with a value
		Any attempt to poll this promise on consumer side will return that value
		:param obj: (ANY) The response to resolve with
		:return: (None)
		:raises IOError: If promise is already fulfilled or this process is consumer
		"""

		if os.getpid() == self.__src__:
			raise IOError('Cannot send reply as consumer')
		elif self.__pipes__[1].closed:
			raise IOError('Response already sent')
		else:
			self.__pipes__[1].send((True, obj))
			self.__pipes__[1].close()

	def wait(self, throw_err: bool = True) -> typing.Any:
		"""
		Blocks current thread until this promise is fulfilled
		Will raise an error if producer resolved with "throw"
		:return: (ANY) The response value
		:raises IOError: If this process is producer
		"""

		if os.getpid() == self.__src__:
			while not self.__pipes__[0].poll():
				time.sleep(1e-6)

			return self.response(throw_err)
		else:
			raise IOError('Cannot poll reply as producer')

	def then(self, callback: typing.Callable[[CONCURRENT_PROMISE_T], None]) -> None:
		"""
		Binds a callback to execute once this promise is fulfilled
		Callback should be a callable accepting this promise as the first argument
		:param callback: (CALLABLE) The callback to bind
		:return: (None)
		:raises AssertionError: If promise already fulfilled
		"""

		assert self.__response__ is None, 'Response already handled'
		CustomMethodsVI.Misc.raise_ifn(callable(callback), CustomMethodsVI.Exceptions.InvalidArgumentException(ConcurrentPromise.then, 'callback', type(callback)))

		if self.__poll_thread__ is None:
			self.__poll_thread__ = threading.Thread(target=self.__poll_loop)
			self.__poll_thread__.start()

		self.__callbacks__.append(callback)

	def response(self, throw_err: bool = True) -> typing.Any:
		"""
		Polls this promise for a response
		:param throw_err: If true, throws the associated error (if producer used "throw") otherwise, the error is returned
		:return: (ANY) The response value or the associated error
		:raises IOError: If promise is not fulfilled or this process is producer
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
		"""
		Checks if this promise was resolved with "throw"
		Returns None if promise is not fulfilled
		:return: (bool or None) Erredness
		"""

		if self.__response__ is not None:
			state, _ = self.__response__
			return not state
		elif self.__pipes__[0].poll():
			state, msg = self.__pipes__[0].recv()
			self.__response__ = (state, msg)
			return not state
		else:
			return None


class ThreadedPromise(Promise):
	"""
	[ThreadedPromise(Promise)] - Class handling single ITC event from ThreadedFunction
	"""

	def __init__(self):
		"""
		[ThreadedPromise(Promise)] - Class handling single ITC event from ThreadedFunction
		- Constructor -
		"""

		super().__init__()
		self.__response__: tuple[bool, typing.Any] | None = None
		self.__src__: int = threading.current_thread().native_id

	def fulfilled(self) -> bool:
		"""
		Checks whether this promise is fulfilled
		:return: (bool) Fulfilledness
		"""

		return self.__response__ is not None

	def throw(self, err: BaseException) -> None:
		"""
		Resolves this promise with an error
		Any attempt to poll this promise on consumer side will raise that error
		:param err: (extends BaseException) The error to resolve with
		:return: (None)
		:raises IOError: If promise is already fulfilled or this process is consumer
		"""

		if threading.current_thread().native_id == self.__src__:
			raise IOError('Cannot send reply as consumer')
		elif self.__response__ is not None:
			raise IOError('Response already sent')
		else:
			CustomMethodsVI.Misc.raise_ifn(isinstance(err, BaseException), CustomMethodsVI.Exceptions.InvalidArgumentException(ThreadedPromise.throw, 'err', type(err)))
			self.__response__ = (False, err)

			for i, cb in enumerate(self.__callbacks__):
				try:
					cb(self)
				except Exception as e:
					sys.stderr.write(f'Error-{type(e).__name__} during Promise callback[{i}]:\n\t...\n{"".join(traceback.format_exception(e))}')
					sys.stderr.flush()

	def resolve(self, obj: typing.Any) -> None:
		"""
		Resolves this promise with a value
		Any attempt to poll this promise on consumer side will return that value
		:param obj: (ANY) The response to resolve with
		:return: (None)
		:raises IOError: If promise is already fulfilled or this process is consumer
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

	def wait(self, throw_err: bool = True) -> typing.Any:
		"""
		Blocks current thread until this promise is fulfilled
		Will raise an error if producer resolved with "throw"
		:return: (ANY) The response value
		:raises IOError: If this process is producer
		"""

		if threading.current_thread().native_id == self.__src__ or self.fulfilled():
			while not self.fulfilled():
				time.sleep(1e-6)

			return self.response(throw_err)
		else:
			raise IOError('Cannot poll reply as producer')

	def response(self, throw_err: bool = True) -> typing.Any:
		"""
		Polls this promise for a response
		:param throw_err: If true, throws the associated error (if producer used "throw") otherwise, the error is returned
		:return: (ANY) The response value or the associated error
		:raises IOError: If promise is not fulfilled or this process is producer
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


try:
	import win32file
	import win32con
	import win32security
	import win32pipe
	import pickle

	class NamedPipePromise(Promise):
		def __init__(self):
			super().__init__()
			pipe_security: win32security.SECURITY_ATTRIBUTES = win32security.SECURITY_ATTRIBUTES()
			pipe_security.SECURITY_DESCRIPTOR = None
			pipe_security.bInheritHandle = True
			pipe_name: str = f'\\\\.\\pipe\\{hex(id(self))}::01'
			self.__conn__ = win32pipe.CreateNamedPipe(pipe_name, win32con.PIPE_ACCESS_DUPLEX | win32con.FILE_FLAG_OVERLAPPED, win32con.PIPE_TYPE_BYTE, 2, 1024, 1024, 1000, pipe_security)
			self.__src__: int = os.getpid()
			self.__poll_thread__: threading.Thread | None = None

		def __poll_loop(self) -> None:
			"""
			INTERNAL METHOD; DO NOT USE
			Started on a new thread to poll internal pipes for response
			:return: (None)
			"""

			self.wait()

			for i, cb in enumerate(self.__callbacks__):
				try:
					cb(self)
				except Exception as e:
					sys.stderr.write(f'Error-{type(e).__name__} during Promise callback[{i}]:\n\t...\n')
					sys.stderr.flush()
					traceback.print_tb(e.__traceback__)

		def fulfilled(self) -> bool:
			"""
			Checks whether this promise is fulfilled
			:return: (bool) Fulfilledness
			"""

			return self.__response__ is not None or win32pipe.PeekNamedPipe(self.__conn__, 1024)[1] > 0

		def throw(self, err: BaseException) -> None:
			"""
			Resolves this promise with an error
			Any attempt to poll this promise on consumer side will raise that error
			:param err: (extends BaseException) The error to resolve with
			:return: (None)
			:raises IOError: If promise is already fulfilled or this process is consumer
			"""

			if os.getpid() == self.__src__:
				raise IOError('Cannot send reply as consumer')
			elif self.__pipes__[1].closed:
				raise IOError('Response already sent')
			else:
				CustomMethodsVI.Misc.raise_ifn(isinstance(err, BaseException), CustomMethodsVI.Exceptions.InvalidArgumentException(ConcurrentPromise.throw, 'err', type(err)))
				self.__pipes__[1].send((False, err))
				self.__pipes__[1].close()

		def resolve(self, obj: typing.Any) -> None:
			"""
			Resolves this promise with a value
			Any attempt to poll this promise on consumer side will return that value
			:param obj: (ANY) The response to resolve with
			:return: (None)
			:raises IOError: If promise is already fulfilled or this process is consumer
			"""

			if os.getpid() == self.__src__:
				raise IOError('Cannot send reply as consumer')
			elif self.__pipes__[1].closed:
				raise IOError('Response already sent')
			else:
				self.__pipes__[1].send((True, obj))
				self.__pipes__[1].close()

		def wait(self) -> typing.Any:
			"""
			Blocks current thread until this promise is fulfilled
			Will raise an error if producer resolved with "throw"
			:return: (ANY) The response value
			:raises IOError: If this process is producer
			"""

			if os.getpid() == self.__src__:
				while not self.__pipes__[0].poll():
					time.sleep(1e-6)

				return self.response()
			else:
				raise IOError('Cannot poll reply as producer')

		def then(self, callback: typing.Callable) -> None:
			"""
			Binds a callback to execute once this promise is fulfilled
			Callback should be a callable accepting this promise as the first argument
			:param callback: (CALLABLE) The callback to bind
			:return: (None)
			:raises AssertionError: If promise already fulfilled
			"""

			assert self.__response__ is None, 'Response already handled'
			CustomMethodsVI.Misc.raise_ifn(callable(callback), CustomMethodsVI.Exceptions.InvalidArgumentException(ConcurrentPromise.then, 'callback', type(callback)))

			if self.__poll_thread__ is None:
				self.__poll_thread__ = threading.Thread(target=self.__poll_loop)
				self.__poll_thread__.start()

			self.__callbacks__.append(callback)

		def response(self, throw_err: bool = True) -> typing.Any:
			"""
			Polls this promise for a response
			:param throw_err: If true, throws the associated error (if producer used "throw") otherwise, the error is returned
			:return: (ANY) The response value or the associated error
			:raises IOError: If promise is not fulfilled or this process is producer
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
			"""
			Checks if this promise was resolved with "throw"
			Returns None if promise is not fulfilled
			:return: (bool or None) Erredness
			"""

			if self.__response__ is not None:
				state, _ = self.__response__
				return not state
			elif self.__pipes__[0].poll():
				state, msg = self.__pipes__[0].recv()
				self.__response__ = (state, msg)
				return not state
			else:
				return None

except ImportError:
	pass


class ThreadedFunction:
	"""
	[ThreadedFunction] - Class handling function spawned on separate threading.Thread
	"""

	def __init__(self, function: typing.Callable):
		"""
		[ThreadedFunction] - Class handling function spawned on separate threading.Thread
		- Constructor -
		:param function: (CALLABLE) A callable object
		"""

		CustomMethodsVI.Misc.raise_ifn(callable(function), CustomMethodsVI.Exceptions.InvalidArgumentException(ThreadedFunction.__init__, 'function', type(function)))
		self.__cb__ = function
		self.__thread__: None | threading.Thread = None

	def __wrapper__(self, promise: ThreadedPromise, *args: tuple, **kwargs: dict) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Calls the function, handling all errors, and responds to promise accordingly
		:param promise: The promise to respond to
		:param args: The function's positional arguments
		:param kwargs: The function's keyword arguments
		:return: (None)
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
	[ConcurrentFunction] - Class handling function spawned on separate multiprocessing.Process
	"""

	def __init__(self, function: typing.Callable):
		"""
		[ConcurrentFunction] - Class handling function spawned on separate multiprocessing.Process
		- Constructor -
		:param function: (CALLABLE) A callable object
		"""

		CustomMethodsVI.Misc.raise_ifn(callable(function), CustomMethodsVI.Exceptions.InvalidArgumentException(ThreadedFunction.__init__, 'function', type(function)))
		self.__cb__ = function
		self.__thread__ = None  # type: None | multiprocessing.Process

	@staticmethod
	def __wrapper__(promise: ConcurrentPromise, func: typing.Callable, *args: tuple, **kwargs: dict) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Calls the function, handling all errors, and responds to promise accordingly
		:param promise: The promise to respond to
		:param func: The callable to call
		:param args: The function's positional arguments
		:param kwargs: The function's keyword arguments
		:return: (None)
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
		:return: (None)
		"""

		psutil.Process(self.__thread__.pid).suspend()

	def resume(self) -> None:
		"""
		Resumes the function process execution
		:return: (None)
		"""

		psutil.Process(self.__thread__.pid).resume()

	def kill(self) -> None:
		"""
		Kills the function process
		:return: (None)
		"""

		self.__thread__.kill()

	def join(self, timeout: float = None) -> None:
		"""
		If alive, blocks this thread until function process is complete
		:param timeout: (float) The time (in seconds) to block
		:return: (None)
		"""

		if self.__thread__.is_alive():
			self.__thread__.join(timeout)

	def is_running(self) -> bool:
		"""
		Returns whether the function process is still running
		:return: Aliveness
		"""

		return self.__thread__ is not None and self.__thread__.is_alive()


class ThreadPool:
	"""
	[ThreadPool] - Class for managing a pool of worker multiprocessing.Process processes
	"""

	@CustomMethodsVI.Decorators.Overload
	def __init__(self, function: typing.Callable, workers: int, *, synchronous_start: bool = True, daemon: bool = False):
		"""
		[ThreadPool] - Class for managing a pool of worker multiprocessing.Process processes
		- Constructor -
		:param function: (CALLABLE) The function to pool
		:param workers: (int) The number of workers
		:param synchronous_start: (bool) Whether to suspend all processes until creation is complete
		:param daemon: (bool) Whether to spawn processes as daemon
		"""

		self.__processes: list[multiprocessing.Process] = []
		self.__function: typing.Callable = function
		self.__workers: int = int(workers)
		self.__synchronous_start: bool = bool(synchronous_start)
		self.__daemon: bool = bool(daemon)

	def __call__(self, *args, **kwargs) -> None:
		"""
		Starts the pool
		:param args: (*ANY) Positional arguments to call the function with
		:param kwargs: (**ANY) Keyword arguments to call the function with
		:return: (None)
		:raises ChildProcessError: If the pool is still running
		"""

		if any(x.is_alive() for x in self.__processes):
			raise ChildProcessError('Thread pool already active')

		for _ in range(self.__workers):
			process: multiprocessing.Process = multiprocessing.Process(target=self.__function, args=args, kwargs=kwargs, daemon=self.__daemon)
			process.start()

			if self.__synchronous_start:
				psutil.Process(process.pid).suspend()

			self.__processes.append(process)

		if self.__synchronous_start:
			for worker in self.__processes:
				psutil.Process(worker.pid).resume()

	def wait(self, timeout: float = None) -> None:
		"""
		Blocks the current thread until all workers are complete
		Waits at most 'timeout' seconds or infinitely if 'timeout' is None
		:param timeout:
		:return:
		"""

		t1 = time.perf_counter_ns()

		while (timeout is None or (time.perf_counter_ns() - t1) * 1e-9 < timeout) and any(p.is_alive() for p in self.__processes):
			time.sleep(1e-7)

	def kill(self) -> None:
		"""
		Kills all active workers in the pool
		:return:
		"""

		for worker in self.__processes:
			if worker.is_alive():
				worker.kill()

	def terminate(self) -> None:
		"""
		Terminates all active workers in the pool
		:return:
		"""

		for worker in self.__processes:
			if worker.is_alive():
				worker.terminate()

	def signal(self, signal: int) -> None:
		"""
		Sends an OS signal to all active workers
		:param signal: (int) The signal to send
		:return: (None)
		"""

		for worker in self.__processes:
			if worker.is_alive():
				os.kill(worker.pid, signal)

	def restart_closed(self, *args, **kwargs) -> None:
		"""
		Restarts all workers not currently running
		:param args: (*ANY) Positional arguments to call the function with
		:param kwargs: (**ANY) Keyword arguments to call the function with
		:return: (None)
		"""

		for i, worker in enumerate(self.__processes):
			if not worker.is_alive():
				process: multiprocessing.Process = multiprocessing.Process(target=self.__function, args=args, kwargs=kwargs, daemon=self.__daemon)
				process.start()
				worker.close()
				self.__processes[i] = process

	def restart_failed(self, *args, **kwargs) -> None:
		"""
		Restarts all workers whose exit code is greater than 0; restarting all workers that failed without keyboard interrupt
		:param args: (*ANY) Positional arguments to call the function with
		:param kwargs: (**ANY) Keyword arguments to call the function with
		:return: (None)
		"""

		for i, worker in enumerate(self.__processes):
			if worker.exitcode is not None and worker.exitcode > 0:
				process: multiprocessing.Process = multiprocessing.Process(target=self.__function, args=args, kwargs=kwargs, daemon=self.__daemon)
				process.start()
				worker.close()
				self.__processes[i] = process

	def restart_all(self, *args, __sigint_time: float = 3, **kwargs) -> None:
		"""
		Restarts all workers
		:param __sigint_time: The time (in seconds) to wait between SIGINT call and SIGKILL
		:param args: (*ANY) Positional arguments to call the function with
		:param kwargs: (**ANY) Keyword arguments to call the function with
		:return: (None)
		"""

		for i, worker in enumerate(self.__processes):
			if worker.is_alive():
				os.kill(worker.pid, signal.SIGINT)
				worker.join(__sigint_time)

				if worker.is_alive():
					worker.kill()

				worker.close()

			process: multiprocessing.Process = multiprocessing.Process(target=self.__function, args=args, kwargs=kwargs, daemon=self.__daemon)
			process.start()
			self.__processes[i] = process

	def is_any_alive(self) -> bool:
		"""
		Checks if any workers are running
		:return: (bool) Aliveness
		"""

		return any(x.is_alive() for x in self.__processes)

	def active_count(self) -> int:
		"""
		Gets the number of workers currently running
		:return: (int) Runningness
		"""

		count: int = 0

		for worker in self.__processes:
			count += int(worker.is_alive())

		return count

	@property
	def pids(self) -> tuple[int, ...]:
		"""
		Gets the respective pids for all worker processes
		:return: (tuple[int]) PIDness
		"""

		return tuple(x.pid for x in self.__processes)

	@property
	def exit_codes(self) -> tuple[int | None, ...]:
		"""
		Gets the respective exit codes for all worker processes
		Workers still running will have an exit code: 'None'
		:return: (tuple[int]) Exitcodeness
		"""

		return tuple(x.exitcode for x in self.__processes)


class Thread:
	"""
	[Thread] - Class handling a single multiprocessing.Process each on a single core
	Consecutive instances of this class will execute on the next core
	"""

	__next_cpu = 0

	@classmethod
	def __get_next_cpu_core(cls) -> int:
		"""
		INTERNAL METHOD; DO NOT USE
		Returns the next cpu core and updates internal counter
		:return: Next CPU core
		"""

		core = cls.__next_cpu
		cls.__next_cpu = cls.__next_cpu + 1 % psutil.cpu_count(True)
		return core

	def __init__(self, function: typing.Callable, *args, **kwargs):
		"""
		[Thread] - Class handling a single multiprocessing.Process each on a single core
		Consecutive instances of this class will execute on the next core
		- Constructor -
		:param function: (CALLABLE) The function to call
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		"""

		CustomMethodsVI.Misc.raise_ifn(callable(function), CustomMethodsVI.Exceptions.InvalidArgumentException(Thread.__init__, 'function', type(function)))
		self.__core = type(self).__get_next_cpu_core()
		self.__call = function
		self.__args = args
		self.__kwargs = kwargs
		self.__proc = None		# type: None | multiprocessing.Process

	def signal(self, sig) -> None:
		"""
		Sends a signal to the function process
		:param sig: The signal to send
		:return: (None)
		"""

		psutil.Process(self.__proc.pid).send_signal(sig)

	def join(self, timeout: float = None) -> None:
		"""
		Blocks this thread until underlying process is complete
		:param timeout: The time (in seconds) to wait
		:return: (None)
		"""

		self.__proc.join(timeout)

	def start(self, daemon: bool = True) -> int:
		"""
		Starts the underlying process and calls the function
		:param daemon: Whether to mark the process as a daemon
		:return: (int) The underlying process ID
		"""

		self.__proc = multiprocessing.Process(target=self.__call, args=self.__args, kwargs=self.__kwargs, daemon=bool(daemon))
		self.__proc.start()
		psutil.Process(self.__proc.pid).cpu_affinity([self.__core])
		return self.__proc.pid

	def is_alive(self) -> bool:
		"""
		Checks whether the function process is alive
		:return: Aliveness
		"""

		return self.__proc.is_alive()

	def core(self) -> int:
		"""
		Gets the current core this thread runs on
		:return: Coreness
		"""

		return self.__core

