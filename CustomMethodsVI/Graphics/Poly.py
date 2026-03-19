from __future__ import annotations

import collections.abc
import math
import typing

from . import Math
from . import Material
from . import Util
from .. import Exceptions
from .. import Misc
from .. import Stream


class Polygon3D:
	"""
	Class representing a single n-gon in 3D space
	"""

	def __init__(self, *points: Math.Vector3, uv_mat: typing.Optional[Material.UVMap] = None, invert_normal: bool = False):
		"""
		Class representing a single triangle in 3D space
		:param points: The vertices of this n-gon
		:param uv_mat: The UV material to render with
		:raises InvalidArgumentException: If any argument is invalid
		"""

		invalid_point: type = Stream.LinqStream(points).transform(lambda p: type(p)).filter(lambda t: not issubclass(t, Math.Vector3)).first_or_default()
		Misc.raise_ifn(invalid_point is None, Exceptions.InvalidArgumentException(Polygon3D.__init__, 'points', invalid_point, (Math.Vector3,)))
		Misc.raise_ifn(uv_mat is None or uv_mat is ... or isinstance(uv_mat, Material.UVMap), Exceptions.InvalidArgumentException(Polygon3D.__init__, 'uv', type(uv_mat), (Material.UVMap,)))
		Misc.raise_ifn(len(points) >= 3, ValueError(f'N-Gon must contain at least three points, got {len(points)}'))
		p1, p2, p3, *p = points
		dir1: Math.Vector3 = (p2 - p1)
		dir2: Math.Vector3 = (p3 - p1)
		normal: Math.Vector3 = dir1.cross(dir2).normalized() if dir1.angle(dir2) != 0 else Math.Vector3.zero()
		self.__points__: tuple[Math.Vector3, ...] = tuple(points)
		self.__uv__: typing.Optional[Material.UVMap] = None if uv_mat is ... or uv_mat is None else uv_mat
		self.__center__: Math.Vector3 = Math.Vector3.average(*points)
		self.__invert_normal__: bool = bool(invert_normal)
		self.__normal__: Math.Vector3 = -normal if self.is_normal_inverted else normal

	def __hash__(self) -> int:
		return hash(self.points)

	def __eq__(self, other: Polygon3D) -> bool:
		return isinstance(other, Polygon3D) and self.points == other.points

	def closest_vertex_to(self, point: Math.Vector3) -> Math.Vector3:
		"""
		Calculates the closest vertex to the specified point
		:param point: The point
		:return: The closest vertex
		"""

		return Stream.LinqStream(self.points).sort(lambda p: p.distance_squared(point)).first()

	def farthest_vertex_from(self, point: Math.Vector3) -> Math.Vector3:
		"""
		Calculates the farthest vertex from the specified point
		:param point: The point
		:return: The farthest vertex
		"""

		return Stream.LinqStream(self.points).sort(lambda p: p.distance_squared(point), reverse=True).first()

	def transform(self, matrix: Math.TransformMatrix3D) -> Polygon3D:
		"""
		Transforms this n-gon by the specified transform matrix
		:param matrix: The transform matrix
		:return: The transformed  n-gon
		"""

		return Polygon3D(*[matrix.transform_vector(point) for point in self.points], uv_mat=self.material, invert_normal=self.is_normal_inverted)

	@property
	def is_normal_inverted(self) -> bool:
		"""
		:return: Whether this triangle's normal is inverted
		"""

		return self.__invert_normal__

	@property
	def center(self) -> Math.Vector3:
		"""
		:return: This triangle's average midpoint
		"""

		return self.__center__

	@property
	def normal(self) -> Math.Vector3:
		"""
		:return: This triangle's facing normal
		"""

		return self.__normal__

	@property
	def points(self) -> tuple[Math.Vector3, ...]:
		"""
		:return: The vertices of this n-gon
		"""

		return self.__points__

	@property
	def material(self) -> typing.Optional[Material.UVMap]:
		return self.__uv__

	@material.setter
	def material(self, uv: typing.Optional[Material.UVMap]) -> None:
		Misc.raise_ifn(uv is None or uv is ... or isinstance(uv, Material.UVMap), Exceptions.InvalidArgumentException(Polygon3D.material.setter, 'uv', type(uv), (Material.UVMap,)))
		self.__uv__ = None if uv is ... or uv is None else uv


