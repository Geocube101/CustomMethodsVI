import collections.abc
import inspect
import typing
import types


class InvalidArgumentException(TypeError):
	"""
	Exception representing an invalid type passed to a parameter
	"""

	def __init__(self, caller: collections.abc.Callable | types.FunctionType | types.MethodType | types.LambdaType = None, parameter_name: str = None, argument_type: type = None, parameter_types: collections.abc.Iterable[type | str] = None, message: str = None):
		"""
		Exception representing an invalid type passed to a parameter
		- Constructor -
		:param caller: The callable that raised this exception or None to locate
		:param parameter_name: The name of the parameter
		:param argument_type: The type of the argument passed in
		:param parameter_types: The types this parameter accepts or the associated type annotations if None
		:param message: Extra message to display
		"""

		if parameter_name is None:
			super().__init__()

		if caller is None:
			parent: types.FrameType = inspect.currentframe().f_back
			caller_names: list[str] = parent.f_code.co_qualname.split('.')
			frame_vars: dict = parent.f_globals | parent.f_locals

			for name, var in frame_vars.items():
				if name == caller_names[0]:
					for subname in caller_names[1:]:
						var = getattr(var, subname)
					caller = var
					break

			if caller is None:
				super().__init__(message if isinstance(message, str) else '')
				return

		if argument_type is None:
			parent: types.FrameType = inspect.currentframe().f_back
			argument: typing.Any = parent.f_locals.get(parameter_name)
			argument_type = type(argument)

			if argument is None:
				super().__init__(message if isinstance(message, str) else '')
				return

		caller_annotations: dict[str, ...] = caller.__annotations__
		annotations: typing.Union | type

		if parameter_types is None and (annotations := caller_annotations.get(parameter_name)) is not None:
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

		try:
			parameters: str = ", ".join(inspect.signature(caller).parameters.keys())
		except ValueError:
			parameters = '...'

		extra: str = f'\n\t...\n{message}' if isinstance(message, str) else ''
		super().__init__(f'\033[0m{callable_type} {caller.__qualname__.replace(".", "::")}({parameters}) - parameter \'\033[38;2;255;0;0m{parameter_name}\033[0m\' must be {type_list}; got \'{argument_type}\'{extra}')


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


__all__: list[str] = ['InvalidArgumentException', 'CorruptError', 'AmbiguousError', 'AlreadyDefinedError', 'IterableEmptyException', 'InaccessibleAttributeException']
