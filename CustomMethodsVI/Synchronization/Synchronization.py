from __future__ import annotations

import multiprocessing
import multiprocessing.synchronize
import threading
import _thread

from .. import Exceptions
from .. import Misc


class BarrierPrimitive:
	"""
	Base class for Synchronization barriers
	"""

	def wait(self, timeout: float = None) -> bool:
		"""
		Reaches the barrier\n
		Blocks until all executors have reached the barrier or until timeout reached\n
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		pass

	@property
	def max_count(self) -> int:
		"""
		:return: The maximum number of executors this barrier will wait for
		"""

		return 0


class DynamicBarrierPrimitive(BarrierPrimitive):
	"""
	Base class for dynamic Synchronization barriers
	"""

	def __del__(self):
		if self.entered:
			self.exit()

	def __enter__(self) -> BarrierPrimitive:
		"""
		Binds this executor to this barrier for the duration of the context
		:return: This barrier
		"""

		self.enter()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb) -> None:
		"""
		Releases this executor from this barrier
		:param exc_type: The exception type
		:param exc_val: The exception
		:param exc_tb: The exception traceback
		"""

		self.exit()

	def enter(self) -> None:
		"""
		Binds this executor to this barrier for the duration of the context
		:return: This barrier
		"""

		pass

	def exit(self) -> None:
		"""
		Releases this executor from this barrier
		"""

		pass

	def wait(self, timeout: float = None) -> bool:
		"""
		Reaches the barrier\n
		Blocks until all executors have reached the barrier or until timeout reached\n
		Must be used inside this barrier's context manager
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		pass

	async def async_wait(self, timeout: float = None) -> bool:
		"""
		*Async compatible*\n
		Reaches the barrier\n
		Blocks until all executors have reached the barrier or until timeout reached\n
		Must be used inside this barrier's context manager
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		pass

	@property
	def entered(self) -> bool:
		"""
		:return: Whether this executor is within the barrier channel
		"""

		return False


class SynchronizationPrimitive:
	"""
	Base class for Synchronization locks
	"""

	def __del__(self):
		if self.acquired:
			self.release()

	def __enter__(self) -> SynchronizationPrimitive:
		"""
		Acquires the lock
		:return: This lock
		"""

		self.acquire()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb) -> None:
		"""
		Releases the lock
		:param exc_type: The exception type
		:param exc_val: The exception
		:param exc_tb: The exception traceback
		"""

		if self.acquired:
			self.release()

	def release(self) -> None:
		"""
		Releases the lock
		"""

		pass

	def acquire(self, timeout: float = None) -> bool:
		"""
		Tries to acquire the lock\n
		Blocks until lock is acquired or until timeout reached
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		pass

	@property
	def acquired(self) -> bool:
		"""
		:return: Whether this lock is acquired
		"""

		return False


class ReaderWriterPrimitive:
	def release_reader(self) -> None:
		"""
		Releases the reader lock
		:raise IOError: If the lock was not acquired
		"""

		pass

	def release_writer(self) -> None:
		"""
		Releases the writer lock
		:raise IOError: If the lock was not acquired
		"""

		pass

	def acquire_reader(self, timeout: float = None) -> bool:
		"""
		Tries to acquire the reader lock\n
		Blocks until lock is acquired or until timeout reached
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		pass

	def acquire_writer(self, timeout: float = None) -> bool:
		"""
		Tries to acquire the writer lock\n
		Blocks until lock is acquired or until timeout reached
		:param timeout: The number of seconds to wait or None to wait indefinitely
		:return: Whether the lock was acquired
		"""

		pass

	def reader(self) -> SynchronizationPrimitive:
		"""
		:return: The reader lock
		"""

		return ...

	def writer(self) -> SynchronizationPrimitive:
		"""
		:return: The writer lock
		"""

		return ...

	@property
	def reader_acquired(self) -> bool:
		"""
		:return: Whether the reader lock is acquired
		"""

		return False

	@property
	def writer_acquired(self) -> bool:
		"""
		:return: Whether the writer lock is acquired
		"""

		return False


class LockUser:
	def __init__(self, lock: LockType_T):
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

		if isinstance(self.__lock__, ReaderWriterPrimitive):
			return self.__lock__.acquire_reader()
		else:
			return self.__lock__.acquire()

	def acquire_write_lock(self) -> bool:
		"""
		Acquires the writer lock if an RW lock, otherwise acquires the lock\n
		Blocks until lock is acquired
		:return: Whether the lock was acquired
		"""

		if isinstance(self.__lock__, ReaderWriterPrimitive,):
			return self.__lock__.acquire_writer()
		else:
			return self.__lock__.acquire()

	def read_lock(self) -> LockType_T:
		"""
		Returns the reader lock if an RW lock, otherwise the lock
		:return: The lock object for context management
		"""

		if isinstance(self.__lock__, ReaderWriterPrimitive):
			return self.__lock__.reader()
		else:
			return self.__lock__

	def write_lock(self) -> LockType_T:
		"""
		Returns the reader lock if an RW lock, otherwise the lock
		:return: The lock object for context management
		"""

		if isinstance(self.__lock__, ReaderWriterPrimitive):
			return self.__lock__.writer()
		else:
			return self.__lock__

	@property
	def lock(self) -> LockType_T:
		"""
		:return: The underlying lock
		"""

		return self.__lock__


LockType_T = _thread.LockType | multiprocessing.synchronize.Lock | SynchronizationPrimitive | ReaderWriterPrimitive

__all__: list[str] = ['BarrierPrimitive', 'DynamicBarrierPrimitive', 'SynchronizationPrimitive', 'ReaderWriterPrimitive', 'LockUser', 'LockType_T']
