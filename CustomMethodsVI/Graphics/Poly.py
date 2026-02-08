from __future__ import annotations

import collections.abc
import typing

from . import Math
from . import Material
from . import Util
from .. import Exceptions
from .. import Misc
from .. import Stream


class Triangle3D:
	"""
	Class representing a single triangle in 3D space
	"""

	def __init__(self, point1: Math.Vector3, point2: Math.Vector3, point3: Math.Vector3, uv_mat: typing.Optional[Material.UVMap] = None):
		"""
		Class representing a single triangle in 3D space
		:param point1: The first vertex
		:param point2: The second vertex
		:param point3: The third vertex
		:param uv_mat: The UV material to render with
		:raises InvalidArgumentException: If any argument is invalid
		"""

		Misc.raise_ifn(isinstance(point1, Math.Vector3), Exceptions.InvalidArgumentException(Triangle3D.__init__, 'point1', type(point1), (Math.Vector3,)))
		Misc.raise_ifn(isinstance(point2, Math.Vector3), Exceptions.InvalidArgumentException(Triangle3D.__init__, 'point2', type(point2), (Math.Vector3,)))
		Misc.raise_ifn(isinstance(point3, Math.Vector3), Exceptions.InvalidArgumentException(Triangle3D.__init__, 'point3', type(point3), (Math.Vector3,)))
		Misc.raise_ifn(uv_mat is None or uv_mat is ... or isinstance(uv_mat, Material.UVMap), Exceptions.InvalidArgumentException(Triangle3D.__init__, 'uv', type(uv_mat), (Material.UVMap,)))
		self.__points__: tuple[Math.Vector3, Math.Vector3, Math.Vector3] = (point1, point2, point3)
		self.__uv__: typing.Optional[Material.UVMap] = None if uv_mat is ... or uv_mat is None else uv_mat

	def __hash__(self) -> int:
		return hash(self.points)

	def __eq__(self, other: Triangle3D) -> bool:
		return isinstance(other, Triangle3D) and self.points == other.points

	def compute_normal(self) -> Math.Vector3:
		"""
		Computes this triangle's facing normal
		:return: The computed normal
		"""

		p1, p2, p3 = self.points
		dir1: Math.Vector3 = p2 - p1
		dir2: Math.Vector3 = p3 - p1
		return dir1.cross(dir2)

	def compute_center(self) -> Math.Vector3:
		"""
		Computes this triangle's center of area
		:return: The midpoint of all three vertices
		"""

		p1, p2, p3 = self.points
		return (p1 + p2 + p3) / 3

	def transform(self, matrix: Math.TransformMatrix3D) -> Triangle3D:
		"""
		Transforms this triangle by the specified transform matrix
		:param matrix: The transform matrix
		:return: The transformed  triangle
		"""

		return Triangle3D(*[matrix.transform_vector(point) for point in self.points])

	@property
	def points(self) -> tuple[Math.Vector3, Math.Vector3, Math.Vector3]:
		"""
		:return: The three vertices of this triangle
		"""

		return self.__points__

	@property
	def material(self) -> typing.Optional[Material.UVMap]:
		return self.__uv__

	@material.setter
	def material(self, uv: typing.Optional[Material.UVMap]) -> None:
		Misc.raise_ifn(uv is None or uv is ... or isinstance(uv, Material.UVMap), Exceptions.InvalidArgumentException(Triangle3D.material.setter, 'uv', type(uv), (Material.UVMap,)))
		self.__uv__ = None if uv is ... or uv is None else uv


