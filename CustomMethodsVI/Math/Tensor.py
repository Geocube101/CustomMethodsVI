from __future__ import annotations

import collections.abc
import math
import numpy
import os
import random
import typing
import types

from ..Math import Vector
from ..Decorators import Overload


class Tensor(typing.SupportsRound['Matrix'], typing.SupportsAbs['Matrix'], collections.abc.Hashable):
	@classmethod
	def shaped(cls, array: typing.Iterable, dimension: int, *dimensions: int) -> Tensor:
		instance: Tensor = cls(dimension, *dimensions)
		size: int = len(instance)

		for i, x in enumerate(tuple(array)[:size]):
			if isinstance(x, (float, int)):
				instance.__array__[i] = float(x)
			elif x is None or x is ...:
				instance.__array__[i] = None
			else:
				raise TypeError(f'Unexpected matrix value \'{x}\' ({type(x)}), expected either a float, int, \'...\' or None')

		return instance

	@classmethod
	def random(cls, dimension: int, *dimensions: int) -> Tensor:
		instance: Tensor = cls(dimension, *dimensions)

		for i in range(len(instance)):
			instance.__array__[i] = random.random()

		return instance

	@classmethod
	def osrandom(cls, dimension: int, *dimensions: int) -> Tensor:
		instance: Tensor = cls(dimension, *dimensions)
		random_bytes: bytes = os.urandom(len(instance))

		for i in range(len(instance)):
			instance.__array__[i] = float(random_bytes[i])

		return instance

	@classmethod
	def full(cls, value: float | int | None | types.EllipsisType, dimension: int, *dimensions: int) -> Tensor:
		if isinstance(value, (float, int)):
			value = float(value)
		elif value is None or value is ...:
			value = None
		else:
			raise TypeError(f'Unexpected matrix value \'{value}\' ({type(value)}), expected either a float, int, \'...\' or None')

		size: int = math.prod((dimension, *dimensions))
		return cls.shaped([value] * size, dimension, *dimensions)

	@classmethod
	def alternating(cls, dimension: int, *dimensions: int) -> Tensor:
		return cls.shaped((1 if i % 2 == 0 else -1 for i in range(math.prod((dimension, *dimensions)))), dimension, *dimensions)

	@Overload(strict=True)
	def __init__(self, dimension: int, *dimensions: int):
		dimensions: tuple[int, ...] = (dimension, *dimensions)
		self.__size__: int = math.prod(dimensions)
		self.__dimensions__: tuple[int, ...] = (1, *dimensions) if len(dimensions) < 2 else tuple(dimensions)
		self.__array__: list[float | None] = [None] * self.__size__

	@Overload(strict=True)
	def __init__(self, matrix: typing.Iterable):
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
				raise TypeError(f'Unexpected matrix value \'{__input}\' ({type(__input)}), expected either a float, int, \'...\' or None')

		dimensions: dict[int, int] = {}
		flattened: list[float | None] = []
		_flattener(flattened, 0, matrix, dimensions)
		dimensions: tuple[int, ...] = tuple(dimensions[x] for x in sorted(dimensions.keys()))
		self.__size__: int = len(flattened)
		self.__dimensions__: tuple[int, ...] = (1, *dimensions) if len(dimensions) < 2 else tuple(dimensions)
		self.__array__: list[float | None] = flattened

	@Overload(strict=True)
	def __init__(self, matrix: Tensor):
		self.__size__: int = int(matrix.__size__)
		self.__dimensions__: tuple[int, ...] = tuple(matrix.__dimensions__)
		self.__array__: list[float | None] = list(matrix.__array__.copy())

	@Overload(strict=True)
	def __init__(self, matrix: numpy.ndarray):
		self.__size__: int = int(matrix.size)
		self.__dimensions__: tuple[int, ...] = tuple(matrix.shape)
		self.__array__: list[float | None] = list(matrix)

	def __index_to_position__(self, index: int) -> tuple[int, ...]:
		position: list[int] = [index]

		for i in range(1, len(self.__dimensions__)):
			d: int = position[-1] // self.__dimensions__[i]
			m: int = position[-1] % self.__dimensions__[i]
			position[-1] = d
			position.append(m)

		return tuple(position)

	def __hash__(self) -> int:
		return hash(tuple(self.__array__))

	def __len__(self) -> int:
		return self.__size__

	def __iter__(self) -> typing.Iterator[float | None]:
		index: int = 0
		result: list = self.__array__
		buffer: list = []

		for dimension in reversed(self.__dimensions__):
			end: int = len(result) // dimension * dimension

			while index < end:
				buffer.append(result[index:index + dimension])
				index += dimension

			index = 0
			result = buffer.copy()
			buffer.clear()

		return iter(result[0])

	def __repr__(self) -> str:
		return f'<{type(self).__name__} {"x".join(str(x) for x in self.__dimensions__)} @ {hex(id(self))}>'

	def __str__(self) -> str:
		__list: list = list(self)
		return str(__list[0] if self.__dimensions__[0] == 1 else __list)

	def __abs__(self) -> Tensor:
		return type(self)(None if x is None else abs(x) for x in self.__array__)

	def __round__(self, n: typing.Optional[int] = None) -> Tensor | int:
		return type(self)(None if x is None else round(x, n) for x in self.__array__)

	def __getitem__(self, item: int | tuple | slice) -> float | None | Tensor | Vector.Vector:
		shaped: list = list(self)
		cls: type = type(self)

		if type(item) is tuple:
			src: Tensor | float | None = self

			for index in item:
				src = src[index]

			return src

		elif type(item) is slice:
			length: int = self.__dimensions__[1] if self.__dimensions__[0] == 1 else self.__dimensions__[0]
			start: int = 0 if item.start is None else int(item.start)
			stop: int = length if item.stop is None else int(item.stop)
			step: int = 1 if item.step is None else int(item.step)

			start = length + start if start < 0 else start
			stop = length + stop if stop < 0 else stop

			__object: list = []

			for i in range(start, stop, step):
				elem: float | Tensor = self[i]

				if elem is None or elem is ... or isinstance(elem, (int, float)):
					__object.append(elem)
				else:
					__object.append(list(elem)[0])

			return Vector.Vector(__object) if self.__dimensions__[0] == 1 else cls(__object)

		elif type(item) is int:
			__object: list | int | None = shaped[0][item] if self.__dimensions__[0] == 1 else shaped[item]
			return Vector.Vector(__object) if self.__dimensions__[0] == 1 and isinstance(__object, list) else cls(__object) if isinstance(__object, list) else __object

	def __add__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((x + other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot add matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a + b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __sub__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((x - other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot subtract matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a - b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __mul__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((x * other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot multiply matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a * b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __matmul__(self, other: Tensor | numpy.ndarray[typing.Any]) -> Tensor:
		if not isinstance(other, (type(self), numpy.ndarray)):
			return NotImplemented
		elif isinstance(other, numpy.ndarray):
			other = Tensor(other)

		if self.dimension != other.dimension:
			raise ValueError(f'Cannot matrix-multiply {len(other.__dimensions__)}-dimensional matrix with {len(self.__dimensions__)}-dimensional matrix')
		elif (self.dimension == 2 and self.__dimensions__[-1] != other.__dimensions__[0]) or (self.dimension > 2 and self.__dimensions__[:-2] != other.__dimensions__[:-2]):
			raise ValueError(f'Cannot matrix-multiply matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')
		else:
			tensor_a: numpy.ndarray[float | None] = self.to_numpy()
			tensor_b: numpy.ndarray[float | None] = other.to_numpy()
			return Tensor(tuple(numpy.tensordot(tensor_a, tensor_b, 1)))

	def __truediv__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((x / other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a / b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __floordiv__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((x // other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a // b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __mod__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((x % other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a % b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __divmod__(self, other: float | int | Tensor) -> Tensor:
		raise NotImplementedError('DIVMOD not implemented')

	def __pow__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((x ** other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot exponentiate matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a ** b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __radd__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((other + x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot add matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b + a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rsub__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((other - x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot subtract matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b - a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rmul__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((other * x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot multiply matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b * a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rmatmul__(self, other: Tensor | numpy.ndarray[typing.Any]) -> Tensor:
		if not isinstance(other, (type(self), numpy.ndarray)):
			return NotImplemented
		elif isinstance(other, numpy.ndarray):
			other = Tensor(other)

		if self.dimension != other.dimension:
			raise ValueError(f'Cannot matrix-multiply {len(other.__dimensions__)}-dimensional matrix with {len(self.__dimensions__)}-dimensional matrix')
		elif (self.dimension == 2 and self.__dimensions__[-1] != other.__dimensions__[0]) or (self.dimension > 2 and self.__dimensions__[:-2] != other.__dimensions__[:-2]):
			raise ValueError(f'Cannot matrix-multiply matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')
		else:
			tensor_a: numpy.ndarray[float | None] = other.to_numpy()
			tensor_b: numpy.ndarray[float | None] = self.to_numpy()
			return Tensor(tuple(numpy.tensordot(tensor_a, tensor_b, 1)))

	def __rtruediv__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((other / x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b / a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rfloordiv__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((other // x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b // a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rmod__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((other % x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b % a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rdivmod__(self, other: float | int | Tensor) -> Tensor:
		raise NotImplementedError('DIVMOD not implemented')

	def __rpow__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			return type(self).shaped((other ** x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot exponentiate matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b ** a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __iadd__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			for i in range(self.__size__):
				self.__array__[i] += other
			return self
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot add matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] += other.__array__[i]
			return self
		else:
			return NotImplemented

	def __isub__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			for i in range(self.__size__):
				self.__array__[i] -= other
			return self
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot subtract matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] -= other.__array__[i]
			return self
		else:
			return NotImplemented

	def __imul__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			for i in range(self.__size__):
				self.__array__[i] *= other
			return self
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot multiply matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] *= other.__array__[i]
			return self
		else:
			return NotImplemented

	def __imatmul__(self, other: Tensor | numpy.ndarray[typing.Any]) -> Tensor:
		if not isinstance(other, (type(self), numpy.ndarray)):
			return NotImplemented
		elif isinstance(other, numpy.ndarray):
			other = Tensor(other)

		if self.dimension != other.dimension:
			raise ValueError(f'Cannot matrix-multiply {len(other.__dimensions__)}-dimensional matrix with {len(self.__dimensions__)}-dimensional matrix')
		elif (self.dimension == 2 and self.__dimensions__[-1] != other.__dimensions__[0]) or (self.dimension > 2 and self.__dimensions__[:-2] != other.__dimensions__[:-2]):
			raise ValueError(f'Cannot matrix-multiply matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')
		else:
			tensor_a: numpy.ndarray[float | None] = self.to_numpy()
			tensor_b: numpy.ndarray[float | None] = other.to_numpy()
			self.__array__ = numpy.tensordot(tensor_a, tensor_b, 1).flatten()
			return self

	def __itruediv__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			for i in range(self.__size__):
				self.__array__[i] /= other
			return self
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] /= other.__array__[i]
			return self
		else:
			return NotImplemented

	def __ifloordiv__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			for i in range(self.__size__):
				self.__array__[i] //= other
			return self
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] //= other.__array__[i]
			return self
		else:
			return NotImplemented

	def __imod__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			for i in range(self.__size__):
				self.__array__[i] %= other
			return self
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] %= other.__array__[i]
			return self
		else:
			return NotImplemented

	def __ipow__(self, other: float | int | Tensor) -> Tensor:
		if isinstance(other, (float, int)):
			for i in range(self.__size__):
				self.__array__[i] **= other
			return self
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot exponentiate matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			for i in range(self.__size__):
				self.__array__[i] **= other.__array__[i]
			return self
		else:
			return NotImplemented

	def __neg__(self) -> Tensor:
		return type(self).shaped((-x for x in self.__array__), *self.__dimensions__)

	def __pos__(self) -> Tensor:
		return type(self).shaped((+x for x in self.__array__), *self.__dimensions__)

	def is_square(self) -> bool:
		"""
		Checks if this matrix is square
		:return: (bool) True if all dimensions are equal
		"""

		return len(self.__dimensions__) > 1 and all(d == self.__dimensions__[0] for d in self.__dimensions__[1:])

	def is_eigenvector(self, vector: Vector.Vector) -> bool:
		assert isinstance(vector, Vector.Vector), 'Not a vector'
		assert self.dimension == 2, 'Self is not a rank-2 tensor'
		assert vector.dimension == self.__dimensions__[0], 'Vector dimension misaligned'

		result: Vector.Vector = Vector.Vector((self @ Tensor.shaped(vector.components(), vector.dimension, 1)).__array__)
		ratio: tuple[float, ...] = (result / vector).components()
		initial: float = ratio[0]
		print(self @ Tensor.shaped(vector.components(), vector.dimension, 1), result, vector)
		return all(rat == initial for rat in ratio)

	def determinant(self) -> float | None:
		"""
		Calculates the determinate if this matrix is square
		:return: (float | None) The determinate or None if any single value is None
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

	def flattened(self) -> tuple[float | None, ...]:
		"""
		Converts the matrix to a single dimensional list of values
		:return: (tuple[float | None) The flattened array
		"""

		return tuple(self.__array__)

	def to_numpy(self) -> numpy.ndarray[float | None]:
		"""
		Converts this matrix to a numpy array
		:return: (numpy.array) The numpy array
		"""

		return numpy.array(list(self), dtype=float).reshape(self.__dimensions__)

	def transposed(self) -> Tensor:
		"""
		Transposes this matrix
		:return: (Matrix) The transposed matrix
		"""

		if len(self.__dimensions__) == 2:
			y, x = self.__dimensions__
			elements: tuple[float | None, ...] = self.flattened()
			matrix: list[tuple[float | None, ...]] = []

			for i in range(x):
				sublist: tuple[float | None, ...] = tuple(elements[i + j * x] for j in range(0, y))
				matrix.append(sublist)

			return Tensor(matrix)
		else:
			result: list[float | None] = []

			for i in range(self.__dimensions__[0] - 1, -1, -1):
				result.extend(self[i].transposed().__array__)

			return Tensor.shaped(result, *reversed(self.__dimensions__))

	def copy(self) -> Tensor:
		"""
		Copies this matrix
		:return: (Matrix) A copy
		"""

		return type(self).shaped(self.__array__.copy(), *self.__dimensions__)

	def transform_by(self, callback: typing.Callable[[float | None], float | None]) -> Tensor:
		"""
		Applies a function to all values in this matrix
		:param callback: ((float | None) -> float | None) The transformer callback
		:return: (Matrix) The transformed matrix
		"""

		assert callable(callback), 'Callback is not callable'
		return type(self).shaped((float(callback(x)) for x in self.__array__), *self.__dimensions__)

	def filter_by(self, callback: typing.Callable[[float | None], bool]) -> Tensor:
		"""
		Applies a function to filter all values in this matrix
		Any non-matching values are replaced with 'None'
		:param callback: ((float | None) -> bool) The filterer callback
		:return: (Matrix) The filtered matrix
		"""

		assert callable(callback), 'Callback is not callable'
		return type(self).shaped((x if bool(callback(x)) else None for x in self.__array__), *self.__dimensions__)

	def row_echelon(self) -> Tensor:
		pass

	def reduced_row_echelon(self) -> Tensor:
		pass

	def submatrix(self, rows: int, columns: int, start_row: int = 0, start_column: int = 0) -> Tensor:
		"""
		Gets a sub-matrix from this matrix
		:param rows: (int) The number of rows to index
		:param columns: (int) The number of columns to index
		:param start_row: (int) The row to begin indexing
		:param start_column: (int) The column to begin indexing
		:return: (Matrix) The resulting sub-matrix
		"""

		rows: Tensor = self[start_row:start_row + rows]
		submtx: list = [row[start_column:start_column + columns] for row in rows]
		return Tensor(submtx)

	def adjugate(self) -> Tensor:
		pass

	def minor(self, *position) -> Tensor:
		"""
		Calculates the minor matrix of the given position
		:param position: (*int) The element indices
		:return: (Matrix) The minor matrix
		"""

		assert len(position) == self.dimension, 'Number of specified dimensions does not match matrix dimension'
		minor: list[float | None] = []

		for i, value in enumerate(self.__array__):
			index: tuple[int, ...] = self.__index_to_position__(i)

			if all(index[j] != position[j] for j in range(len(self.__dimensions__))):
				minor.append(value)

		return Tensor.shaped(minor, *[x - 1 for x in self.__dimensions__])

	def augmented(self, other: Tensor) -> Tensor:
		assert self.__dimensions__[:-1] == other.__dimensions__[:-1], 'Mismatched dimensions'
		dimensions: tuple[int, ...] = (*self.__dimensions__[:-1], self.__dimensions__[-1] + other.__dimensions__[-1])
		return Tensor.shaped(self.__array__ + other.__array__, *dimensions)

	@property
	def dimensions(self) -> tuple[int, ...]:
		"""
		:return: (tuple[int, ...]) The dimensions of this matrix
		"""

		return self.__dimensions__

	@property
	def dimension(self) -> int:
		"""
		:return: (int) The number of dimensions this matrix has
		"""

		return len(tuple(x for x in self.__dimensions__ if x))
