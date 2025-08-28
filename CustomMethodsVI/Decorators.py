from __future__ import annotations

import inspect
import os
import typing
import types
import typeguard

from . import Exceptions
from . import Misc
from . import Stream


class __OverloadCaller__:
	"""
	INTERNAL CLASS; DO NOT USE
	Class for handling function overloads and delegation
	"""

	__FunctionOverloads: dict[str, __OverloadCaller__] = {}
	__FunctionCallers: dict[typing.Callable, __OverloadCaller__] = {}

	@classmethod
	def assoc(cls, lambda_: typing.Callable, caller: __OverloadCaller__) -> None:
		if callable(caller):
			cls.__FunctionCallers[lambda_] = caller
		elif lambda_ in cls.__FunctionCallers:
			del cls.__FunctionCallers[lambda_]

	@classmethod
	def new(cls, function: typing.Callable | types.FunctionType | types.LambdaType | types.MethodType, strict_only: bool | None = False) -> __OverloadCaller__:
		"""
		Creates and stores a new function overload
		:param function: (CALLABLE) The function to overload
		:param strict_only: (bool or None) Whether the function should only allow strict matches or whether this function is a default fallback if None
		:return: (__OverloadCaller) The delegator
		"""

		if function.__qualname__ in cls.__FunctionOverloads:
			caller = cls.__FunctionOverloads[function.__qualname__]

			if strict_only is None:
				caller.__default = function
			else:
				annotations = {cb: cb.__annotations__ for cb in caller.__function_overloads}

				for cb, annotation in annotations.items():
					if function.__annotations__ == annotation:
						del caller.__function_overloads[cb]
						break

				caller.__function_overloads[function] = strict_only

			return caller
		else:
			new_caller: __OverloadCaller__ = super().__new__(cls)
			cls.__init__(new_caller, function, strict_only)
			cls.__FunctionOverloads[function.__qualname__] = new_caller
			return new_caller

	def __init__(self, function: typing.Callable, strict_only: bool | None):
		"""
		INTERNAL CLASS; DO NOT USE
		[__OverloadCaller] - Class for handling function overloads and delegation
		- Constructor -
		SHOULD NOT BE CALLED DIRECTLY; USE '__OverloadCaller.new'
		:param function: (CALLABLE) The initial function to overload
		:param strict_only: (bool) Whether to allow only strict matches
		"""

		self.__function_qual_name: str = function.__qualname__
		self.__function_overloads: dict[typing.Callable | types.FunctionType | types.LambdaType | types.MethodType, bool] = {} if strict_only is None else {function: strict_only}
		self.__default: 'typing.Callable | None' = function if strict_only is None else None

	def __eq__(self, other: '__OverloadCaller | typing.Any') -> bool:
		return self is other or (type(other) is type(self) and other.__function_qual_name == self.__function_qual_name)

	def __call__(self, *_args, **_kwargs) -> typing.Any:
		"""
		Calls the overloaded function based on argument types
		:param args: The arguments to call with
		:param kwargs: The keyword arguments to call with
		:return: (ANY) The function result
		:raises CorruptError: If multiple strict matches are found
		:raises AmbiguousError: If multiple matches are found
		:raises TypeError: If no matches are found and no default fallback was supplied
		"""

		def match_type(_value: typing.Any, annotation: tuple[type | types.UnionType, ...]) -> int:
			def check_type(v, t) -> bool:
				try:
					typeguard.check_type(v, t)
					return True
				except typeguard.TypeCheckError:
					return False

			_match: int = 0

			for annotate in annotation:
				if isinstance(annotate, type):
					_match = max(_match, 2 if type(_value) is annotate else 1 if isinstance(_value, annotate) or can_cast(_value, annotate) else 0)
				else:
					_match = max(_match, 2 if check_type(_value, annotate) else 0)

			return _match

		def deduce_annotation(annotation: str | type | typing._GenericAlias | typing._SpecialGenericAlias | types.UnionType) -> tuple[type, ...]:
			if isinstance(annotation, (type, typing._GenericAlias, types.GenericAlias, typing._SpecialGenericAlias)):
				return (annotation,)
			elif isinstance(annotation, types.UnionType):
				return annotation.__args__
			elif annotation == typing.Callable:
				return types.FunctionType, types.MethodType, types.BuiltinFunctionType, types.LambdaType, types.MethodDescriptorType
			elif isinstance(annotation, str):
				try:
					return deduce_annotation(eval(annotation))
				except NameError:
					return typing.Any,
			elif annotation is None:
				return type(None),
			else:
				raise TypeError(f'Non-standard type hint: \'{annotation}\' ({type(annotation)})')

		def can_cast(_value: typing.Any, _type: type) -> bool:
			if _type is inspect._empty or _type is typing.Any:
				return True
			elif hasattr(_value, f'__cast_{_type.__name__}__') or isinstance(_value, _type) or _type.__init__ in type(self).__FunctionCallers:
				return True
			elif hasattr(_type, '__iter__') and _type.__name__ in dir(__builtins__) and hasattr(_value, '__iter__'):
				return True

			try:
				_type(_value)
				return True
			except (TypeError, ValueError, NotImplementedError):
				return False

		def cast(_value: typing.Any, _type: type) -> typing.Any:
			if _type is inspect._empty or _type is typing.Any:
				return _value
			elif hasattr(_value, f'__cast_{_type.__name__}__'):
				_result = getattr(_value, f'__cast_{_type.__name__}__')()

				if not isinstance(_result, _type):
					raise TypeError('CastingError during cast operation - returned cast is not the correct type')

				return _result

			try:
				return _type(_value)
			except (TypeError, ValueError, NotImplementedError):
				raise TypeError(f'Uncastable [{type(_value)} >> {_type}]') from None

		assert len(self.__function_overloads) > 0 or self.__default is not None, 'No function to call'
		strict_match: list[tuple[typing.Callable, inspect.Signature]] = []
		soft_match: list[tuple[typing.Callable, inspect.Signature]] = []

		for function, strict_only in self.__function_overloads.items():
			args: list[typing.Any] = list(reversed(_args))
			is_valid: bool = True
			is_bound: bool = function.__qualname__ != function.__name__ and not isinstance(function, (staticmethod, classmethod))
			bound_removed: bool = False
			signature: inspect.Signature = inspect.signature(function)
			parameters: typing.Mapping[str, inspect.Parameter] = signature.parameters
			var_keyword: inspect.Parameter | None = next(p for p in parameters.values() if p.kind == p.VAR_KEYWORD) if any(p.kind == p.VAR_KEYWORD for p in parameters.values()) else None
			arguments: dict[str, typing.Any] = {}
			_annotations: dict[str, typing.Any] = typing.get_type_hints(function)

			if var_keyword is not None:
				arguments[var_keyword.name] = {}

			for parameter_name, arg in _kwargs.items():
				if parameter_name not in parameters or parameter_name in arguments or ((parameter := parameters[parameter_name]).kind == parameter.VAR_KEYWORD or parameter.kind == parameter.VAR_POSITIONAL):
					is_valid = False
					break
				elif var_keyword is not None:
					arguments[var_keyword.name][parameter_name] = arg
				else:
					arguments[parameter_name] = arg

			if not is_valid:
				continue

			for parameter_name, parameter in parameters.items():
				if is_bound and not bound_removed and not (function.__name__.startswith('__') and function.__name__.endswith('__')):
					bound_removed = True
					arguments[parameter_name] = args.pop()
					continue

				if parameter.kind == parameter.POSITIONAL_OR_KEYWORD or parameter.kind == parameter.POSITIONAL_ONLY:
					if len(args) == 0:
						is_valid = False
						break
					elif parameter_name not in arguments:
						arguments[parameter_name] = args.pop()
				elif parameter.kind == parameter.VAR_POSITIONAL:
					arguments[parameter_name] = tuple(args)
					args.clear()
				elif parameter.kind == parameter.KEYWORD_ONLY and parameter_name not in arguments:
					is_valid = False
					break

			if not is_valid or len(args):
				continue

			strict: bool = True
			soft: bool = True

			for name, parameter in parameters.items():
				if not is_valid:
					break

				allowed_types: tuple[type, ...] | None = deduce_annotation(_annotations[name]) if name in _annotations else None

				if allowed_types is not None:
					values: tuple[typing.Any, ...] = arguments[parameter.name] if parameter.kind == parameter.VAR_POSITIONAL else tuple(arguments[parameter.name].values()) if parameter.kind == parameter.VAR_KEYWORD else (arguments[parameter.name],)

					for value in values:
						match: int = match_type(value, allowed_types)

						if match == 2:
							strict = strict and True
						elif match == 1:
							strict = False
							soft = soft and True
						elif match == 0:
							soft = False
							is_valid = False
							break

			if not is_valid:
				continue
			elif strict:
				strict_match.append((function, signature))
			elif soft:
				soft_match.append((function, signature))

		if len(strict_match) > 1:
			raise Exceptions.CorruptError(f'Multiple strict matches found for function \'{self.__function_qual_name}\':\n{"\n".join(str(match[1]) for match in strict_match)}')
		elif len(strict_match) == 1:
			func, sig = strict_match[0]
			returns: tuple[type, ...] = tuple(x for x in deduce_annotation(sig.return_annotation) if x is not inspect._empty)
			result = func(*_args, **_kwargs)

			if len(returns) == 0 or typing.Any in returns or match_type(result, returns):
				return result

			for rtype in returns:
				if isinstance(rtype, type):
					try:
						return rtype(result)
					except (ValueError, TypeError):
						pass

			raise TypeError(f'Failed to cast function return ({type(result)}) to one of type(s) \'{returns}\'')
		elif len(soft_match) > 1:
			raise Exceptions.AmbiguousError(f'Multiple matches found for function \'{self.__function_qual_name}\':\n{"\n".join(str(match[1]) for match in strict_match)}')
		elif len(soft_match) == 1 and not self.__function_overloads[soft_match[0][0]]:
			func, sig = soft_match[0]
			returns: tuple[type, ...] = tuple(x for x in deduce_annotation(sig.return_annotation) if x is not inspect._empty)
			casted_args: list = []
			casted_kwargs: dict = {}
			parameter_names: tuple[str, ...] = tuple(sig.parameters.keys())
			variadic: str | None = None

			for i, argument in enumerate(_args):
				parameter_name: str = parameter_names[i] if variadic is None else variadic
				parameter: inspect.Parameter = sig.parameters[parameter_name]
				parameter_types: tuple[type, ...] = deduce_annotation(parameter.annotation)

				if parameter.kind == parameter.VAR_POSITIONAL:
					variadic = parameter_name

				for parameter_type in parameter_types:
					if can_cast(argument, parameter_type):
						casted_args.append(cast(argument, parameter_type))

			variadic = None

			for kw_name, argument in _kwargs.items():
				parameter_name: str = kw_name if variadic is None else variadic
				parameter: inspect.Parameter = sig.parameters[kw_name]
				parameter_types: tuple[type, ...] = deduce_annotation(parameter.annotation)

				if parameter.kind == parameter.VAR_POSITIONAL:
					variadic = parameter_name

				for parameter_type in parameter_types:
					if can_cast(argument, parameter_type):
						casted_kwargs[parameter_name] = cast(argument, parameter_type)

			result = func(*casted_args, **casted_kwargs)

			if len(returns) == 0 or typing.Any in returns or match_type(result, returns):
				return result

			for rtype in returns:
				if isinstance(rtype, type):
					try:
						return rtype(result)
					except (ValueError, TypeError):
						pass

			raise TypeError(f'Failed to cast function return ({type(result)}) to one of type(s) \'{returns}\'')
		elif self.__default is not None:
			return self.__default(*_args, **_kwargs)
		else:
			msg: list[str] = []

			for function, strict_only in self.__function_overloads.items():
				sstream: Stream.StringStream = Stream.StringStream()
				sstream.write(f'\'{function}\' Strictly Accepts:' if strict_only else f'\'{function}\' Accepts:')
				signature: inspect.Signature = inspect.signature(function)
				_annotations: dict[str, typing.Any] = typing.get_type_hints(function)
				total: str = str(len(signature.parameters))

				for i, (parameter_name, parameter) in enumerate(signature.parameters.items()):
					header: str = '**' if parameter.kind == parameter.VAR_KEYWORD else '*' if parameter.kind == parameter.VAR_POSITIONAL else ''
					index: str = str(i + 1).zfill(len(total))

					if parameter_name in _annotations:
						sstream.write(f'\n - [{index}/{total}] Parameter \'{header}{parameter_name}\' - One of type: [{", ".join(str(x) for x in deduce_annotation(_annotations[parameter_name]))}]')
					else:
						sstream.write(f'\n - [{index}/{total}] Parameter \'{header}{parameter_name}\' - ?')

				msg.append(sstream.read())

			msg.append(f'\t...\nArguments were: ({", ".join(str(type(x)) for x in _args)})')
			msg.append(f'Keyword arguments were: {", ".join(f"{x}={str(type(y))}" for x, y in _kwargs.items())}')
			msg: str = '\n'.join(msg)
			raise TypeError(f'No matches found for function \'{self.__function_qual_name}\':\n\t...\n{msg}')


