from __future__ import annotations

import collections.abc
import math
import numpy
import typing

from CustomMethodsVI.Exceptions import InvalidArgumentException

from .. import Exceptions
from .. import Math
from .. import Misc

try:
	import cupy
	Misc.raise_ifn(False and cupy.is_available(), ImportError('CuPy not available'))
	CPU = numpy
	GPU = cupy
except ImportError:
	CPU = numpy
	GPU = numpy
	NUMPY = numpy


class TransformMatrix2D:
	"""
	Class representing a 3x3 transform matrix
	"""

	@classmethod
	def identity(cls) -> TransformMatrix2D:
		"""
		:return: The 3x3 identity matrix
		"""

		return cls(Math.Tensor.Tensor.identity(3, 3))

	@classmethod
	def zero(cls) -> TransformMatrix2D:
		"""
		:return: A 3x3 matrix of all zeroes
		"""

		return cls(Math.Tensor.Tensor.full(0, 3, 3))

	@classmethod
	def one(cls) -> TransformMatrix2D:
		"""
		:return: A 3x3 matrix of all ones
		"""

		return cls(Math.Tensor.Tensor.full(1, 3, 3))

	@classmethod
	def nan(cls) -> TransformMatrix2D:
		"""
		:return: A NaN matrix
		"""

		return cls.full(float('nan'))

	@classmethod
	def full(cls, value: float) -> TransformMatrix2D:
		"""
		:return: A 3x3 matrix of all one value
		"""

		return cls(Math.Tensor.Tensor.full(float(value), 3, 3))

	@classmethod
	def create_world(cls, right: Vector2, up: Vector2, translation: Vector2) -> TransformMatrix2D:
		"""
		Creates a world matrix
		:param right: The right axis
		:param up: The up axis
		:param translation: The position
		:return: The world matrix
		"""

		m11, m12 = right
		m21, m22 = up
		m31, m32 = translation
		return cls((
			m11, m12, 0,
			m21, m22, 0,
			m31, m32, 1
		))

	@classmethod
	def create_scale(cls, scale_x: float, scale_y: float) -> TransformMatrix2D:
		"""
		Creates a scaling matrix
		:param scale_x: The x-axis scale
		:param scale_y: The y-axis scale
		:return: The scaling matrix
		"""

		return cls((
			scale_x, 0, 0,
			0, scale_y, 0,
			0, 0, 1
		))

	@classmethod
	def create_rotation(cls, rotation_z: float) -> TransformMatrix2D:
		"""
		Creates a rotation matrix
		:param rotation_z: The z-axis rotation in radians
		:return: The rotation matrix
		"""

		return cls((
			math.cos(rotation_z), -math.sin(rotation_z), 0,
			math.sin(rotation_z), -math.cos(rotation_z), 0,
			0, 0, 1
		))

	@classmethod
	def create_translation(cls, translation_x: float, translation_y: float) -> TransformMatrix2D:
		"""
		Creates a translation matrix
		:param translation_x: The x-axis translation
		:param translation_y: The y-axis translation
		:return: The translation matrix
		"""

		return cls((
			1, 0, 0,
			0, 1, 0,
			translation_x, translation_y, 1
		))

	@classmethod
	def create_shear(cls, shear_xy: float, shear_yx: float) -> TransformMatrix2D:
		"""
		Creates a shearing matrix
		:param shear_xy: The x along y shearing
		:param shear_yx: The y along x shearing
		:return: The shearing matrix
		"""

		return cls((
			1, shear_yx, 0,
			shear_xy, 1, 0,
			0, 0, 0, 1
		))

	def __init__(self, matrix: collections.abc.Sequence[float] | Math.Tensor.Tensor | CPU.ndarray | GPU.ndarray):
		"""
		Class representing a 3x3 transform matrix
		- Constructor -
		:param matrix: The matrix or tensor to construct from
		"""

		length: int = ...
		assert (
			(isinstance(matrix, Math.Tensor.Tensor) and (matrix.dimensions == (2, 2) or matrix.dimensions == (3, 3)))
			or (isinstance(matrix, CPU.ndarray) and (matrix.shape == (2, 2) or matrix.shape == (3, 3)))
			or (isinstance(matrix, GPU.ndarray) and (matrix.shape == (2, 2) or matrix.shape == (3, 3)))
			or (isinstance(matrix, collections.abc.Sequence) and ((length := len(matrix := tuple(matrix))) == 9 or length == 9) and all(isinstance(x, (int, float)) for x in matrix))),\
			'Matrix must be either a 2x2 or 3x3 array of floats'

		if (isinstance(matrix, Math.Tensor.Tensor) and matrix.dimensions == (2, 2)) or length == 4:
			m11, m12, m21, m22 = matrix
			self.__matrix__: CPU.ndarray = CPU.array((
				(m11, m12, 0),
				(m21, m22, 0),
				(0, 0, 1)
			), CPU.float64)
		elif isinstance(matrix, Math.Tensor.Tensor) and matrix.dimensions == (3, 3):
			self.__matrix__: CPU.ndarray = matrix.to_numpy()
		elif isinstance(matrix, CPU.ndarray) and matrix.shape == (2, 2):
			self.__matrix__: CPU.ndarray = CPU.identity(3, CPU.float64)
			self.__matrix__[:2, :2] = matrix
		elif isinstance(matrix, CPU.ndarray):
			self.__matrix__: CPU.ndarray = matrix.astype(CPU.float64)
		elif isinstance(matrix, GPU.ndarray) and matrix.shape == (2, 2):
			self.__matrix__: CPU.ndarray = CPU.identity(3, CPU.float64)
			self.__matrix__[:2, :2] = matrix
		elif isinstance(matrix, GPU.ndarray):
			self.__matrix__: CPU.ndarray = matrix.astype(CPU.float64)
		else:
			self.__matrix__: CPU.ndarray = Math.Tensor.Tensor.shaped(matrix, 3, 3).to_numpy()

	def __hash__(self) -> int:
		return hash(self.__matrix__)

	def __repr__(self) -> str:
		return f'<{TransformMatrix2D.__name__} 3x3 @ {hex(id(self))}>'

	def __str__(self) -> str:
		cells: tuple[str, ...] = tuple(str(cell) for cell in self.__matrix__.flatten())
		c1_length: int = max((len(cells[0]), len(cells[3]), len(cells[6])))
		c2_length: int = max((len(cells[1]), len(cells[4]), len(cells[7])))
		c3_length: int = max((len(cells[2]), len(cells[5]), len(cells[8])))

		return f'''{cells[0].rjust(c1_length, ' ')}, {cells[1].rjust(c2_length, ' ')}, {cells[2].rjust(c3_length, ' ')}
{cells[3].rjust(c1_length, ' ')}, {cells[4].rjust(c2_length, ' ')}, {cells[5].rjust(c3_length, ' ')}
{cells[6].rjust(c1_length, ' ')}, {cells[7].rjust(c2_length, ' ')}, {cells[8].rjust(c3_length, ' ')}
'''

	def __iter__(self) -> typing.Iterator[float]:
		return iter(self.__matrix__)

	def __getitem__(self, index: int | tuple[int | slice, int | slice] | slice) -> CPU.ndarray | TransformMatrix2D | Vector2 | Vector3 | float:
		"""
		Gets a sub-matrix, vector row, or cell value from this matrix
		:param index: The positions to retrieve
		:return: The resulting matrix, vector, or cell value
		"""

		if isinstance(index, int):
			return Vector3(*self.__matrix__[index])
		elif isinstance(index, slice):
			return self.__matrix__[index]
		elif isinstance(index, tuple) and len(index := tuple(index)) == 2:
			result: CPU.ndarray | float = self.__matrix__[index]

			if isinstance(result, float) or len(result) == 1:
				return float(result)
			elif len(result.shape) == 1 or result.shape[1] == 1:
				return Vector2(*result) if result.size == 2 else Vector3(*result)
			elif result.shape == (3, 3):
				return TransformMatrix2D(result)
			else:
				return result
		else:
			raise TypeError('TransformMatrix indices must be either an integer, slice, or tuple of two indices')

	def __abs__(self) -> TransformMatrix2D:
		"""
		:return: A copy of this matrix with all cells absolute
		"""

		return TransformMatrix2D(abs(self.__matrix__))

	def __round__(self, n: typing.Optional[int] = None) -> TransformMatrix2D:
		"""
		:param n: The number of places to round to
		:return: A copy of this matrix with all cells rounded
		"""

		return TransformMatrix2D(CPU.round(self.__matrix__, n))

	def __add__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(self.__matrix__ + other)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix2D(self.__matrix__ + other.__matrix__)
		else:
			return NotImplemented

	def __sub__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(self.__matrix__ - other)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix2D(self.__matrix__ - other.__matrix__)
		else:
			return NotImplemented

	def __mul__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(self.__matrix__ * other)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix2D(self.__matrix__ * other.__matrix__)
		else:
			return NotImplemented

	def __matmul__(self, other: TransformMatrix2D) -> TransformMatrix2D:
		return TransformMatrix2D(self.__matrix__ @ other.__matrix__) if isinstance(other, TransformMatrix2D) else NotImplemented

	def __truediv__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(self.__matrix__ / other)
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(self.__matrix__ / other.__matrix__)
		else:
			return NotImplemented

	def __floordiv__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(self.__matrix__ // other)
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(self.__matrix__ // other.__matrix__)
		else:
			return NotImplemented

	def __mod__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(self.__matrix__ % other)
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(self.__matrix__ % other.__matrix__)
		else:
			return NotImplemented

	def __pow__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(self.__matrix__ ** other)
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(self.__matrix__ ** other.__matrix__)
		else:
			return NotImplemented

	def __radd__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(other + self.__matrix__)
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(other.__matrix__ + self.__matrix__)
		else:
			return NotImplemented

	def __rsub__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(other - self.__matrix__)
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(other.__matrix__ - self.__matrix__)
		else:
			return NotImplemented

	def __rmul__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(other * self.__matrix__)
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(other.__matrix__ * self.__matrix__)
		else:
			return NotImplemented

	def __rmatmul__(self, other: TransformMatrix2D) -> TransformMatrix2D:
		return TransformMatrix2D(other.__matrix__ @ self.__matrix__) if isinstance(other, TransformMatrix2D) else NotImplemented

	def __rtruediv__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(other / self.__matrix__)
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(other.__matrix__ / self.__matrix__)
		else:
			return NotImplemented

	def __rfloordiv__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(other // self.__matrix__)
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(other.__matrix__ // self.__matrix__)
		else:
			return NotImplemented

	def __rmod__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(other % self.__matrix__)
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(other.__matrix__ % self.__matrix__)
		else:
			return NotImplemented

	def __rpow__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(other ** self.__matrix__)
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(other.__matrix__ ** self.__matrix__)
		else:
			return NotImplemented

	def __iadd__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			self.__matrix__ += other
			return self
		elif isinstance(other, TransformMatrix2D):
			self.__matrix__ += other.__matrix__
			return self
		else:
			return NotImplemented

	def __isub__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			self.__matrix__ -= other
			return self
		elif isinstance(other, TransformMatrix2D):
			self.__matrix__ -= other.__matrix__
			return self
		else:
			return NotImplemented

	def __imul__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			self.__matrix__ *= other
			return self
		elif isinstance(other, TransformMatrix2D):
			self.__matrix__ *= other.__matrix__
			return self
		else:
			return NotImplemented

	def __imatmul__(self, other: TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, TransformMatrix2D):
			self.__matrix__ @= other.__matrix__
			return self
		else:
			return NotImplemented

	def __itruediv__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			self.__matrix__ /= other
			return self
		elif isinstance(other, TransformMatrix2D):
			self.__matrix__ /= other.__matrix__
			return self
		else:
			return NotImplemented

	def __ifloordiv__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			self.__matrix__ //= other
			return self
		elif isinstance(other, TransformMatrix2D):
			self.__matrix__ //= other.__matrix__
			return self
		else:
			return NotImplemented

	def __imod__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			self.__matrix__ %= other
			return self
		elif isinstance(other, TransformMatrix2D):
			self.__matrix__ %= other.__matrix__
			return self
		else:
			return NotImplemented

	def __ipow__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			self.__matrix__ **= other
			return self
		elif isinstance(other, TransformMatrix2D):
			self.__matrix__ **= other.__matrix__
			return self
		else:
			return NotImplemented

	def __neg__(self) -> TransformMatrix2D:
		return TransformMatrix2D(-self.__matrix__)

	def __pos__(self) -> TransformMatrix2D:
		return TransformMatrix2D(+self.__matrix__)

	def transform_vector(self, vector: Vector2 | Vector3) -> Vector2 | Vector3:
		"""
		Transforms a vector by this transform matrix
		:param vector: The vector to transform
		:return: The transformed vector
		"""

		if isinstance(vector, Vector3):
			result: CPU.ndarray = vector.array.transpose() @ self.array
			return Vector3(*result.transpose())
		elif isinstance(vector, Vector2):
			source: CPU.ndarray = CPU.zeros((3,), CPU.float64)
			source[:2] = vector.array
			result: CPU.ndarray = source.transpose() @ self.array
			return Vector2(*result.transpose()[:2])
		else:
			raise Exceptions.InvalidArgumentException(TransformMatrix3D.transform_vector, 'vector', type(vector), (Vector2, Vector3))

	def inversed(self) -> TransformMatrix2D:
		try:
			inverse: CPU.ndarray = CPU.linalg.inv(self.__matrix__)
			return TransformMatrix2D(inverse)
		except numpy.linalg.LinAlgError as e:
			raise ValueError('Matrix is singular') from e

	def transposed(self) -> TransformMatrix2D:
		return TransformMatrix2D((
			self.m11, self.m21, self.m31,
			self.m12, self.m22, self.m32,
			self.m13, self.m23, self.m33
		))

	@property
	def m11(self) -> float:
		return self[0, 0]

	@property
	def m12(self) -> float:
		return self[0, 1]

	@property
	def m13(self) -> float:
		return self[0, 2]

	@property
	def m21(self) -> float:
		return self[1, 0]

	@property
	def m22(self) -> float:
		return self[1, 1]

	@property
	def m23(self) -> float:
		return self[1, 2]

	@property
	def m31(self) -> float:
		return self[2, 0]

	@property
	def m32(self) -> float:
		return self[2, 1]

	@property
	def m33(self) -> float:
		return self[2, 2]

	@property
	def right(self) -> Vector2:
		return Vector2(*self.__matrix__[0, :-1])

	@property
	def up(self) -> Vector2:
		return Vector2(*self.__matrix__[1, :-1])

	@property
	def translation(self) -> Vector2:
		return Vector2(*self.__matrix__[2, :-1])

	@property
	def left(self) -> Vector2:
		return -self.right

	@property
	def down(self) -> Vector2:
		return -self.up

	@property
	def scale(self) -> Vector2:
		return Vector2(self.right.length(), self.up.length())

	@property
	def rotation(self) -> CPU.ndarray:
		return self.__matrix__[:2, :2]

	@right.setter
	def right(self, vector: Vector2) -> None:
		Misc.raise_ifn(isinstance(vector, Vector2), Exceptions.InvalidArgumentException(None, 'vector', type(vector), (Vector2,)))
		self.__matrix__[0, :-1] = vector.array

	@up.setter
	def up(self, vector: Vector2) -> None:
		Misc.raise_ifn(isinstance(vector, Vector2), Exceptions.InvalidArgumentException(None, 'vector', type(vector), (Vector2,)))
		self.__matrix__[1, :-1] = vector.array

	@translation.setter
	def translation(self, vector: Vector2) -> None:
		Misc.raise_ifn(isinstance(vector, Vector2), Exceptions.InvalidArgumentException(None, 'vector', type(vector), (Vector2,)))
		self.__matrix__[2, :-1] = vector.array

	@down.setter
	def down(self, vector: Vector2) -> None:
		self.up = -vector

	@left.setter
	def left(self, vector: Vector2) -> None:
		self.right = -vector

	@rotation.setter
	def rotation(self, rotation: Math.Tensor.Tensor | CPU.ndarray | GPU.ndarray) -> None:
		if isinstance(rotation, Math.Tensor.Tensor):
			assert rotation.dimension == 2 and rotation.dimensions == (2, 2), 'Matrix must be a 2x2 rotation matrix'
			self.__matrix__[0:2, 0:2] = rotation.to_numpy()
		elif isinstance(rotation, (CPU.ndarray, GPU.ndarray)):
			assert rotation.shape == (2, 2), 'Matrix must be a 2x2 rotation matrix'
			self.__matrix__[0:2, 0:2] = rotation
		else:
			raise InvalidArgumentException(None, 'rotation', type(rotation), (Math.Tensor.Tensor, CPU.ndarray, GPU.ndarray))

	@scale.setter
	def scale(self, scale: Vector2) -> None:
		Misc.raise_ifn(isinstance(scale, Vector2), Exceptions.InvalidArgumentException(None, 'scale', type(scale), (Vector2,)))
		x, y = scale.components
		self.right = self.right.normalized() * x
		self.up = self.up.normalized() * y

	@property
	def array(self) -> CPU.ndarray:
		"""
		:return: The underlying numpy array
		"""

		return self.__matrix__


class TransformMatrix3D:
	"""
	Class representing a 4x4 transform matrix
	"""

	@classmethod
	def identity(cls) -> TransformMatrix3D:
		"""
		:return: The 4x4 identity matrix
		"""

		return cls(Math.Tensor.Tensor.identity(4, 4))

	@classmethod
	def zero(cls) -> TransformMatrix3D:
		"""
		:return: A 4x4 matrix of all zeroes
		"""

		return cls(Math.Tensor.Tensor.full(0, 4, 4))

	@classmethod
	def one(cls) -> TransformMatrix3D:
		"""
		:return: A 4x4 matrix of all ones
		"""

		return cls(Math.Tensor.Tensor.full(1, 4, 4))

	@classmethod
	def nan(cls) -> TransformMatrix3D:
		"""
		:return: A NaN matrix
		"""

		return cls.full(float('nan'))

	@classmethod
	def full(cls, value: float) -> TransformMatrix3D:
		"""
		:return: A 4x4 matrix of all one value
		"""

		return cls(Math.Tensor.Tensor.full(float(value), 4, 4))

	@classmethod
	def create_world(cls, forward: Vector3, up: Vector3, translation: Vector3) -> TransformMatrix3D:
		"""
		Creates a world matrix
		:param forward: The forward axis
		:param up: The up axis
		:param translation: The position
		:return: The world matrix
		"""

		m11, m12, m13 = forward
		m21, m22, m23 = up
		m31, m32, m33 = forward.cross(up)
		m41, m42, m43 = translation
		return cls((
			m11, m12, m13, 0,
			m21, m22, m23, 0,
			m31, m32, m33, 0,
			m41, m42, m43, 1
		))

	@classmethod
	def create_scale(cls, scale_x: float, scale_y: float, scale_z: float) -> TransformMatrix3D:
		"""
		Creates a scaling matrix
		:param scale_x: The x-axis scale
		:param scale_y: The y-axis scale
		:param scale_z: The z-axis scale
		:return: The scaling matrix
		"""

		return cls((
			scale_x, 0, 0, 0,
			0, scale_y, 0, 0,
			0, 0, scale_z, 0,
			0, 0, 0, 1
		))

	@classmethod
	def create_rotation(cls, rotation_x: float, rotation_y: float, rotation_z: float) -> TransformMatrix3D:
		"""
		Creates a rotation matrix
		:param rotation_x: The x-axis rotation in radians
		:param rotation_y: The y-axis rotation in radians
		:param rotation_z: The z-axis rotation in radians
		:return: The rotation matrix
		"""

		cos_alpha: float = math.cos(rotation_z)
		sin_alpha: float = math.sin(rotation_z)
		cos_beta: float = math.cos(rotation_y)
		sin_beta: float = math.sin(rotation_y)
		cos_gamma: float = math.cos(rotation_x)
		sin_gamma: float = math.sin(rotation_x)

		return cls((
			cos_beta * cos_alpha, cos_beta * sin_alpha, -sin_beta, 0,
			sin_gamma * sin_beta * cos_alpha - cos_gamma * sin_alpha, sin_gamma * sin_beta * sin_alpha + cos_gamma * cos_alpha, sin_gamma * cos_beta, 0,
			cos_gamma * sin_beta * cos_alpha + sin_gamma * sin_alpha, cos_gamma * sin_beta * sin_alpha - sin_gamma * cos_alpha, cos_gamma * cos_beta, 0,
			0, 0, 0, 1
		))

	@classmethod
	def create_translation(cls, translation_x: float, translation_y: float, translation_z: float) -> TransformMatrix3D:
		"""
		Creates a translation matrix
		:param translation_x: The x-axis translation
		:param translation_y: The y-axis translation
		:param translation_z: The z-axis translation
		:return: The translation matrix
		"""

		return cls((
			1, 0, 0, 0,
			0, 1, 0, 0,
			0, 0, 1, 0,
			translation_x, translation_y, translation_z, 1
		))

	@classmethod
	def create_shear(cls, shear_xy: float, shear_xz: float, shear_yx: float, shear_yz: float, shear_zx: float, shear_zy: float) -> TransformMatrix3D:
		"""
		Creates a shearing matrix
		:param shear_xy: The x along y shearing
		:param shear_xz: The x along z shearing
		:param shear_yx: The y along x shearing
		:param shear_yz: The y along z shearing
		:param shear_zx: The z along x shearing
		:param shear_zy: The z along y shearing
		:return: The shearing matrix
		"""

		return cls((
			1, shear_yx, shear_zx, 0,
			shear_xy, 1, shear_zy, 0,
			shear_xz, shear_yz, 1, 0,
			0, 0, 0, 1
		))

	@classmethod
	def from_quaternion(cls, quaternion: Quaternion3D) -> TransformMatrix3D:
		"""
		Creates a transform matrix from a rotation quaternion\n
		The translation will be (0, 0, 0)
		:param quaternion: The rotation quaternion
		:return: The rotation matrix
		"""

		i, j, k, w = quaternion.components

		m11: float = 2 * (w * w + i * i) - 1
		m12: float = 2 * (i * j - w * k)
		m13: float = 2 * (i * k + w * j)

		m21: float = 2 * (i * j + w * k)
		m22: float = 2 * (w * w + j * j) - 1
		m23: float = 2 * (j * k - w * i)

		m31: float = 2 * (i * k - w * j)
		m32: float = 2 * (j * k + w * i)
		m33: float = 2 * (w * w + k * k) - 1

		return cls((m11, m12, m13, m21, m22, m23, m31, m32, m33))

	def __init__(self, matrix: collections.abc.Sequence[float] | Math.Tensor.Tensor):
		"""
		Class representing a 4x4 transform matrix
		- Constructor -
		:param matrix: The matrix or tensor to construct from
		"""

		length: int = ...
		assert (
			(isinstance(matrix, Math.Tensor.Tensor) and (matrix.dimensions == (3, 3) or matrix.dimensions == (4, 4)))
			or (isinstance(matrix, CPU.ndarray) and (matrix.shape == (3, 3) or matrix.shape == (4, 4)))
			or (isinstance(matrix, GPU.ndarray) and (matrix.shape == (3, 3) or matrix.shape == (4, 4)))
			or (isinstance(matrix, collections.abc.Sequence) and ((length := len(matrix := tuple(matrix))) == 9 or length == 16) and all(isinstance(x, (int, float)) for x in matrix))), \
			'Matrix must be either a 3x3 or 4x4 array of floats'

		if (isinstance(matrix, Math.Tensor.Tensor) and matrix.dimensions == (3, 3)) or length == 9:
			m11, m12, m13, m21, m22, m23, m31, m32, m33 = matrix
			self.__matrix__: CPU.ndarray = CPU.array((
				(m11, m12, m13, 0),
				(m21, m22, m23, 0),
				(m31, m32, m33, 0),
				(0, 0, 0, 1)
			), CPU.float64)
		elif isinstance(matrix, Math.Tensor.Tensor) and matrix.dimensions == (4, 4):
			self.__matrix__: CPU.ndarray = matrix.to_numpy()
		elif isinstance(matrix, CPU.ndarray) and matrix.shape == (3, 3):
			self.__matrix__: CPU.ndarray = CPU.identity(4, CPU.float64)
			self.__matrix__[:3, :3] = matrix
		elif isinstance(matrix, CPU.ndarray):
			self.__matrix__: CPU.ndarray = matrix.astype(CPU.float64)
		elif isinstance(matrix, GPU.ndarray) and matrix.shape == (3, 3):
			self.__matrix__: CPU.ndarray = CPU.identity(4, CPU.float64)
			self.__matrix__[:3, :3] = matrix
		elif isinstance(matrix, GPU.ndarray):
			self.__matrix__: CPU.ndarray = matrix.astype(CPU.float64)
		else:
			self.__matrix__: CPU.ndarray = Math.Tensor.Tensor.shaped(matrix, 4, 4).to_numpy()

	def __hash__(self) -> int:
		return hash(self.__matrix__)

	def __repr__(self) -> str:
		return f'<{TransformMatrix3D.__name__} 4x4 @ {hex(id(self))}>'

	def __str__(self) -> str:
		cells: tuple[str, ...] = tuple(str(cell) for cell in self.__matrix__.flatten())
		c1_length: int = max((len(cells[0]), len(cells[4]), len(cells[8]), len(cells[12])))
		c2_length: int = max((len(cells[1]), len(cells[5]), len(cells[9]), len(cells[13])))
		c3_length: int = max((len(cells[2]), len(cells[6]), len(cells[10]), len(cells[14])))
		c4_length: int = max((len(cells[3]), len(cells[7]), len(cells[11]), len(cells[15])))

		return f'''{cells[0].rjust(c1_length, ' ')}, {cells[1].rjust(c2_length, ' ')}, {cells[2].rjust(c3_length, ' ')}, {cells[3].rjust(c4_length, ' ')}
{cells[4].rjust(c1_length, ' ')}, {cells[5].rjust(c2_length, ' ')}, {cells[6].rjust(c3_length, ' ')}, {cells[7].rjust(c4_length, ' ')}
{cells[8].rjust(c1_length, ' ')}, {cells[9].rjust(c2_length, ' ')}, {cells[10].rjust(c3_length, ' ')}, {cells[11].rjust(c4_length, ' ')}
{cells[12].rjust(c1_length, ' ')}, {cells[13].rjust(c2_length, ' ')}, {cells[14].rjust(c3_length, ' ')}, {cells[15].rjust(c4_length, ' ')}
'''

	def __iter__(self) -> typing.Iterator[float]:
		return iter(self.__matrix__)

	def __getitem__(self, index: int | tuple[int | slice, int | slice] | slice) -> CPU.ndarray | TransformMatrix3D | Vector2 | Vector3 | Vector4 | float:
		"""
		Gets a sub-matrix, vector row, or cell value from this matrix
		:param index: The positions to retrieve
		:return: The resulting matrix, vector, or cell value
		"""

		if isinstance(index, int):
			return Vector4(*self.__matrix__[index])
		elif isinstance(index, slice):
			return self.__matrix__[index]
		elif isinstance(index, tuple) and len(index := tuple(index)) == 3:
			result: CPU.ndarray | float = self.__matrix__[index]

			if isinstance(result, float) or len(result) == 1:
				return float(result)
			elif len(result.shape) == 1 or result.shape[1] == 1:
				return Vector2(*result) if result.size == 2 else Vector3(*result) if result.size == 3 else Vector4(*result)
			elif result.shape == (3, 3):
				return TransformMatrix2D(result)
			elif result.shape == (4, 4):
				return TransformMatrix3D(result)
			else:
				return result
		else:
			raise TypeError('TransformMatrix indices must be either an integer, slice, or tuple of three indices')

	def __abs__(self) -> TransformMatrix3D:
		"""
		:return: A copy of this matrix with all cells absolute
		"""

		return TransformMatrix3D(abs(self.__matrix__))

	def __round__(self, n: typing.Optional[int] = None) -> TransformMatrix3D:
		"""
		:param n: The number of places to round to
		:return: A copy of this matrix with all cells rounded
		"""

		return TransformMatrix3D(CPU.round(self.__matrix__, n))

	def __add__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(self.__matrix__ + other)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(self.__matrix__ + other.__matrix__)
		else:
			return NotImplemented

	def __sub__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(self.__matrix__ - other)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(self.__matrix__ - other.__matrix__)
		else:
			return NotImplemented

	def __mul__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(self.__matrix__ * other)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(self.__matrix__ * other.__matrix__)
		else:
			return NotImplemented

	def __matmul__(self, other: TransformMatrix3D) -> TransformMatrix3D:
		return TransformMatrix3D(self.__matrix__ @ other.__matrix__) if isinstance(other, TransformMatrix3D) else NotImplemented

	def __truediv__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(self.__matrix__ / other)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(self.__matrix__ / other.__matrix__)
		else:
			return NotImplemented

	def __floordiv__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(self.__matrix__ // other)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(self.__matrix__ // other.__matrix__)
		else:
			return NotImplemented

	def __mod__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(self.__matrix__ % other)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(self.__matrix__ % other.__matrix__)
		else:
			return NotImplemented

	def __pow__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(self.__matrix__ ** other)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(self.__matrix__ ** other.__matrix__)
		else:
			return NotImplemented

	def __radd__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(other + self.__matrix__)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(other.__matrix__ + self.__matrix__)
		else:
			return NotImplemented

	def __rsub__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(other - self.__matrix__)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(other.__matrix__ - self.__matrix__)
		else:
			return NotImplemented

	def __rmul__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(other * self.__matrix__)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(other.__matrix__ * self.__matrix__)
		else:
			return NotImplemented

	def __rmatmul__(self, other: TransformMatrix3D) -> TransformMatrix3D:
		return TransformMatrix3D(other.__matrix__ @ self.__matrix__) if isinstance(other, TransformMatrix3D) else NotImplemented

	def __rtruediv__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(other / self.__matrix__)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(other.__matrix__ / self.__matrix__)
		else:
			return NotImplemented

	def __rfloordiv__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(other // self.__matrix__)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(other.__matrix__ // self.__matrix__)
		else:
			return NotImplemented

	def __rmod__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(other % self.__matrix__)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(other.__matrix__ % self.__matrix__)
		else:
			return NotImplemented

	def __rpow__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(other ** self.__matrix__)
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(other.__matrix__ ** self.__matrix__)
		else:
			return NotImplemented

	def __iadd__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			self.__matrix__ += other
			return self
		elif isinstance(other, TransformMatrix3D):
			self.__matrix__ += other.__matrix__
			return self
		else:
			return NotImplemented

	def __isub__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			self.__matrix__ -= other
			return self
		elif isinstance(other, TransformMatrix3D):
			self.__matrix__ -= other.__matrix__
			return self
		else:
			return NotImplemented

	def __imul__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			self.__matrix__ *= other
			return self
		elif isinstance(other, TransformMatrix3D):
			self.__matrix__ *= other.__matrix__
			return self
		else:
			return NotImplemented

	def __imatmul__(self, other: TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, TransformMatrix3D):
			self.__matrix__ @= other.__matrix__
			return self
		else:
			return NotImplemented

	def __itruediv__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			self.__matrix__ /= other
			return self
		elif isinstance(other, TransformMatrix3D):
			self.__matrix__ /= other.__matrix__
			return self
		else:
			return NotImplemented

	def __ifloordiv__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			self.__matrix__ //= other
			return self
		elif isinstance(other, TransformMatrix3D):
			self.__matrix__ //= other.__matrix__
			return self
		else:
			return NotImplemented

	def __imod__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			self.__matrix__ %= other
			return self
		elif isinstance(other, TransformMatrix3D):
			self.__matrix__ %= other.__matrix__
			return self
		else:
			return NotImplemented

	def __ipow__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			self.__matrix__ **= other
			return self
		elif isinstance(other, TransformMatrix3D):
			self.__matrix__ **= other.__matrix__
			return self
		else:
			return NotImplemented

	def __neg__(self) -> TransformMatrix3D:
		return TransformMatrix3D(-self.__matrix__)

	def __pos__(self) -> TransformMatrix3D:
		return TransformMatrix3D(+self.__matrix__)

	def transform_vector(self, vector: Vector_T) -> Vector_T:
		"""
		Transforms a vector by this transform matrix
		:param vector: The vector to transform
		:return: The transformed vector
		"""

		if isinstance(vector, Vector4):
			result: CPU.ndarray = vector.array.transpose() @ self.array
			return Vector3(*result.transpose())
		elif isinstance(vector, Vector3):
			source: CPU.ndarray = CPU.zeros((4,), CPU.float64)
			source[:3] = vector.array
			result: CPU.ndarray = source.transpose() @ self.array
			return Vector3(*result.transpose()[:3])
		elif isinstance(vector, Vector2):
			source: CPU.ndarray = CPU.zeros((4,), CPU.float64)
			source[:2] = vector.array
			result: CPU.ndarray = source.transpose() @ self.array
			return Vector2(*result.transpose()[:2])
		else:
			raise Exceptions.InvalidArgumentException(TransformMatrix3D.transform_vector, 'vector', type(vector), (Vector2, Vector3, Vector4))

	def transform_vectors(self, vector: Vector_T, *vectors: Vector_T) -> tuple[Vector_T, ...]:
		"""
		Transforms vectors by this transform matrix
		:param vector: The first vector to transform
		:param vectors: The remaining vector to transform
		:return: The transformed vectors
		"""

		vectors: tuple[Vector3, ...] = (vector, *vectors)
		array: NUMPY.ndarray = NUMPY.zeros((len(vectors), 4), NUMPY.float64)

		for i, vector in enumerate(vectors):
			if isinstance(vector, Vector2):
				array[i, :] = (vector.x, vector.y, 0, 1)
			elif isinstance(vector, Vector3):
				array[i, :] = (vector.x, vector.y, vector.z, 1)
			elif isinstance(vector, Vector4):
				array[i, :] = (vector.x, vector.y, vector.z, vector.w)
			else:
				raise Exceptions.InvalidArgumentException(TransformMatrix3D.transform_vector, 'vector', type(vector), (Vector2, Vector3, Vector4))

		result: NUMPY.ndarray = NUMPY.matmul(array, self.array)
		output: list[Vector_T] = []

		for i in range(len(vectors)):
			x, y, z, w = result[i, :]
			vector: Vector_T = vectors[i]

			if isinstance(vector, Vector2):
				output.append(Vector2(float(x), float(y)))
			elif isinstance(vector, Vector3):
				output.append(Vector3(float(x), float(y), float(z)))
			elif isinstance(vector, Vector4):
				output.append(Vector4(float(x), float(y), float(z), float(w)))

		return tuple(output)

	def inversed(self) -> TransformMatrix3D:
		try:
			inverse: CPU.ndarray = CPU.linalg.inv(self.__matrix__)
			return TransformMatrix3D(inverse)
		except numpy.linalg.LinAlgError as e:
			raise ValueError('Matrix is singular') from e

	def transposed(self) -> TransformMatrix3D:
		return TransformMatrix3D((
			self.m11, self.m21, self.m31, self.m41,
			self.m12, self.m22, self.m32, self.m42,
			self.m13, self.m23, self.m33, self.m43,
			self.m14, self.m24, self.m34, self.m44
		))

	@property
	def m11(self) -> float:
		return self[0, 0]

	@property
	def m12(self) -> float:
		return self[0, 1]

	@property
	def m13(self) -> float:
		return self[0, 2]

	@property
	def m14(self) -> float:
		return self[0, 3]

	@property
	def m21(self) -> float:
		return self[1, 0]

	@property
	def m22(self) -> float:
		return self[1, 1]

	@property
	def m23(self) -> float:
		return self[1, 2]

	@property
	def m24(self) -> float:
		return self[1, 3]

	@property
	def m31(self) -> float:
		return self[2, 0]

	@property
	def m32(self) -> float:
		return self[2, 1]

	@property
	def m33(self) -> float:
		return self[2, 2]

	@property
	def m34(self) -> float:
		return self[2, 3]

	@property
	def m41(self) -> float:
		return self[3, 0]

	@property
	def m42(self) -> float:
		return self[3, 1]

	@property
	def m43(self) -> float:
		return self[3, 2]

	@property
	def m44(self) -> float:
		return self[3, 3]

	@property
	def forward(self) -> Vector3:
		return Vector3(*self.__matrix__[0, :-1])

	@property
	def up(self) -> Vector3:
		return Vector3(*self.__matrix__[1, :-1])

	@property
	def right(self) -> Vector3:
		return Vector3(*self.__matrix__[2, :-1])

	@property
	def translation(self) -> Vector3:
		return Vector3(*self.__matrix__[3, :-1])

	@property
	def backward(self) -> Vector3:
		return -self.forward

	@property
	def down(self) -> Vector3:
		return -self.up

	@property
	def left(self) -> Vector3:
		return -self.right

	@property
	def scale(self) -> Vector3:
		return Vector3(self.forward.length(), self.up.length(), self.right.length())

	@property
	def rotation(self) -> CPU.ndarray:
		return self.__matrix__[:3, :3]

	@forward.setter
	def forward(self, vector: Vector3) -> None:
		Misc.raise_ifn(isinstance(vector, Vector3), Exceptions.InvalidArgumentException(None, 'vector', type(vector), (Vector3,)))
		self.__matrix__[0, :3] = vector.array

	@up.setter
	def up(self, vector: Vector3) -> None:
		Misc.raise_ifn(isinstance(vector, Vector3), Exceptions.InvalidArgumentException(None, 'vector', type(vector), (Vector3,)))
		self.__matrix__[1, :3] = vector.array

	@right.setter
	def right(self, vector: Vector3) -> None:
		Misc.raise_ifn(isinstance(vector, Vector3), Exceptions.InvalidArgumentException(None, 'vector', type(vector), (Vector3,)))
		self.__matrix__[2, :3] = vector.array

	@translation.setter
	def translation(self, vector: Vector3) -> None:
		Misc.raise_ifn(isinstance(vector, Vector3), Exceptions.InvalidArgumentException(None, 'vector', type(vector), (Vector3,)))
		self.__matrix__[3, :3] = vector.array

	@backward.setter
	def backward(self, vector: Vector3) -> None:
		self.forward = -vector

	@down.setter
	def down(self, vector: Vector3) -> None:
		self.up = -vector

	@left.setter
	def left(self, vector: Vector3) -> None:
		self.right = -vector

	@rotation.setter
	def rotation(self, rotation: Math.Tensor.Tensor | CPU.ndarray | GPU.ndarray) -> None:
		if isinstance(rotation, Math.Tensor.Tensor):
			assert rotation.dimension == 2 and rotation.dimensions == (3, 3), 'Matrix must be a 3x3 rotation matrix'
			self.__matrix__[0:3, 0:3] = rotation.to_numpy()
		elif isinstance(rotation, (CPU.ndarray, GPU.ndarray)):
			assert rotation.shape == (3, 3), 'Matrix must be a 3x3 rotation matrix'
			self.__matrix__[0:3, 0:3] = rotation
		else:
			raise InvalidArgumentException(None, 'rotation', type(rotation), (Math.Tensor.Tensor, CPU.ndarray, GPU.ndarray))

	@scale.setter
	def scale(self, scale: Vector3) -> None:
		Misc.raise_ifn(isinstance(scale, Vector3), Exceptions.InvalidArgumentException(None, 'scale', type(scale), (Vector3,)))
		x, y, z = scale.components
		self.forward = self.forward.normalized() * x
		self.up = self.up.normalized() * y
		self.right = self.right.normalized() * z

	@property
	def array(self) -> CPU.ndarray:
		"""
		:return: The underlying numpy array
		"""

		return self.__matrix__


class Vector2(typing.SupportsAbs, typing.SupportsFloat, typing.SupportsComplex):
	@classmethod
	def zero(cls, *, is_polar: bool = False) -> Vector2:
		"""
		:param is_polar: Whether the vector is polar
		:return: The zero vector
		"""

		return cls(0, 0)

	@classmethod
	def one(cls, *, is_polar: bool = False) -> Vector2:
		"""
		:param is_polar: Whether the vector is polar
		:return: Vector with components initialized to 1
		"""

		return cls(1, 1)

	@classmethod
	def nan(cls) -> Vector2:
		"""
		:return: A NaN vector
		"""

		return cls(float('nan'), float('nan'))

	@classmethod
	def right(cls) -> Vector2:
		"""
		:return: Vector pointing right (+x) in cartesian space
		"""

		return cls(1, 0)

	@classmethod
	def left(cls) -> Vector2:
		"""
		:return: Vector pointing left (-x) in cartesian space
		"""

		return cls(-1, 0)

	@classmethod
	def up(cls) -> Vector2:
		"""
		:return: Vector pointing up (+y) in cartesian space
		"""

		return cls(0, 1)

	@classmethod
	def down(cls) -> Vector2:
		"""
		:return: Vector pointing down (-y) in cartesian space
		"""

		return cls(0, -1)

	@classmethod
	def sum(cls, vector1: Vector2, vector2: Vector2, *vectors: Vector2) -> Vector2:
		"""
		Sums all vectors
		:param vector1: The first vector
		:param vector2: The second vector
		:param vectors: The remaining vectors
		:return: The sum of all vectors
		"""

		result: Vector2 = cls.zero()
		vectors: tuple[Vector2, ...] = (vector1, vector2, *vectors)

		for vector in vectors:
			if not isinstance(vector, cls):
				raise TypeError(f'One or more vectors is not a {cls.__name__} instance')

			result += vector

		return result

	@classmethod
	def average(cls, vector1: Vector2, vector2: Vector2, *vectors: Vector2) -> Vector2:
		"""
		Averages all vectors
		:param vector1: The first vector
		:param vector2: The second vector
		:param vectors: The remaining vectors
		:return: The average of all vectors
		"""

		result: Vector2 = cls.zero()
		vectors: tuple[Vector2, ...] = (vector1, vector2, *vectors)

		for vector in vectors:
			if not isinstance(vector, cls):
				raise TypeError(f'One or more vectors is not a {cls.__name__} instance')

			result += vector

		return result / len(vectors)

	def __init__(self, x: float, y: float):
		"""
		Class representing a 2D vector
		:param x: The x component
		:param y: The y component
		:raise InvalidArgumentException: If 'x' or 'y' is not a float
		"""

		Misc.raise_ifn(isinstance(x, (int, float)) or (isinstance(x, (CPU.ndarray, GPU.ndarray)) and x.size == 1), Exceptions.InvalidArgumentException(Vector2.__init__, 'x', type(x), (float,)))
		Misc.raise_ifn(isinstance(y, (int, float)) or (isinstance(x, (CPU.ndarray, GPU.ndarray)) and x.size == 1), Exceptions.InvalidArgumentException(Vector2.__init__, 'y', type(y), (float,)))
		self.__components__: CPU.ndarray = CPU.array((x, y), CPU.float64)

	def __eq__(self, other: Vector2) -> bool:
		"""
		:param other: The other vector
		:return: Whether the two vectors are equal
		"""

		return isinstance(other, type(self)) and other.components == self.components

	def __gt__(self, other: Vector2) -> bool:
		"""
		:param other: The other vector
		:return: Whether this vector's square length is greater than other vector's square length
		"""

		return self.length_squared() > other.length_squared() if isinstance(other, type(self)) else NotImplemented

	def __lt__(self, other: Vector2) -> bool:
		"""
		:param other: The other vector
		:return: Whether this vector's square length is lesser than other vector's square length
		"""

		return self.length_squared() < other.length_squared() if isinstance(other, type(self)) else NotImplemented

	def __hash__(self) -> int:
		"""
		:return: The hash code for this vector
		"""

		return hash(self.components)

	def __getitem__(self, index: int | slice) -> float | Vector2:
		"""
		Gets one or more components of this vector
		:param index: The index or indices to get
		:return: The resulting component or sub-vector
		"""

		result: float | CPU.ndarray = self.__components__[index]
		return float(result) if isinstance(result, float) or len(result) == 1 else Vector2(*result)

	def __iter__(self) -> collections.abc.Iterator[float]:
		"""
		:return: An iterator over this vector's components
		"""

		return iter(self.__components__)

	def __repr__(self) -> str:
		"""
		:return: Representation of this vector
		"""

		return str(self)

	def __str__(self) -> str:
		"""
		:return: String representation of this vector
		"""

		return f'〈{self.x}, {self.y}〉'

	def __add__(self, other: float | Vector2) -> Vector2:
		"""
		Adds a number or vector to this vector
		:param other: The other number or vector to add
		:return: The added vector
		"""

		if isinstance(other, (int, float)):
			other = float(other)
			return type(self)(self.x + other, self.y + other)
		elif isinstance(other, Vector2):
			return type(self)(self.x + other.x, self.y + other.y)
		else:
			return NotImplemented

	def __sub__(self, other: float | Vector2) -> Vector2:
		"""
		Subtracts a number or vector from this vector
		:param other: The other number or vector to subtract
		:return: The subtracted vector
		"""

		if isinstance(other, (int, float)):
			other = float(other)
			return type(self)(self.x - other, self.y - other)
		elif isinstance(other, Vector2):
			return type(self)(self.x - other.x, self.y - other.y)
		else:
			return NotImplemented

	def __mul__(self, other: float | Vector2) -> Vector2:
		"""
		Multiplies a number or vector to this vector
		:param other: The other number or vector to multiply
		:return: The multiplied vector
		"""

		if isinstance(other, (int, float)):
			other = float(other)
			return type(self)(self.x * other, self.y * other)
		elif isinstance(other, Vector2):
			return type(self)(self.x * other.x, self.y * other.y)
		else:
			return NotImplemented

	def __truediv__(self, other: float | Vector2) -> Vector2:
		"""
		Divides a number or vector from this vector
		:param other: The other number or vector to divide
		:return: The divided vector
		"""

		if isinstance(other, (int, float)):
			other = float(other)
			return type(self)(self.x / other, self.y / other)
		elif isinstance(other, Vector2):
			return type(self)(self.x / other.x, self.y / other.y)
		else:
			return NotImplemented

	def __radd__(self, other: float | Vector2) -> Vector2:
		"""
		Adds this vector to a number or vector
		:param other: The other number or vector to add to
		:return: The added vector
		"""

		if isinstance(other, (int, float)):
			other = float(other)
			return type(self)(other + self.x, other + self.y)
		elif isinstance(other, Vector2):
			return type(self)(other.x + self.x, other.y + self.y)
		else:
			return NotImplemented

	def __rsub__(self, other: float | Vector2) -> Vector2:
		"""
		Subtracts this vector from a number or vector
		:param other: The other number or vector to subtract from
		:return: The subtracted vector
		"""

		if isinstance(other, (int, float)):
			other = float(other)
			return type(self)(other - self.x, other - self.y)
		elif isinstance(other, Vector2):
			return type(self)(other.x - self.x, other.y - self.y)
		else:
			return NotImplemented

	def __rmul__(self, other: float | Vector2) -> Vector2:
		"""
		Multiplies this vector to a number or vector
		:param other: The other number or vector to multiply to
		:return: The multiplied vector
		"""

		if isinstance(other, (int, float)):
			other = float(other)
			return type(self)(other * self.x, other * self.y)
		elif isinstance(other, Vector2):
			return type(self)(other.x * self.x, other.y * self.y)
		else:
			return NotImplemented

	def __rtruediv__(self, other: float | Vector2) -> Vector2:
		"""
		Divides this vector from a number or vector
		:param other: The other number or vector to divide from
		:return: The divided vector
		"""

		if isinstance(other, (int, float)):
			other = float(other)
			return type(self)(other / self.x, other / self.y)
		elif isinstance(other, Vector2):
			return type(self)(other.x / self.x, other.y / self.y)
		else:
			return NotImplemented

	def __neg__(self) -> Vector2:
		"""
		:return: The negation of this vector
		"""

		return Vector2(-self.x, -self.y)

	def __pos__(self) -> Vector2:
		"""
		:return: A copy of this vector
		"""

		return Vector2(self.x, self.y)

	def __abs__(self) -> Vector2:
		"""
		:return: The absolute value of this vector
		"""

		return Vector2(abs(self.x), abs(self.y))

	def __float__(self) -> float:
		"""
		:return: The length of this vector
		"""

		return self.length()

	def __complex__(self) -> complex:
		"""
		:return: The length of this vector
		"""

		return complex(self.length())

	def length(self) -> float:
		"""
		:return: The length of this vector
		"""

		return math.sqrt(self.length_squared())

	def length_squared(self) -> float:
		"""
		:return: The square length of this vector
		"""

		return self.x * self.x + self.y * self.y

	def dot(self, other: Vector2) -> float:
		"""
		Applies inner dot-product between two vectors
		:param other: The second vector
		:return: The dot product of these two vectors
		:raises InvalidArgumentException: If 'other' is not a 2D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector2), Exceptions.InvalidArgumentException(Vector2.dot, 'other', type(other), (Vector2,)))
		return self.x * other.x + self.y * other.y

	def distance(self, other: Vector2) -> float:
		"""
		Calculates distance between two vectors
		:param other: The second vector
		:return: The distance between these two vectors
		:raises InvalidArgumentException: If 'other' is not a 2D vector
		"""

		return math.sqrt(self.distance_squared(other))

	def distance_squared(self, other: Vector2) -> float:
		"""
		Calculates square distance between two vectors
		:param other: The second vector
		:return: The square distance between these two vectors
		:raises InvalidArgumentException: If 'other' is not a 2D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector2), Exceptions.InvalidArgumentException(Vector2.distance_squared, 'other', type(other), (Vector2,)))
		return (other - self).length_squared()

	def angle(self, other: Vector2) -> float:
		"""
		Calculates the angle between two vectors
		:param other: The second vector
		:return: The angle (in radians) between these two vectors
		:raises InvalidArgumentException: If 'other' is not a 2D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector2), Exceptions.InvalidArgumentException(Vector2.angle, 'other', type(other), (Vector2,)))
		return math.acos(round(self.dot(other) / (self.length() * other.length()), 7))

	def normalized(self) -> Vector2:
		"""
		:return: This vector normalized
		"""

		return self / self.length()

	@property
	def x(self) -> float:
		"""
		:return: The x component of this vector
		"""

		return self[0]

	@property
	def y(self) -> float:
		"""
		:return: The y component of this vector
		"""

		return self[1]

	@property
	def components(self) -> tuple[float, float]:
		"""
		:return: The components of this vector
		"""

		x, y = self.__components__
		return float(x), float(y)

	@property
	def array(self) -> CPU.ndarray:
		"""
		:return: The underlying numpy array
		"""

		return self.__components__


class Vector3(typing.SupportsAbs, typing.SupportsFloat, typing.SupportsComplex):
	@classmethod
	def zero(cls) -> Vector3:
		return cls(0, 0, 0)

	@classmethod
	def one(cls) -> Vector3:
		return cls(1, 1, 1)

	@classmethod
	def nan(cls) -> Vector3:
		"""
		:return: A NaN vector
		"""

		return cls(float('nan'), float('nan'), float('nan'))

	@classmethod
	def forward(cls) -> Vector3:
		return cls(1, 0, 0)

	@classmethod
	def backward(cls) -> Vector3:
		return cls(-1, 0, 0)

	@classmethod
	def up(cls) -> Vector3:
		return cls(0, 1, 0)

	@classmethod
	def down(cls) -> Vector3:
		return cls(0, -1, 0)

	@classmethod
	def right(cls) -> Vector3:
		return cls(0, 0, 1)

	@classmethod
	def left(cls) -> Vector3:
		return cls(0, 0, -1)

	@classmethod
	def sum(cls, vector1: Vector3, vector2: Vector3, *vectors: Vector3) -> Vector3:
		"""
		Sums all vectors
		:param vector1: The first vector
		:param vector2: The second vector
		:param vectors: The remaining vectors
		:return: The sum of all vectors
		"""

		result: Vector3 = Vector3.zero()
		vectors: tuple[Vector3, ...] = (vector1, vector2, *vectors)

		for vector in vectors:
			if not isinstance(vector, Vector3):
				raise TypeError('One or more vectors is not a Vector3 instance')

			result += vector

		return result

	@classmethod
	def average(cls, vector1: Vector3, vector2: Vector3, *vectors: Vector3) -> Vector3:
		"""
		Averages all vectors
		:param vector1: The first vector
		:param vector2: The second vector
		:param vectors: The remaining vectors
		:return: The average of all vectors
		"""

		result: Vector3 = Vector3.zero()
		vectors: tuple[Vector3, ...] = (vector1, vector2, *vectors)

		for vector in vectors:
			if not isinstance(vector, Vector3):
				raise TypeError('One or more vectors is not a Vector2 instance')

			result += vector

		return result / len(vectors)

	def __init__(self, x: float, y: float, z: float):
		Misc.raise_ifn(isinstance(x, (int, float)) or (isinstance(x, (CPU.ndarray, GPU.ndarray)) and x.size == 1), Exceptions.InvalidArgumentException(Vector3.__init__, 'x', type(x), (float,)))
		Misc.raise_ifn(isinstance(y, (int, float)) or (isinstance(x, (CPU.ndarray, GPU.ndarray)) and x.size == 1), Exceptions.InvalidArgumentException(Vector3.__init__, 'y', type(y), (float,)))
		Misc.raise_ifn(isinstance(z, (int, float)) or (isinstance(x, (CPU.ndarray, GPU.ndarray)) and x.size == 1), Exceptions.InvalidArgumentException(Vector3.__init__, 'z', type(z), (float,)))
		self.__components__: CPU.ndarray = CPU.array((float(x), float(y), float(z)), CPU.float64)

	def __hash__(self) -> int:
		return hash(self.components)

	def __getitem__(self, index: int | slice) -> float | Vector2 | Vector3:
		result: float | CPU.ndarray = self.__components__[index]
		return float(result) if isinstance(result, float) or len(result) == 1 else Vector2(*result) if len(result) == 2 else Vector3(*result)

	def __iter__(self) -> collections.abc.Iterator[float]:
		return iter(self.__components__)

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return f'〈{self.x}, {self.y}, {self.z}〉'

	def __add__(self, other: float | Vector3) -> Vector3:
		if not isinstance(other, (int, float, Vector3)):
			return NotImplemented

		x: float = self.x + (other.x if isinstance(other, Vector3) else float(other))
		y: float = self.y + (other.y if isinstance(other, Vector3) else float(other))
		z: float = self.z + (other.z if isinstance(other, Vector3) else float(other))
		return Vector3(x, y, z)

	def __sub__(self, other: float | Vector3) -> Vector3:
		if not isinstance(other, (int, float, Vector3)):
			return NotImplemented

		x: float = self.x - (other.x if isinstance(other, Vector3) else float(other))
		y: float = self.y - (other.y if isinstance(other, Vector3) else float(other))
		z: float = self.z - (other.z if isinstance(other, Vector3) else float(other))
		return Vector3(x, y, z)

	def __mul__(self, other: float | Vector3) -> Vector3:
		if not isinstance(other, (int, float, Vector3)):
			return NotImplemented

		x: float = self.x * (other.x if isinstance(other, Vector3) else float(other))
		y: float = self.y * (other.y if isinstance(other, Vector3) else float(other))
		z: float = self.z * (other.z if isinstance(other, Vector3) else float(other))
		return Vector3(x, y, z)

	def __truediv__(self, other: float | Vector3) -> Vector3:
		if not isinstance(other, (int, float, Vector3)):
			return NotImplemented

		x: float = self.x / (other.x if isinstance(other, Vector3) else float(other))
		y: float = self.y / (other.y if isinstance(other, Vector3) else float(other))
		z: float = self.z / (other.z if isinstance(other, Vector3) else float(other))
		return Vector3(x, y, z)

	def __radd__(self, other: float | Vector3) -> Vector3:
		if not isinstance(other, (int, float, Vector3)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector3) else float(other)) + self.x
		y: float = (other.y if isinstance(other, Vector3) else float(other)) + self.y
		z: float = (other.z if isinstance(other, Vector3) else float(other)) + self.z
		return Vector3(x, y, z)

	def __rsub__(self, other: float | Vector3) -> Vector3:
		if not isinstance(other, (int, float, Vector3)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector3) else float(other)) - self.x
		y: float = (other.y if isinstance(other, Vector3) else float(other)) - self.y
		z: float = (other.z if isinstance(other, Vector3) else float(other)) - self.z
		return Vector3(x, y, z)

	def __rmul__(self, other: float | Vector3) -> Vector3:
		if not isinstance(other, (int, float, Vector3)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector3) else float(other)) * self.x
		y: float = (other.y if isinstance(other, Vector3) else float(other)) * self.y
		z: float = (other.z if isinstance(other, Vector3) else float(other)) * self.z
		return Vector3(x, y, z)

	def __rtruediv__(self, other: float | Vector3) -> Vector3:
		if not isinstance(other, (int, float, Vector3)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector3) else float(other)) / self.x
		y: float = (other.y if isinstance(other, Vector3) else float(other)) / self.y
		z: float = (other.z if isinstance(other, Vector3) else float(other)) / self.z
		return Vector3(x, y, z)

	def __neg__(self) -> Vector3:
		return Vector3(-self.x, -self.y, -self.z)

	def __pos__(self) -> Vector3:
		return Vector3(self.x, self.y, self.z)

	def __abs__(self) -> Vector3:
		"""
		:return: The absolute value of this vector
		"""

		return Vector3(abs(self.x), abs(self.y), abs(self.z))

	def __float__(self) -> float:
		"""
		:return: The length of this vector
		"""

		return self.length()

	def __complex__(self) -> complex:
		"""
		:return: The length of this vector
		"""

		return complex(self.length())

	def length(self) -> float:
		"""
		:return: The length of this vector
		"""

		return math.sqrt(self.length_squared())

	def length_squared(self) -> float:
		"""
		:return: The square length of this vector
		"""

		return self.x * self.x + self.y * self.y + self.z * self.z

	def dot(self, other: Vector3) -> float:
		"""
		Applies inner dot-product between two vectors
		:param other: The second vector
		:return: The dot product of these two vectors
		:raises InvalidArgumentException: If 'other' is not a 3D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector3), Exceptions.InvalidArgumentException(Vector3.dot, 'other', type(other), (Vector3,)))
		return self.x * other.x + self.y * other.y + self.z * other.z

	def distance(self, other: Vector3) -> float:
		"""
		Calculates distance between two vectors
		:param other: The second vector
		:return: The distance between these two vectors
		:raises InvalidArgumentException: If 'other' is not a 3D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector3), Exceptions.InvalidArgumentException(Vector3.distance, 'other', type(other), (Vector3,)))
		return (other - self).length()

	def distance_squared(self, other: Vector3) -> float:
		"""
		Calculates square distance between two vectors
		:param other: The second vector
		:return: The square distance between these two vectors
		:raises InvalidArgumentException: If 'other' is not a 3D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector3), Exceptions.InvalidArgumentException(Vector3.distance_squared, 'other', type(other), (Vector3,)))
		return (other - self).length_squared()

	def angle(self, other: Vector3) -> float:
		"""
		Calculates the angle between two vectors
		:param other: The second vector
		:return: The angle (in radians) between these two vectors
		:raises InvalidArgumentException: If 'other' is not a 3D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector3), Exceptions.InvalidArgumentException(Vector3.angle, 'other', type(other), (Vector3,)))
		return math.acos(round(self.dot(other) / (self.length() * other.length()), 7))

	def normalized(self) -> Vector3:
		"""
		:return: This vector normalized
		"""

		length: float = self.length()
		return self / length

	def cross(self, other: Vector3) -> Vector3:
		"""
		Calculates cross product between two 3D vectors
		:param other: The second vector
		:return: A vector rotated 90 degrees to both vectors
		:raises InvalidArgumentException: If 'other' is not a 3D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector3), Exceptions.InvalidArgumentException(Vector3.cross, 'other', type(other), (Vector3,)))
		a1, a2, a3 = self
		b1, b2, b3 = other
		c1: float = a2 * b3 - a3 * b2
		c2: float = a3 * b1 - a1 * b3
		c3: float = a1 * b2 - a2 * b1
		return Vector3(c1, c2, c3)

	def project(self, other: Vector3 | Plane3D) -> Vector3:
		"""
		Projects this vector onto another vector
		:param other: The second vector
		:return: The projected vector
		:raises InvalidArgumentException: If 'other' is not a vector
		:raises ValueError: If vector dimensions are mismatched
		"""

		if isinstance(other, Vector3):
			return self.dot(other) / other.length_squared() * self
		elif isinstance(other, Plane3D):
			return other.projected_vector(self)
		else:
			raise Exceptions.InvalidArgumentException(Vector3.project, 'other', type(other), (Vector3, Plane3D))

	def rotate_euler(self, x: float, y: float, z: float) -> Vector3:
		"""
		Rotates this vector by the specified Euler angles
		:param x: X angle in radians
		:param y: Y angle in radians
		:param z: Z angle in radians
		:return: The rotated vector
		"""

		return self.rotate(Quaternion3D.from_euler_angles(x, y, z))

	def rotate_axis_angle(self, axis: Vector3, angle: float) -> Vector3:
		"""
		Rotates this vector around an axis using angle
		:param axis: The axis to rotate around
		:param angle: Angle in radians
		:return: The rotated vector
		"""

		return self.rotate(Quaternion3D.from_axis_angle(axis, angle))

	def rotate(self, quaternion: Quaternion3D) -> Vector3:
		"""
		Rotates this vector by the specified quaternion
		:param quaternion: The quaternion to rotate with
		:return: The rotated vector
		"""

		vector: Quaternion3D = Quaternion3D(*self.components, 0)
		vector = ~quaternion @ (vector @ quaternion)
		i, j, k, w = vector
		return Vector3(i, j, k)

	@property
	def x(self) -> float:
		"""
		:return: The x component of this vector
		"""

		return self[0]

	@property
	def y(self) -> float:
		"""
		:return: The y component of this vector
		"""

		return self[1]

	@property
	def z(self) -> float:
		"""
		:return: The z component of this vector
		"""

		return self[2]

	@property
	def components(self) -> tuple[float, float, float]:
		"""
		:return: The components of this vector
		"""

		x, y, z = self.__components__
		return float(x), float(y), float(z)

	@property
	def array(self) -> CPU.ndarray:
		"""
		:return: The underlying numpy array
		"""

		return self.__components__


