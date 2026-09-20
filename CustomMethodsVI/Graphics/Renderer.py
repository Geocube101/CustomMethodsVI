from __future__ import annotations

import collections.abc
import cv2
import dearpygui.dearpygui as dpg
import math
import numpy as np
import PIL.Image
import PIL.ImageDraw
import tkinter
import typing
import os

from . import Camera
from . import Material
from . import Math
from . import Poly
from . import Util
from .. import Exceptions
from .. import Misc
from .. import Stream


class Renderer3D:
	"""
	Base class for a rendering queue
	"""

	def __init__(self):
		"""
		Base class for a rendering queue
		"""

		self.__meshes__: list[Poly.Mesh3D] = []
		self.__polygons__: list[Poly.Polygon3D] = []
		self.__cameras__: list[Camera.Camera] = []
		self.__active_camera__: Camera.Camera = ...
		self.__sun__: typing.Optional[Math.Vector3] = None

	def add_cameras[T: Renderer3D](self: T, camera: Camera.Camera, *cameras: Camera.Camera) -> T:
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

	def add_meshes[T: Renderer3D](self: T, mesh: Poly.Mesh3D, *meshes: Poly.Mesh3D) -> T:
		"""
		Adds one or more meshes to the rendering queue
		:param mesh: The first mesh
		:param meshes: The remaining meshes
		:raises TypeError: If one or more meshes is not a PolyShape3D instance
		:return: This renderer
		"""

		meshes: tuple[Poly.Mesh3D, ...] = (mesh, *meshes)

		for mesh in meshes:
			if not isinstance(mesh, Poly.Mesh3D):
				raise TypeError('One or more meshes are invalid')

		self.__meshes__.extend(meshes)
		return self

	def add_polygons[T: Renderer3D](self: T, polygon: Poly.Polygon3D, *polygons: Poly.Polygon3D) -> T:
		"""
		Adds one or more triangles to the rendering queue
		:param polygon: The first triangle
		:param polygons: The remaining triangles
		:raises TypeError: If one or more triangles is not a Triangle3D instance
		:return: This renderer
		"""

		polygons: tuple[Poly.Polygon3D, ...] = (polygon, *polygons)

		for polygon in polygons:
			if not isinstance(polygon, Poly.Polygon3D):
				raise TypeError('One or more polygons are invalid')

		self.__polygons__.extend(polygons)
		return self

	def remove_cameras(self, *cameras: Camera.Camera) -> None:
		if len(cameras) == 0:
			self.__cameras__.clear()
		else:
			Stream.LinqStream(self.__cameras__).filter(lambda camera: camera not in cameras).apply(self.__cameras__)

	def remove_meshes(self, *meshes: Poly.Mesh3D) -> None:
		if len(meshes) == 0:
			self.__meshes__.clear()
		else:
			Stream.LinqStream(self.__meshes__).filter(lambda mesh: mesh not in meshes).apply(self.__meshes__)

	def remove_polygons(self, *polygons: Poly.Polygon3D) -> None:
		if len(polygons) == 0:
			self.__polygons__.clear()
		else:
			Stream.LinqStream(self.__polygons__).filter(lambda polygon: polygon not in polygons).apply(self.__polygons__)

	def render(self) -> None:
		"""
		ABSTRACT METHOD\n
		Renders the queue to the viewport
		"""

		pass

	@property
	def is_sun_enabled(self) -> bool:
		"""
		:return: Whether this renderer has a sun normal
		"""

		return self.sun_normal is not None

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
	def sun_normal(self) -> typing.Optional[Math.Vector3]:
		"""
		:return: This renderer's sun normal
		"""

		return self.__sun__

	@sun_normal.setter
	def sun_normal(self, normal: typing.Optional[Math.Vector3]) -> None:
		"""
		Sets this renderer's sun normal
		:param normal: The normal or None to clear
		"""

		Misc.raise_ifn(normal is None or isinstance(normal, Math.Vector3), Exceptions.InvalidArgumentException(Renderer3D.sun_normal.setter, 'normal', type(normal), (Math.Vector3,)))
		self.__sun__ = None if normal is None else normal.normalized()

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

		Misc.raise_ifn(isinstance(camera, Camera.Camera), Exceptions.InvalidArgumentException(Renderer3D.active_camera.setter, 'camera', type(camera), (Camera.Camera,)))
		Misc.raise_ifn(camera in self.cameras, ValueError('Camera not in renderer'))
		self.__active_camera__ = camera

	@property
	def cameras(self) -> list[Camera.Camera]:
		"""
		:return: This renderer's bound cameras
		"""

		return self.__cameras__

	@property
	def meshes(self) -> list[Poly.Mesh3D]:
		"""
		:return: This renderer's queued meshes
		"""

		return self.__meshes__

	@property
	def enabled_meshes(self) -> collections.abc.Iterator[Poly.Mesh3D]:
		"""
		:return: This renderer's enabled queued meshes
		"""

		for mesh in self.__meshes__:
			if mesh.enabled:
				yield mesh

	@property
	def polygons(self) -> list[Poly.Polygon3D]:
		"""
		:return: This renderer's queued polygons
		"""

		return self.__polygons__