def Overload(*function: typing.Callable, strict: bool = False) -> typing.Callable:
	"""
	Decorator for overloading functions
	Function parameters must be type hinted (or typing.Any is assumed)
	This decorator is not suitable for pickling
	:param function: The function to decorate
	:param strict: Whether to only allow exact types (defaults to False)
	:return: None or binder if used as a decorator
	:raises InvalidArgumentException: If callback is not callable
	"""

	if len(function) == 0:
		def binder(callback: typing.Callable):
			Misc.raise_ifn(callable(callback), Exceptions.InvalidArgumentException(Overload, 'function', type(callback)))
			caller: __OverloadCaller__ = __OverloadCaller__.new(callback, strict)
			redirect: typing.Callable = lambda *args, __caller=caller, **kwargs: __caller(*args, **kwargs)
			__OverloadCaller__.assoc(redirect, caller)
			return redirect

		return binder
	elif callable(function[0]):
		caller: __OverloadCaller__ = __OverloadCaller__.new(function[0], strict)
		redirect: typing.Callable = lambda *args, __caller=caller, **kwargs: __caller(*args, **kwargs)
		__OverloadCaller__.assoc(redirect, caller)
		return redirect
	else:
		raise Exceptions.InvalidArgumentException(Overload, 'function', type(function[0]))