class Vector4(typing.SupportsAbs, typing.SupportsFloat, typing.SupportsComplex):
	@classmethod
	def zero(cls) -> Vector4:
		return cls(0, 0, 0, 0)

	@classmethod
	def one(cls) -> Vector4:
		return cls(1, 1, 1, 1)

	@classmethod
	def nan(cls) -> Vector4:
		"""
		:return: A NaN vector
		"""

		return cls(float('nan'), float('nan'), float('nan'), float('nan'))

	@classmethod
	def forward(cls) -> Vector4:
		return cls(1,  0, 0, 0)

	@classmethod
	def backward(cls) -> Vector4:
		return cls(-1, 0, 0, 0)

	@classmethod
	def up(cls) -> Vector4:
		return cls(0, 1, 0, 0)

	@classmethod
	def down(cls) -> Vector4:
		return cls(0, -1, 0, 0)

	@classmethod
	def right(cls) -> Vector4:
		return cls(0, 0, 1, 0)

	@classmethod
	def left(cls) -> Vector4:
		return cls(0, 0, -1, 0)

	@classmethod
	def future(cls) -> Vector4:
		return cls(0, 0, 0, 1)

	@classmethod
	def past(cls) -> Vector4:
		return cls(0, 0, 0, -1)

	@classmethod
	def sum(cls, vector1: Vector4, vector2: Vector4, *vectors: Vector4) -> Vector4:
		"""
		Sums all vectors
		:param vector1: The first vector
		:param vector2: The second vector
		:param vectors: The remaining vectors
		:return: The sum of all vectors
		"""

		result: Vector4 = Vector4.zero()
		vectors: tuple[Vector4, ...] = (vector1, vector2, *vectors)

		for vector in vectors:
			if not isinstance(vector, Vector4):
				raise TypeError('One or more vectors is not a Vector4 instance')

			result += vector

		return result

	@classmethod
	def average(cls, vector1: Vector4, vector2: Vector4, *vectors: Vector4) -> Vector4:
		"""
		Averages all vectors
		:param vector1: The first vector
		:param vector2: The second vector
		:param vectors: The remaining vectors
		:return: The average of all vectors
		"""

		result: Vector4 = Vector4.zero()
		vectors: tuple[Vector4, ...] = (vector1, vector2, *vectors)

		for vector in vectors:
			if not isinstance(vector, Vector4):
				raise TypeError('One or more vectors is not a Vector4 instance')

			result += vector

		return result / len(vectors)

	def __init__(self, x: float, y: float, z: float, w: float):
		Misc.raise_ifn(isinstance(x, (int, float)) or (isinstance(x, (CPU.ndarray, GPU.ndarray)) and x.size == 1), Exceptions.InvalidArgumentException(Vector4.__init__, 'x', type(x), (float,)))
		Misc.raise_ifn(isinstance(y, (int, float)) or (isinstance(x, (CPU.ndarray, GPU.ndarray)) and x.size == 1), Exceptions.InvalidArgumentException(Vector4.__init__, 'y', type(y), (float,)))
		Misc.raise_ifn(isinstance(z, (int, float)) or (isinstance(x, (CPU.ndarray, GPU.ndarray)) and x.size == 1), Exceptions.InvalidArgumentException(Vector4.__init__, 'z', type(z), (float,)))
		Misc.raise_ifn(isinstance(w, (int, float)) or (isinstance(x, (CPU.ndarray, GPU.ndarray)) and x.size == 1), Exceptions.InvalidArgumentException(Vector4.__init__, 'w', type(w), (float,)))
		self.__components__: CPU.ndarray = CPU.array((float(x), float(y), float(z), float(w)), CPU.float64)

	def __hash__(self) -> int:
		return hash(self.components)

	def __getitem__(self, index: int | slice) -> float | Vector2 | Vector3 | Vector4:
		result: float | CPU.ndarray = self.__components__[index]
		return float(result) if isinstance(result, float) or len(result) == 1 else Vector2(*result) if len(result) == 2 else Vector3(*result) if len(result) == 3 else Vector4(*result)

	def __iter__(self) -> collections.abc.Iterator[float]:
		return iter(self.__components__)

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return f'〈{self.x}, {self.y}, {self.z}, {self.w}〉'

	def __add__(self, other: float | Vector4) -> Vector4:
		if not isinstance(other, (int, float, Vector4)):
			return NotImplemented

		x: float = self.x + (other.x if isinstance(other, Vector4) else float(other))
		y: float = self.y + (other.y if isinstance(other, Vector4) else float(other))
		z: float = self.z + (other.z if isinstance(other, Vector4) else float(other))
		w: float = self.w + (other.w if isinstance(other, Vector4) else float(other))
		return Vector4(x, y, z, w)

	def __sub__(self, other: float | Vector4) -> Vector4:
		if not isinstance(other, (int, float, Vector4)):
			return NotImplemented

		x: float = self.x - (other.x if isinstance(other, Vector4) else float(other))
		y: float = self.y - (other.y if isinstance(other, Vector4) else float(other))
		z: float = self.z - (other.z if isinstance(other, Vector4) else float(other))
		w: float = self.w - (other.w if isinstance(other, Vector4) else float(other))
		return Vector4(x, y, z, w)

	def __mul__(self, other: float | Vector4) -> Vector4:
		if not isinstance(other, (int, float, Vector4)):
			return NotImplemented

		x: float = self.x * (other.x if isinstance(other, Vector4) else float(other))
		y: float = self.y * (other.y if isinstance(other, Vector4) else float(other))
		z: float = self.z * (other.z if isinstance(other, Vector4) else float(other))
		w: float = self.w * (other.w if isinstance(other, Vector4) else float(other))
		return Vector4(x, y, z, w)

	def __truediv__(self, other: float | Vector4) -> Vector4:
		if not isinstance(other, (int, float, Vector4)):
			return NotImplemented

		x: float = self.x / (other.x if isinstance(other, Vector4) else float(other))
		y: float = self.y / (other.y if isinstance(other, Vector4) else float(other))
		z: float = self.z / (other.z if isinstance(other, Vector4) else float(other))
		w: float = self.w / (other.w if isinstance(other, Vector4) else float(other))
		return Vector4(x, y, z, w)

	def __radd__(self, other: float | Vector4) -> Vector4:
		if not isinstance(other, (int, float, Vector4)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector4) else float(other)) + self.x
		y: float = (other.y if isinstance(other, Vector4) else float(other)) + self.y
		z: float = (other.z if isinstance(other, Vector4) else float(other)) + self.z
		w: float = (other.w if isinstance(other, Vector4) else float(other)) + self.w
		return Vector4(x, y, z, w)

	def __rsub__(self, other: float | Vector4) -> Vector4:
		if not isinstance(other, (int, float, Vector4)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector4) else float(other)) - self.x
		y: float = (other.y if isinstance(other, Vector4) else float(other)) - self.y
		z: float = (other.z if isinstance(other, Vector4) else float(other)) - self.z
		w: float = (other.w if isinstance(other, Vector4) else float(other)) - self.w
		return Vector4(x, y, z, w)

	def __rmul__(self, other: float | Vector4) -> Vector4:
		if not isinstance(other, (int, float, Vector4)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector4) else float(other)) * self.x
		y: float = (other.y if isinstance(other, Vector4) else float(other)) * self.y
		z: float = (other.z if isinstance(other, Vector4) else float(other)) * self.z
		w: float = (other.w if isinstance(other, Vector4) else float(other)) * self.w
		return Vector4(x, y, z, w)

	def __rtruediv__(self, other: float | Vector4) -> Vector4:
		if not isinstance(other, (int, float, Vector4)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector4) else float(other)) / self.x
		y: float = (other.y if isinstance(other, Vector4) else float(other)) / self.y
		z: float = (other.z if isinstance(other, Vector4) else float(other)) / self.z
		w: float = (other.w if isinstance(other, Vector4) else float(other)) / self.w
		return Vector4(x, y, z, w)

	def __neg__(self) -> Vector4:
		return Vector4(-self.x, -self.y, -self.z, -self.w)

	def __pos__(self) -> Vector4:
		return Vector4(self.x, self.y, self.z, self.w)

	def __abs__(self) -> Vector4:
		"""
		:return: The absolute value of this vector
		"""

		return Vector4(abs(self.x), abs(self.y), abs(self.z), abs(self.w))

	def __float__(self) -> float:
		"""
		:return: The length of this vector
		"""

		return self.length()

	def __complex__(self) -> complex:
		"""
		:return: The length of this vector
		"""

		return complex(self.length())

	def length(self) -> float:
		"""
		:return: The length of this vector
		"""

		return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2 + self.w ** 2)

	def length_squared(self) -> float:
		"""
		:return: The square length of this vector
		"""

		return self.x ** 2 + self.y ** 2 + self.z ** 2 + self.w ** 2

	def dot(self, other: Vector4) -> float:
		"""
		Applies inner dot-product between two vectors
		:param other: The second vector
		:return: The dot product of these two vectors
		:raises InvalidArgumentException: If 'other' is not a 4D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector4), Exceptions.InvalidArgumentException(Vector4.dot, 'other', type(other), (Vector4,)))
		return self.x * other.x + self.y * other.y + self.z * other.z + self.w * other.w

	def distance(self, other: Vector4) -> float:
		"""
		Calculates distance between two vectors
		:param other: The second vector
		:return: The distance between these two vectors
		:raises InvalidArgumentException: If 'other' is not a 4D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector4), Exceptions.InvalidArgumentException(Vector4.distance, 'other', type(other), (Vector4,)))
		return (other - self).length()

	def distance_squared(self, other: Vector4) -> float:
		"""
		Calculates square distance between two vectors
		:param other: The second vector
		:return: The square distance between these two vectors
		:raises InvalidArgumentException: If 'other' is not a 4D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector4), Exceptions.InvalidArgumentException(Vector4.distance_squared, 'other', type(other), (Vector4,)))
		return (other - self).length_squared()

	def angle(self, other: Vector4) -> float:
		"""
		Calculates the angle between two vectors
		:param other: The second vector
		:return: The angle (in radians) between these two vectors
		:raises InvalidArgumentException: If 'other' is not a 4D vector
		"""

		Misc.raise_ifn(isinstance(other, Vector4), Exceptions.InvalidArgumentException(Vector4.angle, 'other', type(other), (Vector4,)))
		return math.acos(round(self.dot(other) / (self.length() * other.length()), 7))

	def normalized(self) -> Vector4:
		"""
		:return: This vector normalized
		"""

		length: float = self.length()
		return self / length

	@property
	def x(self) -> float:
		return self[0]

	@property
	def y(self) -> float:
		return self[1]

	@property
	def z(self) -> float:
		return self[2]

	@property
	def w(self) -> float:
		return self[3]

	@property
	def xyz(self) -> Vector3:
		"""
		:return: The x, y, and z components
		"""

		return Vector3(*self.components[:3])

	@property
	def components(self) -> tuple[float, float, float, float]:
		x, y, z, w = self.__components__
		return float(x), float(y), float(z), float(w)

	@property
	def array(self) -> CPU.ndarray:
		"""
		:return: The underlying numpy array
		"""

		return self.__components__


class Quaternion3D:
	@classmethod
	def nan(cls) -> Quaternion3D:
		"""
		:return: A NaN quaternion
		"""

		return cls(float('nan'), float('nan'), float('nan'), float('nan'))

	@classmethod
	def from_axis_angle(cls, axis: Vector3, angle: float) -> Quaternion3D:
		"""
		Creates a 3D quaternion from an axis and angle
		:param axis: The axis
		:param angle: The angle in radians
		:return: The 3D quaternion
		"""

		sin_2: float = math.sin(angle / 2)
		w: float = math.cos(angle / 2)
		i: float = axis.x * sin_2
		j: float = axis.y * sin_2
		k: float = axis.z * sin_2
		return cls(i, j, k, w)

	@classmethod
	def from_transform(cls, matrix: TransformMatrix3D) -> Quaternion3D:
		"""
		Creates a 3D quaternion from a transform matrix's rotation
		:param matrix: The transform matrix
		:return: The 3D quaternion
		"""

		w: float = math.sqrt(1 + matrix.m11 + matrix.m22 + matrix.m33) / 2
		i: float = (matrix.m32 - matrix.m23) / (4 * w)
		j: float = (matrix.m13 - matrix.m31) / (4 * w)
		k: float = (matrix.m21 - matrix.m12) / (4 * w)
		return cls(i, j, k, w)

	@classmethod
	def from_euler_angles(cls, x: float, y: float, z: float) -> Quaternion3D:
		"""
		Creates a 3D quaternion from Euler angles
		:param x: The X angle rotation in radians
		:param y: The Y angle rotation in radians
		:param z: The Z angle rotation in radians
		:return: The 3D quaternion
		"""

		cos_alpha: float = math.cos(z / 2)
		cos_beta: float = math.cos(y / 2)
		cos_gamma: float = math.cos(x / 2)
		sin_alpha: float = math.sin(z / 2)
		sin_beta: float = math.sin(y / 2)
		sin_gamma: float = math.sin(x / 2)

		w: float = cos_alpha * cos_beta * cos_gamma + sin_alpha * sin_beta * sin_gamma
		i: float = cos_alpha * cos_beta * sin_gamma - sin_alpha * sin_beta * cos_gamma
		j: float = cos_alpha * sin_beta * cos_gamma + sin_alpha * cos_beta * sin_gamma
		k: float = sin_alpha * cos_beta * cos_gamma - cos_alpha * sin_beta * sin_gamma
		return cls(i, j, k, w)

	def __init__(self, i: float, j: float, k: float, w: float):
		self.__components__: CPU.ndarray = CPU.array((float(i), float(j), float(k), float(w)), CPU.float64)

	def __hash__(self) -> int:
		return hash(self.components)

	def __getitem__(self, index: int | slice) -> float | Vector2 | Vector3:
		result: float | CPU.ndarray = self.__components__[index]
		return float(result) if isinstance(result, float) or len(result) == 1 else Vector2(*result) if len(result) == 2 else Vector3(*result) if len(result) == 3 else Quaternion3D(*result)

	def __iter__(self) -> collections.abc.Iterator[float]:
		return iter(self.__components__)

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return f'〈〈{self.i}, {self.j}, {self.k}, {self.w}〉〉'

	def __invert__(self) -> Quaternion3D:
		return self.invert()

	def __matmul__(self, other: Quaternion3D) -> Quaternion3D:
		if not isinstance(other, Quaternion3D):
			return NotImplemented

		b1, b2, b3, b0 = self.components
		c1, c2, c3, c0 = other.components
		w: float = b0 * c0 - b1 * c1 - b2 * c2 - b3 * c3
		i: float = b0 * c1 + b1 * c0 - b2 * c3 + b3 * c2
		j: float = b0 * c2 + b1 * c3 + b2 * c0 - b3 * c1
		k: float = b0 * c3 - b1 * c2 + b2 * c1 + b3 * c0
		return Quaternion3D(i, j, k, w)

	def invert(self) -> Quaternion3D:
		"""
		:return: The inverse of this quaternion
		"""

		i, j, k, w = self.components
		return Quaternion3D(-i, -j, -k, w)

	@property
	def i(self) -> float:
		"""
		:return: The i component of this quaternion
		"""

		return self[0]

	@property
	def j(self) -> float:
		"""
		:return: The j component of this quaternion
		"""

		return self[1]

	@property
	def k(self) -> float:
		"""
		:return: The k component of this quaternion
		"""

		return self[2]

	@property
	def w(self) -> float:
		"""
		:return: The w component of this quaternion
		"""

		return self[3]

	@property
	def components(self) -> tuple[float, float, float, float]:
		"""
		:return: The components of this quaternion
		"""

		i, j, k, w = self.__components__
		return float(i), float(j), float(k), float(w)

	@property
	def array(self) -> CPU.ndarray:
		"""
		:return: The underlying numpy array
		"""

		return self.__components__


class Line2D:
	def __init__(self, start: Vector2, end: Vector2):
		"""
		Class representing a line in 2D space
		:param start: The first point
		:param end: The second point
		"""

		Misc.raise_ifn(isinstance(start, Vector2), Exceptions.InvalidArgumentException(Line2D.__init__, 'start', type(start), (Vector2,)))
		Misc.raise_ifn(isinstance(end, Vector2), Exceptions.InvalidArgumentException(Line2D.__init__, 'end', type(end), (Vector2,)))
		self.__start__: Vector2 = start
		self.__end__: Vector2 = end

	@property
	def start(self) -> Vector2:
		"""
		:return: This line's start
		"""

		return self.__start__

	@property
	def end(self) -> Vector2:
		"""
		:return: This line's end
		"""

		return self.__end__


class Line3D:
	def __init__(self, start: Vector3, end: Vector3):
		"""
		Class representing a line in 3D space
		:param start: The first point
		:param end: The second point
		"""

		Misc.raise_ifn(isinstance(start, Vector3), Exceptions.InvalidArgumentException(Line3D.__init__, 'start', type(start), (Vector3,)))
		Misc.raise_ifn(isinstance(end, Vector3), Exceptions.InvalidArgumentException(Line3D.__init__, 'end', type(end), (Vector3,)))
		self.__start__: Vector3 = start
		self.__end__: Vector3 = end

	@property
	def start(self) -> Vector3:
		"""
		:return: This line's start
		"""

		return self.__start__

	@property
	def end(self) -> Vector3:
		"""
		:return: This line's end
		"""

		return self.__end__


class Plane3D:
	@classmethod
	def create_from_normal(cls, normal: Vector3, position: Vector3 = Vector3.zero()) -> Plane3D:
		"""
		Creates a positioned plane using a normal
		:param normal: The plane's normal
		:param position: The plane's world position
		:return: The plane
		"""

		Misc.raise_ifn(isinstance(normal, Vector3), Exceptions.InvalidArgumentException(Plane3D.create_from_normal, 'normal', type(normal), (Vector3,)))
		Misc.raise_ifn(isinstance(position, Vector3), Exceptions.InvalidArgumentException(Plane3D.create_from_normal, 'position', type(position), (Vector3,)))
		return cls(Line3D(position, position + normal))

	def __init__(self, normal: Line3D):
		"""
		Class representing a 3D plane
		:param normal: The plane normal
		"""

		Misc.raise_ifn(isinstance(normal, Line3D), Exceptions.InvalidArgumentException(Plane3D.__init__, 'normal', type(normal), (Line3D,)))
		self.__line__: Line3D = normal

	def projected_vector(self, vector: Vector3) -> Vector3:
		"""
		Projects a vector onto this plane
		:param vector: The vector to project
		:return: The projected vector
		"""

		first: Vector3 = self.normal.project(vector)
		return self.normal - first

	@property
	def normal(self) -> Vector3:
		"""
		:return: This plane's local normal
		"""

		return self.__line__.end - self.__line__.start


Vector_T = Vector2 | Vector3 | Vector4

__all__: list[str] = [
	'NUMPY', 'CPU', 'GPU',
	'TransformMatrix2D', 'TransformMatrix3D',
	'Vector2', 'Vector3', 'Vector4', 'Vector_T',
	'Quaternion3D',
	'Line2D', 'Line3D', 'Plane3D'
]
