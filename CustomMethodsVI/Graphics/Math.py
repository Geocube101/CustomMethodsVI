from __future__ import annotations

import collections.abc
import math
import numpy
import typing

from .. import Exceptions
from .. import Math
from .. import Misc


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
	def full(cls, value: float) -> TransformMatrix2D:
		"""
		:return: A 3x3 matrix of all one value
		"""

		return cls(Math.Tensor.Tensor.full(float(value), 3, 3))

	@classmethod
	def create_world(cls, right: Vector3, up: Vector3, translation: Vector3) -> TransformMatrix2D:
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
			scale_x, 0, 0, 0,
			0, scale_y, 0, 0,
			0, 0, 0, 1
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

	def __init__(self, matrix: typing.Iterable[float] | Math.Tensor.Tensor):
		"""
		Class representing a 3x3 transform matrix
		- Constructor -
		:param matrix: The matrix or tensor to construct from
		"""

		length: int = ...
		assert (isinstance(matrix, Math.Tensor.Tensor) and (matrix.dimensions == (2, 2) or matrix.dimensions == (3, 3))) or (isinstance(matrix, typing.Iterable) and ((length := len(matrix := tuple(matrix))) == 9 or length == 9) and all(isinstance(x, (int, float)) for x in matrix)), 'Matrix must be either a 2x2 or 3x3 array of floats'

		if (isinstance(matrix, Math.Tensor.Tensor) and matrix.dimensions == (2, 2)) or length == 4:
			m11, m12, m21, m22 = matrix
			self.__matrix__: Math.Tensor.Tensor = Math.Tensor.Tensor((
				(m11, m12, 0),
				(m21, m22, 0),
				(0, 0, 1)
			))
		elif isinstance(matrix, Math.Tensor.Tensor) and matrix.dimensions == (3, 3):
			self.__matrix__ = matrix
		else:
			self.__matrix__: Math.Tensor.Tensor = Math.Tensor.Tensor.shaped(matrix, 3, 3)

	def __hash__(self) -> int:
		return hash(self.__matrix__)

	def __repr__(self) -> str:
		return f'<{TransformMatrix2D.__name__} 3x3 @ {hex(id(self))}>'

	def __str__(self) -> str:
		cells: tuple[str, ...] = tuple(str(cell) for cell in self.__matrix__.flattened())
		c1_length: int = max((len(cells[0]), len(cells[3]), len(cells[6])))
		c2_length: int = max((len(cells[1]), len(cells[4]), len(cells[7])))
		c3_length: int = max((len(cells[2]), len(cells[5]), len(cells[8])))

		return f'''{cells[0].rjust(c1_length, ' ')}, {cells[1].rjust(c2_length, ' ')}, {cells[2].rjust(c3_length, ' ')}
{cells[3].rjust(c1_length, ' ')}, {cells[4].rjust(c2_length, ' ')}, {cells[5].rjust(c3_length, ' ')}
{cells[6].rjust(c1_length, ' ')}, {cells[7].rjust(c2_length, ' ')}, {cells[8].rjust(c3_length, ' ')}
'''

	def __iter__(self) -> typing.Iterator[float]:
		return iter(self.__matrix__)

	def __getitem__(self, index: int | tuple[int | slice, int | slice] | slice) -> Math.Tensor.Tensor | TransformMatrix2D | Vector2 | Vector3 | float:
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
			result: Math.Tensor.Tensor | Math.Vector.Vector | float = self.__matrix__[index]

			if isinstance(result, Math.Tensor.Tensor):
				return TransformMatrix2D(result) if result.dimensions == (3, 3) else result
			elif isinstance(result, Math.Vector.Vector):
				return result[0] if result.dimension == 1 else Vector2(*result) if result.dimension == 2 else Vector3(*result)
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

		return TransformMatrix2D(round(self.__matrix__, n))

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

	def __divmod__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(divmod(self.__matrix__, other))
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(divmod(self.__matrix__, other.__matrix__))
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

	def __rdivmod__(self, other: float | int | TransformMatrix2D) -> TransformMatrix2D:
		if isinstance(other, (float, int)):
			return TransformMatrix2D(divmod(other, self.__matrix__))
		elif isinstance(other, TransformMatrix2D):
			return TransformMatrix2D(divmod(other.__matrix__, self.__matrix__))
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

		m11, m12, m13, m21, m22, m23, m31, m32, m33 = self.__matrix__.flattened()

		if isinstance(vector, Vector3):
			x, y, z = vector
			xt: float = x * m11 + y * m21 + z * m31
			yt: float = x * m12 + y * m22 + z * m32
			zt: float = x * m13 + y * m23 + z * m33
			return Vector3(xt, yt, zt)
		elif isinstance(vector, Vector2):
			x, y = vector
			z: float = 1
			xt: float = x * m11 + y * m21 + z * m31
			yt: float = x * m12 + y * m22 + z * m32
			return Vector2(xt, yt)
		else:
			raise Exceptions.InvalidArgumentException(TransformMatrix3D.transform_vector, 'vector', type(vector), (Vector2, Vector3))

	def inversed(self) -> TransformMatrix2D:
		try:
			inverse: numpy.ndarray = numpy.linalg.inv(self.__matrix__.to_numpy())
			return TransformMatrix2D(inverse.flatten())
		except numpy.linalg.LinAlgError as e:
			raise ValueError('Matrix is singular') from e

	def transposed(self) -> TransformMatrix2D:
		return TransformMatrix2D((
			self.m11, self.m21, self.m31,
			self.m12, self.m22, self.m32,
			self.m13, self.m23, self.m33
		))

	def to_numpy(self) -> numpy.ndarray:
		"""
		:return: This matrix as a numpy array
		"""

		return self.__matrix__.to_numpy()

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
	def rotation(self) -> Math.Tensor.Tensor:
		return self.__matrix__.subtensor(2, 2)

	@right.setter
	def right(self, vector: Vector2) -> None:
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[0], matrix[1] = vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 3, 3)

	@up.setter
	def up(self, vector: Vector2) -> None:
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[3], matrix[4] = vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 3, 3)

	@translation.setter
	def translation(self, vector: Vector2) -> None:
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[6], matrix[7] = vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 3, 3)

	@down.setter
	def down(self, vector: Vector2) -> None:
		self.up = -vector

	@left.setter
	def left(self, vector: Vector2) -> None:
		self.right = -vector

	@rotation.setter
	def rotation(self, rotation: Math.Tensor.Tensor) -> None:
		assert rotation.dimension == 2 and rotation.dimensions == (2, 2), 'Matrix must be a 2x2 rotation matrix'
		m11, m12, m21, m22 = rotation
		m31, m32 = self.translation
		self.__matrix__ = Math.Tensor.Tensor.shaped((
			m11, m12, 0,
			m21, m22, 0,
			m31, m32, 1,
		), 3, 3)

	@scale.setter
	def scale(self, scale: Vector2) -> None:
		x, y = scale.components
		self.right = self.right.normalized() * x
		self.up = self.up.normalized() * y


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
			cos_alpha * cos_beta, cos_alpha * sin_beta * sin_gamma - sin_alpha * cos_gamma, cos_alpha * sin_beta * cos_gamma + sin_alpha * sin_gamma, 0,
			sin_alpha * cos_beta, sin_alpha * sin_beta * sin_gamma + cos_alpha * cos_gamma, sin_alpha * sin_beta * cos_gamma - cos_alpha * sin_gamma, 0,
			-sin_beta, cos_beta * sin_gamma, cos_beta * cos_gamma, 0,
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

	def __init__(self, matrix: typing.Iterable[float] | Math.Tensor.Tensor):
		"""
		Class representing a 4x4 transform matrix
		- Constructor -
		:param matrix: The matrix or tensor to construct from
		"""

		length: int = ...
		assert (isinstance(matrix, Math.Tensor.Tensor) and (matrix.dimensions == (3, 3) or matrix.dimensions == (4, 4))) or (isinstance(matrix, typing.Iterable) and ((length := len(matrix := tuple(matrix))) == 9 or length == 16) and all(isinstance(x, (int, float)) for x in matrix)), 'Matrix must be either a 3x3 or 4x4 array of floats'

		if (isinstance(matrix, Math.Tensor.Tensor) and matrix.dimensions == (3, 3)) or length == 9:
			m11, m12, m13, m21, m22, m23, m31, m32, m33 = matrix
			self.__matrix__: Math.Tensor.Tensor = Math.Tensor.Tensor((
				(m11, m12, m13, 0),
				(m21, m22, m23, 0),
				(m31, m32, m33, 0),
				(0, 0, 0, 1)
			))
		elif isinstance(matrix, Math.Tensor.Tensor) and matrix.dimensions == (4, 4):
			self.__matrix__ = matrix
		else:
			self.__matrix__: Math.Tensor.Tensor = Math.Tensor.Tensor.shaped(matrix, 4, 4)

	def __hash__(self) -> int:
		return hash(self.__matrix__)

	def __repr__(self) -> str:
		return f'<{TransformMatrix3D.__name__} 4x4 @ {hex(id(self))}>'

	def __str__(self) -> str:
		cells: tuple[str, ...] = tuple(str(cell) for cell in self.__matrix__.flattened())
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

	def __getitem__(self, index: int | tuple[int | slice, int | slice] | slice) -> Math.Tensor.Tensor | TransformMatrix3D | Vector2 | Vector3 | Vector4 | float:
		"""
		Gets a sub-matrix, vector row, or cell value from this matrix
		:param index: The positions to retrieve
		:return: The resulting matrix, vector, or cell value
		"""

		if isinstance(index, int):
			return Vector4(*self.__matrix__[index])
		elif isinstance(index, slice):
			return self.__matrix__[index]
		elif isinstance(index, tuple) and len(index := tuple(index)) == 2:
			result: Math.Tensor.Tensor | Math.Vector.Vector | float = self.__matrix__[index]

			if isinstance(result, Math.Tensor.Tensor):
				return TransformMatrix3D(result) if result.dimensions == (4, 4) else result
			elif isinstance(result, Math.Vector.Vector):
				return result[0] if result.dimension == 1 else Vector2(*result) if result.dimension == 2 else Vector3(*result) if result.dimension == 3 else Vector4(*result)
			else:
				return result
		else:
			raise TypeError('TransformMatrix indices must be either an integer, slice, or tuple of two indices')

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

		return TransformMatrix3D(round(self.__matrix__, n))

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

	def __divmod__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(divmod(self.__matrix__, other))
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(divmod(self.__matrix__, other.__matrix__))
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

	def __rdivmod__(self, other: float | int | TransformMatrix3D) -> TransformMatrix3D:
		if isinstance(other, (float, int)):
			return TransformMatrix3D(divmod(other, self.__matrix__))
		elif isinstance(other, TransformMatrix3D):
			return TransformMatrix3D(divmod(other.__matrix__, self.__matrix__))
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

	def transform_vector(self, vector: Vector2 | Vector3 | Vector4) -> Vector2 | Vector3 | Vector4:
		"""
		Transforms a vector by this transform matrix
		:param vector: The vector to transform
		:return: The transformed vector
		"""

		m11, m12, m13, m14, m21, m22, m23, m24, m31, m32, m33, m34, m41, m42, m43, m44 = self.__matrix__.flattened()

		if isinstance(vector, Vector4):
			x, y, z, w = vector
			xt: float = x * m11 + y * m21 + z * m31 + w * m41
			yt: float = x * m12 + y * m22 + z * m32 + w * m42
			zt: float = x * m13 + y * m23 + z * m33 + w * m43
			wt: float = x * m14 + y * m24 + z * m34 + w * m44
			return Vector4(xt, yt, zt, wt)
		elif isinstance(vector, Vector3):
			x, y, z = vector
			w: float = 1
			xt: float = x * m11 + y * m21 + z * m31 + w * m41
			yt: float = x * m12 + y * m22 + z * m32 + w * m42
			zt: float = x * m13 + y * m23 + z * m33 + w * m43
			return Vector3(xt, yt, zt)
		elif isinstance(vector, Vector2):
			x, y = vector
			z: float = 0
			w: float = 1
			xt: float = x * m11 + y * m21 + z * m31 + w * m41
			yt: float = x * m12 + y * m22 + z * m32 + w * m42
			return Vector2(xt, yt)
		else:
			raise Exceptions.InvalidArgumentException(TransformMatrix3D.transform_vector, 'vector', type(vector), (Vector2, Vector3, Vector4))

	def inversed(self) -> TransformMatrix3D:
		try:
			inverse: numpy.ndarray = numpy.linalg.inv(self.__matrix__.to_numpy())
			return TransformMatrix3D(inverse.flatten())
		except numpy.linalg.LinAlgError as e:
			raise ValueError('Matrix is singular') from e

	def transposed(self) -> TransformMatrix3D:
		return TransformMatrix3D((
			self.m11, self.m21, self.m31, self.m41,
			self.m12, self.m22, self.m32, self.m42,
			self.m13, self.m23, self.m33, self.m43,
			self.m14, self.m24, self.m34, self.m44
		))

	def to_numpy(self) -> numpy.ndarray:
		"""
		:return: This matrix as a numpy array
		"""

		return self.__matrix__.to_numpy()

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
	def rotation(self) -> Math.Tensor.Tensor:
		return self.__matrix__.subtensor(3, 3)

	@forward.setter
	def forward(self, vector: Vector3) -> None:
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[0], matrix[1], matrix[2] = vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 4, 4)

	@up.setter
	def up(self, vector: Vector3) -> None:
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[4], matrix[5], matrix[6] = vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 4, 4)

	@right.setter
	def right(self, vector: Vector3) -> None:
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[8], matrix[9], matrix[10] = vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 4, 4)

	@translation.setter
	def translation(self, vector: Vector3) -> None:
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[12], matrix[13], matrix[14] = vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 4, 4)

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
	def rotation(self, rotation: Math.Tensor.Tensor) -> None:
		assert rotation.dimension == 2 and rotation.dimensions == (3, 3), 'Matrix must be a 3x3 rotation matrix'
		m11, m12, m13, m21, m22, m23, m31, m32, m33 = rotation
		m41, m42, m43 = self.translation
		self.__matrix__ = Math.Tensor.Tensor.shaped((
			m11, m12, m13, 0,
			m21, m22, m23, 0,
			m31, m32, m33, 0,
			m41, m42, m43, 1,
		), 4, 4)

	@scale.setter
	def scale(self, scale: Vector3) -> None:
		x, y, z = scale.components
		self.forward = self.forward.normalized() * x
		self.up = self.up.normalized() * y
		self.right = self.right.normalized() * z


