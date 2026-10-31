from __future__ import annotations

import ast
import collections
import collections.abc
import copy
import importlib.machinery
import importlib.util
import inspect
import multiprocessing
import multiprocessing.connection
import multiprocessing.context
import multiprocessing.managers
import multiprocessing.reduction
import multiprocessing.shared_memory
import multiprocessing.synchronize
import os
import sys
import threading
import time
import types
import typing

from . import Promise

from .. import Iterable
from .. import Misc
from .. import Wrapper


class SynchronizedVariablePool:
	@staticmethod
	def __value_copier__(value: typing.Any) -> tuple[bool, typing.Any]:
		"""
		* INTERNAL METHOD *
		Copies a value using copy.deepcopy
		:param value: The value to copy
		:return: A tuple containing whether the copy succeeded and the copied value
		"""

		try:
			true_value: typing.Any = value.cell_contents if isinstance(value, types.CellType) else value
			return True, copy.deepcopy(true_value)
		except (RuntimeError, TypeError, copy.Error):
			return False, None

	@staticmethod
	def __variable_map_assembler__(variable_dict: dict[str, typing.Any]) -> dict[str, typing.Any]:
		"""
		* INTERNAL METHOD *
		Creates the variable dictionary used to synchronize values between processes
		:param variable_dict: The variables to clone
		:return: The variable dictionary
		"""

		converted_map: dict[str, typing.Any] = {}

		for k, v in variable_dict.items():
			if k.startswith('__') or isinstance(v, (types.ModuleType, types.FunctionType, type, types.MethodType, type(annotations))):
				continue

			success, copied = SynchronizedVariablePool.__value_copier__(v)

			if not success:
				continue

			converted_map[k] = copied

		return converted_map

	def __init__(self, variable_dict: dict[str, typing.Any]):
		"""
		Handles synchronizing global and local variables between processes\n
		Modules, functions, and methods will not be synced\n
		Methods starting with '__' will not be synced
		:param variable_dict: The dictionary of variables to sync
		"""

		recv, send = multiprocessing.Pipe(True)
		self.__variables__: dict[str, typing.Any] = SynchronizedVariablePool.__variable_map_assembler__(variable_dict)
		self.__name_map__: dict[str, str] = {}
		self.__handles__: tuple[multiprocessing.connection.PipeConnection, multiprocessing.connection.PipeConnection] = (recv, send)
		self.__conn__: multiprocessing.connection.PipeConnection = ...
		self.__is_master__: bool = True
		self.__serialized__: bool = False

	def __setstate__(self, state: dict[str, typing.Any]) -> None:
		self.__dict__.update(state)
		self.__serialized__ = True

	def __iter__(self) -> collections.abc.Iterator[tuple[str, typing.Any]]:
		for k, v in self.__variables__.items():
			name: str = k if self.__is_master__ else self.__name_map__.get(k, k)
			yield name, v

	def __getstate__(self) -> dict[str, typing.Any]:
		recv, send = self.__handles__
		self.__conn__ = send if self.__conn__ is ... else self.__conn__
		self.__serialized__ = True
		removed: tuple[str, ...] = tuple(k for k in self.__name_map__ if k not in self.__variables__)

		for rem in removed:
			del self.__name_map__[rem]

		data: dict[str, typing.Any] = copy.copy(self.__dict__)
		data['__conn__'] = recv
		data['__is_master__'] = False
		return data

	def poll(self, frame: types.FrameType) -> None:
		"""
		Updates the variables' synchronization
		:param frame: The stack frame whose variables to update
		"""

		variable_maps: tuple[dict[str, typing.Any], ...] = (frame.f_locals, frame.f_globals)

		while self.__conn__.poll():
			name, value = self.__conn__.recv()

			if name in self.__variables__:
				self.__variables__[name] = copy.deepcopy(value)
				alt_name: str = name if self.__is_master__ else self.__name_map__.get(name, name)

				for vmap in variable_maps:
					if alt_name not in vmap:
						continue
					elif isinstance(cell := vmap[alt_name], types.CellType):
						cell.cell_contents = value
					else:
						vmap[alt_name] = value

		for name, reference in self.__variables__.items():
			updated: bool = False
			new_value: typing.Any = None
			alt_name: str = name if self.__is_master__ else self.__name_map__.get(name, name)

			for i, variables in enumerate(variable_maps):
				if alt_name not in variables:
					continue
				elif updated and isinstance(cell := variables[alt_name], types.CellType):
					cell.cell_contents = new_value
					continue
				elif updated:
					variables[alt_name] = new_value
					continue

				value: typing.Any = variables[alt_name]

				if isinstance(value, types.CellType):
					value = value.cell_contents

				if reference == value:
					continue

				updated = True
				new_value = value

			if updated:
				self.__conn__.send((name, new_value))
				self.__variables__[name] = copy.deepcopy(new_value)

	def update(self, variable_dict: dict[str, typing.Any]) -> None:
		"""
		Appends new variables to track to this pool
		:param variable_dict: The variable map to append
		"""

		assert not self.__serialized__, 'Variable pool already serialized'
		self.__variables__.update(SynchronizedVariablePool.__variable_map_assembler__(variable_dict))

	def set_name_alias(self, true_name: str, alt_name: str) -> None:
		"""
		Sets an alias in the name pool
		:param true_name: The true variable name
		:param alt_name: The alternate alias
		"""

		assert isinstance(true_name, str) and len(true_name := str(true_name).strip()) > 0
		assert isinstance(alt_name, str) and len(alt_name := str(alt_name).strip()) > 0
		assert true_name not in self.__name_map__ and alt_name not in self.__name_map__
		self.__name_map__[true_name] = alt_name
		self.__name_map__[alt_name] = true_name


