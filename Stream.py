from __future__ import annotations

import io
import sys
import typing
import math
import zlib
import dill
import pickle
import threading
import multiprocessing


class StreamError(IOError):
	pass


class StreamFullError(StreamError):
	pass


class StreamEmptyError(StreamError):
	pass


class Stream(io.BufferedIOBase):
	"""
	[Stream(io.BufferedIOBase)] - Base class for CustomMethodsVI Streams
	"""

	def __init__(self):
		"""
		[Stream(io.BufferedIOBase)] - Base class for CustomMethodsVI Streams
		- Constructor -
		"""

		self.__state__: bool = True
		self.__pipes__: dict[io.BufferedIOBase, bool] = {}
		self.__buffer_writer__: list[typing.Callable] = []
		self.__buffer_reader__: list[typing.Callable] = []

	def __enter__(self) -> Stream:
		return self

	def __exit__(self, exc_type, exc_val: typing.Any, exc_tb) -> None:
		if self.__state__:
			self.close()

	def __del__(self) -> None:
		if self.__state__:
			self.close()

	def __eq__(self, other) -> bool:
		return type(other) is type(self) and id(other) == id(self)

	def __hash__(self) -> int:
		return id(self)

	def __iter__(self) -> Stream:
		return self

	def __next__(self) -> typing.Any:
		"""
		Alias for 'Stream::read(1)'
		:return: (ANY) The read item
		:raises StopIteration: If the stream is not seekable or the stream is exhausted
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		if not self.seekable():
			raise StopIteration

		pos: int = self.tell()
		self.seek(0, 2)
		end: int = self.tell()
		self.seek(pos, 0)

		if pos >= end:
			raise StopIteration

		return self.read(1)

	def __reader_stack__(self, __data: tuple[typing.Any, ...]) -> typing.Any:
		"""
		INTERNAL METHOD; DO NOT USE
		Executes the reader callback stack on read data
		:param __data: (tuple[ANY]) The input data to transform
		:return: (ANY) The resulting data
		"""

		for callback in self.__buffer_reader__:
			if callable(callback):
				__data = callback(__data)

		return __data

	def __writer_stack__(self, __object: typing.Any) -> typing.Any:
		"""
		INTERNAL METHOD; DO NOT USE
		Executes the reader callback stack on read data
		:param __object: (ANY) The input object to transform
		:return: (ANY) The resulting object
		"""

		for callback in self.__buffer_writer__:
			if callable(callback):
				__object = callback(__object)

		return __object

	def __auto_flush__(self, ignore_invalid: bool = False) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Flushes internal buffer to all connected auto-pipes
		:param ignore_invalid: (bool) Whether to ignore closed or non-writable streams
		:return: (None)
		"""

		targets: tuple[io.BufferedIOBase, ...] = tuple(pipe for pipe, auto in self.__pipes__.items() if auto)

		if len(targets) == 0:
			return

		for data in self.read(...):
			for pipe in targets:
				if pipe.closed and not ignore_invalid:
					raise BrokenPipeError(f'Pipe \'{pipe}\' is closed')
				elif not pipe.writable() and not ignore_invalid:
					raise BrokenPipeError(f'Pipe \'{pipe}\' is not writable')
				elif not pipe.closed and pipe.writable():
					pipe.write(data)

	def close(self) -> None:
		"""
		Closes the stream
		:return: (None)
		:raises StreamError: If the stream is already closed
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')

		self.__state__ = False

	def readable(self) -> bool:
		"""
		Gets if this stream can be read from
		:return: (bool) Readableness
		"""

		return self.__state__

	def writable(self) -> bool:
		"""
		Gets if this stream can be written to
		:return: (bool) Writableness
		"""

		return self.__state__

	def seekable(self) -> bool:
		"""
		Gets if this stream can seek cursor position
		:return: (bool) Seekableness
		"""

		return False

	def pipe(self, *pipes: io.IOBase) -> Stream:
		"""
		Creates a link between this pipe (src) and the specified pipes (*dst)
		Use 'Stream::flush' to move data from this stream to all linked pipes
		:param pipes: (*io.BufferedIOBase) The pipes to link with
		:return: (Stream) This instance
		:raises StreamError: If this stream is closed
		:raises TypeError: If one of the specified pipes is not an 'io.BufferedIOBase' instance
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not all(isinstance(x, io.IOBase) for x in pipes):
			raise TypeError('Specified stream is not an \'io.BufferedIOBase\'')

		self.__pipes__.update({pipe: False for pipe in pipes})
		return self

	def autopipe(self, *pipes: io.BufferedIOBase, ignore_invalid: bool = False):
		"""
		Creates a link between this pipe (src) and the specified pipes (*dst)
		Data from this stream is automatically flushed to all linked auto pipes
		:param pipes: (*io.BufferedIOBase) The pipes to link with
		:param ignore_invalid: (bool) Whether to ignore closed or non-writable streams
		:return: (Stream) This instance
		:raises StreamError: If this stream is closed
		:raises TypeError: If one of the specified pipes is not an 'io.BufferedIOBase' instance
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not all(isinstance(x, io.BufferedIOBase) for x in pipes):
			raise TypeError('Specified stream is not an \'io.BufferedIOBase\'')

		self.__pipes__.update({pipe: True for pipe in pipes})
		self.__auto_flush__(ignore_invalid)
		return self

	def del_pipe(self, *pipes: io.BufferedIOBase) -> Stream:
		"""
		Destroys a link between this pipe and the specified pipes
		:param pipes: (*io.BufferedIOBase)
		:return: (Stream) This instance
		:raises StreamError: If this stream is closed
		:raises TypeError: If one of the specified pipes is not an 'io.BufferedIOBase' instance
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not all(isinstance(x, io.BufferedIOBase) for x in pipes):
			raise TypeError('Specified stream is not an \'io.BufferedIOBase\'')

		for pipe in pipes:
			if pipe in self.__pipes__:
				del self.__pipes__[pipe]

		return self

	def flush(self, ignore_invalid: bool = False) -> Stream:
		"""
		Flushes the internal buffer, clearing all contents
		If connected to another stream via 'Stream::pipe', contents are read from this stream, duplicated, and written to each connected stream
		:param ignore_invalid: (bool) Whether to ignore closed or non-writable streams
		:return: (Stream) This instance
		:raises StreamError: If this stream is closed
		:raises BrokenPipeError: If 'ignore_invalid' is false and at least one pipe is non-writable or closed
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')

		if self.readable():
			for data in self.read(...):
				for pipe in self.__pipes__:
					if pipe.closed and not ignore_invalid:
						raise BrokenPipeError(f'Pipe \'{pipe}\' is closed')
					elif not pipe.writable() and not ignore_invalid:
						raise BrokenPipeError(f'Pipe \'{pipe}\' is not writable')
					elif not pipe.closed and pipe.writable():
						pipe.write(data)

		return self

	@property
	def closed(self) -> bool:
		return not self.__state__


class FileStream(Stream):
	"""
	[FileStream(Stream)] - Stream for file IO
	"""

	def __init__(self, path: str, mode: str, encoding: str = 'utf-8'):
		"""
		[FileStream(Stream)] - Stream for file IO
		- Constructor -
		:param path: (str) The filepath
		:param mode: (str) The stream IO mode
		:param encoding: (str) For non-binary streams, the encoding to use
		"""

		super().__init__()
		self.__stream__ = open(str(path), mode, encoding=None if 'b' in mode else encoding)
		self.__filepath__: str = str(path)

	def __len__(self) -> int:
		"""
		Gets the number of remaining characters to read
		No read operation is performed
		:return: (int) Number of remaining characters
		"""

		cursor = self.tell()
		self.seek(0, 2)
		size = self.tell()
		self.seek(cursor, 0)
		return size - cursor

	def close(self) -> None:
		super().close()
		self.__stream__.close()

	def readable(self) -> bool:
		return self.__state__ and self.__stream__.readable()

	def writable(self) -> bool:
		return self.__state__ and self.__stream__.writable()

	def seekable(self) -> bool:
		return self.__state__ and self.__stream__.seekable()

	def seek(self, __offset: int, __whence: int = ...) -> int:
		"""
		Moves the stream cursor
		:param __offset: The amount to move the cursor
		:param __whence: 0 - Seek relative to beginning of file<br/>1 - Seek relative to current position<br/>2 - Seek relative to end of file
		:return: (int) The new cursor position relative to file beginning
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.seekable():
			raise StreamError('Stream is not seekable')

		return self.__stream__.seek(__offset, __whence)

	def tell(self) -> int:
		"""
		Gets the current stream cursor relative to beginning of file
		:return: (int) Current cursorness
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')

		return self.__stream__.tell()

	def cursor(self, offset: typing.Optional[int] = ..., whence: typing.Optional[int] = ...) -> int:
		"""
		Sets or gets the current stream cursor position
		:param offset: (int?) If supplied, seeks to the specified position
		:param whence: (int?) If supplied, sets the offset for 'seek'; cannot be supplied without 'offset'
		:return: (int) The current position if neither 'offset' nor 'whence' is supplied, otherwise the new absolute cursor position
		:raises StreamError: If this stream is closed or not seekable
		:raises TypeError: If 'whence' is supplied without 'offset'
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')

		if offset is ... and whence is ...:
			return self.__stream__.tell()
		elif offset is ... and whence is not ...:
			raise TypeError('Expected \'offset\' alongside \'whence\'')
		elif not self.seekable():
			raise StreamError('Stream is not seekable')
		else:
			return self.__stream__.seek(offset, whence)

	def truncate(self, __size: typing.Optional[int] = ...) -> int:
		"""
		Truncates the file to either the current cursor position if '__size' is not specified otherwise to '__size' bytes
		:param __size: (int?) The new size of the file in bytes
		:return: (int) The new file size in bytes
		:raises StreamError: If this stream is closed
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')

		return self.__stream__.truncate(None if __size is None or __size is ... else int(__size))

	def size(self) -> int:
		"""
		Gets the total size of the file contents
		No read operation is performed
		:return: (int) Total size of contents in chars
		:raises StreamError: If this stream is closed
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')

		cursor = self.tell()
		self.seek(0, 2)
		size = self.tell()
		self.seek(cursor, 0)
		return size

	def read(self, __size: typing.Optional[int] = ...) -> bytes | str:
		"""
		Reads '__size' characters from the file
		:param __size: (int?) The number of characters to read or all if not supplied
		:return: (bytes | str) The read data
		:raises StreamError: If this stream is closed or not readable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		return self.__stream__.read(None if __size is None or __size is ... else int(__size))

	def peek(self, __size: typing.Optional[int] = ...) -> bytes | str:
		"""
		Reads '__size' characters from the file without moving the cursor
		:param __size: (int?) The number of characters to read or all if not supplied
		:return: (bytes | str) The read data
		:raises StreamError: If this stream is closed or not readable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		cursor: int = self.tell()
		data: bytes | str = self.__stream__.read(None if __size is None or __size is ... else int(__size))
		self.seek(cursor, 0)
		return data

	def readline(self, __size: typing.Optional[int] = ...) -> bytes | str:
		"""
		Reads one line from the file reading at most '__size' bytes if supplied
		:param __size: (int?) The number of characters to read or all until line delimiter if not supplied
		:return: (bytes | str) The read data
		:raises StreamError: If this stream is closed or not readable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		return self.__stream__.readline(None if __size is None or __size is ... else int(__size))

	def peekline(self, __size: typing.Optional[int] = ...) -> bytes | str:
		"""
		Reads one line from the file without moving the cursor, reading at most '__size' bytes if supplied
		:param __size: (int?) The number of characters to read or all until line delimiter if not supplied
		:return: (bytes | str) The read data
		:raises StreamError: If this stream is closed or not readable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		cursor: int = self.tell()
		data: bytes | str = self.__stream__.readline(None if __size is None or __size is ... else int(__size))
		self.seek(cursor, 0)
		return data

	def readlines(self, __hint: int = ...) -> list[bytes | str]:
		"""
		Reads multiple line from the file stopping if '__hint' is supplied and the size of all read lines exceeds this amount
		:param __hint: (int?) A hint indicating the number of characters to read
		:return: (list[bytes | str]) The read data
		:raises StreamError: If this stream is closed or not readable
		"""
		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		return self.__stream__.readlines(None if __hint is None or __hint is ... else int(__hint))

	def write(self, __buffer: str | bytes) -> FileStream:
		"""
		Writes data to the file
		:param __buffer: (str | bytes) The data to write
		:return: (FileStream) This instance
		:raises StreamError: If this stream is closed or not writable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.writable():
			raise StreamError('Stream is not writable')

		self.__stream__.write(__buffer)
		return self

	def writelines(self, __lines: typing.Iterable[str | bytes]) -> FileStream:
		"""
		Writes multiple lines to the file
		:param __lines: (ITERABLE[str | bytes]) The data to write
		:return: (FileStream) This instance
		:raises StreamError: If this stream is closed or not writable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.writable():
			raise StreamError('Stream is not writable')

		self.__stream__.writelines(__lines)
		return self

	def reopen(self, mode: str, encoding: str = 'utf8') -> FileStream:
		"""
		Closes and reopens the underlying file stream
		:param mode: (str) The new file mode
		:param encoding: (str) For non-binary modes, the new encoding
		:return: (FileStream) This instance
		"""

		if self.__state__:
			self.close()

		self.__stream__ = open(self.__filepath__, mode, encoding=encoding)
		self.__state__ = True
		return self

	def flush(self, ignore_invalid: bool = False) -> FileStream:
		"""
		Flushes the underlying stream; Writes queued data to connected pipes
		:return: (FileStream) This instance
		:raises StreamError: If this stream is closed
		"""
		if not self.__state__:
			raise StreamError('Stream is closed')

		self.__stream__.flush()
		super().flush(ignore_invalid)
		return self


