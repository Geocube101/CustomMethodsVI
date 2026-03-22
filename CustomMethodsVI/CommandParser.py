from __future__ import annotations

import collections.abc
import re
import shlex
import sys
import typing

from . import Exceptions
from . import Misc
from .Iterable import String
from . import Stream


class CommandException(ValueError):
	pass


class MutualExclusionException(CommandException):
	pass


class ArgumentRequiredException(CommandException):
	pass


class ParserArgumentOverride(StopIteration):
	def __init__(self, command: Command, parent: Command, group: CommandArgumentGroup, argument: CommandArgument, values: tuple[typing.Any, ...]):
		Misc.raise_ifn(isinstance(command, Command), Exceptions.InvalidArgumentException(parameter_name='command'))
		Misc.raise_ifn(isinstance(parent, Command), Exceptions.InvalidArgumentException(parameter_name='parent'))
		Misc.raise_ifn(isinstance(group, CommandArgumentGroup), Exceptions.InvalidArgumentException(parameter_name='group'))
		Misc.raise_ifn(isinstance(argument, CommandArgument), Exceptions.InvalidArgumentException(parameter_name='argument'))
		Misc.raise_ifn(isinstance(values, tuple), Exceptions.InvalidArgumentException(parameter_name='values'))

		self.__command__: Command = command
		self.__parent__: Command = parent
		self.__group__: CommandArgumentGroup = group
		self.__argument__: CommandArgument = argument
		self.__values__: tuple[typing.Any, ...] = tuple(values)

	@property
	def command(self) -> Command:
		return self.__command__

	@property
	def parent(self) -> Command:
		return self.__parent__

	@property
	def argument_group(self) -> CommandArgumentGroup:
		return self.__group__

	@property
	def argument(self) -> CommandArgument:
		return self.__argument__

	@property
	def values(self) -> tuple[typing.Any, ...]:
		return self.__values__


class NoCommandHandlerException(RuntimeError):
	pass


class CommandArgument:
	def __init__(self, name: str, *, description: str = '', min_count: int = 0, max_count: int = None, named: bool = False, aliases: typing.Iterable[str] = ..., default: typing.Any = ..., override_parsing: bool = False, store: str = ...):
		"""
		Class representing a single command line argument
		:param name: The argument name
		:param description: The argument description
		:param min_count: The minimum number of arguments that must be supplied
		:param max_count: The maximum number of arguments that must be supplied
		:param named: Whether the argument name must be explicitly supplied
		:param aliases: The alternate names that can be used to trigger this argument
		:param default: The default value if no command line value is supplied
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		"""

		max_count = 0xFFFFFFFFFFFFFFFF if max_count is None else max_count
		Misc.raise_ifn(isinstance(name, str) and len(name := str(name)) > 0, Exceptions.InvalidArgumentException(parameter_name='name', message='\'name\' must be a non-empty string'))
		Misc.raise_ifn(isinstance(description, str), Exceptions.InvalidArgumentException(parameter_name='description'))
		Misc.raise_ifn(isinstance(min_count, int) and (min_count := int(min_count)) >= 0, Exceptions.InvalidArgumentException(parameter_name='min_count', message='\'min_count\' must be an integer >= 0'))
		Misc.raise_ifn(isinstance(max_count, int) and (max_count := int(max_count)) >= min_count, Exceptions.InvalidArgumentException(parameter_name='max_count', message='\'max_count\' must be an integer >= \'min_count\''))
		Misc.raise_ifn(aliases is ... or (isinstance(aliases, typing.Iterable) and len(aliases := tuple(aliases)) >= 0 and all(isinstance(x, str) for x in aliases)), Exceptions.InvalidArgumentException(parameter_name='aliases'))
		Misc.raise_ifn(store is ... or (isinstance(store, str) and len(store := str(store)) > 0), Exceptions.InvalidArgumentException(parameter_name='store', message='\'store\' must be a non-empty string'))

		self.__argument_name__: str = name
		self.__description__: str = str(description)
		self.__count__: tuple[int, int] = (min_count, max_count)
		self.__named__: bool = bool(named)
		self.__override__: bool = bool(override_parsing)
		self.__aliases__: tuple[str, ...] = () if aliases is ... else aliases
		self.__default__: typing.Any = default
		self.__store__: str = store

		for name in self.get_names():
			if not self.is_name_valid(name):
				raise ValueError(f'Invalid name \'{name}\' for argument of type \'{type(self).__name__}\'')

	def is_name(self, name: str) -> bool:
		"""
		:param name: The name to check
		:return: Whether 'name' is a name or alias of this argument
		"""

		return isinstance(name, str) and name in self.get_names()

	def is_name_valid(self, name: str) -> bool:
		"""
		*Abstract Method*
		:param name: The name to check
		:return: Whether 'name' should be a valid name for this argument (If false, will throw error)
		"""

		return True

	def get_help_string(self) -> str:
		"""
		:return: The help string for this command argument
		"""

		sstream: Stream.StringStream = Stream.StringStream()
		sstream.write(f'{self.name}')

		if len(self.aliases) > 1:
			sstream.write(f' (AKA {", ".join(self.aliases[:-1])}')
			sstream.write(f' or {self.aliases[-1]})')
		elif len(self.aliases) == 1:
			sstream.write(f' (AKA {self.aliases[0]})')

		sstream.write(' - ')

		if self.min_nargs == self.max_nargs and self.min_nargs == 1:
			sstream.write(f'Accepts exactly {self.min_nargs} value')
		elif self.min_nargs == self.max_nargs:
			sstream.write(f'Accepts exactly {self.min_nargs} values')
		else:
			sstream.write(f'Accepts between {self.min_nargs} and {self.max_nargs} values')

		if self.is_required:
			sstream.write(' (REQUIRED)')

		if len(self.description) > 0:
			sstream.write(f': {self.description}')

		return sstream.read()

	def get_names(self) -> typing.Iterator[str]:
		"""
		:return: The primary name and all aliases for this argument
		"""

		yield self.name
		yield from self.aliases

	def match(self, arguments: list[String.String]) -> tuple[int, typing.Optional[tuple[typing.Any, ...]]]:
		"""
		Matches this argument with input
		Greedily consumes command line arguments from the queue
		:param arguments: The command line arguments
		:return: A tuple containing the number of arguments matched and the resolved values
		"""

		matched: list[typing.Any] = []

		for i in range(self.max_nargs):
			if i >= len(arguments):
				break

			argument: String.String = arguments[i]
			success, result = self.single_match(argument)

			if success:
				matched.append(result)
			else:
				break

		if len(matched) < self.min_nargs:
			return 0, None

		return len(matched), tuple(matched)

	def single_match(self, argument: String.String) -> tuple[bool, typing.Any]:
		"""
		*Abstract Method*
		Matches a single command line argument
		:param argument: The argument to match
		:return: Whether the argument was matched and the resolved value
		"""

		return False, None

	def resolve(self, values: typing.Iterable[typing.Any]) -> typing.Any:
		"""
		* Abstract Method *\n
		Finalizes the resolved values of an argument's command line arguments
		:param values: The values as converted from the parser
		:return: The return value(s)
		"""

		return values

	def get_default(self) -> tuple[typing.Any, ...]:
		"""
		:return: This argument's default value as should be added to the tree
		"""

		default: typing.Any = self.default
		return () if default is ... else tuple(default) if isinstance(default, tuple) else (default,)

	@property
	def name(self) -> str:
		"""
		:return: This argument's name
		"""

		return self.__argument_name__

	@property
	def store_name(self) -> str:
		"""
		:return: The name to store this argument's values as in the parsed CommandArguments object
		"""

		return self.name if self.__store__ is ... else self.__store__

	@property
	def description(self) -> str:
		"""
		:return: This argument's description
		"""

		return self.__description__

	@property
	def is_required(self) -> bool:
		"""
		:return: Whether this argument is required (min_count > 0)
		"""

		return self.min_nargs > 0

	@property
	def is_named(self) -> bool:
		"""
		:return: Whether this argument's name must be explicitly supplied
		"""

		return self.__named__

	@property
	def override_parsing(self) -> bool:
		"""
		:return: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		"""

		return self.__override__

	@property
	def min_nargs(self) -> int:
		"""
		:return: This argument's minimum count
		"""

		return self.__count__[0]

	@property
	def max_nargs(self) -> int:
		"""
		:return: This argument's maximum count
		"""

		return self.__count__[1]

	@property
	def aliases(self) -> tuple[str, ...]:
		"""
		:return: This argument's aliases
		"""

		return self.__aliases__

	@property
	def default(self) -> typing.Any:
		"""
		:return: This argument's default value
		"""

		return self.__default__


