from __future__ import annotations

import asyncio
import threading
import time
import typing

from . import Synchronization
from .. import Exceptions
from .. import Misc
from .. import Stream


class SpinLock(Synchronization.SynchronizationPrimitive):
	def __init__(self):
		"""
		Class representing a threading compatible spin lock
		"""

		self.__event__: threading.Event = threading.Event()
		self.__lock__: threading.Lock = threading.Lock()
		self.__active__: int = -1
		self.__count__: int = 0

	def acquire(self, timeout: float = None) -> bool:
		"""
		Acquires the lock\n
		Blocks until lock is acquired
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		lock_id: int = threading.current_thread().native_id
		remaining: typing.Optional[float] = None if timeout is None or timeout is ... else float(timeout)
		t1: float = time.perf_counter()

		while True:
			with self.__lock__:
				if self.__active__ == -1:
					self.__event__.clear()
					self.__active__ = lock_id
					self.__count__ = 1
					return True
				elif self.__active__ == lock_id:
					self.__event__.clear()
					self.__count__ += 1
					return True

			self.__event__.wait(remaining)

			if remaining is not None:
				t2: float = time.perf_counter()
				td: float = t2 - t1
				t1 = t2
				remaining -= td

				if remaining <= 0:
					return False

	def release(self) -> None:
		"""
		Releases the lock
		"""

		lock_id: int = threading.current_thread().native_id

		with self.__lock__:
			Misc.raise_ifn(self.__active__ == lock_id and self.__count__ > 0, IOError('Lock is not acquired'))
			self.__count__ -= 1

			if self.__count__ == 0:
				self.__active__ = -1
				self.__event__.set()

	@property
	def acquired(self) -> bool:
		"""
		:return: Whether this thread has the lock
		"""

		lock_id: int = threading.current_thread().native_id

		with self.__lock__:
			return self.__active__ == lock_id and self.__count__ > 0


class PriorityLock(Synchronization.SynchronizationPrimitive):
	class __ThreadInfo__:
		def __init__(self, tid: int, priority: int):
			self.__thread_id__: int = tid
			self.__count__: int = 1
			self.__priority__: int = priority

		def increment(self) -> int:
			self.__count__ += 1
			return self.__count__

		def decrement(self) -> int:
			self.__count__ -= 1
			return self.__count__

		@property
		def thread(self) -> int:
			return self.__thread_id__

		@property
		def count(self) -> int:
			return self.__count__

		@property
		def priority(self) -> int:
			return self.__priority__

	def __init__(self):
		"""
		Class representing a threading compatible priority queue lock\n
		Threads are allowed in the order of their acquisition priority
		"""

		self.__event__: threading.Event = threading.Event()
		self.__lock__: threading.Lock = threading.Lock()
		self.__queue__: list[PriorityLock.__ThreadInfo__] = []

	def acquire(self, priority: int = 0, timeout: float = None) -> bool:
		"""
		Acquires the lock\n
		Blocks until lock is acquired
		:param priority: The lock priority (lower is higher)
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		this: PriorityLock.__ThreadInfo__ = PriorityLock.__ThreadInfo__(threading.current_thread().native_id, priority)

		with self.__lock__:
			added: bool = False

			for i, info in enumerate(self.__queue__):
				if info.thread == this.thread:
					info.increment()
					this = info
					added = True
					break
				elif i > 0 and this.priority < info.priority:
					self.__queue__.insert(i, this)
					self.__queue__[i + 1:] = [thread for thread in self.__queue__[i + 1:] if thread.thread != this.thread]
					added = True
					break

			if not added:
				self.__queue__.append(this)

			front: PriorityLock.__ThreadInfo__ = self.__queue__[0]

			if front.thread == this.thread:
				self.__event__.clear()
				return True

		while True:
			t1: float = time.perf_counter()
			result: bool = self.__event__.wait(timeout)
			t2: float = time.perf_counter()

			if not result:
				with self.__lock__:
					if this.decrement() == 0:
						self.__queue__.remove(this)

				return False

			if timeout is not None and timeout is not ...:
				timeout -= (t2 - t1)

			if self.acquired:
				return True

	def release(self) -> None:
		"""
		Releases the lock
		"""

		lock_id: int = threading.current_thread().native_id

		with self.__lock__:
			info: PriorityLock.__ThreadInfo__ = Stream.LinqStream(self.__queue__).first_or_default()
			Misc.raise_if(info is None or info.thread != lock_id or info.count <= 0, IOError('Lock is not acquired'))

			if info.decrement() == 0:
				del self.__queue__[0]
				self.__event__.set()

	@property
	def acquired(self) -> bool:
		"""
		:return: Whether this thread has the lock
		"""

		lock_id: int = threading.current_thread().native_id

		with self.__lock__:
			info: PriorityLock.__ThreadInfo__ = Stream.LinqStream(self.__queue__).first_or_default()
			return info is not None and info.thread == lock_id


