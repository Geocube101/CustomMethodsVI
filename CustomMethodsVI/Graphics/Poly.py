from __future__ import annotations

import collections.abc
import math
import typing

from . import Math
from . import Material
from . import Util
from . import VectorOps
from .. import Exceptions
from .. import Misc
from .. import Stream


class Polygon3D(Util.Object):
	"""
	Class representing a single n-gon in 3D space
	"""

	def __init__(self, point1: Math.Vector3, point2: Math.Vector3, point3: Math.Vector3, *points: Math.Vector3, uv_mat: typing.Optional[Material.UVMap] = None, invert_normal: bool = False):
		"""
		Class representing a single n-gon in 3D space
		:param point1: The first vertex of this n-gon
		:param point2: The second vertex of this n-gon
		:param point3: The third vertex of this n-gon
		:param points: The remaining vertices of this n-gon
		:param uv_mat: The UV material to render with
		:raises InvalidArgumentException: If any argument is invalid
		"""

		points: tuple[Math.Vector3, ...] = (point1, point2, point3, *points)
		invalid_point: typing.Optional[typing.Any] = Stream.LinqStream(points).filter(lambda p: not isinstance(p, Math.Vector3)).first_or_default()
		Misc.raise_ifn(invalid_point is None, Exceptions.InvalidArgumentException(Polygon3D.__init__, 'points', type(invalid_point), (Math.Vector3,)))
		Misc.raise_ifn(uv_mat is None or uv_mat is ... or isinstance(uv_mat, Material.UVMap), Exceptions.InvalidArgumentException(Polygon3D.__init__, 'uv', type(uv_mat), (Material.UVMap,)))
		super().__init__()
		self.__points__: VectorOps.Vector3List = VectorOps.Vector3List(*points)
		self.__uv__: typing.Optional[Material.UVMap] = None if uv_mat is ... or uv_mat is None else uv_mat
		self.__invert_normal__: bool = bool(invert_normal)
		self.__normal__: Math.Vector3 = ...

	def __eq__(self, other: Polygon3D) -> bool:
		return isinstance(other, Polygon3D) and self.points == other.points

	def transform(self, matrix: Math.TransformMatrix3D) -> Polygon3D:
		"""
		Transforms this n-gon by the specified transform matrix in-place
		:param matrix: The transform matrix
		:return: This polygon
		"""

		self.points.transform(matrix)
		return self

	def copy_from(self, polygon: Polygon3D, *, copy_uv: bool = True, copy_normal: bool = True) -> Polygon3D:
		"""
		Copies the data from the specified polygon to this one
		:param polygon: The polygon to copy from
		:param copy_uv: Whether to copy the polygon's UV and material
		:param copy_normal: Whether to copy the polygon's normal
		:return: This polygon
		"""

		self.__points__ = VectorOps.Vector3List.from_numpy(polygon.points.array)
		self.__uv__ = polygon.__uv__ if copy_uv else self.__uv__
		self.__invert_normal__ = polygon.__invert_normal__ if copy_normal else self.__invert_normal__
		self.__normal__ = polygon.__normal__ if copy_normal else self.__normal__
		return self

	def closest_vertex_to(self, point: Math.Vector3) -> tuple[Math.Vector3, float]:
		"""
		Calculates the closest vertex to the specified point
		:param point: The point
		:return: The closest vertex and distance to 'point'
		"""

		distances: Math.NUMPY.ndarray = self.points.distance_squared(VectorOps.Vector3List.repeat(point, len(self.points)))
		merged: Math.NUMPY.ndarray = Math.NUMPY.hstack((self.points.array, distances.reshape((len(self.points), 1))))
		result: Math.NUMPY.ndarray = merged[merged[:, 3].argsort()]
		return Math.Vector3(*result[0, :3]), float(result[0, 3])

	def farthest_vertex_from(self, point: Math.Vector3) -> tuple[Math.Vector3, float]:
		"""
		Calculates the farthest vertex from the specified point
		:param point: The point
		:return: The farthest vertex and distance to 'point'
		"""

		distances: Math.NUMPY.ndarray = self.points.distance_squared(VectorOps.Vector3List.repeat(point, len(self.points)))
		merged: Math.NUMPY.ndarray = Math.NUMPY.hstack((self.points.array, distances.reshape((len(self.points), 1))))
		result: Math.NUMPY.ndarray = merged[merged[:, 3].argsort()]
		return Math.Vector3(*result[-1, :3]), float(result[-1, 3])

	def transformed(self, matrix: Math.TransformMatrix3D) -> Polygon3D:
		"""
		Transforms this n-gon by the specified transform matrix
		:param matrix: The transform matrix
		:return: The transformed n-gon
		"""

		return Polygon3D(*self.points.transformed(matrix), uv_mat=self.material, invert_normal=self.is_normal_inverted)

	def clone(self) -> Polygon3D:
		"""
		Clones this polygon
		:return: A copy of this n-gon
		"""

		return Polygon3D(*self.points, uv_mat=self.__uv__, invert_normal=self.__invert_normal__)

	def invert_normal(self) -> Polygon3D:
		"""
		Inverts this polygon's normal
		:return: This polygon
		"""

		self.__invert_normal__ = not self.__invert_normal__

		if self.__normal__ is not ...:
			self.__normal__ = -self.__normal__

		return self

	@property
	def is_normal_inverted(self) -> bool:
		"""
		:return: Whether this polygon's normal is inverted
		"""

		return self.__invert_normal__

	@property
	def center(self) -> Math.Vector3:
		"""
		:return: This polygon's average midpoint
		"""

		return Math.Vector3.average(*self.points)

	@property
	def normal(self) -> Math.Vector3:
		"""
		:return: This triangle's facing normal
		"""

		if self.__normal__ is ...:
			p1, p2, p3, *p = self.points
			dir1: Math.Vector3 = (p2 - p1)
			dir2: Math.Vector3 = (p3 - p1)
			normal: Math.Vector3 = dir1.cross(dir2).normalized() if dir1.angle(dir2) % math.pi != 0 else Math.Vector3.zero()
			self.__normal__ = -normal if self.is_normal_inverted else normal

		return self.__normal__

	@property
	def points(self) -> VectorOps.Vector3List:
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


