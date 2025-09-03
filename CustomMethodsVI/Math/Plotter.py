from __future__ import annotations

import colorsys
import inspect
import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageTk
import math
import matplotlib.cm
import numpy
import numpy.exceptions
import numpy.polynomial.polyutils
import scipy
import sys
import typing
import tkinter
import warnings

from ..Math import Vector
from ..Math.Statistics import Functions as Stats
from .. import Iterable
from .. import Misc


class AxisPlot2D(object):
	"""
	Base class representing plots with axes
	"""

	class Axis:
		"""
		Class representing a single plot axis
		"""

		def __init__(self, name: str, center: tuple[float, float], angle: float, color: int, minor_spacing: float | None, major_spacing: int | None, tick_offset: int):
			"""
			Class representing a single plot axis
			- Constructor -
			:param name: The axis name
			:param center: The axis plot-local position
			:param angle: The axis angle in degrees
			:param color: The axis hex encoded RGBA color
			:param minor_spacing: The plot spacing between minor ticks or None to disable
			:param major_spacing: The number of minor ticks between major ticks or None to disable
			:param tick_offset: The amount of minor ticks to shift major ticks
			"""

			self.__axis_name__: str = str(name)
			self.__position__: tuple[float, float] = (float(center[0]), float(center[1]))
			self.__angle__: float = float(angle)
			self.__color__: int = int(color) & 0xFFFFFFFF
			self.__minor_spacing__: float | None = None if minor_spacing is None else float(minor_spacing)
			self.__major_spacing__: int | None = None if major_spacing is None else int(major_spacing)
			self.__tick_offset__: int = int(tick_offset)

		def axis_info(self, *, center: tuple[float, float] = ..., angle: float = ..., color: int = ..., minor_spacing: float | None = ..., major_spacing: int | None = ..., tick_offset: int = ...) -> None:
			"""
			Modifies this axis's attributes
			Any attribute left blank will not be updated
			:param center: The new axis plot-local position
			:param angle: The new axis angle in degrees
			:param color: The new axis hex encoded RGBA color
			:param minor_spacing: The new plot spacing between minor ticks or None to disable
			:param major_spacing: The new number of minor ticks between major ticks or None to disable
			:param tick_offset: The new amount of minor ticks to shift major ticks
			"""

			if center is not None and center is not ...:
				assert hasattr(center, '__iter__') and len(center := tuple(center)) == 2 and all(isinstance(x, (float, int)) for x in center), 'Center must be an iterable with 2 numerical coordinates'

			self.__color__ = self.__color__ if color is ... or color is None else (int(color) & 0xFFFFFFFF)
			self.__angle__ = self.__angle__ if angle is ... or angle is None else float(angle) % 360
			self.__position__ = self.__position__ if center is ... or center is None else center
			self.__minor_spacing__: float | None = self.__minor_spacing__ if minor_spacing is ... else None if minor_spacing is None else float(minor_spacing)
			self.__major_spacing__: int | None = self.__major_spacing__ if major_spacing is ... else None if major_spacing is None else int(major_spacing)
			self.__tick_offset__: int = self.__tick_offset__ if tick_offset is ... or tick_offset is None else int(tick_offset)

		@property
		def name(self) -> str:
			"""
			:return: The name of this axis
			"""

			return self.__axis_name__

		@property
		def position(self) -> tuple[float, float]:
			"""
			:return: The plot-local position of this axis
			"""

			return self.__position__

		@position.setter
		def position(self, position: tuple[float, float]) -> None:
			"""
			The plot-local position of this axis
			:param position: The new position
			:raises ValueError: If the new position is not iterable, has a length other than 2, or contains non-numerical values
			"""

			Misc.raise_ifn(hasattr(position, '__iter__') and len(position := tuple(position)) == 2 and all(isinstance(x, (float, int)) for x in position), ValueError('Position must be an iterable with 2 numerical coordinates'))
			self.__position__ = position

		@property
		def angle(self) -> float:
			"""
			:return: The axis angle in degrees
			"""

			return self.__angle__

		@angle.setter
		def angle(self, angle: float) -> None:
			"""
			The axis angle in degrees
			:param angle: The new angle in degrees
			"""

			self.__angle__ = float(angle) % 360

		@property
		def color(self) -> int:
			"""
			:return: The hex encoded RGBA color
			"""

			return self.__color__

		@color.setter
		def color(self, color: int) -> None:
			"""
			The hex encoded RGBA color
			:param color: The new axis color
			"""

			self.__color__ = int(color) & 0xFFFFFFFF

		@property
		def minor_spacing(self) -> float:
			"""
			:return: The number of graph units between minor ticks
			"""

			return self.__minor_spacing__

		@minor_spacing.setter
		def minor_spacing(self, spacing: float) -> None:
			"""
			The number of graph units between minor ticks
			:param spacing: The new minor tick spacing
			"""

			self.__minor_spacing__ = abs(float(spacing))

		@property
		def major_spacing(self) -> int:
			"""
			:return: The number of minor ticks between major ticks
			"""
			return self.__major_spacing__

		@major_spacing.setter
		def major_spacing(self, spacing: int) -> None:
			"""
			The number of minor ticks between major ticks
			:param spacing: The new major tick spacing
			"""

			self.__major_spacing__ = abs(int(spacing))

		@property
		def tick_offset(self) -> int:
			"""
			:return: The amount of minor ticks to shift major ticks
			"""

			return self.__tick_offset__

		@tick_offset.setter
		def tick_offset(self, offset: int) -> None:
			"""
			The amount of minor ticks to shift major ticks
			:param offset: The new tick offset
			"""

			self.__tick_offset__ = abs(int(offset))

	def __init__(self, plot: Plot2D | MultiPlot2D):
		"""
		Base class representing plots with axes
		- Constructor -
		:param plot: The plot requiring axes
		"""

		super(AxisPlot2D, self).__init__()
		self.__source__: Plot2D | MultiPlot2D = plot
		self.__axes__: dict[str, AxisPlot2D.Axis] = {}

	def add_axis(self, name: str, center: tuple[float, float], angle: float = 0, color: int = 0xEEEEEEFF, minor_spacing: float = 1, major_spacing: int | None = None, tick_offset: int = 0) -> AxisPlot2D.Axis:
		"""
		Adds a new axis to the plot
		Must be called within the plot's __init__
		:param name: The name of the axis
		:param center: The graph space center of the axis
		:param angle: The angle of the axis in degrees
		:param color: The color of the axis in hex encoded RGBA
		:param minor_spacing: The graph spacing between minor ticks or None to disable
		:param major_spacing: The number of minor ticks between major ticks or None to disable
		:param tick_offset: The amount by which to offset axis ticks
		:return: The resulting axis
		"""

		assert any(call for call in inspect.stack() if call.function == '__init__' and any(isinstance(attr, AxisPlot2D) for attr in call.frame.f_locals.values())), 'Cannot add axis outside Plot2D initializer'

		if name in self.__axes__:
			raise KeyError(f'Axis \'{name}\' already defined')

		axis: AxisPlot2D.Axis = AxisPlot2D.Axis(name, center, angle, color, minor_spacing, major_spacing, tick_offset)
		self.__axes__[name] = axis
		return axis

	def axes_info(self, *axes: str, center: tuple[float, float] = ..., angle: float = ..., color: int = ..., minor_spacing: float | None = ..., major_spacing: int | None = ..., tick_offset: int = ...) -> None:
		"""
		Modifies attributes of the specified axes
		:param axes: The axes to modify
		:param center: The new graph local center
		:param angle: The new angle in degrees
		:param color: The color of the axis in hex encoded RGBA
		:param minor_spacing: (float) The spacing between minor ticks or None to disable
		:param major_spacing: (int) The number of minor ticks between major ticks or None to disable
		:param tick_offset: (int) The amount by which to offset axis ticks
		:return: (None)
		:raises KeyError: If the specified axis is not a part of this plot
		"""

		for axis in axes:
			if not isinstance(axis, str):
				raise TypeError(f'Axis name must be a string; got \'{type(axis)}\'')
			elif axis not in self.__axes__:
				raise KeyError(f'Axis \'{axis}\' is not a part of this plot')

			self.__axes__[axis].axis_info(center=center, angle=angle, color=color, minor_spacing=minor_spacing, major_spacing=major_spacing, tick_offset=tick_offset)

	def get_axis(self, axis: str) -> AxisPlot2D.Axis:
		"""
		Gets an axis by name
		:param axis: The axis name to get
		:return: The specified axis
		:raises KeyError: If the specified axis is not a part of this plot
		"""

		if not isinstance(axis, str):
			raise TypeError(f'Axis name must be a string; got \'{type(axis)}\'')
		elif axis not in self.__axes__:
			raise KeyError(f'Axis \'{axis}\' is not a part of this plot')
		else:
			return self.__axes__[axis]

	def draw_linear_axis(self, image: PIL.Image.Image, size: int, axis: str) -> AxisPlot2D:
		"""
		Draws a linear axis
		:param image: The PIL image to draw to
		:param size: The square size of the image
		:param axis: The axis name to draw
		:return: This graph
		"""

		if not isinstance(axis, str):
			raise TypeError(f'Axis name must be a string; got \'{type(axis)}\'')
		elif axis not in self.__axes__:
			raise KeyError(f'Axis \'{axis}\' is not a part of this plot')

		axis: AxisPlot2D.Axis = self.__axes__[axis]
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)
		diagonal: float = (size ** 2 + size ** 2) ** 0.5
		diagonal_radius: float = diagonal / 2
		center: Vector.Vector = Vector.Vector(axis.position)
		theta: float = round((axis.angle % 360) * math.pi / 180, 8)
		x: float = diagonal_radius * math.cos(theta)
		y: float = diagonal_radius * math.sin(theta)
		line_pos: Vector.Vector = Vector.Vector(x, y)
		line_p1: Vector.Vector = line_pos + center
		line_p2: Vector.Vector = -line_pos + center
		theta = round((theta + math.pi / 2) % (2 * math.pi), 8)
		tick_dir: Vector.Vector = Vector.Vector(math.cos(theta), math.sin(theta))
		image_line_p1: tuple[int, int] = self.__source__.plot_point_to_image_point((line_p1[0], line_p1[1]), size)
		image_line_p2: tuple[int, int] = self.__source__.plot_point_to_image_point((line_p2[0], line_p2[1]), size)

		r: int = (axis.color >> 24) & 0xFF
		g: int = (axis.color >> 16) & 0xFF
		b: int = (axis.color >> 8) & 0xFF
		a: int = axis.color & 0xFF
		drawer.line((*image_line_p1, *image_line_p2), (r, g, b, a), 1)

		x = 0
		tick_index: int = 0
		line_dir: Vector.Vector = (line_p1 - center).normalized()
		offset: Vector.Vector = line_dir * axis.tick_offset
		extent: float = max(self.__source__.extents())

		while x <= extent:
			is_major: bool = False if axis.major_spacing <= 0 else tick_index % axis.major_spacing == 0
			pixel_height: int = size // (64 if is_major else 128)
			pos1: Vector.Vector = center + line_dir * x + offset
			pos2: Vector.Vector = center - line_dir * x + offset
			impos1: Vector.Vector = self.__source__.plot_point_to_image_point(pos1, size)
			impos2: Vector.Vector = self.__source__.plot_point_to_image_point(pos2, size)
			tick1_pos1: Vector.Vector = round(impos1 + (tick_dir * pixel_height))
			tick1_pos2: Vector.Vector = round(impos1 - (tick_dir * pixel_height))
			tick2_pos1: Vector.Vector = round(impos2 + (tick_dir * pixel_height))
			tick2_pos2: Vector.Vector = round(impos2 - (tick_dir * pixel_height))
			drawer.line((*tick1_pos1.components(), *tick1_pos2.components()), (r, g, b, a), 1)
			drawer.line((*tick2_pos1.components(), *tick2_pos2.components()), (r, g, b, a), 1)
			x += axis.minor_spacing
			tick_index += 1

		return self

	def draw_radial_axis(self, image: PIL.Image.Image, size: int, axis: str) -> AxisPlot2D:
		"""
		Draws a radial axis
		:param image: The PIL image to draw to
		:param size: The square size of the image
		:param axis: The axis name to draw
		:return: This graph
		"""

		if not isinstance(axis, str):
			raise TypeError(f'Axis name must be a string; got \'{type(axis)}\'')
		elif axis not in self.__axes__:
			raise KeyError(f'Axis \'{axis}\' is not a part of this plot')

		axis: AxisPlot2D.Axis = self.__axes__[axis]
		radius: float = size / 2 * 0.95
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)
		image_center: tuple[int, int] = self.__source__.plot_point_to_image_point(axis.position, size)

		r: int = (axis.color >> 24) & 0xFF
		g: int = (axis.color >> 16) & 0xFF
		b: int = (axis.color >> 8) & 0xFF
		a: int = axis.color & 0xFF
		drawer.circle(image_center, radius, (0, 0, 0, 0), (r, g, b, a), 1)
		image_center: Vector.Vector = Vector.Vector(*image_center)

		angle = axis.angle * math.pi / 180
		theta: float = 0
		delta: float = axis.minor_spacing * math.pi / 180
		tick_index: int = 0

		while theta < math.pi * 2:
			tick_index += 1
			is_major: bool = False if axis.major_spacing <= 0 else tick_index % axis.major_spacing == 0
			pixel_height: int = size // (64 if is_major else 128)
			tx: float = radius * math.cos(theta + angle)
			ty: float = radius * math.sin(theta + angle)
			tick_dir: Vector.Vector = (Vector.Vector(tx, ty)).normalized() * pixel_height
			pos: Vector.Vector = Vector.Vector(tx, ty) + image_center
			pos1: Vector.Vector = pos + tick_dir
			pos2: Vector.Vector = pos - tick_dir
			drawer.line((*pos1.components(), *pos2.components()), (r, g, b, a), 1)
			theta += delta

		return self