class QueueLock(PriorityLock):
	"""
	Class representing a threading compatible queue lock\n
	Threads are allowed in the order of their acquisition order
	"""

	def acquire(self, timeout: float = None) -> bool:
		"""
		Acquires the lock\n
		Blocks until lock is acquired
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		return super().acquire(0, timeout)


class Semaphore(Synchronization.SynchronizationPrimitive):
	def __init__(self, max_count: int):
		"""
		Class representing a threading compatible integer semaphore\n
		- Constructor -
		:param max_count: The semaphore maximum count
		"""

		Misc.raise_ifn(isinstance(max_count, int), Exceptions.InvalidArgumentException(Semaphore.__init__, 'max_count', type(max_count), (int,)))
		Misc.raise_if(max_count <= 0, ValueError('Semaphore max count must be a positive, non-zero integer'))
		self.__max_count__: int = int(max_count)
		self.__threads__: set[int] = set()
		self.__count__: int = self.__max_count__
		self.__lock__: threading.Lock = threading.Lock()
		self.__event__: threading.Event = threading.Event()
		self.__event__.set()

	def acquire(self, timeout: float = None) -> bool:
		"""
		Tries to acquire the lock\n
		Blocks until lock is acquired or until timeout reached\n
		The internal counter is decremented by one
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		tid: int = threading.current_thread().native_id
		t1: float = time.perf_counter()

		with self.__lock__:
			while self.__count__ == 0:
				t2: float = time.perf_counter()
				self.__lock__.release()

				if not self.__event__.wait(None if timeout is None or timeout is ... else max(0., timeout - (t2 - t1))):
					return False

				self.__lock__.acquire()

			self.__count__ -= 1
			self.__threads__.add(tid)

			if self.__count__ == 0:
				self.__event__.clear()

			return True

	def release(self) -> None:
		"""
		Releases the lock\n
		The internal counter is incremented by one
		:raises IOError: If the lock's internal counter exceeds the maximum count (released too many times)
		"""

		tid: int = threading.current_thread().native_id

		if not self.acquired:
			raise IOError('Lock not acquired')

		with self.__lock__:
			self.__count__ += 1
			self.__threads__.remove(tid)
			self.__event__.set()

			if self.__count__ > self.__max_count__:
				raise IOError('Semaphore count exceeded')

	@property
	def acquired(self) -> bool:
		with self.__lock__:
			return threading.current_thread().native_id in self.__threads__


class ReaderWriterLock(Synchronization.ReaderWriterPrimitive):
	class __ThreadInfo__:
		"""
		INTERNAL CLASS
		"""

		def __init__(self, is_writer: bool, thread: int):
			self.__event__: threading.Event = threading.Event()
			self.__threads__: list[tuple[int, bool]] = [(thread, is_writer)]

		def __contains__(self, thread: int) -> bool:
			return isinstance(thread, int) and any(thread == tid for tid, _ in self.__threads__)

		def __eq__(self, other: ReaderWriterLock.__ThreadInfo__) -> bool:
			return isinstance(other, type(self)) and other.__threads__ == self.__threads__

		def __hash__(self) -> int:
			return hash(self.__threads__)

		def increment(self, thread: int, is_writer: bool) -> int:
			self.__threads__.append((thread, is_writer))
			return len(self.__threads__)

		def decrement(self, thread: int, is_writer: bool) -> int:
			for i, (tid, writer) in enumerate(self.__threads__):
				if tid == thread and writer == is_writer:
					del self.__threads__[i]
					break

			return len(self.__threads__)

		@property
		def is_reader(self) -> bool:
			return any(not pair[1] for pair in self.__threads__)

		@property
		def is_writer(self) -> bool:
			return any(pair[1] for pair in self.__threads__)

		@property
		def signal(self) -> threading.Event:
			return self.__event__

	class Lock(Synchronization.SynchronizationPrimitive):
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

		@property
		def acquired(self) -> bool:
			return self.__rw_lock__.writer_acquired if self.__writer__ else self.__rw_lock__.reader_acquired

	def __init__(self):
		"""
		Class representing a threading compatible reader writer lock\n
		- Constructor -
		"""

		self.__queued_threads__: list[ReaderWriterLock.__ThreadInfo__] = []
		self.__lock__: threading.RLock = threading.RLock()

	def __del__(self) -> None:
		if self.reader_acquired:
			self.release_reader()
		elif self.writer_acquired:
			self.release_writer()

	def release_reader(self) -> None:
		"""
		Releases the reader lock
		"""

		tid: int = threading.current_thread().ident

		with self.__lock__:
			thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).first_or_default()
			acquired: bool = thread_info is not None and tid in thread_info and not thread_info.is_writer

			if acquired and thread_info.decrement(tid, False) == 0:
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

			if acquired and thread_info.decrement(tid, True) == 0:
				thread_info.signal.clear()
				del self.__queued_threads__[0]

			if acquired and (thread_info := Stream.LinqStream(self.__queued_threads__).first_or_default()) is not None:
				thread_info.signal.set()

		if not acquired:
			raise IOError('The writer is not acquired')

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

			if thread_info is None or (writer_active and tid not in thread_info):
				this = ReaderWriterLock.__ThreadInfo__(False, tid)
				self.__queued_threads__.append(this)
			else:
				this = thread_info
				thread_info.increment(tid, False)

		if thread_info is None or tid in thread_info:
			this.signal.set()
			return True
		elif this.signal.wait(timeout):
			return True
		else:
			with self.__lock__:
				if this.decrement(tid) == 0:
					self.__queued_threads__.remove(this)

			return False

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
			writer_active: bool = any(info.is_writer for info in self.__queued_threads__)

			if thread_info is None or (writer_active and tid not in thread_info):
				this = ReaderWriterLock.__ThreadInfo__(True, tid)
				self.__queued_threads__.append(this)
			else:
				this = thread_info
				thread_info.increment(tid, False)

		if thread_info is None:
			this.signal.set()
			return True
		elif this.signal.wait(timeout):
			return True
		else:
			with self.__lock__:
				self.__queued_threads__.remove(this)

			return False

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
			return thread_info is not None and thread_info.is_reader and threading.current_thread().ident in thread_info

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