class Vector2:
	@classmethod
	def zero(cls) -> Vector2:
		return cls(0, 0)

	@classmethod
	def one(cls) -> Vector2:
		return cls(1, 1)

	@classmethod
	def right(cls) -> Vector2:
		return cls(1, 0)

	@classmethod
	def left(cls) -> Vector2:
		return cls(-1, 0)

	@classmethod
	def up(cls) -> Vector2:
		return cls(0, 1)

	@classmethod
	def down(cls) -> Vector2:
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

		result: Vector2 = Vector2.zero()
		vectors: tuple[Vector2, ...] = (vector1, vector2, *vectors)

		for vector in vectors:
			if not isinstance(vector, Vector2):
				raise TypeError('One or more vectors is not a Vector2 instance')

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

		result: Vector2 = Vector2.zero()
		vectors: tuple[Vector2, ...] = (vector1, vector2, *vectors)

		for vector in vectors:
			if not isinstance(vector, Vector2):
				raise TypeError('One or more vectors is not a Vector2 instance')

			result += vector

		return result / len(vectors)

	def __init__(self, x: float, y: float):
		Misc.raise_ifn(isinstance(x, (int, float)), Exceptions.InvalidArgumentException(Vector2.__init__, 'x', type(x), (float,)))
		Misc.raise_ifn(isinstance(y, (int, float)), Exceptions.InvalidArgumentException(Vector2.__init__, 'y', type(y), (float,)))
		self.__components__: tuple[float, float] = (float(x), float(y))

	def __hash__(self) -> int:
		return hash(self.components)

	def __getitem__(self, index: int | slice) -> float | Vector2:
		result: float | tuple[float, ...] = self.__components__[index]
		return result if isinstance(result, float) else Vector2(*result)

	def __iter__(self) -> collections.abc.Iterator[float]:
		return iter(self.__components__)

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return f'〈{self.x}, {self.y}〉'

	def __add__(self, other: float | Vector2) -> Vector2:
		if not isinstance(other, (int, float, Vector2)):
			return NotImplemented

		x: float = self.x + (other.x if isinstance(other, Vector2) else float(other))
		y: float = self.y + (other.y if isinstance(other, Vector2) else float(other))
		return Vector2(x, y)

	def __sub__(self, other: float | Vector2) -> Vector2:
		if not isinstance(other, (int, float, Vector2)):
			return NotImplemented

		x: float = self.x - (other.x if isinstance(other, Vector2) else float(other))
		y: float = self.y - (other.y if isinstance(other, Vector2) else float(other))
		return Vector2(x, y)

	def __mul__(self, other: float | Vector2) -> Vector2:
		if not isinstance(other, (int, float, Vector2)):
			return NotImplemented

		x: float = self.x * (other.x if isinstance(other, Vector2) else float(other))
		y: float = self.y * (other.y if isinstance(other, Vector2) else float(other))
		return Vector2(x, y)

	def __truediv__(self, other: float | Vector2) -> Vector2:
		if not isinstance(other, (int, float, Vector2)):
			return NotImplemented

		x: float = self.x / (other.x if isinstance(other, Vector2) else float(other))
		y: float = self.y / (other.y if isinstance(other, Vector2) else float(other))
		return Vector2(x, y)

	def __radd__(self, other: float | Vector2) -> Vector2:
		if not isinstance(other, (int, float, Vector2)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector2) else float(other)) + self.x
		y: float = (other.y if isinstance(other, Vector2) else float(other)) + self.y
		return Vector2(x, y)

	def __rsub__(self, other: float | Vector2) -> Vector2:
		if not isinstance(other, (int, float, Vector2)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector2) else float(other)) - self.x
		y: float = (other.y if isinstance(other, Vector2) else float(other)) - self.y
		return Vector2(x, y)

	def __rmul__(self, other: float | Vector2) -> Vector2:
		if not isinstance(other, (int, float, Vector2)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector2) else float(other)) * self.x
		y: float = (other.y if isinstance(other, Vector2) else float(other)) * self.y
		return Vector2(x, y)

	def __rtruediv__(self, other: float | Vector2) -> Vector2:
		if not isinstance(other, (int, float, Vector2)):
			return NotImplemented

		x: float = (other.x if isinstance(other, Vector2) else float(other)) / self.x
		y: float = (other.y if isinstance(other, Vector2) else float(other)) / self.y
		return Vector2(x, y)

	def __neg__(self) -> Vector2:
		return Vector2(-self.x, -self.y)

	def __pos__(self) -> Vector2:
		return Vector2(self.x, self.y)

	def length(self) -> float:
		"""
		:return: The length of this vector
		"""

		return math.sqrt(self.x ** 2 + self.y ** 2)

	def length_squared(self) -> float:
		"""
		:return: The square length of this vector
		"""

		return self.x ** 2 + self.y ** 2

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

		Misc.raise_ifn(isinstance(other, Vector2), Exceptions.InvalidArgumentException(Vector2.distance, 'other', type(other), (Vector2,)))
		return (other - self).length()

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

		length: float = self.length()
		return self / length

	@property
	def x(self) -> float:
		return self[0]

	@property
	def y(self) -> float:
		return self[1]

	@property
	def components(self) -> tuple[float, float]:
		return self.__components__