class Plottable(object):
	"""
	Base class representing a plot that can be imaged
	"""

	def __init__(self):
		"""
		Base class representing a plot that can be imaged
		- Constructor -
		"""

		super(Plottable, self).__init__()
		self.__grid__: list[int] = [0, 0]
		self.__alpha__: float = 1
		self.__explicit_bounds__: tuple[float, float, float, float] | None = None

	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		"""
		- ABSTRACT -
		Overload this method to control plot drawing
		This method draws the specified plot to the given image
		:param image: The PIL image to draw to
		:param size: The square image size
		"""
		pass

	def show(self, *, square_size: int = 1024) -> None:
		"""
		Shows this plot in a tkinter window
		:param square_size: The square image size to render at
		"""

		square_size: int = int(square_size)
		root: tkinter.Tk = tkinter.Tk()
		root.overrideredirect(False)
		root.resizable(False, False)
		root.title(f'{type(self).__name__}@{hex(id(self))}')
		root.configure(background='#222222')

		canvas: tkinter.Canvas = tkinter.Canvas(root, background='#222222', highlightthickness=1, highlightcolor='#eeeeee', highlightbackground='#eeeeee', width=square_size, height=square_size)
		canvas.pack()

		image: numpy.ndarray[numpy.uint8] = self.as_image(square_size=square_size)
		pilmage: PIL.Image.Image = PIL.Image.fromarray(image)
		pilmage_tk: PIL.ImageTk.PhotoImage = PIL.ImageTk.PhotoImage(pilmage)
		canvas.create_image(0, 0, image=pilmage_tk, anchor='nw')

		root.mainloop()

	def save(self, filename: str, *, square_size: int = 1024) -> None:
		"""
		Saves this plot as a rendered image
		:param filename: The filepath to save to
		:param square_size: The square image size to render at
		"""

		image: PIL.Image.Image = PIL.Image.fromarray(self.as_image(square_size=square_size))
		image.save(filename)

	def plot_point_to_image_point(self, point: tuple[float, float] | Vector.Vector, size: int) -> tuple[int, int] | Vector.Vector:
		"""
		Converts a point from plot-space into image-space
		:param point: The plot-space point
		:param size: The square image size
		:return: The image-space point
		"""

		x, y = point
		bounds: tuple[float, float, float, float] = self.get_bounds()
		minx, maxx, miny, maxy = bounds
		rx: float = Misc.get_ratio(x, minx, maxx)
		ry: float = Misc.get_ratio(y, miny, maxy)
		fx: float = Misc.get_value(rx, 0, size)
		fy: float = Misc.get_value(1 - ry, 0, size)
		return Vector.Vector(round(fx), round(fy)) if isinstance(point, Vector.Vector) else (round(fx), round(fy))

	def image_point_to_plot_point(self, point: tuple[int, int] | Vector.Vector, size: int) -> tuple[float, float]:
		"""
		Converts a point from image-space into plot-space
		:param point: The image-space point
		:param size: The square image size
		:return: The plot-space point
		"""

		x, y = point
		bounds: tuple[float, float, float, float] = self.get_bounds()
		minx, maxx, miny, maxy = bounds
		rx: float = Misc.get_ratio(x, 0, size)
		ry: float = Misc.get_ratio(y, 0, size)
		fx: float = Misc.get_value(rx, minx, maxx)
		fy: float = Misc.get_value(1 - ry, miny, maxy)
		return Vector.Vector(fx, fy) if isinstance(point, Vector.Vector) else (fx, fy)

	def as_image(self, *, square_size: int = 1024) -> numpy.ndarray[numpy.uint8]:
		"""
		Renders this plot as an image
		:param square_size: The square image size to render as
		:return: The rendered RGBA image
		"""

		square_size: int = int(square_size)
		image: PIL.Image.Image = PIL.Image.new('RGBA', (square_size, square_size), '#222222')
		self.__draw__(image, square_size)
		return numpy.array(image)

	def set_bounds(self, minx: float | None, maxx: float | None, miny: float | None, maxy: float | None) -> Plottable:
		"""
		Sets the boundaries of this plot
		Data outside this bound will not be rendered
		Any 'None' values are infinite
		:param minx: The minimum x bound
		:param maxx: The maximum x bound
		:param miny: The minimum y bound
		:param maxy: The maximum y bound
		:return: This plot
		"""

		inf: float = float('inf')
		bounds: tuple[float, float, float, float] = (-inf if minx is None or minx is ... else float(minx), inf if maxx is None or maxx is ... else float(maxx), -inf if miny is None or miny is ... else float(miny), inf if maxy is None or maxy is ... else float(maxy))
		self.__explicit_bounds__ = None if all(b == inf for b in bounds) else bounds
		return self

	def get_bounds(self) -> tuple[float, float, float, float]:
		"""
		Gets the bounds of this plot
		Any infinite boundaries are set to 10
		:return: (min_x, max_x, min_y, max_y)
		"""

		minx, maxx, miny, maxy = (-10, 10, -10, 10) if self.__explicit_bounds__ is None else self.__explicit_bounds__
		inf: float = float('inf')
		return -10 if abs(minx) == inf else minx, 10 if abs(maxx) == inf else maxx, -10 if abs(miny) == inf else miny, 10 if abs(maxy) == inf else maxy

