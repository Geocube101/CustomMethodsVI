from __future__ import annotations

import collections.abc

from . import Math
from . import Material
from . import Poly
from . import Util
from .. import Misc


class BoundingShape2D(Util.Transformable2D):
	def __init__(self, transform: Math.TransformMatrix2D):
		"""
		Base class for a 2D bounding shape
		:param transform: The shape's transform matrix
		"""

		super().__init__(transform)

	def intersects(self, shape: BoundingShape2D) -> bool:
		"""
		Checks if the specified shape intersects this one
		:param shape: The target shape
		:return: Whether shapes intersect
		"""

		return False

	def includes(self, point: Math.Vector2) -> bool:
		"""
		Checks if the specified point is within this shape
		:param point: The point
		:return: Whether point is contained
		"""

		return False

	def meshify(self, uv_mat: Material.UVMap) -> Poly.Mesh2D:
		"""
		Converts this bounding shape to a 3D mesh
		:return: The mesh
		"""

		return Poly.Mesh2D(self.world_matrix, ())


class BoundingEllipse2D(BoundingShape2D):
	def __init__(self, center: Math.Vector2, radii: Math.Vector2):
		"""
		Class representing an ellipse
		:param center: The ellipse's position
		:param radii: The ellipse's radii
		"""

		super().__init__(Math.TransformMatrix2D.create_scale(*radii) @ Math.TransformMatrix2D.create_translation(*center))

	def includes(self, point: Math.Vector2) -> bool:
		return self.world_matrix_inv.transform_vector(point).length_squared() <= 1

	def meshify(self, uv_mat: Material.UVMap, *, count: int = 32) -> Poly.Mesh2D:
		circle: Poly.Mesh2D = Poly.Mesh2D.create_circle(self.world_matrix.translation, count, uv_mat)
		return circle.scale(*self.radii)

	@property
	def radii(self) -> Math.Vector2:
		"""
		:return: This ellipsoid's radii
		"""

		return self.world_matrix.scale


class BoundingBox2D(BoundingShape2D):
	def __init__(self, center: Math.Vector2, extents: Math.Vector2):
		super().__init__(Math.TransformMatrix2D.create_scale(*extents) @ Math.TransformMatrix2D.create_translation(*center))

	def includes(self, point: Math.Vector2) -> bool:
		x, y = self.world_matrix_inv.transform_vector(point)
		return -1 <= x <= 1 and -1 <= y <= 1

	def vertex(self, index: int) -> Math.Vector2:
		"""
		Gets the vertex at the specified index
		:param index: The vertex index
		:return: The vertex world position
		"""

		Misc.raise_ifn(0 <= (index := int(index)) < 4, ValueError('Vertex index must be in the range [0,4)'))
		x: int = index & 0b100
		y: int = index & 0b010
		return self.world_matrix.transform_vector(Math.Vector2(x, y))

	def vertices(self) -> collections.abc.Generator[Math.Vector2]:
		"""
		:return: A generator over all vertices of this box
		"""

		for packed in range(4):
			yield self.vertex(packed)

	def meshify(self, uv_mat: Material.UVMap) -> Poly.Mesh2D:
		box: Poly.Mesh2D = Poly.Mesh2D.create_square(self.world_matrix.translation, uv_mat)
		return box.scale(*self.extents)

	@property
	def extents(self) -> Math.Vector2:
		"""
		:return: This box's extents
		"""

		return self.world_matrix.scale

	@property
	def half_extents(self) -> Math.Vector2:
		"""
		:return: This box's half extents
		"""

		return self.world_matrix.scale / 2


class BoundingShape3D(Util.Transformable3D):
	def __init__(self, transform: Math.TransformMatrix3D):
		"""
		Base class for a 3D bounding shape
		:param transform: The shape's transform matrix
		"""

		super().__init__(transform)

	def intersects(self, shape: BoundingShape3D) -> bool:
		"""
		Checks if the specified shape intersects this one
		:param shape: The target shape
		:return: Whether shapes intersect
		"""

		return False

	def includes(self, point: Math.Vector3) -> bool:
		"""
		Checks if the specified point is within this shape
		:param point: The point
		:return: Whether point is contained
		"""

		return False

	def meshify(self, uv_mat: Material.UVMap) -> Poly.Mesh3D:
		"""
		Converts this bounding shape to a 3D mesh
		:return: The mesh
		"""

		return Poly.Mesh3D(self.world_matrix, ())


class BoundingEllipsoid3D(BoundingShape3D):
	def __init__(self, center: Math.Vector3, radii: Math.Vector3):
		"""
		Class representing an ellipsoid
		:param center: The ellipsoid's position
		:param radii: The ellipsoid's radii
		"""

		super().__init__(Math.TransformMatrix3D.create_scale(*radii) @ Math.TransformMatrix3D.create_translation(*center))

	def includes(self, point: Math.Vector3) -> bool:
		return self.world_matrix_inv.transform_vector(point).length_squared() <= 1

	def meshify(self, uv_mat: Material.UVMap, *, count: int = 32) -> Poly.Mesh3D:
		sphere: Poly.Mesh3D = Poly.Mesh3D.create_sphere(self.world_matrix.translation, count, uv_mat)
		return sphere.scale(*self.radii)

	@property
	def radii(self) -> Math.Vector3:
		"""
		:return: This ellipsoid's radii
		"""

		return self.world_matrix.scale