class Mesh3D(Util.Transformable3D):
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

	@classmethod
	def create_sphere(cls, position: Math.Vector3, count: int = 32, uv_mat: typing.Optional[Material.UVMap] = None) -> Mesh3D:
		Misc.raise_ifn(isinstance(count, int), Exceptions.InvalidArgumentException(cls.create_sphere, 'count', type(count), (int,)))
		Misc.raise_if((count := int(count)) < 3, ValueError(f'Sphere must have a vertex count of at least 3; got \'{count}\''))
		delta: float = math.radians(360 / count)
		deg_90: float = math.pi / 2
		faces: list[Polygon3D] = []

		for index_1 in range(count >> 1):
			phi1: float = Misc.get_value(index_1 / count, -deg_90, deg_90)
			phi2: float = Misc.get_value((index_1 + 1) % count / count, -deg_90, deg_90)
			cos_phi_1: float = math.cos(phi1)
			cos_phi_2: float = math.cos(phi2)
			sin_phi_1: float = math.sin(phi1)
			sin_phi_2: float = math.sin(phi2)

			for index_2 in range(count):
				theta1: float = delta * index_2
				theta2: float = delta * ((index_2 + 1) % count)
				cos_theta_1: float = math.cos(theta1)
				cos_theta_2: float = math.cos(theta2)
				sin_theta_1: float = math.sin(theta1)
				sin_theta_2: float = math.sin(theta2)

				x1: float = cos_phi_1 * cos_theta_1
				z1: float = cos_phi_1 * sin_theta_1
				y1: float = sin_phi_1

				x2: float = cos_phi_2 * cos_theta_1
				z2: float = cos_phi_2 * sin_theta_1
				y2: float = sin_phi_2

				x3: float = cos_phi_2 * cos_theta_2
				z3: float = cos_phi_2 * sin_theta_2
				y3: float = sin_phi_2

				x4: float = cos_phi_1 * cos_theta_2
				z4: float = cos_phi_1 * sin_theta_2
				y4: float = sin_phi_1

				points1: tuple[Math.Vector3, ...] = (Math.Vector3(x1, y1, z1), Math.Vector3(x2, y2, z2), Math.Vector3(x3, y3, z3), Math.Vector3(x4, y4, z4))
				points2: tuple[Math.Vector3, ...] = (Math.Vector3(x1, -y1, z1), Math.Vector3(x2, -y2, z2), Math.Vector3(x3, -y3, z3), Math.Vector3(x4, -y4, z4))
				faces.append(Polygon3D(*Stream.LinqStream(points1).distinct().collect(), uv_mat=uv_mat, invert_normal=False))
				faces.append(Polygon3D(*Stream.LinqStream(points2).distinct().collect(), uv_mat=uv_mat, invert_normal=True))

		return cls(
			Math.TransformMatrix3D.create_world(Math.Vector3.forward(), Math.Vector3.up(), position), faces
		)

	@classmethod
	def create_capsule(cls, position: Math.Vector3, count: int = 32, ratio: float = 1, uv_mat: typing.Optional[Material.UVMap] = None) -> Mesh3D:
		Misc.raise_ifn(isinstance(count, int), Exceptions.InvalidArgumentException(cls.create_capsule, 'count', type(count), (int,)))
		Misc.raise_ifn(isinstance(ratio, (int, float)), Exceptions.InvalidArgumentException(cls.create_capsule, 'ratio', type(ratio), (float,)))
		Misc.raise_if((count := int(count)) < 3, ValueError(f'Capsule must have a vertex count of at least 3; got \'{count}\''))
		Misc.raise_ifn((ratio := float(ratio)) >= 0, ValueError(f'Capsule must have a positive or zero height ratio; got \'{ratio}\''))

		delta: float = math.radians(360 / count)
		deg_90: float = math.pi / 2
		half_height: float = ratio / 2
		faces: list[Polygon3D] = []
		lateral_count: int = count >> 1

		for index_1 in range(lateral_count):
			phi1: float = Misc.get_value(index_1 / count, -deg_90, deg_90)
			phi2: float = Misc.get_value((index_1 + 1) % count / count, -deg_90, deg_90)
			cos_phi_1: float = math.cos(phi1)
			cos_phi_2: float = math.cos(phi2)
			sin_phi_1: float = math.sin(phi1)
			sin_phi_2: float = math.sin(phi2)

			for index_2 in range(count):
				theta1: float = delta * index_2
				theta2: float = delta * ((index_2 + 1) % count)
				cos_theta_1: float = math.cos(theta1)
				cos_theta_2: float = math.cos(theta2)
				sin_theta_1: float = math.sin(theta1)
				sin_theta_2: float = math.sin(theta2)

				x1: float = cos_phi_1 * cos_theta_1
				z1: float = cos_phi_1 * sin_theta_1
				y1: float = sin_phi_1

				x2: float = cos_phi_2 * cos_theta_1
				z2: float = cos_phi_2 * sin_theta_1
				y2: float = sin_phi_2

				x3: float = cos_phi_2 * cos_theta_2
				z3: float = cos_phi_2 * sin_theta_2
				y3: float = sin_phi_2

				x4: float = cos_phi_1 * cos_theta_2
				z4: float = cos_phi_1 * sin_theta_2
				y4: float = sin_phi_1

				points1: tuple[Math.Vector3, ...] = (Math.Vector3(x1, y1 - half_height, z1), Math.Vector3(x2, y2 - half_height, z2), Math.Vector3(x3, y3 - half_height, z3), Math.Vector3(x4, y4 - half_height, z4))
				points2: tuple[Math.Vector3, ...] = (Math.Vector3(x1, -y1 + half_height, z1), Math.Vector3(x2, -y2 + half_height, z2), Math.Vector3(x3, -y3 + half_height, z3), Math.Vector3(x4, -y4 + half_height, z4))
				faces.append(Polygon3D(*Stream.LinqStream(points1).distinct().collect(), uv_mat=uv_mat, invert_normal=False))
				faces.append(Polygon3D(*Stream.LinqStream(points2).distinct().collect(), uv_mat=uv_mat, invert_normal=True))

				if ratio > 0 and index_1 == lateral_count - 1:
					points3: tuple[Math.Vector3, ...] = (points1[1], points2[1], points2[2], points1[2])
					faces.append(Polygon3D(*Stream.LinqStream(points3).distinct().collect(), uv_mat=uv_mat, invert_normal=False))

		return cls(
			Math.TransformMatrix3D.create_world(Math.Vector3.forward(), Math.Vector3.up(), position), faces
		)

	def __init__(self, world_matrix: Math.TransformMatrix3D, polygons: collections.abc.Iterable[Polygon3D]):
		"""
		Class representing a mesh in 3D space
		:param world_matrix: The mesh's world matrix
		:param polygons: The polygons that compose this mesh
		"""

		Misc.raise_ifn(isinstance(polygons, collections.abc.Iterable), Exceptions.InvalidArgumentException(Mesh3D.__init__, 'polygons', type(polygons), (collections.abc.Iterable,)))
		Misc.raise_ifn(len(polygons := tuple(polygons)) > 0 and all(isinstance(x, Polygon3D) for x in polygons), ValueError('Polygons list is empty or invalid'))
		super().__init__(world_matrix)
		self.__polygons__: tuple[Polygon3D, ...] = tuple(polygon for polygon in polygons if polygon.normal.length() > 0)
		self.__transformed__: tuple[Polygon3D, ...] = tuple(VectorOps.Polygon3DList(*self.__polygons__).transformed(self.world_matrix))
		self.on_world_matrix_changed += self.__on_world_matrix_changed__

	def __on_world_matrix_changed__(self, obj: Util.Object3D) -> None:
		self.__transformed__ = ...

	def __hash__(self) -> int:
		return hash(self.polygons)

	def __eq__(self, other: Mesh3D) -> bool:
		return isinstance(other, Mesh3D) and self.polygons == other.polygons

	def copy_from(self, mesh: Mesh3D, *, copy_uvs: bool = True, copy_normals: bool = True) -> Mesh3D:
		"""
		Copies the data from the specified polygon to this one
		:param mesh: The polygon to copy from
		:param copy_uvs: Whether to copy the mesh's polygon UVs and materials
		:param copy_normals: Whether to copy the mesh's polygon normals
		:return: This mesh
		"""

		for i in range(min(len(self.polygons), len(mesh.polygons))):
			self.__polygons__[i].copy_from(mesh.polygons[i], copy_uv=copy_uvs, copy_normal=copy_normals)

		if len(self.polygons) > len(mesh.polygons):
			del self.polygons[len(mesh.polygons):]
		elif len(self.polygons) < len(mesh.polygons):
			self.__polygons__ = (*self.polygons, mesh.polygons[len(self.polygons):])

		return self

	def clone(self) -> Mesh3D:
		"""
		Clones this mesh
		:return: A copy of this mesh
		"""

		return Mesh3D(self.__world_matrix__, self.__polygons__)

	def invert_normals(self) -> Mesh3D:
		"""
		Inverts the normals of this mesh's polygons
		:return: This mesh
		"""

		for poly in self.__polygons__:
			poly.invert_normal()

		if self.__transformed__ is not ...:
			for poly in self.__transformed__:
				poly.invert_normal()

		return self

	def get_vertices(self) -> collections.abc.Iterator[Math.Vector3]:
		"""
		:return: The vertices of this mesh with world matrix applied
		"""

		return Stream.LinqStream(self.get_polygons()).transform_many(lambda poly: poly.points).distinct()

	def get_polygons(self) -> collections.abc.Iterator[Polygon3D]:
		"""
		Calculates the world space polygons of this mesh
		:return: The n-gons of this mesh with world matrix applied
		"""

		if self.__transformed__ is ...:
			self.__transformed__ = VectorOps.Polygon3DList(*self.__polygons__).transformed(self.world_matrix)

		return iter(self.__transformed__)

	@property
	def polygons(self) -> tuple[Polygon3D, ...]:
		"""
		:return: The raw, untransformed n-gons of this mesh
		"""

		return self.__polygons__