class Plot2D[PointType](Plottable):
	"""
	Base class representing a single 2D graph
	"""

	def __init__(self):
		"""
		Base class representing a single 2D graph
		- Constructor -
		"""

		super(Plot2D, self).__init__()
		self.__points__: list[PointType] = []
		self.__point_regular_shape__: int = 4
		self.__point_color__: int = 0xFFFFFFFF
		self.__point_size__: int = 10

	def plot_info(self, *, regular_point_shape: typing.Optional[int] = ..., point_color: typing.Optional[str | int | tuple[int, int, int]] = ..., point_size: typing.Optional[int] = ...) -> Plot2D:
		"""
		Modifies information about this plot
		:param regular_point_shape: The number of sides for a regular polygon representing points on this graph
		:param point_color: The colors used for points
		:param point_size: The size of points in pixels
		:return: This plot
		:raises ValueError: If the point color is invalid
		"""

		self.__point_regular_shape__ = self.__point_regular_shape__ if regular_point_shape is None or regular_point_shape is ... else int(regular_point_shape)
		self.__point_size__ = self.__point_size__ if point_size is None or point_size is ... else max(0, int(point_size))

		if point_color is ... or point_color is None:
			return self
		elif isinstance(point_color, str):
			self.__point_color__ = int(point_color[1:], 16) & 0xFFFFFFFF
		elif isinstance(point_color, int):
			self.__point_color__ =  int(point_color) & 0xFFFFFFFF
		elif isinstance(point_color, tuple) and len(point_color) == 3:
			self.__point_color__ = point_color[0] | (point_color[1] >> 8) | (point_color[2] >> 16)
		else:
			raise ValueError(f'Invalid point color - \'{point_color}\'')

		return self

	def add_points(self, *points: PointType) -> Plot2D:
		"""
		Adds points to this plot
		:param points: The points to add
		:return: This plot
		"""

		self.__points__.extend(points)
		return self

	def extents(self) -> tuple[float, float]:
		"""
		Gets the extends of this image calculated from bounds
		:return: The x and y extends
		"""

		bounds: tuple[float, float, float, float] = self.bounds
		x_extent: float = (bounds[1] - bounds[0]) * 2
		y_extent: float = (bounds[3] - bounds[2]) * 2
		x_extent = 20 if abs(x_extent) == float('inf') else x_extent
		y_extent = 20 if abs(y_extent) == float('inf') else y_extent
		return x_extent, y_extent

	def get_bounds(self) -> tuple[float, float, float, float]:
		"""
		Gets the bounds of this plot
		Any infinite boundaries are set to 10
		:return: (min_x, max_x, min_y, max_y)
		"""

		minx, maxx, miny, maxy = self.bounds
		inf: float = float('inf')
		return -10 if abs(minx) == inf else minx, 10 if abs(maxx) == inf else maxx, -10 if abs(miny) == inf else miny, 10 if abs(maxy) == inf else maxy

	@property
	def points(self) -> tuple[PointType, ...]:
		"""
		:return: All points stored in this plot
		"""

		return tuple(self.__points__)

	@property
	def point_color(self) -> int:
		"""
		:return: The point color of this plot
		"""

		return self.__point_color__

	@property
	def point_color_rgba(self) -> tuple[int, int, int, int]:
		"""
		:return: The point color of this plot as RGBA
		"""

		return (self.__point_color__ >> 24) & 0xFF, (self.__point_color__ >> 16) & 0xFF, (self.__point_color__ >> 8) & 0xFF, self.__point_color__ & 0xFF

	@property
	def regular_point_shape(self) -> int:
		"""
		:return: The number of sides used to represent a point on this plot
		"""

		return self.__point_regular_shape__

	@property
	def point_size(self) -> int:
		"""
		:return: The size of points on this plot in pixels
		"""

		return self.__point_size__

	@property
	def bounds(self) -> tuple[float, float, float, float]:
		"""
		Gets the bounds of this plot
		:return: (min_x, max_x, min_y, max_y)
		"""

		if self.__explicit_bounds__ is not None:
			return self.__explicit_bounds__

		minx: float = float('inf')
		maxx: float = float('-inf')
		miny: float = float('inf')
		maxy: float = float('-inf')

		for x, y in self.__points__:
			minx = min(minx, x)
			maxx = max(maxx, x)
			miny = min(miny, y)
			maxy = max(maxy, y)

		return minx - 1, maxx + 1, miny - 1, maxy + 1

	@bounds.setter
	def bounds(self, bounds: tuple[float, float, float, float] | None) -> None:
		"""
		Sets the boundaries of this plot
		Data outside this bound will not be rendered
		Any 'None' values are infinite
		:param bounds: The (minx, maxx, miny, maxy) bounds
		"""

		if bounds is None or bounds is ...:
			self.__explicit_bounds__ = None
		else:
			bounds: tuple[float, float, float, float] = tuple(bounds)
			assert all(isinstance(x, (int, float)) for x in bounds), 'One or more bounds is not a float'
			self.__explicit_bounds__ = bounds[:4]