class PolyShape3D(Util.Transformable):
	"""
	Class representing a shape in 3D space
	"""

	@classmethod
	def create_cube[T: PolyShape3D](cls: type[T], position: Math.Vector3, extents: Math.Vector3, uv_mat: typing.Optional[Material.UVMap] = None) -> T:
		return cls(
			Math.TransformMatrix3D.create_scale(*extents) @ Math.TransformMatrix3D.create_world(Math.Vector3.forward(), Math.Vector3.up(), position),
			(
				Triangle3D(
					Math.Vector3(0.5, 0.5, 0.5),
					Math.Vector3(0.5, 0.5, -0.5),
					Math.Vector3(-0.5, 0.5, 0.5),
					uv_mat
				),
				Triangle3D(
					Math.Vector3(-0.5, 0.5, -0.5),
					Math.Vector3(0.5, 0.5, -0.5),
					Math.Vector3(-0.5, 0.5, 0.5),
					uv_mat
				),
				Triangle3D(
					Math.Vector3(0.5, -0.5, 0.5),
					Math.Vector3(0.5, -0.5, -0.5),
					Math.Vector3(-0.5, -0.5, 0.5),
					uv_mat
				),
				Triangle3D(
					Math.Vector3(-0.5, -0.5, -0.5),
					Math.Vector3(0.5, -0.5, -0.5),
					Math.Vector3(-0.5, -0.5, 0.5),
					uv_mat
				),
				Triangle3D(
					Math.Vector3(0.5, -0.5, -0.5),
					Math.Vector3(-0.5, -0.5, -0.5),
					Math.Vector3(-0.5, 0.5, -0.5),
					uv_mat
				),
				Triangle3D(
					Math.Vector3(0.5, -0.5, -0.5),
					Math.Vector3(0.5, 0.5, -0.5),
					Math.Vector3(-0.5, 0.5, -0.5),
					uv_mat
				),
				Triangle3D(
					Math.Vector3(-0.5, -0.5, -0.5),
					Math.Vector3(-0.5, -0.5, 0.5),
					Math.Vector3(-0.5, 0.5, 0.5),
					uv_mat
				),
				Triangle3D(
					Math.Vector3(-0.5, -0.5, -0.5),
					Math.Vector3(-0.5, 0.5, -0.5),
					Math.Vector3(-0.5, 0.5, 0.5),
					uv_mat
				),
				Triangle3D(
					Math.Vector3(-0.5, -0.5, 0.5),
					Math.Vector3(0.5, -0.5, 0.5),
					Math.Vector3(0.5, 0.5, 0.5),
					uv_mat
				),
				Triangle3D(
					Math.Vector3(-0.5, -0.5, 0.5),
					Math.Vector3(-0.5, 0.5, 0.5),
					Math.Vector3(0.5, 0.5, 0.5),
					uv_mat
				),
				Triangle3D(
					Math.Vector3(0.5, -0.5, 0.5),
					Math.Vector3(0.5, -0.5, -0.5),
					Math.Vector3(0.5, 0.5, -0.5),
					uv_mat
				),
				Triangle3D(
					Math.Vector3(0.5, -0.5, 0.5),
					Math.Vector3(0.5, 0.5, 0.5),
					Math.Vector3(0.5, 0.5, -0.5),
					uv_mat
				)
			)
		)

	def __init__(self, world_matrix: Math.TransformMatrix3D, triangles: collections.abc.Iterable[Triangle3D]):
		"""
		Class representing a shape in 3D space
		:param world_matrix: The shape's world matrix
		:param triangles: The triangles that compose this shape's mesh
		"""

		Misc.raise_ifn(isinstance(triangles, collections.abc.Iterable), Exceptions.InvalidArgumentException(PolyShape3D.__init__, 'triangles', type(triangles), (Math.Vector3,)))
		Misc.raise_ifn(len(triangles := tuple(triangles)) > 0 and all(isinstance(x, Triangle3D) for x in triangles), ValueError('Triangles list is empty or invalid'))
		self.__triangles__: tuple[Triangle3D, ...] = triangles
		super().__init__(world_matrix)

	def __hash__(self) -> int:
		return hash(self.triangles)

	def __eq__(self, other: PolyShape3D) -> bool:
		return isinstance(other, PolyShape3D) and self.triangles == other.triangles

	def get_vertices(self) -> collections.abc.Iterator[Math.Vector3]:
		"""
		:return: The vertices of this mesh with world matrix applied
		"""

		return Stream.LinqStream(self.get_triangles()).transform_many(lambda tri: tri.points).distinct()

	def get_triangles(self) -> collections.abc.Iterator[Triangle3D]:
		"""
		:return: The triangles of this mesh with world matrix applied
		"""

		for triangle in self.triangles:
			p1, p2, p3 = triangle.points
			p1 = self.__world_matrix__.transform_vector(p1)
			p2 = self.__world_matrix__.transform_vector(p2)
			p3 = self.__world_matrix__.transform_vector(p3)
			yield Triangle3D(p1, p2, p3, triangle.material)

	@property
	def triangles(self) -> tuple[Triangle3D, ...]:
		"""
		:return: The raw, untransformed triangles of this mesh
		"""

		return self.__triangles__


__all__: list[str] = ['Triangle3D', 'PolyShape3D']
