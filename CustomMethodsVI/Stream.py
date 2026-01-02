from __future__ import annotations

import collections.abc
import dill
import io
import math
import multiprocessing
import pickle
import sys
import threading
import typing
import zlib

from . import Exceptions
from . import Misc


class StreamError(IOError):
	pass


class StreamFullError(StreamError):
	pass


class StreamEmptyError(StreamError):
	pass


class Stream[T](io.BufferedIOBase):
	"""
	Base class for CustomMethodsVI Streams
	"""

	def __init__(self):
		"""
		Base class for CustomMethodsVI Streams
		- Constructor -
		"""

		self.__state__: bool = True
		self.__pipes__: dict[io.BufferedIOBase, bool] = {}
		self.__buffer_writer__: list[typing.Callable] = []
		self.__buffer_reader__: list[typing.Callable] = []

	def __len__(self) -> int:
		"""
		:return: The number of items remaining in this stream
		"""

		return 0

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

	def __iter__(self) -> Stream[T]:
		return self

	def __next__(self) -> T:
		"""
		Alias for 'Stream::read(1)'
		:return: The read item
		:raises StopIteration: If the stream is not seekable or the stream is exhausted
		:raises StreamError: If stream is closed or not readable
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

	def __reader_stack__(self, __data: tuple[T, ...]) -> T | typing.Iterable[T]:
		"""
		INTERNAL METHOD
		Executes the reader callback stack on read data
		:param __data: The input data to transform
		:return: The resulting data
		"""

		items: list = [__data]

		for callback in self.__buffer_reader__:
			if callable(callback):
				results: list = []

				for data in items:
					results.extend(callback(data))

				items = results

		return items

	def __writer_stack__(self, __object: typing.Any) -> list[T]:
		"""
		INTERNAL METHOD
		Executes the writer callback stack on written data
		:param __object: The input object to transform
		:return: The resulting object
		"""

		items: list = [__object]

		for callback in self.__buffer_writer__:
			if callable(callback):
				results: list = []

				for obj in items:
					results.extend(callback(obj))

				items = results

		return items

	def __auto_flush__(self, ignore_invalid: bool = False) -> None:
		"""
		INTERNAL METHOD
		Flushes internal buffer to all connected auto-pipes
		:param ignore_invalid: Whether to ignore closed or non-writable streams
		:raises BrokenPipeError: If the targeted pipe is closed
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
		:raises StreamError: If the stream is already closed
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')

		self.__state__ = False

	def readable(self) -> bool:
		"""
		:return: Whether this stream can be read from
		"""

		return self.__state__

	def writable(self) -> bool:
		"""
		:return: Whether this stream can be written to
		"""

		return self.__state__

	def seekable(self) -> bool:
		"""
		:return: Whether this stream can seek cursor position
		"""

		return False

	def pipe(self, *pipes: io.IOBase) -> Stream:
		"""
		Creates a link between this pipe (src) and the specified pipes (*dst)
		Use 'Stream::flush' to move data from this stream to all linked pipes
		:param pipes: The pipes to link with
		:return: This instance
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
		:param pipes: The pipes to link with
		:param ignore_invalid: Whether to ignore closed or non-writable streams
		:return: This instance
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
		:param pipes: The pipes to remove
		:return: This instance
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
		:param ignore_invalid: Whether to ignore closed or non-writable streams
		:return: This instance
		:raises StreamError: If this stream is closed
		:raises BrokenPipeError: If 'ignore_invalid' is false and at least one pipe is non-writable or closed
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')

		if self.readable() and len(self) > 0:
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
		"""
		:return: Whether this stream is closed
		"""

		return not self.__state__


class FileStream(Stream[str | bytes]):
	"""
	Stream for file IO
	"""

	def __init__(self, path: str, mode: str, encoding: str = 'utf-8'):
		"""
		Stream for file IO
		- Constructor -
		:param path: The filepath
		:param mode: The stream IO mode
		:param encoding: For non-binary streams, the encoding to use
		:raises InvalidArgumentException: If 'path' is not a string
		:raises InvalidArgumentException: If 'mode' is not a string
		:raises InvalidArgumentException: If 'encoding' is not a string
		"""

		super().__init__()
		Misc.raise_ifn(isinstance(path, str), Exceptions.InvalidArgumentException(FileStream.__init__, 'path', type(path), (str,)))
		Misc.raise_ifn(isinstance(mode, str), Exceptions.InvalidArgumentException(FileStream.__init__, 'mode', type(mode), (str,)))
		Misc.raise_ifn(isinstance(encoding, str), Exceptions.InvalidArgumentException(FileStream.__init__, 'encoding', type(encoding), (str,)))
		self.__stream__ = open(str(path), mode, encoding=None if 'b' in mode else encoding)
		self.__filepath__: str = str(path)

	def __len__(self) -> int:
		"""
		No read operation is performed
		:return: The number of remaining characters to read
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
		:return: The new cursor position relative to file beginning
		:raises StreamError: If stream is closed or not seekable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.seekable():
			raise StreamError('Stream is not seekable')

		return self.__stream__.seek(__offset, __whence)

	def tell(self) -> int:
		"""
		:return: The current stream cursor relative to beginning of file
		:raises StreamError: If stream is closed
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')

		return self.__stream__.tell()

	def cursor(self, offset: typing.Optional[int] = ..., whence: typing.Optional[int] = ...) -> int:
		"""
		Sets or gets the current stream cursor position
		:param offset: If supplied, seeks to the specified position
		:param whence: If supplied, sets the offset for 'seek'; cannot be supplied without 'offset'
		:return: The current position if neither 'offset' nor 'whence' is supplied, otherwise the new absolute cursor position
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
		:param __size: The new size of the file in bytes
		:return: The new file size in bytes
		:raises StreamError: If this stream is closed
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')

		return self.__stream__.truncate(None if __size is None or __size is ... else int(__size))

	def size(self) -> int:
		"""
		No read operation is performed
		:return: The total size of the file contents in bytes
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
		:param __size: The number of characters to read or all if not supplied
		:return: The read data
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
		:param __size: The number of characters to read or all if not supplied
		:return: The read data
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
		:param __size: The number of characters to read or all until line delimiter if not supplied
		:return: The read data
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
		:param __size: The number of characters to read or all until line delimiter if not supplied
		:return: The read data
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
		:param __hint: A hint indicating the number of characters to read
		:return: The read data
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
		:param __buffer: The data to write
		:return: This instance
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
		:param __lines: The data to write
		:return: This instance
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
		:param mode: The new file mode
		:param encoding: For non-binary modes, the new encoding
		:return: This instance
		:raises InvalidArgumentException: If 'mode' is not a string
		:raises InvalidArgumentException: If 'encoding' is not a string
		"""

		Misc.raise_ifn(isinstance(mode, str), Exceptions.InvalidArgumentException(FileStream.reopen, 'mode', type(mode), (str,)))
		Misc.raise_ifn(isinstance(encoding, str), Exceptions.InvalidArgumentException(FileStream.reopen, 'encoding', type(encoding), (str,)))

		if self.__state__:
			self.close()

		self.__stream__ = open(self.__filepath__, mode, encoding=encoding)
		self.__state__ = True
		return self

	def flush(self, ignore_invalid: bool = False) -> FileStream:
		"""
		Flushes the underlying stream; Writes queued data to connected pipes
		:return: This instance
		:raises StreamError: If this stream is closed
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')

		self.__stream__.flush()
		super().flush(ignore_invalid)
		return self

	@property
	def filepath(self) -> str:
		"""
		:return: The filepath this stream points to
		"""

		return self.__filepath__


class ListStream[T](Stream[T]):
	"""
	Basic FIFO stream using a list for its internal buffer
	"""

	def __init__(self, max_length: int = -1):
		"""
		Basic FIFO stream using a list for its internal buffer
		- Constructor -
		:param max_length: The maximum length (in number of items) of this stream or -1 to disable
		:raises InvalidArgumentException: If max length is not an integer
		:raises ValueError: If max length negative and not -1
		"""

		super().__init__()
		Misc.raise_ifn(isinstance(max_length, int), Exceptions.InvalidArgumentException(ListStream.__init__, 'max_length', type(max_length), (int,)))
		Misc.raise_ifn((max_length := int(max_length)) > 0 or max_length == -1, ValueError('Max length cannot be less than 0'))
		self.__buffer__: list[typing.Any] = []
		self.__max_len__: int = int(max_length)

	def __len__(self) -> int:
		"""
		:return: The length of the internal buffer
		"""

		return len(self.__buffer__)

	def __iter__(self) -> typing.Iterator[T]:
		while not self.empty():
			yield self.read(1)

	def empty(self) -> bool:
		"""
		:return: Whether the underlying buffer is empty
		"""

		return len(self.__buffer__) == 0

	def full(self) -> bool:
		"""
		:return: Whether the underlying buffer is full
		"""

		return len(self.__buffer__) == self.__max_len__

	def readinto(self, __buffer: io.IOBase | typing.IO | bytearray | list[T] | set[T]) -> int:
		"""
		Reads all contents from this stream into the specified buffer
		:param __buffer: The buffer to write to
		:return: The number of elements written
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

	def read(self, __size: typing.Optional[int] = ...) -> tuple[T, ...] | T:
		"""
		Reads data from the internal queue
		:param __size: If specified, reads this many items, otherwise reads all data
		:return: A tuple of read elements if more than one otherwise the single element
		:raises StreamError: If this stream is closed or not readable
		:raises StreamEmptyError: If the stream is empty
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		count: int = len(self.__buffer__) if __size is ... or __size is None or int(__size) < 0 else int(__size)
		temp: tuple[typing.Any, ...] = tuple(self.__buffer__[:count])
		del self.__buffer__[:count]
		result: tuple[typing.Any, ...] = tuple((y := self.__reader_stack__(x))[0 if len(y) == 1 else slice(None)] for x in temp)

		if len(result) == 0:
			raise StreamEmptyError('Stream is empty')

		return result[0] if __size == 1 else result

	def peek(self, __size: typing.Optional[int] = ...) -> tuple[T, ...] | T:
		"""
		Reads data from the internal queue without removing it
		:param __size: f specified, reads this many items, otherwise reads all data
		:return: A tuple of read elements if more than one otherwise the single element
		:raises StreamError: If this stream is closed or not readable
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		count: int = len(self.__buffer__) if __size is ... or __size is None or int(__size) < 0 else int(__size)
		temp: tuple[typing.Any, ...] = tuple(self.__buffer__[:count])
		result: tuple[typing.Any, ...] = tuple((y := self.__reader_stack__(x))[0 if len(y) == 1 else slice(None)] for x in temp)
		return result[0] if __size == 1 else result

	def write(self, __object: T, *, ignore_invalid=False) -> ListStream[T]:
		"""
		Writes an object to the internal queue
		:param __object: The object to write
		:param ignore_invalid: Whether to ignore closed or non-writable streams
		:return: This instance
		:raises StreamError: If this stream is closed or not writable
		:raises StreamFullError: If this stream is full
		"""

		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.writable():
			raise StreamError('Stream is not writable')

		if self.__max_len__ < 0 or len(self.__buffer__) < self.__max_len__:
			self.__buffer__.extend(self.__writer_stack__(__object))
			self.__auto_flush__(ignore_invalid)
			return self

		raise StreamFullError('Stream is full')

	def writefrom(self, __buffer: typing.Iterable[T] | typing.IO | io.BufferedIOBase, __size: typing.Optional[int] = ..., *, ignore_invalid=False) -> ListStream[T]:
		"""
		Reads all contents from the specified buffer into this stream
		:param __buffer: The buffer to read from
		:param __size: The number of elements to write
		:param ignore_invalid: Whether to ignore closed or non-writable streams
		:return: This instance
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

	@property
	def max_length(self) -> int:
		"""
		:return: This stream's max length or -1 if not bounded
		"""

		return self.__max_len__


class OrderedStream[T](ListStream[T]):
	"""
	A stream allowing for LIFO capabilities
	"""

	def __init__(self, max_length: int = -1, fifo: bool = True):
		"""
		A stream allowing for LIFO capabilities
		- Constructor -
		:param max_length: The maximum length (in number of items) of this stream
		:param fifo: Whether this stream is FIFO or LIFO
		"""

		super().__init__(max_length)
		self.__fifo__: bool = bool(fifo)

	def read(self, __size: typing.Optional[int] = ...) -> tuple[T, ...] | T:
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

		result: tuple[typing.Any, ...] = tuple((y := self.__reader_stack__(x))[0 if len(y) == 1 else slice(None)] for x in temp)

		if len(result) == 0:
			raise StreamEmptyError('Stream is empty')

		return result[0] if __size == 1 else result

	def peek(self, __size: typing.Optional[int] = ...) -> tuple[T, ...] | T:
		if not self.__state__:
			raise StreamError('Stream is closed')
		elif not self.readable():
			raise StreamError('Stream is not readable')

		count: int = len(self.__buffer__) if __size is ... or __size is None or int(__size) < 0 else int(__size)
		temp: tuple[typing.Any, ...] = tuple(self.__buffer__[:count] if self.__fifo__ else reversed(self.__buffer__[-count:]))
		result: tuple[typing.Any, ...] = tuple((y := self.__reader_stack__(x))[0 if len(y) == 1 else slice(None)] for x in temp)
		return result[0] if __size == 1 else result

	@property
	def is_fifo(self) -> bool:
		"""
		:return: Whether this stream is FIFO
		"""

		return self.__fifo__

	@property
	def is_lifo(self) -> bool:
		"""
		:return: Whether this stream is LIFO
		"""

		return not self.__fifo__


class TypedStream[T](OrderedStream[T]):
	"""
	Stream limiting stored items to instances of specified types
	"""

	def __init__(self, cls: type | typing.Iterable[type], max_length: int = -1, fifo: bool = True):
		"""
		Stream limiting stored items to instances of specified types
		- Constructor -
		:param cls: The type(s) to allow
		:param max_length: The maximum length (in number of items) of this stream
		:param fifo: Whether this stream is FIFO or LIFO
		:raises InvalidArgumentException: If any value in 'cls' is not a type
		"""

		super().__init__(max_length, fifo)
		self.__cls__: tuple[type, ...] = tuple(cls) if isinstance(cls, typing.Iterable) else (cls,)
		Misc.raise_ifn(all(type(c) is type for c in self.__cls__), Exceptions.InvalidArgumentException(TypedStream.__init__, 'cls', type(cls)))

	def write(self, __object: T, *, ignore_invalid = False) -> TypedStream[T]:
		"""
		Writes an object to the internal queue
		:param __object: The object to write
		:param ignore_invalid: Whether to ignore closed or non-writable streams
		:return: This instance
		:raises StreamError: If this stream is closed or not writable
		:raises StreamFullError: If this stream is full
		:raises AssertionError: If the object is not an instance of a whitelisted type
		"""

		assert isinstance(__object, self.__cls__), f'Object of type  \'{type(__object)}\' does not match one of the specified type(s):\n  {"\n  ".join(str(c) for c in self.__cls__)}'
		super().write(__object)
		return self


class ByteStream(TypedStream[bytes | bytearray], io.BytesIO):
	"""
	Stream designed for storing only byte-strings
	"""

	@staticmethod
	def __buffer_writer_cb__(__object: bytes | bytearray | int | str) -> typing.Iterator[int] | typing.Generator[int, None, None]:
		"""
		INTERNAL METHOD
		Converts data to write into a bytes object
		:param __object: The object being written
		:return: The resulting bytes object
		"""

		if isinstance(__object, int):
			byte_count: int = max(1, math.ceil((__object.bit_length()) / 8)) + (__object < 0)
			return iter(__object.to_bytes(byte_count, sys.byteorder, signed=__object < 0))
		elif isinstance(__object, str):
			return iter(__object.encode())
		else:
			return iter(bytes(__object))

	def __init__(self, max_length: int = -1, fifo: bool = True):
		"""
		Stream designed for storing only byte-strings
		- Constructor -
		:param max_length: The maximum length (in number of items) of this stream
		:param fifo: Whether this stream is FIFO or LIFO
		"""

		super().__init__((bytes, bytearray, int, str), max_length, fifo)
		self.__buffer_writer__.append(ByteStream.__buffer_writer_cb__)

	def read(self, __size: typing.Optional[int] = ...) -> bytes:
		"""
		Reads data from the internal queue
		:param __size: If specified, reads this many items, otherwise reads all data
		:return: The read data as a single bytes object
		:raises StreamError: If this stream is closed or not readable
		"""

		data: int | tuple[int, ...] = super().read(__size)
		return data.to_bytes(1) if isinstance(data, int) else bytes(data)

	def peek(self, __size: typing.Optional[int] = ...) -> bytes:
		"""
		Reads data from the internal queue without removing it
		:param __size: If specified, reads this many items, otherwise reads all data
		:return: The read data as a single bytes object
		:raises StreamError: If this stream is closed or not readable
		"""

		data: int | tuple[int, ...] = super().peek(__size)
		return data.to_bytes(1) if isinstance(data, int) else bytes(data)


class BitStream(TypedStream[bytes | bytearray | str | int | bool], io.BytesIO):
	"""
	Stream designed for storing individual bits
	"""

	@staticmethod
	def __buffer_writer_cb__(__object: bytes | bytearray | int | str | bool) -> typing.Iterable[bool]:
		"""
		INTERNAL METHOD
		Converts data to write into bits
		:param __object: The object being written
		:return: The resulting bits
		"""

		if isinstance(__object, bool):
			return (bool(__object),)
		elif isinstance(__object, int):
			bits: list[bool] = []

			for _ in range((__object := int(__object)).bit_length()):
				bits.append(bool(__object & 0b1))
				__object >>= 1

			return reversed(bits)
		elif isinstance(__object, str):
			bytes_: list[bool] = []

			for byte in str(__object).encode():
				bits: list[bool] = []

				for _ in range(8):
					bits.append(bool(byte & 0b1))
					byte >>= 1

				bytes_.extend(reversed(bits))

			return bytes_
		elif isinstance(__object, (bytes, bytearray)):
			bytes_: list[bool] = []

			for byte in bytes(__object):
				bits: list[bool] = []

				for _ in range(8):
					bits.append(bool(byte & 0b1))
					byte >>= 1

				bytes_.extend(reversed(bits))

			return iter(bytes_)
		else:
			raise TypeError()

	def __init__(self, max_length: int = -1, fifo: bool = True, pack: bool = True):
		"""
		Stream designed for storing individual bits
		- Constructor -
		:param max_length: The maximum length (in number of items) of this stream
		:param fifo: Whether this stream is FIFO or LIFO
		:param pack: Whether to read bits packed into bytes or read individual bits
		"""

		super().__init__((bool, int, bytes, bytearray, str), max_length, fifo)
		self.__buffer_writer__.append(BitStream.__buffer_writer_cb__)
		self.__packed__: bool = bool(pack)

	def write_padded(self, data: bytes | bytearray | int | str | bool, size: int, pad_bit: bool = False) -> BitStream:
		"""
		Writes an object to the internal queue
		:param data: The bit or bytes to write
		:param size: The number of leading bits to pad
		:param pad_bit: The bit to pad with
		:return: This instance
		:raises StreamError: If this stream is closed or not writable
		:raises StreamFullError: If this stream is full
		:raises AssertionError: If the object is not an instance of a whitelisted type
		:raises ValueError: If the number of bits in 'data' exceeds 'size'
		"""

		bits: list[bool] = list(self.__buffer_writer_cb__(data))

		if len(bits) > size:
			raise ValueError('Object bit length exceeded size')

		while len(bits) < size:
			bits.insert(0, bool(pad_bit))

		self.writefrom(bits)
		return self

	def read(self, __size: typing.Optional[int] = ...) -> bytes | bool | tuple[bool, ...]:
		"""
		Reads data from the internal queue
		:param __size: If specified, reads this many items, otherwise reads all data
		:return: The read bits as a single bytes object
		:raises StreamError: If this stream is closed or not readable
		"""

		data: bool | tuple[bool, ...] = super().read(__size)

		if not self.__packed__:
			return data

		packed: list[int] = []

		for i in range(0, len(data), 8):
			byte: int = 0

			for bit in data[i:i+8]:
				byte <<= 1
				byte |= int(bit) & 0b1

			packed.append(byte)

		return bytes(packed)

	def peek(self, __size: typing.Optional[int] = ...) -> bytes | bool | tuple[bool, ...]:
		"""
		Reads data from the internal queue without removing it
		:param __size: If specified, reads this many items, otherwise reads all data
		:return: The read bits as a single bytes object
		:raises StreamError: If this stream is closed or not readable
		"""

		data: bool | tuple[bool, ...] = super().peek(__size)

		if not self.__packed__:
			return data

		packed: list[int] = []

		for i in range(0, len(data), 8):
			byte: int = 0

			for bit in data[i:i + 8]:
				byte <<= 1
				byte |= int(bit) & 0b1

			packed.append(byte)

		return bytes(packed)


class StringStream(OrderedStream[str]):
	"""
	Stream designed for storing only strings
	"""

	def __init__(self, max_length: int = -1, fifo: bool = True):
		"""
		Stream designed for storing only strings
		- Constructor -
		:param max_length: The maximum length (in number of items) of this stream
		:param fifo: Whether this stream is FIFO or LIFO
		"""

		super().__init__(max_length, fifo)
		self.__buffer_writer__.append(str)
		self.__buffer_reader__.append(''.join)

	def read(self, __size: typing.Optional[int] = ...) -> str:
		"""
		Reads data from the internal queue
		:param __size: If specified, reads this many items, otherwise reads all data
		:return: The read data as a single string
		:raises StreamError: If this stream is closed or not readable
		"""

		return ''.join(super().read(__size))

	def peek(self, __size: typing.Optional[int] = ...) -> str:
		"""
		Reads data from the internal queue without removing it
		:param __size: If specified, reads this many items, otherwise reads all data
		:return: The read data as a single string
		:raises StreamError: If this stream is closed or not readable
		"""

		return super().peek(__size)


class ZLibCompressorStream(ByteStream):
	"""
	Stream designed for ZLIB compressing arbitrary byte-strings
	"""

	def __init__(self, compression_ratio: int = zlib.Z_DEFAULT_COMPRESSION, max_length: int = -1, fifo: bool = True):
		"""
		Stream designed for ZLIB compressing arbitrary byte-strings
		:param compression_ratio: The ZLIB compression ratio
		:param max_length:  The maximum length (in number of items) of this stream
		:param fifo:Whether this stream is FIFO or LIFO
		:raises InvalidArgumentException: If 'compression_ratio' is not an integer
		:raises ValueError: If 'compression_ratio' is invalid
		"""

		super().__init__(max_length, fifo)
		Misc.raise_ifn(isinstance(compression_ratio, int), Exceptions.InvalidArgumentException(ZLibCompressorStream.__init__, 'compression_ratio', type(compression_ratio), (int,)))
		Misc.raise_ifn(zlib.Z_NO_COMPRESSION <= (compression_ratio := int(compression_ratio)) <= zlib.Z_BEST_COMPRESSION, ValueError('Invalid compression ratio'))
		self.__compression__: int = int(compression_ratio)

	def read(self, __size: typing.Optional[int] = ...) -> bytes:
		return zlib.compress(super().read(__size), self.__compression__)

	def peek(self, __size: typing.Optional[int] = ...) -> bytes:
		return zlib.compress(super().peek(__size), self.__compression__)


class ZLibDecompressorStream(ByteStream):
	"""
	Stream designed for ZLIB decompressing arbitrary byte-strings
	"""

	def __init__(self, max_length: int = -1, fifo: bool = True):
		"""
		Stream designed for ZLIB decompressing arbitrary byte-strings
		:param max_length: The maximum length (in number of items) of this stream
		:param fifo: Whether this stream is FIFO or LIFO
		"""

		super().__init__(max_length, fifo)

	def read(self, __size: typing.Optional[int] = ...) -> bytes:
		return zlib.decompress(super().read(__size))

	def peek(self, __size: typing.Optional[int] = ...) -> bytes:
		return zlib.decompress(super().peek(__size))


class PickleSerializerStream(ByteStream):
	"""
	Stream that serializes all data with pickle during write
	"""

	def __init__(self, max_length: int = -1, fifo: bool = True, header_size: int = 4):
		"""
		Stream that serializes all data with pickle during write
		- Constructor -
		:param max_length: The maximum length (in number of items) of this stream
		:param fifo: Whether this stream is FIFO or LIFO
		:param header_size: The number of bytes to use for serialized object size
		:raises InvalidArgumentException: If 'header_size' is not an integer
		:raises ValueError: If 'header_size' is smaller than 1
		"""

		super().__init__(max_length, fifo)
		Misc.raise_ifn(isinstance(header_size, int), Exceptions.InvalidArgumentException(PickleSerializerStream.__init__, 'header_size', type(header_size), (int,)))
		Misc.raise_ifn((header_size := int(header_size) < 1), ValueError('Header size cannot be smaller than 1'))
		self.__header_size__: int = int(header_size)
		assert self.__header_size__ > 0, 'Header size must be at least 1'

	def write(self, __object: typing.Any, *, ignore_invalid = False) -> PickleSerializerStream:
		serialized: bytes = pickle.dumps(__object)
		serialized = len(serialized).to_bytes(self.__header_size__, 'big', signed=False) + serialized
		super().write(serialized)
		return self


class PickleDeserializerStream(ByteStream):
	"""
	Stream that deserializes all data with pickle during read
	"""

	def __init__(self, max_length: int = -1, fifo: bool = True, header_size: int = 4):
		"""
		Stream that deserializes all data with pickle during read
		- Constructor -
		:param max_length: The maximum length (in number of items) of this stream
		:param fifo: Whether this stream is FIFO or LIFO
		:param header_size: The number of bytes to use for serialized object size
		:raises InvalidArgumentException: If 'header_size' is not an integer
		:raises ValueError: If 'header_size' is smaller than 1
		"""

		super().__init__(max_length, fifo)
		Misc.raise_ifn(isinstance(header_size, int), Exceptions.InvalidArgumentException(PickleSerializerStream.__init__, 'header_size', type(header_size), (int,)))
		Misc.raise_ifn((header_size := int(header_size) < 1), ValueError('Header size cannot be smaller than 1'))
		self.__header_size__: int = int(header_size)
		assert self.__header_size__ > 0, 'Header size must be at least 1'

	def read(self, __size: typing.Optional[int] = ...) -> typing.Any | tuple[typing.Any]:
		results: list[typing.Any] = []
		count: int = 0

		while True:
			if (__size is not ... and __size is not None and count > __size) or self.empty():
				break

			length: int = int.from_bytes(super().read(self.__header_size__), 'big', signed=False)
			results.append(pickle.loads(super().read(length)))
			count += 1

		if len(results) == 0:
			raise StreamEmptyError('Stream is empty')

		return results[0] if len(results) == 1 else tuple(results)


class DillSerializerStream(ByteStream):
	"""
	Stream that serializes all data with dill during write
	"""

	def __init__(self, max_length: int = -1, fifo: bool = True, header_size: int = 4):
		"""
		Stream that serializes all data with dill during write
		- Constructor -
		:param max_length: The maximum length (in number of items) of this stream
		:param fifo: Whether this stream is FIFO or LIFO
		:param header_size: The number of bytes to use for serialized object size
		:raises InvalidArgumentException: If 'header_size' is not an integer
		:raises ValueError: If 'header_size' is smaller than 1
		"""

		super().__init__(max_length, fifo)
		Misc.raise_ifn(isinstance(header_size, int), Exceptions.InvalidArgumentException(PickleSerializerStream.__init__, 'header_size', type(header_size), (int,)))
		Misc.raise_ifn((header_size := int(header_size) < 1), ValueError('Header size cannot be smaller than 1'))
		self.__header_size__: int = int(header_size)
		assert self.__header_size__ > 0, 'Header size must be at least 1'

	def write(self, __object: typing.Any, *, ignore_invalid = False) -> DillSerializerStream:
		serialized: bytes = dill.dumps(__object)
		serialized = len(serialized).to_bytes(self.__header_size__, 'big', signed=False) + serialized
		super().write(serialized)
		return self


class DillDeserializerStream(ByteStream):
	"""
	Stream that deserializes all data with dill during read
	"""

	def __init__(self, max_length: int = -1, fifo: bool = True, header_size: int = 4):
		"""
		Stream that deserializes all data with dill during read
		- Constructor -
		:param max_length: The maximum length (in number of items) of this stream
		:param fifo: Whether this stream is FIFO or LIFO
		:param header_size: The number of bytes to use for serialized object size
		:raises InvalidArgumentException: If 'header_size' is not an integer
		:raises ValueError: If 'header_size' is smaller than 1
		"""

		super().__init__(max_length, fifo)
		Misc.raise_ifn(isinstance(header_size, int), Exceptions.InvalidArgumentException(PickleSerializerStream.__init__, 'header_size', type(header_size), (int,)))
		Misc.raise_ifn((header_size := int(header_size) < 1), ValueError('Header size cannot be smaller than 1'))
		self.__header_size__: int = int(header_size)
		assert self.__header_size__ > 0, 'Header size must be at least 1'

	def read(self, __size: typing.Optional[int] = ...) -> typing.Any | tuple[typing.Any]:
		results: list[typing.Any] = []
		count: int = 0

		while True:
			if (__size is not ... and __size is not None and count > __size) or self.empty():
				break

			length: int = int.from_bytes(super().read(self.__header_size__), 'big', signed=False)
			results.append(dill.loads(super().read(length)))
			count += 1

		if len(results) == 0:
			raise StreamEmptyError('Stream is empty')

		return results[0] if len(results) == 1 else tuple(results)


class EventedStream[T](OrderedStream[T]):
	"""
	Stream which allows binding of callbacks to various stream events
	"""

	NO_THREADING: int = 0
	MULTITHREADING: int = 1
	MULTIPROCESSING: int = 2

	def __init__(self, max_length: int = -1, fifo: bool = True):
		"""
		Stream which allows binding of callbacks to various stream events
		- Constructor -
		:param max_length: The maximum length (in number of items) of this stream
		:param fifo: Whether this stream is FIFO or LIFO
		"""

		super().__init__(max_length, fifo)
		self.__callbacks__: dict[str, dict[typing.Callable, int]] = {'write': {}, 'read': {}, 'pipe': {}, 'del_pipe': {}, 'close': {}, 'peek': {}, 'flush': {}}

	def __exec__(self, eid: str, *args, **kwargs) -> None:
		"""
		INTERNAL METHOD
		Executes the callbacks for a specified event ID
		:param eid: The event ID
		:param args: Arguments to call callbacks with
		:param kwargs: Keyword arguments to call callbacks with
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

	def read(self, __size: typing.Optional[int] = ...) -> tuple[T, ...]:
		data: tuple[typing.Any, ...] = super().read(__size)
		self.__exec__('read', data)
		return data

	def peek(self, __size: typing.Optional[int] = ...) -> tuple[T, ...]:
		data: tuple[typing.Any, ...] = super().peek(__size)
		self.__exec__('peek', data)
		return data

	def write(self, __object: T, *, ignore_invalid = False) -> EventedStream[T]:
		super().write(__object)
		self.__exec__('write', __object)
		return self

	def pipe(self, *pipes: io.BufferedIOBase) -> EventedStream[T]:
		super().pipe(*pipes)
		self.__exec__('pipe', *pipes)
		return self

	def del_pipe(self, *pipes: io.BufferedIOBase) -> EventedStream[T]:
		super().del_pipe(*pipes)
		self.__exec__('del_pipe', *pipes)
		return self

	def flush(self, ignore_invalid: bool = False) -> EventedStream[T]:
		super().flush(ignore_invalid)
		self.__exec__('flush')
		return self

	def on(self, eid: str, callback: typing.Optional[typing.Callable] = ..., *, threadability: int = NO_THREADING) -> None | typing.Callable:
		"""
		Binds a callback to the specified event ID
		Can be used as a decorator
		:param eid: The event ID, one of<br/>
		 . . . . . 'write' - Called when an item is written to this stream<br/>
		 . . . . . 'read' - Called when an item is read from this stream<br/>
		 . . . . . 'peek' - called when an item is peeked from this stream<br/>
		 . . . . . 'pipe' - Called when a stream is connected to this stream (Called once for every pipe to add)<br/>
		 . . . . . 'del_pipe' - Called when a stream is disconnected to this stream (Called once for every pipe to remove)<br/>
		 . . . . . 'flush' - Called when this stream is flushed<br/>
		 . . . . . 'close' - Called when this stream is closed
		:param callback: The callback to bind or None if a decorator
		:param threadability: The threading to use, one of<br/>
		. . . . . 0 - No Threading<br/>
		. . . . . 1 - 'threading.Thread' threads<br/>
		. . . . . 2 - 'multiprocessing.Process' processes
		:return: The binder if used as a decorator otherwise None
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
		:param eid: The event ID, see 'EventedStream::on' for a list of valid IDs
		:param callback: The callable to unbind, or all if no callback supplied
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


class LinqStream[T](typing.Reversible):
	"""
	Lazy generator mimicking C# LINQ or Java Streams
	"""

	def __init__(self, iterable: typing.Iterable[T]):
		"""
		Lazy generator mimicking C# LINQ or Java Streams
		- Constructor -
		:param iterable: The source iterable
		:raises InvalidArgumentException: If 'iterable' is not iterable
		"""

		Misc.raise_ifn(hasattr(iterable, '__iter__'), Exceptions.InvalidArgumentException(LinqStream.__init__, 'iterable', type(iterable)))
		self.__source__: typing.Iterable[T] = iterable

	def __contains__(self, item: T) -> bool:
		"""
		*Evaluates the query*
		:param item: The item to check
		:return: Whether the specified item is within this query
		"""

		for elem in self:
			if elem == item:
				return True

		return False

	def __iter__(self) -> typing.Iterator[T]:
		iterator: typing.Iterator[T] = iter(self.__source__)

		while True:
			try:
				yield next(iterator)
			except StopIteration:
				break

	def __reversed__(self) -> typing.Iterator[T]:
		return reversed(tuple(self))

	def __next__(self) -> T:
		"""
		*Evaluates one item from the query*
		:return: The first item in the query
		:raises StopIteration: If the query is empty
		"""

		return next(iter(self))

	def for_each(self, callback: typing.Callable[[T], typing.Any]) -> None:
		"""
		*Evaluates the query*
		Executes a callback for every element in this query
		:param callback: The callback
		:raises InvalidArgumentException: If the callback is not callable
		"""

		Misc.raise_ifn(callable(callback), Exceptions.InvalidArgumentException(LinqStream.for_each, 'callback', type(callback)))

		for elem in self:
			callback(elem)

	def any(self) -> bool:
		"""
		*Evaluates the query*
		:return: Whether this query contains any items
		"""

		try:
			next(self)
			return True
		except StopIteration:
			return False

	def contains(self, elem: T) -> bool:
		"""
		*Evaluates the query*
		:param elem: The item to check
		:return: Whether the item is within this query
		"""

		return elem in self

	def count(self) -> int:
		"""
		*Evaluates the query*
		:return: The number of elements in this query
		"""

		return sum(1 for _ in self)

	def first(self) -> T:
		"""
		*Evaluates the query*
		:return: The first element in this query
		:raises IterableEmptyException: If this query contains no elements
		"""

		try:
			return next(self)
		except StopIteration:
			raise Exceptions.IterableEmptyException('Collection is empty') from None

	def first_or_default(self, default: typing.Any = None) -> typing.Optional[T]:
		"""
		*Evaluates the query*
		:param default: The default
		:return: The first element in this query or "default" if this query has no elements
		"""

		try:
			return next(self)
		except StopIteration:
			return default

	def last(self) -> T:
		"""
		*Evaluates the query*
		:return: The last element in this query
		:raises IterableEmptyException: If this query contains no elements
		"""

		element: typing.Any = None
		has_one: bool = False

		for element in self:
			has_one = True

		if not has_one:
			raise Exceptions.IterableEmptyException('Collection is empty') from None

		return element

	def last_or_default(self, default: typing.Any = None) -> typing.Optional[T]:
		"""
		*Evaluates the query*
		:param default: The default
		:return: The last element in this query or "default" if this query has no elements
		"""

		element: typing.Any = default

		for element in self:
			pass

		return element

	def min(self, comparer: typing.Callable[[T], typing.Any] = None) -> T:
		"""
		*Evaluates the query*
		:param comparer: The comparer to use for comparisons
		:return: The smallest value in this query
		:raises InvalidArgumentException: If 'comparer' is not callable
		"""

		Misc.raise_ifn(callable(comparer), Exceptions.InvalidArgumentException(LinqStream.min, 'comparer', type(comparer)))
		return min(self, key=comparer)

	def max(self, comparer: typing.Callable[[T], typing.Any] = None) -> T:
		"""
		*Evaluates the query*
		:param comparer: The comparer to use for comparisons
		:return: The largest value in this query
		:raises InvalidArgumentException: If 'comparer' is not callable
		"""

		Misc.raise_ifn(callable(comparer), Exceptions.InvalidArgumentException(LinqStream.max, 'comparer', type(comparer)))
		return max(self, key=comparer)

	def aggregate(self, initial: T, aggregator: typing.Callable[[T, T], T]) -> T:
		"""
		Applies an aggregator function over all elements in this query
		:param initial: The initial value
		:param aggregator: The aggregate functon
		:return: The aggregate result
		:raises InvalidArgumentException: If 'aggregator' is not callable
		"""

		Misc.raise_ifn(callable(aggregator), Exceptions.InvalidArgumentException(LinqStream.aggregate, 'aggregator', type(aggregator)))

		for elem in self:
			initial = aggregator(initial, elem)

		return initial

	def element_at(self, index: int) -> T:
		"""
		*Evaluates the query*
		:param index: The element index
		:return: The element at the specified index
		:raises IndexError: If the specified index is out of bounds or negative
		"""

		current: int = 0

		for elem in self:
			if index == current:
				return elem

			current += 1

		raise IndexError(f'Index \'{index}\' out of bounds for LinqStream of len \'{current}\'')

	def element_at_or_default(self, index: int, default: typing.Optional[T] = None) -> T:
		"""
		*Evaluates the query*
		:param index: The element index
		:param default: The default
		:return: The element at the specified index or "default" if index is out of bounds
		"""

		current: int = 0

		for elem in self:
			if index == current:
				return elem

			current += 1

		return default

	def single(self) -> T:
		"""
		*Evaluates the query*
		:return: The sole element of this query
		:raises ValueError: If this query's length is not 1
		"""

		singled: bool = False
		result: T = None

		for elem in self:
			if singled:
				raise ValueError('LinqStream does not have exactly one element')

			result = elem
			singled	= True

		if singled:
			return result
		else:
			raise ValueError('LinqStream does not have exactly one element')

	def single_or_default(self, default: typing.Optional[T] = None) -> T:
		"""
		*Evaluates the query*
		:param default: The default
		:return: The sole element of this query or "default" is this query's length is not 1
		"""

		singled: bool = False
		result: T = None

		for elem in self:
			if singled:
				return default

			result = elem
			singled = True

		return result if singled else default

	def sum(self) -> typing.Any:
		"""
		*Evaluates the query*
		:return: The sum of all elements in this query
		"""

		return sum(self)

	def average(self) -> complex:
		"""
		*Evaluates the query*
		:return: The average of all numbers in this query
		:raises TypeError: If any element in this query is not a number
		"""

		count: int = 0
		total: complex = 0

		for elem in self:
			Misc.raise_ifn(isinstance(elem, (int, float, complex)), TypeError('Resulting element is not a number'))
			count += 1
			total += elem

		return total / count

	def collect[C: typing.Iterable](self, collector: Stream[T] | type[C] = tuple, *args, **kwargs) -> Stream[T] | C:
		"""
		*Evaluates the query*
		Collects all elements in this query into the specified collection or Stream
		:param collector: The type of collection to collect into or a Stream instance
		:param args: Extra positional arguments to apply to the collector's constructor
		:param kwargs: Extra keyword arguments to apply to the collector's constructor
		:return: The populated collection or Stream
		:raises InvalidArgumentException: If 'collector' is not an iterable type, Stream, or Stream type
		"""

		if isinstance(collector, type) and issubclass(collector, Stream):
			stream: Stream = collector(*args, **kwargs)

			for elem in self:
				stream.write(elem)

			return stream
		elif isinstance(collector, type) and issubclass(collector, (typing.Iterable, collections.abc.Sequence, collections.abc.Iterable)):
			return collector(self, *args, **kwargs)
		elif isinstance(collector, Stream):
			for elem in self:
				collector.write(elem)
			return collector
		else:
			raise Exceptions.InvalidArgumentException(LinqStream.collect, 'collector', type(collector), (type, Stream))

	def transform[K](self, mapper: typing.Callable[[T], K]) -> LinqStream[K]:
		"""
		Applies a transformer to all elements in this query
		:param mapper: Transformer function
		:return: The modified query
		:raises InvalidArgumentException: If 'mapper' is not callable
		"""

		Misc.raise_ifn(callable(mapper), Exceptions.InvalidArgumentException(LinqStream.transform, 'mapper', type(mapper)))
		return LinqStream(mapper(x) for x in self)

	def transform_many[K](self, mapper: typing.Callable[[T], typing.Iterable[K]]) -> LinqStream[K]:
		"""
		Applies a transformer to all elements in this query and flattens the result
		:param mapper: Transformer function
		:return: The modified query
		:raises InvalidArgumentException: If 'mapper' is not callable
		"""

		Misc.raise_ifn(callable(mapper), Exceptions.InvalidArgumentException(LinqStream.transform_many, 'mapper', type(mapper)))

		def _many() -> typing.Generator[K]:
			for elem in self:
				collection: typing.Iterable[K] = mapper(elem)

				for subelem in collection:
					yield subelem

		return LinqStream(_many())

	def filter(self, filter_: typing.Callable[[T], bool]) -> LinqStream[T]:
		"""
		Filters elements in this query
		:param filter_: The filter function (return True to keep and False to discard)
		:return: The modified query
		:raises InvalidArgumentException: If 'filter_' is not callable
		"""

		Misc.raise_ifn(callable(filter_), Exceptions.InvalidArgumentException(LinqStream.filter, 'filter_', type(filter_)))
		return LinqStream(x for x in self if filter_(x))

	def instance_of[I](self, cls: type[I]) -> LinqStream[I]:
		"""
		Filters elements in this query
		All elements that derive the specified type are allowed
		:param cls: The class type to check for
		:return: The modified query
		:raises InvalidArgumentException: If 'cls' is not a type
		"""

		Misc.raise_ifn(isinstance(cls, type), Exceptions.InvalidArgumentException(LinqStream.instance_of, 'cls', type(cls), (type,)))
		return LinqStream(x for x in self if isinstance(x, cls))

	def not_instance_of[I](self, cls: type[I]) -> LinqStream[I]:
		"""
		Filters elements in this query
		All elements that do not derive the specified type are allowed
		:param cls: The class type to check for
		:return: The modified query
		:raises InvalidArgumentException: If 'cls' is not a type
		"""

		Misc.raise_ifn(isinstance(cls, type), Exceptions.InvalidArgumentException(LinqStream.not_instance_of, 'cls', type(cls), (type,)))
		return LinqStream(x for x in self if not isinstance(x, cls))

	def skip(self, count: int) -> LinqStream[T]:
		"""
		Skips the first 'count' elements in this query
		:param count: The number of elements to skip
		:return: The modified query
		:raises InvalidArgumentException: If 'count' is not an integer
		:raises ValueError: If 'count' is negative
		"""

		def _skip(stream: LinqStream[T]) -> typing.Generator[T]:
			nonlocal index

			for elem in stream:
				if (index := (index + 1)) > count:
					yield elem

		Misc.raise_ifn(isinstance(count, int), Exceptions.InvalidArgumentException(LinqStream.skip, 'count', type(count), (int,)))
		Misc.raise_ifn((count := int(count)) >= 0, ValueError('Count cannot be negative'))
		index: int = 0
		return LinqStream(_skip(self))

	def skip_while(self, condition: typing.Callable[[T], bool]) -> LinqStream[T]:
		"""
		Skips the elements in this query while the condition callback returns True
		:param condition: The condition
		:return: The modified query
		:raises InvalidArgumentException: If 'condition' is not callable
		"""

		def _skip(stream: LinqStream[T]) -> typing.Generator[T]:
			for elem in stream:
				if not condition(elem):
					yield elem
					break

			for elem in stream:
				yield elem

		Misc.raise_ifn(callable(condition), Exceptions.InvalidArgumentException(LinqStream.skip_while, 'condition', type(condition)))
		return LinqStream(_skip(self))

	def take(self, count: int) -> LinqStream[T]:
		"""
		Takes the first 'count' elements in this query, discarding all remaining elements
		:param count: The number of elements to take
		:return: The modified query
		:raises InvalidArgumentException: If 'count' is not an integer
		:raises ValueError: If 'count' is negative
		"""

		def _take(stream: LinqStream[T]) -> typing.Generator[T]:
			nonlocal index

			for elem in stream:
				if (index := (index + 1)) <= count:
					yield elem

		Misc.raise_ifn(isinstance(count, int), Exceptions.InvalidArgumentException(LinqStream.take, 'count', type(count), (int,)))
		Misc.raise_ifn((count := int(count)) >= 0, ValueError('Count cannot be negative'))
		index: int = 0
		return LinqStream(_take(self))

	def take_while(self, condition: typing.Callable[[T], bool]) -> LinqStream[T]:
		"""
		Takes the first "count" elements in this query, discarding all remaining elements, while the condition callback returns True
		:param condition: (CALLABLE) The condition
		:return: (LinqStream) The modified query
		:raises InvalidArgumentException: If 'condition' is not callable
		"""

		def _take(stream: LinqStream[T]) -> typing.Generator[T]:
			for elem in stream:
				if condition(elem):
					yield elem
				else:
					break

		Misc.raise_ifn(callable(condition), Exceptions.InvalidArgumentException(LinqStream.take_while, 'condition', type(condition)))
		return LinqStream(_take(self))

	def chunk(self, batch_size: int) -> LinqStream[tuple[T, ...]]:
		"""
		Groups elements in this query into batches of a set size
		:param batch_size: The batch size
		:return: The modified query
		:raises InvalidArgumentException: If 'batch_size' is not an integer
		:raises ValueError: If 'batch_size' is smaller than 1
		"""

		def _chunk(stream: LinqStream[T]) -> typing.Generator[tuple[T, ...]]:
			for elem in stream:
				chunk.append(elem)

				if len(chunk) == batch_size:
					yield tuple(chunk)
					chunk.clear()

			if len(chunk) > 0:
				yield tuple(chunk)

		Misc.raise_ifn(isinstance(batch_size, int), Exceptions.InvalidArgumentException(LinqStream.chunk, 'batch_size', type(batch_size), (int,)))
		Misc.raise_ifn((batch_size := int(batch_size)) >= 1, ValueError('Batch size must be greater than or equal to 1'))
		chunk: list[T] = []
		return LinqStream(_chunk(self))

	def enumerate(self) -> LinqStream[tuple[int, T]]:
		"""
		For each element in this query, returns a tuple containing the element's index and value
		*Identical to "LinqStream(enumerate(self))"*
		:return: The modified query
		"""

		return LinqStream(enumerate(self))

	def group[K](self, grouper: typing.Callable[[T], K]) -> LinqStream[tuple[T, tuple[K, ...]]]:
		"""
		Groups all elements in this query by a key
		:param grouper: Grouping function retuning the key used for comparisons
		:return: The modified query
		:raises InvalidArgumentException: If 'grouper' is not callable
		"""

		def _group(stream: LinqStream[T]) -> typing.Generator[tuple[T, tuple[K, ...]]]:
			for elem in stream:
				key: K = grouper(elem)

				if key in grouping:
					grouping[key].append(elem)
				else:
					grouping[key] = [elem]

			for key, group in grouping.items():
				yield key, tuple(group)

		Misc.raise_ifn(callable(grouper), Exceptions.InvalidArgumentException(LinqStream.group, 'grouper', type(grouper)))
		grouping: dict[K, list[T]] = {}
		return LinqStream(_group(self))

	def distinct(self, key: typing.Optional[typing.Callable[[T], typing.Hashable]] = ...) -> LinqStream[T]:
		"""
		Returns a distinct (non-duplicate) list of elements in this query
		:param key: If provided, a function returning the keys used for comparison
		:return: The modified query
		:raises InvalidArgumentException: If 'key' is not callable
		"""

		def _distinct(stream: LinqStream[T]) -> typing.Generator[T]:
			matched: set[typing.Hashable] = set()

			for elem in stream:
				_key: typing.Hashable = key(elem) if callable(key) else elem

				if _key in matched:
					continue

				matched.add(_key)
				yield elem

		Misc.raise_ifn(key is None or key is ... or callable(key), Exceptions.InvalidArgumentException(LinqStream.distinct, 'key', type(key)))
		return LinqStream(_distinct(self))

	def set_difference(self, iterable: typing.Iterable[T], key: typing.Optional[typing.Callable[[T], typing.Hashable]] = ...) -> LinqStream[T]:
		"""
		Applies the set difference between the elements in this query and the supplied iterable
		:param iterable: The second iterable to apply difference with
		:param key: If provided, a function returning the keys used for comparison
		:return: The modified query
		:raises InvalidArgumentException: If 'iterable' is not iterable
		:raises InvalidArgumentException: If 'key' is not callable
		"""

		def _difference(stream: LinqStream[T]) -> typing.Generator[T]:
			for elem in stream:
				_key: typing.Hashable = hash(elem) if key is None or key is ... else key(elem)

				if _key in primary or _key in secondary:
					continue

				primary.add(_key)
				yield elem

		Misc.raise_ifn(key is ... or key is None or callable(key), Exceptions.InvalidArgumentException(LinqStream.set_difference, 'key', type(key)))
		Misc.raise_ifn(hasattr(iterable, '__iter__'), Exceptions.InvalidArgumentException(LinqStream.set_difference, 'iterable', type(iterable)))
		secondary: set[typing.Hashable] = set(iterable)
		primary: set[typing.Hashable] = set()
		return LinqStream(_difference(self))

	def set_intersect(self, iterable: typing.Iterable[T], key: typing.Optional[typing.Callable[[T], typing.Hashable]] = ...) -> LinqStream[T]:
		"""
		Applies the set intersection between the elements in this query and the supplied iterable
		:param iterable: The second iterable to apply intersection with
		:param key: If provided, a function returning the keys used for comparison
		:return: The modified query
		:raises InvalidArgumentException: If 'iterable' is not iterable
		:raises InvalidArgumentException: If 'key' is not callable
		"""

		def _intersect(stream: LinqStream[T]) -> typing.Generator[T]:
			for elem in stream:
				_key: typing.Hashable = hash(elem) if key is None or key is ... else key(elem)

				if _key in primary or _key not in secondary:
					continue

				primary.add(_key)
				yield elem

		Misc.raise_ifn(key is ... or key is None or callable(key), Exceptions.InvalidArgumentException(LinqStream.set_intersect, 'key', type(key)))
		Misc.raise_ifn(hasattr(iterable, '__iter__'), Exceptions.InvalidArgumentException(LinqStream.set_intersect, 'iterable', type(iterable)))
		secondary: set[typing.Hashable] = set(iterable)
		primary: set[typing.Hashable] = set()
		return LinqStream(_intersect(self))

	def set_union(self, iterable: typing.Iterable[T], key: typing.Optional[typing.Callable[[T], typing.Hashable]] = ...) -> LinqStream[T]:
		"""
		Applies the set union between the elements in this query and the supplied iterable
		:param iterable: The second iterable to apply union with
		:param key: If provided, a function returning the keys used for comparison
		:return: The modified query
		:raises InvalidArgumentException: If 'iterable' is not iterable
		:raises InvalidArgumentException: If 'key' is not callable
		"""

		def _union(stream: LinqStream[T]) -> typing.Generator[T]:
			for elem in stream:
				_key: typing.Hashable = hash(elem) if key is None or key is ... else key(elem)

				if _key not in primary:
					primary.add(_key)
					yield elem

			for elem in iterable:
				_key: typing.Hashable = hash(elem) if key is None or key is ... else key(elem)

				if _key not in primary:
					primary.add(_key)
					yield elem

		Misc.raise_ifn(key is ... or key is None or callable(key), Exceptions.InvalidArgumentException(LinqStream.set_union, 'key', type(key)))
		Misc.raise_ifn(hasattr(iterable, '__iter__'), Exceptions.InvalidArgumentException(LinqStream.set_union, 'iterable', type(iterable)))
		primary: set[typing.Hashable] = set()
		return LinqStream(_union(self))

	def to_lookup[K, V](self, key_converter: typing.Optional[typing.Callable[[T], K]] = ..., value_converter: typing.Optional[typing.Callable[[T], V]] = ...) -> dict[K, tuple[V, ...]]:
		"""
		*Evaluates this query*
		:param key_converter: The function to convert elements to keys
		:param value_converter: The function to convert elements to values
		:return: A dict mapping a key with multiple values
		:raises InvalidArgumentException: If 'key_converter' is not callable
		:raises InvalidArgumentException: If 'value_converter' is not callable
		"""

		Misc.raise_ifn(key_converter is ... or key_converter is None or callable(key_converter), Exceptions.InvalidArgumentException(LinqStream.to_lookup, 'key_converter', type(key_converter)))
		Misc.raise_ifn(value_converter is ... or value_converter is None or callable(value_converter), Exceptions.InvalidArgumentException(LinqStream.to_lookup, 'value_converter', type(value_converter)))
		mapping: dict[K, list[V]] = {}

		for elem in self:
			key: K = key_converter(elem) if callable(key_converter) else elem[0]
			value: V = value_converter(elem) if callable(value_converter) else elem[1]

			if key in mapping:
				mapping[key].append(value)
			else:
				mapping[key] = [value]

		return {k: tuple(v) for k, v in mapping.items()}

	def to_dictionary[K, V](self, key_converter: typing.Optional[typing.Callable[[T], K]] = ..., value_converter: typing.Optional[typing.Callable[[T], V]] = ...) -> dict[K, V]:
		"""
		*Evaluates this query*
		:param key_converter: The function to convert elements to keys
		:param value_converter: The function to convert elements to values
		:return: A dict mapping each key with a single value
		:raises InvalidArgumentException: If 'key_converter' is not callable
		:raises InvalidArgumentException: If 'value_converter' is not callable
		:raises KeyError: If a duplicate key is found
		"""

		Misc.raise_ifn(key_converter is ... or key_converter is None or callable(key_converter), Exceptions.InvalidArgumentException(LinqStream.to_dictionary, 'key_converter', type(key_converter)))
		Misc.raise_ifn(value_converter is ... or value_converter is None or callable(value_converter), Exceptions.InvalidArgumentException(LinqStream.to_dictionary, 'value_converter', type(value_converter)))
		mapping: dict[K, V] = {}

		for elem in self:
			key: K = key_converter(elem) if callable(key_converter) else elem[0]
			value: V = value_converter(elem) if callable(value_converter) else elem[1]

			if key in mapping:
				raise KeyError('Duplicate key during LinqStream evaluation')
			else:
				mapping[key] = value

		return mapping

	def sort(self, sorter: typing.Optional[typing.Callable[[T], typing.Any]] = None, *, reverse: bool = False) -> LinqStream[T]:
		"""
		Sorts all elements in this query and yields the sorted query
		:param sorter: The optional sorter used to supply sort keys
		:param reverse: Whether to sort in reverse order
		:return: The modified query
		:raises InvalidArgumentException: If 'sorter' is not callable
		"""

		Misc.raise_ifn(sorter is ... or sorter is None or callable(sorter), Exceptions.InvalidArgumentException(LinqStream.sort, 'sorter', type(sorter)))
		return LinqStream(sorted(self, key=None if sorter is ... or sorter is None else sorter, reverse=reverse))

	def reverse(self) -> LinqStream[T]:
		"""
		Reverses the order of elements in this query
		:return: THe modified query
		"""

		return LinqStream(reversed(self))

	def merge(self, *others: typing.Iterable[T]) -> LinqStream[T]:
		"""
		Appends multiple iterables to the end of this query
		:param others: The iterable whose elements to append
		:return: The modified query
		:raises InvalidArgumentException: If one or more iterables is not iterable
		"""

		Misc.raise_ifn(all(hasattr(x, '__iter__') for x in others), Exceptions.InvalidArgumentException(LinqStream.merge, 'others', type(others)))
		streams: tuple[LinqStream, ...] = (self, *others)

		def iterator() -> typing.Generator[T]:
			for stream in streams:
				for item in stream:
					yield item

		return LinqStream(iterator())

	def zip(self, *others: typing.Iterable[T]) -> LinqStream[tuple[T, ...]]:
		"""
		Zips multiple iterables with this one
		The resulting query contains a tuple of index aligned elements from each iterable
		:param others: The iterable whose elements to zip
		:return: The modified query
		:raises InvalidArgumentException: If one or more iterables is not iterable
		"""

		Misc.raise_ifn(all(hasattr(x, '__iter__') for x in others), Exceptions.InvalidArgumentException(LinqStream.zip, 'others', type(others)))
		streams: tuple[typing.Iterator[T], ...] = tuple(iter(x) for x in (self, *others))

		def iterator() -> typing.Generator[T]:
			package: list[T] = []

			while True:
				try:
					for i in streams:
						package.append(next(i))
					yield tuple(package)
					package.clear()
				except StopIteration:
					break

		return LinqStream(iterator())

	def append(self, element: T) -> LinqStream[T]:
		"""
		Appends an element to the end of this query
		:param element: The element to append
		:return: The modified query
		"""

		def _append(stream: LinqStream[T]) -> typing.Generator[T]:
			for elem in stream:
				yield elem

			yield element

		return LinqStream(_append(self))

	def prepend(self, element: T) -> LinqStream[T]:
		"""
		Prepends an element to the end of this query
		:param element: The element to prepend
		:return: The modified query
		"""

		def _prepend(stream: LinqStream[T]) -> typing.Generator[T]:
			yield element

			for elem in stream:
				yield elem

		return LinqStream(_prepend(self))

	def insert(self, index: int, element: T) -> LinqStream[T]:
		"""
		Inserts an element into this query
		:param index: The index to insert at
		:param element: The element to insert
		:return: The modified query
		:raises InvalidArgumentException: If 'index' is not an integer
		:raises ValueError: If 'index' is negative
		"""

		def _insert(stream: LinqStream[T]) -> typing.Generator[T]:
			count: int = 0

			for elem in stream:
				if count == index:
					yield element
					count += 1
					continue

				yield elem
				count += 1

		Misc.raise_ifn(isinstance(index, int), Exceptions.InvalidArgumentException(LinqStream.insert, 'index', type(index), (int,)))
		Misc.raise_ifn((index := int(index)) >= 0, ValueError('Index cannot be negative'))
		return LinqStream(_insert(self))