class MultiPlot2D[PlotType: Plot2D](Plottable):
	"""
	Base class representing multiple stacked 2D plots
	"""

	def __init__(self):
		"""
		Base class representing multiple stacked 2D plots
		- Constructor -
		"""

		super(MultiPlot2D, self).__init__()
		self.__plots__: dict[str, PlotType] = {'': Plot2D()}
		self.__plot_order__: list[str] = ['']
		self.__active_plot__: str = ''

	def __getitem__(self, index: int | str) -> PlotType:
		"""
		Gets a plot by index or name
		:param index: The index or name of a plot
		:return: The specified plot
		:raises IndexError: If the index is out of bounds
		:raises KeyError: If the plot does not exist
		"""

		order_index: int | None = (index if index >= 0 else (len(self.__plot_order__) + index)) if isinstance(index, int) else None

		if order_index is not None and order_index >= len(self.__plot_order__):
			raise IndexError(f'Index {index} out of bounds for multi-plot with {len(self.__plot_order__)} plots')

		key: str = index if order_index is None else self.__plot_order__[order_index]
		return self.__plots__[key]

	def __setitem__(self, index: int | str, value: PlotType) -> None:
		"""
		Sets a plot by index or name
		If by index, index must be in bounds
		:param index: The index or name of a plot
		:param value: The plot to set or add
		:raises IndexError: If the index is out of bounds
		"""

		order_index: int | None = (index if index >= 0 else (len(self.__plot_order__) + index)) if isinstance(index, int) else None

		if order_index is not None and order_index >= len(self.__plot_order__):
			raise IndexError(f'Index {index} out of bounds for multi-plot with {len(self.__plot_order__)} plots')

		key: str = index if order_index is None else self.__plot_order__[order_index]
		self.__plots__[key] = value

	def __delitem__(self, index: int | str) -> None:
		"""
		Removes a plot by index or name
		:param index: The index or name of a plot
		:raises IndexError: If the index is out of bounds
		:raises KeyError: If the plot does not exist
		"""

		order_index: int | None = (index if index >= 0 else (len(self.__plot_order__) + index)) if isinstance(index, int) else None

		if order_index is not None and order_index >= len(self.__plot_order__):
			raise IndexError(f'Index {index} out of bounds for multi-plot with {len(self.__plot_order__)} plots')

		key: str = index if order_index is None else self.__plot_order__[order_index]
		del self.__plots__[key]

	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		super().__draw__(image, size)
		bounds: tuple[float, float, float, float] = tuple(bound * 1.25 for bound in self.bounds)

		for plot_name in reversed(self.__plot_order__):
			self.__draw_plot__(image, size, plot_name, bounds)

	def __draw_plot__(self, image: PIL.Image.Image, size: int, sub_plot_name: str, bounds: tuple[float, float, float, float]) -> None:
		"""
		- ABSTRACT -
		Overload this method to control plot drawing
		This method draws the specified sub-plot to the given image
		:param image: The PIL image to draw to
		:param size: The square image size
		:param sub_plot_name: The name of the sub-plot to draw
		:param bounds: The bounds of the entire stacked multi-plot
		"""

		self.__plots__[sub_plot_name].__draw__(image, size)

	def extents(self) -> tuple[float, float]:
		"""
		Gets the extends of this image calculated from bounds
		:return: The x and y extends
		"""

		bounds: tuple[float, float, float, float] = self.bounds
		x_extent: float = (bounds[1] - bounds[0]) * 2
		y_extent: float = (bounds[3] - bounds[2]) * 2
		x_extent = 20 if abs(x_extent) == float('inf') else x_extent
		y_extent = 20 if abs(y_extent) == float('inf') else y_extent
		return x_extent, y_extent

	def get_bounds(self) -> tuple[float, float, float, float]:
		"""
		Gets the bounds of this plot
		Any infinite boundaries are set to 10
		:return: (min_x, max_x, min_y, max_y)
		"""

		minx, maxx, miny, maxy = self.bounds
		inf: float = float('inf')
		return -10 if abs(minx) == inf else minx, 10 if abs(maxx) == inf else maxx, -10 if abs(miny) == inf else miny, 10 if abs(maxy) == inf else maxy

	def add_plot(self, plot_name: str, plot: PlotType, *, make_active: bool = True) -> PlotType:
		"""
		Adds a single plot to this multi-plot
		:param plot_name: The plot name to add as
		:param plot: The plot to add
		:param make_active: Whether to set the newly added plot as active
		:return: The newly added plot
		"""

		if plot_name in self.__plots__:
			raise KeyError('A plot with this name already exists')
		elif not isinstance(plot_name, str):
			raise TypeError('Plot name must be a string')

		self.__plots__[plot_name] = plot
		self.__plot_order__.append(plot_name)
		self.__active_plot__ = plot_name if make_active else self.__active_plot__
		return plot

	@property
	def bounds(self) -> tuple[float, float, float, float]:
		"""
		Gets the bounds of this plot
		If no bounds were set, returns the calculated bounds
		:return: The (minx, maxx, miny, maxy) bounds
		"""

		if self.__explicit_bounds__ is not None:
			return self.__explicit_bounds__

		bounds: tuple[tuple[float, float, float, float], ...] = tuple(plot.bounds for plot in self.__plots__.values())
		minx: float = min(bound[0] for bound in bounds)
		maxx: float = max(bound[1] for bound in bounds)
		miny: float = min(bound[2] for bound in bounds)
		maxy: float = max(bound[3] for bound in bounds)
		return minx, maxx, miny, maxy

	@bounds.setter
	def bounds(self, bounds: tuple[float, float, float, float] | None) -> None:
		"""
		Sets the boundaries of this plot
		Data outside this bound will not be rendered
		Any 'None' values are infinite
		:param bounds: The (minx, maxx, miny, maxy) bounds
		"""

		if bounds is None or bounds is ...:
			self.__explicit_bounds__ = None
		else:
			bounds: tuple[float, float, float, float] = tuple(bounds)
			assert all(isinstance(x, (int, float)) for x in bounds), 'One or more bounds is not a float'
			self.__explicit_bounds__ = bounds[:4]