class Vector3:
	@classmethod
	def zero(cls) -> Vector3:
		return cls(0, 0, 0)

	@classmethod
	def one(cls) -> Vector3:
		return cls(1, 1, 1)

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
		Misc.raise_ifn(isinstance(x, (int, float)), Exceptions.InvalidArgumentException(Vector3.__init__, 'x', type(x), (float,)))
		Misc.raise_ifn(isinstance(y, (int, float)), Exceptions.InvalidArgumentException(Vector3.__init__, 'y', type(y), (float,)))
		Misc.raise_ifn(isinstance(z, (int, float)), Exceptions.InvalidArgumentException(Vector3.__init__, 'z', type(z), (float,)))
		self.__components__: tuple[float, float, float] = (float(x), float(y), float(z))

	def __hash__(self) -> int:
		return hash(self.components)

	def __getitem__(self, index: int | slice) -> float | Vector2 | Vector3:
		result: float | tuple[float, ...] = self.__components__[index]
		return result if isinstance(result, float) else Vector2(*result) if len(result) == 2 else Vector3(*result)

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

	def length(self) -> float:
		"""
		:return: The length of this vector
		"""

		return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

	def length_squared(self) -> float:
		"""
		:return: The square length of this vector
		"""

		return self.x ** 2 + self.y ** 2 + self.z ** 2

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
		c1: typing.Optional[float] = None if a2 is None or b3 is None else (a2 * b3 - a3 * b2)
		c2: typing.Optional[float] = None if a1 is None or b3 is None else (a3 * b1 - a1 * b3)
		c3: typing.Optional[float] = None if a1 is None or b2 is None else (a1 * b2 - a2 * b1)
		return Vector3(c1, c2, c3)

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
	def components(self) -> tuple[float, float, float]:
		return self.__components__