class LiteralCommandArgument(CommandArgument):
	__TYPE_CONVERTERS: dict[str, type] = {
		'bit': int, 'bool': bool, 'boolean': bool,
		'char': int, 'wchar': int, 'int8': int, 'uint8': int,
		'short': int, 'int16': int, 'uint16': int,
		'int': int, 'integer': int, 'int32': int, 'uint32': int,
		'long': int, 'int64': int, 'uint64': int,
		'float': float, 'double': float,
		'str': str, 'string': str,
	}

	__SORTED_TYPES: tuple[type, ...] = (bool, int, float, str)

	@staticmethod
	def __convert_string_to_type(typestr: str | type) -> type:
		if isinstance(typestr, type):
			return typestr
		elif not isinstance(typestr, str):
			raise TypeError(f'Expected string, got \'{type(typestr).__name__}\'')
		elif (converted := LiteralCommandArgument.__TYPE_CONVERTERS.get(typestr)) is not None:
			return converted

		variables: dict = globals() | locals()

		for name, variable in variables.items():
			if name == typestr and isinstance(variable, type):
				return variable

		raise ValueError(f'Failed to deduce type from string: \'{typestr}\'')

	@staticmethod
	def convert_argument_to_type(argument_value: String.String, argument_type: type) -> typing.Any:
		"""
		Converts an input value to the specified type
		:param argument_value: The input value
		:param argument_type: The target  type
		:return: The converted value
		:raises ValueError: If the target type is not supported or casting failed
		"""

		lowered: String.String = argument_value.lower()

		if argument_type is bool and (lowered == 'true' or lowered == '1'):
			return True
		elif argument_type is bool and (lowered == 'false' or lowered == '0'):
			return False
		elif argument_type is int:
			result: int = argument_value.literal_to_number()

			if not isinstance(result, int):
				raise ValueError('Not an integer')

			return result
		elif argument_type is float:
			return argument_value.to_extended_float()
		elif argument_type is str:
			return argument_value
		else:
			raise ValueError(f'Unsupported type: \'{argument_type.__name__}\'')

	def __init__(self, name: str, *, description: str = '', min_count: int = 0, max_count: int = None, named: bool = False, pattern: str = '', allowed_types: typing.Iterable[str | type] = (), default: typing.Any = ..., aliases: typing.Iterable[str] = ..., override_parsing: bool = False, store: str = ...):
		"""
		Class representing a single literal command line argument
		:param name: The argument name
		:param description: The argument description
		:param min_count: The minimum number of arguments that must be supplied
		:param max_count:The maximum number of arguments that must be supplied
		:param named: Whether the argument name must be explicitly supplied
		:param pattern: The regex pattern to match potential input values against
		:param allowed_types: A set of types the input must be convertable to
		:param default: The default value if no command line value is supplied
		:param aliases: The alternate names that can be used to trigger this argument
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		"""

		super().__init__(name, description=description, min_count=min_count, max_count=max_count, named=named, aliases=aliases, default=default, override_parsing=override_parsing, store=store)
		Misc.raise_ifn(isinstance(pattern, str), Exceptions.InvalidArgumentException(parameter_name='pattern'))
		Misc.raise_ifn(isinstance(allowed_types, typing.Iterable) and len(allowed_types := tuple(allowed_types)) >= 0 and all(isinstance(t, (str, type)) for t in allowed_types), Exceptions.InvalidArgumentException(parameter_name='allowed_types'))
		types: tuple[type, ...] = tuple(LiteralCommandArgument.__convert_string_to_type(x) for x in allowed_types)
		self.__pattern__: str = str(pattern)
		self.__allowed_types__: tuple[type, ...] = tuple(allowed for allowed in LiteralCommandArgument.__SORTED_TYPES if allowed in types)

	def get_help_string(self) -> str:
		sstream: Stream.StringStream = Stream.StringStream()
		sstream.write(f'{self.name}')

		if len(self.aliases) > 1:
			sstream.write(f' (AKA {", ".join(self.aliases[:-1])}')
			sstream.write(f' or {self.aliases[-1]})')
		elif len(self.aliases) == 1:
			sstream.write(f' (AKA {self.aliases[0]})')

		sstream.write(' - ')

		if self.min_nargs == self.max_nargs and self.min_nargs == 1:
			sstream.write(f'Accepts exactly {self.min_nargs} value')
		elif self.min_nargs == self.max_nargs:
			sstream.write(f'Accepts exactly {self.min_nargs} values')
		else:
			sstream.write(f'Accepts between {self.min_nargs} and {self.max_nargs} values')

		if self.is_required:
			sstream.write(' (REQUIRED)')

		if len(self.types) == 1:
			sstream.write(f' of type {self.types[0].__name__}')
		elif len(self.types) == 2:
			sstream.write(f' of types {self.types[0].__name__} or {self.types[1].__name__}')
		elif len(self.types) > 2:
			sstream.write(f' of types {", ".join(t.__name__ for t in self.types[:-1])} or {self.types[-1].__name__}')

		if len(self.description) > 0:
			sstream.write(f': {self.description}')

		return sstream.read()

	def single_match(self, argument: String.String) -> tuple[bool, typing.Any]:
		if len(self.pattern) > 0 and re.fullmatch(self.pattern, argument) is None:
			return False, None
		elif len(self.types) == 0:
			return True, argument

		for allowed in self.types:
			try:
				return True, LiteralCommandArgument.convert_argument_to_type(argument, allowed)
			except ValueError:
				continue

		return False, None

	@property
	def pattern(self) -> str:
		"""
		:return: This argument's pattern. Empty patterns will not be matched
		"""

		return self.__pattern__

	@property
	def types(self) -> tuple[type, ...]:
		"""
		:return: This argument's allowed types
		"""

		return self.__allowed_types__


class FlagCommandArgument(CommandArgument):
	def __init__(self, name: str, *, description: str = '', min_count: int = 0, max_count: int = None, aliases: typing.Iterable[str] = ..., override_parsing: bool = False, store: str = ...):
		"""
		Class representing a single command line flag
		:param name: The flag name
		:param description: The flag description
		:param min_count: The minimum number of flags that must be supplied
		:param max_count:The maximum number of flags that must be supplied
		:param aliases: The alternate names that can be used to trigger this flag
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		"""

		super().__init__(name, description=description, min_count=min_count, max_count=max_count, named=False, aliases=aliases, override_parsing=override_parsing, store=store)

	def is_name_valid(self, name: str) -> bool:
		return re.fullmatch(r'-[a-zA-Z]', name) is not None or re.fullmatch(r'--[a-zA-Z]+', name) is not None

	def resolve(self, values: typing.Iterable[typing.Any]) -> typing.Any:
		return Stream.LinqStream(values).count()

	def single_match(self, argument: String.String) -> tuple[bool, typing.Any]:
		return self.is_name(argument), argument

	@property
	def default(self) -> typing.Any:
		return ()