class Triangle3D(Polygon3D):
	def __init__(self, point1: Math.Vector3, point2: Math.Vector3, point3: Math.Vector3, *, uv_mat: typing.Optional[Material.UVMap] = None, invert_normal: bool = False):
		"""
		Class representing a single triangle in 3D space
		:param point1: The first vertex
		:param point2: The second vertex
		:param point3: The third vertex
		:param uv_mat: The UV material to render with
		:raises InvalidArgumentException: If any argument is invalid
		"""

		super().__init__(point1, point2, point3, uv_mat=uv_mat, invert_normal=invert_normal)


class Quadrangle3D(Polygon3D):
	def __init__(self, point1: Math.Vector3, point2: Math.Vector3, point3: Math.Vector3, point4: Math.Vector3, *, uv_mat: typing.Optional[Material.UVMap] = None, invert_normal: bool = False):
		"""
		Class representing a single quadrangle in 3D space
		:param point1: The first vertex
		:param point2: The second vertex
		:param point3: The third vertex
		:param point4: The fourth vertex
		:param uv_mat: The UV material to render with
		:raises InvalidArgumentException: If any argument is invalid
		"""

		super().__init__(point1, point2, point3, point4, uv_mat=uv_mat, invert_normal=invert_normal)

	def triangulate_faces(self) -> tuple[Triangle3D, Triangle3D]:
		"""
		Triangles this quad into two triangular faces
		:return: The triangles
		"""

		p1, p2, p3, p4 = self.points
		return Triangle3D(p1, p2, p3, uv_mat=self.material, invert_normal=self.is_normal_inverted), Triangle3D(p1, p4, p3, uv_mat=self.material, invert_normal=not self.is_normal_inverted)


