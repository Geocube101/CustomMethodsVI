from __future__ import annotations

import math
import typing

from ... import Exceptions
from ... import Math
from ... import Misc


class TransformMatrix:
	"""
	Class representing a 4x4 transform matrix
	"""

	@classmethod
	def identity(cls) -> TransformMatrix:
		"""
		:return: The 4x4 identity matrix
		"""

		return cls(Math.Tensor.Tensor.identity(4, 4))

	@classmethod
	def zero(cls) -> TransformMatrix:
		"""
		:return: A 4x4 matrix of all zeroes
		"""

		return cls(Math.Tensor.Tensor.full(0, 4, 4))

	@classmethod
	def one(cls) -> TransformMatrix:
		"""
		:return: A 4x4 matrix of all ones
		"""

		return cls(Math.Tensor.Tensor.full(1, 4, 4))

	@classmethod
	def full(cls, value: float) -> TransformMatrix:
		"""
		:return: A 4x4 matrix of all one value
		"""

		return cls(Math.Tensor.Tensor.full(float(value), 4, 4))

	@classmethod
	def create_world(cls, forward: Vector3, up: Vector3, translation: Vector3) -> TransformMatrix:
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
	def create_scale(cls, scale_x: float, scale_y: float, scale_z: float) -> TransformMatrix:
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
	def create_rotation(cls, rotation_x: float, rotation_y: float, rotation_z: float) -> TransformMatrix:
		"""
		Creates a rotation matrix
		:param rotation_x: The x-axis scale
		:param rotation_y: The y-axis scale
		:param rotation_z: The z-axis scale
		:return: The rotation matrix
		"""

		cos_alpha: float = math.cos(rotation_y)
		sin_alpha: float = math.sin(rotation_y)
		cos_beta: float = math.cos(rotation_z)
		sin_beta: float = math.sin(rotation_z)
		cos_gamma: float = math.cos(rotation_x)
		sin_gamma: float = math.sin(rotation_x)

		return cls((
			cos_alpha * cos_beta, cos_alpha * sin_beta * sin_gamma - sin_alpha * cos_gamma, cos_alpha * sin_beta * cos_gamma + sin_alpha * sin_gamma, 0,
			sin_alpha * cos_beta, sin_alpha * sin_beta * sin_gamma + cos_alpha * cos_gamma, sin_alpha * sin_beta * cos_gamma - cos_alpha * sin_gamma, 0,
			-sin_beta, cos_beta * sin_gamma, cos_beta * cos_gamma, 0,
			0, 0, 0, 1
		))

	@classmethod
	def create_translation(cls, translation_x: float, translation_y: float, translation_z: float) -> TransformMatrix:
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
	def create_shear(cls, shear_xy: float, shear_xz: float, shear_yx: float, shear_yz: float, shear_zx: float, shear_zy: float) -> TransformMatrix:
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
		return f'<{TransformMatrix.__name__} 4x4 @ {hex(id(self))}>'

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

	def __getitem__(self, index: int | tuple[int | slice, int | slice] | slice) -> Math.Tensor.Tensor | TransformMatrix | Vector2 | Vector3 | Vector4 | float:
		"""
		Gets a sub-matrix, vector row, or cell value from this matrix
		:param index: The positions to retrieve
		:return: The resulting matrix, vector, or cell value
		"""

		if isinstance(index, int):
			return Vector4(self.__matrix__[index])
		elif isinstance(index, slice):
			return self.__matrix__[index]
		elif isinstance(index, tuple) and len(index := tuple(index)) == 2:
			result: Math.Tensor.Tensor | Math.Vector.Vector | float = self.__matrix__[index]

			if isinstance(result, Math.Tensor.Tensor):
				return TransformMatrix(result) if result.dimensions == (4, 4) else result
			elif isinstance(result, Math.Vector.Vector):
				return result[0] if result.dimension == 1 else Vector2(result) if result.dimension == 2 else Vector3(result) if result.dimension == 3 else Vector4(result)
			else:
				return result
		else:
			raise TypeError('TransformMatrix indices must be either an integer, slice, or tuple of two indices')

	def __abs__(self) -> TransformMatrix:
		"""
		:return: A copy of this matrix with all cells absolute
		"""

		return TransformMatrix(abs(self.__matrix__))

	def __round__(self, n: typing.Optional[int] = None) -> TransformMatrix:
		"""
		:param n: The number of places to round to
		:return: A copy of this matrix with all cells rounded
		"""

		return TransformMatrix(round(self.__matrix__, n))

	def __add__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(self.__matrix__ + other)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(self.__matrix__ + other.__matrix__)
		else:
			return NotImplemented

	def __sub__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(self.__matrix__ - other)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(self.__matrix__ - other.__matrix__)
		else:
			return NotImplemented

	def __mul__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(self.__matrix__ * other)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(self.__matrix__ * other.__matrix__)
		else:
			return NotImplemented

	def __matmul__(self, other: TransformMatrix) -> TransformMatrix:
		return TransformMatrix(self.__matrix__ @ other.__matrix__) if isinstance(other, TransformMatrix) else NotImplemented

	def __truediv__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(self.__matrix__ / other)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(self.__matrix__ / other.__matrix__)
		else:
			return NotImplemented

	def __floordiv__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(self.__matrix__ // other)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(self.__matrix__ // other.__matrix__)
		else:
			return NotImplemented

	def __mod__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(self.__matrix__ % other)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(self.__matrix__ % other.__matrix__)
		else:
			return NotImplemented

	def __divmod__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(divmod(self.__matrix__, other))
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(divmod(self.__matrix__, other.__matrix__))
		else:
			return NotImplemented

	def __pow__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(self.__matrix__ ** other)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(self.__matrix__ ** other.__matrix__)
		else:
			return NotImplemented

	def __radd__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(other + self.__matrix__)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(other.__matrix__ + self.__matrix__)
		else:
			return NotImplemented

	def __rsub__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(other - self.__matrix__)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(other.__matrix__ - self.__matrix__)
		else:
			return NotImplemented

	def __rmul__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(other * self.__matrix__)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(other.__matrix__ * self.__matrix__)
		else:
			return NotImplemented

	def __rmatmul__(self, other: TransformMatrix) -> TransformMatrix:
		return TransformMatrix(other.__matrix__ @ self.__matrix__) if isinstance(other, TransformMatrix) else NotImplemented

	def __rtruediv__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(other / self.__matrix__)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(other.__matrix__ / self.__matrix__)
		else:
			return NotImplemented

	def __rfloordiv__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(other // self.__matrix__)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(other.__matrix__ // self.__matrix__)
		else:
			return NotImplemented

	def __rmod__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(other % self.__matrix__)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(other.__matrix__ % self.__matrix__)
		else:
			return NotImplemented

	def __rdivmod__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(divmod(other, self.__matrix__))
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(divmod(other.__matrix__, self.__matrix__))
		else:
			return NotImplemented

	def __rpow__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			return TransformMatrix(other ** self.__matrix__)
		elif isinstance(other, TransformMatrix):
			return TransformMatrix(other.__matrix__ ** self.__matrix__)
		else:
			return NotImplemented

	def __iadd__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			self.__matrix__ += other
			return self
		elif isinstance(other, TransformMatrix):
			self.__matrix__ += other.__matrix__
			return self
		else:
			return NotImplemented

	def __isub__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			self.__matrix__ -= other
			return self
		elif isinstance(other, TransformMatrix):
			self.__matrix__ -= other.__matrix__
			return self
		else:
			return NotImplemented

	def __imul__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			self.__matrix__ *= other
			return self
		elif isinstance(other, TransformMatrix):
			self.__matrix__ *= other.__matrix__
			return self
		else:
			return NotImplemented

	def __imatmul__(self, other: TransformMatrix) -> TransformMatrix:
		if isinstance(other, TransformMatrix):
			self.__matrix__ @= other.__matrix__
			return self
		else:
			return NotImplemented

	def __itruediv__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			self.__matrix__ /= other
			return self
		elif isinstance(other, TransformMatrix):
			self.__matrix__ /= other.__matrix__
			return self
		else:
			return NotImplemented

	def __ifloordiv__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			self.__matrix__ //= other
			return self
		elif isinstance(other, TransformMatrix):
			self.__matrix__ //= other.__matrix__
			return self
		else:
			return NotImplemented

	def __imod__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			self.__matrix__ %= other
			return self
		elif isinstance(other, TransformMatrix):
			self.__matrix__ %= other.__matrix__
			return self
		else:
			return NotImplemented

	def __ipow__(self, other: float | int | TransformMatrix) -> TransformMatrix:
		if isinstance(other, (float, int)):
			self.__matrix__ **= other
			return self
		elif isinstance(other, TransformMatrix):
			self.__matrix__ **= other.__matrix__
			return self
		else:
			return NotImplemented

	def __neg__(self) -> TransformMatrix:
		return TransformMatrix(-self.__matrix__)

	def __pos__(self) -> TransformMatrix:
		return TransformMatrix(+self.__matrix__)

	def transform_vector(self, vector: Vector2 | Vector3 | Vector4) -> Vector2 | Vector3 | Vector4:
		"""
		Transforms a vector by this transform matrix
		:param vector: The vector to transform
		:return: The transformed vector
		"""

		if isinstance(vector, Vector4):
			transformed: Math.Tensor.Tensor = self.__matrix__ @ Math.Tensor.Tensor.shaped(vector, 4, 1)
			return Vector4(transformed.flattened())
		elif isinstance(vector, Vector3):
			transformed: Math.Tensor.Tensor = self.__matrix__ @ Math.Tensor.Tensor.shaped((*vector, 0), 4, 1)
			return Vector3(transformed.flattened()[:3])
		elif isinstance(vector, Vector2):
			transformed: Math.Tensor.Tensor = self.__matrix__ @ Math.Tensor.Tensor.shaped((*vector, 0, 0), 4, 1)
			return Vector2(transformed.flattened()[:2])
		else:
			raise Exceptions.InvalidArgumentException(TransformMatrix.transform_vector, 'vector', type(vector), (Vector3, Vector4))

	def inverse(self) -> TransformMatrix:
		pass

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
	def right(self) -> Vector3:
		return Vector3(*self.__matrix__[0, :-1].components)

	@property
	def up(self) -> Vector3:
		return Vector3(self.__matrix__[1, :-1])

	@property
	def forward(self) -> Vector3:
		return Vector3(self.__matrix__[2, :-1])

	@property
	def translation(self) -> Vector3:
		return Vector3(*self.__matrix__[3, :-1])

	@property
	def left(self) -> Vector3:
		return -self.right

	@property
	def down(self) -> Vector3:
		return -self.up

	@property
	def backward(self) -> Vector3:
		return -self.forward

	@property
	def scale(self) -> Vector3:
		return Vector3(self.right.length(), self.up.length(), self.forward.length())

	@property
	def rotation(self) -> Math.Tensor.Tensor:
		return self.__matrix__.subtensor(3, 3)

	@right.setter
	def right(self, vector: Math.Vector.Vector) -> None:
		assert vector.dimension == 3, 'Vector must be 3D'
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[0], matrix[1], matrix[2] = vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 4, 4)

	@up.setter
	def up(self, vector: Math.Vector.Vector) -> None:
		assert vector.dimension == 3, 'Vector must be 3D'
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[4], matrix[5], matrix[6] = vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 4, 4)

	@forward.setter
	def forward(self, vector: Math.Vector.Vector) -> None:
		assert vector.dimension == 3, 'Vector must be 3D'
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[8], matrix[9], matrix[10] = vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 4, 4)

	@translation.setter
	def translation(self, vector: Math.Vector.Vector) -> None:
		assert vector.dimension == 3, 'Vector must be 3D'
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[12], matrix[13], matrix[14] = vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 4, 4)

	@left.setter
	def left(self, vector: Math.Vector.Vector) -> None:
		assert vector.dimension == 3, 'Vector must be 3D'
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[0], matrix[1], matrix[2] = -vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 4, 4)

	@down.setter
	def down(self, vector: Math.Vector.Vector) -> None:
		assert vector.dimension == 3, 'Vector must be 3D'
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[4], matrix[5], matrix[6] = -vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 4, 4)

	@backward.setter
	def backward(self, vector: Math.Vector.Vector) -> None:
		assert vector.dimension == 3, 'Vector must be 3D'
		matrix: list[float | None] = list(self.__matrix__.flattened())
		matrix[8], matrix[9], matrix[10] = -vector
		self.__matrix__ = Math.Tensor.Tensor.shaped(matrix, 4, 4)

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
	def scale(self, scale: Math.Vector.Vector) -> None:
		x, y, z = scale.components
		self.right = self.right.normalized() * x
		self.up = self.up.normalized() * y
		self.forward = self.forward.normalized() * z