class Vector4:
	@classmethod
	def zero(cls) -> Vector4:
		return cls(0, 0, 0, 0)

	@classmethod
	def one(cls) -> Vector4:
		return cls(1, 1, 1, 1)

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
		Misc.raise_ifn(isinstance(x, (int, float)), Exceptions.InvalidArgumentException(Vector4.__init__, 'x', type(x), (float,)))
		Misc.raise_ifn(isinstance(y, (int, float)), Exceptions.InvalidArgumentException(Vector4.__init__, 'y', type(y), (float,)))
		Misc.raise_ifn(isinstance(z, (int, float)), Exceptions.InvalidArgumentException(Vector4.__init__, 'z', type(z), (float,)))
		Misc.raise_ifn(isinstance(w, (int, float)), Exceptions.InvalidArgumentException(Vector4.__init__, 'w', type(w), (float,)))
		self.__components__: tuple[float, float, float, float] = (float(x), float(y), float(z), float(w))

	def __hash__(self) -> int:
		return hash(self.components)

	def __getitem__(self, index: int | slice) -> float | Vector2 | Vector3 | Vector4:
		result: float | tuple[float, ...] = self.__components__[index]
		return result if isinstance(result, float) else Vector2(*result) if len(result) == 2 else Vector3(*result) if len(result) == 3 else Vector4(*result)

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
		return self.__components__


class Line3D:
	def __init__(self, start: Vector3, end: Vector3):
		Misc.raise_ifn(isinstance(start, Vector3), Exceptions.InvalidArgumentException(Line3D.__init__, 'start', type(start), (Vector3,)))
		Misc.raise_ifn(isinstance(end, Vector3), Exceptions.InvalidArgumentException(Line3D.__init__, 'end', type(end), (Vector3,)))
		self.__start__: Vector3 = start
		self.__end__: Vector3 = end

	@property
	def start(self) -> Vector3:
		return self.__start__

	@property
	def end(self) -> Vector3:
		return self.__end__


Vector_T = Vector2 | Vector3 | Vector4

__all__: list[str] = ['TransformMatrix3D', 'Vector2', 'Vector3', 'Vector4', 'Vector_T']
