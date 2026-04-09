from __future__ import annotations

import multiprocessing
import multiprocessing.synchronize
import os
import struct
import threading
import time

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

		def __init__(self, is_writer: bool, thread: int):
			self.__is_writer__: bool = bool(is_writer)
			self.__event__: threading.Event = threading.Event()
			self.__threads__: set[int] = {thread}

		def __contains__(self, thread: int) -> bool:
			return isinstance(thread, int) and thread in self.__threads__

		def increment(self, thread: int) -> int:
			self.__threads__.add(thread)
			return len(self.__threads__)

		def decrement(self, thread: int) -> int:
			self.__threads__.discard(thread)
			return len(self.__threads__)

		@property
		def is_writer(self) -> bool:
			return self.__is_writer__

		@property
		def counter(self) -> int:
			return len(self.__threads__)

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

	def __del__(self) -> None:
		if self.reader_acquired:
			self.release_reader()
		elif self.writer_acquired:
			self.release_writer()

	def acquire_reader(self, timeout: float = None) -> bool:
		"""
		Acquires the reader lock\n
		If no writer is in the queue, will return immediately
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		tid: int = threading.current_thread().ident
		this: ReaderWriterLock.__ThreadInfo__

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).last_or_default()
			writer_active: bool = any(info.is_writer for info in self.__queued_threads__)

			if thread_info is None or writer_active:
				this = ReaderWriterLock.__ThreadInfo__(False, tid)
				self.__queued_threads__.append(this)
			else:
				this = thread_info
				thread_info.increment(tid)

		if thread_info is None or tid in thread_info:
			this.signal.set()
			return True
		else:
			return this.signal.wait(timeout)

	def acquire_writer(self, timeout: float = None) -> bool:
		"""
		Acquires the writer lock\n
		If no writer is in the queue, will return immediately
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		tid: int = threading.current_thread().ident
		this: ReaderWriterLock.__ThreadInfo__

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).last_or_default()
			this = ReaderWriterLock.__ThreadInfo__(True, tid)
			self.__queued_threads__.append(this)

		if thread_info is None:
			this.signal.set()
			return True
		else:
			return this.signal.wait(timeout)

	def release_reader(self) -> None:
		"""
		Releases the reader lock
		"""

		tid: int = threading.current_thread().ident

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).first_or_default()
			acquired: bool = thread_info is not None and tid in thread_info and not thread_info.is_writer

			if acquired and thread_info.decrement(tid) == 0:
				thread_info.signal.clear()
				del self.__queued_threads__[0]

			if acquired and (thread_info := Stream.LinqStream(self.__queued_threads__).first_or_default()) is not None:
				thread_info.signal.set()

		if not acquired:
			raise IOError('The reader is not acquired')

	def release_writer(self) -> None:
		"""
		Releases the writer lock
		"""

		tid: int = threading.current_thread().ident

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).first_or_default()
			acquired: bool = thread_info is not None and tid in thread_info and thread_info.is_writer

			if acquired and thread_info.decrement(tid) == 0:
				thread_info.signal.clear()
				del self.__queued_threads__[0]

			if acquired and (thread_info := Stream.LinqStream(self.__queued_threads__).first_or_default()) is not None:
				thread_info.signal.set()

		if not acquired:
			raise IOError('The writer is not acquired')

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

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).first_or_default()
			return thread_info is not None and not thread_info.is_writer and threading.current_thread().ident in thread_info

	@property
	def writer_acquired(self) -> bool:
		"""
		:return: Whether the writer lock is acquired
		"""

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).first_or_default()
			return thread_info is not None and thread_info.is_writer and threading.current_thread().ident in thread_info

	@property
	def acquired(self) -> bool:
		"""
		:return: Whether the reader or writer lock is acquired
		"""

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).first_or_default()
			return thread_info is not None and threading.current_thread().ident in thread_info


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

	def acquire(self, timeout: float = None) -> bool:
		"""
		Acquires the lock\n
		Blocks until lock is acquired
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		lock_id: int = struct.unpack('=Q', struct.pack('=II', os.getpid(), threading.current_thread().native_id))[0]
		t1: float = time.perf_counter()

		while True:
			with self.__source__.get_lock():
				if self.__source__.value == 0 or self.__source__.value == lock_id:
					self.__source__.value = lock_id
					self.__count__ += 1
					return True
				elif timeout is not None and timeout is not ... and time.perf_counter() - t1 >= timeout:
					return False

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

	def __init__(self, max_count: int):
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

	def acquire(self, timeout: float = None) -> bool:
		"""
		Acquires the lock\n
		The internal counter is decremented by one
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		try:
			t1: float = time.perf_counter()

			if not self.__acc_lock__.acquire(timeout=-1 if timeout is None or timeout is ... else timeout):
				return False

			t2: float = time.perf_counter()

			if not self.__event__.wait(None if timeout is None or timeout is ... else (timeout - (t2 - t1))):
				return False

			with self.__rel_lock__:
				self.__count__ -= 1

				if self.__count__ == 0:
					self.__event__.clear()

			return True
		finally:
			self.__acc_lock__.release()

	def release(self) -> None:
		"""
		Releases the lock\n
		The internal counter is incremented by one
		:raises TimeoutError: If the lock is not acquired withing the specified timeout
		:raises IOError: If the lock's internal counter exceeds the maximum count (released too many times)
		"""

		with self.__rel_lock__:
			self.__count__ += 1
			self.__event__.set()

			if self.__count__ > self.__max_count__:
				raise IOError('Semaphore count exceeded')


