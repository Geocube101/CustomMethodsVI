from __future__ import annotations

import typing

from . import Colors
from . import Math
from . import Util
from .. import Exceptions
from .. import Misc


class Material:
	def pixel_at(self, point: Math.Vector2) -> Util.Color:
		"""
		Gets the color at the specified texture coordinate
		:param point: The normalized texture coordinate
		:return: The pixel color
		"""

		return Colors.Transparent


class SimpleMaterial(Material):
	def __init__(self, fill: Util.Color, outline: Util.Color):
		Misc.raise_ifn(isinstance(fill, Util.Color), Exceptions.InvalidArgumentException(SimpleMaterial.__init__, 'fill', type(fill), (Util.Color,)))
		Misc.raise_ifn(isinstance(outline, Util.Color), Exceptions.InvalidArgumentException(SimpleMaterial.__init__, 'outline', type(outline), (Util.Color,)))
		self.__fill__: Util.Color = fill
		self.__outline__: Util.Color = outline

	def pixel_at(self, point: Math.Vector2) -> Util.Color:
		return self.fill

	@property
	def fill(self) -> Util.Color:
		return self.__fill__

	@property
	def outline(self) -> Util.Color:
		return self.__outline__


class TextureMaterial(Material):
	pass


class UVMap:
	@classmethod
	def simple(cls, fill: Util.Color, outline: Util.Color) -> UVMap:
		return cls(SimpleMaterial(fill, outline), Math.TransformMatrix2D.identity())

	def __init__(self, material: Material, matrix: Math.TransformMatrix2D):
		Misc.raise_ifn(isinstance(material, Material), Exceptions.InvalidArgumentException(UVMap.__init__, 'material', type(material), (Material,)))
		Misc.raise_ifn(isinstance(matrix, Math.TransformMatrix2D), Exceptions.InvalidArgumentException(UVMap.__init__, 'matrix', type(matrix), (Math.TransformMatrix2D,)))
		self.__material__: Material = material
		self.__matrix__: Math.TransformMatrix2D = matrix

	def map_coordinate(self, point: Math.Vector2) -> Math.Vector2:
		"""
		Maps a coordinate from face to UV space
		:param point: The geometry point
		:return: The UV point
		"""

		return self.__matrix__.transform_vector(point)

	def pixel_at(self, point: Math.Vector2) -> Util.Color:
		"""
		Gets the color at the specified uv coordinate
		:param point: The normalized UV coordinate
		:return: The pixel color
		"""

		return self.material.pixel_at(self.map_coordinate(point))

	def get_material[M: Material](self, material_type: type[M]) -> typing.Optional[M]:
		material: Material = self.material
		return material if isinstance(material, material_type) else None

	@property
	def material(self) -> Material:
		return self.__material__

	@property
	def matrix(self) -> Math.TransformMatrix2D:
		return self.__matrix__

	@matrix.setter
	def matrix(self, matrix: Math.TransformMatrix2D) -> None:
		Misc.raise_ifn(isinstance(matrix, Math.TransformMatrix2D), Exceptions.InvalidArgumentException(UVMap.matrix.setter, 'matrix', type(matrix), (Math.TransformMatrix2D,)))
		self.__matrix__ = matrix

	@material.setter
	def material(self, material: Material) -> None:
		Misc.raise_ifn(isinstance(material, Material), Exceptions.InvalidArgumentException(UVMap.material.setter, 'material', type(material), (Material,)))
		self.__material__ = material


__all__: list[str] = ['Material', 'SimpleMaterial', 'TextureMaterial', 'UVMap']
