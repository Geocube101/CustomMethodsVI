from __future__ import annotations

import collections.abc
import math

from . import Math
from . import Poly
from .. import Exceptions
from .. import Misc


class Camera:
	"""
	Class representing a camera in 3D space
	"""

	@staticmethod
	def create_lookat_view(position: Math.Vector3, target: Math.Vector3, up: Math.Vector3) -> Math.TransformMatrix3D:
		"""
		Creates a view matrix using lookat convention
		:param position: The camera's position in world space
		:param target: The camera's target in world space
		:param up: The camera's up vector in world space
		:return: The view matrix
		"""

		forward: Math.Vector3 = target - position
		return Math.TransformMatrix3D.create_world(forward.normalized(), up, position).inversed()

	@staticmethod
	def create_fov_perspective_projection(fov: float, aspect: float = 1920 / 1080, near: float = 1e-3, far: float = 1e3) -> Math.TransformMatrix3D:
		"""
		Creates a perspective matrix using fov and aspect
		:param fov: The camera's FOV
		:param aspect: The viewport's aspect (width / height)
		:param near: The near clipping plane
		:param far: The far clipping plane
		:return: The perspective matrix
		"""

		fy: float = 1 / math.tan(math.radians(fov / 2))
		fz: float = fy / aspect
		va: float = far / (far - near)
		vb: float = (-far * near) / (far - near)

		return Math.TransformMatrix3D((
			00, 00, fz, 1,
			00, fy, 00, 00,
			va, 00, 00, 00,
			vb, 00, 00, 00
		))

	def __init__(self, view_matrix: Math.TransformMatrix3D, projection_matrix: Math.TransformMatrix3D):
		"""
		Class representing a camera in 3D space
		:param view_matrix: The camera's view matrix
		:param projection_matrix: The camera's projection matrix
		"""

		Misc.raise_ifn(isinstance(view_matrix, Math.TransformMatrix3D), Exceptions.InvalidArgumentException(Camera.__init__, 'view_matrix', type(view_matrix), (Math.TransformMatrix3D,)))
		Misc.raise_ifn(isinstance(projection_matrix, Math.TransformMatrix3D), Exceptions.InvalidArgumentException(Camera.__init__, 'projection_matrix', type(projection_matrix), (Math.TransformMatrix3D,)))
		self.__view__: Math.TransformMatrix3D = view_matrix
		self.__projection__: Math.TransformMatrix3D = projection_matrix
		self.__view_projection__: Math.TransformMatrix3D = self.view @ self.projection

	def rotate(self, x_radians: float, y_radians: float, z_radians: float) -> Camera:
		"""
		Rotates the camera by the specified amounts
		:param x_radians: The x rotation in radians
		:param y_radians: The y rotation in radians
		:param z_radians: The z rotation in radians
		:return: This camera
		"""

		rotation: Math.TransformMatrix3D = Math.TransformMatrix3D.create_rotation(x_radians, y_radians, z_radians)
		self.view = rotation @ self.view
		return self

	def translate(self, x: float, y: float, z: float) -> Camera:
		"""
		Translates this camera by the specified amounts
		:param x: The x translation
		:param y: The y translation
		:param z: The z translation
		:return: This camera
		"""

		translation: Math.TransformMatrix3D = Math.TransformMatrix3D.create_translation(x, y, z)
		self.view = translation @ self.view
		return self

	def scale(self, x: float, y: float, z: float) -> Camera:
		"""
		Scales this camera by the specified amount
		:param x: The x scale
		:param y: The y scale
		:param z: The z scale
		:return:
		"""

		scale: Math.TransformMatrix3D = Math.TransformMatrix3D.create_scale(x, y, z)
		self.view = scale @ self.view
		return self

	def points_world_to_screen(self, screen_width: int, screen_height: int, point: Math.Vector3, *points: Math.Vector3) -> collections.abc.Iterator[Math.Vector3]:
		"""
		Converts the specified points from world space into screen space\n
		Points out of bounds will be '...'
		:param screen_width: The screen width
		:param screen_height: The screen height
		:param point: The first point to transform
		:param points: The remaining points to transform
		:return: All transformed points in front of the camera
		"""

		points: tuple[Math.Vector3, ...] = (point, *points)
		aspect: float = screen_width / screen_height / math.sqrt(2)

		for point in points:
			full_clip_space: Math.Vector4 = self.view_projection.transform_vector(Math.Vector4(*point, 1))

			if full_clip_space.w <= 0:
				yield ...
				continue

			ndc: Math.Vector3 = Math.Vector3(*full_clip_space[:3]) / full_clip_space.w / Math.Vector3(aspect, 1, 1)

			screen: Math.Vector3 = Math.Vector3(
				(ndc.x + 1) / 2 * screen_width,
				(1 - (ndc.y + 1) / 2) * screen_height,
				(ndc.z + 1) / 2
			)

			yield screen

	def polygons_world_to_screen(self, screen_width: int, screen_height: int, polygon: Poly.Polygon3D, *polygons: Poly.Polygon3D) -> collections.abc.Iterator[Poly.Polygon3D]:
		"""
		Converts the specified triangles from world space into screen space\n
		Polygons out of bounds will be '...'
		:param screen_width: The screen width
		:param screen_height: The screen height
		:param polygon: The first polygon to transform
		:param polygons: The remaining polygons to transform
		:return: All transformed triangles fully in front of the camera
		"""

		polygons: tuple[Poly.Polygon3D, ...] = (polygon, *polygons)
		view_direction: Math.Vector3 = self.view.backward * Math.Vector3(-1, 1, 1)

		for polygon in polygons:
			if view_direction.dot(polygon.normal) >= 0:
				yield ...
				continue

			points: tuple[Math.Vector3, ...] = tuple(self.points_world_to_screen(screen_width, screen_height, *polygon.points))

			if ... in points:
				yield ...
				continue

			yield Poly.Polygon3D(*points, uv_mat=polygon.material, invert_normal=polygon.is_normal_inverted)

	def shapes_world_to_screen(self, screen_width: int, screen_height: int, shape: Poly.Mesh3D, *shapes: Poly.Mesh3D) -> collections.abc.Iterator[Poly.Mesh3D]:
		"""
		Converts the specified shapes from world space into screen space\n
		Shapes out of bounds will be '...'
		:param screen_width: The screen width
		:param screen_height: The screen height
		:param shape: The first shape to transform
		:param shapes: The remaining shapes to transform
		:return: All transformed shapes fully in front of the camera
		"""

		shapes: tuple[Poly.Mesh3D, ...] = (shape, *shapes)

		for shape in shapes:
			shape_polygons: tuple[Poly.Polygon3D, ...] = tuple(shape.get_polygons())
			polygons: tuple[Poly.Polygon3D, ...] = tuple(self.polygons_world_to_screen(screen_width, screen_height, *shape_polygons))

			if ... in polygons:
				yield ...
				continue

			yield Poly.Mesh3D(Math.TransformMatrix3D.identity(), polygons)

	@property
	def view_projection(self) -> Math.TransformMatrix3D:
		"""
		:return: The current view projection matrix
		"""

		return self.__view_projection__

	@property
	def view(self) -> Math.TransformMatrix3D:
		"""
		:return: The current view matrix
		"""

		return self.__view__

	@property
	def projection(self) -> Math.TransformMatrix3D:
		"""
		:return: The current projection matrix
		"""

		return self.__projection__

	@view.setter
	def view(self, matrix: Math.TransformMatrix3D) -> None:
		"""
		Sets the view matrix
		:param matrix: The new view matrix
		:raises InvalidArgumentException: If 'matrix' is not a TransformMatrix3D instance
		"""

		Misc.raise_ifn(isinstance(matrix, Math.TransformMatrix3D), Exceptions.InvalidArgumentException(Camera.view.setter, 'matrix', type(matrix), (Math.TransformMatrix3D,)))
		self.__view__ = matrix
		self.__view_projection__ = self.view @ self.projection

	@projection.setter
	def projection(self, matrix: Math.TransformMatrix3D) -> None:
		"""
		Sets the projection matrix
		:param matrix: The new projection matrix
		:raises InvalidArgumentException: If 'matrix' is not a TransformMatrix3D instance
		"""

		Misc.raise_ifn(isinstance(matrix, Math.TransformMatrix3D), Exceptions.InvalidArgumentException(Camera.projection.setter, 'matrix', type(matrix), (Math.TransformMatrix3D,)))
		self.__projection__ = matrix
		self.__view_projection__ = self.view @ self.projection


__all__: list[str] = ['Camera']