class Mesh3D(Util.Transformable):
	"""
	Class representing a mesh in 3D space
	"""

	@classmethod
	def create_cube(cls, position: Math.Vector3, uv_mat: typing.Optional[Material.UVMap] = None) -> Mesh3D:
		return cls(
			Math.TransformMatrix3D.create_world(Math.Vector3.forward(), Math.Vector3.up(), position),
			(
				Quadrangle3D(
					Math.Vector3(0.5, 0.5, 0.5),
					Math.Vector3(-0.5, 0.5, 0.5),
					Math.Vector3(-0.5, 0.5, -0.5),
					Math.Vector3(0.5, 0.5, -0.5),
					uv_mat=uv_mat,
					invert_normal=True
				),
				Quadrangle3D(
					Math.Vector3(0.5, -0.5, 0.5),
					Math.Vector3(-0.5, -0.5, 0.5),
					Math.Vector3(-0.5, -0.5, -0.5),
					Math.Vector3(0.5, -0.5, -0.5),
					uv_mat=uv_mat,
					invert_normal=False
				),
				Quadrangle3D(
					Math.Vector3(0.5, -0.5, 0.5),
					Math.Vector3(0.5, 0.5, 0.5),
					Math.Vector3(-0.5, 0.5, 0.5),
					Math.Vector3(-0.5, -0.5, 0.5),
					uv_mat=uv_mat,
					invert_normal=False
				),
				Quadrangle3D(
					Math.Vector3(0.5, -0.5, -0.5),
					Math.Vector3(0.5, 0.5, -0.5),
					Math.Vector3(-0.5, 0.5, -0.5),
					Math.Vector3(-0.5, -0.5, -0.5),
					uv_mat=uv_mat,
					invert_normal=True
				),
				Quadrangle3D(
					Math.Vector3(0.5, -0.5, -0.5),
					Math.Vector3(0.5, 0.5, -0.5),
					Math.Vector3(0.5, 0.5, 0.5),
					Math.Vector3(0.5, -0.5, 0.5),
					uv_mat=uv_mat,
					invert_normal=False
				),
				Quadrangle3D(
					Math.Vector3(-0.5, -0.5, -0.5),
					Math.Vector3(-0.5, 0.5, -0.5),
					Math.Vector3(-0.5, 0.5, 0.5),
					Math.Vector3(-0.5, -0.5, 0.5),
					uv_mat=uv_mat,
					invert_normal=True
				),
			)
		)

	@classmethod
	def create_pyramid(cls, position: Math.Vector3, uv_mat: typing.Optional[Material.UVMap] = None) -> Mesh3D:
		return cls(
			Math.TransformMatrix3D.create_world(Math.Vector3.forward(), Math.Vector3.up(), position),
			(
				Quadrangle3D(
					Math.Vector3(0.5, -0.5, 0.5),
					Math.Vector3(-0.5, -0.5, 0.5),
					Math.Vector3(-0.5, -0.5, -0.5),
					Math.Vector3(0.5, -0.5, -0.5),
					uv_mat=uv_mat,
					invert_normal=False
				),
				Triangle3D(
					Math.Vector3(0.5, -0.5, 0.5),
					Math.Vector3(-0.5, -0.5, 0.5),
					Math.Vector3(0, 0.5, 0),
					uv_mat=uv_mat,
					invert_normal=True
				),
				Triangle3D(
					Math.Vector3(0.5, -0.5, -0.5),
					Math.Vector3(-0.5, -0.5, -0.5),
					Math.Vector3(0, 0.5, 0),
					uv_mat=uv_mat,
					invert_normal=False
				),
				Triangle3D(
					Math.Vector3(0.5, -0.5, 0.5),
					Math.Vector3(0.5, -0.5, -0.5),
					Math.Vector3(0, 0.5, 0),
					uv_mat=uv_mat,
					invert_normal=False
				),
				Triangle3D(
					Math.Vector3(-0.5, -0.5, 0.5),
					Math.Vector3(-0.5, -0.5, -0.5),
					Math.Vector3(0, 0.5, 0),
					uv_mat=uv_mat,
					invert_normal=True
				)
			)
		)

	@classmethod
	def create_tetrahedron(cls, position: Math.Vector3, uv_mat: typing.Optional[Material.UVMap] = None) -> Mesh3D:
		theta120: float = math.radians(120)
		theta240: float = math.radians(240)
		sin120: float = math.sin(theta120)
		cos120: float = math.cos(theta120)
		sin240: float = math.sin(theta240)
		cos240: float = math.cos(theta240)

		return cls(
			Math.TransformMatrix3D.create_world(Math.Vector3.forward(), Math.Vector3.up(), position),
			(
				Triangle3D(
					Math.Vector3(1, -0.5, 0),
					Math.Vector3(cos120, -0.5, sin120),
					Math.Vector3(0, 0.5, 0),
					uv_mat=uv_mat,
					invert_normal=True
				),
				Triangle3D(
					Math.Vector3(1, -0.5, 0),
					Math.Vector3(cos240, -0.5, sin240),
					Math.Vector3(0, 0.5, 0),
					uv_mat=uv_mat,
					invert_normal=False
				),
				Triangle3D(
					Math.Vector3(cos120, -0.5, sin120),
					Math.Vector3(cos240, -0.5, sin240),
					Math.Vector3(0, 0.5, 0),
					uv_mat=uv_mat,
					invert_normal=True
				),
				Triangle3D(
					Math.Vector3(cos120, -0.5, sin120),
					Math.Vector3(cos240, -0.5, sin240),
					Math.Vector3(1, -0.5, 0),
					uv_mat=uv_mat,
					invert_normal=False
				),
			)
		)

	@classmethod
	def create_octahedron(cls, position: Math.Vector3, uv_mat: typing.Optional[Material.UVMap] = None) -> Mesh3D:
		h: float = math.radians(45)

		return cls(
			Math.TransformMatrix3D.create_world(Math.Vector3.forward(), Math.Vector3.up(), position),
			(
				Triangle3D(
					Math.Vector3(0.5, 0, -0.5),
					Math.Vector3(0.5, 0, 0.5),
					Math.Vector3(0, h, 0),
					uv_mat=uv_mat,
					invert_normal=True
				),
				Triangle3D(
					Math.Vector3(-0.5, 0, -0.5),
					Math.Vector3(-0.5, 0, 0.5),
					Math.Vector3(0, h, 0),
					uv_mat=uv_mat,
					invert_normal=False
				),
				Triangle3D(
					Math.Vector3(0.5, 0, 0.5),
					Math.Vector3(-0.5, 0, 0.5),
					Math.Vector3(0, h, 0),
					uv_mat=uv_mat,
					invert_normal=True
				),
				Triangle3D(
					Math.Vector3(0.5, 0, -0.5),
					Math.Vector3(-0.5, 0, -0.5),
					Math.Vector3(0, h, 0),
					uv_mat=uv_mat,
					invert_normal=False
				),
				Triangle3D(
					Math.Vector3(0.5, 0, -0.5),
					Math.Vector3(0.5, 0, 0.5),
					Math.Vector3(0, -h, 0),
					uv_mat=uv_mat,
					invert_normal=False
				),
				Triangle3D(
					Math.Vector3(-0.5, 0, -0.5),
					Math.Vector3(-0.5, 0, 0.5),
					Math.Vector3(0, -h, 0),
					uv_mat=uv_mat,
					invert_normal=True
				),
				Triangle3D(
					Math.Vector3(0.5, 0, 0.5),
					Math.Vector3(-0.5, 0, 0.5),
					Math.Vector3(0, -h, 0),
					uv_mat=uv_mat,
					invert_normal=False
				),
				Triangle3D(
					Math.Vector3(0.5, 0, -0.5),
					Math.Vector3(-0.5, 0, -0.5),
					Math.Vector3(0, -h, 0),
					uv_mat=uv_mat,
					invert_normal=True
				),
			)
		)

	@classmethod
	def create_cylinder(cls, position: Math.Vector3, count: int = 32, uv_mat: typing.Optional[Material.UVMap] = None) -> Mesh3D:
		Misc.raise_ifn(isinstance(count, int), Exceptions.InvalidArgumentException(cls.create_cylinder, 'count', type(count), (int,)))
		Misc.raise_if((count := int(count)) < 3, ValueError(f'Cylinder must have a vertex count of at least 3; got \'{count}\''))
		delta: float = math.radians(360 / count)
		lateral_points: tuple[Math.Vector3, ...] = tuple(Math.Vector3(math.cos(delta * i), 0, math.sin(delta * i)) for i in range(count))
		offset: Math.Vector3 = Math.Vector3(0, 0.5, 0)
		top: Polygon3D = Polygon3D(*[point + offset for point in lateral_points], uv_mat=uv_mat, invert_normal=True)
		bottom: Polygon3D = Polygon3D(*[point - offset for point in lateral_points], uv_mat=uv_mat)
		faces: list[Polygon3D] = []

		for index_1 in range(count):
			index_2: int = (index_1 + 1) % count
			face: Polygon3D = Polygon3D(
				top.points[index_1], top.points[index_2], bottom.points[index_2], bottom.points[index_1],
				uv_mat=uv_mat,
				invert_normal=False
			)
			faces.append(face)

		return cls(
			Math.TransformMatrix3D.create_world(Math.Vector3.forward(), Math.Vector3.up(), position), (top, bottom, *faces)
		)

	def __init__(self, world_matrix: Math.TransformMatrix3D, polygons: collections.abc.Iterable[Polygon3D]):
		"""
		Class representing a mesh in 3D space
		:param world_matrix: The mesh's world matrix
		:param polygons: The polygons that compose this mesh
		"""

		Misc.raise_ifn(isinstance(polygons, collections.abc.Iterable), Exceptions.InvalidArgumentException(Mesh3D.__init__, 'polygons', type(polygons), (Math.Vector3,)))
		Misc.raise_ifn(len(polygons := tuple(polygons)) > 0 and all(isinstance(x, Polygon3D) for x in polygons), ValueError('Polygons list is empty or invalid'))
		self.__polygons__: tuple[Polygon3D, ...] = tuple(polygon for polygon in polygons if polygon.normal.length() > 0)
		super().__init__(world_matrix)

	def __hash__(self) -> int:
		return hash(self.polygons)

	def __eq__(self, other: Mesh3D) -> bool:
		return isinstance(other, Mesh3D) and self.polygons == other.polygons

	def get_vertices(self) -> collections.abc.Iterator[Math.Vector3]:
		"""
		:return: The vertices of this mesh with world matrix applied
		"""

		return Stream.LinqStream(self.get_polygons()).transform_many(lambda poly: poly.points).distinct()

	def get_polygons(self) -> collections.abc.Iterator[Polygon3D]:
		"""
		:return: The n-gons of this mesh with world matrix applied
		"""

		for polygon in self.polygons:
			yield polygon.transform(self.world_matrix)

	@property
	def polygons(self) -> tuple[Polygon3D, ...]:
		"""
		:return: The raw, untransformed n-gons of this mesh
		"""

		return self.__polygons__


__all__: list[str] = ['Triangle3D', 'Mesh3D']