class Vector2(Math.Vector.Vector):
	@classmethod
	def zero(cls) -> Vector2:
		return cls(0, 0)

	@classmethod
	def one(cls) -> Vector2:
		return cls(1, 1, 1)

	@classmethod
	def right(cls) -> Vector2:
		return cls(1, 0, 0)

	@classmethod
	def left(cls) -> Vector2:
		return cls(-1, 0, 0)

	@classmethod
	def up(cls) -> Vector2:
		return cls(0, 1)

	@classmethod
	def down(cls) -> Vector2:
		return cls(0, -1)

	def __init__(self, vector: typing.Iterable[float] | Math.Vector.Vector | float, *components: float):
		if isinstance(vector, Math.Vector.Vector):
			assert len(components) == 0, 'Extra data after argument: \'vector\''
			assert vector.dimension == 2 and vector.complete, 'Vector must be a complete 2D vector'
			super().__init__(vector)
		elif isinstance(vector, typing.Iterable):
			assert len(components) == 0, 'Extra data after argument: \'vector\''
			assert len(vector := tuple(vector)) == 2 and all(isinstance(x, (float, int)) for x in vector), 'Vector must be an iterable of floats of length 2'
			super().__init__(vector)
		elif len(components) == 0:
			super().__init__(vector, vector, vector)
		else:
			components: tuple[float, ...] = (vector, *components)
			assert len(components) == 2 and all(isinstance(x, (float, int)) for x in components), 'Vector must be an iterable of floats of length 2'
			super().__init__(components)


