import collections.abc
import typing
import types


class InvalidArgumentException(TypeError):
	"""
	Exception representing an invalid type passed to a parameter
	"""

	def __init__(self, caller: collections.abc.Callable | types.FunctionType | types.MethodType | types.LambdaType = None, parameter_name: str = None, argument_type: type = None, parameter_types: collections.abc.Iterable[type | str] = None):
		"""
		Exception representing an invalid type passed to a parameter
		- Constructor -
		:param caller: The callable that raised this exception
		:param parameter_name: The name of the parameter
		:param argument_type: The type of the argument passed in
		:param parameter_types: The types this parameter accepts or the associated type annotations if None
		"""

		if caller is None or parameter_name is None or argument_type is None:
			super().__init__()
		else:
			if parameter_types is None and parameter_name in caller.__annotations__:
				annotations: types.Union | type = caller.__annotations__[parameter_name]
				parameter_types: tuple[type | str, ...] = (f"'{annotations}'",) if isinstance(annotations, (type, type(typing.Type), str)) else tuple(f"'{x}'" for x in annotations.__args__)
				type_list: str = f'either {", ".join(parameter_types[:-1])}{f" or {parameter_types[-1]}" if len(parameter_types) > 1 else ""}' if len(parameter_types) > 1 else parameter_types[0]
			elif parameter_types is None:
				type_list: str = '<UNKNOWN>'
			else:
				parameter_types: tuple[type | str, ...] = tuple(f"'{x}'" for x in parameter_types)
				type_list: str = f'either {", ".join(parameter_types[:-1])}{f" or {parameter_types[-1]}" if len(parameter_types) > 1 else ""}' if len(parameter_types) > 1 else parameter_types[0]

			callable_type: str = 'Callable'

			if '<lambda>' in caller.__qualname__:
				callable_type = 'Lambda'
			elif '.' in caller.__qualname__:
				callable_type = 'Method'
			elif isinstance(caller, types.FunctionType):
				callable_type = 'Function'

			super().__init__(f'{callable_type} {caller.__qualname__.replace(".", "::")}({", ".join(caller.__code__.co_varnames)}) - parameter \'\033[38;2;255;0;0m{parameter_name}\033[0m\' must be {type_list}; got \'{argument_type}\'')


class CorruptError(RuntimeError):
	"""
	Exception representing invalid data or state
	"""

	def __init__(self, what: str = ''):
		"""
		Exception representing invalid data or state
		- Constructor -
		:param what: The message
		"""

		super().__init__(what)


class AmbiguousError(ValueError):
	"""
	Exception representing ambiguous data or state
	"""

	def __init__(self, what: str = ''):
		"""
		Exception representing ambiguous data or state
		- Constructor -
		:param what: The message
		"""

		super().__init__(what)


class AlreadyDefinedError(BaseException):
	"""
	Exception representing data already set or defined
	"""

	def __init__(self, what: str = ''):
		"""
		Exception representing data already set or defined
		- Constructor -
		:param what: The message
		"""

		super().__init__(what)


class IterableEmptyException(Exception):
	"""
	Exception representing attempt to pull from empty iterable
	"""

	def __init__(self, what: str = ''):
		"""
		Exception representing attempt to pull from empty iterable
		- Constructor -
		:param what: The message
		"""

		super().__init__(what)


class InaccessibleAttributeException(AttributeError):
	"""
	Exception representing attempt access inaccessible attribute
	"""

	def __init__(self, what: str = ''):
		"""
		Exception representing attempt access inaccessible attribute
		- Constructor -
		:param what: The message
		"""

		super().__init__(what)
