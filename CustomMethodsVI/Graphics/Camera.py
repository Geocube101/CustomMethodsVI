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

		return Math.TransformMatrix3D.create_world((target - position).normalized(), up.normalized(), position)

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
		fa: float = (far + near) / (near - far)
		fb: float = (2 * far * near) / (near - far)

		return Math.TransformMatrix3D((
			00, 00, fz, 1,
			00, fy, 00, 00,
			fa, 00, 00, 00,
			fb, 00, 00, 00
		))

	def __init__(self, view_matrix: Math.TransformMatrix3D, projection_matrix: Math.TransformMatrix3D, *, cull_faces: bool = True):
		"""
		Class representing a camera in 3D space
		:param view_matrix: The camera's view matrix
		:param projection_matrix: The camera's projection matrix
		:param cull_faces: Whether to cull faces facing away from camera
		"""

		Misc.raise_ifn(isinstance(view_matrix, Math.TransformMatrix3D), Exceptions.InvalidArgumentException(Camera.__init__, 'view_matrix', type(view_matrix), (Math.TransformMatrix3D,)))
		Misc.raise_ifn(isinstance(projection_matrix, Math.TransformMatrix3D), Exceptions.InvalidArgumentException(Camera.__init__, 'projection_matrix', type(projection_matrix), (Math.TransformMatrix3D,)))
		self.__view__: Math.TransformMatrix3D = view_matrix
		self.__projection__: Math.TransformMatrix3D = projection_matrix
		self.__view_projection__: Math.TransformMatrix3D = self.view.inversed() @ self.projection
		self.__point_cache__: dict[Math.Vector3, Math.Vector3] = ...
		self.__cull_faces__: bool = bool(cull_faces)

	def open_draw_cache(self) -> None:
		"""
		Opens the draw cache\n
		Draw conversions are cached to reduce overhead
		:raise RuntimeError: If the cache is already opened
		"""

		if self.__point_cache__ is not ...:
			raise RuntimeError('Draw cache already open')

		self.__point_cache__ = {}

	def close_draw_cache(self) -> None:
		"""
		Closes the draw cache
		:raise RuntimeError: If the cache is already closed
		"""

		if self.__point_cache__ is ...:
			raise RuntimeError('Draw cache not open')

		self.__point_cache__.clear()
		self.__point_cache__ = ...

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
		translation: Math.Vector3 = self.view.translation
		self.view.translation = Math.Vector3.zero()
		result: Math.TransformMatrix3D = scale @ self.view
		result.translation = translation
		self.view = result
		return self

	def set_position(self, x: float, y: float, z: float) -> Camera:
		"""
		Sets this camera's position
		:param x: The x position
		:param y: The y position
		:param z: The z position
		:return: This camera
		"""

		view: Math.TransformMatrix3D = self.view
		view.translation = Math.Vector3(x, y, z)
		self.view = view
		return self

	def points_world_to_screen(self, screen_width: int, screen_height: int, points: collections.abc.Iterable[Math.Vector3]) -> collections.abc.Iterator[Math.Vector3]:
		"""
		Converts the specified points from world space into screen space\n
		Points out of bounds will be '...'
		:param screen_width: The screen width
		:param screen_height: The screen height
		:param points: The points to transform
		:return: All transformed points in front of the camera
		"""

		aspect: float = screen_width / screen_height / math.sqrt(2)

		for point in points:
			if self.is_draw_cache_opened and (converted := self.__point_cache__.get(point)) is not None:
				yield converted
				continue

			full_clip: Math.Vector4 = self.view_projection.transform_vector(Math.Vector4(*point, 1))

			if full_clip.w <= 0 and self.is_draw_cache_opened:
				self.__point_cache__[point] = ...
				yield ...
				continue
			elif full_clip.w <= 0:
				yield ...
				continue

			ndc: Math.Vector3 = full_clip[:3] / full_clip.w / Math.Vector3(aspect, 1, 1)
			screen: Math.Vector3 = Math.Vector3((ndc.x + 1) / 2 * screen_width, (1 - (ndc.y + 1) / 2) * screen_height, (ndc.z + 1) / 2)

			if self.is_draw_cache_opened:
				self.__point_cache__[point] = screen

			yield screen

	def polygons_world_to_screen(self, screen_width: int, screen_height: int, polygons: collections.abc.Iterable[Poly.Polygon3D]) -> collections.abc.Iterator[Poly.Polygon3D]:
		"""
		Converts the specified polygons from world space into screen space\n
		Polygons out of bounds will be '...'
		:param screen_width: The screen width
		:param screen_height: The screen height
		:param polygons: The polygons to transform
		:return: All transformed polygons fully in front of the camera
		"""

		view_direction: Math.Vector3 = self.view.backward

		for polygon in polygons:
			if polygon.material is None or (self.cull_faces and view_direction.dot(polygon.normal) <= 0):
				yield ...
				continue

			points: tuple[Math.Vector3, ...] = tuple(self.points_world_to_screen(screen_width, screen_height, polygon.points))

			if ... in points:
				yield ...
				continue

			yield Poly.Polygon3D(*points, uv_mat=polygon.material, invert_normal=polygon.is_normal_inverted)

	def shapes_world_to_screen(self, screen_width: int, screen_height: int, shapes: collections.abc.Iterable[Poly.Mesh3D]) -> collections.abc.Iterator[Poly.Mesh3D]:

		"""
		Converts the specified shapes from world space into screen space\n
		Shapes out of bounds will be '...'
		:param screen_width: The screen width
		:param screen_height: The screen height
		:param shapes: The shapes to transform
		:return: All transformed shapes fully in front of the camera
		"""

		for shape in shapes:
			if not shape.enabled:
				continue

			shape_polygons: tuple[Poly.Polygon3D, ...] = tuple(shape.get_polygons())
			polygons: tuple[Poly.Polygon3D, ...] = tuple(self.polygons_world_to_screen(screen_width, screen_height, shape_polygons))

			if ... in polygons:
				yield ...
				continue

			yield Poly.Mesh3D(Math.TransformMatrix3D.identity(), polygons)

	@property
	def is_draw_cache_opened(self) -> bool:
		"""
		:return: Whether the draw cache is open
		"""

		return self.__point_cache__ is not ...

	@property
	def cull_faces(self) -> bool:
		"""
		:return: Whether faces facing away from camera are culled
		"""

		return self.__cull_faces__

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
		self.__view_projection__ = self.view.inversed() @ self.projection

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


