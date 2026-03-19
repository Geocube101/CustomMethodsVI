from __future__ import annotations

import colorsys

from . import Math

from .. import Exceptions
from .. import Misc


class Object3D:
	"""
	Class representing an object with a world matrix in 3D space
	"""

	def __init__(self, world_matrix: Math.TransformMatrix3D):
		"""
		Class representing an object with a world matrix in 3D space
		:param world_matrix: The object's world matrix
		:raises InvalidArgumentException: If 'world_matrix' is not a TransformMatrix3D instance
		"""

		Misc.raise_ifn(isinstance(world_matrix, Math.TransformMatrix3D), Exceptions.InvalidArgumentException(Transformable.__init__, 'world_matrix', type(world_matrix), (Math.TransformMatrix3D,)))
		self.__world_matrix__: Math.TransformMatrix3D = world_matrix

	@property
	def world_matrix(self) -> Math.TransformMatrix3D:
		"""
		:return: The object's world matrix
		"""

		return self.__world_matrix__

	@world_matrix.setter
	def world_matrix(self, matrix: Math.TransformMatrix3D) -> None:
		"""
		Sets this object's world matrix
		:param matrix: The new world matrix
		:raises InvalidArgumentException: If 'matrix' is not a TransformMatrix3D instance
		"""

		Misc.raise_ifn(isinstance(matrix, Math.TransformMatrix3D), Exceptions.InvalidArgumentException(Object3D.world_matrix.setter, 'matrix', type(matrix), (Math.TransformMatrix3D,)))
		self.__world_matrix__ = matrix


class Scalable(Object3D):
	"""
	Class representing an object that can be scaled
	"""

	def scale[T: Scalable](self: T, x_scale: float, y_scale: float, z_scale: float) -> T:
		"""
		Scales this object by the specified axis amounts
		:param x_scale: The x scale
		:param y_scale: The y scale
		:param z_scale: The z scale
		:return:
		"""

		self.world_matrix = Math.TransformMatrix3D.create_scale(x_scale, y_scale, z_scale) @ self.world_matrix
		return self


class Rotatable(Object3D):
	"""
	Class representing an object that can be rotated
	"""

	def rotate[T: Rotatable](self: T, x_rotation: float, y_rotation: float, z_rotation: float) -> T:
		"""
		Rotates this object by the specified axis amounts
		:param x_rotation: The x rotation in radians
		:param y_rotation: The y rotation in radians
		:param z_rotation: The z rotation in radians
		:return:
		"""

		self.world_matrix = Math.TransformMatrix3D.create_rotation(x_rotation, y_rotation, z_rotation) @ self.world_matrix
		return self


class Translatable(Object3D):
	"""
	Class representing an object that can be translated
	"""

	def translate[T: Translatable](self: T, x_translation: float, y_translation: float, z_translation: float) -> T:
		"""
		Translates this object by the specified axis amounts
		:param x_translation: The x translation
		:param y_translation: The y translation
		:param z_translation: The z translation
		:return:
		"""

		self.world_matrix = Math.TransformMatrix3D.create_translation(x_translation, y_translation, z_translation) @ self.world_matrix
		return self


class Transformable(Scalable, Rotatable, Translatable):
	"""
	Class representing an object that can be scaled, rotated, and translated
	"""