def DefaultOverload(function: typing.Callable):
	"""
	Decorator for overloading functions
	Marks this function as a default fallback
	This decorator is not suitable for pickling
	:return: None or binder if used as a decorator
	:raises InvalidArgumentException: If callback is not callable
	"""

	Misc.raise_ifn(callable(function), Exceptions.InvalidArgumentException(Overload, 'function', type(function)))
	caller: __OverloadCaller__ = __OverloadCaller__.new(function, None)
	redirect: typing.Callable = lambda *args, __caller=caller, **kwargs: __caller(*args, **kwargs)
	__OverloadCaller__.assoc(redirect, caller)
	return redirect


class __AccessRestrictedClass__(type):
	"""
	INTERNAL CLASS; DO NOT USE
	Class for handling classes with access restrictions
	"""

	__OWN_ATTRS = ('__delinstattribute__', '__setinstattribute__', '__getinstattribute__', '__name__', '__qualname__')

	def __delattr__(self, name: str) -> None:
		attribute: typing.Any = super().__getattribute__(name)

		if name in __AccessRestrictedClass__.__OWN_ATTRS or not isinstance(attribute, __AccessRestrictedAttribute__):
			super().__delattr__(name)
		else:
			stack: tuple[inspect.FrameInfo, ...] = Stream.LinqStream(inspect.stack()).skip(1).collect(tuple)

			if attribute.check_access(self, None, stack):
				attribute.__attribute__ = None
				super().__delattr__(name)
			else:
				raise Exceptions.InaccessibleAttributeException(attribute.fail_message(self.__name__, name))

	def __setattr__(self, name: str, value: typing.Any) -> None:
		attribute: typing.Any = super().__getattribute__(name)

		if name in __AccessRestrictedClass__.__OWN_ATTRS or not isinstance(attribute, __AccessRestrictedAttribute__):
			super().__setattr__(name, value)
		else:
			stack: tuple[inspect.FrameInfo, ...] = Stream.LinqStream(inspect.stack()).skip(1).collect(tuple)

			if attribute.check_access(self, None, stack):
				attribute.__attribute__ = value
			else:
				raise Exceptions.InaccessibleAttributeException(attribute.fail_message(self.__name__, name))

	def __getattribute__(self, name: str):
		attribute: typing.Any = super().__getattribute__(name)

		if name in __AccessRestrictedClass__.__OWN_ATTRS:
			return super().__getattribute__(name)
		elif isinstance(attribute, __AccessRestrictedAttribute__):
			stack: tuple[inspect.FrameInfo, ...] = Stream.LinqStream(inspect.stack()).skip(1).collect(tuple)

			if attribute.check_access(self, None, stack):
				return attribute.__attribute__
			else:
				raise Exceptions.InaccessibleAttributeException(attribute.fail_message(self.__name__, name))

		else:
			return attribute

	def __delinstattribute__[T](cls: type[T], instance: T, name: str) -> None:
		attribute: typing.Any = super().__getattribute__(name)

		if name in __AccessRestrictedClass__.__OWN_ATTRS or not isinstance(attribute, __AccessRestrictedAttribute__):
			super().__delattr__(name)
		else:
			stack: tuple[inspect.FrameInfo, ...] = Stream.LinqStream(inspect.stack()).skip(2).collect(tuple)

			if attribute.check_access(cls, instance, stack):
				attribute.__attribute__ = None
				super().__delattr__(name)
			else:
				raise Exceptions.InaccessibleAttributeException(attribute.fail_message(cls.__name__, name))

	def __setinstattribute__[T](cls: type[T], instance: T, name: str, value: typing.Any) -> None:
		attribute: typing.Any = super().__getattribute__(name)

		if name in __AccessRestrictedClass__.__OWN_ATTRS or not isinstance(attribute, __AccessRestrictedAttribute__):
			super().__setattr__(name, value)
		else:
			stack: tuple[inspect.FrameInfo, ...] = Stream.LinqStream(inspect.stack()).skip(2).collect(tuple)

			if attribute.check_access(cls, instance, stack):
				attribute.__attribute__ = value
			else:
				raise Exceptions.InaccessibleAttributeException(attribute.fail_message(cls.__name__, name))

	def __getinstattribute__[T](cls: type[T], instance: T, name: str) -> typing.Any:
		attribute: typing.Any = super().__getattribute__(name)

		if name in __AccessRestrictedClass__.__OWN_ATTRS:
			return super().__getattribute__(name)
		elif isinstance(attribute, __AccessRestrictedAttribute__):
			stack: tuple[inspect.FrameInfo, ...] = Stream.LinqStream(inspect.stack()).skip(2).collect(tuple)

			if attribute.check_access(cls, instance, stack):
				return types.MethodType(attribute.__attribute__, instance) if callable(attribute.__attribute__) else attribute.__attribute__
			else:
				raise Exceptions.InaccessibleAttributeException(attribute.fail_message(cls.__name__, name))

		else:
			return types.MethodType(attribute, instance) if callable(attribute) else attribute


