from __future__ import annotations

import multiprocessing
import multiprocessing.synchronize
import os
import threading
import struct
import time

from . import Stream


class ReaderWriterLock:
	class __ThreadInfo__:
		def __init__(self, initial_thread: int, is_writer: bool):
			self.__thread_queue__: list[int] = [initial_thread]
			self.__is_writer__: bool = bool(is_writer)

		def __repr__(self) -> str:
			if self.is_writer:
				return f'Writer @ {self.__thread_queue__[0]}'
			else:
				return f'Reader(s) @ {self.__thread_queue__}'

		@property
		def is_writer(self) -> bool:
			return self.__is_writer__

	def __init__(self):
		self.__queued_threads__: list[ReaderWriterLock.__ThreadInfo__] = []
		self.__lock__: threading.RLock = threading.RLock()

	def __del__(self):
		self.__lock__.acquire()
		remaining: int = len(self.__queued_threads__)
		self.__lock__.release()

		if remaining > 0:
			raise IOError('Reader writer lock incomplete')

	def acquire_reader(self) -> None:
		thread_id: int = threading.current_thread().native_id
		self.__lock__.acquire()
		thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).last_or_default()
		writer_active: bool = Stream.LinqStream(self.__queued_threads__).filter(lambda info: info.is_writer).any()

		if writer_active and (thread_info is None or thread_info.is_writer):
			self.__queued_threads__.append(ReaderWriterLock.__ThreadInfo__(thread_id, False))
		elif writer_active:
			thread_info.__thread_queue__.append(thread_id)
		elif thread_info is None:
			self.__queued_threads__.append(ReaderWriterLock.__ThreadInfo__(thread_id, False))
		else:
			thread_info.__thread_queue__.append(thread_id)

		thread_info = Stream.LinqStream(self.__queued_threads__).first_or_default()

		if thread_id in thread_info.__thread_queue__:
			self.__lock__.release()
			return

		while True:
			self.__lock__.release()
			time.sleep(0.000001)
			self.__lock__.acquire()
			thread_info = Stream.LinqStream(self.__queued_threads__).first_or_default()

			if thread_id in thread_info.__thread_queue__:
				break

		self.__lock__.release()

	def acquire_writer(self) -> None:
		thread_id: int = threading.current_thread().native_id
		self.__lock__.acquire()
		thread_info: ReaderWriterLock.__ThreadInfo__ = ReaderWriterLock.__ThreadInfo__(thread_id, True)
		self.__queued_threads__.append(thread_info)

		while True:
			self.__lock__.release()
			time.sleep(0.000001)
			self.__lock__.acquire()
			thread_info = Stream.LinqStream(self.__queued_threads__).first_or_default()

			if thread_id in thread_info.__thread_queue__:
				break

		self.__lock__.release()

	def release_reader(self) -> None:
		thread_id: int = threading.current_thread().native_id
		self.__lock__.acquire()
		thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).first_or_default()

		if thread_info is None or thread_info.is_writer or thread_id not in thread_info.__thread_queue__:
			self.__lock__.release()
			return

		thread_info.__thread_queue__.remove(thread_id)

		if len(thread_info.__thread_queue__) == 0:
			self.__queued_threads__.pop(0)

		self.__lock__.release()

	def release_writer(self) -> None:
		thread_id: int = threading.current_thread().native_id
		self.__lock__.acquire()
		thread_info: ReaderWriterLock.__ThreadInfo__ = Stream.LinqStream(self.__queued_threads__).first_or_default()

		if thread_info is None or not thread_info.is_writer or thread_id not in thread_info.__thread_queue__:
			self.__lock__.release()
			return

		self.__queued_threads__.pop(0)
		self.__lock__.release()


class SpinLock:
	def __init__(self):
		self.__source__ = multiprocessing.Value('Q')
		self.__count__: int = 0

	def __del__(self):
		if self.acquired:
			self.release()

	def acquire(self) -> None:
		lock_id: int = struct.unpack('=Q', struct.pack('=II', os.getpid(), threading.current_thread().native_id))[0]

		while True:
			with self.__source__.get_lock():
				if self.__source__.value == 0 or self.__source__.value == lock_id:
					self.__source__.value = lock_id
					self.__count__ += 1
					return

	def release(self) -> None:
		lock_id: int = struct.unpack('=Q', struct.pack('=II', os.getpid(), threading.current_thread().native_id))[0]

		with self.__source__.get_lock():
			if self.__source__.value != lock_id or self.__count__ == 0:
				raise IOError('Lock not acquired')

			self.__count__ -= 1

			if self.__count__ == 0:
				self.__source__.value = 0

	@property
	def acquired(self) -> bool:
		lock_id: int = struct.unpack('=Q', struct.pack('=II', os.getpid(), threading.current_thread().native_id))[0]

		with self.__source__.get_lock():
			return self.__source__.value == lock_id