class Polygon2D(Util.Object):
	"""
	Class representing a single n-gon in 2D space
	"""

	def __init__(self, point1: Math.Vector2, point2: Math.Vector2, point3: Math.Vector2, *points: Math.Vector2, uv_mat: typing.Optional[Material.UVMap] = None):
		"""
		Class representing a single n-gon in 2D space
		:param point1: The first vertex of this n-gon
		:param point2: The second vertex of this n-gon
		:param point3: The third vertex of this n-gon
		:param points: The remaining vertices of this n-gon
		:param uv_mat: The UV material to render with
		:raises InvalidArgumentException: If any argument is invalid
		"""

		points: tuple[Math.Vector2, ...] = (point1, point2, point3, *points)
		invalid_point: typing.Optional[typing.Any] = Stream.LinqStream(points).filter(lambda p: not isinstance(p, Math.Vector2)).first_or_default()
		Misc.raise_ifn(invalid_point is None, Exceptions.InvalidArgumentException(Polygon2D.__init__, 'points', type(invalid_point), (Math.Vector2,)))
		Misc.raise_ifn(uv_mat is None or uv_mat is ... or isinstance(uv_mat, Material.UVMap), Exceptions.InvalidArgumentException(Polygon2D.__init__, 'uv', type(uv_mat), (Material.UVMap,)))
		super().__init__()
		self.__points__: VectorOps.Vector2List = VectorOps.Vector2List(*points)
		self.__uv__: typing.Optional[Material.UVMap] = None if uv_mat is ... or uv_mat is None else uv_mat

	def __eq__(self, other: Polygon2D) -> bool:
		return isinstance(other, Polygon2D) and self.points == other.points

	def transform(self, matrix: Math.TransformMatrix2D) -> Polygon2D:
		"""
		Transforms this n-gon by the specified transform matrix in-place
		:param matrix: The transform matrix
		:return: This polygon
		"""

		self.points.transform(matrix)
		return self

	def copy_from(self, polygon: Polygon2D, *, copy_uv: bool = True, copy_normal: bool = True) -> Polygon2D:
		"""
		Copies the data from the specified polygon to this one
		:param polygon: The polygon to copy from
		:param copy_uv: Whether to copy the polygon's UV and material
		:param copy_normal: Whether to copy the polygon's normal
		:return: This polygon
		"""

		self.__points__ = VectorOps.Vector2List.from_numpy(polygon.points.array)
		self.__uv__ = polygon.__uv__ if copy_uv else self.__uv__
		return self

	def closest_vertex_to(self, point: Math.Vector2) -> tuple[Math.Vector2, float]:
		"""
		Calculates the closest vertex to the specified point
		:param point: The point
		:return: The closest vertex and distance to 'point'
		"""

		distances: Math.NUMPY.ndarray = self.points.distance_squared(VectorOps.Vector2List.repeat(point, len(self.points)))
		merged: Math.NUMPY.ndarray = Math.NUMPY.hstack((self.points.array, distances.reshape((len(self.points), 1))))
		result: Math.NUMPY.ndarray = merged[merged[:, 2].argsort()]
		return Math.Vector2(*result[0, :2]), float(result[0, 2])

	def farthest_vertex_from(self, point: Math.Vector2) -> tuple[Math.Vector2, float]:
		"""
		Calculates the farthest vertex from the specified point
		:param point: The point
		:return: The farthest vertex and distance to 'point'
		"""

		distances: Math.NUMPY.ndarray = self.points.distance_squared(VectorOps.Vector2List.repeat(point, len(self.points)))
		merged: Math.NUMPY.ndarray = Math.NUMPY.hstack((self.points.array, distances.reshape((len(self.points), 1))))
		result: Math.NUMPY.ndarray = merged[merged[:, 2].argsort()]
		return Math.Vector2(*result[-1, :2]), float(result[-1, 2])

	def transformed(self, matrix: Math.TransformMatrix2D) -> Polygon2D:
		"""
		Transforms this n-gon by the specified transform matrix
		:param matrix: The transform matrix
		:return: The transformed n-gon
		"""

		return Polygon2D(*self.points.transformed(matrix), uv_mat=self.material)

	def clone(self) -> Polygon2D:
		"""
		Clones this polygon
		:return: A copy of this n-gon
		"""

		return Polygon2D(*self.points, uv_mat=self.__uv__)

	def to_3d(self, z: float, invert_normal: bool = False) -> Polygon3D:
		"""
		Converts this 2D polygon to a 2D polygon
		:param z: The z value to fill
		:param invert_normal: Whether to invert the result's normal
		:return: The 3D polygon
		"""

		return Polygon3D(*[Math.Vector3(x, y, z) for x, y in self.points], uv_mat=self.material, invert_normal=invert_normal)

	@property
	def center(self) -> Math.Vector2:
		"""
		:return: This polygon's average midpoint
		"""

		return Math.Vector2.average(*self.points)

	@property
	def points(self) -> VectorOps.Vector2List:
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