class BooleanFlagCommandArgument(FlagCommandArgument):
	def __init__(self, name: str, *, description: str = '', inverted: bool = False, aliases: typing.Iterable[str] = ..., override_parsing: bool = False, store: str = ...):
		"""
		Class representing a single command line boolean flag
		:param name: The flag name
		:param description: The flag description
		:param inverted: Whether the stored value is inverted (false when applied instead of true)
		:param aliases: The alternate names that can be used to trigger this flag
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		"""

		super().__init__(name, description=description, min_count=0, max_count=1, aliases=aliases, override_parsing=override_parsing, store=store)
		self.__inverted__: bool = bool(inverted)

	def resolve(self, values: typing.Iterable[typing.Any]) -> typing.Any:
		result: bool = Stream.LinqStream(values).any()
		return not result if self.is_inverted else result

	@property
	def is_inverted(self) -> bool:
		"""
		:return: Whether the stored value is inverted (false when applied instead of true)
		"""

		return self.__inverted__


class HelpCommandArgument(BooleanFlagCommandArgument):
	def __init__(self):
		"""
		Class representing a single help command line argument (--help, -h)
		"""

		super().__init__('--help', description='Displays help and exits', inverted=False, aliases=('-h',), override_parsing=True, store='help')


class ChoicesCommandArgument(CommandArgument):
	def __init__(self, name: str, choices: typing.Iterable[str], *, description: str = '', min_count: int = 0, max_count: int = None, named: bool = False, default: typing.Any = ..., aliases: typing.Iterable[str] = ..., override_parsing: bool = False, store: str = ...):
		"""
		Class representing a single choice command line argument
		:param name: The argument name
		:param choices: The allowed choices an input can be
		:param description: The argument description
		:param min_count: The minimum number of arguments that must be supplied
		:param max_count:The maximum number of arguments that must be supplied
		:param named: Whether the argument name must be explicitly supplied
		:param default: The default value if no command line value is supplied
		:param aliases: The alternate names that can be used to trigger this argument
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		"""

		super().__init__(name, description=description, min_count=min_count, max_count=max_count, named=named, aliases=aliases, default=default, override_parsing=override_parsing, store=store)
		Misc.raise_ifn(isinstance(choices, typing.Iterable) and len(choices := tuple(choices)) > 0 and all(isinstance(x, str) for x in choices), Exceptions.InvalidArgumentException(parameter_name='choices', message='Choices must be an iterable of strings with a length above 0'))
		self.__choices__: tuple[str, ...] = choices

	def get_help_string(self) -> str:
		sstream: Stream.StringStream = Stream.StringStream()
		sstream.write(f'{self.name}')

		if len(self.aliases) > 1:
			sstream.write(f' (AKA {", ".join(self.aliases[:-1])}')
			sstream.write(f' or {self.aliases[-1]})')
		elif len(self.aliases) == 1:
			sstream.write(f' (AKA {self.aliases[0]})')

		sstream.write(' - ')

		if self.min_nargs == self.max_nargs and self.min_nargs == 1:
			sstream.write(f'Accepts exactly {self.min_nargs} value')
		elif self.min_nargs == self.max_nargs:
			sstream.write(f'Accepts exactly {self.min_nargs} values')
		else:
			sstream.write(f'Accepts between {self.min_nargs} and {self.max_nargs} values')

		if self.is_required:
			sstream.write(' (REQUIRED)')

		if len(self.choices) == 1:
			sstream.write(f' equaling {self.choices[0]}')
		elif len(self.choices) == 2:
			sstream.write(f' either {self.choices[0]} or {self.choices[1]}')
		elif len(self.choices) > 2:
			sstream.write(f' either {", ".join(self.choices[:-1])} or {self.choices[-1]}')

		if len(self.description) > 0:
			sstream.write(f': {self.description}')

		return sstream.read()

	def single_match(self, argument: String.String) -> tuple[bool, typing.Any]:
		return argument in self.choices, argument

	@property
	def is_required(self) -> bool:
		return super().is_required and len(self.choices) > 0

	@property
	def choices(self) -> tuple[str, ...]:
		"""
		:return: This argument's allowed choices
		"""

		return self.__choices__