class ListStream(Stream):
	"""
	[ListStream(Stream)] - Basic FIFO stream using a list for it's internal buffer
	"""

	def __init__(self, max_length: int = -1):
		"""
		[ListStream(Stream)] - Basic FIFO stream using a list for it's internal buffer
		- Constructor -
		:param max_length: (int) The maximum length (in number of items) of this stream
		"""

		super().__init__()
		self.__buffer__: list[typing.Any] = []
		self.__max_len__: int = int(max_length)

	def __len__(self) -> int:
		"""
		Returns the length of the internal buffer
		:return: (int) Lengthness
		"""

		return len(self.__buffer__)

	def empty(self) -> bool:
		"""
		Checks if the underlying buffer is empty
		:return: (bool) Emptiness
		"""

		return len(self.__buffer__) == 0

	def readinto(self, __buffer: io.IOBase | typing.IO | bytearray | list | set) -> int:
		"""
		Reads all contents from this stream into the specified buffer
		:param __buffer: (io.IOBase | typing.IO | bytearray | list | set) The buffer to write to
		:return: (int) The number of elements written
		:raises StreamError: If this stream is closed or not readable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		count: int = 0

		if isinstance(__buffer, io.IOBase) or hasattr(__buffer, 'write'):

			try:
				for data in self.read():
					__buffer.write(data)
			except StreamFullError:
				pass

		elif isinstance(__buffer, bytearray):

			for data in self.read():
				__buffer.append(data)

		elif isinstance(__buffer, list):
			__buffer.extend(self.read())

		elif isinstance(__buffer, set):
			__buffer.union(self.read())

		else:
			raise TypeError(f'Cannot \'readinto\' non-writable object \'{type(__buffer).__name__}\'')

		return count

	def read(self, __size: typing.Optional[int] = ...) -> tuple[typing.Any, ...] | typing.Any:
		"""
		Reads data from the internal queue
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (tuple[ANY]) The stored data
		:raises StreamError: If this stream is closed or not readable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		count: int = len(self.__buffer__) if __size is ... or __size is None or int(__size) < 0 else int(__size)
		temp: tuple[typing.Any, ...] = tuple(self.__buffer__[:count])
		del self.__buffer__[:count]
		return self.__reader_stack__(temp)

	def peek(self, __size: typing.Optional[int] = ...) -> tuple[typing.Any, ...] | typing.Any:
		"""
		Reads data from the internal queue without removing it
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (tuple[ANY]) The stored data
		:raises StreamError: If this stream is closed or not readable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		count: int = len(self.__buffer__) if __size is ... or __size is None or int(__size) < 0 else int(__size)
		temp: tuple[typing.Any, ...] = tuple(self.__buffer__[:count])
		return self.__reader_stack__(temp)

	def write(self, __object: typing.Any, *, ignore_invalid = False) -> ListStream:
		"""
		Writes an object to the internal queue
		:param __object: (ANY) The object to write
		:param ignore_invalid: (bool) Whether to ignore closed or non-writable streams
		:return: (ListStream) This instance
		:raises StreamError: If this stream is closed or not writable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.writable():
			raise StreamError('Stream is not writable')

		if self.__max_len__ < 0 or len(self.__buffer__) < self.__max_len__:
			self.__buffer__.append(self.__writer_stack__(__object))
			self.__auto_flush__(ignore_invalid)
			return self

		raise StreamFullError('Stream is full')

	def writefrom(self, __buffer: typing.Iterable | typing.IO | io.BufferedIOBase, __size: typing.Optional[int] = ..., *, ignore_invalid = False) -> ListStream:
		"""
		Reads all contents from the specified buffer into this stream
		:param __buffer: (ITERABLE[ANY] | typing.IO | io.BufferedIOBase) The buffer to read from
		:param __size: (int?) The number of elements to write
		:param ignore_invalid: (bool) Whether to ignore closed or non-writable streams
		:return: (ListStream) This instance
		:raises StreamError: If this stream is closed or not writable or '__buffer' is closed or not readable
		:raises StreamFullError: If this stream becomes full
		:raises TypeError: If '__buffer' is not a supported stream nor an iterable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.writable():
			raise StreamError('Stream is not writable')

		if isinstance(__buffer, (typing.IO, io.BufferedIOBase, io.IOBase)):
			if __buffer.closed:
				raise StreamError('Source buffer is closed')
			elif not __buffer.readable():
				raise StreamError('Source buffer is not readable')

			try:
				count: int = 0

				while self.__max_len__ < 0 or len(self.__buffer__) < self.__max_len__:
					count += 1
					self.write(__buffer.read(1))
					self.__auto_flush__(ignore_invalid)

					if __size is not ... and __size is not None and count >= __size:
						break
			except StopIteration:
				pass

			return self

		elif isinstance(__buffer, typing.Iterable):
			iterator = iter(__buffer)

			try:
				while True:
					if 0 <= self.__max_len__ <= len(self.__buffer__):
						raise StreamFullError('Stream is full')

					self.write(next(iterator))
					self.__auto_flush__(ignore_invalid)
			except StopIteration:
				pass

			return self

		else:
			raise TypeError('Source is neither a stream nor an iterable')


class OrderedStream(ListStream):
	"""
	[OrderedStream(ListStream)] - A stream allowing for LIFO capabilities
	"""

	def __init__(self, max_length: int = -1, fifo: bool = True):
		"""
		[OrderedStream(ListStream)] - A stream allowing for LIFO capabilities
		- Constructor -
		:param max_length: (int) The maximum length (in number of items) of this stream
		:param fifo: (bool) Whether this stream is FIFO or LIFO
		"""

		super().__init__(max_length)
		self.__fifo__: bool = bool(fifo)

	def read(self, __size: typing.Optional[int] = ...) -> tuple[typing.Any, ...] | typing.Any:
		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		count: int = len(self.__buffer__) if __size is ... or __size is None or int(__size) < 0 else int(__size)
		temp: tuple[typing.Any, ...] = tuple(self.__buffer__[:count] if self.__fifo__ else reversed(self.__buffer__[-count:]))

		if self.__fifo__:
			del self.__buffer__[:count]
		else:
			del self.__buffer__[-count:]

		return self.__reader_stack__(temp)

	def peek(self, __size: typing.Optional[int] = ...) -> tuple[typing.Any, ...] | typing.Any:
		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		count: int = len(self.__buffer__) if __size is ... or __size is None or int(__size) < 0 else int(__size)
		temp: tuple[typing.Any, ...] = tuple(self.__buffer__[:count] if self.__fifo__ else reversed(self.__buffer__[-count:]))
		return self.__reader_stack__(temp)

	@property
	def is_fifo(self) -> bool:
		"""
		Whether this stream is FIFO
		:return: (bool) FIFOness
		"""

		return self.__fifo__

	@property
	def is_lifo(self) -> bool:
		"""
		Whether this stream is LIFO
		:return: (bool) LIFOness
		"""

		return not self.__fifo__


class TypedStream(OrderedStream):
	"""
	[TypedStream(OrderedStream)] - Stream limiting stored items to instances of specified types
	"""

	def __init__(self, cls: type | typing.Iterable[type], max_length: int = -1, fifo: bool = True):
		"""
		[TypedStream(OrderedStream)] - Stream limiting stored items to instances of specified types
		- Constructor -
		:param cls: (type | tuple[type]) The types to allow
		:param max_length: (int) The maximum length (in number of items) of this stream
		:param fifo: (bool) Whether this stream is FIFO or LIFO
		:raises AssertionError: If any value in 'cls' is not a type
		"""

		super().__init__(max_length, fifo)
		self.__cls__: tuple[type, ...] = tuple(cls) if isinstance(cls, typing.Iterable) else (cls,)
		assert all(type(c) is type for c in self.__cls__), 'Got non-type object in cls'

	def write(self, __object: typing.Any, *, ignore_invalid = False) -> TypedStream:
		"""
		Writes an object to the internal queue
		:param __object: (ANY) The object to write
		:param ignore_invalid: (bool) Whether to ignore closed or non-writable streams
		:return: (ListStream) This instance
		:raises StreamError: If this stream is closed or not writable
		:raises AssertionError: If the object is not an instance of a whitelisted type
		"""

		assert isinstance(__object, self.__cls__), f'Object of type  \'{type(__object)}\' does not match one of the specified type(s):\n  {"\n  ".join(str(c) for c in self.__cls__)}'
		super().write(__object)
		return self


class ByteStream(TypedStream, io.BytesIO):
	"""
	[ByteStream(TypedStream, io.BytesIO)] - Stream designed for storing only byte-strings
	"""

	@staticmethod
	def __buffer_writer_cb__(__object: bytes | bytearray | int | str) -> bytes:
		"""
		INTERNAL METHOD; DO NOT USE
		Converts data to write into a bytes object
		:param __object: (ANY) The object being written
		:return: (bytes) The resulting bytes object
		"""

		if type(__object) is int:
			byte_count: int = max(1, math.ceil((__object.bit_length()) / 8))
			return (__object if __object >= 0 else int(pow(2, byte_count * 8)) + __object).to_bytes(byte_count, sys.byteorder, signed=False)
		elif type(__object) is str:
			return __object.encode()
		else:
			return bytes(__object)

	def __init__(self, max_length: int = -1, fifo: bool = True):
		"""
		[ByteStream(TypedStream, io.BytesIO)] - Stream designed for storing only byte-strings
		- Constructor -
		:param max_length: (int) The maximum length (in number of items) of this stream
		:param fifo: (bool) Whether this stream is FIFO or LIFO
		"""

		super().__init__((bytes, bytearray, int, str), max_length, fifo)
		self.__buffer_writer__.append(ByteStream.__buffer_writer_cb__)
		self.__buffer_reader__.append(b''.join)

	def read(self, __size: typing.Optional[int] = ...) -> bytes:
		"""
		Reads data from the internal queue
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (bytes) The stored data
		:raises StreamError: If this stream is closed or not readable
		"""

		return super().read(__size)

	def peek(self, __size: typing.Optional[int] = ...) -> bytes:
		"""
		Reads data from the internal queue without removing it
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (bytes) The stored data
		:raises StreamError: If this stream is closed or not readable
		"""

		return super().peek(__size)


class StringStream(OrderedStream):
	"""
	[StringStream(OrderedStream)] - Stream designed for storing only strings
	"""

	def __init__(self, max_length: int = -1, fifo: bool = True):
		"""
		[StringStream(OrderedStream)] - Stream designed for storing only strings
		- Constructor -
		:param max_length: (int) The maximum length (in number of items) of this stream
		:param fifo: (bool) Whether this stream is FIFO or LIFO
		"""

		super().__init__(max_length, fifo)
		self.__buffer_writer__.append(str)
		self.__buffer_reader__.append(''.join)

	def read(self, __size: typing.Optional[int] = ...) -> str:
		"""
		Reads data from the internal queue
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (str) The stored data
		:raises StreamError: If this stream is closed or not readable
		"""

		return super().read(__size)

	def peek(self, __size: typing.Optional[int] = ...) -> str:
		"""
		Reads data from the internal queue without removing it
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (str) The stored data
		:raises StreamError: If this stream is closed or not readable
		"""

		return super().peek(__size)


class ZLibStream(ByteStream):
	"""
	[ZLibStream(ByteStream)] - Stream designed for ZLIB compressing arbitrary byte-strings
	"""

	def __init__(self, compression_ratio: int = zlib.Z_DEFAULT_COMPRESSION, max_length: int = -1, fifo: bool = True):
		"""
		[ZLibStream(ByteStream)] - Stream designed for ZLIB compressing arbitrary byte-strings
		:param compression_ratio: (int) The ZLIB compression ratio
		:param max_length: (int) The maximum length (in number of items) of this stream
		:param fifo: (bool) Whether this stream is FIFO or LIFO
		"""

		super().__init__(max_length, fifo)
		self.__compression__: int = int(compression_ratio)

	def read(self, __size: typing.Optional[int] = ...) -> bytes:
		"""
		Reads data from the internal queue
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (bytes) The stored data compressed with ZLIB
		:raises StreamError: If this stream is closed or not readable
		"""

		return zlib.compress(super().read(__size), self.__compression__)

	def peek(self, __size: typing.Optional[int] = ...) -> bytes:
		"""
		Reads data from the internal queue without removing it
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (bytes) The stored data compressed with ZLIB
		:raises StreamError: If this stream is closed or not readable
		"""

		return zlib.compress(super().peek(__size), self.__compression__)


class PickleStream(OrderedStream):
	"""
	[PickleStream(OrderedStream)] - Stream that serializes all data with pickle during write
	"""

	@staticmethod
	def __buffer_reader_cb__(__data: tuple[bytes, ...]) -> typing.Any:
		"""
		INTERNAL METHOD; DO NOT USE
		Deserializes data from the internal queue
		:param __data: (ANY) The data being read
		:return: (bytes) The resulting deserialized data
		"""

		return tuple(pickle.loads(x) for x in __data)

	def __init__(self, max_length: int = -1, fifo: bool = True):
		"""
		[PickleStream(OrderedStream)] - Stream that serializes all data with pickle during write
		- Constructor -
		:param max_length: (int) The maximum length (in number of items) of this stream
		:param fifo: (bool) Whether this stream is FIFO or LIFO
		"""

		super().__init__(max_length, fifo)
		self.__buffer_writer__.append(pickle.dumps)
		self.__buffer_reader__.append(PickleStream.__buffer_reader_cb__)

	def readbytes(self, __size: typing.Optional[int] = ...) -> tuple[bytes, ...]:
		"""
		Reads data from the internal queue
		Data is not deserialized first
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (tuple[bytes]) The stored data without deserialization
		:raises StreamError: If this stream is closed or not readable
		"""

		callback: typing.Callable = self.__buffer_reader__.pop(-1)
		data: tuple[bytes, ...] = self.read(__size)
		self.__buffer_reader__.append(callback)
		return data

	def peekbytes(self, __size: typing.Optional[int] = ...) -> tuple[bytes, ...]:
		"""
		Reads data from the internal queue without removing it
		Data is not deserialized first
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (tuple[bytes]) The stored data without deserialization
		:raises StreamError: If this stream is closed or not readable
		"""

		callback: typing.Callable = self.__buffer_reader__.pop(-1)
		data: tuple[bytes, ...] = self.peek(__size)
		self.__buffer_reader__.append(callback)
		return data


class DillStream(OrderedStream):
	"""
	[DillStream(OrderedStream)] - Stream that serializes all data with dill during write
	"""

	@staticmethod
	def __buffer_reader_cb__(__data: tuple[bytes, ...]) -> typing.Any:
		"""
		INTERNAL METHOD; DO NOT USE
		Deserializes data from the internal queue
		:param __data: (ANY) The data being read
		:return: (bytes) The resulting deserialized data
		"""

		return tuple(dill.loads(x) for x in __data)

	def __init__(self, max_length: int = -1, fifo: bool = True):
		"""
		[DillStream(OrderedStream)] - Stream that serializes all data with dill during write
		- Constructor -
		:param max_length: (int) The maximum length (in number of items) of this stream
		:param fifo: (bool) Whether this stream is FIFO or LIFO
		"""

		super().__init__(max_length, fifo)
		self.__buffer_writer__.append(dill.dumps)
		self.__buffer_reader__.append(DillStream.__buffer_reader_cb__)

	def readbytes(self, __size: typing.Optional[int] = ...) -> tuple[bytes, ...]:
		"""
		Reads data from the internal queue
		Data is not deserialized first
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (tuple[bytes]) The stored data without deserialization
		:raises StreamError: If this stream is closed or not readable
		"""

		callback: typing.Callable = self.__buffer_reader__.pop(-1)
		data: tuple[bytes, ...] = self.read(__size)
		self.__buffer_reader__.append(callback)
		return data

	def peekbytes(self, __size: typing.Optional[int] = ...) -> tuple[bytes, ...]:
		"""
		Reads data from the internal queue without removing it
		Data is not deserialized first
		:param __size: (int?) If specified, reads this many items, otherwise reads all data
		:return: (tuple[bytes]) The stored data without deserialization
		:raises StreamError: If this stream is closed or not readable
		"""

		callback: typing.Callable = self.__buffer_reader__.pop(-1)
		data: tuple[bytes, ...] = self.peek(__size)
		self.__buffer_reader__.append(callback)
		return data


class FilteredStream(OrderedStream):
	"""
	[FilteredStream(OrderedStream)] - Stream which applies a filter function to any data being written
	"""

	def __init__(self, __filter: typing.Callable, max_length: int = -1, fifo: bool = True):
		"""
		[FilteredStream(OrderedStream)] - Stream which applies a filter function to any data being written
		- Constructor -
		:param __filter: (CALLABLE) The filter function
		:param max_length: (int) The maximum length (in number of items) of this stream
		:param fifo: (bool) Whether this stream is FIFO or LIFO
		:raises AssertionError: If '__filter' is not callable
		"""

		super().__init__(max_length, fifo)
		assert callable(__filter), 'Filter callback is not callable'
		self.__filter__: typing.Callable = __filter

	def write(self, __object: typing.Any, *, ignore_invalid = False) -> FilteredStream:
		"""
		Writes an object to the internal queue only if the filter returns a value that evaluates to True
		:param __object: (ANY) The object to write
		:param ignore_invalid: (bool) Whether to ignore closed or non-writable streams
		:return: (FilteredStream) This instance
		:raises StreamError: If this stream is closed or not writable
		"""

		if bool(self.__filter__(__object)):
			super().write(__object)

		return self


class TransformedStream(OrderedStream):
	"""
	[TransformedStream(OrderedStream)] - Stream which applies a transformer function to any data being written
	"""

	def __init__(self, __transformer: typing.Callable, max_length: int = -1, fifo: bool = True):
		"""
		[TransformedStream(OrderedStream)] - Stream which applies a transformer function to any data being written
		- Constructor -
		:param __transformer: (CALLABLE) The transformer function
		:param max_length: (int) The maximum length (in number of items) of this stream
		:param fifo: (bool) Whether this stream is FIFO or LIFO
		:raises AssertionError: If '__transformer' is not callable
		"""

		super().__init__(max_length, fifo)
		assert callable(__transformer), 'Transformer callback is not callable'
		self.__transformer__: typing.Callable = __transformer

	def write(self, __object: typing.Any, *, ignore_invalid = False) -> TransformedStream:
		"""
		Writes an object to the internal queue only if the filter returns a value that evaluates to True
		:param __object: (ANY) The object to write
		:param ignore_invalid: (bool) Whether to ignore closed or non-writable streams
		:return: (FilteredStream) This instance
		:raises StreamError: If this stream is closed or not writable
		"""

		super().write(self.__transformer__(__object))
		return self


class EventedStream(OrderedStream):
	"""
	[EventedStream(OrderedStream)] - Stream which allows binding of callbacks to various stream events
	"""

	NO_THREADING: int = 0
	MULTITHREADING: int = 1
	MULTIPROCESSING: int = 2

	def __init__(self, max_length: int = -1, fifo: bool = True):
		"""
		[EventedStream(OrderedStream)] - Stream which allows binding of callbacks to various stream events
		- Constructor -
		:param max_length: (int) The maximum length (in number of items) of this stream
		:param fifo: (bool) Whether this stream is FIFO or LIFO
		"""

		super().__init__(max_length, fifo)
		self.__callbacks__: dict[str, dict[typing.Callable, int]] = {'write': {}, 'read': {}, 'pipe': {}, 'del_pipe': {}, 'close': {}, 'peek': {}, 'flush': {}}

	def __exec__(self, eid: str, *args, **kwargs) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Executes the callbacks for a specified event ID
		:param eid: (str) The event ID
		:param args: (*ANY) Arguments to call callbacks with
		:param kwargs: (**ANY) Keyword arguments to call callbacks with
		:return: (None)
		"""

		assert eid in self.__callbacks__

		for callback, threaded in self.__callbacks__[eid].items():
			if threaded == EventedStream.NO_THREADING:
				callback(*args, **kwargs)
			elif threaded == EventedStream.MULTITHREADING:
				threading.Thread(target=callback, args=args, kwargs=kwargs).start()
			elif threaded == EventedStream.MULTIPROCESSING:
				multiprocessing.Process(target=callback, args=args, kwargs=kwargs).start()

	def close(self) -> None:
		super().close()
		self.__exec__('close')

	def read(self, __size: typing.Optional[int] = ...) -> tuple[typing.Any, ...]:
		data: tuple[typing.Any, ...] = super().read(__size)
		self.__exec__('read', data)
		return data

	def peek(self, __size: typing.Optional[int] = ...) -> tuple[typing.Any, ...]:
		data: tuple[typing.Any, ...] = super().peek(__size)
		self.__exec__('peek', data)
		return data

	def write(self, __object: typing.Any, *, ignore_invalid = False) -> EventedStream:
		super().write(__object)
		self.__exec__('write', __object)
		return self

	def pipe(self, *pipes: io.BufferedIOBase) -> EventedStream:
		super().pipe(*pipes)
		self.__exec__('pipe', *pipes)
		return self

	def del_pipe(self, *pipes: io.BufferedIOBase) -> EventedStream:
		super().del_pipe(*pipes)
		self.__exec__('del_pipe', *pipes)
		return self

	def flush(self, ignore_invalid: bool = False) -> EventedStream:
		super().flush(ignore_invalid)
		self.__exec__('flush')
		return self

	def on(self, eid: str, callback: typing.Optional[typing.Callable] = ..., *, threadability: int = NO_THREADING) -> 'None | typing.Callable':
		"""
		Binds a callback to the specified event ID
		Can be used as a decorator
		:param eid: (str) The event ID, one of<br/>
		 . . . . . 'write' - Called when an item is written to this stream<br/>
		 . . . . . 'read' - Called when an item is read from this stream<br/>
		 . . . . . 'peek' - called when an item is peeked from this stream<br/>
		 . . . . . 'pipe' - Called when a stream is connected to this stream (Called once for every pipe to add)<br/>
		 . . . . . 'del_pipe' - Called when a stream is disconnected to this stream (Called once for every pipe to remove)<br/>
		 . . . . . 'flush' - Called when this stream is flushed<br/>
		 . . . . . 'close' - Called when this stream is closed
		:param callback: (CALLABLE?) The callback to bind or None if a decorator
		:param threadability: The threading to use, one of<br/>
		. . . . . 0 - No Threading<br/>
		. . . . . 1 - 'threading.Thread' threads<br/>
		. . . . . 2 - 'multiprocessing.Process' processes
		:return: (None | CALLABLE) The binder if used as a decorator otherwise None
		:raises NameError: If the event ID is not valid
		:raises AssertionError: If the supplied callback is not callable
		"""

		if eid not in self.__callbacks__:
			raise NameError(f'Unexpected event ID, expected one of:\n  {"\n  ".join(self.__callbacks__.keys())}')

		elif callback is None or callback is ...:
			def binder(func: typing.Callable):
				assert callable(func), 'Callback is not callable'
				self.__callbacks__[eid][func] = threadability

			return binder

		else:
			assert callable(callback), 'Callback is not callable'
			self.__callbacks__[eid][callback] = threadability

	def off(self, eid: str, callback: typing.Optional[typing.Callable] = ...) -> None:
		"""
		Unbinds a callback from the specified event ID
		:param eid: (str) The event ID, see 'EventedStream::on' for a list of valid IDs
		:param callback: (CALLABLE?) The callable to unbind, or all if no callback supplied
		:return: (None)
		:raises NameError: If the event ID is not valid
		:raises AssertionError: If the supplied callback is not bound
		"""

		if eid not in self.__callbacks__:
			raise NameError(f'Unexpected event ID, expected one of:\n  {"\n  ".join(self.__callbacks__.keys())}')

		elif callback is None or callback is ...:
			self.__callbacks__[eid].clear()

		else:
			assert callback in self.__callbacks__[eid], 'Specified callback not bound'
			del self.__callbacks__[eid][callback]


