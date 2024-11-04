from __future__ import annotations

import math
import typing
import collections.abc

import CustomMethodsVI.Math as Math

from CustomMethodsVI.Decorators import Overload


class Vector(typing.SupportsRound['Vector'], typing.SupportsAbs['Vector'], collections.abc.Hashable):
	"""
	[Vector] - Class representing an N-dimensional immutable vector
	"""

	@classmethod
	def orthogonal(cls: type, vector_0: Vector, vector_1: Vector, *vectors: Vector) -> bool:
		"""
		Determines if all specified vectors are 90 degrees rotated from each other
		:param vector_0: (Vector) The first vector
		:param vector_1: (Vector) The next vector
		:param vectors: (*Vector) All remaining vectors
		:return: (bool) Orthogonalness
		"""

		vectors: tuple[Vector, ...] = (vector_0, vector_1, *vectors)
		assert all(type(v) is cls for v in vectors), f'Expected a variadic list of vectors; got:\n({",".join(str(type(x)) for x in vectors)})'

		for i in range(len(vectors)):
			for j in range(i + 1, len(vectors)):
				if vectors[i].dot(vectors[j]) != 0:
					return False

		return True

	@classmethod
	def orthonormal(cls: type, vector_0: Vector, vector_1: Vector, *vectors: Vector):
		"""
		Determines if all specified vectors are 90 degrees rotated from each other and all vectors are a unit vector
		:param vector_0: (Vector) The first vector
		:param vector_1: (Vector) The next vector
		:param vectors: (*Vector) All remaining vectors
		:return: (bool) Orthonormalness
		"""

		vectors: tuple[Vector, ...] = (vector_0, vector_1, *vectors)
		assert all(type(v) is cls for v in vectors), f'Expected a variadic list of vectors; got:\n({",".join(str(type(x)) for x in vectors)})'

		for i in range(len(vectors)):
			for j in range(i + 1, len(vectors)):
				if vectors[i].length() != 1 or vectors[j].length() != 1 or vectors[i].dot(vectors[j]) != 0:
					return False

		return True

	@classmethod
	def gram_schmidt(cls: type, vector_0: Vector, vector_1: Vector) -> tuple[Vector, ...]:
		"""00
		Applies Gram-Schmidt process to two vectors
		:param vector_0: (Vector) The first vector
		:param vector_1: (Vector) The second vector
		:return: (tuple[Vector]) Orthonormal basis vectors u1, u2
		"""

		assert type(vector_0) is cls
		assert type(vector_1) is cls

		w1: Vector = vector_0
		w2: Vector = vector_1 - (vector_1.dot(w1) / w1.dot(w1)) * w1
		u1: Vector = w1.normalized()
		u2: Vector = w2.normalized()
		return u1, u2

	@Overload(strict=True)
	def __init__(self, vector: Vector):
		"""
		[Vector] - Class representing an N-dimensional immutable vector
		- Constructor -
		:param vector: (Vector) Another vector
		"""

		self.__dimensions: tuple[float, ...] = tuple(vector.__dimensions)

	@Overload(strict=True)
	def __init__(self, iterable: typing.Iterable[int | float | typing.Sized]):
		"""
		Constructor
		:param iterable: (ITERABLE[int | float]) An iterable of ints or floats
		:raises ValueError: If the vector's dimension is less than 2
		"""

		components: list[float] = []

		for i, value in enumerate(iterable):
			if hasattr(value, '__float__') or isinstance(value, (int, float)):
				components.append(float(value))
			elif hasattr(value, '__int__'):
				components.append(float(int(value)))
			elif hasattr(value, '__bool__'):
				components.append(float(bool(value)))
			elif hasattr(value, '__index__'):
				components.append(float(value.__index__()))
			elif hasattr(value, '__len__'):
				components.append(float(len(value)))
			else:
				try:
					components.append(float(value))
				except Exception as _:
					raise TypeError(f'Component at {i} is not a float or int: {value} ({type(value)})') from None

		self.__dimensions: tuple[float, ...] = tuple(components)

		if len(self.__dimensions) < 2:
			raise ValueError(f'Vector dimension \'{len(self.__dimensions)}\' is less than 2')

	@Overload(strict=True)
	def __init__(self, *components: int | float):
		"""
		Constructor
		:param iterable: (ITERABLE[int | float]) An iterable of ints or floats
		:raises ValueError: If the vector's dimension is less than 2
		"""

		_components: list[float] = []

		for i, value in enumerate(components):
			if hasattr(value, '__float__') or type(value) is int or type(value) is float:
				_components.append(float(value))
			elif hasattr(value, '__int__'):
				_components.append(float(int(value)))
			elif hasattr(value, '__bool__'):
				_components.append(float(bool(value)))
			elif hasattr(value, '__index__'):
				_components.append(float(value.__index__()))
			elif hasattr(value, '__len__'):
				_components.append(float(value.__len__()))
			else:
				try:
					_components.append(float(value))
				except Exception as _:
					raise TypeError(f'Component at {i} is not a float or int: {value} ({type(value)})') from None

		self.__dimensions: tuple[float, ...] = tuple(_components)

		if len(self.__dimensions) < 2:
			raise ValueError(f'Vector dimension is \'{len(self.__dimensions)}\' is less than 2')

	def __add__(self, other: Vector | float | int) -> Vector:
		"""
		Adds either a scalar or another vector to this
		For scalars: Each element is added by this value
		For Vectors: Each element added respectively
		:param other: (Vector or float or int) The item to add
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(a + b for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float, int)):
			return Vector(x + other for x in self.__dimensions)
		else:
			return NotImplemented

	def __sub__(self, other: Vector | float | int) -> Vector:
		"""
		Subtracts either a scalar or another vector to this
		For scalars: Each element is subtracted by this value
		For Vectors: Each element subtracted respectively
		:param other: (Vector or float or int) The item to subtract
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(a - b for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float, int)):
			return Vector(x - other for x in self.__dimensions)
		else:
			return NotImplemented

	def __mul__(self, other: Vector | float | int) -> Vector:
		"""
		Multiplies either a scalar or another vector to this
		For scalars: Each element is multiplied by this value
		For Vectors: Each element multiplied respectively
		:param other: (Vector or float or int) The item to multiply
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(a * b for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float | int)):
			return Vector(x * other for x in self.__dimensions)
		else:
			return NotImplemented

	def __truediv__(self, other: Vector | float | int) -> Vector:
		"""
		Divides either a scalar or another vector to this
		For scalars: Each element is divided by this value
		For Vectors: Each element divided respectively
		:param other: (Vector or float or int) The item to divide
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(a / b for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float | int)):
			return Vector(x / other for x in self.__dimensions)
		else:
			return NotImplemented

	def __floordiv__(self, other: Vector | float | int) -> Vector:
		"""
		Floor divides either a scalar or another vector to this
		For scalars: Each element is divided by this value
		For Vectors: Each element divided respectively
		:param other: (Vector or float or int) The item to divide
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(a // b for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float | int)):
			return Vector(x // other for x in self.__dimensions)
		else:
			return NotImplemented

	def __divmod__(self, other: Vector | float | int) -> Vector:
		"""
		NOT IMPLEMENTED
		Modulo divides either a scalar or another vector to this
		For scalars: Each element is modulo divided by this value
		For Vectors: Each element modulo divided respectively
		:param other: (Vector or float or int) The item to modulo divide
		:return: (Matrix) The matrix containing the modulo and quotient or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		raise NotImplementedError('Required matrix class not implemented')

	def __mod__(self, other: Vector | float | int) -> Vector:
		"""
		Reduce mods either a scalar or another vector to this
		For scalars: Each element is modded by this value
		For Vectors: Each element modded respectively
		:param other: (Vector or float or int) The item to modulo
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(a % b for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float | int)):
			return Vector(x % other for x in self.__dimensions)
		else:
			return NotImplemented

	def __pow__(self, other: Vector | float | int, modulo: int | float = None) -> Vector:
		"""
		Exponentiates either a scalar or another vector to this
		For scalars: Each element is exponentiated by this value
		For Vectors: Each element exponentiated respectively
		:param other: (Vector or float or int) The item to exponentiate
		:return: (Vector) The new vector
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(pow(a, b, modulo) for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float | int)):
			return Vector(pow(x, other, modulo) for x in self.__dimensions)
		else:
			return NotImplemented

	def __radd__(self, other: Vector | float | int) -> Vector:
		"""
		Adds either a scalar or another vector to this
		For scalars: Each element is added to this value
		For Vectors: Each element added respectively
		:param other: (Vector or float or int) The item to add
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		return self + other

	def __rsub__(self, other: Vector | float | int) -> Vector:
		"""
		Subtracts either a scalar or another vector to this
		For scalars: Each element is subtracted from this value
		For Vectors: Each element subtracted respectively
		:param other: (Vector or float or int) The item to subtract
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(b - a for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float | int)):
			return Vector(other - x for x in self.__dimensions)
		else:
			return NotImplemented

	def __rmul__(self, other: Vector | float | int) -> Vector:
		"""
		Multiplies either a scalar or another vector to this
		For scalars: Each element is multiplied by this value
		For Vectors: Each element multiplied respectively
		:param other: (Vector or float or int) The item to multiply
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		return self * other

	def __rtruediv__(self, other: Vector | float | int) -> Vector:
		"""
		Divides either a scalar or another vector to this
		For scalars: Each element is divided from this value
		For Vectors: Each element divided respectively
		:param other: (Vector or float or int) The item to divide
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(b / a for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float | int)):
			return Vector(other / x for x in self.__dimensions)
		else:
			return NotImplemented

	def __rfloordiv__(self, other: Vector | float | int) -> Vector:
		"""
		Floor divides either a scalar or another vector to this
		For scalars: Each element is divided from this value
		For Vectors: Each element divided respectively
		:param other: (Vector or float or int) The item to divide
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(b // a for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float | int)):
			return Vector(other // x for x in self.__dimensions)
		else:
			return NotImplemented

	def __rdivmod__(self, other: Vector | float | int) -> Vector:
		"""
		NOT IMPLEMENTED
		Modulo divides either a scalar or another vector to this
		For scalars: Each element is modulo divided from this value
		For Vectors: Each element modulo divided respectively
		:param other: (Vector or float or int) The item to modulo divide
		:return: (Matrix) The matrix containing the modulo and quotient or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		raise NotImplementedError('Required matrix class not implemented')

	def __rmod__(self, other: Vector | float | int) -> Vector:
		"""
		Reduce mods either a scalar or another vector to this
		For scalars: Each element is modded from this value
		For Vectors: Each element modded respectively
		:param other: (Vector or float or int) The item to modulo
		:return: (Vector) The new vector or 'NotImplemented' if 'other' is not a Vector, float, or int
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(b / a for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float | int)):
			return Vector(other % x for x in self.__dimensions)
		else:
			return NotImplemented

	def __rpow__(self, other: Vector | float | int, modulo: int | float = None) -> Vector:
		"""
		Exponentiates either a scalar or another vector to this
		For scalars: This value is exponentiated by each element
		For Vectors: Each element exponentiated respectively
		:param other: (Vector or float or int) The item to exponentiate
		:return: (Vector) The new vector
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return Vector(pow(b, a, modulo) for a, b in zip(self.__dimensions, other.__dimensions))
		elif isinstance(other, (float | int)):
			return Vector(pow(other, x, modulo) for x in self.__dimensions)
		else:
			return NotImplemented

	def __lt__(self, other: Vector | float | int) -> bool:
		"""
		Determines if the length of this vector is less than 'other'
		For scalars: This length is less than 'other'
		For Vectors: This length is less than 'other.length()'
		:param other: (Vector or float or int) The item to compare
		:return: (bool) Comparison
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return self.length() < other.length()
		elif isinstance(other, (float | int)):
			return self.length() < other
		else:
			return NotImplemented

	def __le__(self, other: Vector | float | int) -> bool:
		"""
		Determines if the length of this vector is less than or equal to 'other'
		For scalars: This length is less than or equal to 'other'
		For Vectors: This length is less than or equal to 'other.length()'
		:param other: (Vector or float or int) The item to compare
		:return: (bool) Comparison
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return self.length() <= other.length()
		elif isinstance(other, (float | int)):
			return self.length() <= other
		else:
			return NotImplemented

	def __gt__(self, other: Vector | float | int) -> bool:
		"""
		Determines if the length of this vector is greater than 'other'
		For scalars: This length is greater than 'other'
		For Vectors: This length is greater than 'other.length()'
		:param other: (Vector or float or int) The item to compare
		:return: (bool) Comparison
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return self.length() > other.length()
		elif isinstance(other, (float | int)):
			return self.length() > other
		else:
			return NotImplemented

	def __ge__(self, other: Vector | float | int) -> bool:
		"""
		Determines if the length of this vector is greater than or equal to 'other'
		For scalars: This length is greater than or equal to 'other'
		For Vectors: This length is greater than or equal to 'other.length()'
		:param other: (Vector or float or int) The item to compare
		:return: (bool) Comparison
		:raises AssertionError: If other vector's dimensions differ from this
		"""

		if isinstance(other, type(self)):
			assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
			return self.length() >= other.length()
		elif isinstance(other, (float | int)):
			return self.length() >= other
		else:
			return NotImplemented

	def __eq__(self, other: Vector | float | int) -> bool:
		"""
		Determines if 'this' equals 'other'
		For scalars: This length is equal to 'other'
		For Vectors: The dimensions and components of these vectors are equal
		:param other: (Vector or float or int) The item to compare
		:return: (bool) Comparison
		"""

		if isinstance(other, type(self)):
			return self.dimension() == other.dimension() and self.__dimensions == other.__dimensions
		elif isinstance(other, (float | int)):
			return self.length() == other
		else:
			return False

	def __ne__(self, other: Vector | float | int) -> bool:
		"""
		Determines if 'this' is not equal to 'other'
		For scalars: This length is not equal to 'other'
		For Vectors: The dimensions and components of these vectors are not equal
		:param other: (Vector or float or int) The item to compare
		:return: (bool) Comparison
		"""

		return not (self == other)

	def __getitem__(self, item: int | slice) -> float | tuple[float, ...]:
		"""
		Gets a component or components from this vector
		:param item: (int or slice) The components to get
		:return: (float or tuple[float) The components
		"""

		return self.__dimensions[item]

	def __bool__(self) -> bool:
		"""
		Checks if this vector is a zero vector
		:return: (bool) If any component is not zero
		"""

		return all(self.__dimensions)

	def __hash__(self) -> int:
		"""
		Gets the hash-code of this vector
		:return: (int) Hashness
		"""

		return hash(self.__dimensions)

	def __abs__(self) -> Vector:
		"""
		Returns the absolute value of this vector |v|
		:return: (Vector) Vector whose components are the absolute value of this
		"""

		return Vector(abs(x) for x in self.__dimensions)

	def __neg__(self) -> Vector:
		"""
		Returns the negation of this vector -v
		:return: (Vector) Vector whose components are the negation of this
		"""

		return Vector(-x for x in self.__dimensions)

	def __pos__(self) -> Vector:
		"""
		Returns a copy of this vector +v
		:return: (Vector) Vector whose components are the same as this
		"""

		return Vector(+x for x in self.__dimensions)

	def __round__(self, n: int = None) -> Vector | int:
		"""
		Returns this vector rounded to 'n' places
		:param n: (int) The number of places to round (defaults to 1)
		:return: (Vector) Vector whose components are this rounded to 'n' places
		"""

		return Vector(round(x, n) for x in self.__dimensions)

	def __trunc__(self) -> Vector:
		"""
		Returns this vector truncated
		:return: (Vector) Vector whose components are this truncated
		"""

		return Vector(math.trunc(x) for x in self.__dimensions)

	def __floor__(self) -> Vector:
		"""
		Returns this vector floored
		:return: (Vector) Vector whose components are this floored
		"""

		return Vector(math.floor(x) for x in self.__dimensions)

	def __ceil__(self) -> Vector:
		"""
		Returns this vector ceiled
		:return: (Vector) Vector whose components are this ceiled
		"""

		return Vector(math.ceil(x) for x in self.__dimensions)

	def __repr__(self) -> str:
		return f'<{type(self).__name__} {self.dimension()}D at {hex(id(self))}>'

	def __str__(self) -> str:
		return f'〈{", ".join(str(x) for x in self.__dimensions)}〉'

	def dimension(self) -> int:
		"""
		Gets the total dimension of this vector
		:return: (int) Dimensioness
		"""

		return len(self.__dimensions)

	def length(self) -> float:
		"""
		Gets the length of this vector
		:return: (float) This vector's magnitude
		"""

		return math.sqrt(sum(pow(a, 2) for a in self.__dimensions))

	@Overload
	def dot(self, other: Vector) -> float:
		"""
		Applies inner dot-product between two vectors
		:param other: (Vector) The other vector
		:return: (float) The dot product: dot(this, other)
		:raises AssertionError: If vector dimensions are mismatched
		"""

		assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
		return sum(a * b for a, b in zip(self.__dimensions, other.__dimensions))

	@Overload
	def distance(self, other: Vector) -> float:
		"""
		Calculates distance between two vectors
		:param other: (Vector) The other vector
		:return: (float) The distance from 'this' to 'other'
		:raises AssertionError: If vector dimensions are mismatched
		"""

		assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
		return (other - self).length()

	@Overload
	def angle(self, other: Vector) -> float:
		"""
		Calculates angle between two vectors
		:param other: (Vector) The other vector
		:return: (float) The angle (in radians) between 'this' to 'other'
		:raises AssertionError: If vector dimensions are mismatched
		"""

		assert self.dimension() == other.dimension(), 'Mismatched vector dimensions'
		return math.acos(self.dot(other) / (self.length() * other.length()))

	def normalized(self) -> Vector:
		"""
		Normalizes this vector
		:return: (Vector) This vector normalized
		"""

		length: float = self.length()
		return self / length

	@Overload
	def cross(self, other: Vector) -> Vector:
		"""
		NOT IMPLEMENTED
		Calculates cross product between two vectors
		:param other: (Vector) The other vector
		:return: (float) The cross product of 'this' and 'other'
		:raises AssertionError: If 'other' is not a Vector or vector dimensions are mismatched
		"""

		raise NotImplementedError('Cross product not implemented')

	def components(self) -> tuple[float, ...]:
		"""
		Returns the individual components of this vector
		:return: (tuple[float]) Componentness
		"""

		return self.__dimensions

	def to_matrix(self) -> Math.Matrix.Matrix:
		"""
		Converts this vector to a matrix of the same shape
		:return: (Matrix) Matrixified vector
		"""

		return Math.Matrix.Matrix(self)

	@Overload
	def relative_coord_matrix(self, orthonormal_basis: typing.Iterable[Vector]) -> Math.Matrix.Matrix:
		"""
		Calculates orthonormal basis coefficients for this vector given a basis
		:param orthonormal_basis: (ITERABLE[Vector]) A basis defined by some list of vectors
		:return: (Matrix) The coefficients
		"""

		basis: tuple[Vector, ...] = tuple(orthonormal_basis)
		assert all(type(x) is type(self) for x in basis), 'Basis is not a vector set'
		return Math.Matrix.Matrix(tuple((self.dot(v) for v in basis)))

	@Overload
	def project(self, subspace: typing.Iterable[Vector]) -> Vector:
		"""
		Projects this vector onto a subspace
		:param subspace: (ITERABLE[Vector]) A subspace defined by 2 vectors
		:return: (Vector) The projected vector
		"""

		subspace: tuple[Vector, ...] = tuple(subspace)
		assert all(type(x) is type(self) for x in subspace), 'Subbspace is not a vector set'
		u1, u2 = Vector.gram_schmidt(subspace[0], subspace[1])
		return self.dot(u1) * u1 + self.dot(u2) * u2