class Vector3(Math.Vector.Vector):
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

	def __init__(self, vector: typing.Iterable[float] | Math.Vector.Vector | float, *components: float):
		if isinstance(vector, Vector2):
			assert len(components) == 1, 'Missing \'Z\' for 3D vector'
			super().__init__(*vector.components, components[0])
		elif isinstance(vector, Math.Vector.Vector):
			assert len(components) == 0, 'Extra data after argument: \'vector\''
			assert vector.dimension == 3 and vector.complete, 'Vector must be a complete 3D vector'
			super().__init__(vector)
		elif isinstance(vector, typing.Iterable):
			assert len(components) == 0, 'Extra data after argument: \'vector\''
			assert len(vector := tuple(vector)) == 3 and all(isinstance(x, (float, int)) for x in vector), 'Vector must be an iterable of floats of length 3'
			super().__init__(vector)
		elif len(components) == 0:
			super().__init__(vector, vector, vector)
		else:
			components: tuple[float, ...] = (vector, *components)
			assert len(components) == 3 and all(isinstance(x, (float, int)) for x in components), 'Vector must be an iterable of floats of length 3'
			super().__init__(components)


class Vector4(Math.Vector.Vector):
	@classmethod
	def zero(cls) -> Vector4:
		return cls(0, 0, 0, 0)

	@classmethod
	def one(cls) -> Vector4:
		return cls(1, 1, 1, 0)

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

	def __init__(self, vector: typing.Iterable[float] | Math.Vector.Vector | float, *components: float):
		if isinstance(vector, Vector2):
			assert len(components) == 2, 'Missing \'Z\' or \'W\' for 4D vector'
			super().__init__(*vector.components, components[0], components[1])
		elif isinstance(vector, Vector3):
			assert len(components) == 1, 'Missing \'W\' for 4D vector'
			super().__init__(*vector.components, components[0])
		elif isinstance(vector, Math.Vector.Vector):
			assert len(components) == 0, 'Extra data after argument: \'vector\''
			assert vector.dimension == 4 and vector.complete, 'Vector must be a complete 4D vector'
			super().__init__(vector)
		elif isinstance(vector, typing.Iterable):
			assert len(components) == 0, 'Extra data after argument: \'vector\''
			assert len(vector := tuple(vector)) == 4 and all(isinstance(x, (float, int)) for x in vector), 'Vector must be an iterable of floats of length 4'
			super().__init__(vector)
		elif len(components) == 0:
			super().__init__(vector, vector, vector, vector)
		else:
			components: tuple[float, ...] = (vector, *components)
			assert len(components) == 4 and all(isinstance(x, (float, int)) for x in components), 'Vector must be an iterable of floats of length 4'
			super().__init__(components)