class LinqStream:
	"""
	[LinqStream] - Lazy generator mimicking C# LINQ or Java Streams
	"""

	def __init__(self, iterable: typing.Iterable):
		"""
		[LinqStream] - Lazy generator mimicking C# LINQ or Java Streams
		- Constructor -
		:param iterable: (ITERABLE) The source iterable
		"""

		self.__functions__: list[typing.Callable] = []
		self.__func_purpose__: list[int] = []
		self.__source__: typing.Iterable = iterable

	def filter(self, callback: typing.Callable) -> LinqStream:
		"""
		Filters elements based on this filter function
		:param callback: (CALLABLE) The filter function
		:return: (LinqStream) This instance
		:raises AssertionError: If 'callback' is not callable
		"""

		assert callable(callback), 'Filter is not callable'
		self.__functions__.append(callback)
		self.__func_purpose__.append(0)
		return self

	def transform(self, callback: typing.Callable) -> LinqStream:
		"""
		Transforms elements based on this transform function
		:param callback: (CALLABLE) The transformer function
		:return: (LinqStream) This instance
		:raises AssertionError: If 'callback' is not callable
		"""

		assert callable(callback), 'Transformer is not callable'
		self.__functions__.append(callback)
		self.__func_purpose__.append(1)
		return self

	def count(self) -> int:
		"""
		Executes the generator
		:return: (int) The length of the resulting collection
		"""

		return len(self.collect(tuple))

	def max(self) -> typing.Any:
		"""
		Executes the generator
		:return: (int) The largest value of the resulting collection
		"""

		return max(self.collect())

	def min(self) -> typing.Any:
		"""
		Executes the generator
		:return: (int) The smallest of the resulting collection
		"""

		return min(self.collect())

	def sum(self) -> typing.Any:
		"""
		Executes the generator
		:return: (int) The sum of all elements in the resulting collection
		"""

		return sum(self.collect())

	def sort(self, key: typing.Optional[typing.Callable] = ...) -> LinqStream:
		pass

	def collect(self, iter_type: typing.Optional[type] = ...) -> typing.Iterable | typing.Sized | typing.Generator:
		"""
		Executes the generator
		:param iter_type: (type?) The type of the collection to return
		:return: (ITERABLE) The resulting collection
		"""

		def _generator(src: typing.Iterable, func: typing.Callable, purpose: int):
			if purpose == 0:
				yield from (x for x in src if func(x))
			elif purpose == 1:
				yield from (func(x) for x in src)

		source = self.__source__

		for func, purpose in zip(self.__functions__, self.__func_purpose__):
			source = _generator(source, func, purpose)

		return source if iter_type is None or iter_type is ... else iter_type(source)