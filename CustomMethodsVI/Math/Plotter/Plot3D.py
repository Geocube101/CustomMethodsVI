from __future__ import annotations

import numpy
import typing

from . import Plotter


class Plot3D[PointType](Plotter.Plottable):
	"""
		Base class representing a single 3D graph
		"""

	def __init__(self):
		"""
		Base class representing a single 3D graph
		- Constructor -
		"""

		super(Plot3D, self).__init__()
		self.__points__: list[PointType] = []
		self.__point_regular_shape__: int = 4
		self.__point_color__: int = 0xFFFFFFFF
		self.__point_size__: int = 10

	def plot_info(self, *, regular_point_shape: typing.Optional[int] = ..., point_color: typing.Optional[str | int | tuple[int, int, int]] = ..., point_size: typing.Optional[int] = ...) -> Plot3D:
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
			self.__point_color__ = int(point_color) & 0xFFFFFFFF
		elif isinstance(point_color, tuple) and len(point_color) == 3:
			self.__point_color__ = point_color[0] | (point_color[1] >> 8) | (point_color[2] >> 16)
		else:
			raise ValueError(f'Invalid point color - \'{point_color}\'')

		return self

	def add_points(self, *points: PointType) -> Plot3D:
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

		if self.has_calculated_bounds:
			return self.__calculated_bounds__

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
	def point_color_bgra(self) -> tuple[int, int, int, int]:
		"""
		:return: The point color of this plot as BGRA
		"""

		r, g, b, a = self.point_color_rgba
		return b, g, r, a

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
			assert all(x is None or isinstance(x, (int, float)) for x in bounds), 'One or more bounds is not a float'
			self.__explicit_bounds__ = bounds[:4]

		self.invalidate_bounds()