class CartesianScatterPlot2D(AxisPlot2D, MultiPlot2D[Plot2D[tuple[float, float]]]):
	"""
	Class representing a scatter plot in 2D cartesian space
	 ... PointType = tuple[float, float]
	"""

	POLY_FIT_METHODS: dict[str, typing.Callable] = {
		'poly': numpy.polynomial.polynomial.polyfit,
		'polynomial': numpy.polynomial.polynomial.polyfit,
		'chebyshev': numpy.polynomial.chebyshev.chebfit,
		'hermite': numpy.polynomial.hermite.hermfit,
		'hermite_e': numpy.polynomial.hermite_e.hermefit,
		'laguerre': numpy.polynomial.laguerre.lagfit,
		'legendre': numpy.polynomial.legendre.legfit
	}

	def __init__(self):
		"""
		Class representing a scatter plot in 2D cartesian space
		 ... PointType = tuple[float, float]
		"""

		super(CartesianScatterPlot2D, self).__init__(self)
		self.__graph_functions__: dict[str, list[typing.Callable[[float], float]]] = {}
		self.add_axis('x', (0, 0), 0, major_spacing=5)
		self.add_axis('y', (0, 0), 90, major_spacing=5)

	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		super().draw_linear_axis(image, size, 'x')
		super().draw_linear_axis(image, size, 'y')
		super().__draw__(image, size)

	def __draw_plot__(self, image: PIL.Image.Image, size: int, sub_plot_name: str, bounds: tuple[float, float, float, float]) -> None:
		sub_plot: Plot2D = self.__plots__[sub_plot_name]
		points: tuple[tuple[float, float], ...] = tuple(sorted(sub_plot.points, key=lambda point: point[0]))
		mapped_points: list[tuple[int, int]] = []
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)

		for x, y in points:
			image_point: tuple[int, int] = self.plot_point_to_image_point((x, y), size)
			mapped_points.append(image_point)

			if sub_plot.regular_point_shape == 0:
				drawer.circle(image_point, sub_plot.point_size / 2, sub_plot.point_color_rgba, width=0)
			elif sub_plot.regular_point_shape >= 3:
				drawer.regular_polygon((*image_point, sub_plot.point_size / 2), sub_plot.regular_point_shape, 0, sub_plot.point_color_rgba, width=0)

		drawer.line(mapped_points, sub_plot.point_color_rgba, max(1, round(sub_plot.point_size / 4)))

		if sub_plot_name in self.__graph_functions__:
			functions: list[typing.Callable[[float], float]] = self.__graph_functions__[sub_plot_name]

			for function in functions:
				mapped_function_points: list[tuple[float, float]] = []

				for pixel in range(size):
					x: float = self.image_point_to_plot_point((pixel, 0), size)[0]
					y: float = function(x)
					assert isinstance(y, (float, int)), 'Returned value is not a float'
					image_point: tuple[int, int] = self.plot_point_to_image_point((x, y), size)
					mapped_function_points.append(image_point)

				drawer.line(mapped_function_points, sub_plot.point_color_rgba, max(1, round(sub_plot.point_size / 4)))

	def graph(self, function: typing.Callable[[float], float], *, plot_name: typing.Optional[str] = ...) -> CartesianScatterPlot2D:
		"""
		Graphs the specified function onto this plot
		This function is not called immediately, instead the function is queued and will be called on draw
		:param function: A function accepting a single float and returning a single float
		:param plot_name: The plot name to graph to or the active plot if None
		:return: This plot
		:raises TypeError: If plot name is not a string
		:raises KeyError: If a plot with the specified name does not exist
		:raises ValueError: If the specified function is not callable
		"""

		plot: str = self.__active_plot__ if plot_name is None or plot_name is ... else plot_name

		if not isinstance(plot, str):
			raise TypeError('Plot name must be a string')
		elif plot not in self.__plots__:
			raise KeyError('A plot with this name does not exist')
		elif not callable(function):
			raise ValueError('Specified function is not callable')

		if plot in self.__graph_functions__:
			self.__graph_functions__[plot].append(function)
		else:
			self.__graph_functions__[plot] = [function]

		return self

	def graph_points(self, function: typing.Callable[[float], float], minx: float = None, maxx: float = None, step: float = 1e-3, *, plot_name: typing.Optional[str] = ...) -> CartesianScatterPlot2D:
		"""
		Graphs the specified function onto this plot
		This runs the function immediately, storing the resulting points on this graph
		:param function: A function accepting a single float and returning a single float
		:param minx: The minimum x value to graph or None to use calculated bounds
		:param maxx: The maximum x value to graph or None to use calculated bounds
		:param step: The step between x values
		:param plot_name: The plot name to graph to or the active plot if None
		:return: This plot
		:raises TypeError: If plot name is not a string
		:raises KeyError: If a plot with the specified name does not exist
		:raises ValueError: If the specified function is not callable
		:raises TypeError: If the function does not return a float or integer
		"""

		plot: str = self.__active_plot__ if plot_name is None or plot_name is ... else plot_name

		if not isinstance(plot, str):
			raise TypeError('Plot name must be a string')
		elif plot not in self.__plots__:
			raise KeyError('A plot with this name does not exist')
		elif not callable(function):
			raise ValueError('Specified function is not callable')

		inf: float = float('inf')
		bounds: tuple[float, float, float, float] = self.bounds
		step: float = float(step)
		minx: float = float(minx) if minx is not None else -10 if abs(bounds[0]) == inf else bounds[0]
		maxx: float = float(maxx) if maxx is not None else 10 if abs(bounds[1]) == inf else bounds[1]
		x: float = minx
		plot: Plot2D = self.__plots__[plot]

		while x <= maxx:
			y: float = function(x)
			Misc.raise_ifn(isinstance(y, (float, int)), TypeError('Returned value is not a float'))
			plot.add_points((x, y))
			x += step

		return self

	def linear_regression(self, *, plot_name: typing.Optional[str] = ...) -> tuple[typing.Optional[str], typing.Optional[float], typing.Callable[[float], typing.Optional[float]]]:
		"""
		Calculates the best fit linear regression for the active plot's points
		:param plot_name: The plot name to graph to or the active plot if None
		:return: Either a tuple of None if the graph is empty or a tuple containing the equation, r squared, and a callable representing the regression function
		:raises KeyError: If a plot with the specified name does not exist
		:raises ValueError: If the specified function is not callable
		"""

		plot: str = self.__active_plot__ if plot_name is None or plot_name is ... else plot_name

		if not isinstance(plot, str):
			raise TypeError('Plot name must be a string')
		elif plot not in self.__plots__:
			raise KeyError('A plot with this name does not exist')

		points: set[tuple[float, float]] = set(self.__plots__[plot].points)

		if len(points) == 0:
			return None, None, lambda x: None

		_x: float = sum(point[0] for point in points) / len(points)
		_y: float = sum(point[1] for point in points) / len(points)
		_a: float = sum((point[1] - _y) * (point[0] - _x) for point in points) / sum((point[0] - _x) ** 2 for point in points)
		_b: float = _y - _a * _x
		r2: float = 1 - sum((point[1] - (_a * point[0] + _b)) ** 2 for point in points) / sum((point[1] - _y) ** 2 for point in points)
		return f'y={_a}x+{_b}; r²={r2}', r2, lambda x, m=_a, b=_b: m * x + b

	def exponential_regression(self, *, plot_name: typing.Optional[str] = ...) -> tuple[typing.Optional[str], typing.Optional[float], typing.Callable[[float], typing.Optional[float]]]:
		"""
		Calculates the best fit exponential regression for the active plot's points
		:param plot_name: The plot name to graph to or the active plot if None
		:return: Either a tuple of None if the graph is empty or a tuple containing the equation, r squared, and a callable representing the regression function
		:raises KeyError: If a plot with the specified name does not exist
		:raises ValueError: If the specified function is not callable
		"""

		plot: str = self.__active_plot__ if plot_name is None or plot_name is ... else plot_name

		if not isinstance(plot, str):
			raise TypeError('Plot name must be a string')
		elif plot not in self.__plots__:
			raise KeyError('A plot with this name does not exist')

		points: set[tuple[float, float]] = {(x, math.log(y, math.e)) for x, y in self.__plots__[plot].points if y > 0}

		if len(points) == 0:
			return None, None, lambda x: None

		_x: float = sum(point[0] for point in points) / len(points)
		_y: float = sum(point[1] for point in points) / len(points)
		_a: float = sum((point[1] - _y) * (point[0] - _x) for point in points) / sum((point[0] - _x) ** 2 for point in points)
		_b: float = _y - _a * _x
		r2: float = 1 - sum((point[1] - (_a * point[0] + _b)) ** 2 for point in points) / sum(point[1] - _y for point in points)
		return f'y=e^({_a}x+{_b}); r²={r2}', r2, lambda x: pow(math.e, _a * x + _b)

	def polynomial_regression(self, degree: int = None, max_degree: int = None, fit_method='poly', *, plot_name: typing.Optional[str] = ...) -> tuple[typing.Optional[str], typing.Optional[float], typing.Callable[[float], typing.Optional[float]]]:
		"""
		Calculates the best fit polynomial regression for the active plot's points
		Calculates an equation of degree 'degree' if 'max_degree' is None otherwise returns the best fit from equations between 'degree' and 'max_degree'
		:param degree: The degree (or minimum degree if 'max_degree' is not None) to test
		:param max_degree: The maximum degree to test
		:param fit_method: The method used to fit the data, one of the values returned from 'CartesianScatterPlot2D::POLY_FIT_METHODS'
		:param plot_name: The plot name to graph to or the active plot if None
		:return: Either a tuple of None if the graph is empty or a tuple containing the equation, r squared, and a callable representing the regression function
		:raises KeyError: If a plot with the specified name does not exist
		:raises ValueError: If the specified function is not callable
		:raises AssertionError: If any argument is invalid
		"""

		assert degree is None or isinstance(degree, int) and (degree := int(degree)) > 0, 'Degree must be an int greater than 0'
		assert max_degree is None or type(max_degree) is int and max_degree > 0, 'Max Degree must be an int greater than 0'
		assert fit_method is None or fit_method.lower() in CartesianScatterPlot2D.POLY_FIT_METHODS, f'Fit method must be one of {tuple(CartesianScatterPlot2D.POLY_FIT_METHODS.keys())}'

		plot: str = self.__active_plot__ if plot_name is None or plot_name is ... else plot_name

		if not isinstance(plot, str):
			raise TypeError('Plot name must be a string')
		elif plot not in self.__plots__:
			raise KeyError('A plot with this name does not exist')

		stop_at_rank: bool = degree is None and max_degree is None
		max_degree = max_degree if max_degree is not None else 32 if degree is None else degree
		degree = 1 if degree is None else degree - 1
		points: set[tuple[float, float]] = set(self.__plots__[plot].points)
		factors: tuple[float, ...] = ()
		r2: float = 0
		degree_error: int = 0
		fit_methods: tuple[str, ...] = tuple(CartesianScatterPlot2D.POLY_FIT_METHODS.keys()) if fit_method is None else (fit_method,)

		if len(points) == 0:
			return None, None, lambda x_: None

		assert max_degree >= degree, f'{type(self).__name__}::polynomial_regression - \'max_degree\' must be equal to or greater than \'degree\''

		for n in range(degree, max_degree):
			for fit in fit_methods:
				x = numpy.array([point[0] for point in points])
				y = numpy.array([point[1] for point in points])

				if degree_error == 0:
					with warnings.catch_warnings():
						warnings.simplefilter('error', numpy.exceptions.RankWarning)

						try:
							factors_local = tuple(CartesianScatterPlot2D.POLY_FIT_METHODS[fit.lower()](x, y, n + 1))
						except numpy.exceptions.RankWarning:
							if stop_at_rank:
								break
							else:
								with warnings.catch_warnings():
									warnings.simplefilter('ignore', numpy.exceptions.RankWarning)
									factors_local = tuple(CartesianScatterPlot2D.POLY_FIT_METHODS[fit.lower()](x, y, n + 1))

								degree_error = n + 1
				else:
					with warnings.catch_warnings():
						warnings.simplefilter('ignore', numpy.exceptions.RankWarning)
						factors_local = tuple(CartesianScatterPlot2D.POLY_FIT_METHODS[fit.lower()](x, y, n + 1))

				_y: float = sum(point[1] for point in points) / len(points)
				r2_local: float = 1 - sum((point[1] - sum((m * point[0] ** (len(factors_local) - b - 1)) for b, m in enumerate(factors_local))) ** 2 for point in points) / sum((point[1] - _y) ** 2 for point in points)

				if abs(r2_local - 1) < abs(r2 - 1) or len(factors) == 0:
					r2 = r2_local
					factors = factors_local

		if degree_error > 0:
			sys.stderr.write(f'[RankWarning]: numpy marked potential fit error from high polynomial degree (started at degree {degree_error})\n')
			sys.stderr.flush()

		equation: str = ''.join(f'{"+" if m >= 0 and b > 0 else ""}{m}x^{(len(factors) - b - 1)}' for b, m in enumerate(factors))
		return (f'y={equation}; r²={r2}', r2, lambda x_, f=factors: sum(m * x_ ** (len(f) - b - 1) for b, m in enumerate(f))) if len(factors) > 0 else (None, None, lambda x_: None)

	def sinusoidal_regression(self, *, plot_name: typing.Optional[str] = ...) -> tuple[typing.Optional[str], typing.Optional[float], typing.Callable[[float], typing.Optional[float]]]:
		"""
		Calculates the best fit sinusoidal regression for the active plot's points
		:return: Either a tuple of None if the graph is empty or a tuple containing the equation, r squared, and a callable representing the regression function
		:raises KeyError: If a plot with the specified name does not exist
		:raises ValueError: If the specified function is not callable
		"""

		plot: str = self.__active_plot__ if plot_name is None or plot_name is ... else plot_name

		if not isinstance(plot, str):
			raise TypeError('Plot name must be a string')
		elif plot not in self.__plots__:
			raise KeyError('A plot with this name does not exist')

		points: set[tuple[float, float]] = set(self.__plots__[plot].points)

		if len(points) == 0:
			return None, None, lambda x: None

		sorted_points: tuple[tuple[float, float], ...] = tuple(sorted(points, key=lambda p: p[0]))
		tt = numpy.array([point[0] for point in sorted_points])
		yy = numpy.array([point[1] for point in sorted_points])
		ff = numpy.fft.fftfreq(len(tt), (tt[1] - tt[0]))  # assume uniform spacing
		Fyy = abs(numpy.fft.fft(yy))
		guess_freq = abs(ff[numpy.argmax(Fyy[1:]) + 1])  # excluding the zero frequency "peak", which is related to offset
		guess_amp = numpy.std(yy) * 2. ** 0.5
		guess_offset = numpy.mean(yy)
		guess = numpy.array([guess_amp, 2. * numpy.pi * guess_freq, 0., guess_offset])

		try:
			(a, b, c, d), _ = scipy.optimize.curve_fit(lambda x, a_, b_, c_, d_: a_ * numpy.sin(b_ * x + c_) + d_, numpy.array([point[0] for point in sorted_points]), numpy.array([point[1] for point in sorted_points]), p0=guess)
		except RuntimeError:
			a, b, c, d = guess

		_y: float = sum(point[1] for point in points) / len(points)
		r2: float = 1 - sum((point[1] - (a * math.sin(b * point[0] + c) + d)) ** 2 for point in points) / sum((point[1] - _y) ** 2 for point in points)
		return f'y={a}*sin({b}*x+{c})+{d}; r²={r2}', r2, lambda x: a * math.sin(b * x + c) + d