class BoundingBox3D(BoundingShape3D):
	def __init__(self, center: Math.Vector3, extents: Math.Vector3):
		super().__init__(Math.TransformMatrix3D.create_scale(*extents) @ Math.TransformMatrix3D.create_translation(*center))

	def includes(self, point: Math.Vector3) -> bool:
		x, y, z = self.world_matrix_inv.transform_vector(point)
		return -1 <= x <= 1 and -1 <= y <= 1 and -1 <= z <= 1

	def vertex(self, index: int) -> Math.Vector3:
		"""
		Gets the vertex at the specified index
		:param index: The vertex index
		:return: The vertex world position
		"""

		Misc.raise_ifn(0 <= (index := int(index)) < 8, ValueError('Vertex index must be in the range [0,8)'))
		x: int = index & 0b100
		y: int = index & 0b010
		z: int = index & 0b001
		return self.world_matrix.transform_vector(Math.Vector3(x, y, z))

	def vertices(self) -> collections.abc.Generator[Math.Vector3]:
		"""
		:return: A generator over all vertices of this box
		"""

		for packed in range(8):
			yield self.vertex(packed)

	def meshify(self, uv_mat: Material.UVMap) -> Poly.Mesh3D:
		box: Poly.Mesh3D = Poly.Mesh3D.create_cube(self.world_matrix.translation, uv_mat)
		return box.scale(*self.extents)

	@property
	def extents(self) -> Math.Vector3:
		"""
		:return: This box's extents
		"""

		return self.world_matrix.scale

	@property
	def half_extents(self) -> Math.Vector3:
		"""
		:return: This box's half extents
		"""

		return self.world_matrix.scale / 2


class BoundingCylinder3D(BoundingShape3D):
	def __init__(self, center: Math.Vector3, r1: float, r2: float, height: float):
		super().__init__(Math.TransformMatrix3D.create_scale(r1, height, r2) @ Math.TransformMatrix3D.create_translation(*center))

	def includes(self, point: Math.Vector3) -> bool:
		x, y, z = self.world_matrix_inv.transform_vector(point)
		return -1 <= z <= 1 and x * x + y * y <= 1

	def meshify(self, uv_mat: Material.UVMap, *, count: int = 32) -> Poly.Mesh3D:
		cylinder: Poly.Mesh3D = Poly.Mesh3D.create_cylinder(self.world_matrix.translation, count, uv_mat)
		return cylinder.scale(*self.world_matrix.scale)

	@property
	def height(self) -> float:
		"""
		:return: This cylinder's height
		"""

		return self.world_matrix.scale.y

	@property
	def radii(self) -> Math.Vector2:
		"""
		:return: This cylinder's radii
		"""

		sx, sy, sz = self.world_matrix.scale
		return Math.Vector2(sx, sz)


class BoundingCapsule3D(BoundingCylinder3D):
	def __init__(self, center: Math.Vector3, r1: float, r2: float, height: float):
		self.__inner_height__: float = height - 2 * max(r1, r2)
		Misc.raise_if(self.__inner_height__ < 0, ValueError(f'Capsule too short for given radii - must be at least {2 * max(r1, r2)}'))
		super().__init__(center, r1, r2, height)

	def includes(self, point: Math.Vector3) -> bool:
		point = self.world_matrix_inv.transform_vector(point)
		half_height: float = self.height
		normal: Math.Vector3 = Math.Vector3(0, half_height, 0)
		projected: Math.Vector3 = normal.project(point)
		return (point - projected).length_squared() <= 1

	def meshify(self, uv_mat: Material.UVMap, *, count: int = 32) -> Poly.Mesh3D:
		ratio: float = self.__inner_height__ / max(self.radii)
		capsule: Poly.Mesh3D = Poly.Mesh3D.create_capsule(self.world_matrix.translation, count, ratio, uv_mat)
		return capsule.scale(self.world_matrix.scale.x, 1, self.world_matrix.scale.z)

	@property
	def node1(self) -> Math.Vector3:
		"""
		:return: The first node of this capsule
		"""

		return self.world_matrix.transform_vector(Math.Vector3(0, self.__inner_height__, 0))

	@property
	def node2(self) -> Math.Vector3:
		"""
		:return: The second node of this capsule
		"""

		return self.world_matrix.transform_vector(Math.Vector3(0, -self.__inner_height__, 0))

	@property
	def line(self) -> Math.Line3D:
		"""
		:return: This capsule's central line
		"""

		return Math.Line3D(self.node1, self.node2)


__all__: list[str] = [
	'BoundingShape2D', 'BoundingShape3D',
	'BoundingEllipsoid3D', 'BoundingBox3D', 'BoundingCylinder3D', 'BoundingCapsule3D'
]