class Triangle2D(Polygon2D):
	def __init__(self, point1: Math.Vector2, point2: Math.Vector2, point3: Math.Vector2, *, uv_mat: typing.Optional[Material.UVMap] = None):
		"""
		Class representing a single triangle in 3D space
		:param point1: The first vertex
		:param point2: The second vertex
		:param point3: The third vertex
		:param uv_mat: The UV material to render with
		:raises InvalidArgumentException: If any argument is invalid
		"""

		super().__init__(point1, point2, point3, uv_mat=uv_mat)


class Quadrangle2D(Polygon2D):
	def __init__(self, point1: Math.Vector2, point2: Math.Vector2, point3: Math.Vector2, point4: Math.Vector2, *, uv_mat: typing.Optional[Material.UVMap] = None):
		"""
		Class representing a single quadrangle in 2D space
		:param point1: The first vertex
		:param point2: The second vertex
		:param point3: The third vertex
		:param point4: The fourth vertex
		:param uv_mat: The UV material to render with
		:raises InvalidArgumentException: If any argument is invalid
		"""

		super().__init__(point1, point2, point3, point4, uv_mat=uv_mat)

	def triangulate_faces(self) -> tuple[Triangle2D, Triangle2D]:
		"""
		Triangles this quad into two triangular faces
		:return: The triangles
		"""

		p1, p2, p3, p4 = self.points
		return Triangle2D(p1, p2, p3, uv_mat=self.material), Triangle2D(p1, p4, p3, uv_mat=self.material)