class Barrier(Synchronization.BarrierPrimitive):
	def __init__(self, count: int):
		"""
		Class representing threading compatible barrier
		:param count: The number of threads that must reach the barrier
		"""

		Misc.raise_ifn(isinstance(count, int) and (count := int(count)) >= 0, Exceptions.InvalidArgumentException(Barrier.__init__, 'count', type(count), (int,), 'Count must be a positive integer'))

		self.__max_count__: int = int(count)
		self.__count__: int = 0
		self.__event__: threading.Event = threading.Event()
		self.__thread_lock__: threading.Lock = threading.Lock()

	def wait(self, timeout: float = None) -> bool:
		with self.__thread_lock__:
			self.__count__ += 1

			if self.__count__ == self.__max_count__:
				self.__count__ = 0
				self.__event__.set()
				self.__event__.clear()
				return True

		return self.__event__.wait(timeout)


class DynamicBarrier(Synchronization.DynamicBarrierPrimitive):
	def __init__(self):
		"""
		Class representing threading compatible barrier\n
		Executors must enter the barrier before waiting at the barrier
		"""

		self.__max_count__: int = 0
		self.__count__: int = 0
		self.__event__: threading.Event = threading.Event()
		self.__thread_lock__: threading.Lock = threading.Lock()
		self.__ready__: set[int] = set()
		self.__channel__: set[int] = set()

	def enter(self) -> None:
		if self.entered:
			return

		tid: int = threading.current_thread().native_id

		with self.__thread_lock__:
			self.__channel__.add(tid)
			self.__max_count__ += 1

		self.__event__.clear()

	def exit(self) -> None:
		if not self.entered:
			return

		tid: int = threading.current_thread().native_id

		with self.__thread_lock__:
			self.__channel__.remove(tid)

			if tid in self.__ready__:
				self.__ready__.remove(tid)
				self.__count__ -= 1

			self.__max_count__ -= 1

		self.__event__.clear()

	def wait(self, timeout: float = None) -> bool:
		if not self.entered:
			raise IOError('Not in barrier channel')

		tid: int = threading.current_thread().native_id

		with self.__thread_lock__:
			if tid not in self.__ready__:
				self.__ready__.add(tid)
				self.__count__ += 1

				if self.__count__ == self.__max_count__:
					self.__count__ = 0
					self.__ready__.clear()
					self.__event__.set()
					self.__event__.clear()
					return True

		return self.__event__.wait(timeout)

	@property
	def entered(self) -> bool:
		with self.__thread_lock__:
			return threading.current_thread().native_id in self.__channel__

	@property
	def max_count(self) -> int:
		return len(self.__channel__)


__all__: list[str] = ['SpinLock', 'PriorityLock', 'QueueLock', 'Semaphore', 'ReaderWriterLock', 'Barrier', 'DynamicBarrier']
