from __future__ import annotations

import math

from . import Math
from .. import Exceptions


class Coordinate2D(Math.Vector2):
	def to_coordinate_system[U: Coordinate2D](self, system: type[U]) -> U:
		"""
		Converts this coordinate to the target coordinate system\n
		This method searches for applicable converters using the following:\n
		- Searches for methods with the format "__convert_{name}__" where {name} is the class name or value returned from 'name' property\n
		- Searches for methods with the format "to_{name}" where {name} is the value returned from 'name' property\n
		:param system: The system to convert to
		:return: The converted coordinate
		"""

		if not issubclass(system, type(self)):
			raise TypeError(f'Target coordinate system must be a sub-class of {type(self).__name__}')
		elif system is type(self):
			return self
		elif callable(converter := vars(self).get(f'__convert_{system.__name__}__')):
			return converter()
		elif callable(converter := vars(self).get(f'__convert_{system.name}__')):
			return converter()
		elif callable(converter := vars(self).get(f'to_{system.name}')):
			return converter()
		else:
			raise ValueError(f'Unable to cast this coordinate to the target coordinate system: \'{system.name}\'')

	def length(self) -> float:
		"""
		:return: The distance from the origin
		"""

		return math.sqrt(self.length_squared())

	def length_squared(self) -> float:
		"""
		:return: The squared distance from the origin
		"""

		return super().length_squared()

	@property
	def vector(self) -> Math.Vector2:
		"""
		:return: This coordinate as a vector
		"""

		return Math.Vector2(*self)

	@property
	def name(self) -> str:
		"""
		The name of this coordinate system used to assist with conversions
		:return: This coordinate system's name
		"""

		return ...


class CartesianCoordinate2D(Coordinate2D):
	def to_polar(self) -> PolarCoordinate2D:
		"""
		Converts this vector to polar coordinates
		:return: The polar vector
		"""

		return PolarCoordinate2D(self.length(), math.atan2(self.y, self.x))

	@property
	def name(self) -> str:
		return 'cartesian'


class PolarCoordinate2D(Coordinate2D):
	def __init__(self, radius: float, theta: float):
		super().__init__(abs(float(radius)), float(theta) % (2 * math.pi))

	def __neg__(self) -> PolarCoordinate2D:
		return PolarCoordinate2D(self.radius, -self.theta)

	def length(self) -> float:
		return self.radius

	def length_squared(self) -> float:
		return self.radius * self.radius

	def dot(self, other: Coordinate2D) -> float:
		if not isinstance(other, PolarCoordinate2D) and isinstance(other, Coordinate2D):
			other = other.to_coordinate_system(type(self))
		elif not isinstance(other, PolarCoordinate2D):
			raise Exceptions.InvalidArgumentException(parameter_name='other')

		return self.radius * other.radius * math.cos(self.theta - other.theta)

	def distance_squared(self, other: Coordinate2D) -> float:
		if not isinstance(other, PolarCoordinate2D) and isinstance(other, Coordinate2D):
			other = other.to_coordinate_system(type(self))
		elif not isinstance(other, PolarCoordinate2D):
			raise Exceptions.InvalidArgumentException(parameter_name='other')

		r1_2: float = self.length_squared()
		r2_2: float = other.length_squared()
		return r1_2 + r2_2 - 2 * self.radius * other.radius * math.cos(self.theta - other.theta)

	def angle(self, other: Coordinate2D) -> float:
		if isinstance(other, PolarCoordinate2D):
			return abs(self.theta - other.theta)
		elif isinstance(other, Coordinate2D):
			return abs(self.theta - other.to_coordinate_system(type(self)).theta)
		else:
			raise Exceptions.InvalidArgumentException(parameter_name='other')

	def normalized(self) -> PolarCoordinate2D:
		return PolarCoordinate2D(1, self.theta)

	def to_cartesian(self) -> CartesianCoordinate2D:
		"""
		Converts this coordinate to cartesian coordinates
		:return: The cartesian vector
		"""

		return CartesianCoordinate2D(self.radius * math.cos(self.theta), self.radius * math.sin(self.theta))

	@property
	def radius(self) -> float:
		"""
		:return: The radius component of this vector
		"""

		return self[0]

	@property
	def theta(self) -> float:
		"""
		:return: The theta component of this vector
		"""

		return self[1]

	@property
	def name(self) -> str:
		return 'polar'


__all__: list[str] = [
	'Coordinate2D', 'CartesianCoordinate2D', 'PolarCoordinate2D'
]