class TkinterRenderer3DCPU(Renderer3D):
	"""
	Renderer rendering to a tkinter canvas
	"""

	def __init__(self, canvas: tkinter.Canvas):
		"""
		Renderer rendering to a tkinter canvas
		:param canvas: The tkinter canvas
		:raises InvalidArgumentException: If 'canvas' is not a tkinter canvas
		"""

		Misc.raise_ifn(isinstance(canvas, tkinter.Canvas), Exceptions.InvalidArgumentException(TkinterRenderer3DCPU.__init__, 'canvas', type(canvas), (tkinter.Canvas,)))
		self.__canvas__: tkinter.Canvas = canvas
		self.__drawn__: list[tuple[int, int]] = []
		super().__init__()

	def render(self) -> None:
		Misc.raise_if(self.active_camera is None, ValueError('No active camera'))
		self.active_camera.open_draw_cache()
		polygons: tuple[Poly.Triangle3D, ...] = Stream.LinqStream(self.enabled_meshes).transform_many(lambda shape: shape.get_polygons()).merge(self.polygons).sort(lambda poly: self.active_camera.view.translation.distance_squared(poly.center), reverse=True).collect()
		transformed: collections.abc.Iterator[Poly.Polygon3D] = self.active_camera.polygons_world_to_screen(self.width, self.height, polygons)
		last_drawn: int = 0
		reverse: bool = self.active_camera.view.backward.angle(Math.Vector3.backward()) <= math.radians(90)

		for i, polygon in enumerate(transformed):
			if polygon is ...:
				continue
			elif (uv := polygon.material) is None:
				continue
			elif (material := uv.get_material(Material.SimpleMaterial)) is None:
				raise TypeError('CPU render only supports simple materials')

			points: tuple[tuple[float, float], ...] = tuple((x, y) for (x, y, z) in polygon.points)
			fill: Util.Color = material.fill
			outline: Util.Color = material.outline

			if self.is_sun_enabled:
				ratio: float = polygons[i].normal.angle(self.sun_normal) / math.pi
				ratio_v4: Math.Vector4 = Math.Vector4(ratio, ratio, ratio, 1)
				fill *= ratio_v4
				outline *= ratio_v4

			if last_drawn < len(self.__drawn__):
				shape_id: int = self.__drawn__[last_drawn][0]
				self.__canvas__.coords(shape_id, *points)
				self.__canvas__.itemconfigure(shape_id, state='normal', outline=str(outline)[:7], fill=str(fill)[:7])
				self.__drawn__[last_drawn] = (shape_id, i)
			else:
				shape_id: int = self.__canvas__.create_polygon(points, outline=str(outline)[:7], fill=str(fill)[:7])
				self.__drawn__.append((shape_id, i))

			last_drawn += 1

		for i, pair in enumerate(self.__drawn__[last_drawn:]):
			self.__canvas__.itemconfigure(pair[0], state='hidden')

		z_order: list[tuple[int, int]] = sorted(self.__drawn__, key=lambda p: p[1], reverse=reverse)

		for i in range(len(z_order) - 1):
			self.__canvas__.tag_lower(z_order[i][0], z_order[i + 1][0])

		self.active_camera.close_draw_cache()

	@property
	def width(self) -> int:
		current_width: int = self.__canvas__.winfo_width()
		return int(self.__canvas__.cget('width')) if current_width <= 1 else current_width

	@property
	def height(self) -> int:
		current_height: int = self.__canvas__.winfo_height()
		return int(self.__canvas__.cget('height')) if current_height <= 1 else current_height