class PolarScatterPlot2D(AxisPlot2D, MultiPlot2D[Plot2D[tuple[float, float]]]):
	"""
	Class representing a scatter plot in 2D polar space
	 ... PointType = tuple[float, float]
	"""

	def __init__(self):
		"""
		Class representing a scatter plot in 2D polar space
	 	... PointType = tuple[float, float]
	 	- Constructor -
		"""

		super(PolarScatterPlot2D, self).__init__(self)
		self.__graph_functions__: dict[str, list[tuple[typing.Callable[[float], float], float]]] = {}
		self.add_axis('x', (0, 0), 0, major_spacing=5)
		self.add_axis('y', (0, 0), 90, major_spacing=5)
		self.add_axis('t', (0, 0), 0, minor_spacing=22.5, major_spacing=2)

	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		super().draw_radial_axis(image, size, 't')
		super().draw_linear_axis(image, size, 'x')
		super().draw_linear_axis(image, size, 'y')
		super().__draw__(image, size)

	def __draw_plot__(self, image: PIL.Image.Image, size: int, sub_plot_name: str, bounds: tuple[float, float, float, float]) -> None:
		sub_plot: Plot2D = self.__plots__[sub_plot_name]
		points: tuple[tuple[float, float], ...] = tuple(sorted(sub_plot.points, key=lambda point: point[0]))
		mapped_points: list[tuple[int, int]] = []
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)

		for t, r in points:
			x: float = r * math.cos(t)
			y: float = r * math.sin(t)
			image_point: tuple[int, int] = self.plot_point_to_image_point((x, y), size)
			mapped_points.append(image_point)

			if sub_plot.regular_point_shape == 0:
				drawer.circle(image_point, sub_plot.point_size / 2, sub_plot.point_color_rgba, width=0)
			elif sub_plot.regular_point_shape >= 3:
				drawer.regular_polygon((*image_point, sub_plot.point_size / 2), sub_plot.regular_point_shape, 0, sub_plot.point_color_rgba, width=0)

		drawer.line(mapped_points, sub_plot.point_color_rgba, max(1, round(sub_plot.point_size / 4)))

		if sub_plot_name in self.__graph_functions__:
			functions: list[tuple[typing.Callable[[float], float], float]] = self.__graph_functions__[sub_plot_name]
			radian: float = 0.001 * math.pi / 180

			for function, max_radian in functions:
				mapped_function_points: list[tuple[float, float]] = []
				theta: float = 0

				while theta < max_radian:
					r: float = function(theta)
					assert isinstance(r, (float, int)), 'Returned value is not a float'
					x: float = r * math.cos(theta)
					y: float = r * math.sin(theta)
					image_point: tuple[int, int] = self.plot_point_to_image_point((x, y), size)
					mapped_function_points.append(image_point)
					theta += radian

				drawer.line(mapped_function_points, sub_plot.point_color_rgba, max(1, round(sub_plot.point_size / 4)))

	def graph(self, function: typing.Callable[[float], float], *, angle: float = 360, plot_name: typing.Optional[str] = ...) -> PolarScatterPlot2D:
		"""
		Graphs the specified function onto this plot
		This function is not called immediately, instead the function is queued and will be called on draw
		:param function: A function accepting a single float and returning a single float
		:param plot_name: The plot name to graph to or the active plot if None
		:return: This plot
		:raises TypeError: If plot name is not a string
		:raises KeyError: If a plot with the specified name does not exist
		:raises ValueError: If the specified function is not callable
		"""

		plot: str = self.__active_plot__ if plot_name is None or plot_name is ... else plot_name

		if not isinstance(plot, str):
			raise TypeError('Plot name must be a string')
		elif plot not in self.__plots__:
			raise KeyError('A plot with this name does not exist')
		elif not callable(function):
			raise ValueError('Specified function is not callable')

		if plot in self.__graph_functions__:
			self.__graph_functions__[plot].append((function, angle * math.pi / 180))
		else:
			self.__graph_functions__[plot] = [(function, angle * math.pi / 180)]

		return self

	def graph_points(self, function: typing.Callable[[float], float], minx: float = None, maxx: float = None, step: float = 1e-3, *, plot_name: typing.Optional[str] = ...) -> PolarScatterPlot2D:
		"""
		Graphs the specified function onto this plot
		This runs the function immediately, storing the resulting points on this graph
		:param function: A function accepting a single float and returning a single float
		:param minx: The minimum x value to graph or None to use calculated bounds
		:param maxx: The maximum x value to graph or None to use calculated bounds
		:param step: The step between x values
		:param plot_name: The plot name to graph to or the active plot if None
		:return: This plot
		:raises TypeError: If plot name is not a string
		:raises KeyError: If a plot with the specified name does not exist
		:raises ValueError: If the specified function is not callable
		:raises TypeError: If the function does not return a float or integer
		"""

		plot: str = self.__active_plot__ if plot_name is None or plot_name is ... else plot_name

		if not isinstance(plot, str):
			raise TypeError('Plot name must be a string')
		elif plot not in self.__plots__:
			raise KeyError('A plot with this name does not exist')
		elif not callable(function):
			raise ValueError('Specified function is not callable')

		inf: float = float('inf')
		bounds: tuple[float, float, float, float] = self.bounds
		step: float = float(step)
		minx: float = float(minx) if minx is not None else -10 if abs(bounds[0]) == inf else bounds[0]
		maxx: float = float(maxx) if maxx is not None else 10 if abs(bounds[1]) == inf else bounds[1]
		x: float = minx
		plot: Plot2D = self.__plots__[plot]

		while x <= maxx:
			y: float = function(x)
			Misc.raise_ifn(isinstance(y, (float, int)), ValueError('Returned value is not a float'))
			plot.add_points((x, y))
			x += step

		return self

