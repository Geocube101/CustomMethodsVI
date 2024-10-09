from __future__ import annotations

import multiprocessing
import multiprocessing.synchronize
import os
import threading
import struct


class ReaderWriterLock:
	class ReaderLock:
		def __init__(self, src: ReaderWriterLock):
			assert isinstance(src, ReaderWriterLock)

			self.__rwlock__: ReaderWriterLock = src
			self.__count__: int = 0

		def __del__(self):
			if self.__count__ > 0:
				self.__rwlock__.release_reader()

		def __enter__(self) -> ReaderWriterLock.ReaderLock:
			self.acquire()
			return self

		def __exit__(self, exc_type, exc_val, exc_tb) -> None:
			self.release()

		def acquire(self) -> None:
			if self.__count__ == 0:
				self.__rwlock__.acquire_reader()

			self.__count__ += 1

		def release(self) -> None:
			if self.__count__ == 1:
				self.__rwlock__.release_reader()

			if self.__count__ > 0:
				self.__count__ -= 1

	class WriterLock:
		def __init__(self, src: ReaderWriterLock):
			assert isinstance(src, ReaderWriterLock)

			self.__rwlock__: ReaderWriterLock = src
			self.__count__: int = 0

		def __del__(self):
			if self.__count__ > 0:
				self.__rwlock__.release_writer()

		def __enter__(self) -> ReaderWriterLock.WriterLock:
			self.acquire()
			return self

		def __exit__(self, exc_type, exc_val, exc_tb) -> None:
			self.release()

		def acquire(self) -> None:
			if self.__count__ == 0:
				self.__rwlock__.acquire_writer()

			self.__count__ += 1

		def release(self) -> None:
			if self.__count__ == 1:
				self.__rwlock__.release_writer()

			if self.__count__ > 0:
				self.__count__ -= 1

	def __init__(self):
		self.__mutex__: multiprocessing.synchronize.RLock = multiprocessing.RLock()
		self.__readers_active__ = multiprocessing.Value('Q', 0)
		self.__writers_pending__ = multiprocessing.Value('Q', 0)
		self.__writer_active__ = multiprocessing.Value('B', 0)
		self.__condition__ = multiprocessing.Condition(self.__mutex__)
		self.__process_local_readers__: list[int] = []
		self.__process_local_writers__: list[int] = []

	def __del__(self):
		tid: int = threading.current_thread().native_id

		while tid in self.__process_local_readers__:
			self.release_reader()

		while tid in self.__process_local_writers__:
			self.release_writer()

	def acquire_reader(self) -> None:
		self.__mutex__.acquire()

		try:
			while self.__writers_pending__.value > 0 or self.__writer_active__.value == 1:
				self.__condition__.wait()

			with self.__readers_active__.get_lock():
				self.__readers_active__.value += 1

			self.__process_local_readers__.append(threading.current_thread().native_id)
		except (SystemExit, KeyboardInterrupt) as e:
			raise e
		finally:
			self.__mutex__.release()

	def release_reader(self) -> None:
		tid: int = threading.current_thread().native_id

		if tid not in self.__process_local_readers__:
			return

		self.__mutex__.acquire()

		try:
			with self.__readers_active__.get_lock():
				self.__readers_active__.value -= 1

			if self.__readers_active__.value == 0:
				self.__condition__.notify()

			self.__process_local_readers__.remove(tid)
		except (SystemExit, KeyboardInterrupt) as e:
			raise e
		finally:
			self.__mutex__.release()

	def acquire_writer(self) -> None:
		self.__mutex__.acquire()

		try:
			with self.__writers_pending__.get_lock():
				self.__writers_pending__.value += 1

			while self.__readers_active__.value > 0 or self.__writer_active__.value == 1:
				self.__condition__.wait()

			with self.__writers_pending__.get_lock():
				self.__writers_pending__.value -= 1

			with self.__writer_active__.get_lock():
				self.__writer_active__.value = 1

			self.__process_local_writers__.append(threading.current_thread().native_id)
		except (SystemExit, KeyboardInterrupt) as e:
			raise e
		finally:
			self.__mutex__.release()

	def release_writer(self) -> None:
		tid: int = threading.current_thread().native_id

		if tid not in self.__process_local_writers__:
			return

		self.__mutex__.acquire()

		try:
			with self.__writer_active__.get_lock():
				self.__writer_active__.value = 0

			self.__condition__.notify()
			self.__process_local_writers__.remove(tid)
		except (SystemExit, KeyboardInterrupt) as e:
			raise e
		finally:
			self.__mutex__.release()

	@property
	def readers(self) -> tuple[int, ...]:
		return tuple(self.__process_local_readers__)

	@property
	def writers(self) -> tuple[int, ...]:
		return tuple(self.__process_local_writers__)

	@property
	def reader_lock(self) -> ReaderWriterLock.ReaderLock:
		return ReaderWriterLock.ReaderLock(self)

	@property
	def writer_lock(self) -> ReaderWriterLock.WriterLock:
		return ReaderWriterLock.WriterLock(self)


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