class Counter(SynchronizationPrimitive):
	"""
	Class representing an integer counter
	"""

	def __init__(self, initial_count: int = 0):
		"""
		Class representing an integer counter\n
		- Constructor -
		:param initial_count: The counter initial count
		"""

		Misc.raise_ifn(isinstance(initial_count, int), Exceptions.InvalidArgumentException(Counter.__init__, 'initial_count', type(initial_count), (int,)))
		self.__count__: int = int(initial_count)
		self.__acc_lock__: threading.Lock = threading.Lock()
		self.__rel_lock__: threading.Lock = threading.Lock()
		self.__event__: threading.Event = threading.Event()
		self.__event__.set()

	def __enter__(self) -> Counter:
		self.acquire()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb) -> None:
		self.release()

	def acquire(self, timeout: float = None) -> bool:
		"""
		Acquires the lock\n
		The internal counter is incremented by one
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		try:
			t1: float = time.perf_counter()

			if not self.__acc_lock__.acquire(timeout=-1 if timeout is None or timeout is ... else timeout):
				return False

			t2: float = time.perf_counter()

			if not self.__event__.wait(None if timeout is None or timeout is ... else (timeout - (t2 - t1))):
				return False

			with self.__rel_lock__:
				self.__count__ += 1

				if self.__count__ == 0:
					self.__event__.clear()

			return True
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
			self.__count__ -= 1
			self.__event__.set()


class LockUser:
	def __init__(self, lock: LockType_T = SpinLock()):
		"""
		Class representing an object that can acquire a lock
		:param lock: The underlying lock to use
		"""

		Misc.raise_ifn(isinstance(lock, LockType_T), Exceptions.InvalidArgumentException(LockUser.__init__, 'lock', type(lock), (threading.Lock, multiprocessing.synchronize.Lock, SynchronizationPrimitive)))
		self.__lock__: LockType_T = lock

	def acquire_read_lock(self) -> bool:
		"""
		Acquires the reader lock if an RW lock, otherwise acquires the lock\n
		Blocks until lock is acquired
		:return: Whether the lock was acquired
		"""

		if isinstance(self.__lock__, (ReaderWriterLock,)):
			return self.__lock__.acquire_reader()
		else:
			return self.__lock__.acquire()

	def acquire_write_lock(self) -> bool:
		"""
		Acquires the writer lock if an RW lock, otherwise acquires the lock\n
		Blocks until lock is acquired
		:return: Whether the lock was acquired
		"""

		if isinstance(self.__lock__, (ReaderWriterLock,)):
			return self.__lock__.acquire_writer()
		else:
			return self.__lock__.acquire()

	def read_lock(self) -> LockType_T | ReaderWriterLock.Lock:
		"""
		Returns the reader lock if an RW lock, otherwise the lock
		:return: The lock object for context management
		"""

		if isinstance(self.__lock__, (ReaderWriterLock,)):
			return self.__lock__.reader()
		else:
			return self.__lock__

	def write_lock(self) -> LockType_T | ReaderWriterLock.Lock:
		"""
		Returns the reader lock if an RW lock, otherwise the lock
		:return: The lock object for context management
		"""

		if isinstance(self.__lock__, (ReaderWriterLock,)):
			return self.__lock__.writer()
		else:
			return self.__lock__


LockType_T = threading.Lock | multiprocessing.synchronize.Lock | SynchronizationPrimitive


__all__: list[str] = ['SynchronizationPrimitive', 'ReaderWriterLock', 'SpinLock', 'Semaphore']
