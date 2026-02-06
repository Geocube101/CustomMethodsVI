from __future__ import annotations

import cv2
import numpy
import numpy.exceptions
import numpy.polynomial.polyutils
import PIL.Image
import PIL.ImageTk
import tkinter

from ...Math import Vector
from ... import Iterable
from ... import Misc


class Plottable(object):
	"""
	Base class representing a plot that can be imaged
	"""

	@staticmethod
	def generate_image_plate(width: int, height: int) -> numpy.ndarray:
		"""
		Generates the base background image for a plot
		:param width: The image width
		:param height: The image height
		:return: The image plate
		"""

		image: numpy.ndarray = numpy.full((width, height, 3), 0x22, numpy.uint8)
		return numpy.dstack((image, numpy.full((width, height), 0xFF, numpy.uint8)))

	def __init__(self):
		"""
		Base class representing a plot that can be imaged
		- Constructor -
		"""

		super(Plottable, self).__init__()
		self.__grid__: list[int] = [0, 0]
		self.__alpha__: float = 1
		self.__explicit_bounds__: tuple[float, float, float, float] | None = None
		self.__calculated_bounds__: tuple[float, float, float, float] | None = None

	def __draw__(self, image: numpy.ndarray, size: int) -> None:
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

		image: numpy.ndarray = self.as_image(square_size=square_size)
		cv2.imwrite(filename, image)

	def invalidate_bounds(self) -> None:
		"""
		Invalidates the calculated bounds\n
		Bounds will be re-calculated on next call to 'get_bounds'
		"""

		self.__calculated_bounds__ = None

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
		rx: float = Misc.clamp(Misc.get_ratio(x, minx, maxx), -1, 2)
		ry: float = Misc.clamp(Misc.get_ratio(y, miny, maxy), -1, 2)
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

	def bounds_distance_to_origin(self) -> tuple[float, float]:
		"""
		:return: The distance from graph origin to the nearest, farthest bounding corner
		"""

		return self.bounds_distance_to_point((0, 0))

	def bounds_distance_to_point(self, point: tuple[float, float] | Vector.Vector) -> tuple[float, float]:
		"""
		:return: The distance from graph origin to the nearest, farthest bounding corner
		"""

		minx, maxx, miny, maxy = self.get_bounds()
		cx, cy = point
		points: tuple[tuple[float, float], ...] = (
			(minx, miny), (minx, maxy),
			(maxx, miny), (maxx, maxy)
		)
		min_distance, max_distance = Iterable.Iterable.minmax((Vector.Vector(p) - Vector.Vector(point)).length() for p in points)

		if minx <= cx <= maxx and miny <= cy <= maxy:
			min_distance = 0

		return min_distance, max_distance

	def as_image(self, *, square_size: int = 1024) -> numpy.ndarray:
		"""
		Renders this plot as an image
		:param square_size: The square image size to render as
		:return: The rendered RGBA image
		"""

		square_size = int(square_size)
		image: numpy.ndarray = Plottable.generate_image_plate(square_size, square_size)
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

		if self.has_calculated_bounds:
			return self.__calculated_bounds__

		minx, maxx, miny, maxy = (-10, 10, -10, 10) if self.__explicit_bounds__ is None else self.__explicit_bounds__
		inf: float = float('inf')
		self.__calculated_bounds__ = (-10 if abs(minx) == inf else minx, 10 if abs(maxx) == inf else maxx, -10 if abs(miny) == inf else miny, 10 if abs(maxy) == inf else maxy)
		return self.__calculated_bounds__

	@property
	def has_explicit_bounds(self) -> bool:
		"""
		:return: Whether this plot has explicit bounds set
		"""

		return self.__explicit_bounds__ is not None

	@property
	def has_calculated_bounds(self) -> bool:
		"""
		:return: Whether this plot has calculated bounds set
		"""

		return self.__calculated_bounds__ is not None


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

		image: numpy.ndarray = self.as_image(square_size=square_size)
		cv2.imwrite(filename, image)

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
		border_size: int = square_size + border_width * 2
		image: numpy.ndarray = Plottable.generate_image_plate(image_width, image_height)
		border: numpy.ndarray = numpy.dstack((numpy.full((border_size, border_size, 3), 0xEE, numpy.uint8), numpy.full((border_size, border_size), 0xFF, numpy.uint8)))

		for coord, plot in self.__grid__.items():
			result: numpy.ndarray[numpy.uint8] = plot.as_image(square_size=square_size)
			y: int = coord[0] * (square_size + padding) + (padding >> 1)
			x: int = coord[1] * (square_size + padding) + (padding >> 1)
			border[border_width:border_width + square_size, border_width:border_width + square_size, :] = result
			image[x - border_width:x + square_size + border_width, y - border_width:y + square_size + border_width, :] = border

		return image
