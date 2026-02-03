from __future__ import annotations

import multiprocessing
import os
import struct
import threading
import time
import typing

from . import Exceptions
from . import Misc
from . import Stream


class SynchronizationPrimitive:
	"""
	Base class for Synchronization locks
	"""


class ReaderWriterLock(SynchronizationPrimitive):
	"""
	Class representing a reader writer lock
	"""

	class __ThreadInfo__:
		"""
		INTERNAL CLASS
		"""

		def __init__(self, is_writer: bool):
			self.__counter__: int = 1
			self.__is_writer__: bool = bool(is_writer)
			self.__event__: threading.Event = threading.Event()

		def increment(self) -> int:
			self.__counter__ += 1
			return self.__counter__

		def decrement(self) -> int:
			self.__counter__ -= 1
			return self.__counter__

		@property
		def is_writer(self) -> bool:
			return self.__is_writer__

		@property
		def counter(self) -> int:
			return self.__counter__

		@property
		def signal(self) -> threading.Event:
			return self.__event__

	class Lock:
		"""
		Single reader-writer lock allowing context
		"""

		def __init__(self, rw_lock: ReaderWriterLock, is_writer: bool):
			"""
			Single reader-writer lock allowing context\n
			- Constructor -
			:param rw_lock: The parent RW lock
			:param is_writer: Whether this lock is a writer
			"""

			assert isinstance(rw_lock, ReaderWriterLock)
			self.__rw_lock__: ReaderWriterLock = rw_lock
			self.__writer__: bool = bool(is_writer)

		def __enter__(self) -> ReaderWriterLock.Lock:
			if self.__writer__:
				self.__rw_lock__.acquire_writer()
			else:
				self.__rw_lock__.acquire_reader()

			return self

		def __exit__(self, exc_type, exc_val, exc_tb) -> None:
			if self.__writer__:
				self.__rw_lock__.release_writer()
			else:
				self.__rw_lock__.release_reader()

	def __init__(self):
		"""
		Class representing a reader writer lock\n
		- Constructor -
		"""

		self.__queued_threads__: list[ReaderWriterLock.__ThreadInfo__] = []
		self.__lock__: threading.RLock = threading.RLock()
		self.__thread_info__: typing.Optional[ReaderWriterLock.__ThreadInfo__] = None

	def __del__(self) -> None:
		if self.reader_acquired:
			self.release_reader()
		elif self.writer_acquired:
			self.release_writer()

	def acquire_reader(self, timeout: float = None) -> None:
		"""
		Acquires the reader lock\n
		If no writer is in the queue, will return immediately
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:raises TimeoutError: If the lock is not acquired withing the specified timeout
		"""

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).last_or_default()
			writer_active: bool = any(info.is_writer for info in self.__queued_threads__)

			if thread_info is None or writer_active:
				self.__thread_info__ = ReaderWriterLock.__ThreadInfo__(False)
				self.__queued_threads__.append(self.__thread_info__)
			else:
				thread_info.increment()
				self.__thread_info__ = thread_info

		if thread_info is None:
			self.__thread_info__.signal.set()
		else:
			Misc.raise_ifn(self.__thread_info__.signal.wait(timeout), TimeoutError('Lock acquisition timed out'))

	def acquire_writer(self, timeout: float = None) -> None:
		"""
		Acquires the writer lock\n
		If no writer is in the queue, will return immediately
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:raises TimeoutError: If the lock is not acquired withing the specified timeout
		"""

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).last_or_default()
			self.__thread_info__ = ReaderWriterLock.__ThreadInfo__(True)
			self.__queued_threads__.append(self.__thread_info__)

		if thread_info is None:
			self.__thread_info__.signal.set()
		else:
			Misc.raise_ifn(self.__thread_info__.signal.wait(timeout), TimeoutError('Lock acquisition timed out'))

	def release_reader(self) -> None:
		"""
		Releases the reader lock
		"""

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).first_or_default()
			Misc.raise_ifn(thread_info is not None and thread_info is self.__thread_info__ and not thread_info.is_writer, IOError('The reader is not acquired'))

			if thread_info.decrement() == 0:
				self.__thread_info__.signal.clear()
				del self.__queued_threads__[0]

			if (thread_info := Stream.LinqStream(self.__queued_threads__).first_or_default()) is not None:
				thread_info.signal.set()

	def release_writer(self) -> None:
		"""
		Releases the writer lock
		"""

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).first_or_default()
			Misc.raise_ifn(thread_info is not None and thread_info is self.__thread_info__ and thread_info.is_writer, IOError('The writer is not acquired'))

			if thread_info.decrement() == 0:
				self.__thread_info__.signal.clear()
				del self.__queued_threads__[0]

			if (thread_info := Stream.LinqStream(self.__queued_threads__).first_or_default()) is not None:
				thread_info.signal.set()

	def reader(self) -> ReaderWriterLock.Lock:
		"""
		Returns a reader lock supporting the context manager protocol
		:return: The reader lock
		"""

		return ReaderWriterLock.Lock(self, False)

	def writer(self) -> ReaderWriterLock.Lock:
		"""
		Returns a writer lock supporting the context manager protocol
		:return: The writer lock
		"""

		return ReaderWriterLock.Lock(self, True)

	@property
	def reader_acquired(self) -> bool:
		"""
		:return: Whether the reader lock is acquired
		"""

		return self.__thread_info__ is not None and not self.__thread_info__.is_writer and self.__thread_info__.signal.is_set()

	@property
	def writer_acquired(self) -> bool:
		"""
		:return: Whether the writer lock is acquired
		"""

		return self.__thread_info__ is not None and self.__thread_info__.is_writer and self.__thread_info__.signal.is_set()

	@property
	def acquired(self) -> bool:
		"""
		:return: Whether the reader or writer lock is acquired
		"""

		return self.__thread_info__ is not None and self.__thread_info__.signal.is_set()