class PiePlot2D(Plot2D[tuple[str, float]]):
	"""
	Class representing a 2D pie plot
	 ... PointType = tuple[str, float]
	"""

	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		pie_size: float = size * 0.95 / 2
		center: float = size / 2
		corner1: float = center - pie_size
		corner2: float = center + pie_size
		bounds: tuple[float, float, float, float] = (corner1, corner1, corner2, corner2)
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)

		if len(self.__points__) > 0:
			total: float = sum(point[1] for point in self.__points__ if point[1] > 0)
			theta: float = 0

			for i, (label, value) in enumerate(self.__points__):
				if value <= 0:
					continue

				percent: float = (value / total)
				color: tuple[float, float, float, float] = matplotlib.cm.brg(percent)
				partial: float = 360 * percent
				degree1: float = theta
				theta += partial
				degree2: float = theta
				drawer.pieslice(bounds, degree1, degree2, tuple(round(c * 255) for c in color), self.point_color_rgba, 1)

class BarPlot2D(AxisPlot2D, Plot2D[tuple[str, float]]):
	"""
	Class representing a 2D bar plot
	 ... PointType = tuple[str, float]
	"""

	def __init__(self):
		"""
		Class representing a 2D bar plot
	 	... PointType = tuple[str, float]
	 	- Constructor -
		"""

		super().__init__(self)
		self.add_axis('x', (0, 0), 0, major_spacing=0, minor_spacing=1, tick_offset=1)
		self.add_axis('y', (0, 0), 90, major_spacing=0, minor_spacing=1, tick_offset=0)

	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)
		count: int = len(self.__points__)

		for i, (label, value) in enumerate(self.__points__):
			p1: tuple[float, float] = self.plot_point_to_image_point((i + 1.375, 0), size)
			p2: tuple[float, float] = self.plot_point_to_image_point((i + 0.625, 0 + value), size)
			x1, y1 = p1
			x2, y2 = p2
			minx, maxx = Iterable.minmax(x1, x2)
			miny, maxy = Iterable.minmax(y1, y2)
			color: tuple[float, float, float, float] = matplotlib.cm.brg(i / count)
			drawer.rectangle((minx, miny, maxx, maxy), tuple(round(c * 255) for c in color), width=0)

		super().draw_linear_axis(image, size, 'x')
		super().draw_linear_axis(image, size, 'y')

	@property
	def bounds(self) -> tuple[float, float, float, float]:
		if len(self.__points__) == 0:
			return -1, 1, -1, 1

		miny: float
		maxy: float
		miny, maxy = Iterable.minmax(point[1] for point in self.__points__)
		return -1.0, len(self.__points__) + 1.0, min(miny - 1, -1), maxy + 1

class HistogramPlot2D(AxisPlot2D, Plot2D[tuple[float, float]]):
	"""
	Class representing a 2D histogram plot
	 ... PointType = tuple[float, float]
	"""

	def __init__(self):
		"""
		Class representing a 2D histogram plot
		 ... PointType = tuple[float, float]
		"""

		super().__init__(self)
		self.add_axis('x', (0, 0), 0, major_spacing=0, minor_spacing=1, tick_offset=1)
		self.add_axis('y', (0, 0), 90, major_spacing=0, minor_spacing=1, tick_offset=0)

	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)

		for i, (label, value) in enumerate(self.__points__):
			p1: tuple[float, float] = self.plot_point_to_image_point((i + 1.5, 0), size)
			p2: tuple[float, float] = self.plot_point_to_image_point((i + 0.5, value), size)
			x1, y1 = p1
			x2, y2 = p2
			minx, maxx = Iterable.minmax(x1, x2)
			miny, maxy = Iterable.minmax(y1, y2)
			drawer.rectangle((minx, miny, maxx, maxy), self.point_color_rgba, width=0)

		super().draw_linear_axis(image, size, 'x')
		super().draw_linear_axis(image, size, 'y')

	@property
	def bounds(self) -> tuple[float, float, float, float]:
		if len(self.__points__) == 0:
			return -1, 1, -1, 1

		miny: float
		maxy: float
		miny, maxy = Iterable.minmax(point[1] for point in self.__points__)
		return -1.0, len(self.__points__) + 1.0, min(miny - 1, -1), maxy + 1

class DensityPlot2D(AxisPlot2D, MultiPlot2D[HistogramPlot2D]):
	"""
	Class representing a 2D density plot
	 ... PointType = tuple[float, float]
	"""

	def __init__(self):
		"""
		Class representing a 2D density plot
	 	... PointType = tuple[float, float]
		"""

		super().__init__(self)
		self.add_axis('x', (0, 0), 0, major_spacing=0, minor_spacing=1, tick_offset=1)
		self.add_axis('y', (0, 0), 90, major_spacing=0, minor_spacing=1, tick_offset=0)

	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		super().draw_linear_axis(image, size, 'x')
		super().draw_linear_axis(image, size, 'y')
		super().__draw__(image, size)

	def __draw_plot__(self, image: PIL.Image.Image, size: int, sub_plot_name: str, bounds: tuple[float, float, float, float]) -> None:
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)
		plot: HistogramPlot2D = self.__plots__[sub_plot_name]
		minx, maxx, _, _ = self.get_bounds()
		final_points: tuple[tuple[float, float], ...] = ((minx, 0), *plot.points, (maxx, 0))
		points: tuple[tuple[int, int], ...] = tuple(self.plot_point_to_image_point(point, size) for point in final_points)
		line_x: tuple[int, ...] = tuple(point[0] for point in points)
		line_y: tuple[int, ...] = tuple(point[1] for point in points)
		interpolator: typing.Callable = scipy.interpolate.interp1d(line_x, line_y, kind=2)
		line_x: numpy.ndarray = numpy.linspace(*Iterable.minmax(line_x), num=100)
		line_y: numpy.ndarray = interpolator(line_x)

		for i in range(len(line_x) - 1):
			point1: tuple[int, int] = (int(line_x[i]), int(line_y[i]))
			point2: tuple[int, int] = (int(line_x[i + 1]), int(line_y[i + 1]))
			drawer.line((point1, point2), fill=plot.point_color_rgba, width=1)

		for x, y in points[1:-1]:
			drawer.circle((x, y), plot.point_size / 2, fill=plot.point_color_rgba, width=0)

	@property
	def bounds(self) -> tuple[float, float, float, float]:
		minx, maxx, miny, maxy = super().bounds
		return -1, max(maxx, 1), min(miny, -1), max(maxy, 1)

class DotPlot2D(AxisPlot2D, MultiPlot2D[BarPlot2D]):
	"""
	Class representing a 2D dot plot
	 ... PointType = tuple[str, float]
	"""

	def __init__(self):
		"""
		Class representing a 2D dot plot
		 ... PointType = tuple[str, float]
		"""

		super().__init__(self)
		self.add_axis('x', (0, 0), 0, major_spacing=0, minor_spacing=1, tick_offset=1)
		self.add_axis('y', (0, 0), 90, major_spacing=0, minor_spacing=1, tick_offset=0)

	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		super().draw_linear_axis(image, size, 'x')
		super().draw_linear_axis(image, size, 'y')
		super().__draw__(image, size)

	def __draw_plot__(self, image: PIL.Image.Image, size: int, sub_plot_name: str, bounds: tuple[float, float, float, float]) -> None:
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)
		plot: BarPlot2D = self.__plots__[sub_plot_name]
		index: int = self.__plot_order__.index(sub_plot_name)
		r, g, b, a = matplotlib.cm.brg(index / len(self.__plots__))
		total: float = sum(point[1] for point in plot.points)

		for i, (label, value) in enumerate(plot.points):
			if value < 0:
				continue

			image_point: tuple[int, int] = self.plot_point_to_image_point((i + 1, index + 1), size)
			h, s, v = colorsys.rgb_to_hsv(r, g, b)
			dr, dg, db = colorsys.hsv_to_rgb(h, s * (value / total), v)
			color: tuple[float, float, float, float] = (dr, dg, db, a)
			drawer.circle(image_point, plot.point_size, tuple(round(c * 255) for c in color), width=0)

	@property
	def bounds(self) -> tuple[float, float, float, float]:
		if len(self.__plots__) == 0:
			return -1, 1, -1, 1

		maxx: float = max(len(plot.points) for plot in self.__plots__.values())
		return -1.0, maxx + 1.0, -1, len(self.__plots__) + 1

class StackedDotPlot2D(AxisPlot2D, Plot2D[tuple[str, int]]):
	"""
	Class representing a 2D stacked dot plot
	 ... PointType = tuple[str, int]
	"""

	def __init__(self):
		"""
		Class representing a 2D stacked dot plot
		 ... PointType = tuple[str, int]
		"""

		super().__init__(self)
		self.add_axis('x', (0, 0), 0, major_spacing=0, minor_spacing=1, tick_offset=1)
		self.add_axis('y', (0, 0), 90, major_spacing=0, minor_spacing=1, tick_offset=0)

	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)

		for i, (label, value) in enumerate(self.__points__):
			for j in range(1, value + 1) if value > 0 else range(value, 0):
				image_point: tuple[int, int] = self.plot_point_to_image_point((i + 1, j), size)
				drawer.circle(image_point, self.point_size / 2, self.point_color_rgba, width=0)

		super().draw_linear_axis(image, size, 'x')
		super().draw_linear_axis(image, size, 'y')

	@property
	def bounds(self) -> tuple[float, float, float, float]:
		if len(self.__points__) == 0:
			return -1, 1, -1, 1

		miny: float
		maxy: float
		miny, maxy = Iterable.minmax(point[1] for point in self.__points__)
		return -1.0, len(self.__points__) + 1.0, min(miny - 1, -1), maxy + 1