class CallableInfo:
	@staticmethod
	def __lambda_source_getter__(function: types.LambdaType) -> list[str]:
		"""
		Retrieves the source code for a lambda function\n
		Resulting source code is an assignment binding lambda to a variable
		:param function: The lambda function
		:return: The assignment source code
		"""

		root: ast.AST = ast.parse(inspect.getsource(function).strip())
		lambdas: tuple[ast.Lambda, ...] = tuple(node for node in ast.walk(root) if isinstance(node, ast.Lambda))
		Misc.raise_if(len(lambdas) > 1, OSError('Failed to resolve lambda source - too many lambda definitions on line'))
		Misc.raise_if(len(lambdas) == 0, OSError('Failed to resolve lambda source - no lambda definitions on line'))
		code_str: str = ast.unparse(lambdas[0])
		return [f'lambda_{hex(id(function))} = {code_str}\n']

	@staticmethod
	def __is_lambda__(function: typing.Callable) -> bool:
		"""
		Checks if a function is actually a lambda
		:param function: The function to check
		:return: Lambdaness
		"""

		return isinstance(function, types.LambdaType) and function.__name__ == '<lambda>'

	def __init__(self, function: typing.Callable):
		"""
		Class holding information on a callable object
		:param function: The callable object
		"""

		assert callable(function)
		is_lambda: bool = CallableInfo.__is_lambda__(function)
		self.__is_builtin__: bool = isinstance(function, (types.BuiltinMethodType, types.BuiltinFunctionType, type))
		self.__data__: list[str] = [] if self.is_builtin else CallableInfo.__lambda_source_getter__(function) if is_lambda else inspect.getsourcelines(function)[0]
		self.__this__: typing.Any = function.__self__ if isinstance(function, (types.MethodType, types.BuiltinMethodType)) else ...
		self.__fpath__: str = '' if self.is_builtin else sys.modules[function.__module__].__file__
		self.__closures__: dict[str, types.CellType] = {} if not hasattr(function, '__code__') or not isinstance(function.__closure__, tuple) else {name: var for name, var in zip(function.__code__.co_freevars, function.__closure__)}
		self.__fname__: str = f'lambda_{hex(id(function))}' if is_lambda else function.__name__
		self.__parameters__: collections.OrderedDict[str, inspect.Parameter] = collections.OrderedDict(inspect.signature(function).parameters)

	def __getstate__(self) -> dict[str, typing.Any]:
		data: dict[str, typing.Any] = copy.copy(vars(self))
		data['__closures__'] = {k: v.cell_contents for k, v in self.__closures__.items()}
		return data

	@property
	def is_builtin(self) -> bool:
		"""
		:return: Whether the callable is a type or builtin function/method
		"""

		return self.__is_builtin__

	@property
	def is_method(self) -> bool:
		"""
		:return: Whether the callable is a method
		"""

		return self.__this__ is not ...

	@property
	def data(self) -> list[str]:
		"""
		:return: The code lines or ... if not a user defined callable
		"""

		return self.__data__

	@property
	def filepath(self) -> str:
		"""
		:return: The filename defining this function or an empty string if a builtin
		"""

		return self.__fpath__

	@property
	def function_name(self) -> str:
		"""
		:return: The function name
		"""

		return self.__fname__

	@property
	def this(self) -> typing.Any:
		"""
		:return: The method 'self' variable if a method otherwise ...
		"""

		return self.__this__

	@property
	def closures(self) -> dict[str, types.CellType]:
		"""
		:return: A mapping of variable names and closure cells
		"""

		return self.__closures__

	@property
	def parameters(self) -> collections.OrderedDict[str, inspect.Parameter]:
		"""
		:return: A mapping of parameters
		"""

		return self.__parameters__


