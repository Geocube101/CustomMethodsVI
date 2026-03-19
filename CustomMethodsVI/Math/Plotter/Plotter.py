from __future__ import annotations

import collections.abc
import cv2
import enum
import numpy
import numpy.exceptions
import numpy.polynomial.polyutils
import PIL.Image
import PIL.ImageTk
import tkinter


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

		super().__init__()
		self.__grid__: list[int] = [0, 0]
		self.__alpha__: float = 1

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


class LabelSpacing(enum.IntFlag):
	MAJOR = 1
	MINOR = 2


class LabelAlignment(enum.IntEnum):
	LEFT = 0
	MIDDLE = 1
	RIGHT = 2


class AxisLabel:
	def __init__(self, labeller: collections.abc.Callable[[str, tuple[float, ...]], str] = str, spacing: LabelSpacing = LabelSpacing.MAJOR, alignment: LabelAlignment = LabelAlignment.LEFT, color: int | collections.abc.Callable[[str, tuple[float, ...]], int] = ..., font_scale: float = 1, font_thickness: int = 1):
		assert callable(labeller), 'Labeller not callable'
		assert callable(color) or (isinstance(color, int) and 0x00 <= int(color) <= 0xFFFFFFFF)
		assert isinstance(font_scale, (int, float)) and 0 <= (font_scale := float(font_scale))
		assert isinstance(font_thickness, int) and (font_thickness := int(font_thickness)) > 0

		self.__labeller__: collections.abc.Callable[[str, tuple[float, ...]], str] = labeller
		self.__spacing__: LabelSpacing = LabelSpacing(spacing)
		self.__alignment__: LabelAlignment = LabelAlignment(alignment)
		self.__color__: int | collections.abc.Callable[[str, tuple[float, ...]], int] = color
		self.__font_scale__: float = font_scale
		self.__font_thickness__: int = font_thickness

	def get_text(self, axis: str, point: tuple[float, ...]) -> str:
		return str(self.labeller(axis, point))

	def get_color(self, axis: str, point: tuple[float, ...]) -> int:
		return int(self.color(axis, point) if callable(self.color) else self.color) & 0xFFFFFFFF

	@property
	def labeller(self) -> collections.abc.Callable[[str, tuple[float, ...]], str]:
		return self.__labeller__

	@labeller.setter
	def labeller(self, labeller: collections.abc.Callable[[str, tuple[float, ...]], str]) -> None:
		assert callable(labeller), 'Labeller not callable'
		self.__labeller__ = labeller

	@property
	def spacing(self) -> LabelSpacing:
		return self.__spacing__

	@spacing.setter
	def spacing(self, spacing: LabelSpacing) -> None:
		self.__spacing__ = LabelSpacing(spacing)

	@property
	def alignment(self) -> LabelAlignment:
		return self.__alignment__

	@alignment.setter
	def alignment(self, alignment: LabelAlignment) -> None:
		self.__alignment__ = LabelAlignment(alignment)

	@property
	def color(self) -> int | collections.abc.Callable[[str, tuple[float, ...]], int]:
		return self.__color__

	@color.setter
	def color(self, color: int | collections.abc.Callable[[str, tuple[float, ...]], int]) -> None:
		assert callable(color) or (isinstance(color, int) and 0x00 <= int(color) <= 0xFFFFFFFF)
		self.__color__ = color

	@property
	def font_scale(self) -> float:
		return self.__font_scale__

	@font_scale.setter
	def font_scale(self, font_scale: float) -> None:
		assert isinstance(font_scale, float) and 0 <= (font_scale := float(font_scale))
		self.__font_scale__ = font_scale

	@property
	def font_thickness(self) -> int:
		return self.__font_thickness__

	@font_thickness.setter
	def font_thickness(self, font_thickness: int) -> None:
		assert isinstance(font_thickness, int) and (font_thickness := int(font_thickness)) > 0
		self.__font_thickness__ = font_thickness


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


__all__: list[str] = ['Plottable', 'GridPlotDisplay', 'LabelSpacing', 'LabelAlignment', 'AxisLabel']