class CommandArgumentGroup:
	def __init__(self, name: str, description: str = '', is_mutually_exclusive: bool = False, is_required: bool = False):
		"""
		Class representing a group of command arguments
		:param name: The group name
		:param description: The group description
		:param is_mutually_exclusive: Whether only one subgroup or command argument may be specified
		:param is_required: Whether one subgroup or command argument must be supplied (only for mutually exclusive groups)
		"""

		Misc.raise_ifn(isinstance(name, str) and len(name := str(name)) > 0, Exceptions.InvalidArgumentException(parameter_name='name', message='\'name\' must be a non-empty string'))
		Misc.raise_ifn(isinstance(description, str), Exceptions.InvalidArgumentException(parameter_name='description'))

		self.__group_name__: str = name
		self.__description__: str = str(description)
		self.__mutually_exclusive__: bool = bool(is_mutually_exclusive)
		self.__required__: bool = bool(is_required)
		self.__arguments__: list[CommandArgument] = []
		self.__groups__: list[CommandArgumentGroup] = []

	def get_help_string(self, *, indent: int = 0) -> str:
		"""
		:return: The help string for this command argument group
		"""

		assert isinstance(indent, int) and (indent := int(indent)) >= 0
		tab: str = '  ' * indent
		sstream: Stream.StringStream = Stream.StringStream()

		if self.is_mutually_exclusive:
			sstream.write(f'{tab}Mutually Exclusive Argument Group [ {self.name} ]')
		else:
			sstream.write(f'{tab}Argument Group [ {self.name} ]')

		if self.is_required:
			sstream.write(' (REQUIRED)')

		arguments: tuple[CommandArgument, ...] = tuple(self.get_command_arguments())
		groups: tuple[CommandArgumentGroup, ...] = tuple(self.get_sub_groups())

		if len(arguments) > 0:
			sstream.write(f'\n{tab}    Arguments:')

			for argument in arguments:
				sstream.write(f'\n{tab}      * {argument.get_help_string()}')

		if len(groups) > 0:
			sstream.write(f'\n{tab}    Argument Groups:')

			for group in groups:
				sstream.write(f'\n{tab}{group.get_help_string(indent=indent + 2)}')

		return sstream.read()

	def add_argument(self, argument: CommandArgument) -> None:
		"""
		Adds an argument to this argument group
		:param argument: The argument to add
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		Misc.raise_ifn(isinstance(argument, CommandArgument), Exceptions.InvalidArgumentException(parameter_name='argument'))

		for name in argument.get_names():
			if self.get_child_by_name(name) is not None:
				raise NameError(f'An object in this group already has the name: \'{name}\'')

		Misc.warn_if(argument.is_required and self.is_mutually_exclusive, RuntimeWarning('Use of required argument in mutually exclusive argument group - If an argument must be supplied, set the parent group \'required\' attribute to \'True\''))
		self.__arguments__.append(argument)

	def create_literal_argument(self, name: str, *, description: str = '', min_count: int = 0, max_count: int = None, named: bool = False, pattern: str = '', allowed_types: typing.Iterable[str | type] = (), aliases: typing.Iterable[str] = ..., default: typing.Any = ..., override_parsing: bool = False, store: str = ...) -> LiteralCommandArgument:
		"""
		Creates a literal argument and adds it to this argument group
		:param name: The argument name
		:param description: The argument description
		:param min_count: The minimum number of accepted command line arguments
		:param max_count: The maximum number of accepted command line arguments
		:param named: Whether the argument name must be explicitly supplied
		:param pattern: The regex pattern required to accept command line arguments or an empty string to accept all
		:param allowed_types: The allowed types a command line argument must be convertible to or an empty iterable to allow all
		:param aliases: The argument aliases
		:param default: The default value if no command line value is supplied
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		:return: The new argument
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		argument: LiteralCommandArgument = LiteralCommandArgument(name, description=description, min_count=min_count, max_count=max_count, named=named, pattern=pattern, allowed_types=allowed_types, aliases=aliases, default=default, override_parsing=override_parsing, store=store)
		self.add_argument(argument)
		return argument

	def create_flag(self, name: str, *, description: str = '', min_count: int = 0, max_count: int = None, aliases: typing.Iterable[str] = ..., override_parsing: bool = False, store: str = ...) -> FlagCommandArgument:
		"""
		Creates a flag argument and adds it to this argument group
		:param name: The argument name
		:param description: The argument description
		:param min_count: The minimum number of accepted command line arguments
		:param max_count: The maximum number of accepted command line arguments
		:param aliases: The argument aliases
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		:return: The new argument
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		argument: FlagCommandArgument = FlagCommandArgument(name, description=description, min_count=min_count, max_count=max_count, aliases=aliases, override_parsing=override_parsing, store=store)
		self.add_argument(argument)
		return argument

	def create_boolean_flag(self, name: str, *, description: str = '', inverted: bool = False, aliases: typing.Iterable[str] = ..., override_parsing: bool = False, store: str = ...) -> FlagCommandArgument:
		"""
		Creates a boolean flag argument and adds it to this argument group
		:param name: The argument name
		:param description: The argument description
		:param inverted: Whether the stored value is inverted (false when applied instead of true)
		:param aliases: The argument aliases
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		:return: The new argument
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		argument: BooleanFlagCommandArgument = BooleanFlagCommandArgument(name, description=description, inverted=inverted, aliases=aliases, override_parsing=override_parsing, store=store)
		self.add_argument(argument)
		return argument

	def create_choices_argument(self, name: str, choices: typing.Iterable[str], *, description: str = '', min_count: int = 0, max_count: int = None, named: bool = False, aliases: typing.Iterable[str] = ..., default: typing.Any = ..., override_parsing: bool = False, store: str = ...) -> ChoicesCommandArgument:
		"""
		Creates a choices argument and adds it to this argument group
		:param name: The argument name
		:param description: The argument description
		:param min_count: The minimum number of accepted command line arguments
		:param max_count: The maximum number of accepted command line arguments
		:param named: Whether the argument name must be explicitly supplied
		:param choices: The list of allowed choices a command line argument must be in
		:param aliases: The argument aliases
		:param default: The default value if no command line value is supplied
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		:return: The new argument
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		argument: ChoicesCommandArgument = ChoicesCommandArgument(name, choices, description=description, min_count=min_count, max_count=max_count, named=named, default=default, aliases=aliases, override_parsing=override_parsing, store=store)
		self.add_argument(argument)
		return argument

	def add_argument_group(self, argument_group: CommandArgumentGroup) -> None:
		"""
		Adds a subgroup to this argument group
		:param argument_group: The argument group to add
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		Misc.raise_ifn(isinstance(argument_group, CommandArgumentGroup), Exceptions.InvalidArgumentException(parameter_name='argument_group'))
		Misc.raise_if(self.get_child_by_name(argument_group.name) is not None, NameError(f'An object in this group already has the name: \'{argument_group.name}\''))
		Misc.warn_if(argument_group.is_required and self.is_mutually_exclusive, RuntimeWarning('Use of required argument group in mutually exclusive argument group - If an argument must be supplied, set the parent group \'required\' attribute to \'True\''))
		self.__groups__.append(argument_group)

	def create_argument_group(self, name: str, description: str = '', is_mutually_exclusive: bool = False, is_required: bool = False) -> CommandArgumentGroup:
		"""
		Creates a subgroup and adds it to this argument group
		:param name: The group name
		:param description: The group description
		:param is_mutually_exclusive: Whether only one subgroup or command argument may be specified
		:param is_required: Whether one subgroup or command argument must be supplied (only for mutually exclusive groups)
		:return: The new argument group
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		group: CommandArgumentGroup = CommandArgumentGroup(name, description, is_mutually_exclusive, is_required)
		self.add_argument_group(group)
		return group

	def get_argument_by_name(self, name: str) -> typing.Optional[CommandArgument]:
		"""
		Gets a command argument by name
		:param name: The name to search for
		:return: The matching command argument or None if not found
		"""

		for argument in self.get_command_arguments():
			if argument.is_name(name):
				return argument

		return None

	def get_argument_group_by_name(self, name: str) -> typing.Optional[CommandArgumentGroup]:
		"""
		Gets a command argument group by name
		:param name: The name to search for
		:return: The matching command argument group or None if not found
		"""

		for group in self.get_sub_groups():
			if group.name == name:
				return group

		return None

	def get_child_by_name(self, name: str) -> typing.Optional[CommandArgumentGroup | CommandArgument]:
		"""
		Gets a command argument or command argument group by name
		:param name: The name to search for
		:return: The matching command argument or command argument group or None if not found
		"""

		return self.get_argument_by_name(name) or self.get_argument_group_by_name(name)

	def get_command_arguments(self) -> typing.Iterator[CommandArgument]:
		"""
		:return: An iterator for all command arguments in this group
		"""

		return iter(self.__arguments__)

	def get_sub_groups(self) -> typing.Iterator[CommandArgumentGroup]:
		"""
		:return: An iterator for all command argument groups in this group
		"""

		return iter(self.__groups__)

	def get_arguments_of_type[T: CommandArgument](self, cls: type[T] | tuple[type[T], ...]) -> typing.Iterator[T]:
		"""
		Gets all command arguments of the specified type
		:param cls: The argument class to get
		:return: An iterator of matching command arguments
		"""

		for argument in self.get_command_arguments():
			if isinstance(argument, cls):
				yield argument

	def match(self, caller: tuple[Command | CommandArgumentGroup, ...], arguments: list[String.String], *, allow_argument_overflow: bool = False) -> typing.Optional[CommandTree]:
		"""
		Matches a set of command line arguments with this argument group
		:param caller: The stack of callers to this method
		:param arguments: The arguments to match
		:param allow_argument_overflow: Whether remaining arguments will fail the match
		:return: The resulting tree or None if match failed
		"""

		toplevel: Command = caller[0]
		parent: CommandArgumentGroup = ... if len(caller) == 1 else self
		command_parent: Command = Stream.LinqStream(reversed(caller)).instance_of(Command).first()

		if self.is_mutually_exclusive:
			matched: str = ...
			tree: CommandTree = ...
			count: int = 0

			for arg in self.get_command_arguments():
				sub_tree: CommandTree = CommandTree(toplevel, parent)
				used_count, values = arg.match(arguments[count:])

				if (used_count == 0 or values is None) and arg.is_required:
					return None
				elif used_count == 0 or values is None:
					continue

				count += used_count
				sub_tree.add_filled_argument(arg, values)
				Misc.raise_ifn(tree is ..., MutualExclusionException(f'{".".join(cmd.name for cmd in caller)}: Argument \'{arg.name}\' is mutually exclusive with \'{matched}\''))
				tree = sub_tree
				matched = arg.name

			for group in self.get_sub_groups():
				group_result: typing.Optional[CommandTree] = group.match((*caller, self), arguments, allow_argument_overflow=allow_argument_overflow)

				if group_result is not None:
					Misc.raise_ifn(tree is ..., MutualExclusionException(f'{".".join(cmd.name for cmd in caller)}: Argument group \'{group.name}\' is mutually exclusive with \'{matched}\''))
					tree = group_result
					matched = group.name

			if tree is ... and self.is_required:
				raise ArgumentRequiredException(f'{".".join(cmd.name for cmd in caller)}: At least one argument in argument group \'{self.name}\' is required')

			return None if tree is ... else tree
		else:
			tree: CommandTree = CommandTree(toplevel, parent)
			sub_tree: CommandTree = ...
			matching_args: list[String.String] = ...
			named, remaining = Stream.LinqStream(self.get_command_arguments()).split(lambda arg: arg.is_named, True, False).collect()

			for arg in sorted(named, reverse=True, key=lambda a: a.override_parsing):
				while any(arg.is_name(a) for a in arguments):
					for i, cmd in enumerate(arguments):
						if arg.is_name(cmd):
							used_count, values = arg.match(arguments[i + 1:])

							if (used_count == 0 or values is None) and arg.is_required:
								return None
							elif used_count == 0 or values is None:
								continue
							elif arg.override_parsing:
								raise ParserArgumentOverride(caller[0], command_parent, self, arg, values)

							tree.add_filled_argument(arg, values)
							del arguments[i:i + used_count + 1]

				if arg.is_required and arg not in tree and (default := arg.get_default()) is not ...:
					tree.add_filled_argument(arg, default)
				elif arg.is_required and arg not in tree:
					raise ArgumentRequiredException(f'{".".join(cmd.name for cmd in caller)}: Named argument \'{arg.name}\' is required')
				elif (count := Stream.LinqStream(tree[arg]).count()) > arg.max_nargs:
					raise CommandException(f'{".".join(cmd.name for cmd in caller)}: Named argument \'{arg.name}\' accepts no more than {arg.max_nargs} value{"" if arg.max_nargs == 1 else "s"}, got {count}')

			for arg in sorted(remaining, reverse=True, key=lambda a: a.override_parsing):
				used_count, values = arg.match(arguments)

				if (used_count == 0 or values is None) and (default := arg.get_default()) is not ...:
					tree.add_filled_argument(arg, default)
					continue
				elif (used_count == 0 or values is None) and arg.is_required:
					return None
				elif used_count == 0 or values is None:
					continue
				elif arg.override_parsing:
					raise ParserArgumentOverride(caller[0], command_parent, self, arg, values)

				tree.add_filled_argument(arg, values)
				del arguments[:used_count]

			for group in self.get_sub_groups():
				clone: list[String.String] = arguments.copy()
				group_result: typing.Optional[CommandTree] = group.match((*caller, self), clone, allow_argument_overflow=allow_argument_overflow)

				if group_result is not None and len(group_result) > len(sub_tree):
					sub_tree = group_result
					matching_args = clone

			if matching_args is not ...:
				arguments.clear()
				arguments.extend(matching_args)

			if len(arguments) > 0 and not allow_argument_overflow:
				return None

			if sub_tree is not ...:
				tree.append(sub_tree)

			return tree

	@property
	def name(self) -> str:
		"""
		:return: This argument group's name
		"""

		return self.__group_name__

	@property
	def description(self) -> str:
		"""
		:return: This argument group's description
		"""

		return self.__description__

	@property
	def is_mutually_exclusive(self) -> bool:
		"""
		:return: Whether this argument group is mutually exclusive
		"""

		return self.__mutually_exclusive__

	@property
	def is_required(self) -> bool:
		"""
		:return: Whether this argument group is required
		"""

		return self.__required__


class Command:
	def __init__(self, name: str, description: str, aliases: typing.Iterable[str] = ..., add_help_argument: bool = True, is_sub_command_required: bool = True, callback: collections.abc.Callable[[CommandArguments], ...] = ...):
		"""
		Class representing a single terminal command
		:param name: The command name
		:param description: The command description
		:param aliases: The command aliases
		:param add_help_argument: Whether to automatically add a help argument (--help, -h)
		:param is_sub_command_required: Whether at least one subcommand is required
		:param callback: The callback to execute if this command or subcommand is executed (Callback will be called with a CommandArguments object)
		"""

		Misc.raise_ifn(isinstance(name, str) and len(name := str(name)) > 0, Exceptions.InvalidArgumentException(parameter_name='name', message='\'name\' must be a non-empty string'))
		Misc.raise_ifn(isinstance(description, str), Exceptions.InvalidArgumentException(parameter_name='description'))
		Misc.raise_ifn(aliases is ... or (isinstance(aliases, typing.Iterable) and len(aliases := tuple(aliases)) >= 0 and all(isinstance(x, str) for x in aliases)), Exceptions.InvalidArgumentException(parameter_name='aliases'))
		Misc.raise_ifn(callback is None or callback is ... or callable(callback), Exceptions.InvalidArgumentException(parameter_name='callback'))

		self.__command_name__: str = name
		self.__description__: str = str(description)
		self.__subcommands__: list[Command] = []
		self.__arguments__: CommandArgumentGroup = CommandArgumentGroup('arguments')
		self.__aliases__: tuple[str, ...] = () if aliases is ... else aliases
		self.__add_help_argument__: bool = bool(add_help_argument)
		self.__subcommand_required__: bool = bool(is_sub_command_required)
		self.__callback__: typing.Optional[collections.abc.Callable[[CommandArguments], []]] = None if callback is ... or callback is None else callback

		if self.add_help_argument:
			self.add_argument(CommandParser.HELP)

	def get_help_string(self, *, indent: int = 0) -> str:
		"""
		:return: The help string for this command
		"""

		tab: str = '  ' * indent
		sstream: Stream.StringStream = Stream.StringStream()
		sstream.write(f'{tab}Command [ {self.name} ]')

		if len(self.aliases) > 1:
			sstream.write(f' (AKA {", ".join(self.aliases[:-1])}')
			sstream.write(f' or {self.aliases[-1]})')
		elif len(self.aliases) == 1:
			sstream.write(f' (AKA {self.aliases[0]})')

		sstream.write(f'\n{tab}{self.get_argument_group().get_help_string(indent=indent + 1)}')
		commands: tuple[Command, ...] = tuple(self.get_sub_commands())

		if len(commands) > 0:
			sstream.write(f'\n{tab}  Subcommands')

			if self.is_sub_command_required:
				sstream.write(' (REQUIRED)')

			sstream.write(':')

			for command in commands:
				sstream.write(f'\n{tab}  {command.get_help_string(indent=indent + 1)}')

		return sstream.read()

	def add_argument(self, argument: CommandArgument) -> None:
		"""
		Adds an argument to this argument group
		:param argument: The argument to add
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		self.get_argument_group().add_argument(argument)

	def create_literal_argument(self, name: str, *, description: str = '', min_count: int = 0, max_count: int = None, named: bool = False, pattern: str = '', allowed_types: typing.Iterable[str | type] = (), aliases: typing.Iterable[str] = ..., default: typing.Any = ..., override_parsing: bool = False, store: str = ...) -> LiteralCommandArgument:
		"""
		Creates a literal argument and adds it to this argument group
		:param name: The argument name
		:param description: The argument description
		:param min_count: The minimum number of accepted command line arguments
		:param max_count: The maximum number of accepted command line arguments
		:param named: Whether the argument name must be explicitly supplied
		:param pattern: The regex pattern required to accept command line arguments or an empty string to accept all
		:param allowed_types: The allowed types a command line argument must be convertible to or an empty iterable to allow all
		:param aliases: The argument aliases
		:param default: The default value if no command line value is supplied
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		:return: The new argument
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		return self.get_argument_group().create_literal_argument(name, description=description, min_count=min_count, max_count=max_count, named=named, pattern=pattern, allowed_types=allowed_types, aliases=aliases, default=default, override_parsing=override_parsing, store=store)

	def create_flag(self, name: str, *, description: str = '', min_count: int = 0, max_count: int = None, aliases: typing.Iterable[str] = ..., override_parsing: bool = False, store: str = ...) -> FlagCommandArgument:
		"""
		Creates a flag argument and adds it to this argument group
		:param name: The argument name
		:param description: The argument description
		:param min_count: The minimum number of accepted command line arguments
		:param max_count: The maximum number of accepted command line arguments
		:param aliases: The argument aliases
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		:return: The new argument
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		return self.get_argument_group().create_flag(name, description=description, min_count=min_count, max_count=max_count, aliases=aliases, override_parsing=override_parsing, store=store)

	def create_boolean_flag(self, name: str, *, description: str = '', inverted: bool = False, aliases: typing.Iterable[str] = ..., override_parsing: bool = False, store: str = ...) -> FlagCommandArgument:
		"""
		Creates a boolean flag argument and adds it to this argument group
		:param name: The argument name
		:param description: The argument description
		:param inverted: Whether the stored value is inverted (false when applied instead of true)
		:param aliases: The argument aliases
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		:return: The new argument
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		return self.get_argument_group().create_boolean_flag(name, description=description, inverted=inverted, aliases=aliases, override_parsing=override_parsing, store=store)

	def create_choices_argument(self, name: str, choices: typing.Iterable[str], *, description: str = '', min_count: int = 0, max_count: int = None, named: bool = False, aliases: typing.Iterable[str] = ..., default: typing.Any = ..., override_parsing: bool = False, store: str = ...) -> ChoicesCommandArgument:
		"""
		Creates a choices argument and adds it to this argument group
		:param name: The argument name
		:param description: The argument description
		:param min_count: The minimum number of accepted command line arguments
		:param max_count: The maximum number of accepted command line arguments
		:param named: Whether the argument name must be explicitly supplied
		:param choices: The list of allowed choices a command line argument must be in
		:param aliases: The argument aliases
		:param default: The default value if no command line value is supplied
		:param override_parsing: If true, and this argument is supplied, it will be the only argument value returned (used for help arguments)
		:param store: The name to store this argument's values as in the parsed CommandArguments object
		:return: The new argument
		:raise NameError: If a subgroup or argument with this name already exists
		"""

		return self.get_argument_group().create_choices_argument(name, choices, description=description, min_count=min_count, max_count=max_count, named=named, aliases=aliases, default=default, override_parsing=override_parsing, store=store)

	def add_sub_command(self, command: Command) -> None:
		"""
		Adds a subcommand to this command
		:param command: The command to add
		:raise NameError: If a subgroup, subcommand, or argument with this name already exists
		"""

		Misc.raise_ifn(isinstance(command, Command), Exceptions.InvalidArgumentException(parameter_name='command'))

		for name in command.get_names():
			if self.get_child_by_name(name) is not None:
				raise NameError(f'An object in this group already has the name: \'{name}\'')

		self.__subcommands__.append(command)

	def create_sub_command(self, name: str, *, description: str = '', aliases: typing.Iterable[str] = ..., add_help_argument: bool = ..., is_sub_command_required: bool = True, callback: collections.abc.Callable[[CommandArguments], ...] = ...) -> Command:
		"""
		Adds a subcommand to this command
		:param name: The command name
		:param description: The command description
		:param aliases: The command aliases
		:param add_help_argument: Whether to automatically add a help argument (--help, -h)
		:param is_sub_command_required: Whether at least one subcommand is required
		:param callback: The callback to execute if this command or subcommand is executed (Callback will be called with a CommandArguments object)
		:return: The new command
		"""

		command: Command = Command(name, description, aliases, self.add_help_argument if add_help_argument is ... or add_help_argument is None else add_help_argument, is_sub_command_required, callback)
		self.add_sub_command(command)
		return command

	def is_name(self, name: str) -> bool:
		"""
		:param name: The name to check
		:return: Whether 'name' is a name or alias of this argument
		"""

		return isinstance(name, str) and name in self.get_names()

	def get_names(self) -> typing.Iterator[str]:
		"""
		:return: The primary name and all aliases for this argument
		"""

		yield self.name
		yield from self.aliases

	def get_argument_by_name(self, name: str) -> typing.Optional[CommandArgument]:
		"""
		Gets a command argument by name
		:param name: The name to search for
		:return: The matching command argument or None if not found
		"""

		return self.get_argument_group().get_argument_by_name(name)

	def get_sub_command_by_name(self, name: str) -> typing.Optional[Command]:
		"""
		Gets a subcommand by name
		:param name: The name to search for
		:return: The matching subcommand or None if not found
		"""

		for command in self.get_sub_commands():
			if command.is_name(name):
				return command

		return None

	def get_child_by_name(self, name: str) -> typing.Optional[Command | CommandArgument]:
		"""
		Gets a command argument, subcommand, or command argument group by name
		:param name: The name to search for
		:return: The matching command argument, subcommand, or command argument group or None if not found
		"""

		return self.get_argument_by_name(name) or self.get_sub_command_by_name(name) or (self.__arguments__ if self.__arguments__.name == name else None)

	def get_command_arguments(self) -> typing.Iterator[CommandArgument]:
		"""
		:return: An iterator for all command arguments in this command
		"""

		return self.get_argument_group().get_command_arguments()

	def get_arguments_of_type[T: CommandArgument](self, cls: type[T] | tuple[type[T], ...]) -> typing.Iterator[T]:
		"""
		Gets all command arguments of the specified type
		:param cls: The argument class to get
		:return: An iterator of matching command arguments
		"""

		return self.get_argument_group().get_arguments_of_type(cls)

	def get_sub_commands(self) -> typing.Iterator[Command]:
		"""
		:return: An iterator for all subcommands in this command
		"""

		return iter(self.__subcommands__)

	def get_argument_group(self) -> CommandArgumentGroup:
		"""
		:return: This command's primary argument group
		"""

		return self.__arguments__

	def execute(self, arguments: typing.Iterable[str], *, caller: tuple[Command, ...] = None, handle_override_arguments: bool = True) -> typing.Optional[CommandTree | CommandArguments]:
		"""
		Attempts to match the command line arguments with this command
		:param arguments: The command line arguments
		:param caller: The calling command
		:param handle_override_arguments: Whether this command should handle argument overrides
		:return: The resulting tree or None if match failed
		"""

		subcommands: tuple[Command, ...] = tuple(self.get_sub_commands())
		arguments: list[String.String] = [String.String(argument) for argument in arguments]

		try:
			path: typing.Optional[CommandTree] = self.get_argument_group().match((self,), arguments, allow_argument_overflow=len(subcommands) > 0)
		except ParserArgumentOverride as override:
			if handle_override_arguments:
				tree: CommandTree = CommandTree(self, override.argument_group)
				tree.add_filled_argument(override.argument, override.values)
				return CommandArguments(tree)
			else:
				raise override

		caller = (self,) if caller is None else caller

		if path is None:
			return None
		elif len(subcommands) == 0:
			return path if len(caller) > 1 else CommandArguments(path)
		else:
			if len(arguments) == 0 and self.is_sub_command_required:
				raise ArgumentRequiredException(f'{".".join(cmd.name for cmd in caller)}: At least one subcommand must be supplied')
			elif len(arguments) == 0:
				return path if len(caller) > 1 else CommandArguments(path)

			subcommand_name: String.String = arguments[0]
			subcommand: typing.Optional[Command] = self.get_sub_command_by_name(subcommand_name)

			if subcommand is None:
				raise NameError(f'{".".join(cmd.name for cmd in caller)}: No such sub-command or argument - \'{subcommand_name}\'')

			command_result: typing.Optional[CommandTree] = subcommand.execute(arguments[1:], caller=(*caller, self))

			if command_result is None:
				return None

			path.append(command_result)
			return path if len(caller) > 1 else CommandArguments(path)

	def run(self, arguments: str) -> typing.Optional[CommandArguments]:
		"""
		Attempts to match the command line with this command
		:param arguments: The command line
		:return: The resulting tree or None if match failed
		"""

		return self.execute(shlex.split(arguments))

	@property
	def add_help_argument(self) -> bool:
		"""
		:return: Whether this command should automatically add a help argument (--help, -h)
		"""

		return self.__add_help_argument__

	@property
	def is_sub_command_required(self) -> bool:
		"""
		:return: Whether this command requires at least one subcommand
		"""

		return self.__subcommand_required__

	@property
	def name(self) -> str:
		"""
		:return: This command's name
		"""

		return self.__command_name__

	@property
	def description(self) -> str:
		"""
		:return: This command's description
		"""

		return self.__description__

	@property
	def aliases(self) -> tuple[str, ...]:
		"""
		:return: This command's aliases
		"""

		return self.__aliases__

	@property
	def callback(self) -> typing.Optional[collections.abc.Callable[[CommandArguments], []]]:
		"""
		:return: The callback to execute if this command or subcommand is called
		"""

		return self.__callback__


class CommandParser:
	HELP: HelpCommandArgument = HelpCommandArgument()

	def __init__(self):
		"""
		Class representing a command parser\n
		Command parsers hold a list of possible commands and can have command lines passed in
		"""

		self.__commands__: list[Command] = []

	def __len__(self) -> int:
		"""
		:return: The number of commands bound to this command parser
		"""

		return len(self.__commands__)

	def add_command(self, command: Command) -> None:
		"""
		Adds a command to this parser
		:param command: The command to add
		"""

		Misc.raise_ifn(isinstance(command, Command), Exceptions.InvalidArgumentException(parameter_name='command'))

		for name in command.get_names():
			if self.get_command_by_name(name) is not None:
				raise NameError(f'A command already has the name: \'{name}\'')

		self.__commands__.append(command)

	def create_command(self, name: str, *, description: str = '', aliases: typing.Iterable[str] = ..., add_help_argument: bool = True, is_sub_command_required: bool = True, callback: collections.abc.Callable[[CommandArguments], ...] = ...) -> Command:
		"""
		Creates and adds a command to this parser
		:param name: The command name
		:param description: The command description
		:param aliases: The command aliases
		:param add_help_argument: Whether command should have a help argument added
		:param is_sub_command_required: Whether command should have at least one of it's subcommands applied
		:param callback: The callback to execute if this command or subcommand is executed (Callback will be called with a CommandArguments object)
		:return: The new command
		"""

		command: Command = Command(name, description, aliases, add_help_argument, is_sub_command_required, callback)
		self.add_command(command)
		return command

	def execute(self, arguments: typing.Iterable[str]) -> tuple[Command, typing.Optional[CommandArguments]]:
		"""
		Parses command line arguments\n
		Result will be a tuple of the command and its matched values\n
		If either the command is None or the matched values is None, command parsing failed
		:param arguments: The command line arguments
		:return: A tuple containing the found command and command tree
		"""

		arguments: tuple[String.String, ...] = tuple(String.String(arg) for arg in arguments)
		command: typing.Optional[Command] = self.get_command_by_name(arguments[0])
		return command, None if command is None else command.execute(arguments[1:])

	def run(self, arguments: str, *args, **kwargs) -> int:
		"""
		Executes the specified command line arguments, handling all errors and printing results to console
		:param arguments: The command line arguments
		:return: The exit code (0 is success)
		"""

		if len(arguments) == 0:
			return -1

		try:
			command_arguments: list[str] = shlex.split(arguments)
			arguments: tuple[String.String, ...] = tuple(String.String(arg) for arg in command_arguments)
			command = self.get_command_by_name(arguments[0])
			tree = None if command is None else command.execute(arguments[1:], handle_override_arguments=False)

			if command is None:
				sys.stderr.write(f'No such command - \'{command_arguments[0]}\'\n')
				return 1
			elif tree is None:
				sys.stderr.write('One or more command line arguments are incorrect\n')
				return 2

			try:
				result: typing.Any = tree(*args, **kwargs)

				if isinstance(result, int):
					return int(result)
				else:
					return 0
			except NoCommandHandlerException:
				return 0
			except Exception as err:
				sys.stderr.write(f'Unknown error executing command: {err}\n')
				return -hash(type(err))
		except ParserArgumentOverride as override:
			sys.stdout.write(f'{override.parent.get_help_string()}\n')
			return -1
		except (NameError, MutualExclusionException, ArgumentRequiredException, CommandException) as err:
			sys.stderr.write(f'{err}\n')
			return 3
		except Exception as err:
			sys.stderr.write(f'Unknown error parsing command: {err}\n')
			return 4

	def parse(self, arguments: str) -> tuple[Command, typing.Optional[CommandArguments]]:
		"""
		Parses command line arguments\n
		Result will be a tuple of the command and its matched values\n
		If either the command is None or the matched values is None, command parsing failed
		:param arguments: The command line arguments
		:return: A tuple containing the found command and command tree
		"""

		return self.execute(shlex.split(arguments))

	def get_command_by_name(self, name: str) -> typing.Optional[Command]:
		"""
		Searches for a command by name
		:param name: The name to search for
		:return: The found command or None if not found
		"""

		for command in self.get_commands():
			if command.is_name(name):
				return command

		return None

	def get_commands(self) -> typing.Iterator[Command]:
		"""
		:return: An iterator over all commands in this parser
		"""

		return iter(self.__commands__)


class CommandTree:
	def __init__(self, command: Command, parent: CommandArgumentGroup = ...):
		"""
		Command tree storing all matched arguments and their resolved values
		:param command: The parent command
		"""

		Misc.raise_ifn(isinstance(command, Command), Exceptions.InvalidArgumentException(parameter_name='command'))
		Misc.raise_ifn(parent is ... or parent is None or isinstance(parent, CommandArgumentGroup), Exceptions.InvalidArgumentException(parameter_name='parent'))
		self.__command__: Command = command
		self.__parent__: Command | CommandArgumentGroup = command if parent is ... else parent
		self.__arguments__: list[tuple[CommandArgument, list[typing.Any]]] = []
		self.__children__: list[CommandTree] = []

	def __contains__(self, argument: CommandArgument) -> bool:
		"""
		:param argument: The argument to check
		:return: Whether the argument is in this tree
		"""

		return any(pair[0] == argument for pair in self.get_arguments())

	def __len__(self) -> int:
		"""
		:return: The number of matched arguments
		"""

		return sum(len(pair[1]) for pair in self.__arguments__) + sum(len(tree) for tree in self.__children__)

	def __getitem__(self, item: CommandArgument) -> typing.Iterator[typing.Any]:
		"""
		Gets the supplied command line values for the specified argument in this tree
		:param item: The argument
		:return: An iterator over the command arguments
		"""

		for arg, values in self.get_arguments():
			if arg == item:
				yield from iter(values)

	def add_filled_argument(self, argument: CommandArgument, supplied_values: typing.Iterable[typing.Any]) -> None:
		"""
		Adds a filled argument to this tree
		:param argument: The filled argument
		:param supplied_values: The resolved argument values
		"""

		Misc.raise_ifn(isinstance(argument, CommandArgument), Exceptions.InvalidArgumentException(parameter_name='argument'))
		Misc.raise_ifn(isinstance(supplied_values, typing.Iterable), Exceptions.InvalidArgumentException(parameter_name='supplied_values'))

		for arg, vals in self.__arguments__:
			if arg == argument:
				vals.extend(supplied_values)
				return

		self.__arguments__.append((argument, list(supplied_values)))

	def append(self, sub_tree: CommandTree) -> None:
		"""
		Appends a subtree to the end of this tree
		:param sub_tree: The tree to add
		"""

		Misc.raise_ifn(isinstance(sub_tree, CommandTree), Exceptions.InvalidArgumentException(parameter_name='sub_tree'))
		self.__children__.append(sub_tree)

	def get_children(self) -> typing.Iterator[CommandTree]:
		"""
		:return: An iterator over all subtrees
		"""

		return iter(self.__children__)

	def get_arguments(self) -> typing.Iterator[tuple[CommandArgument, tuple[typing.Any, ...]]]:
		"""
		:return: An iterator over the argument value pairs in this tree layer
		"""

		for argument, values in self.__arguments__:
			yield argument, tuple(values)

	@property
	def command(self) -> Command:
		"""
		:return: This tree's toplevel command
		"""

		return self.__command__

	@property
	def parent(self) -> Command | CommandArgumentGroup:
		"""
		:return: This tree's parent
		"""

		return self.__parent__


class CommandArguments:
	class NamespaceWrapper:
		def __init__(self, source: CommandTree):
			"""
			Single namespace holding the current and child levels for all command arguments and argument groups parsed from command line
			:param source: The source subtree or root tree to build this namespace from
			"""

			self.__namespace__: dict[str, typing.Any] = {}

			for argument, values in source.get_arguments():
				resolved: typing.Any = argument.resolve(values)
				self.__namespace__[argument.store_name] = resolved[0] if isinstance(resolved, collections.abc.Sequence) and argument.max_nargs == 1 and len(resolved) > 0 else resolved

			for subtree in source.get_children():
				if isinstance(subtree.parent, Command):
					self.__namespace__[subtree.parent.name] = CommandArguments(subtree)
				else:
					self.__namespace__[subtree.parent.name] = CommandArguments.NamespaceWrapper(subtree)

		def __contains__(self, item: str) -> bool:
			"""
			:param item: The argument name or subgroup name to check
			:return: Whether the name is within this namespace
			"""

			return item in self.__namespace__

		def __iter__(self) -> typing.Iterator[tuple[str, typing.Any | CommandArguments.NamespaceWrapper]]:
			"""
			:return: An iterator over all key value pairs in this namespace
			"""

			return iter(self.__namespace__.items())

		def __getitem__(self, key: str) -> typing.Any | CommandArguments | CommandArguments.NamespaceWrapper:
			"""
			Gets an argument value or subspace by name
			:param key: The argument name
			:return: The argument value
			"""

			paths: list[str] = re.split(r'[/\\.]', key)
			*paths, target = paths
			source: dict[str, typing.Any] = self.__namespace__

			for i, path in enumerate(paths):
				if isinstance(source, dict) and path in source:
					source = source[path]
				else:
					raise NameError(f'Command arguments \'{".".join(paths[:i])}\' has no argument or subspace \'{path}\'')

			if target not in source:
				raise NameError(f'Command arguments \'{".".join(paths)}\' has no argument or subspace \'{target}\'')

			return source[target]

		def __getattr__(self, item: str) -> typing.Any | CommandArguments | CommandArguments.NamespaceWrapper:
			"""
			Gets an argument value or subspace by name
			:param item: The argument name
			:return: The argument value
			"""

			return self.__namespace__[item]

		def get_or_default(self, key: str, default: typing.Any = None) -> typing.Any:
			"""
			Gets an argument value or subspace by name or returns 'default' if not found
			:param key: The argument name
			:param default: The default value
			:return: The specified argument value or 'default' if not found
			"""

			return self.__namespace__.get(key, default)

	@classmethod
	def get_command_path(cls, arguments: CommandArguments) -> tuple[Command, ...]:
		"""
		Gets the path of command and subcommands for a given set of command arguments
		:param arguments: The arguments whose command path to get
		:return: The path of commands
		"""

		Misc.raise_ifn(isinstance(arguments, cls), Exceptions.InvalidArgumentException(parameter_name='arguments'))
		path: list[Command] = [arguments.__command__]

		while True:
			changed: bool = False

			for name, value in arguments:
				if isinstance(value, cls):
					path.append(value.__command__)
					arguments = value
					changed = True
					break

			if not changed:
				break

		return tuple(path)

	def __init__(self, tree: CommandTree):
		"""
		Class holding the finalized arguments and argument groups from a parsed command line
		:param tree: The tree to build this object from
		"""

		Misc.raise_ifn(isinstance(tree, CommandTree), Exceptions.InvalidArgumentException(parameter_name='tree'))
		self.__command__: Command = tree.command
		self.__toplevel__: CommandArguments.NamespaceWrapper = CommandArguments.NamespaceWrapper(tree)

	def __call__(self, *args, **kwargs) -> typing.Any:
		"""
		Calls the command callbacks within this namespace
		:param args: The function arguments
		:param kwargs: The function keyword arguments
		:return: The callback's return value
		"""

		command_stack: list[tuple[Command, CommandArguments]] = [(self.__command__, self)]

		for key, value in self:
			if isinstance(value, CommandArguments):
				command_stack.append((value.__command__, value))

		for command, arguments in reversed(command_stack):
			if callable(command.callback):
				return command.callback(arguments, *args, **kwargs)

		raise NoCommandHandlerException(f'No callable defined for any command in stack - \'{self.__command__}\'')

	def __contains__(self, item: str) -> bool:
		"""
		:param item: The argument name or subgroup name to check
		:return: Whether the name is within this namespace
		"""

		return item in self.__toplevel__

	def __iter__(self) -> typing.Iterator[tuple[str, typing.Any | CommandArguments.NamespaceWrapper]]:
		"""
		:return: An iterator over all key value pairs in this namespace
		"""

		return iter(self.__toplevel__)

	def __getitem__(self, key: str) -> typing.Any | CommandArguments | CommandArguments.NamespaceWrapper:
		"""
		Gets an argument value or subspace by name
		:param key: The argument name
		:return: The argument value
		"""

		return self.__toplevel__[key]

	def __getattr__(self, item: str) -> typing.Any | CommandArguments | CommandArguments.NamespaceWrapper:
		"""
		Gets an argument value or subspace by name
		:param item: The argument name
		:return: The argument value
		"""

		return self.__toplevel__[item]

	def get_or_default(self, key: str, default: typing.Any = None) -> typing.Any:
		"""
		Gets an argument value or subspace by name or returns 'default' if not found
		:param key: The argument name
		:param default: The default value
		:return: The specified argument value or 'default' if not found
		"""

		return self.__toplevel__.get_or_default(key, default)


__all__: list[str] = [
	'CommandException', 'MutualExclusionException', 'ArgumentRequiredException', 'NoCommandHandlerException',
	'CommandArgument', 'LiteralCommandArgument', 'FlagCommandArgument', 'HelpCommandArgument', 'ChoicesCommandArgument',
	'CommandArgumentGroup', 'Command',
	'CommandParser', 'CommandTree', 'CommandArguments'
]