class SpinLock(SynchronizationPrimitive):
	"""
	Class representing a spin lock
	"""

	def __init__(self):
		"""
		Class representing a spin lock
		- Constructor -
		"""

		self.__source__ = multiprocessing.Value('Q')
		self.__count__: int = 0

	def __del__(self):
		if self.acquired:
			self.release()

	def __enter__(self) -> SpinLock:
		self.acquire()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb) -> None:
		self.release()

	def acquire(self, timeout: float = None) -> None:
		"""
		Acquires the lock\n
		Blocks until lock is acquired
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:raises TimeoutError: If the lock is not acquired withing the specified timeout
		"""

		lock_id: int = struct.unpack('=Q', struct.pack('=II', os.getpid(), threading.current_thread().native_id))[0]
		t1: float = time.perf_counter()

		while True:
			with self.__source__.get_lock():
				if self.__source__.value == 0 or self.__source__.value == lock_id:
					self.__source__.value = lock_id
					self.__count__ += 1
					return
				elif timeout is not None and timeout is not ... and time.perf_counter() - t1 >= timeout:
					raise TimeoutError('Lock acquisition timed out')

	def release(self) -> None:
		"""
		Releases the lock
		"""

		lock_id: int = struct.unpack('=Q', struct.pack('=II', os.getpid(), threading.current_thread().native_id))[0]

		with self.__source__.get_lock():
			if self.__source__.value != lock_id or self.__count__ == 0:
				raise IOError('Lock not acquired')

			self.__count__ -= 1

			if self.__count__ == 0:
				self.__source__.value = 0

	@property
	def acquired(self) -> bool:
		"""
		:return: Whether this thread has the lock
		"""

		lock_id: int = struct.unpack('=Q', struct.pack('=II', os.getpid(), threading.current_thread().native_id))[0]

		with self.__source__.get_lock():
			return self.__source__.value == lock_id


class Semaphore(SynchronizationPrimitive):
	"""
	Class representing an integer semaphore
	"""

	def __init__(self, max_count: int) -> None:
		"""
		Class representing an integer semaphore\n
		- Constructor -
		:param max_count: The semaphore maximum count
		"""

		Misc.raise_ifn(isinstance(max_count, int), Exceptions.InvalidArgumentException(Semaphore.__init__, 'max_count', type(max_count), (int,)))
		Misc.raise_if(max_count <= 0, ValueError('Semaphore max count must be a positive, non-zero integer'))
		self.__max_count__: int = int(max_count)
		self.__count__: int = self.__max_count__
		self.__acc_lock__: threading.Lock = threading.Lock()
		self.__rel_lock__: threading.Lock = threading.Lock()
		self.__event__: threading.Event = threading.Event()
		self.__event__.set()

	def __enter__(self) -> Semaphore:
		self.acquire()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb) -> None:
		self.release()

	def acquire(self, timeout: float = None) -> None:
		"""
		Acquires the lock\n
		The internal counter is decremented by one
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:raises TimeoutError: If the lock is not acquired withing the specified timeout
		"""

		try:
			t1: float = time.perf_counter()
			Misc.raise_ifn(self.__acc_lock__.acquire(timeout=-1 if timeout is None or timeout is ... else timeout), TimeoutError('Lock acquisition timed out'))
			t2: float = time.perf_counter()
			Misc.raise_ifn(self.__event__.wait(None if timeout is None or timeout is ... else (timeout - (t2 - t1))), TimeoutError('Lock acquisition timed out'))

			with self.__rel_lock__:
				self.__count__ -= 1

				if self.__count__ == 0:
					self.__event__.clear()
		finally:
			self.__acc_lock__.release()

	def release(self) -> None:
		"""
		Releases the lock\n
		The internal counter is decremented by one
		:raises TimeoutError: If the lock is not acquired withing the specified timeout
		:raises IOError: If the lock's internal counter exceeds the maximum count (released too many times)
		"""

		with self.__rel_lock__:
			self.__count__ += 1
			self.__event__.set()

			if self.__count__ > self.__max_count__:
				raise IOError('Semaphore count exceeded')