class ProcessExecutor:
	@staticmethod
	def varsync(variables: SynchronizedVariablePool, local_frame: Wrapper.OptionalReference[types.FrameType], event: threading.Event) -> None:
		"""
		Synchronizes the stack frame variables once every 100ns
		:param variables: The synchronized variable pool to update
		:param local_frame: The stack frame to update
		:param event: Event used to terminate this loop if set
		"""

		while not event.is_set():
			if local_frame.has_value:
				variables.poll(local_frame.value)

	@staticmethod
	def wrapper(function_vars: SynchronizedVariablePool, function: typing.Callable, args: tuple[typing.Any, ...], kwargs: dict[str, typing.Any], local_frame: Wrapper.OptionalReference[types.FrameType]) -> typing.Any:
		"""
		Wrapper function used to call the target function and synchronize variables with parent
		:param function_vars: The synchronized variable pool to update
		:param function: The function to call
		:param args: The function arguments
		:param kwargs: The function keyword arguments
		:param local_frame: The function inner stack frame
		:return: The function return value
		"""

		sync: bool = function_vars is not ...
		event: threading.Event = threading.Event()
		thread: threading.Thread = threading.Thread(target=ProcessExecutor.varsync, args=(function_vars, local_frame, event))

		if sync:
			thread.start()

		try:
			return function(*args, **kwargs)
		finally:
			if sync:
				event.set()
				thread.join()

				if local_frame.has_value:
					function_vars.poll(local_frame.value)

	@staticmethod
	def execute(py_file: str, function_info: CallableInfo, frame_variables: SynchronizedVariablePool, promise: Promise.ConcurrentPromise[typing.Any], args: tuple[typing.Any, ...], kwargs: dict[str, typing.Any]) -> None:
		"""
		Main executor
		:param py_file: The file containing the function definition
		:param function_info: The function info
		:param frame_variables: The function frame variables to sync
		:param promise: The promise to send return value
		:param args: The function arguments
		:param kwargs: The function keyword arguments
		"""

		try:
			function_vars: dict[str, typing.Any] = {}
			this_module: types.ModuleType = sys.modules['__main__']

			if py_file:
				module_spec: importlib.machinery.ModuleSpec = importlib.util.spec_from_file_location('main', py_file)
				module: types.ModuleType = importlib.util.module_from_spec(module_spec)
				sys.modules['__main__'] = module
				sys.modules['main'] = module
				module_spec.loader.exec_module(module)
				function_vars.update(module.__dict__)

			local_frame: Wrapper.OptionalReference[types.FrameType] = Wrapper.OptionalReference.create_empty()

			if frame_variables is not ...:
				function_vars.update({k: copy.deepcopy(v) for k, v in frame_variables})

			if function_info.is_builtin and function_info.is_method:
				function: typing.Callable = getattr(function_info.this, function_info.function_name)
			elif function_info.is_builtin:
				function: typing.Callable = eval(function_info.function_name, function_vars)
			else:
				lowest_indent: int = ...
				lines: list[str] = function_info.data
				code_lines: list[str] = [
					'import inspect\n',
					'def __procmain(varmap, frame_ref):\n',
					'\tglobals().update(varmap)\n',
					'\tdel varmap\n'
				]

				for line in lines:
					count: int = 0

					for c in line:
						if c == ' ' or c == '\t':
							count += 1
						else:
							break

					lowest_indent = count if lowest_indent is ... else min(lowest_indent, count)

				for i, line in enumerate(lines):
					lines[i] = '\t' + line[lowest_indent:]

				for name, value in function_info.closures.items():
					lines.insert(0, f'\t{name} = {value}\n')

				temp: dict[str, typing.Any] = {}
				code_lines.extend(lines)
				code_lines.append(f'\treturn {function_info.function_name}\n')
				code_lines.insert(5, '\t\tframe_ref.value = inspect.currentframe()\n')
				code_str: str = ''.join(code_lines)
				code_lines.clear()
				lines.clear()
				exec(code_str, temp)
				function: typing.Callable = temp['__procmain'](function_vars, local_frame)

				if function_info.is_method:
					args = (function_info.this, *args)

			result: typing.Any = ProcessExecutor.wrapper(frame_variables, function, args, kwargs, local_frame)
			sys.modules['__main__'] = this_module

			if frame_variables is not ... and local_frame.has_value:
				frame_variables.poll(local_frame.value)

			promise.resolve(result)
		except Exception as err:
			promise.throw(err)
			raise err
		finally:
			sys.stdout.flush()
			sys.stderr.flush()
			time.sleep(1e-6)