class Mesh2D(Util.Transformable2D):
	@classmethod
	def create_square(cls, position: Math.Vector2, uv_mat: typing.Optional[Material.UVMap] = None) -> Mesh2D:
		return cls(
			Math.TransformMatrix2D.create_world(Math.Vector2.right(), Math.Vector2.up(), position),
			(
				Math.Vector2(0.5, 0.5),
				Math.Vector2(-0.5, 0.5),
				Math.Vector2(-0.5, -0.5),
				Math.Vector2(0.5, -0.5),
			)
		)

	@classmethod
	def create_circle(cls, position: Math.Vector2, count: int = 32, uv_mat: typing.Optional[Material.UVMap] = None) -> Mesh2D:
		Misc.raise_ifn(isinstance(count, int), Exceptions.InvalidArgumentException(cls.create_circle, 'count', type(count), (int,)))
		Misc.raise_if((count := int(count)) < 3, ValueError(f'Circle must have a vertex count of at least 3; got \'{count}\''))
		points: list[Math.Vector2] = []
		delta: float = math.radians(360 / count)

		for i in range(count):
			x: float = math.cos(delta * i)
			y: float = math.sin(delta * i)
			points.append(Math.Vector2(x, y))

		return cls(
			Math.TransformMatrix2D.create_world(Math.Vector2.right(), Math.Vector2.up(), position),
			points
		)

	def __init__(self, world_matrix: Math.TransformMatrix2D, points: collections.abc.Iterable[Math.Vector2]):
		"""
		Class representing a mesh in 2D space
		:param world_matrix: The mesh's world matrix
		:param points: The edges that compose this mesh
		"""

		Misc.raise_ifn(isinstance(points, collections.abc.Iterable), Exceptions.InvalidArgumentException(Mesh2D.__init__, 'points', type(points), (collections.abc.Iterable,)))
		Misc.raise_ifn(len(points := tuple(points)) > 0 and all(isinstance(x, Math.Vector2) for x in points), ValueError('Points list is empty or invalid'))
		super().__init__(world_matrix)
		self.__points__: tuple[Math.Vector2, ...] = Stream.LinqStream(points).distinct().collect()
		self.__transformed__: tuple[Math.Vector2, ...] = tuple(VectorOps.Vector2List(*self.__points__).transformed(self.world_matrix))
		self.on_world_matrix_changed += self.__on_world_matrix_changed__

	def __on_world_matrix_changed__(self, obj: Util.Object2D) -> None:
		self.__transformed__ = ...

	def __hash__(self) -> int:
		return hash(self.points)

	def __eq__(self, other: Mesh2D) -> bool:
		return isinstance(other, Mesh2D) and self.points == other.points

	def to_polygon(self, uv_mat: typing.Optional[Material.UVMap] = None) -> Polygon2D:
		"""
		Converts this 2D mesh to a 2D polygon
		:param uv_mat: The polygon material
		:return: The 2D polygon
		"""

		return Polygon2D(*[Math.Vector2(x, y) for x, y in self.get_points()], uv_mat=uv_mat)

	def get_points(self) -> collections.abc.Iterator[Math.Vector2]:
		"""
		Calculates the world space points of this mesh
		:return: The points of this mesh with world matrix applied
		"""

		if self.__transformed__ is not ...:
			return iter(self.__transformed__)

		return iter(VectorOps.Vector2List(*self.__points__).transformed(self.world_matrix))

	@property
	def points(self) -> tuple[Math.Vector2, ...]:
		"""
		:return: The raw, untransformed points of this mesh
		"""

		return self.__points__


__all__: list[str] = [
	'Polygon2D', 'Triangle2D', 'Quadrangle2D',
	'Polygon3D', 'Triangle3D', 'Quadrangle3D',
	'Mesh3D', 'Mesh2D'
]