class Color:
	"""
	Class representing a color
	"""

	@classmethod
	def from_vector3(cls, vector: Math.Vector3, alpha: int = 0xFF) -> Color:
		"""
		Constructs a color from a normalized Vector3
		:param vector: The vector
		:param alpha: The alpha
		:return: The color
		"""

		Misc.raise_ifn(isinstance(vector, Math.Vector3), Exceptions.InvalidArgumentException(cls.from_vector3, 'vector', type(vector), (Math.Vector3,)))
		Misc.raise_ifn(isinstance(alpha, int), Exceptions.InvalidArgumentException(cls.from_vector3, 'alpha', type(alpha), (int,)))

		return cls(
			round(vector.x * 0xFF),
			round(vector.y * 0xFF),
			round(vector.z * 0xFF),
			alpha
		)

	@classmethod
	def from_vector4(cls, vector: Math.Vector4) -> Color:
		"""
		Constructs a color from a normalized Vector4
		:param vector: The vector
		:return: The color
		"""

		Misc.raise_ifn(isinstance(vector, Math.Vector4), Exceptions.InvalidArgumentException(cls.from_vector3, 'vector', type(vector), (Math.Vector4,)))

		return cls(
			round(vector.x * 0xFF),
			round(vector.y * 0xFF),
			round(vector.z * 0xFF),
			round(vector.w * 0xFF),
		)

	@classmethod
	def from_int(cls, int32: int) -> Color:
		"""
		Creates a color from a 32-bit integer
		:param int32: The 32-bit positive integer
		:return: The color
		"""

		Misc.raise_ifn(isinstance(int32, int), Exceptions.InvalidArgumentException(cls.from_int, 'int32', type(int32), (int,)))
		a: int = int32 & 0xFF
		b: int = (int32 >> 8) & 0xFF
		g: int = (int32 >> 16) & 0xFF
		r: int = (int32 >> 24) & 0xFF
		return cls(r, g, b, a)

	@classmethod
	def from_hex(cls, color: str) -> Color:
		"""
		Creates a color from a hex string
		:param color: The hex string
		:return: The color
		"""

		return cls.from_int(int(color.lstrip('#'), 16))

	def __init__(self, r: int, g: int, b: int, a: int):
		"""
		Class representing a color
		:param r: The red component (0-255)
		:param g: The green component (0-255)
		:param b: The blue component (0-255)
		:param a: The alpha component (0-255)
		"""

		Misc.raise_ifn(isinstance(r, int), Exceptions.InvalidArgumentException(Color.__init__, 'r', type(r), (int,)))
		Misc.raise_ifn(isinstance(g, int), Exceptions.InvalidArgumentException(Color.__init__, 'g', type(r), (int,)))
		Misc.raise_ifn(isinstance(b, int), Exceptions.InvalidArgumentException(Color.__init__, 'b', type(r), (int,)))
		Misc.raise_ifn(isinstance(a, int), Exceptions.InvalidArgumentException(Color.__init__, 'a', type(r), (int,)))
		Misc.raise_ifn(0 <= (r := int(r)) <= 0xFF, ValueError('Red outside of range [0, 255]'))
		Misc.raise_ifn(0 <= (g := int(g)) <= 0xFF, ValueError('Green outside of range [0, 255]'))
		Misc.raise_ifn(0 <= (b := int(b)) <= 0xFF, ValueError('Blue outside of range [0, 255]'))
		Misc.raise_ifn(0 <= (a := int(a)) <= 0xFF, ValueError('Alpha outside of range [0, 255]'))
		self.__color__: tuple[int, int, int, int] = (r, g, b, a)

	def __str__(self) -> str:
		return f'#{self.r:02X}{self.g:02X}{self.b:02X}{self.a:02X}'

	def __add__(self, other: Color | int) -> Color:
		if isinstance(other, Color):
			return Color(*[Misc.clamp(a + b, 0x00, 0xFF) for a, b in zip(self.rgba, other.rgba)])
		elif isinstance(other, int):
			return Color(*[Misc.clamp(a + other, 0x00, 0xFF) for a in self.rgba])
		else:
			return NotImplemented

	def __sub__(self, other: Color | int) -> Color:
		if isinstance(other, Color):
			return Color(*[Misc.clamp(a - b, 0x00, 0xFF) for a, b in zip(self.rgba, other.rgba)])
		elif isinstance(other, int):
			return Color(*[Misc.clamp(a - other, 0x00, 0xFF) for a in self.rgba])
		else:
			return NotImplemented

	def __mul__(self, other: Math.Vector4 | Math.Vector3 | int | float) -> Color:
		if isinstance(other, Math.Vector4):
			return Color(*[Misc.clamp(a * b, 0x00, 0xFF) for a, b in zip(self.rgba, other)])
		elif isinstance(other, Math.Vector3):
			return Color(*[Misc.clamp(a * b, 0x00, 0xFF) for a, b in zip(self.rgba, Math.Vector4(*other, 1))])
		elif isinstance(other, (float, int)):
			return Color(*[Misc.clamp(round(a * other), 0x00, 0xFF) for a in self.rgba])
		else:
			return NotImplemented

	def __truediv__(self, other: Math.Vector4 | Math.Vector3 | int | float) -> Color:
		if isinstance(other, Math.Vector4):
			return Color(*[Misc.clamp(a / b, 0x00, 0xFF) for a, b in zip(self.rgba, other)])
		elif isinstance(other, Math.Vector3):
			return Color(*[Misc.clamp(a / b, 0x00, 0xFF) for a, b in zip(self.rgba, Math.Vector4(*other, 1))])
		elif isinstance(other, (float, int)):
			return Color(*[Misc.clamp(round(a / other), 0x00, 0xFF) for a in self.rgba])
		else:
			return NotImplemented

	def __floordiv__(self, other: Math.Vector4 | Math.Vector3 | int | float) -> Color:
		if isinstance(other, Math.Vector4):
			return Color(*[Misc.clamp(a // b, 0x00, 0xFF) for a, b in zip(self.rgba, other)])
		elif isinstance(other, Math.Vector3):
			return Color(*[Misc.clamp(a // b, 0x00, 0xFF) for a, b in zip(self.rgba, Math.Vector4(*other, 1))])
		elif isinstance(other, (float, int)):
			return Color(*[Misc.clamp(int(a // other), 0x00, 0xFF) for a in self.rgba])
		else:
			return NotImplemented

	def __radd__(self, other: Color | int) -> Color:
		if isinstance(other, Color):
			return Color(*[Misc.clamp(b + a, 0x00, 0xFF) for a, b in zip(self.rgba, other.rgba)])
		elif isinstance(other, int):
			return Color(*[Misc.clamp(other + a, 0x00, 0xFF) for a in self.rgba])
		else:
			return NotImplemented

	def __rsub__(self, other: Color | int) -> Color:
		if isinstance(other, Color):
			return Color(*[Misc.clamp(b - a, 0x00, 0xFF) for a, b in zip(self.rgba, other.rgba)])
		elif isinstance(other, int):
			return Color(*[Misc.clamp(other - a, 0x00, 0xFF) for a in self.rgba])
		else:
			return NotImplemented

	def __rmul__(self, other: Math.Vector4 | Math.Vector3 | int | float) -> Color:
		if isinstance(other, Math.Vector4):
			return Color(*[Misc.clamp(b * a, 0x00, 0xFF) for a, b in zip(self.rgba, other)])
		elif isinstance(other, Math.Vector3):
			return Color(*[Misc.clamp(b * a, 0x00, 0xFF) for a, b in zip(self.rgba, Math.Vector4(*other, 1))])
		elif isinstance(other, (float, int)):
			return Color(*[Misc.clamp(round(other * a), 0x00, 0xFF) for a in self.rgba])
		else:
			return NotImplemented

	def __rtruediv__(self, other: Math.Vector4 | Math.Vector3 | int | float) -> Color:
		if isinstance(other, Math.Vector4):
			return Color(*[Misc.clamp(b / a, 0x00, 0xFF) for a, b in zip(self.rgba, other)])
		elif isinstance(other, Math.Vector3):
			return Color(*[Misc.clamp(b / a, 0x00, 0xFF) for a, b in zip(self.rgba, Math.Vector4(*other, 1))])
		elif isinstance(other, (float, int)):
			return Color(*[Misc.clamp(round(other / a), 0x00, 0xFF) for a in self.rgba])
		else:
			return NotImplemented

	def __rfloordiv__(self, other: Math.Vector4 | Math.Vector3 | int | float) -> Color:
		if isinstance(other, Math.Vector4):
			return Color(*[Misc.clamp(b // a, 0x00, 0xFF) for a, b in zip(self.rgba, other)])
		elif isinstance(other, Math.Vector3):
			return Color(*[Misc.clamp(b // a, 0x00, 0xFF) for a, b in zip(self.rgba, Math.Vector4(*other, 1))])
		elif isinstance(other, (float, int)):
			return Color(*[Misc.clamp(int(other // a), 0x00, 0xFF) for a in self.rgba])
		else:
			return NotImplemented

	def to_integer32(self) -> int:
		"""
		:return: This color packed into a 32-bit integer
		"""

		return (self.r << 24) | (self.g << 16) | (self.b << 8) | self.a

	def to_vector4(self) -> Math.Vector4:
		"""
		:return: The normalized Vector4
		"""

		return Math.Vector4(self.r / 0xFF, self.g / 0xFF, self.b / 0xFF, self.a / 0xFF)

	def to_hsva(self) -> tuple[int, int, int, int]:
		r, g, b, a = self.__color__
		h, s, v = colorsys.rgb_to_hsv(r / 0xFF, g / 0xFF, b / 0xFF)
		return round(h * 360), round(s * 100), round(v * 100), a

	@property
	def r(self) -> int:
		"""
		:return: The red component
		"""

		return self.__color__[0]

	@property
	def g(self) -> int:
		"""
		:return: The green component
		"""

		return self.__color__[1]

	@property
	def b(self) -> int:
		"""
		:return: The blue component
		"""

		return self.__color__[2]

	@property
	def a(self) -> int:
		"""
		:return: The alpha component
		"""

		return self.__color__[3]

	@property
	def rgb(self) -> tuple[int, int, int]:
		"""
		:return: This color as an RGB tuple
		"""

		r, g, b, a = self.__color__
		return r, g, b

	@property
	def bgr(self) -> tuple[int, int, int]:
		"""
		:return: This color as a BGR tuple
		"""

		r, g, b, a = self.__color__
		return b, g, r

	@property
	def rgba(self) -> tuple[int, int, int, int]:
		"""
		:return: This color as an RGBA tuple
		"""

		return self.__color__

	@property
	def bgra(self) -> tuple[int, int, int, int]:
		"""
		:return: This color as a BGRA tuple
		"""

		r, g, b, a = self.__color__
		return b, g, r, a


__all__: list[str] = ['Object3D', 'Scalable', 'Rotatable', 'Translatable', 'Transformable', 'Color']
