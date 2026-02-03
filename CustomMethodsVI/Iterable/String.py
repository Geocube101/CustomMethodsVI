from __future__ import annotations

import collections
import re
import sys
import typing

from . import Sequence
from .. import Misc


class String(Sequence.MutableSequence[str], str):
	"""
	An extension adding additional string functionality
	"""

	class __Stringify__:
		def __init__(self, callback: collections.abc.Callable):
			self.__callback__: collections.abc.Callable = callback

		def __call__(self, *args, **kwargs) -> typing.Any:
			result: typing.Any = self.__callback__(*args, **kwargs)
			return String(result) if isinstance(result, Sequence.Sequence) and all(isinstance(x, str) for x in result) else result

	def __init__(self, string: typing.Optional[typing.Any] = None):
		"""
		An extension adding additional string functionality\n
		- Constructor -
		:param string: The input value to convert to a string
		"""

		super().__init__([] if string is ... or string is None else list(str(string)))

	def __contains__(self, substr: str | String) -> bool:
		return isinstance(substr, (str, String)) and self.index(substr) >= 0

	def __eq__(self, other: str | String) -> bool:
		return isinstance(other, (str, String)) and str(other) == str(self)

	def __float__(self) -> float:
		return float(str(self))

	def __complex__(self) -> complex:
		return complex(str(self))

	def __int__(self) -> int:
		return int(str(self))

	def __str__(self) -> str:
		return ''.join(self)

	def __repr__(self) -> str:
		return repr(str(self))

	def __iadd__(self, other: str | String) -> String:
		if not isinstance(other, (str, String)):
			return NotImplemented

		super().__iadd__(other)
		return self

	def __imul__(self, other: int) -> String:
		super().__imul__(other)
		return self

	def __lshift__(self, other: str | String) -> String:
		if isinstance(other, String):
			self.append(other.pop())
		elif isinstance(other, str):
			return String(self + other)
		else:
			return NotImplemented

	def __rshift__(self, other: String) -> String:
		if not isinstance(other, String):
			return NotImplemented

		other.append(self.pop())
		return other

	def __setitem__(self, key: int | tuple[int, ...] | slice, value: str | String) -> None:
		"""
		Sets one or more items in this collection
		:param key: The index or indices to modify
		:param value: The value to set
		:raises TypeError: If indices are not integers, slices, or a collection of indices
		"""

		Misc.raise_ifn(isinstance(value, (bytes, bytearray, ByteString)) or (isinstance(value, int) and 0 <= (value := int(value)) <= 255), ValueError('String set item value must be either a string or String instance'))

		if isinstance(key, int) and len(value) == 1:
			self.__buffer__[key] = str(value)
		elif isinstance(key, int):
			key = int(key)

			for i, char in enumerate(value):
				self.__buffer__.insert(key + i, char)

		elif isinstance(key, tuple):
			for k in key:
				self[k] = value

		elif isinstance(key, slice):
			start: int = 0 if key.start is None else int(key.start)
			stop: int = len(self) if key.stop is None else int(key.stop)
			step: int = 1 if key.step is None else int(key.step)
			index: int = 0

			for i in range(start, stop, step):
				element: str = value[index % len(value)]
				self.__buffer__[i] = element
				index += 1

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(key).__name__}')

	def __getitem__(self, item: int | slice | tuple[int, ...]) -> str | Sequence.Sequence[str] | String:
		"""
		Gets one or more items in this collection
		:param item: The index or indices to get
		:return: If a single element, only that character; if multiple non-continuous elements, an iterable of characters; otherwise a substring
		:raises TypeError: If indices are not integers, slices, or a collection of indices
		"""

		if isinstance(item, int):
			return self.__buffer__[item]

		elif isinstance(item, tuple):
			items: list = []

			for key in item:
				result = self[key]

				if isinstance(key, (tuple, slice)):
					items.extend(result)
				else:
					items.append(result)

			return Sequence.Sequence(items)

		elif isinstance(item, slice):
			start: int = 0 if item.start is None else int(item.start)
			stop: int = len(self) if item.stop is None else int(item.stop)
			step: int = 1 if item.step is None else int(item.step)
			items: list = []

			for i in range(start, stop, step):
				items.append(self.__buffer__[i])

			return String(items)

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(item).__name__}')

	def __getattribute__(self, name: str) -> typing.Any:
		attribute: typing.Any = super().__getattribute__(name)
		is_this: bool = name in vars(type(self))
		super_str_attr: typing.Any = getattr(str, name) if hasattr(str, name) else None
		super_iterable_attr: typing.Any = getattr(Sequence.MutableSequence, name) if hasattr(Sequence.MutableSequence, name) else None

		if is_this or not callable(attribute):
			return attribute
		elif super_iterable_attr is not None:
			return String.__Stringify__(attribute) if callable(super_iterable_attr) else attribute
		elif super_str_attr is not None:
			return String.__Stringify__(getattr(str(self), name)) if callable(super_str_attr) else attribute
		else:
			return attribute

	def is_integer2(self) -> bool:
		"""
		Checks if the string is a binary integer
		:return: Whether all characters are 0 or 1
		"""

		return all(x == '0' or x == '1' for x in self)

	def is_integer8(self) -> bool:
		"""
		Checks if the string is an octal integer
		:return: Whether all characters are in the range 0-7
		"""

		chars: tuple[str, ...] = tuple(map(str, range(8)))
		return all(x in chars for x in self)

	def is_integer10(self) -> bool:
		"""
		Checks if the string is a decimal integer
		:return: Whether all characters are in the range 0-9
		"""

		return self.isnumeric()

	def is_integer16(self) -> bool:
		"""
		Checks if the string is a hexadecimal integer
		:return: Whether all characters are in the range 0-9 or A-F
		"""

		chars: tuple[str, ...] = tuple('abcdefABCDEF')
		return all(x.isnumeric() or x in chars for x in self)

	def is_float(self) -> bool:
		"""
		:return: Whether the string is a valid float representation
		"""

		return re.fullmatch(r'\d+(\.\d*(([eE])\d*)?)?', self) is not None

	def is_extended_float(self) -> bool:
		"""
		Allows for a single decimal in the exponent as well: "1.2e3.4"

		Use "String.to_extended_float" to convert the value to a float
		:return: Whether the string is a valid float representation
		"""

		return re.fullmatch(r'\d+(\.\d*(([e|E])\d*(\.\d*)?)?)?', self) is not None

	def is_complex(self) -> bool:
		"""
		:return: Whether the string is a valid complex number representation
		"""

		return re.fullmatch(r'\(?\d*(\.\d*)?(e|E\d*)?(\+\d*(\.\d*)?(e|E\d*)?j)?\)?', self) is not None

	def to_extended_float(self) -> float:
		"""
		Converts the string to a float using the extended float format described in "String.is_extended_float"
		:return: The converted value
		:raises ValueError: If the string is not an extended float
		"""

		Misc.raise_ifn(self.is_extended_float(), ValueError(f'could not convert string to extended float: \'{self}\''))
		sections: list[String] = self.multisplit('eE')
		left: float = float(sections[0])
		right: float = float(sections[1]) if len(sections) > 0 else 1
		return left * 10 ** right

	def copy(self) -> String:
		"""
		:return: A copy of this string
		"""

		return String(self)

	def append(self, element: str | String) -> String:
		"""
		Adds the specified substring to the end of this string
		:param element: The substring to add
		:return: This string
		"""

		if isinstance(element, str):
			self.__buffer__.extend(str(element))
		elif isinstance(element, String):
			self.__buffer__.extend(element.__buffer__)
		else:
			raise TypeError('String elements must be a string or String instance')

		return self

	def extend(self, iterable: typing.Iterable[bytes, bytearray, ByteString, int]) -> String:
		"""
		Adds all strings or bytes from the specified iterable to the end of this string
		:param iterable: The collection of substrings or bytes to add
		:return: This string
		"""

		for item in iterable:
			self.append(item)

		return self

	def insert(self, index: int, element: bytes | bytearray | ByteString | int) -> String:
		if isinstance(element, (str, String)):
			index = int(index)

			for i, char in enumerate(element):
				self.__buffer__.insert(index + i, char)
		else:
			raise TypeError('String elements must be a string or String instance')

		return self

	def multisplit(self, sep: typing.Optional[typing.Iterable[str]] = ..., maxsplit: int = -1) -> list[String]:
		"""
		Splits the string around multiple delimiters
		:param sep: The delimiters to split around
		:param maxsplit: The maximum number of splits to perform (negative or zero values are infinite)
		:return: A list of the split string
		"""

		return [String(s) for s in re.split('|'.join(re.escape(delimiter) for delimiter in sep), self, 0 if maxsplit <= 0 else maxsplit)]