class __AccessRestrictedAttribute__[T]:
	"""
	INTERNAL CLASS; DO NOT USE
	Attribute class for handling attributes with access restrictions
	"""

	def __init__(self, class_name: str, attribute: T):
		"""
		INTERNAL CLASS; DO NOT USE
		Attribute class for handling attributes with access restrictions
		:param class_name: The class name that owns this attribute
		:param attribute: The attribute
		:raises AssertionError: If 'class_name' is invalid
		"""

		assert isinstance(class_name, str) and len(class_name := str(class_name)) > 0, 'Invalid class name'
		self.__class_name__: str = str(class_name)
		self.__arc__: __AccessRestrictedClass__ = ...
		self.__attribute__: T = attribute
		self.__frame__: inspect.FrameInfo = Stream.LinqStream(inspect.stack()).skip_while(lambda frame: frame.frame.f_code.co_name != class_name).first_or_default(None)
		assert self.__frame__ is not None, 'Failed to get frame'

	def __repr__(self) -> str:
		return f'<{self.access_qualifier} attribute \'{self.__class_name__}::{self.__attribute__.__name__}\' at {hex(id(self))}>'

	def __str__(self):
		return str(self.__attribute__)

	def __call__(self, *args, **kwargs):
		self.__attribute__(*args, **kwargs)

	def check_access(self, arc: __AccessRestrictedClass__, instance: typing.Any, calling_stack: tuple[inspect.FrameInfo, ...]) -> bool:
		"""
		*ABSTRACT*
		:param arc: The ARC
		:param instance: The ARC instance
		:param calling_stack: The calling frame stack
		:return: Whether access should be granted
		"""

		return False

	def fail_message(self, class_name: str, attribute_name: str) -> str:
		"""
		:param class_name: The containing class's name
		:param attribute_name: The attribute name
		:return: The message to display when access is rejected
		"""

		return f'Attribute \'{class_name}::{attribute_name}\' is {self.access_qualifier}'

	@property
	def arc(self) -> __AccessRestrictedClass__:
		assert isinstance(self.__arc__, __AccessRestrictedClass__), 'ARC not set'
		return self.__arc__

	@property
	def frame(self) -> inspect.FrameInfo:
		"""
		:return: The call frame this attribute was created in
		"""

		return self.__frame__

	@property
	def access_qualifier(self) -> str:
		return 'locked'


