from __future__ import annotations

import atexit
import base64
import enum
import multiprocessing
import multiprocessing.connection
import multiprocessing.queues
import multiprocessing.reduction
import multiprocessing.resource_sharer
import multiprocessing.shared_memory
import os
import pickle
import psutil
import queue
import struct
import subprocess
import sys
import tempfile
import time
import typing

from .. import FileSystem
from .. import Stream
from .. import Synchronization
from .. import Wrapper


class FileLockedValue[T](Synchronization.Synchronization.LockUser):
	def __init__(self, initial_value: T, *, lock: Synchronization.Synchronization.LockType_T = ...):
		"""
		Class representing a thread-safe value stored on disk\n
		*Unexpected crashes may prevent the file from being deleted automatically*
		:param initial_value: The initial value
		:param lock: The lock used for mutual exclusion
		"""

		super().__init__(Synchronization.Multiprocessing.ReaderWriterLock() if lock is ... else lock)
		temp_dir: FileSystem.Directory = FileSystem.Directory(tempfile.gettempdir())
		self.__filesocket__: FileSystem.File = temp_dir.file(f'{hex(id(self))}.flv')
		self.__value__: T = initial_value

		if not self.__filesocket__.exists():
			with self.__filesocket__.open('wb') as fstream:
				pickle.dump(initial_value, fstream)
				fstream.write(struct.pack('Q', 1))
				os.fsync(fstream)

	def __del__(self):
		with self.write_lock():
			self.__filesocket__.delete()

	def __enter__(self) -> FileLockedValue[T]:
		return self

	def __exit__(self, exc_type, exc_val, exc_tb) -> None:
		self.close()

	def __setstate__(self, state: dict[str, ...]) -> None:
		self.__filesocket__ = FileSystem.File(state['file'])
		self.__lock__ = state['lock']

		if self.closed:
			raise BrokenPipeError('The pipe has been closed')

		with self.read_lock():
			with self.__filesocket__.open('rb+') as f:
				self.__value__ = pickle.load(f)
				f.seek(-8, 2)
				counter: int = struct.unpack('Q', f.read(8))[0] + 1
				f.seek(-8, 2)
				f.truncate()
				f.write(struct.pack('Q', counter))

	def __getstate__(self) -> dict[str, ...]:
		return {'file': self.__filesocket__.abspath, 'lock': self.lock}

	def close(self) -> None:
		"""
		Closes the file
		"""

		if self.closed:
			return

		with self.write_lock():
			count: int = self.counter - 1

			if count == 0:
				self.__filesocket__.delete()
				return

			with self.__filesocket__.open('ab') as f:
				f.seek(8, 2)
				f.truncate()
				f.write(struct.pack('Q', count))

	def set(self, value: T) -> None:
		"""
		Sets the value and updates file
		:param value: The value to set
		:raise BrokenPipeError: If the pipe is closed
		"""

		with self.write_lock():
			if self.closed:
				raise BrokenPipeError('The pipe has been closed')

			with self.__filesocket__.open('rb+') as fstream:
				fstream.seek(-8, 2)
				count: bytes = fstream.read(8)
				fstream.seek(0, 0)
				fstream.truncate()
				pickle.dump(value, fstream)
				fstream.seek(0, 2)
				fstream.write(count)
				os.fsync(fstream)

			self.__value__ = value

	def get(self) -> T:
		"""
		Gets the value from file
		:raise BrokenPipeError: If the pipe is closed
		:return: The new value
		"""

		with self.read_lock():
			if self.closed:
				raise BrokenPipeError('The pipe has been closed')

			data: bytes = self.__filesocket__.single_read(True)[:-8]

		self.__value__ = pickle.loads(data)
		return self.__value__

	def get_or_default(self, default: T) -> T:
		"""
		Gets the value from file
		:param default: The default value if pipe is closed
		:raise BrokenPipeError: If the pipe is closed
		:return: The new value or 'default'
		"""

		with self.read_lock():
			if self.closed:
				return default

			data: bytes = self.__filesocket__.single_read(True)

		self.__value__ = pickle.loads(data)
		return self.__value__

	@property
	def closed(self) -> bool:
		"""
		:return: Whether the pipe is closed
		"""

		return not self.__filesocket__.exists()

	@property
	def counter(self) -> int:
		"""
		:return: The number of active handles to this file
		"""

		if self.closed:
			return 0

		with self.read_lock():
			with self.__filesocket__.open('rb') as f:
				f.seek(-8, 2)
				data: bytes = f.read(8)
				return struct.unpack('Q', data)[0]

	@property
	def value(self) -> T:
		"""
		:return: The value as last retrieved from file - (call 'get' or 'get_or_default' to update from file)
		"""

		return self.__value__