class ByteString(Sequence.MutableSequence[int], bytearray):
	"""
	An extension adding additional bytes functionality
	"""

	class __Byteify__:
		def __init__(self, callback: collections.abc.Callable):
			self.__callback__: collections.abc.Callable = callback

		def __call__(self, *args, **kwargs) -> typing.Any:
			result: typing.Any = self.__callback__(*args, **kwargs)
			return ByteString(result) if isinstance(result, Sequence.Sequence) and all(isinstance(x, int) for x in result) else result

	def __init__(self, string: typing.Optional[typing.Any] = None, encoding: str = 'utf-8', errors: typing.Literal['strict', 'ignore', 'replace', 'xmlcharrefreplace', 'backslashreplace', 'namereplace', 'surrogateescape'] = 'strict'):
		"""
		An extension adding additional string functionality\n
		- Constructor -
		:param string: The input value to convert to a string
		"""

		super().__init__([] if string is ... or string is None else list(bytes(string, encoding, errors)) if isinstance(string, str) else list(bytes(string)))

	def __contains__(self, substr: bytes | bytearray | ByteString) -> bool:
		return isinstance(substr, (bytes, bytearray, ByteString)) and self.index(substr) >= 0

	def __eq__(self, other: bytes | bytearray | ByteString) -> bool:
		return isinstance(other, (bytes, bytearray, ByteString)) and bytes(other) == bytes(self)

	def __float__(self) -> float:
		return float(bytes(self))

	def __int__(self) -> int:
		return int(bytes(self))

	def __bytes__(self) -> bytes:
		return bytes(self.__buffer__)

	def __str__(self) -> str:
		return str(bytes(self.__buffer__))

	def __repr__(self) -> str:
		return repr(bytes(self.__buffer__))

	def __iadd__(self, other: bytes | bytearray | ByteString) -> ByteString:
		if not isinstance(other, (bytes, bytearray, ByteString)):
			return NotImplemented

		super().__iadd__(other)
		return self

	def __imul__(self, other: int) -> ByteString:
		super().__imul__(other)
		return self

	def __lshift__(self, other: bytes | bytearray | ByteString) -> ByteString:
		if isinstance(other, ByteString):
			self.append(other.pop())
		elif isinstance(other, (bytes, bytearray)):
			return ByteString(self + other)
		else:
			return NotImplemented

	def __rshift__(self, other: ByteString) -> ByteString:
		if not isinstance(other, ByteString):
			return NotImplemented

		other.append(self.pop())
		return other

	def __setitem__(self, key: int | tuple[int, ...] | slice, value: bytes | bytearray | ByteString | int) -> None:
		"""
		Sets one or more items in this collection
		:param key: The index or indices to modify
		:param value: The value to set
		:raises TypeError: If indices are not integers, slices, or a collection of indices
		"""

		Misc.raise_ifn(isinstance(value, (bytes, bytearray, ByteString)) or (isinstance(value, int) and 0 <= (value := int(value)) <= 255), ValueError('ByteString set item value must be either a bytes, bytearray, ByteString, or integer in the range 0-255'))

		if isinstance(key, int) and isinstance(value, int):
			self.__buffer__[key] = int(value)
		elif isinstance(key, int):
			key = int(key)

			for i, byte in enumerate(value):
				self.__buffer__.insert(key + i, byte)

		elif isinstance(key, tuple):
			for k in key:
				self[k] = value

		elif isinstance(key, slice):
			start: int = 0 if key.start is None else int(key.start)
			stop: int = len(self) if key.stop is None else int(key.stop)
			step: int = 1 if key.step is None else int(key.step)
			index: int = 0

			for i in range(start, stop, step):
				element: int = int(value) if isinstance(value, int) else value[index % len(value)]
				Misc.raise_ifn(0 <= element <= 255, ValueError('ByteString set item value must be either a bytes, bytearray, ByteString, or integer in the range 0-255'))
				self.__buffer__[i] = element
				index += 1

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(key).__name__}')

	def __getitem__(self, item: int | slice | tuple[int, ...]) -> int | Sequence.Sequence[int] | ByteString:
		"""
		Gets one or more items in this collection
		:param item: The index or indices to get
		:return: If a single element, only that byte; if multiple non-continuous elements, an iterable of integers; otherwise a substring
		:raises TypeError: If indices are not integers, slices, or a collection of indices
		"""

		if isinstance(item, int):
			return self.__buffer__[item]

		elif isinstance(item, tuple):
			items: list = []

			for key in item:
				result = self[key]

				if isinstance(key, (tuple, slice)):
					items.extend(result)
				else:
					items.append(result)

			return Sequence.Sequence(items)

		elif isinstance(item, slice):
			start: int = 0 if item.start is None else int(item.start)
			stop: int = len(self) if item.stop is None else int(item.stop)
			step: int = 1 if item.step is None else int(item.step)
			items: list = []

			for i in range(start, stop, step):
				items.append(self.__buffer__[i])

			return ByteString(items)

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(item).__name__}')

	def __getattribute__(self, name: str) -> typing.Any:
		attribute: typing.Any = super().__getattribute__(name)
		is_this: bool = name in vars(type(self))
		super_bytes_attr: typing.Any = getattr(bytearray, name) if hasattr(bytearray, name) else None
		super_iterable_attr: typing.Any = getattr(Sequence.MutableSequence, name) if hasattr(Sequence.MutableSequence, name) else None

		if is_this or not callable(attribute):
			return attribute
		elif super_iterable_attr is not None:
			return ByteString.__Byteify__(attribute) if callable(super_iterable_attr) else attribute
		elif super_bytes_attr is not None:
			return ByteString.__Byteify__(getattr(bytes(self), name)) if callable(super_bytes_attr) else attribute
		else:
			return attribute

	def is_integer2(self) -> bool:
		"""
		Checks if the string is a binary integer
		:return: Whether all characters are 0 or 1
		"""

		zero: int = ord('0')
		one: int = ord('1')
		return all(x == zero or x == one for x in self)

	def is_integer8(self) -> bool:
		"""
		Checks if the string is an octal integer
		:return: Whether all characters are in the range 0-7
		"""

		chars: tuple[int, ...] = tuple(ord('0') + x for x in range(8))
		return all(x in chars for x in self)

	def is_integer10(self) -> bool:
		"""
		Checks if the string is a decimal integer
		:return: Whether all characters are in the range 0-9
		"""

		chars: tuple[int, ...] = tuple(ord('0') + x for x in range(10))
		return all(x in chars for x in self)

	def is_integer16(self) -> bool:
		"""
		Checks if the string is a hexadecimal integer
		:return: Whether all characters are in the range 0-9 or A-F
		"""

		chars: tuple[int, ...] = (*[ord('0') + x for x in range(10)], *[ord(x) for x in 'abcdefABCDEF'])
		return all(x in chars for x in self)

	def is_float(self) -> bool:
		"""
		:return: Whether the string is a valid float representation
		"""

		return re.fullmatch(rb'\d+(\.\d*(([e|E])\d*)?)?', bytes(self)) is not None

	def is_extended_float(self) -> bool:
		"""
		Allows for a single decimal in the exponent as well: "1.2e3.4"

		Use "String.to_extended_float" to convert the value to a float
		:return: Whether the string is a valid float representation
		"""

		return re.fullmatch(rb'\d+(\.\d*(([e|E])\d*(\.\d*)?)?)?', bytes(self)) is not None

	def to_extended_float(self) -> float:
		"""
		Converts the string to a float using the extended float format described in "String.is_extended_float"
		:return: The converted value
		:raises ValueError: If the string is not an extended float
		"""

		Misc.raise_ifn(self.is_extended_float(), ValueError(f'could not convert string to extended float: \'{self}\''))
		sections: list[ByteString] = self.multisplit(b'eE')
		left: float = float(sections[0])
		right: float = float(sections[1]) if len(sections) > 0 else 1
		return left * 10 ** right

	def index(self, item: int | bytes | bytearray | ByteString, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Returns the index of the specified byte or substring
		:param item: The substring or byte to check for
		:param start: Index to begin check or beginning of string if not supplied
		:param stop: Index to end check or end of string if not supplied
		:return: The substring or byte index or -1 if not found
		"""

		if isinstance(item, int):
			return super().index(item, start, stop) if 0x00 <= (item := int(item)) <= 0xFF else -1

		target: bytes = bytes(item)
		start: int = 0 if start is ... or start is None else int(start)
		stop: int = (len(self) - len(target) + 1) if stop is ... or stop is None else int(stop)

		for i in range(start, stop):
			if bytes(self[i:i + len(item)]) == target:
				return i

		return -1

	def copy(self) -> ByteString:
		"""
		:return: A copy of this string
		"""

		return ByteString(self)

	def append(self, element: bytes | bytearray | ByteString | int) -> ByteString:
		"""
		Adds the specified byte or substring to the end of this string
		:param element: The substring or byte to add
		:return: This string
		"""

		if isinstance(element, (bytes, bytearray)):
			self.__buffer__.extend(bytes(element))
		elif isinstance(element, int) and 0 <= (element := int(element)) <= 255:
			self.__buffer__.append(element)
		elif isinstance(element, ByteString):
			self.__buffer__.extend(element.__buffer__)
		else:
			raise TypeError('Bytestring elements must be a bytes object, bytearray object, ByteString instance, or integer in the range 0-255')

		return self

	def extend(self, iterable: typing.Iterable[bytes, bytearray, ByteString, int]) -> ByteString:
		"""
		Adds all strings or bytes from the specified iterable to the end of this string
		:param iterable: The collection of substrings or bytes to add
		:return: This string
		"""

		for item in iterable:
			self.append(item)

		return self

	def insert(self, index: int, element: bytes | bytearray | ByteString | int) -> ByteString:
		if isinstance(element, int) and 0 <= (element := int(element)) < 255:
			self.__buffer__.insert(int(index), element)
		elif isinstance(element, (bytes, bytearray, ByteString)):
			index = int(index)

			for i, byte in enumerate(element):
				self.__buffer__.insert(index + i, byte)
		else:
			raise TypeError('Bytestring elements must be a bytes object, bytearray object, ByteString instance, or integer in the range 0-255')

		return self

	def multisplit(self, sep: typing.Optional[typing.Iterable[int | bytes | bytearray | ByteString]] = ..., maxsplit: int = -1) -> list[ByteString]:
		"""
		Splits the string around multiple delimiters
		:param sep: The delimiters to split around
		:param maxsplit: The maximum number of splits to perform (negative or zero values are infinite)
		:return: A list of the split string
		"""

		segments: list[ByteString] = []
		segment: ByteString = ByteString()
		matches: int = 0

		for i, byte in enumerate(self):
			matched: bool = False

			if maxsplit <= 0 or matches < maxsplit:
				for delimiter in sep:
					if not isinstance(delimiter, (int, bytes, bytearray, ByteString)) or (isinstance(delimiter, int) and not (0 <= (delimiter := int(delimiter)) <= 255)):
						raise TypeError('ByteString delimiter must be an integer in the range 0-255')
					elif (isinstance(delimiter, int) and delimiter == self[i]) or self[i:i + len(delimiter)] == delimiter:
						matches += 1
						segments.append(segment)
						matched = True
						segment = ByteString()
						break

			if not matched:
				segment.append(byte)

		segments.append(segment)
		return [ByteString(seg) for seg in segments]

	@property
	def bytes(self) -> typing.Iterator[bytes]:
		"""
		:return: Each byte as a bytes object instead of an integer
		"""

		for byte in self:
			yield byte.to_bytes(1, sys.byteorder)