class __PrivateAttribute__[T](__AccessRestrictedAttribute__[T]):
	def check_access(self, arc: __AccessRestrictedClass__, instance: typing.Any, calling_stack: tuple[inspect.FrameInfo, ...]) -> bool:
		for frame in calling_stack:
			for variable in frame.frame.f_locals.values():
				if type(variable) is self.arc:
					return True

		return False

	@property
	def access_qualifier(self) -> str:
		return 'private'


class __ProtectedAttribute__[T](__AccessRestrictedAttribute__[T]):
	def check_access(self, arc: __AccessRestrictedClass__, instance: typing.Any, calling_stack: tuple[inspect.FrameInfo, ...]) -> bool:
		for frame in calling_stack:
			for variable in frame.frame.f_locals.values():
				if isinstance(variable, self.arc):
					return True

		return False

	@property
	def access_qualifier(self) -> str:
		return 'protected'


class __FiledAttribute__[T](__AccessRestrictedAttribute__[T]):
	def check_access(self, arc: __AccessRestrictedClass__, instance: typing.Any, calling_stack: tuple[inspect.FrameInfo, ...]) -> bool:
		return os.path.abspath(self.frame.filename) == os.path.abspath(calling_stack[0].filename)

	@property
	def access_qualifier(self) -> str:
		return 'filed'


