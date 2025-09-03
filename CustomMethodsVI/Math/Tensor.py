from __future__ import annotations

import collections.abc
import math
import numpy
import os
import random
import typing
import types

from ..Math import Functions, Vector
from ..Decorators import Overload


class Tensor(typing.SupportsRound['Tensor'], typing.SupportsAbs['Tensor'], collections.abc.Hashable):
	"""
	Class representing an N-rank tensor
	"""

	@classmethod
	def shaped(cls, array: typing.Iterable[typing.Optional[float]], dimension: int, *dimensions: int) -> Tensor:
		"""
		Creates a tensor from the specified iterable with the specified dimensions
		:param array: The input values
		:param dimension: The first dimension
		:param dimensions: All subsequent dimensions
		:return: The shaped tensor
		"""

		instance: Tensor = cls(dimension, *dimensions)
		size: int = len(instance)

		for i, x in enumerate(tuple(array)[:size]):
			if isinstance(x, (float, int)):
				instance.__array__[i] = float(x)
			elif x is None or x is ...:
				instance.__array__[i] = None
			else:
				raise TypeError(f'Unexpected tensor value \'{x}\' ({type(x)}), expected either a float, int, \'...\' or None')

		return instance

	@classmethod
	def random(cls, dimension: int, *dimensions: int) -> Tensor:
		"""
		Creates a tensor from random values with the specified dimensions
		:param dimension: The first dimension
		:param dimensions: All subsequent dimensions
		:return: The shaped random tensor
		"""

		instance: Tensor = cls(dimension, *dimensions)

		for i in range(len(instance)):
			instance.__array__[i] = random.random()

		return instance

	@classmethod
	def osrandom(cls, dimension: int, *dimensions: int) -> Tensor:
		"""
		Creates a tensor from random values with the specified dimensions
		:param dimension: The first dimension
		:param dimensions: All subsequent dimensions
		:return: The shaped random tensor
		"""

		instance: Tensor = cls(dimension, *dimensions)
		random_bytes: bytes = os.urandom(len(instance))

		for i in range(len(instance)):
			instance.__array__[i] = float(random_bytes[i])

		return instance

	@classmethod
	def identity(cls, dimension: int, *dimensions: int) -> Tensor:
		"""
		Creates an identity tensor with the specified dimensions
		:param dimension: The first dimension
		:param dimensions: All subsequent dimensions
		:return: The identity tensor
		"""

		instance: Tensor = cls(dimension, *dimensions)

		for i in range(len(instance)):
			pos: tuple[int, ...] = instance.__index_to_position__(i)
			instance.__array__[i] = 1 if all(x == pos[0] for x in pos) else 0

		return instance

	@classmethod
	def full(cls, value: typing.Optional[float] | types.EllipsisType, dimension: int, *dimensions: int) -> Tensor:
		"""
		Creates a tensor setting all values to the specified value
		:param value: The value for all tensor cells
		:param dimension: The first dimension
		:param dimensions: All subsequent dimensions
		:return: The shaped tensor
		"""

		if isinstance(value, (float, int)):
			value = float(value)
		elif value is None or value is ...:
			value = None
		else:
			raise TypeError(f'Unexpected tensor value \'{value}\' ({type(value)}), expected either a float, int, \'...\' or None')

		size: int = math.prod((dimension, *dimensions))
		return cls.shaped([value] * size, dimension, *dimensions)

	@classmethod
	def alternating(cls, dimension: int, *dimensions: int) -> Tensor:
		"""
		Creates a tensor alternating all values between 0 and 1
		:param dimension: The first dimension
		:param dimensions: All subsequent dimensions
		:return: The shaped tensor
		"""

		return cls.shaped((1 if i % 2 == 0 else -1 for i in range(math.prod((dimension, *dimensions)))), dimension, *dimensions)

	@Overload(strict=True)
	def __init__(self, dimension: int, *dimensions: int):
		"""
		Class representing an N-rank tensor
		- Constructor -
		Creates an empty tensor with the specified dimensions
		:param dimension: The first dimension
		:param dimensions: All subsequent dimensions
		"""

		dimensions: tuple[int, ...] = (dimension, *dimensions)
		self.__size__: int = math.prod(dimensions)
		self.__dimensions__: tuple[int, ...] = tuple(int(d) for d in dimensions)
		self.__array__: list[float | None] = [None] * self.__size__

	@Overload(strict=True)
	def __init__(self, tensor: typing.Iterable):
		"""
		Class representing an N-rank tensor
		- Constructor -
		Creates a tensor from an iterable
		:param tensor: The source iterable
		"""

		def _flattener(__flattened: list[float | None], __index: int, __input: typing.Any, __dimensions: dict[int, int]) -> None:
			if hasattr(__input, '__iter__') and not isinstance(__input, str):
				__input: tuple = tuple(__input)

				for x in __input:
					_flattener(__flattened, __index + 1, x, __dimensions)

				__dimensions[__index] = max(__dimensions[__index], len(__input)) if __index in __dimensions else len(__input)

			elif isinstance(__input, (float, int)):
				__flattened.append(float(__input))
			elif __input is None or __input is ...:
				__flattened.append(None)
			else:
				raise TypeError(f'Unexpected tensor value \'{__input}\' ({type(__input)}), expected either a float, int, \'...\' or None')

		dimensions: dict[int, int] = {}
		flattened: list[float | None] = []
		_flattener(flattened, 0, tensor, dimensions)
		dimensions: tuple[int, ...] = tuple(dimensions[x] for x in sorted(dimensions.keys()))
		self.__size__: int = len(flattened)
		self.__dimensions__: tuple[int, ...] = tuple(int(d) for d in dimensions)
		self.__array__: list[float | None] = flattened

	@Overload(strict=True)
	def __init__(self, tensor: Tensor):
		"""
		Class representing an N-rank tensor
		- Constructor -
		Copies a tensor into this one
		:param tensor: The source tensor
		"""

		self.__size__: int = int(tensor.__size__)
		self.__dimensions__: tuple[int, ...] = tuple(tensor.__dimensions__)
		self.__array__: list[float | None] = list(tensor.__array__.copy())

	@Overload(strict=True)
	def __init__(self, tensor: numpy.ndarray):
		"""
		Class representing an N-rank tensor
		- Constructor -
		Copies a tensor into this one
		:param tensor: The source tensor
		"""

		self.__size__: int = int(tensor.size)
		self.__dimensions__: tuple[int, ...] = tuple(tensor.shape)
		self.__array__: list[float | None] = list(tensor)

	def __index_to_position__(self, index: int) -> tuple[int, ...]:
		"""
		INTERNAL METHOD
		Converts a flat index into a tensor position
		:param index: The flat index to convert
		:return: The tensor cell coordinate
		"""

		position: list[int] = [index]

		for i in range(1, len(self.__dimensions__)):
			d: int = position[-1] // self.__dimensions__[i]
			m: int = position[-1] % self.__dimensions__[i]
			position[-1] = m
			position.append(d)

		return tuple(reversed(position))

	def __position_to_index__(self, position: tuple[int, ...]) -> int:
		"""
		INTERNAL METHOD
		Converts a tensor position into a flat index
		:param position: The tensor cell coordinate to convert
		:return: The flat index
		"""

		return sum(pos * math.prod(self.__dimensions__[i + 1:]) for i, pos in enumerate(position))

	def __hash__(self) -> int:
		return hash(tuple(self.__array__))

	def __len__(self) -> int:
		"""
		:return: The number of cells in this tensor
		"""

		return self.__size__

	def __iter__(self) -> typing.Iterator[typing.Optional[float] | Tensor | Vector.Vector]:
		"""
		:return: An iterator over the major dimension of this tensor
		"""

		for i in range(self.__dimensions__[0]):
			yield self[i]

	def __repr__(self) -> str:
		return f'<{type(self).__name__} {"x".join(str(x) for x in self.__dimensions__)} @ {hex(id(self))}>'

	def __str__(self) -> str:
		return str(self.to_nested())

	def __abs__(self) -> Tensor:
		"""
		:return: A copy of this tensor with all cells absolute
		"""

		return Tensor.shaped((None if x is None else abs(x) for x in self.__array__), *self.__dimensions__)

	def __round__(self, n: typing.Optional[int] = None) -> Tensor | int:
		"""
		:param n: The number of places to round to
		:return: A copy of this tensor with all cells rounded
		"""

		return Tensor.shaped((None if x is None else round(x, n) for x in self.__array__), *self.__dimensions__)

	def __getitem__(self, position: tuple[int | slice, ...] | int | slice) -> typing.Optional[float | Tensor | Vector.Vector]:
		"""
		Gets either the sub-tensor, cell value, or vector from this tensor
		:param position: The zero-indexed cell position
		:return: The cell value, sub-tensor, or vector
		"""

		if isinstance(position, int):
			position = position if (position := int(position)) >= 0 else self.__dimensions__[0] + position

			if self.dimension == 1:
				return self.__array__[position]
			elif self.dimension == 2:
				index: int = self.__position_to_index__((position, 0))
				return Vector.Vector(self.__array__[index:index + self.__dimensions__[1]])
			else:
				index: int = self.__position_to_index__((position, *[0 for _ in range(self.dimension - 1)]))
				return Tensor.shaped(self.__array__[index:index + math.prod(self.__dimensions__[1:])], *self.__dimensions__[1:])
		elif isinstance(position, slice):
			start: int = 0 if position.start is None else int(position.start)
			stop: int = self.__dimensions__[0] if position.stop is None else int(position.stop)
			step: int = 1 if position.step is None else int(position.step)
			start = start if start >= 0 else self.__dimensions__[0] + start
			stop = stop if stop >= 0 else self.__dimensions__[0] + stop

			if self.dimension == 1:
				return Vector.Vector(self.__array__[start:stop:step])
			else:
				return Tensor(self[i] for i in range(start, stop, step))
		elif not isinstance(position, tuple):
			raise TypeError(f'Matrix position must be a tuple, slice, or integer, not \'{type(position).__name__}\'')
		elif len(position) > len(self.__dimensions__):
			raise ValueError(f'Cannot index dimension \'{len(position)}\' for a tensor of rank \'{len(self.__dimensions__)}\'')

		def lister(source: list, posdex: int) -> None:
			pos: int | slice = position[posdex]

			for i in range(len(source)):
				source[i] = source[i][pos]

				if posdex + 1 < len(position):
					lister(source[i], posdex + 1)

		result: list = self.to_nested()[position[0]]
		lister(result, 1)
		return Tensor(result)

	def __add__(self, other: float | int | Tensor) -> Tensor:
		"""
		Adds this tensor with another tensor or number
		:param other: The single number or tensor to add
		:return: The added tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else x + float(other) for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot add tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else (a + b) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __sub__(self, other: float | int | Tensor) -> Tensor:
		"""
		Subtracts this tensor with another tensor or number
		:param other: The single number or tensor to subtract
		:return: The subtracted tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else x - float(other) for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot subtract tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else (a - b) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __mul__(self, other: float | int | Tensor) -> Tensor:
		"""
		Multiplies this tensor with another tensor or number
		:param other: The single number or tensor to multiply
		:return: The multiplied tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else x * float(other) for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot multiply tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else (a * b) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __matmul__(self, other: Tensor | numpy.ndarray[typing.Any]) -> Tensor:
		"""
		Tensor-multiplies this tensor with another tensor or number
		:param other: The tensor to multiply
		:return: The tensor-multiplied tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if not isinstance(other, (type(self), numpy.ndarray)):
			return NotImplemented
		elif isinstance(other, numpy.ndarray):
			other = Tensor(other)

		if self.dimension != other.dimension:
			raise ValueError(f'Cannot tensor-multiply {len(other.__dimensions__)}-dimensional tensor with {len(self.__dimensions__)}-dimensional tensor')
		elif (self.dimension == 2 and self.__dimensions__[-1] != other.__dimensions__[0]) or (self.dimension > 2 and self.__dimensions__[:-2] != other.__dimensions__[:-2]):
			raise ValueError(f'Cannot tensor-multiply tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')
		else:
			tensor_a: numpy.ndarray[float | None] = self.to_numpy()
			tensor_b: numpy.ndarray[float | None] = other.to_numpy()
			return Tensor(tuple(numpy.tensordot(tensor_a, tensor_b, 1)))

	def __truediv__(self, other: float | int | Tensor) -> Tensor:
		"""
		Divides this tensor with another tensor or number
		:param other: The single number or tensor to divide
		:return: The divided tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else Functions.safe_divide(x, float(other)) for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else Functions.safe_divide(a, b) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __floordiv__(self, other: float | int | Tensor) -> Tensor:
		"""
		Floor-divides this tensor with another tensor or number
		:param other: The single number or tensor to floor-divide
		:return: The floor-divided tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else Functions.safe_floor_divide(x, float(other)) for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else Functions.safe_floor_divide(a, b) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __mod__(self, other: float | int | Tensor) -> Tensor:
		"""
		Modulos this tensor with another tensor or number
		:param other: The single number or tensor to modulo
		:return: The moduloed tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else Functions.safe_modulo(x, float(other)) for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot modulo tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else Functions.safe_modulo(a, b) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __divmod__(self, other: float | int | Tensor) -> Tensor:
		if not isinstance(other, (float, int, Tensor)):
			return NotImplemented
		elif isinstance(other, Tensor) and self.__dimensions__ != other.__dimensions__:
			raise ValueError(f'Cannot divide tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

		tensor: Tensor = Tensor(*self.__dimensions__, 2)

		for i, value in enumerate(self.__array__):
			a: typing.Optional[float] = self.__array__[i]
			b: typing.Optional[float] = other.__array__[i] if isinstance(other, Tensor) else float(other)
			a, b = None if a is None or b is None else Functions.safe_divmod(a, b)
			position: list[int] = [*list(self.__index_to_position__(i)), 0]
			tensor.__array__[tensor.__position_to_index__(tuple(position))] = a
			position[-1] = 1
			tensor.__array__[tensor.__position_to_index__(tuple(position))] = b

		return tensor

	def __pow__(self, other: float | int | Tensor) -> Tensor:
		"""
		Raises this tensor with another tensor or number
		:param other: The single number or tensor to raise by
		:return: The raised tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else x ** float(other) for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot exponentiate tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else (a ** b) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __radd__(self, other: float | int | Tensor) -> Tensor:
		"""
		Adds this tensor to another tensor or number
		:param other: The single number or tensor to add
		:return: The added tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else float(other) + x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot add tensor of dimension {"x".join(str(x) for x in self.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in other.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else (b + a) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rsub__(self, other: float | int | Tensor) -> Tensor:
		"""
		Subtracts this tensor from another tensor or number
		:param other: The single number or tensor to subtract
		:return: The subtracted tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else float(other) - x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot subtract tensor of dimension {"x".join(str(x) for x in self.__dimensions__)} from tensor of dimension {"x".join(str(x) for x in other.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else (b - a) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rmul__(self, other: float | int | Tensor) -> Tensor:
		"""
		Multiplies this tensor to another tensor or number
		:param other: The single number or tensor to multiply
		:return: The multiplied tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else float(other) * x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot multiply tensor of dimension {"x".join(str(x) for x in self.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in other.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else (b * a) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rmatmul__(self, other: Tensor | numpy.ndarray[typing.Any]) -> Tensor:
		"""
		Tensor-multiplies this tensor to another tensor or number
		:param other: The tensor to multiply
		:return: The tensor-multiplied tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if not isinstance(other, (type(self), numpy.ndarray)):
			return NotImplemented
		elif isinstance(other, numpy.ndarray):
			other = Tensor(other)

		if self.dimension != other.dimension:
			raise ValueError(f'Cannot tensor-multiply {len(other.__dimensions__)}-dimensional tensor with {len(self.__dimensions__)}-dimensional tensor')
		elif (self.dimension == 2 and self.__dimensions__[-1] != other.__dimensions__[0]) or (self.dimension > 2 and self.__dimensions__[:-2] != other.__dimensions__[:-2]):
			raise ValueError(f'Cannot tensor-multiply tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')
		else:
			tensor_a: numpy.ndarray[float | None] = other.to_numpy()
			tensor_b: numpy.ndarray[float | None] = self.to_numpy()
			return Tensor(tuple(numpy.tensordot(tensor_a, tensor_b, 1)))

	def __rtruediv__(self, other: float | int | Tensor) -> Tensor:
		"""
		Divides this tensor from another tensor or number
		:param other: The single number or tensor to divide
		:return: The divided tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else Functions.safe_divide(float(other), x) for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide tensor of dimension {"x".join(str(x) for x in self.__dimensions__)} from tensor of dimension {"x".join(str(x) for x in other.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else Functions.safe_divide(b, a) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rfloordiv__(self, other: float | int | Tensor) -> Tensor:
		"""
		Floor-divides this tensor from another tensor or number
		:param other: The single number or tensor to floor-divide
		:return: The floor-divided tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else Functions.safe_floor_divide(float(other), x) for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide tensor of dimension {"x".join(str(x) for x in self.__dimensions__)} from tensor of dimension {"x".join(str(x) for x in other.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else Functions.safe_floor_divide(b, a) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rmod__(self, other: float | int | Tensor) -> Tensor:
		"""
		Modulos this tensor from another tensor or number
		:param other: The single number or tensor to modulo
		:return: The moduloed tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else Functions.safe_modulo(float(other), x) for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot modulo tensor of dimension {"x".join(str(x) for x in self.__dimensions__)} from tensor of dimension {"x".join(str(x) for x in other.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else Functions.safe_modulo(b, a) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rdivmod__(self, other: float | int | Tensor) -> Tensor:
		if not isinstance(other, (float, int, Tensor)):
			return NotImplemented
		elif isinstance(other, Tensor) and self.__dimensions__ != other.__dimensions__:
			raise ValueError(f'Cannot divide tensor of dimension {"x".join(str(x) for x in self.__dimensions__)} from tensor of dimension {"x".join(str(x) for x in other.__dimensions__)}')

		tensor: Tensor = Tensor(*self.__dimensions__, 2)

		for i, value in enumerate(self.__array__):
			a: typing.Optional[float] = self.__array__[i]
			b: typing.Optional[float] = other.__array__[i] if isinstance(other, Tensor) else float(other)
			a, b = None if a is None or b is None else Functions.safe_divmod(b, a)
			position: list[int] = [*list(self.__index_to_position__(i)), 0]
			tensor.__array__[tensor.__position_to_index__(tuple(position))] = a
			position[-1] = 1
			tensor.__array__[tensor.__position_to_index__(tuple(position))] = b

		return tensor

	def __rpow__(self, other: float | int | Tensor) -> Tensor:
		"""
		Raises another tensor or number by this tensor
		:param other: The single number or tensor to raise
		:return: The raised tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):
			return Tensor.shaped((None if x is None else float(other) ** x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot exponentiate tensor of dimension {"x".join(str(x) for x in self.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in other.__dimensions__)}')

			return Tensor.shaped((None if a is None or b is None else (b ** a) for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __iadd__(self, other: float | int | Tensor) -> Tensor:
		"""
		Adds this tensor with another tensor or number in-place
		:param other: The single number or tensor to add
		:return: This tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):

			for i in range(self.__size__):
				if self.__array__[i] is not None:
					self.__array__[i] += float(other)

			return self
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot add tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] = None if self.__array__[i] is None or other.__array__[i] is None else (self.__array__[i] + other.__array__[i])

			return self
		else:
			return NotImplemented

	def __isub__(self, other: float | int | Tensor) -> Tensor:
		"""
		Subtracts this tensor with another tensor or number in-place
		:param other: The single number or tensor to subtract
		:return: This tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):

			for i in range(self.__size__):
				if self.__array__[i] is not None:
					self.__array__[i] -= float(other)

			return self
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot subtract tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] = None if self.__array__[i] is None or other.__array__[i] is None else (self.__array__[i] - other.__array__[i])

			return self
		else:
			return NotImplemented

	def __imul__(self, other: float | int | Tensor) -> Tensor:
		"""
		Multiplies this tensor with another tensor or number in-place
		:param other: The single number or tensor to multiply
		:return: This tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):

			for i in range(self.__size__):
				if self.__array__[i] is not None:
					self.__array__[i] *= float(other)

			return self
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot multiply tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] = None if self.__array__[i] is None or other.__array__[i] is None else (self.__array__[i] * other.__array__[i])

			return self
		else:
			return NotImplemented

	def __imatmul__(self, other: Tensor | numpy.ndarray[typing.Any]) -> Tensor:
		"""
		Tensor-multiplies this tensor with another tensor or number in-place
		:param other: The single number or tensor to tensor-multiply
		:return: This tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if not isinstance(other, (type(self), numpy.ndarray)):
			return NotImplemented
		elif isinstance(other, numpy.ndarray):
			other = Tensor(other)

		if self.dimension != other.dimension:
			raise ValueError(f'Cannot tensor-multiply {len(other.__dimensions__)}-dimensional tensor with {len(self.__dimensions__)}-dimensional tensor')
		elif (self.dimension == 2 and self.__dimensions__[-1] != other.__dimensions__[0]) or (self.dimension > 2 and self.__dimensions__[:-2] != other.__dimensions__[:-2]):
			raise ValueError(f'Cannot tensor-multiply tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')
		else:
			tensor_a: numpy.ndarray[float | None] = self.to_numpy()
			tensor_b: numpy.ndarray[float | None] = other.to_numpy()
			self.__array__ = numpy.tensordot(tensor_a, tensor_b, 1).flatten()
			return self

	def __itruediv__(self, other: float | int | Tensor) -> Tensor:
		"""
		Divides this tensor with another tensor or number in-place
		:param other: The single number or tensor to divide
		:return: This tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):

			for i in range(self.__size__):
				if self.__array__[i] is not None:
					self.__array__[i] = Functions.safe_divide(self.__array__[i], float(other))

			return self
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} from tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] = None if self.__array__[i] is None or other.__array__[i] is None else Functions.safe_divide(self.__array__[i], other.__array__[i])

			return self
		else:
			return NotImplemented

	def __ifloordiv__(self, other: float | int | Tensor) -> Tensor:
		"""
		Floor-divides this tensor with another tensor or number in-place
		:param other: The single number or tensor to floor-divide
		:return: This tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):

			for i in range(self.__size__):
				if self.__array__[i] is not None:
					self.__array__[i] = Functions.safe_floor_divide(self.__array__[i], float(other))

			return self
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} from tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] = None if self.__array__[i] is None or other.__array__[i] is None else Functions.safe_floor_divide(self.__array__[i], other.__array__[i])

			return self
		else:
			return NotImplemented

	def __imod__(self, other: float | int | Tensor) -> Tensor:
		"""
		Modulos this tensor with another tensor or number in-place
		:param other: The single number or tensor to modulo
		:return: This tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):

			for i in range(self.__size__):
				if self.__array__[i] is not None:
					self.__array__[i] = Functions.safe_modulo(self.__array__[i], float(other))

			return self
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot modulo tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} from tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] = None if self.__array__[i] is None or other.__array__[i] is None else Functions.safe_modulo(self.__array__[i], other.__array__[i])

			return self
		else:
			return NotImplemented

	def __ipow__(self, other: float | int | Tensor) -> Tensor:
		"""
		Raises this tensor by another tensor or number in-place
		:param other: The single number or tensor to raise by
		:return: This tensor
		:raises ValueError: If the specified tensor's dimensions do not match
		"""

		if isinstance(other, (float, int)):

			for i in range(self.__size__):
				if self.__array__[i] is not None:
					self.__array__[i] **= float(other)

			return self
		elif isinstance(other, Tensor):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot exponentiate tensor of dimension {"x".join(str(x) for x in other.__dimensions__)} to tensor of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] = None if self.__array__[i] is None or other.__array__[i] is None else (self.__array__[i] ** other.__array__[i])

			return self
		else:
			return NotImplemented

	def __neg__(self) -> Tensor:
		"""
		Negates all elements in this tensor
		:return: The negative tensor
		"""

		return Tensor.shaped((None if x is None else -x for x in self.__array__), *self.__dimensions__)

	def __pos__(self) -> Tensor:
		"""
		:return: A copy of this tensor
		"""

		return Tensor.shaped((None if x is None else +x for x in self.__array__), *self.__dimensions__)

	def __trunc__(self) -> Vector:
		"""
		:return: Returns this tensor truncated
		"""

		return Tensor.shaped((None if x is None else math.trunc(x) for x in self.__components__), *self.__dimensions__)

	def __floor__(self) -> Vector:
		"""
		:return: Returns this tensor floored
		"""

		return Tensor.shaped((None if x is None else math.floor(x) for x in self.__components__), *self.__dimensions__)

	def __ceil__(self) -> Vector:
		"""
		:return: Returns this tensor ceiled
		"""

		return Tensor.shaped((None if x is None else math.ceil(x) for x in self.__components__), *self.__dimensions__)

	def is_square(self) -> bool:
		"""
		:return: Whether this tensor is square-like (all dimensions are equal)
		"""

		return all(d == self.__dimensions__[0] for d in self.__dimensions__[1:])

	def determinant(self) -> typing.Optional[float]:
		"""
		Calculates the determinate if this tensor is square
		:return: The determinate or None if any single value is None
		:raises AssertionError: If this tensor is not square-like
		"""

		assert self.is_square(), 'Matrix is not square'

		if self.__dimensions__ == (2, 2):
			a, b, c, d = self.__array__
			return a * d - b * c
		elif all(d == 2 for d in self.__dimensions__):
			pass
		else:
			determinate: float = 0

			for i, value in enumerate(self.__array__):
				if value is None:
					return None

				position: tuple[int, ...] = self.__index_to_position__(i)
				minor: Tensor = self.minor(*position)
				cofactor: int = (-1) ** i
				determinate += cofactor * value * minor.determinant()

			return determinate

	def flattened(self) -> tuple[typing.Optional[float], ...]:
		"""
		Converts the tensor to a single dimensional list of values
		:return: The flattened array
		"""

		return tuple(self.__array__)

	def to_numpy(self) -> numpy.ndarray[typing.Optional[float]]:
		"""
		:return: This tensor converted to a numpy array
		"""

		return numpy.array(self.to_nested(), dtype=float).reshape(self.__dimensions__)

	def to_nested(self) -> list[typing.Optional[float] | list]:
		"""
		:return: This tensor converted to a nested list
		"""

		def lister(iterable: typing.Iterable | typing.Optional[float]):
			return iterable if iterable is None or isinstance(iterable, float) else [lister(x) for x in iterable]

		return lister(self)

	def transposed(self) -> Tensor:
		"""
		:return: The transposed tensor
		"""

		if len(self.__dimensions__) == 2:
			y, x = self.__dimensions__
			elements: tuple[typing.Optional[float], ...] = self.flattened()
			tensor: list[tuple[typing.Optional[float], ...]] = []

			for i in range(x):
				sublist: tuple[typing.Optional[float], ...] = tuple(elements[i + j * x] for j in range(0, y))
				tensor.append(sublist)

			return Tensor(tensor)
		else:
			result: list[typing.Optional[float]] = []

			for i in range(self.__dimensions__[0] - 1, -1, -1):
				result.extend(self[i].transposed().__array__)

			return Tensor.shaped(result, *reversed(self.__dimensions__))

	def copy(self) -> Tensor:
		"""
		:return: A copy of this tensor
		"""

		return type(self).shaped(self.__array__.copy(), *self.__dimensions__)

	def transform_by(self, callback: typing.Callable[[typing.Optional[float]], typing.Optional[float]]) -> Tensor:
		"""
		Applies a function to all values in this tensor
		:param callback: A transformer callback accepting a single optional float and returning a single optional float
		:return: The transformed tensor
		:raises AssertionError: If the callback is not callable
		"""

		assert callable(callback), 'Callback is not callable'
		return type(self).shaped((float(callback(x)) for x in self.__array__), *self.__dimensions__)

	def filter_by(self, callback: typing.Callable[[typing.Optional[float]], bool]) -> Tensor:
		"""
		Applies a function to filter all values in this tensor
		Any non-matching values are replaced with 'None'
		:param callback: The filterer callback accepting a single optional float and returning a bool
		:return: The filtered tensor
		:raises AssertionError: If the callback is not callable
		"""

		assert callable(callback), 'Callback is not callable'
		return type(self).shaped((x if bool(callback(x)) else None for x in self.__array__), *self.__dimensions__)

	def subtensor(self, rows: int, columns: int, start_row: int = 0, start_column: int = 0) -> Tensor:
		"""
		Gets a sub-tensor from this tensor
		:param rows: The number of rows to index
		:param columns: The number of columns to index
		:param start_row: The row to begin indexing
		:param start_column: The column to begin indexing
		:return: The resulting sub-tensor
		"""

		rows: Tensor = self[start_row:start_row + rows]
		submtx: list = [row[start_column:start_column + columns] for row in rows]
		return Tensor(submtx)

	def minor(self, *position) -> Tensor:
		"""
		Calculates the minor tensor of the given position
		:param position: The element indices
		:return: The minor tensor
		:raises AssertionError: If the position's dimension don't match the tensor's dimension
		"""

		assert len(position) == self.dimension, 'Number of specified dimensions does not match tensor dimension'
		minor: list[typing.Optional[float]] = []

		for i, value in enumerate(self.__array__):
			index: tuple[int, ...] = self.__index_to_position__(i)

			if all(index[j] != position[j] for j in range(len(self.__dimensions__))):
				minor.append(value)

		return Tensor.shaped(minor, *[x - 1 for x in self.__dimensions__])

	def augmented(self, other: Tensor) -> Tensor:
		"""
		Augments this tensor with another tensor
		All but the minor dimensions of both tensors must match
		:param other: The other tensor
		:return: The augmented tensor
		:raises AssertionError: If the dimensions do not match
		"""

		assert len(self.__dimensions__) == len(other.__dimensions__) and self.__dimensions__[:-1] == other.__dimensions__[:-1], 'Mismatched dimensions'
		result: Tensor = Tensor(*self.__dimensions__[:-1], self.__dimensions__[-1] + other.__dimensions__[-1])

		for i in range(len(result)):
			position: tuple[int, ...] = result.__index_to_position__(i)

			if all(x < self.__dimensions__[i] for i, x in enumerate(position)):
				result.__array__[i] = self.__array__[self.__position_to_index__(position)]
			else:
				result.__array__[i] = other.__array__[self.__position_to_index__(tuple(x % other.__dimensions__[i] for i, x in enumerate(position)))]

		return result

	@property
	def dimensions(self) -> tuple[int, ...]:
		"""
		:return: The dimensions of this tensor
		"""

		return self.__dimensions__

	@property
	def dimension(self) -> int:
		"""
		:return: The number of dimensions this tensor has
		"""

		return len(tuple(x for x in self.__dimensions__ if x))

	@property
	def rank(self) -> int:
		"""
		:return: The number of dimensions this tensor has
		"""

		return self.dimension
