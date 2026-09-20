from __future__ import annotations

import collections.abc

from . import Material
from . import Math
from . import Poly
from .. import Exceptions
from .. import Misc


class Vector2List(collections.abc.Sequence):
	@classmethod
	def from_numpy(cls, array: Math.CPU.ndarray) -> Vector2List:
		"""
		Creates a list of Vector2 vectors from an Nx2 numpy array
		:param array: The array
		:return: The vector list
		"""

		Misc.raise_ifn(isinstance(array, Math.CPU.ndarray), Exceptions.InvalidArgumentException(Vector2List.from_numpy, 'array', type(array), (Math.CPU.ndarray,)))
		Misc.raise_if(len(array.shape) != 2 or array.shape[1] != 2, ValueError(f'Input array must be Nx2, got {"x".join(str(x) for x in array.shape)}'))
		vectors: Vector2List = cls.__new__(cls)
		vectors.__array__ = array.copy()
		return vectors

	@classmethod
	def repeat(cls, vector: Math.Vector2, count: int) -> Vector2List:
		"""
		Creates a vector list of the same vector repeated
		:param vector: The vector to repeat
		:param count: The number of times to repeat
		:return: The vector list
		"""

		Misc.raise_ifn(isinstance(vector, Math.Vector2), Exceptions.InvalidArgumentException(Vector2List.repeat, 'vector', type(vector), (Math.Vector2,)))
		vectors: Vector2List = cls.__new__(cls)
		vectors.__array__ = Math.CPU.zeros((int(count), 2), Math.CPU.float64)

		for i in range(count):
			vectors.__array__[i] = vector.array

		return vectors

	def __init__(self, *vectors: Math.Vector2):
		"""
		Class representing a vectorized list of 2D vectors
		:param vectors: The 2D vectors
		"""

		self.__array__: Math.CPU.ndarray = Math.CPU.zeros((len(vectors), 2), Math.CPU.float64)

		for i, vector in enumerate(vectors):
			Misc.raise_ifn(isinstance(vector, Math.Vector2), Exceptions.InvalidArgumentException(Vector2List.__init__, 'vectors', type(vector), (Math.Vector2,)))
			self.__array__[i] = vector.array

	def __setitem__(self, index: int, vector: Math.Vector2) -> None:
		"""
		Sets the vector at the specified index
		:param index: The index to set
		:param vector: The 2D vector to set to
		"""

		Misc.raise_ifn(isinstance(vector, Math.Vector2), Exceptions.InvalidArgumentException(Vector2List.__setitem__, 'vector', type(vector), (Math.Vector2,)))
		self.__array__[index] = vector.components

	def __len__(self) -> int:
		"""
		:return: The number of vectors in this list
		"""

		return self.__array__.shape[0]

	def __getitem__(self, index: int) -> Math.Vector2:
		"""
		:param index: The index to get
		:return: The 2D vector at 'index'
		"""

		x, y = self.__array__[index]
		return Math.Vector2(float(x), float(y))

	def __iter__(self) -> collections.abc.Iterator[Math.Vector2]:
		"""
		:return: An iterator over all stored vectors
		"""

		for i in range(len(self)):
			yield self[i]

	def __eq__(self, other: Vector2List) -> bool:
		"""
		:param other: The other vector list
		:return: Whether the two vector lists are equal
		"""

		return isinstance(other, type(self)) and other.array == self.array

	def __gt__(self, other: Vector2List) -> Math.CPU.ndarray:
		"""
		:param other: The other vector list
		:return: Whether this vector's square lengths are greater than other vector's square lengths
		"""

		return self.length_squared() > other.length_squared() if isinstance(other, type(self)) else NotImplemented

	def __lt__(self, other: Vector2List) -> Math.CPU.ndarray:
		"""
		:param other: The other vector list
		:return: Whether this vector's square lengths are lesser than other vector's square lengths
		"""

		return self.length_squared() < other.length_squared() if isinstance(other, type(self)) else NotImplemented

	def __hash__(self) -> int:
		"""
		:return: The hash code for this vector list
		"""

		return hash(self.array)

	def __repr__(self) -> str:
		"""
		:return: Representation of this vector list
		"""

		return str(self)

	def __str__(self) -> str:
		"""
		:return: String representation of this vector list
		"""

		return f'[{", ".join(f'〈{x}, {y}〉' for x, y in self)}]'

	def __add__(self, other: float | Math.Vector2 | Vector2List | collections.abc.Iterable[float]) -> Vector2List:
		"""
		Adds a number, vector, or vector list to this vector list
		:param other: The other number, vector, or vector list to add
		:return: The added vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array + float(other))
		elif isinstance(other, Math.Vector2):
			result: Vector2List = type(self).from_numpy(self.array)
			result.array[:, 0] += other.x
			result.array[:, 1] += other.y
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector2List = type(self).from_numpy(self.array[:count] + other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector2List = type(self).from_numpy(self.array[:count])
			result.array[:, :] += sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __sub__(self, other: float | Math.Vector2 | Vector2List | collections.abc.Iterable[float]) -> Vector2List:
		"""
		Subtracts a number, vector, or vector list from this vector list
		:param other: The other number, vector, or vector list to subtract
		:return: The subtracted vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array - float(other))
		elif isinstance(other, Math.Vector2):
			result: Vector2List = type(self).from_numpy(self.array)
			result.array[:, 0] -= other.x
			result.array[:, 1] -= other.y
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector2List = type(self).from_numpy(self.array[:count] - other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector2List = type(self).from_numpy(self.array[:count])
			result.array[:, :] -= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __mul__(self, other: float | Math.Vector2 | Vector2List | collections.abc.Iterable[float]) -> Vector2List:
		"""
		Multiplies a number, vector, or vector list to this vector list
		:param other: The other number, vector, or vector list to multiply
		:return: The multiplied vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array * float(other))
		elif isinstance(other, Math.Vector2):
			result: Vector2List = type(self).from_numpy(self.array)
			result.array[:, 0] *= other.x
			result.array[:, 1] *= other.y
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector2List = type(self).from_numpy(self.array[:count] * other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector2List = type(self).from_numpy(self.array[:count])
			result.array[:, :] *= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __truediv__(self, other: float | Math.Vector2 | Vector2List | collections.abc.Iterable[float]) -> Vector2List:
		"""
		Divides a number, vector, or vector list from this vector list
		:param other: The other number, vector, or vector list to divide
		:return: The divided vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array / float(other))
		elif isinstance(other, Math.Vector2):
			result: Vector2List = type(self).from_numpy(self.array)
			result.array[:, 0] /= other.x
			result.array[:, 1] /= other.y
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector2List = type(self).from_numpy(self.array[:count] / other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector2List = type(self).from_numpy(self.array[:count])
			result.array[:, :] /= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __radd__(self, other: float | Math.Vector2 | Vector2List | collections.abc.Iterable[float]) -> Vector2List:
		"""
		Adds this vector list to a number, vector, or vector list
		:param other: The other number, vector, or vector list to add to
		:return: The added vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(float(other) + self.array)
		elif isinstance(other, Math.Vector2):
			result: Vector2List = type(self).from_numpy(self.array)
			result.array[:, 0] += other.x
			result.array[:, 1] += other.y
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector2List = type(self).from_numpy(other.array[:count] + self.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector2List = type(self).from_numpy(self.array[:count])
			result.array[:, :] += sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __rsub__(self, other: float | Math.Vector2 | Vector2List | collections.abc.Iterable[float]) -> Vector2List:
		"""
		Subtracts this vector from a number, vector, or vector list
		:param other: The other number, vector, or vector list to subtract from
		:return: The subtracted vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(float(other) - self.array)
		elif isinstance(other, Math.Vector2):
			result: Vector2List = type(self).from_numpy(self.array)
			result.array[:, 0] = other.x - result.array[:, 0]
			result.array[:, 1] = other.y - result.array[:, 1]
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector2List = type(self).from_numpy(other.array[:count] - self.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector2List = type(self).from_numpy(self.array[:count])
			result.array[:, :] = sequence.reshape((count, 1)) - result.array[:, :]
			return result
		else:
			return NotImplemented

	def __rmul__(self, other: float | Math.Vector2 | Vector2List | collections.abc.Iterable[float]) -> Vector2List:
		"""
		Multiplies this vector to a number, vector, or vector list
		:param other: The other number, vector, or vector list to multiply to
		:return: The multiplied vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(float(other) * self.array)
		elif isinstance(other, Math.Vector2):
			result: Vector2List = type(self).from_numpy(self.array)
			result.array[:, 0] *= other.x
			result.array[:, 1] *= other.y
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector2List = type(self).from_numpy(other.array[:count] * self.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector2List = type(self).from_numpy(self.array[:count])
			result.array[:, :] *= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __rtruediv__(self, other: float | Math.Vector2 | Vector2List | collections.abc.Iterable[float]) -> Vector2List:
		"""
		Divides this vector from a number, vector, or vector list
		:param other: The other number, vector, or vector list to divide from
		:return: The divided vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(float(other) / self.array)
		elif isinstance(other, Math.Vector2):
			result: Vector2List = type(self).from_numpy(self.array)
			result.array[:, 0] = other.x / result.array[:, 0]
			result.array[:, 1] = other.y / result.array[:, 1]
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector2List = type(self).from_numpy(other.array[:count] / self.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector2List = type(self).from_numpy(self.array[:count])
			result.array[:, :] = sequence.reshape((count, 1)) / result.array[:, :]
			return result
		else:
			return NotImplemented

	def __neg__(self) -> Vector2List:
		"""
		:return: The negation of this vector list
		"""

		return Vector2List.from_numpy(-self.array)

	def __pos__(self) -> Vector2List:
		"""
		:return: A copy of this vector list
		"""

		return Vector2List.from_numpy(self.array)

	def normalize(self) -> None:
		"""
		Normalizes this vector list in-place
		"""

		self.array[:] /= self.length()

	def transform(self, matrix: Math.TransformMatrix2D) -> None:
		"""
		Transforms this vector list my a 2D transform matrix in-place
		:param matrix: The 2D transform matrix
		"""

		vector3: Math.NUMPY.ndarray = Math.NUMPY.ones((len(self), 3), Math.NUMPY.float64)
		vector3[:, :2] = self.array
		Math.NUMPY.matmul(vector3, matrix.array, out=vector3)
		self.array[:, :] = vector3[:, :2]

	def sum(self) -> Math.Vector2:
		"""
		:return: The sum of all vectors in this list
		"""

		result: Math.CPU.ndarray = Math.CPU.sum(self.array, axis=0)
		return Math.Vector2(*result)

	def average(self) -> Math.Vector2:
		"""
		:return: The average of all vectors in this list
		"""

		result: Math.CPU.ndarray = Math.CPU.average(self.array, axis=0)
		return Math.Vector2(*result)

	def length(self) -> Math.CPU.ndarray:
		"""
		:return: The length of all vectors in this vector list
		"""

		return Math.CPU.sqrt(self.length_squared())

	def length_squared(self) -> Math.CPU.ndarray:
		"""
		:return: The square length of all vectors in this vector list
		"""

		return self.x * self.x + self.y * self.y

	def dot(self, other: Vector2List) -> Math.CPU.ndarray:
		"""
		Applies inner dot-product between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The dot product of these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 2D vector list
		"""

		Misc.raise_ifn(isinstance(other, Vector2List), Exceptions.InvalidArgumentException(Vector2List.dot, 'other', type(other), (Vector2List,)))
		count: int = min(len(self), len(other))
		return self.x[:count] * other.x[:count] + self.y[:count] * other.y[:count]

	def distance(self, other: Vector2List) -> Math.CPU.ndarray:
		"""
		Calculates distance between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The distance between these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 2D vector list
		"""

		return Math.CPU.sqrt(self.distance_squared(other))

	def distance_squared(self, other: Vector2List) -> Math.CPU.ndarray:
		"""
		Calculates square distance between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The distance between these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 2D vector list
		"""

		Misc.raise_ifn(isinstance(other, Vector2List), Exceptions.InvalidArgumentException(Vector2List.distance_squared, 'other', type(other), (Vector2List,)))
		return (other - self).length_squared()

	def angle(self, other: Vector2List) -> Math.CPU.ndarray:
		"""
		Calculates the angle between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The angle (in radians) between these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 2D vector list
		"""

		Misc.raise_ifn(isinstance(other, Vector2List), Exceptions.InvalidArgumentException(Vector2List.angle, 'other', type(other), (Vector2List,)))
		return Math.CPU.acos(Math.CPU.round(self.dot(other) / (self.length() * other.length()), 7))

	def normalized(self) -> Vector2List:
		"""
		:return: This vector list will all vectors normalized
		"""

		return self / self.length()

	def transformed(self, matrix: Math.TransformMatrix2D) -> Vector2List:
		"""
		Transforms this vector list my a 2D transform matrix
		:param matrix: The 2D transform matrix
		:return: The transformed vector list
		"""

		vector3: Math.CPU.ndarray = Math.NUMPY.ones((len(self), 3), Math.NUMPY.float64)
		vector3[:, :2] = self.array
		Math.NUMPY.matmul(vector3, matrix.array, out=vector3)
		return Vector2List.from_numpy(vector3[:, :2])

	def to_vector3_list(self, z: float) -> Vector3List:
		"""
		Converts all vectors in this list to 3D vectors
		:param z: The z data to fill with
		:return: The 3D vector list
		"""

		vector3: Math.CPU.ndarray = Math.CPU.hstack((self.__array__, Math.CPU.full((len(self), 1), float(z), Math.CPU.float64)))
		return Vector3List.from_numpy(vector3)

	def to_vector4_list(self, z: float, w: float) -> Vector4List:
		"""
		Converts all vectors in this list to 4D vectors
		:param z: The z data to fill with
		:param w: The w data to fill with
		:return: The 4D vector list
		"""

		vector4: Math.CPU.ndarray = Math.CPU.hstack((self.__array__, Math.CPU.full((len(self), 1), float(z), Math.CPU.float64), Math.CPU.full((len(self), 1), float(w), Math.CPU.float64)))
		return Vector4List.from_numpy(vector4)

	@property
	def array(self) -> Math.CPU.ndarray:
		"""
		:return: The underlying numpy array
		"""

		return self.__array__

	@property
	def x(self) -> Math.CPU.ndarray:
		"""
		:return: The x components of all vectors in this list
		"""

		return self.array[:, 0]

	@property
	def y(self) -> Math.CPU.ndarray:
		"""
		:return: The y components of all vectors in this list
		"""

		return self.array[:, 1]


class Vector3List(collections.abc.Sequence):
	@classmethod
	def from_numpy(cls, array: Math.CPU.ndarray) -> Vector3List:
		"""
		Creates a list of Vector3 vectors from an Nx3 numpy array
		:param array: The array
		:return: The vector list
		"""

		Misc.raise_ifn(isinstance(array, Math.CPU.ndarray), Exceptions.InvalidArgumentException(Vector3List.from_numpy, 'array', type(array), (Math.CPU.ndarray,)))
		Misc.raise_if(len(array.shape) != 2 or array.shape[1] != 3, ValueError(f'Input array must be Nx3, got {"x".join(str(x) for x in array.shape)}'))
		vectors: Vector3List = cls.__new__(cls)
		vectors.__array__ = array
		return vectors

	@classmethod
	def repeat(cls, vector: Math.Vector3, count: int) -> Vector3List:
		"""
		Creates a vector list of the same vector repeated
		:param vector: The vector to repeat
		:param count: The number of times to repeat
		:return: The vector list
		"""

		Misc.raise_ifn(isinstance(vector, Math.Vector3), Exceptions.InvalidArgumentException(Vector2List.repeat, 'vector', type(vector), (Math.Vector3,)))
		vectors: Vector3List = cls.__new__(cls)
		vectors.__array__ = Math.CPU.zeros((int(count), 3), Math.CPU.float64)

		for i in range(count):
			vectors.__array__[i] = vector.array

		return vectors

	def __init__(self, *vectors: Math.Vector3):
		"""
		Class representing a vectorized list of 3D vectors
		:param vectors: The 3D vectors
		"""

		self.__array__: Math.CPU.ndarray = Math.CPU.zeros((len(vectors), 3), Math.CPU.float64)

		for i, vector in enumerate(vectors):
			Misc.raise_ifn(isinstance(vector, Math.Vector3), Exceptions.InvalidArgumentException(Vector3List.__init__, 'vectors', type(vector), (Math.Vector3,)))
			self.__array__[i] = vector.array

	def __setitem__(self, index: int, vector: Math.Vector3) -> None:
		"""
		Sets the vector at the specified index
		:param index: The index to set
		:param vector: The 3D vector to set to
		"""

		Misc.raise_ifn(isinstance(vector, Math.Vector3), Exceptions.InvalidArgumentException(Vector3List.__setitem__, 'vector', type(vector), (Math.Vector3,)))
		self.__array__[index] = vector.components

	def __len__(self) -> int:
		"""
		:return: The number of vectors in this list
		"""

		return self.__array__.shape[0]

	def __getitem__(self, index: int) -> Math.Vector3:
		"""
		:param index: The index to get
		:return: The 3D vector at 'index'
		"""

		x, y, z = self.__array__[index]
		return Math.Vector3(float(x), float(y), float(z))

	def __iter__(self) -> collections.abc.Iterator[Math.Vector3]:
		"""
		:return: An iterator over all stored vectors
		"""

		for i in range(len(self)):
			yield self[i]

	def __eq__(self, other: Vector3List) -> bool:
		"""
		:param other: The other vector list
		:return: Whether the two vector lists are equal
		"""

		return isinstance(other, type(self)) and other.array == self.array

	def __gt__(self, other: Vector3List) -> Math.CPU.ndarray:
		"""
		:param other: The other vector list
		:return: Whether this vector's square lengths are greater than other vector's square lengths
		"""

		return self.length_squared() > other.length_squared() if isinstance(other, type(self)) else NotImplemented

	def __lt__(self, other: Vector3List) -> Math.CPU.ndarray:
		"""
		:param other: The other vector list
		:return: Whether this vector's square lengths are lesser than other vector's square lengths
		"""

		return self.length_squared() < other.length_squared() if isinstance(other, type(self)) else NotImplemented

	def __hash__(self) -> int:
		"""
		:return: The hash code for this vector list
		"""

		return hash(self.array)

	def __repr__(self) -> str:
		"""
		:return: Representation of this vector list
		"""

		return str(self)

	def __str__(self) -> str:
		"""
		:return: String representation of this vector list
		"""

		return f'[{", ".join(f'〈{x}, {y}, {z}〉' for x, y, z in self)}]'

	def __add__(self, other: float | Math.Vector3 | Vector3List | collections.abc.Iterable[float]) -> Vector3List:
		"""
		Adds a number, vector, or vector list to this vector list
		:param other: The other number, vector, or vector list to add
		:return: The added vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array + float(other))
		elif isinstance(other, Math.Vector3):
			result: Vector3List = type(self).from_numpy(self.array)
			result.array[:, 0] += other.x
			result.array[:, 1] += other.y
			result.array[:, 2] += other.z
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector3List = type(self).from_numpy(self.array[:count] + other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector3List = type(self).from_numpy(self.array[:count])
			result.array[:, :] += sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __sub__(self, other: float | Math.Vector3 | Vector3List | collections.abc.Iterable[float]) -> Vector3List:
		"""
		Subtracts a number, vector, or vector list from this vector list
		:param other: The other number, vector, or vector list to subtract
		:return: The subtracted vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array - float(other))
		elif isinstance(other, Math.Vector3):
			result: Vector3List = type(self).from_numpy(self.array)
			result.array[:, 0] -= other.x
			result.array[:, 1] -= other.y
			result.array[:, 2] -= other.z
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector3List = type(self).from_numpy(self.array[:count] - other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector3List = type(self).from_numpy(self.array[:count])
			result.array[:, :] -= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __mul__(self, other: float | Math.Vector3 | Vector3List | collections.abc.Iterable[float]) -> Vector3List:
		"""
		Multiplies a number, vector, or vector list to this vector list
		:param other: The other number, vector, or vector list to multiply
		:return: The multiplied vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array * float(other))
		elif isinstance(other, Math.Vector3):
			result: Vector3List = type(self).from_numpy(self.array)
			result.array[:, 0] *= other.x
			result.array[:, 1] *= other.y
			result.array[:, 2] *= other.z
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector3List = type(self).from_numpy(self.array[:count] * other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector3List = type(self).from_numpy(self.array[:count])
			result.array[:, :] *= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __truediv__(self, other: float | Math.Vector3 | Vector3List | collections.abc.Iterable[float]) -> Vector3List:
		"""
		Divides a number, vector, or vector list from this vector list
		:param other: The other number, vector, or vector list to divide
		:return: The divided vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array / float(other))
		elif isinstance(other, Math.Vector3):
			result: Vector3List = type(self).from_numpy(self.array)
			result.array[:, 0] /= other.x
			result.array[:, 1] /= other.y
			result.array[:, 2] /= other.z
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector3List = type(self).from_numpy(self.array[:count] / other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector3List = type(self).from_numpy(self.array[:count])
			result.array[:, :] /= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __radd__(self, other: float | Math.Vector3 | Vector3List | collections.abc.Iterable[float]) -> Vector3List:
		"""
		Adds this vector list to a number, vector, or vector list
		:param other: The other number, vector, or vector list to add to
		:return: The added vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array + float(other))
		elif isinstance(other, Math.Vector3):
			result: Vector3List = type(self).from_numpy(self.array)
			result.array[:, 0] += other.x
			result.array[:, 1] += other.y
			result.array[:, 2] += other.z
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector3List = type(self).from_numpy(self.array[:count] + other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector3List = type(self).from_numpy(self.array[:count])
			result.array[:, :] += sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __rsub__(self, other: float | Math.Vector3 | Vector3List | collections.abc.Iterable[float]) -> Vector3List:
		"""
		Subtracts this vector from a number, vector, or vector list
		:param other: The other number, vector, or vector list to subtract from
		:return: The subtracted vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(float(other) - self.array)
		elif isinstance(other, Math.Vector3):
			result: Vector3List = type(self).from_numpy(self.array)
			result.array[:, 0] = other.x - result.array[:, 0]
			result.array[:, 1] = other.y - result.array[:, 1]
			result.array[:, 2] = other.z - result.array[:, 2]
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector3List = type(self).from_numpy(other.array[:count] - self.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector3List = type(self).from_numpy(self.array[:count])
			result.array[:, :] = sequence.reshape((count, 1)) - result.array[:, :]
			return result
		else:
			return NotImplemented

	def __rmul__(self, other: float | Math.Vector3 | Vector3List | collections.abc.Iterable[float]) -> Vector3List:
		"""
		Multiplies this vector to a number, vector, or vector list
		:param other: The other number, vector, or vector list to multiply to
		:return: The multiplied vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array * float(other))
		elif isinstance(other, Math.Vector3):
			result: Vector3List = type(self).from_numpy(self.array)
			result.array[:, 0] *= other.x
			result.array[:, 1] *= other.y
			result.array[:, 2] *= other.z
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector3List = type(self).from_numpy(self.array[:count] * other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector3List = type(self).from_numpy(self.array[:count])
			result.array[:, :] *= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __rtruediv__(self, other: float | Math.Vector3 | Vector3List | collections.abc.Iterable[float]) -> Vector3List:
		"""
		Divides this vector from a number, vector, or vector list
		:param other: The other number, vector, or vector list to divide from
		:return: The divided vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(float(other) / self.array)
		elif isinstance(other, Math.Vector3):
			result: Vector3List = type(self).from_numpy(self.array)
			result.array[:, 0] = other.x / result.array[:, 0]
			result.array[:, 1] = other.y / result.array[:, 1]
			result.array[:, 2] = other.z / result.array[:, 2]
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector3List = type(self).from_numpy(other.array[:count] / self.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector3List = type(self).from_numpy(self.array[:count])
			result.array[:, :] = sequence.reshape((count, 1)) / result.array[:, :]
			return result
		else:
			return NotImplemented

	def __neg__(self) -> Vector3List:
		"""
		:return: The negation of this vector list
		"""

		return Vector3List.from_numpy(-self.array)

	def __pos__(self) -> Vector3List:
		"""
		:return: A copy of this vector list
		"""

		return Vector3List.from_numpy(self.array)

	def normalize(self) -> None:
		"""
		Normalizes this vector list in-place
		"""

		self.array[:] /= self.length()

	def transform(self, matrix: Math.TransformMatrix3D) -> None:
		"""
		Transforms this vector list my a 3D transform matrix in-place
		:param matrix: The 3D transform matrix
		"""

		vector4: Math.NUMPY.ndarray = Math.NUMPY.ones((len(self), 4), Math.NUMPY.float64)
		vector4[:, :3] = self.array
		Math.NUMPY.matmul(vector4, matrix.array, out=vector4)
		self.array[:, :] = vector4[:, :3]

	def sum(self) -> Math.Vector3:
		"""
		:return: The sum of all vectors in this list
		"""

		result: Math.CPU.ndarray = Math.CPU.sum(self.array, axis=0)
		return Math.Vector3(*result)

	def average(self) -> Math.Vector3:
		"""
		:return: The average of all vectors in this list
		"""

		result: Math.CPU.ndarray = Math.CPU.average(self.array, axis=0)
		return Math.Vector3(*result)

	def length(self) -> Math.CPU.ndarray:
		"""
		:return: The length of all vectors in this vector list
		"""

		return Math.CPU.sqrt(self.length_squared())

	def length_squared(self) -> Math.CPU.ndarray:
		"""
		:return: The square length of all vectors in this vector list
		"""

		return self.x * self.x + self.y * self.y + self.z * self.z

	def dot(self, other: Vector3List) -> Math.CPU.ndarray:
		"""
		Applies inner dot-product between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The dot product of these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 3D vector list
		"""

		Misc.raise_ifn(isinstance(other, Vector3List), Exceptions.InvalidArgumentException(Vector3List.dot, 'other', type(other), (Vector3List,)))
		count: int = min(len(self), len(other))
		return self.x[:count] * other.x[:count] + self.y[:count] * other.y[:count] + self.z[:count] * other.z[:count]

	def distance(self, other: Vector3List) -> Math.CPU.ndarray:
		"""
		Calculates distance between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The distance between these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 3D vector list
		"""

		return Math.CPU.sqrt(self.distance_squared(other))

	def distance_squared(self, other: Vector3List) -> Math.CPU.ndarray:
		"""
		Calculates square distance between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The distance between these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 3D vector list
		"""

		Misc.raise_ifn(isinstance(other, Vector3List), Exceptions.InvalidArgumentException(Vector3List.distance_squared, 'other', type(other), (Vector3List,)))
		return (other - self).length_squared()

	def angle(self, other: Vector3List) -> Math.CPU.ndarray:
		"""
		Calculates the angle between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The angle (in radians) between these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 3D vector list
		"""

		Misc.raise_ifn(isinstance(other, Vector3List), Exceptions.InvalidArgumentException(Vector3List.angle, 'other', type(other), (Vector3List,)))
		return Math.CPU.acos(Math.CPU.round(self.dot(other) / (self.length() * other.length()), 7))

	def normalized(self) -> Vector3List:
		"""
		:return: This vector list will all vectors normalized
		"""

		return self / self.length()

	def transformed(self, matrix: Math.TransformMatrix3D) -> Vector3List:
		"""
		Transforms this vector list my a 3D transform matrix
		:param matrix: The 3D transform matrix
		:return: The transformed vector list
		"""

		vector4: Math.NUMPY.ndarray = Math.NUMPY.ones((len(self), 4), Math.NUMPY.float64)
		vector4[:, :3] = self.array
		Math.NUMPY.matmul(vector4, matrix.array, out=vector4)
		return Vector3List.from_numpy(vector4[:, :3])

	def to_vector2_list(self) -> Vector2List:
		"""
		Converts all vectors in this list to 2D vectors\n
		Vector z component is stripped
		:return: The 2D vector list
		"""

		return Vector2List.from_numpy(self.__array__[:, :2])

	def to_vector4_list(self, w: float) -> Vector4List:
		"""
		Converts all vectors in this list to 4D vectors
		:param w: The w data to fill with
		:return: The 4D vector list
		"""

		vector4: Math.CPU.ndarray = Math.CPU.hstack((self.__array__, Math.CPU.full((len(self), 1), float(w), Math.CPU.float64)))
		return Vector4List.from_numpy(vector4)

	@property
	def array(self) -> Math.CPU.ndarray:
		"""
		:return: The underlying numpy array
		"""

		return self.__array__

	@property
	def x(self) -> Math.CPU.ndarray:
		"""
		:return: The x components of all vectors in this list
		"""

		return self.array[:, 0]

	@property
	def y(self) -> Math.CPU.ndarray:
		"""
		:return: The y components of all vectors in this list
		"""

		return self.array[:, 1]

	@property
	def z(self) -> Math.CPU.ndarray:
		"""
		:return: The z components of all vectors in this list
		"""

		return self.array[:, 2]


class Vector4List(collections.abc.Sequence):
	@classmethod
	def from_numpy(cls, array: Math.CPU.ndarray) -> Vector4List:
		"""
		Creates a list of Vector4 vectors from an Nx4 numpy array
		:param array: The array
		:return: The vector list
		"""

		Misc.raise_ifn(isinstance(array, Math.CPU.ndarray), Exceptions.InvalidArgumentException(Vector4List.from_numpy, 'array', type(array), (Math.CPU.ndarray,)))
		Misc.raise_if(len(array.shape) != 2 or array.shape[1] != 4, ValueError(f'Input array must be Nx2, got {"x".join(str(x) for x in array.shape)}'))
		vectors: Vector4List = cls.__new__(cls)
		vectors.__array__ = array
		return vectors

	@classmethod
	def repeat(cls, vector: Math.Vector4, count: int) -> Vector4List:
		"""
		Creates a vector list of the same vector repeated
		:param vector: The vector to repeat
		:param count: The number of times to repeat
		:return: The vector list
		"""

		Misc.raise_ifn(isinstance(vector, Math.Vector4), Exceptions.InvalidArgumentException(Vector2List.repeat, 'vector', type(vector), (Math.Vector4,)))
		vectors: Vector4List = cls.__new__(cls)
		vectors.__array__ = Math.CPU.zeros((int(count), 4), Math.CPU.float64)

		for i in range(count):
			vectors.__array__[i] = vector.array

		return vectors

	def __init__(self, *vectors: Math.Vector4):
		"""
		Class representing a vectorized list of 4D vectors
		:param vectors: The 4D vectors
		"""

		self.__array__: Math.CPU.ndarray = Math.CPU.zeros((len(vectors), 4), Math.CPU.float64)

		for i, vector in enumerate(vectors):
			Misc.raise_ifn(isinstance(vector, Math.Vector4), Exceptions.InvalidArgumentException(Vector4List.__init__, 'vectors', type(vector), (Math.Vector4,)))
			self.__array__[i] = vector.array

	def __setitem__(self, index: int, vector: Math.Vector4) -> None:
		"""
		Sets the vector at the specified index
		:param index: The index to set
		:param vector: The 4D vector to set to
		"""

		Misc.raise_ifn(isinstance(vector, Math.Vector4), Exceptions.InvalidArgumentException(Vector4List.__setitem__, 'vector', type(vector), (Math.Vector4,)))
		self.__array__[index] = vector.components

	def __len__(self) -> int:
		"""
		:return: The number of vectors in this list
		"""

		return self.__array__.shape[0]

	def __getitem__(self, index: int) -> Math.Vector4:
		"""
		:param index: The index to get
		:return: The 4D vector at 'index'
		"""

		x, y, z, w = self.__array__[index]
		return Math.Vector4(float(x), float(y), float(z), float(w))

	def __iter__(self) -> collections.abc.Iterator[Math.Vector4]:
		"""
		:return: An iterator over all stored vectors
		"""

		for i in range(len(self)):
			yield self[i]

	def __eq__(self, other: Vector4List) -> bool:
		"""
		:param other: The other vector list
		:return: Whether the two vector lists are equal
		"""

		return isinstance(other, type(self)) and other.array == self.array

	def __gt__(self, other: Vector4List) -> Math.CPU.ndarray:
		"""
		:param other: The other vector list
		:return: Whether this vector's square lengths are greater than other vector's square lengths
		"""

		return self.length_squared() > other.length_squared() if isinstance(other, type(self)) else NotImplemented

	def __lt__(self, other: Vector4List) -> Math.CPU.ndarray:
		"""
		:param other: The other vector list
		:return: Whether this vector's square lengths are lesser than other vector's square lengths
		"""

		return self.length_squared() < other.length_squared() if isinstance(other, type(self)) else NotImplemented

	def __hash__(self) -> int:
		"""
		:return: The hash code for this vector list
		"""

		return hash(self.array)

	def __repr__(self) -> str:
		"""
		:return: Representation of this vector list
		"""

		return str(self)

	def __str__(self) -> str:
		"""
		:return: String representation of this vector list
		"""

		return f'[{", ".join(f'〈{x}, {y}, {z}, {w}〉' for x, y, z, w in self)}]'

	def __add__(self, other: float | Math.Vector4 | Vector4List | collections.abc.Iterable[float]) -> Vector4List:
		"""
		Adds a number, vector, or vector list to this vector list
		:param other: The other number, vector, or vector list to add
		:return: The added vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array + float(other))
		elif isinstance(other, Math.Vector4):
			result: Vector4List = type(self).from_numpy(self.array)
			result.array[:, 0] += other.x
			result.array[:, 1] += other.y
			result.array[:, 2] += other.z
			result.array[:, 3] += other.w
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector4List = type(self).from_numpy(self.array[:count] + other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector4List = type(self).from_numpy(self.array[:count])
			result.array[:, :] += sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __sub__(self, other: float | Math.Vector4 | Vector4List | collections.abc.Iterable[float]) -> Vector4List:
		"""
		Subtracts a number, vector, or vector list from this vector list
		:param other: The other number, vector, or vector list to subtract
		:return: The subtracted vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array - float(other))
		elif isinstance(other, Math.Vector4):
			result: Vector4List = type(self).from_numpy(self.array)
			result.array[:, 0] -= other.x
			result.array[:, 1] -= other.y
			result.array[:, 2] -= other.z
			result.array[:, 3] -= other.w
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector4List = type(self).from_numpy(self.array[:count] - other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector4List = type(self).from_numpy(self.array[:count])
			result.array[:, :] -= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __mul__(self, other: float | Math.Vector4 | Vector4List | collections.abc.Iterable[float]) -> Vector4List:
		"""
		Multiplies a number, vector, or vector list to this vector list
		:param other: The other number, vector, or vector list to multiply
		:return: The multiplied vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array * float(other))
		elif isinstance(other, Math.Vector4):
			result: Vector4List = type(self).from_numpy(self.array)
			result.array[:, 0] *= other.x
			result.array[:, 1] *= other.y
			result.array[:, 2] *= other.z
			result.array[:, 3] *= other.w
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector4List = type(self).from_numpy(self.array[:count] * other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector4List = type(self).from_numpy(self.array[:count])
			result.array[:, :] *= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __truediv__(self, other: float | Math.Vector4 | Vector4List | collections.abc.Iterable[float]) -> Vector4List:
		"""
		Divides a number, vector, or vector list from this vector list
		:param other: The other number, vector, or vector list to divide
		:return: The divided vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array / float(other))
		elif isinstance(other, Math.Vector4):
			result: Vector4List = type(self).from_numpy(self.array)
			result.array[:, 0] /= other.x
			result.array[:, 1] /= other.y
			result.array[:, 2] /= other.z
			result.array[:, 3] /= other.w
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector4List = type(self).from_numpy(self.array[:count] / other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector4List = type(self).from_numpy(self.array[:count])
			result.array[:, :] /= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __radd__(self, other: float | Math.Vector4 | Vector4List | collections.abc.Iterable[float]) -> Vector4List:
		"""
		Adds this vector list to a number, vector, or vector list
		:param other: The other number, vector, or vector list to add to
		:return: The added vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array + float(other))
		elif isinstance(other, Math.Vector4):
			result: Vector4List = type(self).from_numpy(self.array)
			result.array[:, 0] += other.x
			result.array[:, 1] += other.y
			result.array[:, 2] += other.z
			result.array[:, 3] += other.w
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector4List = type(self).from_numpy(self.array[:count] + other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector4List = type(self).from_numpy(self.array[:count])
			result.array[:, :] += sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __rsub__(self, other: float | Math.Vector4 | Vector4List | collections.abc.Iterable[float]) -> Vector4List:
		"""
		Subtracts this vector from a number, vector, or vector list
		:param other: The other number, vector, or vector list to subtract from
		:return: The subtracted vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(float(other) - self.array)
		elif isinstance(other, Math.Vector4):
			result: Vector4List = type(self).from_numpy(self.array)
			result.array[:, 0] = other.x - result.array[:, 0]
			result.array[:, 1] = other.y - result.array[:, 1]
			result.array[:, 2] = other.z - result.array[:, 2]
			result.array[:, 3] = other.z - result.array[:, 3]
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector4List = type(self).from_numpy(other.array[:count] - self.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector4List = type(self).from_numpy(self.array[:count])
			result.array[:, :] = sequence.reshape((count, 1)) - result.array[:, :]
			return result
		else:
			return NotImplemented

	def __rmul__(self, other: float | Math.Vector4 | Vector4List | collections.abc.Iterable[float]) -> Vector4List:
		"""
		Multiplies this vector to a number, vector, or vector list
		:param other: The other number, vector, or vector list to multiply to
		:return: The multiplied vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(self.array * float(other))
		elif isinstance(other, Math.Vector4):
			result: Vector4List = type(self).from_numpy(self.array)
			result.array[:, 0] *= other.x
			result.array[:, 1] *= other.y
			result.array[:, 2] *= other.z
			result.array[:, 3] *= other.w
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector4List = type(self).from_numpy(self.array[:count] * other.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector4List = type(self).from_numpy(self.array[:count])
			result.array[:, :] *= sequence.reshape((count, 1))
			return result
		else:
			return NotImplemented

	def __rtruediv__(self, other: float | Math.Vector4 | Vector4List | collections.abc.Iterable[float]) -> Vector4List:
		"""
		Divides this vector from a number, vector, or vector list
		:param other: The other number, vector, or vector list to divide from
		:return: The divided vector list
		"""

		if isinstance(other, (int, float)):
			return type(self).from_numpy(float(other) / self.array)
		elif isinstance(other, Math.Vector4):
			result: Vector4List = type(self).from_numpy(self.array)
			result.array[:, 0] = other.x / result.array[:, 0]
			result.array[:, 1] = other.y / result.array[:, 1]
			result.array[:, 2] = other.z / result.array[:, 2]
			result.array[:, 3] = other.z / result.array[:, 3]
			return result
		elif isinstance(other, type(self)):
			count: int = min(len(self), len(other))
			result: Vector4List = type(self).from_numpy(other.array[:count] / self.array[:count])
			return result
		elif isinstance(other, collections.abc.Iterable):
			sequence: Math.CPU.ndarray = Math.CPU.array(other, Math.CPU.float64)
			count: int = min(len(self), len(sequence))
			result: Vector4List = type(self).from_numpy(self.array[:count])
			result.array[:, :] = sequence.reshape((count, 1)) / result.array[:, :]
			return result
		else:
			return NotImplemented

	def __neg__(self) -> Vector4List:
		"""
		:return: The negation of this vector list
		"""

		return Vector4List.from_numpy(-self.array)

	def __pos__(self) -> Vector4List:
		"""
		:return: A copy of this vector list
		"""

		return Vector4List.from_numpy(self.array)

	def normalize(self) -> None:
		"""
		Normalizes this vector list in-place
		"""

		self.array[:] /= self.length()

	def transform(self, matrix: Math.TransformMatrix3D) -> None:
		"""
		Transforms this vector list my a 3D transform matrix in-place
		:param matrix: The 3D transform matrix
		"""

		Math.NUMPY.matmul(self.array, matrix.array, out=self.array)

	def sum(self) -> Math.Vector4:
		"""
		:return: The sum of all vectors in this list
		"""

		result: Math.CPU.ndarray = Math.CPU.sum(self.array, axis=0)
		return Math.Vector4(*result)

	def average(self) -> Math.Vector4:
		"""
		:return: The average of all vectors in this list
		"""

		result: Math.CPU.ndarray = Math.CPU.average(self.array, axis=0)
		return Math.Vector4(*result)

	def length(self) -> Math.CPU.ndarray:
		"""
		:return: The length of all vectors in this vector list
		"""

		return Math.CPU.sqrt(self.length_squared())

	def length_squared(self) -> Math.CPU.ndarray:
		"""
		:return: The square length of all vectors in this vector list
		"""

		return self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w

	def dot(self, other: Vector4List) -> Math.CPU.ndarray:
		"""
		Applies inner dot-product between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The dot product of these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 4D vector list
		"""

		Misc.raise_ifn(isinstance(other, Vector4List), Exceptions.InvalidArgumentException(Vector4List.dot, 'other', type(other), (Vector4List,)))
		count: int = min(len(self), len(other))
		return self.x[:count] * other.x[:count] + self.y[:count] * other.y[:count] + self.z[:count] * other.z[:count]

	def distance(self, other: Vector4List) -> Math.CPU.ndarray:
		"""
		Calculates distance between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The distance between these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 4D vector list
		"""

		return Math.CPU.sqrt(self.distance_squared(other))

	def distance_squared(self, other: Vector4List) -> Math.CPU.ndarray:
		"""
		Calculates square distance between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The distance between these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 4D vector list
		"""

		Misc.raise_ifn(isinstance(other, Vector4List), Exceptions.InvalidArgumentException(Vector4List.distance_squared, 'other', type(other), (Vector4List,)))
		return (other - self).length_squared()

	def angle(self, other: Vector4List) -> Math.CPU.ndarray:
		"""
		Calculates the angle between two vector lists\n
		Result length will be the shortest of the two list's lengths
		:param other: The second vector list
		:return: The angle (in radians) between these two vector lists
		:raises InvalidArgumentException: If 'other' is not a 4D vector list
		"""

		Misc.raise_ifn(isinstance(other, Vector4List), Exceptions.InvalidArgumentException(Vector4List.angle, 'other', type(other), (Vector4List,)))
		return Math.CPU.acos(Math.CPU.round(self.dot(other) / (self.length() * other.length()), 7))

	def normalized(self) -> Vector4List:
		"""
		:return: This vector list will all vectors normalized
		"""

		return self / self.length()

	def transformed(self, matrix: Math.TransformMatrix3D) -> Vector4List:
		"""
		Transforms this vector list my a 3D transform matrix
		:param matrix: The 3D transform matrix
		:return: The transformed vector list
		"""

		vector4: Math.NUMPY.ndarray = Math.NUMPY.matmul(self.array, matrix.array)
		return Vector4List.from_numpy(vector4)

	def to_vector2_list(self) -> Vector2List:
		"""
		Converts all vectors in this list to 2D vectors\n
		Vector w and z component is stripped
		:return: The 2D vector list
		"""

		return Vector2List.from_numpy(self.__array__[:, :2])

	def to_vector3_list(self) -> Vector3List:
		"""
		Converts all vectors in this list to 3D vectors\n
		Vector w component is stripped
		:return: The 3D vector list
		"""

		return Vector3List.from_numpy(self.__array__[:, :3])

	@property
	def array(self) -> Math.CPU.ndarray:
		"""
		:return: The underlying numpy array
		"""

		return self.__array__

	@property
	def x(self) -> Math.CPU.ndarray:
		"""
		:return: The x components of all vectors in this list
		"""

		return self.array[:, 0]

	@property
	def y(self) -> Math.CPU.ndarray:
		"""
		:return: The y components of all vectors in this list
		"""

		return self.array[:, 1]

	@property
	def z(self) -> Math.CPU.ndarray:
		"""
		:return: The z components of all vectors in this list
		"""

		return self.array[:, 2]

	@property
	def w(self) -> Math.CPU.ndarray:
		"""
		:return: The z components of all vectors in this list
		"""

		return self.array[:, 3]


class VectorList(collections.abc.Sequence):
	def __init__(self, *vectors: Math.Vector_T):
		self.__array__: Math.CPU.ndarray = Math.CPU.zeros((len(vectors), 4), Math.CPU.float64)
		self.__types__: list[type[Math.Vector_T]] = [type(vec) for vec in vectors]

		for i, vector in enumerate(vectors):

			if isinstance(vector, Math.Vector2):
				self.__array__[i] = (*vector.array, 0, 1)
			elif isinstance(vector, Math.Vector3):
				self.__array__[i] = (*vector.array, 1)
			elif isinstance(vector, Math.Vector4):
				self.__array__[i] = vector.array
			else:
				raise Exceptions.InvalidArgumentException(VectorList.__init__, 'vectors', type(vector), (Math.Vector2, Math.Vector3, Math.Vector4))

	def __setitem__(self, index: int, vector: Math.Vector4) -> None:
		self.__types__[index] = type(vector)

		if isinstance(vector, Math.Vector2):
			self.__array__[index] = (*vector.components, 0, 1)
		elif isinstance(vector, Math.Vector3):
			self.__array__[index] = (*vector.components, 1)
		elif isinstance(vector, Math.Vector4):
			self.__array__[index] = vector.components
		else:
			raise Exceptions.InvalidArgumentException(VectorList.__setitem__, 'vector', type(vector), (Math.Vector2, Math.Vector3, Math.Vector4))

	def __len__(self) -> int:
		return self.__array__.shape[0]

	def __getitem__(self, index: int) -> Math.Vector_T:
		x, y, z, w = self.__array__[index]
		target_type: type[Math.Vector_T] = self.__types__[index]

		if issubclass(target_type, Math.Vector2):
			return Math.Vector2(float(x), float(y))
		elif issubclass(target_type, Math.Vector3):
			return Math.Vector3(float(x), float(y), float(z))
		elif issubclass(target_type, Math.Vector4):
			return Math.Vector4(float(x), float(y), float(z), float(w))

	def __iter__(self) -> collections.abc.Iterator[Math.Vector_T]:
		for i in range(len(self)):
			yield self[i]

	def to_vector2_list(self) -> Vector2List:
		return Vector2List.from_numpy(self.__array__[:, :2])

	def to_vector3_list(self) -> Vector3List:
		return Vector3List.from_numpy(self.__array__[:, :3])

	def to_vector4_list(self) -> Vector4List:
		return Vector4List.from_numpy(self.__array__[:, :])

	@property
	def array(self) -> Math.CPU.ndarray:
		return self.__array__


class Polygon3DList(collections.abc.Sequence):
	def __init__(self, *polygons: Poly.Polygon3D):
		"""
		Class representing a vectorized list of 3D polygons
		:param polygons: The 3D polygons
		"""

		highest_count: int = 0
		array: list[list[tuple[float, float, float, float]]] = []
		nan: float = float('nan')

		for polygon in polygons:
			Misc.raise_ifn(isinstance(polygon, Poly.Polygon3D), Exceptions.InvalidArgumentException(Polygon3DList.__init__, 'polygons', type(polygon), (Poly.Polygon3D,)))
			highest_count = max(highest_count, len(polygon.points))
			array.append([(x, y, z, 1) for x, y, z in polygon.points])

		for points in array:
			points.extend((nan, nan, nan, nan) for _ in range(highest_count - len(points)))

		self.__array__: Math.CPU.ndarray = Math.CPU.array(array, Math.CPU.float64)
		self.__data__: tuple[tuple[Material.UVMap, bool, int], ...] = tuple((polygon.material, polygon.is_normal_inverted, len(polygon.points)) for polygon in polygons)

	def __len__(self) -> int:
		"""
		:return: The number of polygons in this list
		"""

		return self.__array__.shape[0]

	def __getitem__(self, index: int) -> Poly.Polygon3D:
		"""
		:param index: The index to get
		:return: The 3D polygon at 'index'
		"""

		source: tuple[Material.UVMap, bool] = self.__data__[index]
		points: tuple[Math.Vector3, ...] = tuple(Math.Vector3(x, y, z) for x, y, z, _ in self.array[index][:source[2]])
		return Poly.Polygon3D(*points, uv_mat=source[0], invert_normal=source[1])

	def __iter__(self) -> collections.abc.Iterator[Poly.Polygon3D]:
		"""
		:return: An iterator over all stored polygons
		"""

		for i in range(len(self)):
			yield self[i]

	def transform(self, matrix: Math.TransformMatrix3D) -> None:
		"""
		Transforms all polygons in this list by the 3D transform matrix in-place
		:param matrix: The 3D transform matrix
		"""

		self.array[:] = Math.CPU.matmul(self.array, matrix.array)

	def transformed(self, matrix: Math.TransformMatrix3D) -> Polygon3DList:
		"""
		Transforms all polygons in this list by the 3D transform matrix
		:param matrix: The 3D transform matrix
		:return: The transformed polygon list
		"""

		result: Math.CPU.ndarray = Math.CPU.matmul(self.array, matrix.array)
		poly_list: Polygon3DList = Polygon3DList()
		poly_list.__array__ = result
		poly_list.__data__ = self.__data__
		return poly_list

	@property
	def array(self) -> Math.CPU.ndarray:
		"""
		:return: The underlying numpy array
		"""

		return self.__array__


__all__: list[str] = [
	'Vector2List', 'Vector3List', 'Vector4List', 'VectorList',
	'Polygon3DList'
]
