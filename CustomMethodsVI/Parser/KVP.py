from __future__ import annotations

import base64
import typing
import typeguard


class KVP:
	"""
	Class providing parsing capabilities for the custom KeyValuePair (KVP) data storage format
	"""

	class __FormatMarker__:
		"""
		INTERNAL CLASS; DO NOT USE
		Responsible for storing a value and its associated format specifier
		"""

		def __init__(self, value: bool | int | float | str | bytes | None, formatter: str):
			self.value: bool | int | float | str | bytes | None = value
			self.formatter: str = formatter

		def valid(self) -> bool:
			return self.formatter in ('B', 'I', 'L', 'O', 'F', 'D', 'S', 'X', '') and (self.value is None or isinstance(self.value, (bool, float, int, str, bytes)))

	class __ListWrapper__[T](typing.Sized, typing.Iterable[T]):
		def __init__(self, list_: list):
			self.__reference__: list[KVP.__FormatMarker__] = list_

		def __getitem__(self, item: int) -> bool | int | float | str | bytes | None:
			return self.__reference__[item].value

		def __setitem__(self, key: int, value: bool | int | float | str | bytes | None) -> None:
			valid_types: tuple[type, ...] = (bool, int, float, str, bytes, type(None))

			if isinstance(value, valid_types):
				self.__reference__[key] = KVP.__mark_formatter__(value)
			else:
				raise ValueError(f'Expected either an int, float, str, or None; got \'{type(value)}\'')

		def __iter__(self) -> typing.Iterator[bool, int | float | str | bytes | None]:
			for item in self.__reference__:
				yield item.value

		def __len__(self) -> int:
			return len(self.__reference__)

		def __repr__(self) -> str:
			return repr([x.value for x in self.__reference__])

		def __str__(self) -> str:
			return str([x.value for x in self.__reference__])

		def append(self, value: bool | int | float | str | bytes | None) -> None:
			"""
			Appends a value to the end of this list
			:param value: The value to add
			:raises ValueError: If the value is not a boolean, integer, float, string, bytes, or None
			"""

			if value is None or isinstance(value, (bool, int, float, str, bytes)):
				self.__reference__.append(KVP.__mark_formatter__(value))
			else:
				raise ValueError(f'Expected either an int, float, str, or None; got \'{type(value)}\'')

		def clear(self) -> None:
			"""
			Clears this list
			"""

			self.__reference__.clear()

		def copy(self) -> list[bool | int | float | str | bytes | None]:
			"""
			:return: A copy of this list
			"""

			return [x.value for x in self.__reference__]

		def count(self, item: bool | int | float | str | bytes | None) -> int:
			"""
			:param item: The item to count
			:return: The number of occurrences of 'item' in this list
			"""

			count: int = 0

			for x in self.__reference__:
				count += x.value == item

			return count

		def extend(self, iterable: typing.Iterable[bool | int | float | str | bytes | None]) -> None:
			"""
			Adds an iterable to the end of this list
			:param iterable: The iterable to add
			"""

			for item in iterable:
				if item is None or isinstance(item, (int, float, str)):
					self.__reference__.append(KVP.__mark_formatter__(item))
				else:
					raise ValueError(f'Expected either an int, float, str, or None; got \'{type(item)}\'')

		def index(self, item: bool | int | float | str | bytes | None) -> int:
			"""
			:param item: The item to look for
			:return: The item's index in this list or -1 if not found
			"""

			for i, x in enumerate(self.__reference__):
				if x.value == item:
					return i

			return -1

		def insert(self, index: int, item: bool | int | float | str | bytes | None) -> None:
			"""
			Inserts a value at the specified index
			:param index: The index to insert at
			:param item: The value
			:raises ValueError: If the value is not a boolean, integer, float, string, bytes, or None
			"""

			if item is None or isinstance(item, (bool, int, float, str, bytes)):
				self.__reference__.insert(index, KVP.__mark_formatter__(item))
			else:
				raise ValueError(f'Expected either an int, float, str, or None; got \'{type(item)}\'')

		def pop(self, index: int = -1) -> bool | int | float | str | bytes | None:
			"""
			Pops and returns an item from the specified index
			:param index: The index to pop
			:return: The popped item
			"""

			return self.__reference__.pop(index).value

		def remove(self, item: bool | int | float | str | bytes | None) -> None:
			"""
			Removes an item from this list
			:param item: The item to remove
			:raises ValueError: If the item is not in this list
			"""

			for i, x in enumerate(self.__reference__):
				if x.value == item:
					self.__reference__.pop(i)
					return

			raise ValueError('list.remove(x): x not in list')

		def reverse(self) -> None:
			"""
			Reverses this list in-place
			"""

			self.__reference__.reverse()

		def sort(self, *, key: typing.Optional[typing.Callable[[bool | int | float | str | bytes | None], typing.Any]] = None, reverse: bool = False) -> None:
			"""
			Sorts this list in-place
			:param key: The key to sort by
			:param reverse: Whether to reverse the sort order
			"""

			def sorter(wrapper: KVP.__FormatMarker__) -> typing.Any:
				if key is not None and key is not ...:
					return key(wrapper.value)
				else:
					return wrapper.value

			self.__reference__.sort(key=sorter, reverse=reverse)

	@classmethod
	def decode(cls, data: str, root_name: str = None) -> KVP:
		"""
		Parses a string into a KVP object
		:param data: The data to parse
		:param root_name: The name of the root object
		:return: A new KVP object
		:raises KVPDecodeError: If an error occurred during decode
		"""

		def _decode_value(line_number: int, line: str, value: str) -> KVP.__FormatMarker__:
			if '&' not in value:
				return KVP.__FormatMarker__(None, '') if len(value) == 0 else KVP.__FormatMarker__(value, 'S')

			format_start: int = value.rindex('&')

			if format_start > 0 and value[format_start - 1] == '%':
				return KVP.__FormatMarker__(''.join(x for i, x in enumerate(value) if i != format_start - 1), 'S')

			formatter: str = value[format_start:]
			value: str = value[:format_start]

			if len(value) == 0:
				raise KVPDecodeError(f'Format on empty value - LINE.{line_number + 1} {line}')
			elif formatter == '&B':
				if value == 'true':
					return KVP.__FormatMarker__(True, 'B')
				elif value == 'false':
					return KVP.__FormatMarker__(False, 'B')
				else:
					try:
						return KVP.__FormatMarker__(int(value) != 0, 'B')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as boolean - LINE.{line_number + 1} {line}')
			elif formatter.startswith('&I'):
				if len(bit_length_str := formatter[2:]):
					try:
						bit_length = int(bit_length_str)
					except ValueError:
						raise KVPDecodeError(f'Invalid integer bit-length \'{bit_length_str}\' - LINE.{line_number + 1} {line}')

					if bit_length <= 0:
						raise KVPDecodeError(f'Invalid integer bit-length \'{bit_length_str}\' - LINE.{line_number + 1} {line}')

					try:
						return KVP.__FormatMarker__((int(value) & (2 ** bit_length - 1)), 'I')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as integer{bit_length}-10 - LINE.{line_number + 1} {line}')

				else:
					try:
						return KVP.__FormatMarker__(int(value), 'I')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as integer-10 - LINE.{line_number + 1} {line}')
			elif formatter == '&L':
				if len(bit_length_str := formatter[2:]):
					try:
						bit_length = int(bit_length_str)
					except ValueError:
						raise KVPDecodeError(f'Invalid integer bit-length \'{bit_length_str}\' - LINE.{line_number + 1} {line}')

					if bit_length <= 0:
						raise KVPDecodeError(f'Invalid integer bit-length \'{bit_length_str}\' - LINE.{line_number + 1} {line}')

					try:
						return KVP.__FormatMarker__((int(value, 16) & (2 ** bit_length - 1)), 'I')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as integer{bit_length}-16 - LINE.{line_number + 1} {line}')

				else:
					try:
						return KVP.__FormatMarker__(int(value, 16), 'I')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as integer-16 - LINE.{line_number + 1} {line}')
			elif formatter == '&O':
				if len(bit_length_str := formatter[2:]):
					try:
						bit_length = int(bit_length_str)
					except ValueError:
						raise KVPDecodeError(f'Invalid integer bit-length \'{bit_length_str}\' - LINE.{line_number + 1} {line}')

					if bit_length <= 0:
						raise KVPDecodeError(f'Invalid integer bit-length \'{bit_length_str}\' - LINE.{line_number + 1} {line}')

					try:
						return KVP.__FormatMarker__((int(value, 8) & (2 ** bit_length - 1)), 'I')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as integer{bit_length}-8 - LINE.{line_number + 1} {line}')

				else:
					try:
						return KVP.__FormatMarker__(int(value, 8), 'I')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as integer-8 - LINE.{line_number + 1} {line}')
			elif formatter == '&F':
				try:
					return KVP.__FormatMarker__(float(value), 'F')
				except ValueError:
					raise KVPDecodeError(f'Failed to format value \'{value}\' as float - LINE.{line_number + 1} {line}')
			elif formatter == '&D':
				try:
					return KVP.__FormatMarker__(float(value), 'D')
				except ValueError:
					raise KVPDecodeError(f'Failed to format value \'{value}\' as double - LINE.{line_number + 1} {line}')
			elif formatter == '&X':
				return KVP.__FormatMarker__(base64.b64decode(value.encode()), 'X')
			elif formatter == '&S':
				return KVP.__FormatMarker__(value, 'S')
			elif formatter == '&':
				raise KVPDecodeError(f'No formatter specified; - LINE.{line_number + 1} {line}')
			else:
				raise KVPDecodeError(f'Formatter is invalid: \'{formatter}\'; expected one of [ B, I, X, O, F, D, S ] - LINE.{line_number + 1} {line}')

		def _decode_inner(inner_line: str | None) -> tuple[str, dict[str, list[KVP.__FormatMarker__] | dict]]:
			namespace_name: str = '' if inner_line is None else inner_line[2:]
			inner_result: dict[str, list[KVP.__FormatMarker__] | dict] = {}

			for line in lines:
				if len(line) == 0:
					continue
				elif line.startswith('>>'):
					key: str
					value: dict[str, list[int | float | str | None] | dict]
					key, value = _decode_inner(line)
					inner_result[key] = value
				elif (close_namespace := line.startswith('<<')) and inner_line is None:
					raise KVPDecodeError(f'No matching namespace to close - LINE.{line_number + 1} {line}')
				elif close_namespace:
					return namespace_name, inner_result
				elif '=' in line:
					base_index: int = line.index('=')
					length: int = len(line)
					while base_index + 1 < length and line[base_index + 1] == '=': base_index += 1
					key: str = line[:base_index].strip()
					value: str = line[base_index + 1:].strip() if base_index + 1 < length else ''
					values: list[KVP.__FormatMarker__] = []
					token: list[str] = []
					isstring: bool = False

					for i, char in enumerate(value):
						last_char: str = value[i - 1] if i > 0 else None

						if char == '"':
							isstring = False if isstring and last_char != '\\' else True if not isstring and last_char != '%' else isstring

							if isstring and last_char == '\\':
								token[-1] = char
							else:
								token.append(char)
						elif char == ';' and not isstring and last_char != '%':
							values.append(_decode_value(line_number, line, ''.join(token)))
							token.clear()
						elif char == ';' and not isstring and last_char == '%':
							token[-1] = char
						else:
							token.append(char)

					values.append(_decode_value(line_number, line, ''.join(token)))

					if isstring:
						raise KVPDecodeError(f'Unclosed string: \'{"".join(token)}\' - LINE.{line_number + 1} {line}')

					inner_result[key] = values
				else:
					raise KVPDecodeError(f'Line is neither a namespace declaration nor a key value pair - LINE.{line_number + 1} {line}')

			if inner_line is not None:
				raise KVPDecodeError(f'Unclosed namespace: \'{namespace_name}\' - LINE.{line_number + 1} {inner_line}')
			else:
				return namespace_name, inner_result

		def _line_getter():
			nonlocal line_number
			line_number = 0

			for x in data.split('\n'):
				yield x.strip()
				line_number += 1

		line_number: int = 1
		lines: typing.Generator[str] = _line_getter()
		result: dict[str, list[KVP.__FormatMarker__] | KVP]
		_, result = _decode_inner(None)
		return cls(root_name, result)

	@staticmethod
	def __is_iterable(x) -> bool:
		"""
		INTERNAL METHOD; DO NOT USE
		:param x: The object
		:return: Whether an object is iterable
		"""

		try:
			typeguard.check_type(x, typing.Iterable)
			return True
		except typeguard.TypeCheckError:
			return False

	@staticmethod
	def __mark_formatter__(val: bool | int | float | str | bytes | None | KVP.__FormatMarker__) -> KVP.__FormatMarker__:
		"""
		INTERNAL METHOD; DO NOT USE
		Appends the format specifier to a value for storage in a KVP object
		:param val: (The value to mark
		:return: The marked value
		"""

		if isinstance(val, bool):
			return KVP.__FormatMarker__(val, 'B')
		elif isinstance(val, int):
			return KVP.__FormatMarker__(val, 'I')
		elif isinstance(val, float):
			return KVP.__FormatMarker__(val, 'F')
		elif val is None:
			return KVP.__FormatMarker__(val, '')
		elif isinstance(val, KVP.__FormatMarker__):
			return val
		elif isinstance(val, bytes):
			return KVP.__FormatMarker__(val, 'X')
		else:
			return KVP.__FormatMarker__(str(val), 'S')

	def __init__(self, namespace_name: str | None, data: dict[str, list[int | float | str | bytes | None] | list[KVP.__FormatMarker__] | KVP | dict]):
		"""
		Class providing parsing capabilities for the custom KeyValuePair (KVP) data storage format
		- Constructor -
		SHOULD NOT BE CALLED DIRECTLY; USE 'KVP::decode'
		:param namespace_name: The root name
		:param data: The data to store
		:raises AssertionError: If the data is of an invalid type
		:raises TypeError: If the data is of an invalid type
		"""

		assert type(data) is dict, 'Not a dictionary'
		valid_types: tuple[type, ...] = (bool, int, float, str, type(None), type(self), bytes, bytearray)
		super().__setattr__('__initialized__', False)
		self.__mapping__: dict[str, list[KVP.__FormatMarker__] | KVP] = {}
		self.__namespace__: str = f'KVP @ {hex(id(self))} (ROOT)' if namespace_name is None else str(namespace_name)
		key: str
		value: typing.Iterable[KVP.__FormatMarker__ | bool | int | float | str | bytes | None] | KVP | dict | bool | int | float | str | bytes | None | KVP.__FormatMarker__

		for key, value in data.items():
			if type(value) is dict:
				value = type(self)(key, value)

			elif KVP.__is_iterable(value):
				value = tuple(value)
				assert all((type(x) is KVP.__FormatMarker__ and x.valid()) or (isinstance(x, valid_types) and not isinstance(x, (type(self), dict))) for x in value)
				value = [KVP.__mark_formatter__(x) for x in value]

			elif type(value) is not type(self) and type(value) in valid_types:
				value = [KVP.__mark_formatter__(value)]

			else:
				raise TypeError(f'Unstorable type: \'{value}\'')

			self.__mapping__[str(key)] = value

		super().__setattr__('__initialized__', True)

	def __len__(self) -> int:
		return len(self.__mapping__)

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		def _format(value: KVP.__FormatMarker__ | KVP | dict | list) -> str | list | dict:
			if type(value) is list:
				return f'[{", ".join(_format(x) for x in value)}]'
			elif type(value) is type(self):
				return f'{{{", ".join(f"{k}: {_format(v)}" for k, v in value.__mapping__.items())}}}'

			formatter: str = value.formatter
			value: str = value.value

			if formatter == 'B':
				return str(bool(value)).lower()
			elif formatter == 'L':
				return f'{value:X}'
			elif formatter == 'O':
				return f'{value:O}'
			elif formatter == 'S':
				return f'"{value}"' if '\'' in value else f'"""{value}"""' if '\'' in value and '"' in value else f'\'{value}\''
			elif formatter == 'X':
				return f'b"{value}"'
			else:
				return str(value)

		return _format(self)

	def __contains__(self, item: str) -> bool:
		"""
		:param item: The mapping key
		:return: Whether the specified key exists
		"""

		return item in self.__mapping__

	def __getitem__(self, item: str) -> KVP.__ListWrapper__[bool | int | float | str | bytes | None] | KVP:
		"""
		Gets the specified mapping value
		:param item: The mapping key
		:return: The associated map value
		:raises AssertionError: If the key is not a string
		"""

		assert isinstance(item, str), f'KVP key must be \'str\', got \'{type(item)}\''
		value = self.__mapping__[item]
		return KVP.__ListWrapper__(value) if isinstance(value, list) else value

	def __getattr__(self, item: str) -> KVP.__ListWrapper__[bool | int | float | str | bytes | None] | KVP:
		"""
		Gets the specified mapping value
		:param item: The mapping key
		:return: The associated map value
		:raises AssertionError: If the key is not a string
		"""

		return self[item]

	def __setitem__(self, key: str, value: typing.Iterable[bool | int | float | str | bytes | None] | bool | int | float | str | bytes | None | KVP | dict) -> None:
		"""
		Sets the specified mapping key to a value
		:param key: The mapping key
		:param value: The new value
		:raises AssertionError: If the key is not a string
		:raises ValueError: If the value is not a bool, int, float, string, None, iterable of such, a KVP map or dict
		"""

		assert isinstance(key, str), f'KVP key must be \'str\', got \'{type(key)}\''
		valid_types: tuple[type, ...] = (bool, int, float, str, type(None), type(self))
		key = str(key)

		if isinstance(value, typing.Mapping):
			self.__mapping__[key] = KVP(key, value)

		elif not isinstance(value, str) and KVP.__is_iterable(value):
			value: tuple = tuple(value)
			assert all(isinstance(x, valid_types) and not isinstance(x, type(self)) for x in value), f'One or more list values are not one of {valid_types} - \'{value}\''
			self.__mapping__[key] = [KVP.__mark_formatter__(x) for x in value]

		elif isinstance(value, type(self)):
			self.__mapping__[key] = value

		elif isinstance(value, valid_types):
			self.__mapping__[key] = [KVP.__mark_formatter__(value)]

		else:
			raise ValueError(f'Expected either a bool, int, float, str, or None, an iterable of such, another KVP object, or a dictionary that can be converted to a KVP object; got \'{type(value)}\'')

	def __setattr__(self, key: str, value: list[bool | int | float | str | bytes | None] | bool | int | float | str | bytes | None | KVP | dict) -> None:
		"""
		Sets the specified mapping key to a value
		:param key: The mapping key
		:param value: The new value
		:raises AssertionError: If the key is not a string
		:raises ValueError: If the value is not a bool, int, float, string, None, iterable of such, a KVP map or dict
		"""

		if super().__getattribute__('__initialized__'):
			self[key] = value
		else:
			super().__setattr__(key, value)

	def __delitem__(self, key: str):
		"""
		Deletes the specified mapping key
		:param key: The mapping key
		:return: The associated map value
		:raises AssertionError: If the key is not a string
		"""

		assert isinstance(key, str), f'KVP key must be \'str\', got \'{type(key)}\''
		del self.__mapping__[key]

	def __delattr__(self, item: str):
		"""
		Deletes the specified mapping key
		:param key: The mapping key
		:return: The associated map value
		:raises AssertionError: If the key is not a string
		"""

		assert isinstance(item, str), f'KVP key must be \'str\', got \'{type(item)}\''
		del self.__mapping__[item]

	def __iter__(self) -> tuple[str, list[typing.Any] | KVP]:
		for k, v in self.__mapping__.items():
			yield k, v if type(v) is type(self) else [x.value for x in v]

	def keys(self) -> tuple[str, ...]:
		"""
		:return: The keys of this KVP map
		"""

		return tuple(self.__mapping__.keys())

	def values(self) -> tuple[list[typing.Any], ...]:
		"""
		:return: The values of this KVP map
		"""

		return tuple(x if type(x) is type(self) else [a.value for a in x] for x in self.__mapping__.values())

	def pretty_print(self, tab_size: int = 1) -> str:
		"""
		Pretty prints the KVP tree
		:param tab_size: The tab size
		:return: The printed tree
		:raises AssertionError: If tab size is not an integer or is negative
		"""

		def _format(value: KVP.__FormatMarker__) -> str:
			formatter = value.formatter
			value = value.value

			if formatter == 'B':
				return str(bool(value)).lower()
			elif formatter == 'L':
				return f'{value:X}'
			elif formatter == 'O':
				return f'{value:O}'
			elif formatter == 'S':
				return f'"{value}"' if '\'' in value else f'"""{value}"""' if '\'' in value and '"' in value else f'\'{value}\''
			elif formatter == 'X':
				return f'b"{value}"'
			else:
				return str(value)

		def _printer(namespace: KVP, indent: int = 1) -> None:
			tab: str = '\t' * indent * tab_size
			k: str
			v: list[bool | int | float | str | bytes | None] | bool | int | float | str | bytes | None | KVP

			for k, v in namespace.__mapping__.items():
				if type(v) is type(self):
					output.append(f'{tab}{k}:')
					_printer(v, indent + 1)
				else:
					output.append(f'{tab}{k}=[{", ".join(_format(x) for x in v)}]')

		assert isinstance(tab_size, int) and (tab_size := int(tab_size)) > 0, 'Invalid tab size'
		output: list[str] = [f'{self.__namespace__}:']
		_printer(self)
		return '\n'.join(output)

	def encode(self, explicit_str_format: bool = False) -> str:
		"""
		Converts this KVP object back into a string for writing
		:param explicit_str_format: If true, values of type str will have the format marker set
		:return: The encoded data
		:raises KVPEncodeError: If an error occurred during encode
		"""

		def _format(value: KVP.__FormatMarker__) -> str:
			formatter = value.formatter
			value = value.value

			if value is None:
				return ''
			elif formatter == 'B':
				return f'{"true" if value else "false"}&B'
			elif formatter == 'L':
				return f'{value:X}&L'
			elif formatter == 'O':
				return f'{value:O}&O'
			elif formatter == 'F':
				return f'{value}&F'
			elif formatter == 'S':
				return f'{value}&{formatter}' if explicit_str_format else f'{value}'
			elif formatter == 'I':
				return f'{value}&I'
			elif formatter == 'X':
				return f'{base64.b64encode(value).decode()}&X'
			else:
				raise KVPEncodeError(f'Invalid format specifier: \'{formatter}\'')

		output: list[str] = []

		def _encode(kvp: KVP, indent: int = 0):
			tab: str = '\t' * indent

			for k, v in kvp.__mapping__.items():
				if type(v) is type(self):
					output.append(f'{tab}>>{k}')
					_encode(v, indent + 1)
					output.append(f'{tab}<<')
				else:
					output.append(f'{tab}{k}={";".join(_format(val) for val in v)}')

		_encode(self)
		return '\n'.join(output)


class KVPDecodeError(ValueError):
	pass


class KVPEncodeError(ValueError):
	pass