class BoxPlot2D(AxisPlot2D, MultiPlot2D[Plot2D[float]]):
	"""
	Class representing a 2D box plot
	 ... PointType = float
	"""

	def __init__(self):
		"""
		Class representing a 2D box plot
		 ... PointType = float
		"""

		super().__init__(self)
		self.add_axis('x', (0, 0), 0, major_spacing=0, minor_spacing=1, tick_offset=1)
		self.add_axis('y', (0, 0), 90, major_spacing=0, minor_spacing=1, tick_offset=0)

	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		super().draw_linear_axis(image, size, 'x')
		super().draw_linear_axis(image, size, 'y')
		super().__draw__(image, size)

	def __draw_plot__(self, image: PIL.Image.Image, size: int, sub_plot_name: str, bounds: tuple[float, float, float, float]) -> None:
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)
		points: tuple[float, ...] = self.__plots__[sub_plot_name].points
		index: int = self.__plot_order__.index(sub_plot_name)
		yoffset: int = index + 1
		ydelta: float = 0.25
		minx: float
		maxx: float
		minx, maxx = Iterable.minmax(points)
		p25: float = Stats.quantile(points, 0.25)
		p50: float = Stats.quantile(points, 0.5)
		p75: float = Stats.quantile(points, 0.75)
		x1, y1 = self.plot_point_to_image_point((p25, yoffset + ydelta), size)
		x2, y2 = self.plot_point_to_image_point((p75, yoffset - ydelta), size)
		color: tuple[int, ...] = tuple(round(c * 255) for c in matplotlib.cm.brg(index / len(self.__plots__)))
		radius: float = self.plot_point_to_image_point((1, 0), size)[0] * (ydelta / 2)
		drawer.rectangle((x1, y1, x2, y2), outline=color, width=2)
		minx_dot: tuple[float, float] = self.plot_point_to_image_point((minx, yoffset), size)
		maxx_dot: tuple[float, float] = self.plot_point_to_image_point((maxx, yoffset), size)
		drawer.circle(minx_dot, radius, color, width=0)
		drawer.circle(maxx_dot, radius, color, width=0)
		drawer.line((*self.plot_point_to_image_point((p50, yoffset - ydelta), size), *self.plot_point_to_image_point((p50, yoffset + ydelta), size)), color, width=2)
		drawer.line((*minx_dot, *self.plot_point_to_image_point((p25, yoffset), size)), color, width=2)
		drawer.line((*maxx_dot, *self.plot_point_to_image_point((p75, yoffset), size)), color, width=2)

	@property
	def bounds(self) -> tuple[float, float, float, float]:
		if len(self.__plots__) == 0:
			return -1, 1, -1, 1

		maxx: float = max(max(plot.points) for plot in self.__plots__.values())
		return -1.0, maxx + 1.0, -1, len(self.__plots__) + 1

class Plot3D[PointType](Plottable):
	def __draw__(self, image: PIL.Image.Image, size: int) -> None:
		pass

class GridPlotDisplay:
	"""
	Grid-style display for showing multiple plots at once
	"""

	def __init__(self):
		"""
		Grid-style display for showing multiple plots at once
		- Constructor -
		"""

		self.__grid__: dict[tuple[int, int], Plottable] = {}

	def __setitem__(self, coordinate: tuple[int, int], plot: Plottable) -> None:
		"""
		Adds a plot to this display at the specified grid coordinates
		:param coordinate: The grid coordinates starting at 0
		:param plot: The plot to display at these coordinates
		:raises AssertionError: If the coordinate is not an iterable containing exactly 2 integers >= 0
		:raises AssertionError: If the plot is not an instance of 'Plottable'
		"""

		assert hasattr(coordinate, '__iter__') and len(coordinate := tuple(coordinate)) == 2 and all(isinstance(x, int) and int(x) >= 0 for x in coordinate), 'Coordinate must be an iterable containing exactly 2 integers >= 0'
		assert isinstance(plot, Plottable), 'Not a plottable plot'
		row: int = int(coordinate[0])
		col: int = int(coordinate[1])
		self.__grid__[(row, col)] = plot

	def __delitem__(self, coordinate: tuple[int, int]) -> None:
		"""
		Removes a plot at the specified grid coordinates from this display
		:param coordinate: The grid coordinates starting at 0
		:raises AssertionError: If the coordinate is not an iterable containing exactly 2 integers >= 0
		"""

		assert hasattr(coordinate, '__iter__') and len(coordinate := tuple(coordinate)) == 2 and all(isinstance(x, int) and int(x) > 0 for x in coordinate), 'Coordinate must be an iterable containing exactly 2 integers >= 0'
		row: int = int(coordinate[0])
		col: int = int(coordinate[1])
		del self.__grid__[(row, col)]

	def __getitem__(self, coordinate: tuple[int, int]) -> Plottable:
		"""
		Gets a plot at the specified grid coordinates from this display
		:param coordinate: The grid coordinates starting at 0
		:raises AssertionError: If the coordinate is not an iterable containing exactly 2 integers >= 0
		"""

		assert hasattr(coordinate, '__iter__') and len(coordinate := tuple(coordinate)) == 2 and all(isinstance(x, int) and int(x) > 0 for x in coordinate), 'Coordinate must be an iterable containing exactly 2 integers >= 0'
		row: int = int(coordinate[0])
		col: int = int(coordinate[1])
		return self.__grid__[(row, col)]

	def show(self, *, square_size: int = 1024) -> None:
		"""
		Shows this plot in a tkinter window
		:param square_size: The square image size to render each plot as
		"""

		root: tkinter.Tk = tkinter.Tk()
		root.overrideredirect(False)
		root.resizable(False, False)
		root.title(f'{type(self).__name__}@{hex(id(self))}')
		root.configure(background='#222222')

		image: numpy.ndarray[numpy.uint8] = self.as_image(square_size=square_size)
		pilmage: PIL.Image.Image = PIL.Image.fromarray(image)
		pilmage_tk: PIL.ImageTk.PhotoImage = PIL.ImageTk.PhotoImage(pilmage)

		canvas: tkinter.Canvas = tkinter.Canvas(root, background='#222222', highlightthickness=1, highlightcolor='#eeeeee', highlightbackground='#eeeeee', width=pilmage.width, height=pilmage.height)
		canvas.pack()

		canvas.create_image(0, 0, image=pilmage_tk, anchor='nw')

		root.mainloop()

	def save(self, filename: str, *, square_size: int = 1024) -> None:
		"""
		Saves this plot as a rendered image
		:param filename: The filepath to save to
		:param square_size: The square image size to render each plot as
		"""

		image: PIL.Image.Image = PIL.Image.fromarray(self.as_image(square_size=square_size))
		image.save(filename)

	def as_image(self, *, square_size: int = 1024, padding: int = 32, border_width: int = 2) -> numpy.ndarray[numpy.uint8]:
		"""
		Renders this plot display as an image
		:param square_size: The square image size to render each plot as
		:param padding: The padding (in pixels) between images
		:param border_width: The width (in pixels) of the border between images
		:return: The rendered RGBA image
		"""

		border_width: int = int(border_width)
		padding: int = int(padding) + border_width
		plot_width: int = max(coord[1] for coord in self.__grid__.keys()) + 1
		plot_height: int = max(coord[0] for coord in self.__grid__.keys()) + 1
		image_width: int = (square_size + padding) * plot_width
		image_height: int = (square_size + padding) * plot_height
		square_size: int = int(square_size)
		image: PIL.Image.Image = PIL.Image.new('RGBA', (image_width, image_height), '#222222')
		border: PIL.Image.Image = PIL.Image.new('RGBA', (square_size + border_width * 2, square_size + border_width * 2), '#eeeeee')

		for coord, plot in self.__grid__.items():
			result: numpy.ndarray[numpy.uint8] = plot.as_image(square_size=square_size)
			pilmage: PIL.Image.Image = PIL.Image.fromarray(result)
			y: int = coord[0] * (square_size + padding) + (padding >> 1)
			x: int = coord[1] * (square_size + padding) + (padding >> 1)
			image.paste(border, (x - border_width, y - border_width))
			image.paste(pilmage, (x, y))

		return numpy.array(image)