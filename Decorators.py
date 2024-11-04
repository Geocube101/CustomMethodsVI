from __future__ import annotations

import sys
import threading
import typing
import types
import typeguard
import inspect

import CustomMethodsVI.Exceptions as Exceptions
import CustomMethodsVI.Stream as Stream


class __OverloadCaller:
	"""
	INTERNAL CLASS; DO NOT USE
	[__OverloadCaller] - Class for handling function overloads and delegation
	"""

	__FunctionOverloads: dict[str, __OverloadCaller] = {}
	__FunctionCallers: dict[typing.Callable, __OverloadCaller] = {}

	@classmethod
	def assoc(cls, lambda_: typing.Callable, caller: __OverloadCaller) -> None:
		if callable(caller):
			cls.__FunctionCallers[lambda_] = caller
		elif lambda_ in cls.__FunctionCallers:
			del cls.__FunctionCallers[lambda_]

	@classmethod
	def new(cls, function: typing.Callable | types.FunctionType | types.LambdaType | types.MethodType, strict_only: bool | None = False) -> __OverloadCaller:
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
			new_caller: __OverloadCaller = super().__new__(cls)
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
				return deduce_annotation(eval(annotation))
			else:
				raise TypeError(f'Non-standard type hint: \'{annotation}\' ({type(annotation)})')

		def can_cast(_value: typing.Any, _type: type) -> bool:
			if hasattr(_value, f'__cast_{_type.__name__}__') or isinstance(_value, _type) or _type.__init__ in type(self).__FunctionCallers:
				return True
			elif hasattr(_type, '__iter__') and _type.__name__ in dir(__builtins__) and hasattr(_value, '__iter__'):
				return True

			try:
				_type(_value)
				return True
			except (TypeError, ValueError, NotImplementedError):
				return False

		def cast(_value: typing.Any, _type: type) -> typing.Any:
			if hasattr(_value, f'__cast_{_type.__name__}__'):
				_result = getattr(_value, f'__cast_{_type.__name__}__')()

				if not isinstance(_result, _type):
					raise TypeError('CastingError during cast operation - returned cast is not the correct type')

				return _result

			try:
				return _type(_value)
			except (TypeError, ValueError, NotImplementedError):
				return False

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

	def __get_function_annotations(self) -> dict[typing.Callable, dict[str, tuple[type, ...]]]:
		"""
		INTERNAL METHOD; DO NOT USE
		Gets function parameter types from annotations
		:return: (dict[str, tuple[type]]) The function parameter type map
		"""

		parameter_types_map: dict[typing.Callable, dict[str, tuple[type, ...]]] = {}

		for function in self.__function_overloads:
			parameter_map: dict[str, tuple[type, ...]] = {}
			parameter: str
			parameter_type: type | types.Union

			for parameter, parameter_type in typing.get_type_hints(function).items():
				if parameter == 'return':
					continue
				elif isinstance(parameter_type, (type, typing._GenericAlias, typing._SpecialGenericAlias)):
					parameter_map[parameter] = (parameter_type,)
				elif isinstance(parameter_type, types.UnionType):
					parameter_map[parameter] = parameter_type.__args__
				elif parameter_type == typing.Callable:
					parameter_map[parameter] = (types.FunctionType, types.MethodType, types.BuiltinFunctionType, types.LambdaType, types.MethodDescriptorType)
				else:
					raise TypeError(f'Non-standard type hint: \'{parameter_type}\' ({type(parameter_type)})')

			for parameter_types in parameter_map.values():
				assert all(isinstance(x, (type, typing._GenericAlias, typing._SpecialGenericAlias)) for x in parameter_types)

			parameter_types_map[function] = parameter_map

		return parameter_types_map


def Overload(*function: typing.Callable, strict: bool = False) -> typing.Callable:
	"""
	Decorator for overloading functions
	Function parameters must be type hinted (or typing.Any is assumed)
	This decorator is not suitable for pickling
	:param function: (CALLABLE) The function to decorate
	:param strict: (bool) Whether to only allow exact types (defaults to False)
	:return: (CALLABLE) Binder
	"""

	if len(function) == 0:
		def binder(callback: typing.Callable):
			caller: __OverloadCaller = __OverloadCaller.new(callback, strict)
			redirect: typing.Callable = lambda *args, __caller=caller, **kwargs: __caller(*args, **kwargs)
			__OverloadCaller.assoc(redirect, caller)
			return redirect

		return binder
	else:
		caller: __OverloadCaller = __OverloadCaller.new(function[0], strict)
		redirect: typing.Callable = lambda *args, __caller=caller, **kwargs: __caller(*args, **kwargs)
		__OverloadCaller.assoc(redirect, caller)
		return redirect


def DefaultOverload(function: typing.Callable):
	"""
	Decorator for overloading functions
	Marks this function as a default fallback
	This decorator is not suitable for pickling
	:return: (CALLABLE) Binder
	"""

	caller: __OverloadCaller = __OverloadCaller.new(function, None)
	redirect: typing.Callable = lambda *args, __caller=caller, **kwargs: __caller(*args, **kwargs)
	__OverloadCaller.assoc(redirect, caller)
	return redirect
