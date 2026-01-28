from __future__ import annotations

import collections.abc
import math
import typing

from .. import Exceptions
from .. import Math
from .. import Misc
from .. import Stream


class Vector(typing.SupportsRound['Vector'], typing.SupportsAbs['Vector'], collections.abc.Hashable, typing.Iterable[float]):
	"""
	Class representing an N-dimensional immutable vector
	"""

	@classmethod
	def orthogonal(cls: type[Vector], vector_0: Vector, vector_1: Vector, *vectors: Vector) -> bool:
		"""
		Determines if all specified vectors are 90 degrees rotated from each other
		:param vector_0: The first vector
		:param vector_1: The next vector
		:param vectors: All remaining vectors
		:return: Whether all vectors are orthogonal
		:raises AssertionError: If any vector is not a Vector instance
		"""

		vectors: tuple[Vector, ...] = (vector_0, vector_1, *vectors)
		assert all(isinstance(v, cls) for v in vectors), f'Expected a variadic list of vectors; got:\n({",".join(str(type(x)) for x in vectors)})'

		if any(not v.complete for v in vectors):
			return False

		for i in range(len(vectors)):
			for j in range(i + 1, len(vectors)):
				if vectors[i].dot(vectors[j]) != 0:
					return False

		return True

	@classmethod
	def orthonormal(cls: type[Vector], vector_0: Vector, vector_1: Vector, *vectors: Vector):
		"""
		Determines if all specified vectors are 90 degrees rotated from each other and all vectors are a unit vector
		:param vector_0: The first vector
		:param vector_1: The next vector
		:param vectors: All remaining vectors
		:return: Whether all vectors are orthonormal
		:raises AssertionError: If any vector is not a Vector instance
		"""

		vectors: tuple[Vector, ...] = (vector_0, vector_1, *vectors)
		assert all(isinstance(v, cls) for v in vectors), f'Expected a variadic list of vectors; got:\n({",".join(str(type(x)) for x in vectors)})'

		if any(not v.complete for v in vectors):
			return False

		for i in range(len(vectors)):
			for j in range(i + 1, len(vectors)):
				if vectors[i].length() != 1 or vectors[j].length() != 1 or vectors[i].dot(vectors[j]) != 0:
					return False

		return True

	@classmethod
	def gram_schmidt(cls: type[Vector], vector_0: Vector, vector_1: Vector, *, normalized: bool = True) -> tuple[Vector, ...]:
		"""
		Applies Gram-Schmidt process to two vectors
		:param vector_0: The first vector
		:param vector_1: The second vector
		:param normalized: Whether to normalize the resulting vectors
		:return: Orthonormal basis vectors u1, u2
		:raises AssertionError: If any vector is not a Vector instance
		"""

		assert isinstance(vector_0, cls), 'First vector is not a vector'
		assert isinstance(vector_1, cls), 'Second vector is not a vector'

		w1: Vector = vector_0
		w2: Vector = vector_1 - (vector_1.dot(w1) / w1.dot(w1)) * w1

		if not normalized:
			return w1, w2

		u1: Vector = w1.normalized()
		u2: Vector = w2.normalized()
		return u1, u2

	def __init__(self, component: typing.Optional[float] | typing.Iterable[typing.Optional[float]] | Vector, *components: typing.Optional[float]):
		"""
		Class representing an N-dimensional immutable vector
		- Constructor -
		:param components: A list of vector components
		:raises ValueError: If the vector's dimension is less than 1
		:raises TypeError: If any value is not a float or integer
		"""

		components: tuple[typing.Optional[float], ...]

		if isinstance(component, Vector):
			assert len(components) == 0, 'Expected either an iterable of floats, vector or a variadic list of floats'
			components = component.components
		elif isinstance(component, typing.Iterable):
			assert len(components) == 0, 'Expected either an iterable of floats, vector or a variadic list of floats'
			components = tuple(component)
		else:
			components = (component, *components)

		if len(components) < 1:
			raise ValueError(f'Vector dimension is \'{len(components)}\' is less than 1')

		self.__components__: tuple[typing.Optional[float], ...] = Stream.LinqStream(components).assert_if(lambda value: value is not None and not isinstance(value, (int, float)), TypeError(f'One or more components is not a float')).collect(tuple)

	def __iter__(self) -> typing.Iterator[typing.Optional[float]]:
		return iter(self.__components__)

	def __add__(self, other: Vector | float) -> Vector:
		"""
		Adds this vector with another vector or number
		:param other: The single number or vector to add
		:return: The added vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else (a + b) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else (x + float(other)) for x in self.__components__)
		else:
			return NotImplemented

	def __sub__(self, other: Vector | float) -> Vector:
		"""
		Subtracts this vector by another vector or number
		:param other: The single number or vector to subtract
		:return: The subtracted vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else (a - b) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else (x - float(other)) for x in self.__components__)
		else:
			return NotImplemented

	def __mul__(self, other: Vector | float) -> Vector:
		"""
		Multiplies this vector with another vector or number
		:param other: The single number or vector to multiply
		:return: The multiplied vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else (a * b) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else (x * float(other)) for x in self.__components__)
		else:
			return NotImplemented

	def __truediv__(self, other: Vector | float) -> Vector:
		"""
		Divides this vector by another vector or number
		:param other: The single number or vector to divide
		:return: The divided vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else Math.Functions.safe_divide(a, b) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else Math.Functions.safe_divide(x, float(other)) for x in self.__components__)
		else:
			return NotImplemented

	def __floordiv__(self, other: Vector | float) -> Vector:
		"""
		Floor-divides this vector by another vector or number
		:param other: The single number or vector to floor-divide
		:return: The floor-divided vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else Math.Functions.safe_floor_divide(a, b) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else Math.Functions.safe_floor_divide(x, float(other)) for x in self.__components__)
		else:
			return NotImplemented

	def __divmod__(self, other: Vector | float) -> Math.Tensor.Tensor:
		"""
		Div-mods this vector by another vector or number
		:param other: The single number or vector to div-mod
		:return: A rank-2 tensor containing the quotient (column 1) and remainder (column 2)
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			result: list[tuple[float, float]] = [None if a is None or b is None else Math.Functions.safe_divmod(a, b) for a, b in zip(self.__components__, other.__components__)]
			return Math.Tensor.Tensor(result)
		elif isinstance(other, (float, int)):
			result: list[tuple[float, float]] = [None if a is None else Math.Functions.safe_divmod(a, float(other)) for a in self.__components__]
			return Math.Tensor.Tensor(result)
		else:
			return NotImplemented

	def __mod__(self, other: Vector | float) -> Vector:
		"""
		Modulos this vector by another vector or number
		:param other: The single number or vector to modulo
		:return: The moduloed vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else Math.Functions.safe_modulo(a, b) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else Math.Functions.safe_modulo(x, float(other)) for x in self.__components__)
		else:
			return NotImplemented

	def __pow__(self, other: Vector | float, modulo: int | float = None) -> Vector:
		"""
		Raises this vector by another vector or number
		:param other: The single number or vector to raise by
		:return: The raised vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else pow(a, b, modulo) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else pow(x, float(other), modulo) for x in self.__components__)
		else:
			return NotImplemented

	def __radd__(self, other: Vector | float) -> Vector:
		"""
		Adds this vector to another vector or number
		:param other: The single number or vector to add
		:return: The added vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else (b + a) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else (float(other) + x) for x in self.__components__)
		else:
			return NotImplemented

	def __rsub__(self, other: Vector | float) -> Vector:
		"""
		Subtracts this vector from another vector or number
		:param other: The single number or vector to subtract
		:return: The subtracted vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else (b - a) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else (float(other) - x) for x in self.__components__)
		else:
			return NotImplemented

	def __rmul__(self, other: Vector | float) -> Vector:
		"""
		Multiplies this vector to another vector or number
		:param other: The single number or vector to multiply
		:return: The multiplied vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else (b * a) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else (float(other) * x) for x in self.__components__)
		else:
			return NotImplemented

	def __rtruediv__(self, other: Vector | float) -> Vector:
		"""
		Divides this vector from another vector or number
		:param other: The single number or vector to divide
		:return: The divided vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else Math.Functions.safe_divide(b, a) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else Math.Functions.safe_divide(float(other), x) for x in self.__components__)
		else:
			return NotImplemented

	def __rfloordiv__(self, other: Vector | float) -> Vector:
		"""
		Floor-divides this vector from another vector or number
		:param other: The single number or vector to floor-divide
		:return: The floor-divided vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else Math.Functions.safe_floor_divide(b, a) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else Math.Functions.safe_floor_divide(float(other), x) for x in self.__components__)
		else:
			return NotImplemented

	def __rdivmod__(self, other: Vector | float) -> Math.Tensor.Tensor:
		"""
		Div-mods this vector by another vector or number
		:param other: The single number or vector to div-mod
		:return: A rank-2 tensor containing the quotient (column 1) and remainder (column 2)
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			result: list[tuple[float, float]] = [None if a is None or b is None else Math.Functions.safe_divmod(b, a) for a, b in zip(self.__components__, other.__components__)]
			return Math.Tensor.Tensor(result)
		elif isinstance(other, (float, int)):
			result: list[tuple[float, float]] = [None if a is None else Math.Functions.safe_divmod(float(other), a) for a in self.__components__]
			return Math.Tensor.Tensor(result)
		else:
			return NotImplemented

	def __rmod__(self, other: Vector | float) -> Vector:
		"""
		Modulos this vector from another vector or number
		:param other: The single number or vector to modulo
		:return: The moduloed vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else Math.Functions.safe_modulo(b, a) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else Math.Functions.safe_modulo(float(other), x) for x in self.__components__)
		else:
			return NotImplemented

	def __rpow__(self, other: Vector | float, modulo: int | float = None) -> Vector:
		"""
		Raises another vector or number by this vector
		:param other: The single number or vector to raise
		:return: The raised vector
		:raises ValueError: If the specified vector's dimensions do not match
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return Vector(None if a is None or b is None else pow(b, a, modulo) for a, b in zip(self.__components__, other.__components__))
		elif isinstance(other, (float, int)):
			return Vector(None if x is None else pow(float(other), x, modulo) for x in self.__components__)
		else:
			return NotImplemented

	def __lt__(self, other: Vector | float) -> bool:
		"""
		Compares the length of this vector with 'other'
		:param other: The vector or number to compare against
		:return: Whether this vector's length is less than 'number'
		:raises AssertionError: If vector's dimension differ from this
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return self.length_squared() < other.length_squared()
		elif isinstance(other, (float, int)):
			return self.length_squared() < (other * other)
		else:
			return NotImplemented

	def __le__(self, other: Vector | float) -> bool:
		"""
		Compares the length of this vector with 'other'
		:param other: The vector or number to compare against
		:return: Whether this vector's length is less than or equal to 'number'
		:raises AssertionError: If vector's dimension differ from this
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return self.length_squared() <= other.length_squared()
		elif isinstance(other, (float, int)):
			return self.length_squared() <= (other * other)
		else:
			return NotImplemented

	def __gt__(self, other: Vector | float) -> bool:
		"""
		Compares the length of this vector with 'other'
		:param other: The vector or number to compare against
		:return: Whether this vector's length is greater than 'number'
		:raises AssertionError: If vector's dimension differ from this
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return self.length_squared() > other.length_squared()
		elif isinstance(other, (float, int)):
			return self.length_squared() > (other * other)
		else:
			return NotImplemented

	def __ge__(self, other: Vector | float) -> bool:
		"""
		Compares the length of this vector with 'other'
		:param other: The vector or number to compare against
		:return: Whether this vector's length is greater than or equal to 'number'
		:raises AssertionError: If vector's dimension differ from this
		"""

		if isinstance(other, Vector):
			Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
			return self.length_squared() >= other.length_squared()
		elif isinstance(other, (float, int)):
			return self.length_squared() >= (other * other)
		else:
			return NotImplemented

	def __eq__(self, other: Vector | float) -> bool:
		"""
		If other is a number: Compares the length of this vector with 'other'
		If other is a Vector: Checks for equality
		:param other: The vector or number to compare against
		:return: Whether this vector's length equals 'number' or whether these vectors match
		"""

		if isinstance(other, Vector):
			return self.dimension == other.dimension and self.__components__ == other.__components__
		elif isinstance(other, (float, int)):
			return self.length_squared() == (other * other)
		else:
			return False

	def __ne__(self, other: Vector | float) -> bool:
		"""
		If other is a number: Compares the length of this vector with 'other'
		If other is a Vector: Checks for equality
		:param other: The vector or number to compare against
		:return: Whether this vector's length does not equal 'number' or whether these vectors do not match
		"""

		return not (self == other)

	def __getitem__(self, item: int | slice) -> typing.Optional[float] | tuple[typing.Optional[float], ...]:
		"""
		Gets a component or components from this vector
		:param item: The components to get
		:return: The components
		"""

		return self.__components__[item]

	def __bool__(self) -> bool:
		"""
		:return: Whether this vector is a zero vector
		"""

		return all(x is None or x == 0 for x in self.__components__)

	def __hash__(self) -> int:
		return hash(self.__components__)

	def __abs__(self) -> Vector:
		"""
		:return: Returns the absolute value of this vector "|v|"
		"""

		return Vector(None if x is None else abs(x) for x in self.__components__)

	def __neg__(self) -> Vector:
		"""
		:return: Returns the negation of this vector "-v"
		"""

		return Vector(None if x is None else -x for x in self.__components__)

	def __pos__(self) -> Vector:
		"""
		:return: Returns a copy of this vector "+v"
		"""

		return Vector(None if x is None else +x for x in self.__components__)

	def __round__(self, n: int = None) -> Vector | int:
		"""
		:param n: The number of places to round
		:return: Returns this vector rounded to 'n' places
		"""

		return Vector(None if x is None else float(round(x, n)) for x in self.__components__)

	def __trunc__(self) -> Vector:
		"""
		:return: Returns this vector truncated
		"""

		return Vector(None if x is None else math.trunc(x) for x in self.__components__)

	def __floor__(self) -> Vector:
		"""
		:return: Returns this vector floored
		"""

		return Vector(None if x is None else math.floor(x) for x in self.__components__)

	def __ceil__(self) -> Vector:
		"""
		:return: Returns this vector ceiled
		"""

		return Vector(None if x is None else math.ceil(x) for x in self.__components__)

	def __repr__(self) -> str:
		return f'<{Vector.__name__} {self.dimension}D at {hex(id(self))}>'

	def __str__(self) -> str:
		return f'〈{", ".join(str(x) for x in self.__components__)}〉'

	def length(self) -> float:
		"""
		:return: The length of this vector
		"""

		return float('nan') if None in self.__components__ else math.sqrt(sum(pow(a, 2) for a in self.__components__))

	def length_squared(self) -> float:
		"""
		:return: The square length of this vector
		"""

		return float('nan') if None in self.__components__ else sum(pow(a, 2) for a in self.__components__)

	def dot(self, other: Vector) -> float:
		"""
		Applies inner dot-product between two vectors
		:param other: The second vector
		:return: The dot product of these two vectors
		:raises InvalidArgumentException: If 'other' is not a vector
		:raises ValueError: If vector dimensions are mismatched
		"""

		Misc.raise_ifn(isinstance(other, Vector), Exceptions.InvalidArgumentException(Vector.dot, 'other', type(other), (Vector,)))
		Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
		return float('nan') if None in self.__components__ or None in other.__components__ else sum(a * b for a, b in zip(self.__components__, other.__components__))

	def distance(self, other: Vector) -> float:
		"""
		Calculates distance between two vectors
		:param other: The second vector
		:return: The distance between these two vectors
		:raises InvalidArgumentException: If 'other' is not a vector
		:raises ValueError: If vector dimensions are mismatched
		"""

		Misc.raise_ifn(isinstance(other, Vector), Exceptions.InvalidArgumentException(Vector.distance, 'other', type(other), (Vector,)))
		Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
		return float('nan') if None in self.__components__ or None in other.__components__ else (other - self).length()

	def distance_squared(self, other: Vector) -> float:
		"""
		Calculates square distance between two vectors
		:param other: The second vector
		:return: The square distance between these two vectors
		:raises InvalidArgumentException: If 'other' is not a vector
		:raises ValueError: If vector dimensions are mismatched
		"""

		Misc.raise_ifn(isinstance(other, Vector), Exceptions.InvalidArgumentException(Vector.distance_squared, 'other', type(other), (Vector,)))
		Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
		return float('nan') if None in self.__components__ or None in other.__components__ else (other - self).length_squared()

	def angle(self, other: Vector) -> float:
		"""
		Calculates the angle between two vectors
		:param other: The second vector
		:return: The angle (in radians) between these two vectors
		:raises InvalidArgumentException: If 'other' is not a vector
		:raises ValueError: If vector dimensions are mismatched
		"""

		Misc.raise_ifn(isinstance(other, Vector), Exceptions.InvalidArgumentException(Vector.angle, 'other', type(other), (Vector,)))
		Misc.raise_ifn(self.dimension == other.dimension, ValueError('Mismatched vector dimensions'))
		return float('nan') if None in self.__components__ or None in other.__components__ else math.acos(round(self.dot(other) / (self.length() * other.length()), 7))

	def normalized(self) -> Vector:
		"""
		:return: This vector normalized
		"""

		length: float = self.length()
		return self / length

	def hodge_star(self, *others: Vector) -> Vector:
		"""
		Calculates hodge product between this vector and n-2 vectors
		:param others: The other vectors to compute against (The number of vectors must equal this vector's dimension minus 2)
		:return: (float) The hodge product of all included vectors
		:raises AssertionError: If 'callback' is not a Vector or vector dimensions are mismatched
		:raises ValueError: If any vector is incomplete
		"""

		others: list[Vector] = [self, *others]
		dimension: int = self.dimension
		assert all(isinstance(x, Vector) for x in others), 'One or more object is not a Vector'
		assert len(others) == dimension - 1, f'Need {dimension - 1} vector(s) to compute {dimension} cross product'
		components: list[float] = []

		if any(not v.complete for v in others):
			raise ValueError('Incomplete vector')

		for i in range(dimension):
			indices: tuple[int, ...] = tuple(j for j in range(dimension) if j != i)
			component: float = math.prod(others[j][k] for j, k in enumerate(indices)) - math.prod(others[j][k] for j, k in enumerate(reversed(indices)))
			components.append(component)

		return Vector(components)

	def cross(self, other: Vector) -> Vector:
		"""
		Calculates cross product between vectors
		:param other: The second vector
		:return: A vector rotated 90 degrees to both vectors
		:raises InvalidArgumentException: If 'other' is not a vector
		:raises ValueError: If vector dimensions are mismatched
		"""

		Misc.raise_ifn(isinstance(other, Vector), Exceptions.InvalidArgumentException(Vector.cross, 'other', type(other), (Vector,)))
		assert self.dimension == other.dimension and self.dimension == 3, 'Vector not 3D'

		a1, a2, a3 = self
		b1, b2, b3 = other

		c1: typing.Optional[float] = None if a2 is None or b3 is None else (a2 * b3 - a3 * b2)
		c2: typing.Optional[float] = None if a1 is None or b3 is None else (a3 * b1 - a1 * b3)
		c3: typing.Optional[float] = None if a1 is None or b2 is None else (a1 * b2 - a2 * b1)
		return Vector(c1, c2, c3)

	def to_matrix(self) -> Math.Tensor.Tensor:
		"""
		:return: This vector as a matrix
		"""

		return Math.Tensor.Tensor(self)

	def relative_coord_matrix(self, *orthonormal_basis: Vector) -> Math.Tensor.Tensor:
		"""
		Calculates the coordinate matrix of the specified coordinate relative to the orthonormal basis vectors
		:param orthonormal_basis: The basis vectors; there must be "n" vectors each "n" dimensions where "n" is the coordinate vector's dimension
		:return: The coordinate matrix
		:raises AssertionError: If any vector is not a vector or vector dimensions are mismatched
		"""

		assert all(isinstance(vector, Vector) for vector in orthonormal_basis), 'One or more basis vectors is not a Vector'
		assert all(vector.dimension == len(orthonormal_basis) for vector in orthonormal_basis), 'Vector dimension does not match basis dimension'
		assert self.dimension == len(orthonormal_basis), 'Coordinate dimension does not match basis dimension'

		result: tuple[float, ...] = tuple(self.dot(vector) for vector in orthonormal_basis)
		return Math.Tensor.Tensor.shaped(result, self.dimension, 1)

	def project(self, subspace: typing.Iterable[Vector]) -> Vector:
		"""
		Projects this vector onto a subspace
		:param subspace: A subspace defined by 2 vectors
		:return: The projected vector
		:raises AssertionError: If any vector in 'subspace' is not a vector
		"""

		subspace: tuple[Vector, ...] = tuple(subspace)
		assert all(isinstance(x, Vector) for x in subspace), 'Subspace is not a vector set'
		u1, u2 = Vector.gram_schmidt(subspace[0], subspace[1])
		return self.dot(u1) * u1 + self.dot(u2) * u2

	@property
	def complete(self) -> bool:
		"""
		:return: Whether any component of this vector is None
		"""

		return None not in self.__components__

	@property
	def dimension(self) -> int:
		"""
		:return: The total dimension of this vector
		"""

		return len(self.__components__)

	@property
	def components(self) -> tuple[typing.Optional[float], ...]:
		"""
		:return: Returns the individual components of this vector
		"""

		return self.__components__
