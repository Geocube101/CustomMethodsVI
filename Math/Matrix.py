from __future__ import annotations

import collections.abc
import math
import numpy
import os
import random
import typing
import types

import CustomMethodsVI.Math.Vector as Vector
import CustomMethodsVI.Math.Based as Based

from CustomMethodsVI.Decorators import Overload


class Matrix(typing.SupportsRound['Matrix'], typing.SupportsAbs['Matrix'], collections.abc.Hashable):
	@classmethod
	def shaped(cls, array: typing.Iterable, dimension: int, *dimensions: int) -> Matrix:
		def _validator() -> None:
			for i, x in enumerate(array[:size]):
				if isinstance(x, (float, int)):
					instance.__array__[i] = float(x)
				elif x is None or x is ...:
					instance.__array__[i] = None
				else:
					raise TypeError(f'Unexpected matrix value \'{x}\' ({type(x)}), expected either a float, int, \'...\' or None')

		instance: Matrix = cls(dimension, *dimensions)
		size: int = len(instance)
		_validator()
		return instance

	@classmethod
	def random(cls, dimension: int, *dimensions: int) -> Matrix:
		instance: Matrix = cls(dimension, *dimensions)

		for i in range(len(instance)):
			instance.__array__[i] = random.random()

		return instance

	@classmethod
	def osrandom(cls, dimension: int, *dimensions: int) -> Matrix:
		instance: Matrix = cls(dimension, *dimensions)
		random_bytes: bytes = os.urandom(len(instance))

		for i in range(len(instance)):
			instance.__array__[i] = float(random_bytes[i])

		return instance

	@classmethod
	def full(cls, value: float | int | None | types.EllipsisType, dimension: int, *dimensions: int) -> Matrix:
		if isinstance(value, (float, int)):
			value = float(value)
		elif value is None or value is ...:
			value = None
		else:
			raise TypeError(f'Unexpected matrix value \'{value}\' ({type(value)}), expected either a float, int, \'...\' or None')

		size: int = math.prod((dimension, *dimensions))
		return cls.shaped([value] * size, dimension, *dimensions)

	@classmethod
	def alternating(cls, dimension: int, *dimensions: int) -> Matrix:
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
	def __init__(self, matrix: Matrix):
		self.__size__: int = int(matrix.__size__)
		self.__dimensions__: tuple[int, ...] = tuple(matrix.__dimensions__)
		self.__array__: list[float | None] = list(matrix.__array__.copy())

	@Overload(strict=True)
	def __init__(self, matrix: numpy.ndarray):
		self.__size__: int = int(matrix.size)
		self.__dimensions__: tuple[int, ...] = tuple(matrix.shape)
		self.__array__: list[float | None] = list(matrix)

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

	def __abs__(self) -> Matrix:
		return type(self)(None if x is None else abs(x) for x in self.__array__)

	def __round__(self, n: typing.Optional[int] = None) -> Matrix | int:
		return type(self)(None if x is None else round(x, n) for x in self.__array__)

	def __getitem__(self, item: int | tuple | slice) -> float | None | Matrix | Vector.Vector:
		shaped: list = list(self)
		cls: type = type(self)

		if type(item) is tuple:
			src: Matrix | float | None = self

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
				elem: float | Matrix = self[i]

				if elem is None or elem is ... or isinstance(elem, (int, float)):
					__object.append(elem)
				else:
					__object.append(list(elem)[0])

			return Vector.Vector(__object) if self.__dimensions__[0] == 1 else cls(__object)

		elif type(item) is int:
			__object: list | int | None = shaped[0][item] if self.__dimensions__[0] == 1 else shaped[item]
			return Vector.Vector(__object) if self.__dimensions__[0] == 1 and isinstance(__object, list) else cls(__object) if isinstance(__object, list) else __object

	def __add__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((x + other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot add matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a + b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __sub__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((x - other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot subtract matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a - b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __mul__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((x * other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot multiply matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a * b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __matmul__(self, other: Matrix | numpy.ndarray[typing.Any]) -> Matrix:
		if not isinstance(other, (type(self), numpy.ndarray)):
			return NotImplemented
		elif isinstance(other, numpy.ndarray):
			other = Matrix(other)

		if self.dimension != other.dimension:
			raise ValueError(f'Cannot matrix-multiply {len(other.__dimensions__)}-dimensional matrix with {len(self.__dimensions__)}-dimensional matrix')
		elif (self.dimension == 2 and self.__dimensions__[-1] != other.__dimensions__[0]) or (self.dimension > 2 and self.__dimensions__[:-2] != other.__dimensions__[:-2]):
			raise ValueError(f'Cannot matrix-multiply matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')
		elif self.dimension == 2:
			result_dimensions: tuple[int, ...] = (*self.__dimensions__[:-1], *other.__dimensions__[1:])
			result: Matrix = Matrix(*result_dimensions)
			common: int = self.__dimensions__[-1]
			converter: Based.BaseN = Based.BaseN(common)
			indices: list[tuple[int, ...]] = [converter.convert(x).of_size(2).digits() for x in range(len(self))]

			for indexer in indices:
				index: int = sum(d * common ** (1 - p) for p, d in enumerate(indexer))
				total: float | None = 0

				for k in range(common):
					indexer_a: tuple[int, ...] = (*indexer[:-1], k)
					indexer_b: tuple[int, ...] = (k, *indexer[1:])
					element_a: float | None = self[indexer_a]
					element_b: float | None = other[indexer_b]

					if element_a is None or element_b is None:
						total = None
						break

					total += element_a * element_b

				result.__array__[index] = total

			return result
		else:
			inner: tuple[int, ...] = (self.__dimensions__[-2], other.__dimensions__[-1])
			result_dimensions: tuple[int, ...] = (*self.__dimensions__[:-2], *inner)
			result: Matrix = Matrix(*result_dimensions)
			index: int = 0

			for i in range(self.__dimensions__[0]):
				a: Matrix = self[i]
				b: Matrix = other[i]
				c: Matrix = a @ b

				for j, value in enumerate(c.__array__):
					result.__array__[index + j] = value

				index += len(c.__array__)

			return result

	def __truediv__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((x / other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a / b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __floordiv__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((x // other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a // b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __mod__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((x % other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a % b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __divmod__(self, other: float | int | Matrix) -> Matrix:
		raise NotImplementedError('DIVMOD not implemented')

	def __pow__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((x ** other for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot exponentiate matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((a ** b for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __radd__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((other + x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot add matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b + a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rsub__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((other - x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot subtract matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b - a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rmul__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((other * x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot multiply matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b * a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rmatmul__(self, other: Matrix | numpy.ndarray[typing.Any]) -> Matrix:
		if not isinstance(other, (type(self), numpy.ndarray)):
			return NotImplemented
		elif isinstance(other, numpy.ndarray):
			other = Matrix(other)

		if self.dimension != other.dimension:
			raise ValueError(f'Cannot matrix-multiply {len(other.__dimensions__)}-dimensional matrix with {len(self.__dimensions__)}-dimensional matrix')
		elif (self.dimension == 2 and self.__dimensions__[-1] != other.__dimensions__[0]) or (self.dimension > 2 and self.__dimensions__[:-2] != other.__dimensions__[:-2]):
			raise ValueError(f'Cannot matrix-multiply matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')
		elif self.dimension == 2:
			result_dimensions: tuple[int, ...] = (*other.__dimensions__[:-1], *self.__dimensions__[1:])
			result: Matrix = Matrix(*result_dimensions)
			common: int = other.__dimensions__[-1]
			converter: Based.BaseN = Based.BaseN(common)
			indices: list[tuple[int, ...]] = [converter.convert(x).of_size(2).digits() for x in range(len(self))]

			for indexer in indices:
				index: int = sum(d * common ** (1 - p) for p, d in enumerate(indexer))
				total: float | None = 0

				for k in range(common):
					indexer_a: tuple[int, ...] = (*indexer[:-1], k)
					indexer_b: tuple[int, ...] = (k, *indexer[1:])
					element_a: float | None = other[indexer_a]
					element_b: float | None = self[indexer_b]

					if element_a is None or element_b is None:
						total = None
						break

					total += element_a * element_b

				result.__array__[index] = total

			return result
		else:
			inner: tuple[int, ...] = (other.__dimensions__[-2], self.__dimensions__[-1])
			result_dimensions: tuple[int, ...] = (*other.__dimensions__[:-2], *inner)
			result: Matrix = Matrix(*result_dimensions)
			index: int = 0

			for i in range(other.__dimensions__[0]):
				a: Matrix = other[i]
				b: Matrix = self[i]
				c: Matrix = a @ b

				for j, value in enumerate(c.__array__):
					result.__array__[index + j] = value

				index += len(c.__array__)

			return result

	def __rtruediv__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((other / x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b / a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rfloordiv__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((other // x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b // a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rmod__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((other % x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot divide matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b % a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __rdivmod__(self, other: float | int | Matrix) -> Matrix:
		raise NotImplementedError('DIVMOD not implemented')

	def __rpow__(self, other: float | int | Matrix) -> Matrix:
		if isinstance(other, (float, int)):
			return type(self).shaped((other ** x for x in self.__array__), *self.__dimensions__)
		elif isinstance(other, type(self)):
			if self.__dimensions__ != other.__dimensions__:
				raise ValueError(f'Cannot exponentiate matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')

			return type(self).shaped((b ** a for a, b in zip(self.__array__, other.__array__)), *self.__dimensions__)
		else:
			return NotImplemented

	def __iadd__(self, other: float | int | Matrix) -> Matrix:
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

	def __isub__(self, other: float | int | Matrix) -> Matrix:
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

	def __imul__(self, other: float | int | Matrix) -> Matrix:
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

	def __imatmul__(self, other: Matrix | numpy.ndarray[typing.Any]) -> Matrix:
		if not isinstance(other, (type(self), numpy.ndarray)):
			return NotImplemented
		elif isinstance(other, numpy.ndarray):
			other = Matrix(other)

		if self.dimension != other.dimension:
			raise ValueError(f'Cannot matrix-multiply {len(other.__dimensions__)}-dimensional matrix with {len(self.__dimensions__)}-dimensional matrix')
		elif (self.dimension == 2 and self.__dimensions__[-1] != other.__dimensions__[0]) or (self.dimension > 2 and self.__dimensions__[:-2] != other.__dimensions__[:-2]):
			raise ValueError(f'Cannot matrix-multiply matrix of dimension {"x".join(str(x) for x in other.__dimensions__)} to matrix of dimension {"x".join(str(x) for x in self.__dimensions__)}')
		elif self.dimension == 2:
			result_dimensions: tuple[int, ...] = (*self.__dimensions__[:-1], *other.__dimensions__[1:])
			result: Matrix = Matrix(*result_dimensions)
			common: int = self.__dimensions__[-1]
			converter: Based.BaseN = Based.BaseN(common)
			indices: list[tuple[int, ...]] = [converter.convert(x).of_size(2).digits() for x in range(len(self))]

			for indexer in indices:
				index: int = sum(d * common ** (1 - p) for p, d in enumerate(indexer))
				total: float | None = 0

				for k in range(common):
					indexer_a: tuple[int, ...] = (*indexer[:-1], k)
					indexer_b: tuple[int, ...] = (k, *indexer[1:])
					element_a: float | None = self[indexer_a]
					element_b: float | None = other[indexer_b]

					if element_a is None or element_b is None:
						total = None
						break

					total += element_a * element_b

				result.__array__[index] = total

			self.__size__ = result.__size__
			self.__dimensions__ = result.__dimensions__
			self.__array__ = result.__array__
			return self
		else:
			inner: tuple[int, ...] = (self.__dimensions__[-2], other.__dimensions__[-1])
			result_dimensions: tuple[int, ...] = (*self.__dimensions__[:-2], *inner)
			result: Matrix = Matrix(*result_dimensions)
			index: int = 0

			for i in range(self.__dimensions__[0]):
				a: Matrix = self[i]
				b: Matrix = other[i]
				c: Matrix = a @ b

				for j, value in enumerate(c.__array__):
					result.__array__[index + j] = value

				index += len(c.__array__)

			self.__size__ = result.__size__
			self.__dimensions__ = result.__dimensions__
			self.__array__ = result.__array__
			return self

	def __itruediv__(self, other: float | int | Matrix) -> Matrix:
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

	def __ifloordiv__(self, other: float | int | Matrix) -> Matrix:
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

	def __imod__(self, other: float | int | Matrix) -> Matrix:
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

	def __ipow__(self, other: float | int | Matrix) -> Matrix:
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

	def __neg__(self) -> Matrix:
		return type(self).shaped((-x for x in self.__array__), *self.__dimensions__)

	def __pos__(self) -> Matrix:
		return type(self).shaped((+x for x in self.__array__), *self.__dimensions__)

	def flattened(self) -> tuple[float | None, ...]:
		return tuple(self.__array__)

	def to_numpy(self) -> numpy.ndarray:
		return numpy.array(list(self), dtype=float)

	def transposed(self) -> Matrix:
		if len(self.__dimensions__) == 2:
			y, x = self.__dimensions__
			elements: tuple[float | None, ...] = self.flattened()
			matrix: list[tuple[float | None, ...]] = []

			for i in range(x):
				sublist: tuple[float | None, ...] = tuple(elements[i + j * x] for j in range(0, y))
				matrix.append(sublist)

			return Matrix(matrix)
		else:
			result: list[float | None] = []

			for i in range(self.__dimensions__[0] - 1, -1, -1):
				result.extend(self[i].transposed().__array__)

			return Matrix.shaped(result, *reversed(self.__dimensions__))

	def copy(self) -> Matrix:
		return type(self).shaped(self.__array__.copy(), *self.__dimensions__)

	def transform_by(self, callback: typing.Callable[[float], float]) -> Matrix:
		assert callable(callback), 'Callback is not callable'
		return type(self).shaped((float(callback(x)) for x in self.__array__), *self.__dimensions__)

	def filter_by(self, callback: typing.Callable[[float], bool]) -> Matrix:
		assert callable(callback), 'Callback is not callable'
		return type(self).shaped((x if bool(callback(x)) else None for x in self.__array__), *self.__dimensions__)

	def row_echelon(self) -> Matrix:
		pass

	def submatrix(self, rows: int, columns: int, start_row: int = 0, start_column: int = 0):
		"""
		Gets a sub-matrix from this matrix
		:param rows: (int) The number of rows to index
		:param columns: (int) The number of columns to index
		:param start_row: (int) The row to begin indexing
		:param start_column: (int) The column to begin indexing
		:return: (Matrix) The resulting sub-matrix
		"""

		rows: Matrix = self[start_row:start_row + rows]
		submtx: list = [row[start_column:start_column + columns] for row in rows]
		return Matrix(submtx)

	@property
	def dimensions(self) -> tuple[int, ...]:
		return self.__dimensions__

	@property
	def dimension(self) -> int:
		return len(tuple(x for x in self.__dimensions__ if x))
