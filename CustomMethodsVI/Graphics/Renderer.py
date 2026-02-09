from __future__ import annotations

import math

import dearpygui.dearpygui as dpg
import tkinter
import typing
import warnings

from . import Camera
from . import Material
from . import Math
from . import Poly
from .. import Exceptions
from .. import Misc
from .. import Stream


class Renderer:
	"""
	Base class for a rendering queue
	"""

	def __init__(self):
		"""
		Base class for a rendering queue
		"""

		self.__meshes__: list[Poly.PolyShape3D] = []
		self.__triangles__: list[Poly.Triangle3D] = []
		self.__cameras__: list[Camera.Camera] = []
		self.__active_camera__: Camera.Camera = ...

	def add_cameras[T: Renderer](self: T, camera: Camera.Camera, *cameras: Camera.Camera) -> T:
		"""
		Adds one or more cameras to the rendering queue
		:param camera: The first camera
		:param cameras: The remaining cameras
		:raises TypeError: If one or more cameras is not a Camera instance
		:return: This renderer
		"""

		cameras: tuple[Camera.Camera, ...] = (camera, *cameras)

		for camera in cameras:
			if not isinstance(camera, Camera.Camera):
				raise TypeError('One or more cameras are invalid')

		self.__cameras__.extend(cameras)
		return self

	def add_meshes[T: Renderer](self: T, mesh: Poly.PolyShape3D, *meshes: Poly.PolyShape3D) -> T:
		"""
		Adds one or more meshes to the rendering queue
		:param mesh: The first mesh
		:param meshes: The remaining meshes
		:raises TypeError: If one or more meshes is not a PolyShape3D instance
		:return: This renderer
		"""

		meshes: tuple[Poly.PolyShape3D, ...] = (mesh, *meshes)

		for mesh in meshes:
			if not isinstance(mesh, Poly.PolyShape3D):
				raise TypeError('One or more meshes are invalid')

		self.__meshes__.extend(meshes)
		return self

	def add_triangles[T: Renderer](self: T, triangle: Poly.Triangle3D, *triangles: Poly.Triangle3D) -> T:
		"""
		Adds one or more triangles to the rendering queue
		:param triangle: The first triangle
		:param triangles: The remaining triangles
		:raises TypeError: If one or more triangles is not a Triangle3D instance
		:return: This renderer
		"""

		triangles: tuple[Poly.Triangle3D, ...] = (triangle, *triangles)

		for triangle in triangles:
			if not isinstance(triangle, Poly.Triangle3D):
				raise TypeError('One or more triangles are invalid')

		self.__triangles__.extend(triangles)
		return self

	def render(self) -> None:
		"""
		ABSTRACT METHOD\n
		Renders the queue to the viewport
		"""

		pass

	@property
	def width(self) -> int:
		"""
		ABSTRACT PROPERTY
		:return: The viewport's width
		"""

		return 0

	@property
	def height(self) -> int:
		"""
		ABSTRACT PROPERTY
		:return: The viewport's height
		"""

		return 0

	@property
	def active_camera(self) -> typing.Optional[Camera.Camera]:
		"""
		:return: The rendering queue's active camera
		"""

		return None if self.__active_camera__ is ... else self.__active_camera__

	@active_camera.setter
	def active_camera(self, camera: Camera.Camera) -> None:
		"""
		Sets the rendering queue's active camera\n
		Camera must be a part of this queue
		:param camera: The active camera
		:raises ValueError: If camera is not a part of this queue
		"""

		Misc.raise_ifn(isinstance(camera, Camera.Camera), Exceptions.InvalidArgumentException(Renderer.active_camera.setter, 'camera', type(camera), (Camera.Camera,)))
		Misc.raise_ifn(camera in self.cameras, ValueError('Camera not in renderer'))
		self.__active_camera__ = camera

	@property
	def cameras(self) -> list[Camera.Camera]:
		"""
		:return: This renderer's bound cameras
		"""

		return self.__cameras__

	@property
	def meshes(self) -> list[Poly.PolyShape3D]:
		"""
		:return: This renderer's queued meshes
		"""

		return self.__meshes__

	@property
	def triangles(self) -> list[Poly.Triangle3D]:
		"""
		:return: This renderer's queued triangles
		"""

		return self.__triangles__