class ProcessLockedValue[T](Synchronization.Synchronization.LockUser):
	class OperationType(enum.IntEnum):
		DISCON = 0,
		SETVAL = 1,
		GETVAL = 2,

	@staticmethod
	def __memory_share__(initial_value: T, initial_recv: multiprocessing.connection.PipeConnection, share_conn: multiprocessing.Queue[multiprocessing.connection.PipeConnection]) -> None:
		sys.stdout.write('\n')
		connections: list[multiprocessing.connection.PipeConnection | None] = [initial_recv]
		has_closed_connection: bool = False
		value: T = initial_value

		try:
			while len(connections) > 0:
				try:
					hint: int = share_conn.qsize()

					for _ in range(hint):
						new_connection: multiprocessing.connection.PipeConnection = share_conn.get(False, 0)

						if not isinstance(new_connection, (multiprocessing.connection.Connection, multiprocessing.connection.PipeConnection)):
							continue
						elif new_connection.closed or new_connection in connections:
							continue

						connections.append(new_connection)
				except queue.Empty:
					pass

				for i, connection in enumerate(connections):
					if connection.closed:
						has_closed_connection = True
						connections[i] = None
						continue

					instr, *data = connection.recv()

					if instr == ProcessLockedValue.OperationType.DISCON:
						has_closed_connection = True
						connections[i] = None
						connection.send((True, None))
						connection.close()
						print('Discon')
						continue
					elif instr == ProcessLockedValue.OperationType.SETVAL:
						value = data[0]
						connection.send((True, None))
					elif instr == ProcessLockedValue.OperationType.GETVAL:
						connection.send((True, value))
					else:
						connection.send((False, ValueError(f'Invalid instruction - {instr}')))

				if has_closed_connection:
					connections.remove(None)
					has_closed_connection = False

				time.sleep(1e-6)

		except (KeyboardInterrupt, SystemExit):
			pass
		finally:
			print('Done')

	def __init__(self, initial_value: T = ...):
		super().__init__(Synchronization.Multiprocessing.ReaderWriterLock())
		recv, send = multiprocessing.Pipe(True)
		share_conn: multiprocessing.Queue[multiprocessing.connection.PipeConnection] = multiprocessing.Queue()
		prgm: str = f'import base64, {__name__}, pickle, sys; initial_value, recv = pickle.loads(base64.b64decode(sys.argv[1].encode("utf-8"))); {__name__}.ProcessLockedValue.__memory_share__(initial_value, recv);'
		arg_stream: Stream.ByteStream = Stream.ByteStream()
		multiprocessing.reduction.dump((initial_value, recv, share_conn), arg_stream)
		args: str = base64.b64encode(arg_stream.read()).decode('utf-8')
		share_process: subprocess.Popen[str] = subprocess.Popen([sys.executable, '-c', prgm, args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
		atexit.register(self.__del__)
		self.__conn__: multiprocessing.connection.PipeConnection = send
		self.__share_process__: psutil.Process = psutil.Process(share_process.pid)
		self.__share_conn__: multiprocessing.Queue[multiprocessing.connection.PipeConnection] = share_conn
		self.__wrapper_context__: Wrapper.ValueWrapper[T] = ...
		share_process.stdout.readline()

	def __del__(self):
		if self.__conn__.closed:
			return

		self.__emit_await_response__(ProcessLockedValue.OperationType.DISCON)
		self.__conn__.close()
		self.__lock__.__del__()
		self.__lock__ = ...

	def __enter__(self) -> Wrapper.ValueWrapper[T]:
		self.acquire_write_lock()
		self.__wrapper_context__ = Wrapper.ValueWrapper(self.value)
		return self.__wrapper_context__

	def __exit__(self, exc_type, exc_val, exc_tb) -> None:
		self.value = Wrapper.ValueWrapper.get_value(self.__wrapper_context__)
		self.__wrapper_context__ = ...
		self.release_write_lock()

	def __setstate__(self, state: dict[str, ...]) -> None:
		recv, send = multiprocessing.Pipe(True)
		self.__dict__.update(state)
		self.__share_process__ = psutil.Process(state['__share_process__'])
		self.__share_conn__.put(recv)
		self.__conn__ = send

	def __getstate__(self) -> dict[str, ...]:
		data: dict[str, ...] = {k: v for k, v in super().__getstate__().items()}
		del data['__wrapper_context__']
		del data['__conn__']
		data['__share_process__'] = self.__share_process__.pid
		return data

	def __emit_await_response__(self, instruction: enum.IntEnum, *args) -> typing.Any:
		if self.__conn__.closed:
			raise BrokenPipeError('Connection is closed')

		self.__conn__.send((instruction, *args))
		suc, res = self.__conn__.recv()

		if not suc:
			raise res

		return res

	@property
	def value(self) -> T:
		return self.__emit_await_response__(ProcessLockedValue.OperationType.GETVAL)

	@value.setter
	def value(self, value: T) -> None:
		self.__emit_await_response__(ProcessLockedValue.OperationType.SETVAL, value)


__all__: list[str] = ['FileLockedValue', 'ProcessLockedValue']