class VectorizedCamera(Camera):
	def points_world_to_screen(self, screen_width: int, screen_height: int, points: collections.abc.Iterable[Math.Vector3]) -> collections.abc.Iterator[Math.Vector3]:
		points: tuple[Math.Vector3, ...] = tuple(points)

		if len(points) == 0:
			return

		aspect: float = screen_width / screen_height / math.sqrt(2)
		matrix: Math.NUMPY.ndarray = self.view_projection.array
		array: Math.NUMPY.ndarray = Math.NUMPY.array(tuple((x, y, z, 1) for (x, y, z) in points), Math.NUMPY.float64)
		full_clip: Math.NUMPY.ndarray = Math.NUMPY.matmul(array, matrix)
		ndc: Math.NUMPY.ndarray = full_clip[:, :3] / full_clip[:, 3:] / Math.NUMPY.asarray((aspect, 1, 1), Math.NUMPY.float64)
		screen: Math.NUMPY.ndarray = ndc
		screen[:, 0] = (ndc[:, 0] + 1) / 2 * screen_width
		screen[:, 1] = (1 - (ndc[:, 1] + 1) / 2) * screen_height
		screen[:, 2] = (ndc[:, 2] + 1) / 2

		for i, (x, y, z) in enumerate(screen):
			if full_clip[i, 3] <= 0:
				yield ...
			else:
				sx: float = float(x)
				sy: float = float(y)
				sz: float = float(z)
				yield Math.Vector3(sx, sy, sz)

	def polygons_world_to_screen(self, screen_width: int, screen_height: int, polygons: collections.abc.Iterable[Poly.Polygon3D]) -> collections.abc.Iterator[Poly.Polygon3D]:
		polygons: tuple[Poly.Polygon3D, ...] = tuple(polygons)

		if len(polygons) == 0:
			return

		view_direction: Math.Vector3 = self.view.backward
		aspect: float = screen_width / screen_height / math.sqrt(2)
		matrix: Math.NUMPY.ndarray = Math.NUMPY.asarray(self.view_projection.array)
		highest_count: int = max(len(polygon.points) for polygon in polygons)
		nan: float = float('nan')
		all_points: Math.CPU.ndarray = Math.CPU.full((len(polygons), highest_count, 4), nan, Math.NUMPY.float64)
		all_points[:, :, 3] = 1

		for i, polygon in enumerate(polygons):
			all_points[i, :len(polygon.points), :3] = polygon.points.array

		if Math.NUMPY.__name__ == 'cupy':
			all_points = Math.GPU.asarray(all_points)

		full_clip: Math.NUMPY.ndarray = Math.NUMPY.matmul(all_points, matrix)
		ndc: Math.NUMPY.ndarray = full_clip[:, :, :3] / full_clip[:, :, 3:] / Math.NUMPY.asarray((aspect, 1, 1), Math.NUMPY.float64)
		screen: Math.NUMPY.ndarray = ndc
		screen[:, :, 0] = (ndc[:, :, 0] + 1) / 2 * screen_width
		screen[:, :, 1] = (1 - (ndc[:, :, 1] + 1) / 2) * screen_height
		screen[:, :, 2] = (ndc[:, :, 2] + 1) / 2
		points: Math.NUMPY.ndarray

		for i, points in enumerate(screen):
			source: Poly.Polygon3D = polygons[i]
			clip: Math.NUMPY.ndarray = full_clip[i, :, 3]

			if source.material is None or (self.cull_faces and view_direction.dot(source.normal) <= 0) or clip[clip <= 0].size > 0:
				yield ...
				continue

			result: tuple[Math.Vector3, ...] = tuple(Math.Vector3(float(x), float(y), float(z)) for x, y, z in points[:len(source.points)])
			yield Poly.Polygon3D(*result, uv_mat=source.material, invert_normal=source.is_normal_inverted)


__all__: list[str] = ['Camera', 'VectorizedCamera']
