import typing
import typeguard


class KVP:
	"""
	[KVP] - Class providing parsing capabilities for the custom KeyValuePair (KVP) data storage format
	"""

	class __FormatMarker:
		"""
		INTERNAL CLASS; DO NOT USE
		Responsible for storing a value and its associated format specifier
		"""

		def __init__(self, value: int | float | str | None, formatter: str):
			self.value = value
			self.formatter = formatter

		def valid(self) -> bool:
			return self.formatter in ('B', 'I', 'X', 'O', 'F', 'D', 'S', '') and (self.value is None or isinstance(self.value, (float, int, str)))

	@classmethod
	def decode(cls, data: str, root_name: str = None) -> 'KVP':
		"""
		Parses a string into a KVP object
		:param data: (str) The data to parse
		:param root_name: (str) The name of the root object
		:return: (KVP) A new KVP object
		:raises KVPDecodeError: If an error occured during decode
		"""

		def _decode_value(line_number: int, line: str, value: str) -> KVP.__FormatMarker:
			if '&' not in value:
				return KVP.__FormatMarker(None, '') if len(value) == 0 else KVP.__FormatMarker(value, 'S')

			format_start: int = value.rindex('&')

			if format_start > 0 and value[format_start - 1] == '%':
				return KVP.__FormatMarker(''.join(x for i, x in enumerate(value) if i != format_start - 1), 'S')

			formatter: str = value[format_start:]
			value: str = value[:format_start]

			if len(value) == 0:
				raise KVPDecodeError(f'Format on empty value - LINE.{line_number + 1} {line}')
			elif formatter == '&B':
				if value == 'true':
					return KVP.__FormatMarker(True, 'B')
				elif value == 'false':
					return KVP.__FormatMarker(False, 'B')
				else:
					try:
						return KVP.__FormatMarker(int(value) != 0, 'B')
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
						return KVP.__FormatMarker((int(value) & (2 ** bit_length - 1)), 'I')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as integer{bit_length}-10 - LINE.{line_number + 1} {line}')

				else:
					try:
						return KVP.__FormatMarker(int(value), 'I')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as integer-10 - LINE.{line_number + 1} {line}')
			elif formatter == '&X':
				if len(bit_length_str := formatter[2:]):
					try:
						bit_length = int(bit_length_str)
					except ValueError:
						raise KVPDecodeError(f'Invalid integer bit-length \'{bit_length_str}\' - LINE.{line_number + 1} {line}')

					if bit_length <= 0:
						raise KVPDecodeError(f'Invalid integer bit-length \'{bit_length_str}\' - LINE.{line_number + 1} {line}')

					try:
						return KVP.__FormatMarker((int(value, 16) & (2 ** bit_length - 1)), 'I')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as integer{bit_length}-16 - LINE.{line_number + 1} {line}')

				else:
					try:
						return KVP.__FormatMarker(int(value, 16), 'I')
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
						return KVP.__FormatMarker((int(value, 8) & (2 ** bit_length - 1)), 'I')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as integer{bit_length}-8 - LINE.{line_number + 1} {line}')

				else:
					try:
						return KVP.__FormatMarker(int(value, 8), 'I')
					except ValueError:
						raise KVPDecodeError(f'Failed to format value \'{value}\' as integer-8 - LINE.{line_number + 1} {line}')
			elif formatter == '&F':
				try:
					return KVP.__FormatMarker(float(value), 'F')
				except ValueError:
					raise KVPDecodeError(f'Failed to format value \'{value}\' as float - LINE.{line_number + 1} {line}')
			elif formatter == '&D':
				try:
					return KVP.__FormatMarker(float(value), 'D')
				except ValueError:
					raise KVPDecodeError(f'Failed to format value \'{value}\' as double - LINE.{line_number + 1} {line}')
			elif formatter == '&S':
				return KVP.__FormatMarker(value, 'S')
			elif formatter == '&':
				raise KVPDecodeError(f'No formatter specified; - LINE.{line_number + 1} {line}')
			else:
				raise KVPDecodeError(f'Formatter is invalid: \'{formatter}\'; expected one of [ B, I, X, O, F, D, S ] - LINE.{line_number + 1} {line}')

		def _decode_inner(inner_line: str | None) -> 'tuple[str, dict[str, list[KVP.__FormatMarker] | dict]]':
			namespace_name: str = '' if inner_line is None else inner_line[2:]
			inner_result: 'dict[str, list[KVP.__FormatMarker] | dict]' = {}

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
					values: list[KVP.__FormatMarker] = []
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
						else:
							token.append(char)

					if len(token) > 0:
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
		result: 'dict[str, list[KVP.__FormatMarker] | KVP]'
		_, result = _decode_inner(None)
		return cls(root_name, result)

	@staticmethod
	def __is_iterable(x) -> bool:
		"""
		INTERNAL METHOD; DO NOT USE
		Checks if an object is iterable
		:param x: (ANY) The object
		:return: (bool) Iterableness
		"""

		try:
			typeguard.check_type(x, typing.Iterable)
			return True
		except typeguard.TypeCheckError:
			return False

	@staticmethod
	def __mark_formatter(val: 'int | float | str | None | KVP.__FormatMarker') -> 'KVP.__FormatMarker':
		"""
		INTERNAL METHOD; DO NOT USE
		Appends the format specifier to a value for storage in a KVP object
		:param val: (int or float or str or None) The value to mark
		:return: (---) The marked value
		"""

		if type(val) is int:
			return KVP.__FormatMarker(val, 'I')
		elif type(val) is float:
			return KVP.__FormatMarker(val, 'F')
		elif val is None:
			return KVP.__FormatMarker(val, '')
		elif type(val) is KVP.__FormatMarker:
			return val
		else:
			return KVP.__FormatMarker(str(val), 'S')

	def __init__(self, namespace_name: str | None, data: 'dict[str, list[int | float | str | None] | list[KVP.__FormatMarker] | KVP | dict]'):
		"""
		[KVP] - Class providing parsing capabilities for the custom KeyValuePair (KVP) data storage format
		- Constructor -
		SHOULD NOT BE CALLED DIRECTLY; USE 'KVP::decode'
		:param namespace_name: (str) The root name
		:param data: (dict) The data to store
		:raises AssertionError: If the data is of an invalid type
		:raises TypeError: If the data is of an invalid type
		"""

		assert type(data) is dict, 'Not a dictionary'
		valid_types: tuple[type, ...] = (int, float, str, type(None), type(self))
		super().__setattr__('__initialized__', False)
		self.__mapping__: dict[str, list[KVP.__FormatMarker] | KVP] = {}
		self.__namespace__: str = f'KVP @ {hex(id(self))} (ROOT)' if namespace_name is None else str(namespace_name)
		key: str
		value: typing.Iterable[KVP.__FormatMarker | int | float | str | None] | KVP | dict | int | float | str | None | KVP.__FormatMarker

		for key, value in data.items():
			if type(value) is dict:
				value = type(self)(key, value)

			elif KVP.__is_iterable(value):
				value = tuple(value)
				assert all((type(x) is KVP.__FormatMarker and x.valid()) or (isinstance(x, valid_types) and not isinstance(x, (type(self), dict))) for x in value)
				value = [KVP.__mark_formatter(x) for x in value]

			elif type(value) is not type(self) and type(value) in valid_types:
				value = [KVP.__mark_formatter(value)]

			else:
				raise TypeError(f'Unstorable type: \'{value}\'')

			self.__mapping__[str(key)] = value

		super().__setattr__('__initialized__', True)

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		def _format(value: KVP.__FormatMarker | KVP | dict | list) -> str | list | dict:
			if type(value) is list:
				return f'[{", ".join(_format(x) for x in value)}]'
			elif type(value) is type(self):
				return f'{{{", ".join(f"{k}: {_format(v)}" for k, v in value.__mapping__.items())}}}'

			formatter: str = value.formatter
			value: str = value.value

			if formatter == 'X':
				return f'{value:X}'
			elif formatter == 'O':
				return f'{value:O}'
			elif formatter == 'S':
				return f'"{value}"' if '\'' in value else f'"""{value}"""' if '\'' in value and '"' in value else f'\'{value}\''
			else:
				return str(value)

		return _format(self)

	def __contains__(self, item: str) -> bool:
		return item in self.__mapping__

	def __getitem__(self, item: str) -> 'list[int | float | str | None] | KVP':
		value = self.__mapping__[item]
		return [x.value for x in value] if type(value) is list else value

	def __getattr__(self, item: str) -> 'list[int | float | str | None] | KVP':
		return self[item]

	def __setitem__(self, key: str, value: 'list[int | float | str | None] | int | float | str | None | KVP | dict'):
		valid_types: tuple[type, ...] = (int, float, str, type(None), type(self))
		key = str(key)

		if type(value) is dict:
			self.__mapping__[key] = KVP(key, value)

		elif not isinstance(value, str) and KVP.__is_iterable(value):
			value: tuple = tuple(value)
			assert all(isinstance(x, valid_types) and not isinstance(x, type(self)) for x in value), f'One or more list values are not one of {valid_types} - \'{value}\''
			self.__mapping__[key] = [KVP.__mark_formatter(x) for x in value]

		elif type(value) is type(self):
			self.__mapping__[key] = value

		elif type(value) in valid_types:
			self.__mapping__[key] = [KVP.__mark_formatter(value)]

		else:
			raise ValueError(f'Expected either an int, float, str, or None, an iterable of such, another KVP object, or a dictionary that can be converted to a KVP object; got \'{type(value)}\'')

	def __setattr__(self, key: str, value):
		if super().__getattribute__('__initialized__'):
			self[key] = value
		else:
			super().__setattr__(key, value)

	def __delitem__(self, key: str):
		del self.__mapping__[key]

	def __delattr__(self, item: str):
		del self.__mapping__[item]

	def __iter__(self) -> 'tuple[str, list[typing.Any] | KVP]':
		for k, v in self.__mapping__.items():
			yield k, v if type(v) is type(self) else [x.value for x in v]

	def keys(self) -> tuple[str, ...]:
		"""
		Gets the keys for this KVP map
		:return: (tuple[str]) The list of keys
		"""

		return tuple(self.__mapping__.keys())

	def values(self) -> tuple[list[typing.Any], ...]:
		"""
		Gets the values for this KVP map
		:return: (tuple[ANY]) The list of values
		"""

		return tuple(x if type(x) is type(self) else [a.value for a in x] for x in self.__mapping__.values())

	def pretty_print(self) -> str:
		"""
		Pretty prints the KVP tree
		:return: (str) The printed tree
		"""

		def _format(value: KVP.__FormatMarker) -> str:
			formatter = value.formatter
			value = value.value

			if formatter == 'X':
				return f'{value:X}'
			elif formatter == 'O':
				return f'{value:O}'
			elif formatter == 'S':
				return f'"{value}"' if '\'' in value else f'"""{value}"""' if '\'' in value and '"' in value else f'\'{value}\''
			else:
				return str(value)

		def _printer(namespace: KVP, indent: int = 1) -> None:
			tab: str = '\t' * indent
			k: str
			v: list[int | float | str | None] | int | float | str | None | KVP

			for k, v in namespace.__mapping__.items():
				if type(v) is type(self):
					output.append(f'{tab}{k}:')
					_printer(v, indent + 1)
				else:
					output.append(f'{tab}{k}=[{", ".join(_format(x) for x in v)}]')

		output: list[str] = [f'{self.__namespace__}:']
		_printer(self)
		return '\n'.join(output)

	def encode(self, explicit_str_format: bool = False) -> str:
		"""
		Converts this KVP object back into a string for writing
		:param explicit_str_format: (bool) If true, values of type str will have the format marker set
		:return: (str) The encoded data
		"""

		def _format(value: KVP.__FormatMarker) -> str:
			formatter = value.formatter
			value = value.value

			if formatter == 'X':
				return f'{value:X}&X'
			elif formatter == 'O':
				return f'{value:O}&O'
			elif formatter == 'F':
				return f'{value}&F'
			elif formatter == 'S':
				return f'{value}&{formatter}' if explicit_str_format else f'{value}'
			elif formatter == 'I':
				return f'{value}&I'
			elif formatter == '':
				return ''
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