class TkinterRendererCPU(Renderer):
	"""
	Renderer rendering to a tkinter canvas
	"""

	def __init__(self, canvas: tkinter.Canvas):
		"""
		Renderer rendering to a tkinter canvas
		:param canvas: The tkinter canvas
		:raises InvalidArgumentException: If 'canvas' is not a tkinter canvas
		"""

		Misc.raise_ifn(isinstance(canvas, tkinter.Canvas), Exceptions.InvalidArgumentException(TkinterRendererCPU.__init__, 'canvas', type(canvas), (tkinter.Canvas,)))
		self.__canvas__: tkinter.Canvas = canvas
		self.__drawn__: list[tuple[int, int]] = []
		super().__init__()

	def render(self) -> None:
		Misc.raise_if(self.active_camera is None, ValueError('No active camera'))
		triangles: tuple[Poly.Triangle3D, ...] = Stream.LinqStream(self.meshes).transform_many(lambda shape: shape.get_triangles()).merge(self.triangles).sort(lambda tri: self.active_camera.view.translation.distance_squared(tri.center), reverse=True).collect()
		transformed: tuple[Poly.Triangle3D, ...] = self.active_camera.triangles_world_to_screen(self.width, self.height, *triangles)
		last_drawn: int = 0
		reverse: bool = self.active_camera.view.backward.angle(Math.Vector3.backward()) <= math.radians(90)

		for i, triangle in enumerate(transformed):
			if (uv := triangle.material) is None:
				continue
			elif (material := uv.get_material(Material.SimpleMaterial)) is None:
				raise TypeError('CPU render only supports simple materials')

			points: tuple[tuple[float, float], ...] = tuple((x, y) for (x, y, z) in triangle.points)

			if last_drawn < len(self.__drawn__):
				shape_id: int = self.__drawn__[last_drawn][0]
				self.__canvas__.coords(shape_id, *points)
				self.__canvas__.itemconfigure(shape_id, state='normal')
				self.__drawn__[last_drawn] = (shape_id, i)
			else:
				shape_id: int = self.__canvas__.create_polygon(points, outline=str(material.outline)[:7], fill=str(material.fill)[:7])
				self.__drawn__.append((shape_id, i))

			last_drawn += 1

		for i, pair in enumerate(self.__drawn__[last_drawn:]):
			self.__canvas__.itemconfigure(pair[0], state='hidden')

		z_order: list[tuple[int, int]] = sorted(self.__drawn__, key=lambda p: p[1], reverse=reverse)

		for i in range(len(z_order) - 1):
			self.__canvas__.tag_lower(z_order[i][0], z_order[i + 1][0])

	@property
	def width(self) -> int:
		current_width: int = self.__canvas__.winfo_width()
		return int(self.__canvas__.cget('width')) if current_width <= 1 else current_width

	@property
	def height(self) -> int:
		current_height: int = self.__canvas__.winfo_height()
		return int(self.__canvas__.cget('height')) if current_height <= 1 else current_height


class DearPyGuiRendererCPU(Renderer):
	"""
	Renderer rendering to a dearpygui drawlist
	"""

	def __init__(self, drawlist: int | str):
		"""
		Renderer rendering to a dearpygui drawlist
		:param drawlist: The dearpygui drawlist ID
		:raises InvalidArgumentException: If 'drawlist' is not an integer or string
		"""

		Misc.raise_ifn(isinstance(drawlist, (int, str)), Exceptions.InvalidArgumentException(DearPyGuiRendererCPU.__init__, 'drawlist', type(drawlist), (int, str)))
		self.__drawlist__: int | str = drawlist
		self.__drawn__: list[tuple[int, int]] = []
		super().__init__()

	def render(self) -> None:
		Misc.raise_if(self.active_camera is None, ValueError('No active camera'))
		triangles: tuple[Poly.Triangle3D, ...] = Stream.LinqStream(self.meshes).transform_many(lambda shape: shape.get_triangles()).merge(self.triangles).sort(lambda tri: self.active_camera.view.translation.distance_squared(tri.center), reverse=True).collect()
		transformed: tuple[Poly.Triangle3D, ...] = self.active_camera.triangles_world_to_screen(self.width, self.height, *triangles)
		last_drawn: int = 0
		reverse: bool = self.active_camera.view.backward.angle(Math.Vector3.backward()) <= math.radians(90)

		for i, triangle in enumerate(transformed):
			if (uv := triangle.material) is None:
				continue
			elif (material := uv.get_material(Material.SimpleMaterial)) is None:
				raise TypeError('CPU render only supports simple materials')

			p1, p2, p3 = tuple((x, y) for x, y, z in triangle.points)

			if last_drawn < len(self.__drawn__):
				shape_id: int = self.__drawn__[last_drawn][0]
				dpg.configure_item(shape_id, p1=p1, p2=p2, p3=p3, show=True)
				self.__drawn__[last_drawn] = (shape_id, i)
			else:
				shape_id: int = dpg.draw_triangle(p1, p2, p3, color=material.outline.rgba, fill=material.fill.rgba, parent=self.__drawlist__)
				self.__drawn__.append((shape_id, i))

			last_drawn += 1

		for i, pair in enumerate(self.__drawn__[last_drawn:]):
			dpg.configure_item(pair[0], show=False)

		z_order: list[tuple[int, int]] = sorted(self.__drawn__, key=lambda p: p[1], reverse=reverse)

		for i in range(len(z_order) - 1):
			dpg.move_item(z_order[i][0], before=z_order[i + 1][0])

	@property
	def width(self) -> int:
		return dpg.get_item_width(self.__drawlist__)

	@property
	def height(self) -> int:
		return dpg.get_item_height(self.__drawlist__)


__all__: list[str] = ['Renderer', 'TkinterRendererCPU', 'DearPyGuiRendererCPU']