class Process:
	def __init__(self, function: typing.Callable, *, sync_variables: bool = True):
		"""
		Class representing a sub-process executing a single callable\n
		If 'sync_variables' is enabled, user must define their own locks when necessary
		:param function: The function to execute
		:param sync_variables: Whether to synchronize the stack frame variables between processes
		"""

		Misc.raise_ifn(callable(function), TypeError('Specified function is not callable'))
		Misc.raise_ifn(hasattr(function, '__module__'), ValueError())
		sync_variables: bool = bool(sync_variables)

		self.__function__: CallableInfo = CallableInfo(function)
		self.__frame__: types.FrameType = inspect.currentframe().f_back
		self.__fpath__: str = self.__frame__.f_code.co_filename
		self.__variable_pool__: SynchronizedVariablePool = SynchronizedVariablePool(self.__frame__.f_globals | self.__function__.closures) if sync_variables else ...
		self.__process__: multiprocessing.Process = ...
		self.__process_handle__: threading.Thread = ...
		self.__return_value__: Promise.ConcurrentPromise[typing.Any] = Promise.ConcurrentPromise()

	def __await__(self) -> collections.abc.Iterator[typing.Optional[int]]:
		"""
		Waits for the underlying process to finish
		:return: The exit code or None if still running
		"""

		while self.is_alive():
			yield None

		return self.exit_code

	def __call__(self, *args, **kwargs) -> Process:
		"""
		Starts the process
		:param args: The callable arguments
		:param kwargs: The callable keyword arguments
		:return: This process instance
		"""

		if self.__process__ is not ...:
			raise OSError('Process was already started')

		outer_frame: types.FrameType = inspect.currentframe().f_back
		frame_argument_vars: dict[str, typing.Any] = {}
		argument_vars: dict[str, typing.Any] = {}
		parameter_names: tuple[str, ...] = tuple(self.__function__.parameters.keys())

		for arg in (*args, *kwargs.values()):
			if not Misc.is_mutable(arg):
				continue

			matching: tuple[tuple[str, typing.Any], ...] = tuple((k, v) for k, v in (outer_frame.f_locals | outer_frame.f_globals).items() if arg is v)

			if len(matching) != 1:
				continue

			name, value = matching[0]
			frame_argument_vars[name] = value

		for i, arg in enumerate(args):
			parameter_name: str = parameter_names[i]
			assert parameter_name not in argument_vars, f'Parameter {parameter_name} already supplied'
			argument_vars[parameter_name] = arg

		for parameter_name, arg in kwargs.items():
			assert parameter_name not in argument_vars, f'Parameter {parameter_name} already supplied'
			argument_vars[parameter_name] = arg

		for parameter_name, arg in argument_vars.items():
			success, frame_name = Iterable.safe_next(name for name, value in frame_argument_vars.items() if value is arg)

			if success and frame_name != parameter_name:
				self.__variable_pool__.set_name_alias(frame_name, parameter_name)

		self.__variable_pool__.update(frame_argument_vars)
		self.__process__ = multiprocessing.Process(target=ProcessExecutor.execute, args=(self.__fpath__, self.__function__, self.__variable_pool__, self.__return_value__, args, kwargs))
		self.__process__.start()

		if self.__variable_pool__ is not ...:
			self.__process_handle__ = threading.Thread(target=self.__process_printer__, args=(self.__frame__,))
			self.__process_handle__.start()

		return self

	def __process_printer__(self, frame: types.FrameType) -> None:
		"""
		* INTERNAL METHOD *
		Prints sub-process output and updates stack frame variables
		:param frame: The stack frame to update
		"""

		while self.is_alive():
			self.__variable_pool__.poll(frame)

		self.__variable_pool__.poll(frame)

	def signal(self, sig: int) -> None:
		"""
		Sends a signal to the underlying remote process
		:param sig: The signal to send
		"""

		if self.__process__ is ...:
			raise OSError('Process is not started')

		os.kill(self.__process__.pid, sig)

	def kill(self) -> None:
		"""
		Kills the underlying process\n
		Sends SIGKILL
		"""

		if self.__process__ is ...:
			raise OSError('Process is not started')

		self.__process__.kill()

	def terminate(self) -> None:
		"""
		Terminates the underlying process\n
		Sends SIGTERM
		"""

		if self.__process__ is ...:
			raise OSError('Process is not started')

		self.__process__.terminate()

	def join(self, timeout: typing.Optional[float] = None) -> typing.Optional[int]:
		"""
		Waits for the underlying process to finish
		:param timeout: The number of seconds to wait at most
		:return: The exit code
		"""

		if self.__process__ is ...:
			raise OSError('Process is not started')

		self.__process__.join(timeout)

		if not self.is_alive():
			self.__process_handle__.join()

		return self.__process__.exitcode

	def is_alive(self) -> bool:
		"""
		:return: Whether the process is alive
		"""

		return self.__process__ is not ... and self.__process__.is_alive()

	@property
	def has_return_value(self) -> bool:
		"""
		:return: Whether the process successfully returned a value
		"""

		return self.__return_value__.fulfilled()

	@property
	def return_value(self) -> typing.Any:
		"""
		:return: The return value or raises an error if no return value received
		"""

		if not self.has_return_value:
			raise IOError('No return value received')

		return self.__return_value__.response()

	@property
	def pid(self) -> int:
		"""
		:return: The underlying process's PID
		"""

		if self.__process__ is ...:
			raise OSError('Process is not started')

		return self.__process__.pid

	@property
	def exit_code(self) -> typing.Optional[int]:
		"""
		:return: The underlying process's exit code
		"""

		if self.__process__ is ...:
			raise OSError('Process is not started')

		return self.__process__.exitcode


__all__: list[str] = ['Process']