class __PackagedAttribute__[T](__AccessRestrictedAttribute__[T]):
	def check_access(self, arc: __AccessRestrictedClass__, instance: typing.Any, calling_stack: tuple[inspect.FrameInfo, ...]) -> bool:
		return os.path.dirname(os.path.abspath(self.frame.filename)) == os.path.dirname(os.path.dirname(calling_stack[0].filename))

	@property
	def access_qualifier(self) -> str:
		return 'packaged'


class __PublicAttribute__[T](__AccessRestrictedAttribute__[T]):
	def check_access(self, arc: __AccessRestrictedClass__, instance: typing.Any, calling_stack: tuple[inspect.FrameInfo, ...]) -> bool:
		return True

	@property
	def access_qualifier(self) -> str:
		return 'public'


def ARC(class_def: type | __AccessRestrictedClass__) -> __AccessRestrictedClass__:
	"""
	Decorator used to mark a class as supporting access restricted attributes
	This will allow the use of the access decorators to control attribute access
	:param class_def: The class to make access restricted
	:return: The new ARC wrapper
	:raises InvalidArgumentException: If 'class_def' is not a type
	"""

	Misc.raise_ifn(isinstance(class_def, type), Exceptions.InvalidArgumentException(ARC, 'class_def', type(class_def), (type,)))

	if isinstance(type(class_def), __AccessRestrictedClass__):
		return class_def

	class MyARC(class_def, metaclass=__AccessRestrictedClass__):
		def __delattr__(self, name: str) -> None:
			type(self).__delinstattribute__(self, name)

		def __setattr__(self, name: str, value: typing.Any) -> None:
			type(self).__setinstattribute__(self, name, value)

		def __getattribute__(self, name: str) -> typing.Any:
			return type(self).__getinstattribute__(self, name)

	MyARC.__name__ = class_def.__name__
	MyARC.__qualname__ = class_def.__qualname__

	for attribute in vars(class_def).values():
		if isinstance(attribute, __AccessRestrictedAttribute__):
			if attribute.__arc__ is ...:
				attribute.__arc__ = MyARC

	return MyARC