class ImageRenderer3DCPU(Renderer3D):
	"""
	Renderer rendering to an image array
	"""

	def __init__(self, image: np.ndarray | collections.abc.Sequence[int]):
		"""
		Renderer rendering to an image array
		:param image: The image array to write to or the size (w, h) of the image to produce
		:raises InvalidArgumentException: If 'image' is not a numpy array of type uint8 or a valid size
		"""

		Misc.raise_ifn(isinstance(image, (collections.abc.Sequence, np.ndarray)), Exceptions.InvalidArgumentException(DearPyGuiRenderer3DCPU.__init__, 'image', type(image), (collections.abc.Sequence, np.ndarray)))
		self.__image__: np.ndarray = image if isinstance(image, np.ndarray) else np.zeros((int(image[1]), int(image[0]), 3), np.uint8)
		super().__init__()

	def render(self) -> None:
		Misc.raise_if(self.active_camera is None, ValueError('No active camera'))
		self.active_camera.open_draw_cache()
		polygons: tuple[Poly.Polygon3D, ...] = Stream.LinqStream(self.enabled_meshes).transform_many(lambda shape: shape.get_polygons()).merge(self.polygons).collect()
		transformed: collections.abc.Iterable[Poly.Polygon3D] = self.active_camera.polygons_world_to_screen(self.width, self.height, polygons)
		canvas: PIL.Image.Image = PIL.Image.new('RGB', self.size, '#000000')
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(canvas, 'RGBA')
		z_stack: list[tuple[float, Poly.Polygon3D]] = []
		i: int

		for i, polygon in enumerate(transformed):
			if polygon is ...:
				continue
			elif polygon.material is None:
				continue

			z_depth: float = polygons[i].points.average().distance(self.active_camera.view.translation)
			z_stack.append((z_depth, polygon))

		z_stack.sort(key=lambda pair: pair[0], reverse=True)

		for i, (z_depth, polygon) in enumerate(z_stack):
			if (material := polygon.material.get_material(Material.SimpleMaterial)) is None:
				raise TypeError('CPU render only supports simple materials')

			points: tuple[tuple[float, float], ...] = tuple((round(x), round(y)) for x, y, z in polygon.points)
			fill: Util.Color = material.fill
			outline: Util.Color = material.outline

			if self.is_sun_enabled:
				ratio: float = polygons[i].normal.angle(self.sun_normal) / math.pi
				ratio_v4: Math.Vector4 = Math.Vector4(ratio, ratio, ratio, 1)
				fill *= ratio_v4
				outline *= ratio_v4

			drawer.polygon(points, fill.rgba, outline.rgba)

		self.__image__[:, :, :] = cv2.cvtColor(np.asarray(canvas, dtype=np.uint8), cv2.COLOR_RGB2BGR)
		self.active_camera.close_draw_cache()

	@property
	def image(self) -> np.ndarray:
		"""
		:return: The underlying image array
		"""

		return self.__image__

	@property
	def size(self) -> tuple[int, int]:
		h, w, _ = self.__image__.shape
		return w, h

	@property
	def width(self) -> int:
		return self.__image__.shape[1]

	@property
	def height(self) -> int:
		return self.__image__.shape[0]


if os.name == 'nt':
	class DearPyGuiRenderer3DCPU(Renderer3D):
		"""
		Renderer rendering to a dearpygui drawlist
		"""

		def __init__(self, drawlist: int | str):
			"""
			Renderer rendering to a dearpygui drawlist
			:param drawlist: The dearpygui drawlist ID
			:raises InvalidArgumentException: If 'drawlist' is not an integer or string
			"""

			Misc.raise_ifn(isinstance(drawlist, (int, str)), Exceptions.InvalidArgumentException(DearPyGuiRenderer3DCPU.__init__, 'drawlist', type(drawlist), (int, str)))
			self.__drawlist__: int | str = drawlist
			self.__drawn__: list[tuple[int, int]] = []
			super().__init__()

		def render(self) -> None:
			Misc.raise_if(self.active_camera is None, ValueError('No active camera'))
			self.active_camera.open_draw_cache()
			polygons: tuple[Poly.Polygon3D, ...] = Stream.LinqStream(self.enabled_meshes).transform_many(lambda shape: shape.get_polygons()).merge(self.polygons).collect()
			transformed: collections.abc.Iterable[Poly.Polygon3D] = self.active_camera.polygons_world_to_screen(self.width, self.height, polygons)
			last_drawn: int = 0
			reverse: bool = self.active_camera.view.backward.angle(Math.Vector3.backward()) <= math.radians(90)

			for i, polygon in enumerate(transformed):
				if polygon is ...:
					continue
				elif (uv := polygon.material) is None:
					continue
				elif (material := uv.get_material(Material.SimpleMaterial)) is None:
					raise TypeError('CPU render only supports simple materials')

				points: tuple[tuple[float, float], ...] = tuple((x, y) for x, y, z in polygon.points)
				fill: Util.Color = material.fill
				outline: Util.Color = material.outline

				if self.is_sun_enabled:
					ratio: float = polygons[i].normal.angle(self.sun_normal) / math.pi
					ratio_v4: Math.Vector4 = Math.Vector4(ratio, ratio, ratio, 1)
					fill *= ratio_v4
					outline *= ratio_v4

				if last_drawn < len(self.__drawn__):
					shape_id: int = self.__drawn__[last_drawn][0]
					dpg.configure_item(shape_id, points=points, show=True, color=outline.rgba, fill=fill.rgba)
					self.__drawn__[last_drawn] = (shape_id, i)
				else:
					shape_id: int = dpg.draw_polygon([[x, y] for x, y in points], color=outline.rgba, fill=fill.rgba, parent=self.__drawlist__)
					self.__drawn__.append((shape_id, i))

				last_drawn += 1

			for i, pair in enumerate(self.__drawn__[last_drawn:]):
				dpg.configure_item(pair[0], show=False)

			z_order: list[tuple[int, int]] = sorted(self.__drawn__, key=lambda p: p[1], reverse=reverse)

			for i in range(len(z_order) - 1):
				dpg.move_item(z_order[i][0], before=z_order[i + 1][0])

			self.active_camera.close_draw_cache()

		@property
		def width(self) -> int:
			return dpg.get_item_width(self.__drawlist__)

		@property
		def height(self) -> int:
			return dpg.get_item_height(self.__drawlist__)


	__all__: list[str] = ['Renderer3D', 'TkinterRenderer3DCPU', 'ImageRenderer3DCPU', 'DearPyGuiRenderer3DCPU']
else:
	__all__: list[str] = ['Renderer3D', 'TkinterRenderer3DCPU', 'ImageRenderer3DCPU']