def Private[T](attribute: T) -> __AccessRestrictedAttribute__[T]:
	"""
	Marks an attribute as 'private'
	Private attributes may only be accessed within this class
	:param attribute: The attribute to mark
	:return: The access restricted attribute
	"""

	parts: list[str] = attribute.__qualname__.split('.')
	Misc.raise_if(len(parts) < 2, ValueError('Supplied function is not bound to a class'))
	class_name: str = parts[-2]
	return __PrivateAttribute__(class_name, attribute)


def Protected[T](attribute: T) -> __AccessRestrictedAttribute__[T]:
	"""
	Marks an attribute as 'protected'
	Protected attributes may only be accessed within this class and child classes
	:param attribute: The attribute to mark
	:return: The access restricted attribute
	"""

	parts: list[str] = attribute.__qualname__.split('.')
	Misc.raise_if(len(parts) < 2, ValueError('Supplied function is not bound to a class'))
	class_name: str = parts[-2]
	return __ProtectedAttribute__(class_name, attribute)


def Filed[T](attribute: T) -> __AccessRestrictedAttribute__[T]:
	"""
	Marks an attribute as 'filed'
	Files attributes may only be accessed within the same file
	:param attribute: The attribute to mark
	:return: The access restricted attribute
	"""

	parts: list[str] = attribute.__qualname__.split('.')
	Misc.raise_if(len(parts) < 2, ValueError('Supplied function is not bound to a class'))
	class_name: str = parts[-2]
	return __FiledAttribute__(class_name, attribute)


def Packaged[T](attribute: T) -> __AccessRestrictedAttribute__[T]:
	"""
	Marks an attribute as 'packaged'
	Packaged attributes may only be accessed within the same package directory
	:param attribute: The attribute to mark
	:return: The access restricted attribute
	"""

	parts: list[str] = attribute.__qualname__.split('.')
	Misc.raise_if(len(parts) < 2, ValueError('Supplied function is not bound to a class'))
	class_name: str = parts[-2]
	return __FiledAttribute__(class_name, attribute)


def Public[T](attribute: T) -> __AccessRestrictedAttribute__[T]:
	"""
	Marks an attribute as 'public'
	Public attributes may be accessed anywhere
	*Containing class must also be marks as access restricted with the ARC decorator*
	:param attribute: The attribute to mark
	:return: The access restricted attribute
	"""

	parts: list[str] = attribute.__qualname__.split('.')
	Misc.raise_if(len(parts) < 2, ValueError('Supplied function is not bound to a class'))
	class_name: str = parts[-2]
	return __PublicAttribute__(class_name, attribute)
