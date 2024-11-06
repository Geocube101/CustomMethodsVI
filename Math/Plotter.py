from __future__ import annotations

import colorsys
import sys
import typing
import tkinter as tk
import tkinter.constants as tkc
import cv2
import PIL.Image
import PIL.ImageTk
import PIL.ImageDraw
import PIL.ImageFont
import numpy as np
import numpy.polynomial.polyutils
import math
import warnings
import scipy.optimize
import scipy.interpolate
import enum

import CustomMethodsVI.FileSystem as FileSystem
import CustomMethodsVI.Math.Vector as Vector

from CustomMethodsVI.Iterable import frange, minmax
# from CustomMethodsVI.Decorators import Overload


class AxisPlot2D:
	class AxisBounding(enum.Enum):
		UNBOUNDED: int = 0
		LOWER: int = 1
		UPPER: int = 2
		BOUND: int = 3

	def __init__(self):
		self.__axes__: dict[str, tuple[tuple[float | None, float | None], float | None, int | None, str | None, typing.Callable[[float, float | None], str], bool]] = {}
		self.__last_image_minor_spacing__: dict[str, tuple[tuple[float, float], ...]] = {}
		self.__last_image_major_spacing__: dict[str, tuple[tuple[float, float], ...]] = {}

	def __draw_linear_axis__(self, axis: str, base_image: np.ndarray, draw_size: tuple[int, int], draw_border: tuple[float, float], pos: tuple[int, int], *, color: int = 0x888888, angle: float = 0, label_font: str = 'Arial', label_font_size: int = 12, label_angle: float = 0, label_pos: typing.Optional[tuple[float, float]] = None):
		"""
		Draws a linear axis
		:param axis: (str) The axis name to draw
		:param base_image: (numpy.ndarray) The image to draw on
		:param draw_size: (tuple[int, int]) The size of the drawable area
		:param draw_border: (tuple[float, float]) The width of the draw size border
		:param pos: (tuple[int, int]) The center of the axis
		:param color: (int) The 24 bit hex color
		:param angle: (float) The angle of this axis in degrees
		:param label_font: (str) The font name of the axis label
		:param label_font_size: (int) The font size of the axis label
		:param label_angle: (float) The label angle in degrees
		:return: (None)
		"""

		assert isinstance(axis, str) and len(axis := str(axis)) == 1, f'{type(self).__name__}::__draw_linear_axis__ - \'axis_name\' must be a single character str'
		assert isinstance(base_image, np.ndarray), f'{type(self).__name__}::__draw_linear_axis__ - \'base_image\' must be a numpy array'
		assert isinstance(draw_size, tuple) and len(draw_size := tuple(draw_size)) == 2 and all(isinstance(x, int) for x in draw_size), f'{type(self).__name__}::__draw_linear_axis__ - \'draw_size\' must be a tuple of 2 ints'
		assert isinstance(draw_border, tuple) and len(draw_border := tuple(draw_border)) == 2 and all(isinstance(x, (int, float)) for x in draw_border), f'{type(self).__name__}::__draw_linear_axis__ - \'draw_border\' must be a tuple of 2 floats'
		assert isinstance(pos, tuple) and len(pos := tuple(pos)) == 2 and all(isinstance(x, int) for x in pos), f'{type(self).__name__}::__draw_linear_axis__ - \'pos\' must be a tuple of 2 ints'
		assert isinstance(color, int) and (color := int(color)) >= 0, f'{type(self).__name__}::__draw_linear_axis__ - \'color\' must be an int greater than 0'
		assert isinstance(angle, (int, float)), f'{type(self).__name__}::__draw_linear_axis__ - \'angle\' must be a float'
		assert isinstance(label_font, str), f'{type(self).__name__}::__draw_linear_axis__ - \'label_font\' must be a str'
		assert isinstance(label_font_size, int), f'{type(self).__name__}::__draw_linear_axis__ - \'label_font_size\' must be an int'
		assert isinstance(label_angle, (int, float)), f'{type(self).__name__}::__draw_linear_axis__ - \'label_angle\' must be a float'
		assert label_pos is None or (isinstance(label_pos, tuple) and len(label_pos := tuple(label_pos)) == 2 and all(isinstance(x, (int, float)) for x in label_pos)), f'{type(self).__name__}::__draw_linear_axis__ - \'label_pos\' must be a tuple of 2 floats'

		angle = float(angle)
		label_font_size = int(label_font_size)
		pilimage: PIL.Image.Image = PIL.Image.fromarray(base_image, 'RGBA')
		width, height, _ = base_image.shape
		radius: float = math.sqrt(width ** 2 + height ** 2) / 2
		cx, cy = int(pos[0]), int(pos[1])
		theta: float = angle * (math.pi / 180)
		lx, ly = cx + radius * math.cos(theta), cy + radius * math.sin(theta)
		rx, ry = cx + radius * math.cos(theta + math.pi), cy + radius * math.sin(theta + math.pi)
		color = color & 0xFFFFFF
		color_str: str = f'#{hex(color)[2:].rjust(6, "0")}'
		(min_, max_), minor_spacing, major_spacing, label, formatter, label_major_ticks = self.__axes__[axis]
		draw_size_unit: int = int(draw_size[0] if angle % 90 <= 45 else draw_size[1])
		draw_border_unit: float = float(draw_border[0] if angle % 90 <= 45 else draw_border[1])
		border_unit: float = draw_border_unit / 2

		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(pilimage)
		drawer.line(((lx, ly), (rx, ry)), color_str, 2)

		if minor_spacing is not None:
			minor_spacings: list[tuple[float, float]] = []
			major_spacings: list[tuple[float, float]] = []
			ratio: float = (0 - min_) / (max_ - min_)
			pos1: int = round(ratio * draw_size_unit + border_unit)
			ratio = (minor_spacing - min_) / (max_ - min_)
			pos2: int = round(ratio * draw_size_unit + border_unit)
			delta: float = pos2 - pos1
			center: Vector.Vector = Vector.Vector(cx, cy)
			l_tick_pos: Vector.Vector = Vector.Vector(center)
			r_tick_pos: Vector.Vector = Vector.Vector(center)
			axis_normal: Vector.Vector = round((Vector.Vector(lx, ly) - Vector.Vector(rx, ry)).normalized() * minor_spacing * delta, 12)
			axis_tangent: Vector.Vector = round(Vector.Vector(math.cos(theta + math.pi / 2), math.sin(theta + math.pi / 2)), 12)
			tick: int = 0

			while (r_tick_pos - center).length() < radius or (l_tick_pos - center).length() < radius:
				ttf: PIL.ImageFont.FreeTypeFont = PIL.ImageFont.truetype(f'{label_font.lower()}.ttf', label_font_size)
				is_major_tick: bool = major_spacing is not None and tick % major_spacing == 0
				tick_height: int = 10 if is_major_tick else 5
				lpos1: tuple[float, ...] = (l_tick_pos + axis_tangent * tick_height).components()
				lpos2: tuple[float, ...] = (l_tick_pos - axis_tangent * tick_height).components()
				rpos1: tuple[float, ...] = (r_tick_pos + axis_tangent * tick_height).components()
				rpos2: tuple[float, ...] = (r_tick_pos - axis_tangent * tick_height).components()
				minor_spacings.append((l_tick_pos[0], l_tick_pos[1]))
				minor_spacings.append((r_tick_pos[0], r_tick_pos[1]))
				drawer.line((lpos1, lpos2), color_str, 2)
				drawer.line((rpos1, rpos2), color_str, 2)

				if is_major_tick:
					major_spacings.append((l_tick_pos[0], l_tick_pos[1]))
					major_spacings.append((r_tick_pos[0], r_tick_pos[1]))

				if tick > 0 and is_major_tick and label_major_ticks:
					lpos: list[float, ...] = list((l_tick_pos - axis_tangent * label_font_size * 1.5).components())
					rpos: list[float, ...] = list((r_tick_pos - axis_tangent * label_font_size * 1.5).components())
					major_tick: float = (tick * minor_spacing) if l_tick_pos[1] > cy or l_tick_pos[0] < cx else (-tick * minor_spacing)
					l_major_tick, r_major_tick = self.axes_format(axis, -major_tick, major_tick)

					l, t, r, b = drawer.textbbox(lpos, l_major_tick, font=ttf, anchor='mm')

					if l < border_unit:
						lpos[0] -= l - border_unit
					if t < border_unit:
						lpos[1] -= t - border_unit
					if r >= draw_size_unit:
						lpos[0] -= draw_border_unit
					if b >= draw_size_unit:
						lpos[1] -= draw_border_unit

					l, t, r, b = drawer.textbbox(rpos, r_major_tick, font=ttf, anchor='mm')

					if l < border_unit:
						rpos[0] -= l - border_unit
					if t < border_unit:
						rpos[1] -= t - border_unit
					if r >= draw_size_unit:
						rpos[0] -= draw_border_unit
					if b >= draw_size_unit:
						rpos[1] -= draw_border_unit

					drawer.text(lpos, l_major_tick, fill=color_str, font=ttf, anchor='mm')
					drawer.text(rpos, r_major_tick, fill=color_str, font=ttf, anchor='mm')

				l_tick_pos -= axis_normal
				r_tick_pos += axis_normal
				tick += 1

			self.__last_image_minor_spacing__[axis] = tuple(minor_spacings)
			self.__last_image_major_spacing__[axis] = tuple(major_spacings)

		result: numpy.ndarray = np.array(pilimage)

		if isinstance(label, str) and label_pos is not None:
			label: str = str(label)
			Plot2D.__generate_image_text__(result, float(label_pos[0]), float(label_pos[1]), label, float(label_angle), str(label_font), 12 if label_font_size is None else label_font_size, color)

		np.copyto(base_image, result)

	def __draw_polar_axis__(self, axis: str, base_image: np.ndarray, draw_size: tuple[int, int], draw_border: tuple[float, float], pos: tuple[int, int], *, color: int = 0x888888, angle: float = 0, label_font: str = 'Arial', label_font_size: int = 12, label_angle: typing.Optional[float] = None, label_pos: typing.Optional[tuple[float, float]] = None) -> None:
		"""
		Draws a radial axis
		:param axis: (str) The axis name to draw
		:param base_image: (numpy.ndarray) The image to draw on
		:param draw_size: (tuple[int, int]) The size of the drawable area
		:param draw_border: (tuple[float, float]) The width of the draw size border
		:param pos: (tuple[int, int]) The center of the axis
		:param color: (int) The 24 bit hex color
		:param angle: (float) The angle of this axis in degrees
		:param label_font: (str) The font name of the axis label
		:param label_font_size: (int) The font size of the axis label
		:param label_angle: (float?) The label angle in degrees
		:return: (None)
		"""

		assert isinstance(axis, str) and len(axis := str(axis)) == 1, f'{type(self).__name__}::__draw_polar_axis__ - \'axis_name\' must be a single character str'
		assert isinstance(base_image, np.ndarray), f'{type(self).__name__}::__draw_polar_axis__ - \'base_image\' must be a numpy array'
		assert isinstance(draw_size, tuple) and len(draw_size := tuple(draw_size)) == 2 and all(isinstance(x, int) for x in draw_size), f'{type(self).__name__}::__draw_polar_axis__ - \'draw_size\' must be a tuple of 2 ints'
		assert isinstance(draw_border, tuple) and len(draw_border := tuple(draw_border)) == 2 and all(isinstance(x, (int, float)) for x in draw_border), f'{type(self).__name__}::__draw_polar_axis__ - \'draw_border\' must be a tuple of 2 floats'
		assert isinstance(pos, tuple) and len(pos := tuple(pos)) == 2 and all(isinstance(x, int) for x in pos), f'{type(self).__name__}::__draw_polar_axis__ - \'pos\' must be a tuple of 2 ints'
		assert isinstance(color, int) and (color := int(color)) >= 0, f'{type(self).__name__}::__draw_polar_axis__ - \'color\' must be an int greater than 0'
		assert isinstance(angle, (int, float)), f'{type(self).__name__}::__draw_polar_axis__ - \'angle\' must be a float'
		assert isinstance(label_font, str), f'{type(self).__name__}::__draw_polar_axis__ - \'label_font\' must be a str'
		assert isinstance(label_font_size, int), f'{type(self).__name__}::__draw_polar_axis__ - \'label_font_size\' must be an int'
		assert label_angle is None or label_angle is ... or isinstance(label_angle, (int, float)), f'{type(self).__name__}::__draw_polar_axis__ - \'label_angle\' must be a float'
		assert label_pos is None or (isinstance(label_pos, tuple) and len(label_pos := tuple(label_pos)) == 2 and all(isinstance(x, (int, float)) for x in label_pos)), f'{type(self).__name__}::__draw_polar_axis__ - \'label_pos\' must be a tuple of 2 floats'

		angle = float(angle)
		label_font_size = int(label_font_size)
		width, height, _ = base_image.shape
		radius: float = math.sqrt(width ** 2 + height ** 2) / 2
		cx, cy = int(pos[0]), int(pos[1])
		theta: float = angle * (math.pi / 180)
		color = color & 0xFFFFFF
		color_str: str = f'#{hex(color)[2:].rjust(6, "0")}'
		(min_, max_), minor_spacing, major_spacing, label, formatter, label_major_ticks = self.__axes__[axis]
		draw_size_unit: int = int(draw_size[0] if angle % 90 <= 45 else draw_size[1])
		draw_border_unit: float = float(draw_border[0] if angle % 90 <= 45 else draw_border[1])
		border_unit: float = draw_border_unit / 2
		axis_radius: float = (width - draw_border_unit) / 2

		pilimage: PIL.Image.Image = PIL.Image.fromarray(base_image, 'RGBA')
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(pilimage)
		ttf: PIL.ImageFont.FreeTypeFont = PIL.ImageFont.truetype(f'{label_font.lower()}.ttf', label_font_size)

		if minor_spacing is not None:
			center: Vector.Vector = Vector.Vector(cx, cy)

			for tick_angle in frange(0, 360, minor_spacing):
				is_major_tick: bool = major_spacing is not None and round(tick_angle % (major_spacing * minor_spacing), 12) == 0
				tick_height: int = 10 if is_major_tick else 5
				tick_radians: float = (tick_angle + angle) * (math.pi / 180)
				tick_pos: Vector.Vector = Vector.Vector(axis_radius * math.cos(tick_radians), axis_radius * math.sin(tick_radians))
				normal: Vector.Vector = tick_pos.normalized() * tick_height
				tick_pos += center
				ipos: tuple[float, ...] = (tick_pos - normal).components()
				opos: tuple[float, ...] = (tick_pos + normal).components()
				drawer.line((ipos, opos), color_str, 2, None)

				if is_major_tick and label_major_ticks:
					pos: list[float, ...] = list((tick_pos - normal * 4).components())
					l, t, r, b = drawer.textbbox(pos, f'{-tick_angle}', font=ttf, anchor='mm')

					if l < border_unit:
						pos[0] -= l - border_unit
					if t < border_unit:
						pos[1] -= t - border_unit
					if r >= draw_size_unit:
						pos[0] -= draw_border_unit
					if b >= draw_size_unit:
						pos[1] -= draw_border_unit

					drawer.text((pos[0], -(pos[1] - cy) + cy), f'{tick_angle}', fill=color_str, font=ttf, anchor='mm')

		result: numpy.ndarray = np.array(pilimage)
		circle: numpy.ndarray = np.zeros(base_image.shape, np.uint8)
		pilcircle: PIL.Image.Image = PIL.Image.fromarray(circle)
		drawer = PIL.ImageDraw.ImageDraw(pilcircle)
		drawer.circle((cx, cy), axis_radius, (0, 0, 0, 0), outline=color_str, width=2)
		circle = np.asarray(pilcircle)
		result = cv2.addWeighted(result, 1, circle, 1, 0)

		if isinstance(label, str) and label_pos is not None:
			label: str = str(label)
			label_pos: tuple[float, float] = float(label_pos[0]), float(label_pos[1])

			if label_angle is ... or label_angle is None:
				label_pos_v: Vector.Vector = Vector.Vector(*label_pos)
				xaxis: Vector.Vector = Vector.Vector(0, -1)
				xangle = xaxis.angle(label_pos_v)
				l, _, r, _ = drawer.textbbox((0, 0), f'{label_font}', font=ttf)
				text_width: float = r - l

				label_angle = xangle * (180 / math.pi) - 90

			Plot2D.__generate_image_text__(result, *label_pos, label, float(label_angle), str(label_font), 12 if label_font_size is None else label_font_size, color)

		np.copyto(base_image, result)

	def __add_axis__(self,  axes_name: str, *, min_: typing.Optional[float] = None, max_: typing.Optional[float] = None, minor_spacing: typing.Optional[float] = None, major_spacing: typing.Optional[int] = None, axis_label: typing.Optional[str] = None, label_formatter: typing.Optional[typing.Callable[[float, float | None], str]] = None, label_major_ticks: bool = False):
		"""
		Adds a new axis to this plot
		:param axes_name: (str) The axis's name
		:param min_: (float?) The minimum of this axis
		:param max_: (float?) The maximum of this axis
		:param minor_spacing: (float?) The spacing between minor ticks
		:param major_spacing: (float?) The spacing between major ticks
		:param axis_label: (str?) The axis label
		:param label_formatter: (Callable[[float, float?], str]?) The label formatting function for major ticks
		:param label_major_ticks: (bool) Whether to label major ticks
		:return: (None)
		"""

		assert isinstance(axes_name, str) and len(axes_name := str(axes_name)) > 0, f'{type(self).__name__}::__add_axis__ - \'axes_name\' must be a str'
		assert min_ is None or min_ is ... or isinstance(min_, (int, float)), f'{type(self).__name__}::__add_axis__ - \'min_\' must be a float or int'
		assert max_ is None or max_ is ... or isinstance(max_, (int, float)), f'{type(self).__name__}::__add_axis__ - \'max_\' must be a float or int'
		assert minor_spacing is None or minor_spacing is ... or (isinstance(minor_spacing, (int, float)) and minor_spacing > 0), f'{type(self).__name__}::__add_axis__ - \'minor_spacing\' must be a float or int greater than 0'
		assert major_spacing is None or major_spacing is ... or (isinstance(major_spacing, int) and major_spacing > 0), f'{type(self).__name__}::__add_axis__ - \'major_spacing\' must be an int greater than 0'
		assert axis_label is None or axis_label is ... or isinstance(axis_label, str), f'{type(self).__name__}::__add_axis__ - \'axis_label\' must be a str'
		assert label_formatter is None or label_formatter is ... or callable(label_formatter), f'{type(self).__name__}::__add_axis__ - \'label_formatter\' must be a callable'
		assert isinstance(label_major_ticks, bool), f'{type(self).__name__}::__add_axis__ - \'label_major_ticks\' must be a bool'

		if min_ is not None and min_ is not ... and max_ is not None and max_ is not ...:
			assert max_ > min_, f'{type(self).__name__}::__add_axis__ - \'max_\' must be greater than \'min_\''

		for axis in axes_name:
			assert axis not in self.__axes__, f'{type(self).__name__}::__add_axis__ - Axis \'{axis}\' already exists'

			self.__axes__[axis] = (
				(None if min_ is None or min_ is ... else float(min_), None if max_ is None or max_ is ... else float(max_)),
				None if minor_spacing is None or minor_spacing is ... else float(minor_spacing),
				None if major_spacing is None or major_spacing is ... else int(major_spacing),
				None if axis_label is None or axis_label is ... or len(axis_label := str(axis_label)) == 0 else axis_label,
				None if label_formatter is None or label_formatter is ... else label_formatter,
				bool(label_major_ticks)
			)

	def axis_info(self, axes: str, *, min_: typing.Optional[float] = ..., max_: typing.Optional[float] = ..., minor_spacing: typing.Optional[float] = ..., major_spacing: typing.Optional[int] = ..., axis_label: typing.Optional[str] = ..., label_formatter: typing.Optional[typing.Callable[[float, float | None], str]] = ..., label_major_ticks: typing.Optional[bool] = ...):
		"""
		Modifies one or more axes
		:param axes: (str) The axes to modify
		:param min_: (float?) The minimum of this axis
		:param max_: (float?) The maximum of this axis
		:param minor_spacing: (float?) The spacing between minor ticks
		:param major_spacing: (float?) The spacing between major ticks
		:param axis_label: (str?) The axis label
		:param label_formatter: (Callable[[float, float?], str]?) The label formatting function for major ticks
		:param label_major_ticks: (bool?) Whether to label major ticks
		:return: (None)
		"""

		assert isinstance(axes, str) and len(axes := str(axes)) > 0, f'{type(self).__name__}::axis_info - \'axes\' must be a non-empty str'
		assert min_ is None or min_ is ... or isinstance(min_, (int, float)), f'{type(self).__name__}::axis_info - \'min_\' must be a float or int'
		assert max_ is None or max_ is ... or isinstance(max_, (int, float)), f'{type(self).__name__}::axis_info - \'max_\' must be a float or int'
		assert minor_spacing is None or minor_spacing is ... or (isinstance(minor_spacing, (int, float)) and minor_spacing > 0), f'{type(self).__name__}::axis_info - \'minor_spacing\' must be a float or int greater than 0'
		assert major_spacing is None or major_spacing is ... or (isinstance(major_spacing, int) and major_spacing > 0), f'{type(self).__name__}::axis_info - \'major_spacing\' must be an int greater than 0'
		assert axis_label is None or axis_label is ... or isinstance(axis_label, str), f'{type(self).__name__}::axis_info - \'axis_label\' must be a str'
		assert label_formatter is None or label_formatter is ... or callable(label_formatter), f'{type(self).__name__}::axis_info - \'label_formatter\' must be a callable'
		assert label_major_ticks is ... or isinstance(label_major_ticks, bool), f'{type(self).__name__}::axis_info - \'label_major_ticks\' must be a bool'

		if min_ is not None and min_ is not ... and max_ is not None and max_ is not ...:
			assert max_ > min_, f'{type(self).__name__}::__add_axis__ - \'max_\' must be greater than \'min_\''

		for axis in axes:
			assert axis in self.__axes__, f'{type(self).__name__}::axis_info - No such axis \'{axis}\''
			bounds, minor, major, label, formatter, label_major = self.__axes__[axis]

			self.__axes__[axis] = (
				(bounds[0] if min_ is ... else None if min_ is None else float(min_), bounds[1] if max_ is ... else None if max_ is None else float(max_)),
				minor if minor_spacing is ... else None if minor_spacing is None else float(minor_spacing),
				major if major_spacing is ... else None if major_spacing is None else int(major_spacing),
				label if axis_label is ... else None if axis_label is None or len(axis_label := str(axis_label)) == 0 else axis_label,
				formatter if label_formatter is ... else None if label_formatter is None else label_formatter,
				label_major if label_major_ticks is ... else bool(label_major_ticks)
			)

	def axes_bounded(self, axes: str) -> bool:
		"""
		:param axes: (str) The axes to check
		:return: (bool) True if the specified axes all have bounds
		"""

		assert isinstance(axes, str) and len(axes := str(axes)) > 0, f'{type(self).__name__}::axes_bounded - \'axes\' must be a non-empty str'

		for axis in axes:
			assert axis in self.__axes__, f'{type(self).__name__}::axes_bounded - No such axis \'{axis}\''
			min_, max_ = self.__axes__[axis][0]

			if min_ is None or max_ is None:
				return False

		return True

	def axes_bounding(self, axes: str) -> tuple[int, ...]:
		"""
		:param axes: (str) The axes to check
		:return: (bool) True if the specified axes all have bounds
		"""

		assert isinstance(axes, str) and len(axes := str(axes)) > 0, f'{type(self).__name__}::axes_bounding - \'axes\' must be a non-empty str'
		bounding: list[int, ...] = []

		for axis in axes:
			assert axis in self.__axes__, f'{type(self).__name__}::axes_bounding - No such axis \'{axis}\''
			min_, max_ = self.__axes__[axis][0]

			if min_ is None and max_ is None:
				bounding.append(AxisPlot2D.AxisBounding.UNBOUNDED)
			elif min_ is None and max_ is not None:
				bounding.append(AxisPlot2D.AxisBounding.UPPER)
			elif min_ is not None and max_ is None:
				bounding.append(AxisPlot2D.AxisBounding.LOWER)
			elif min_ is not None and max_ is not None:
				bounding.append(AxisPlot2D.AxisBounding.BOUND)

		return tuple(bounding)

	def axis_bounds(self, axis: str) -> tuple[float | None, float | None]:
		"""
		:param axis: (str) The axis name
		:return: (tuple[float?, float?]) The axis bounds
		"""

		assert isinstance(axis, str) and len(axis := str(axis)) == 1, f'{type(self).__name__}::axis_bounds - \'axis\' must be a single character str'
		assert axis in self.__axes__, f'{type(self).__name__}::axis_bounds - No such axis \'{axis}\''
		return self.__axes__[axis][0]

	def axes_bounds(self, axes: str) -> tuple[tuple[float | None, float | None], ...]:
		"""
		:param axes: (str) The axes' names
		:return: (tuple[tuple[float?, float?]]) The axes' bounds
		"""
		assert isinstance(axes, str) and len(axes := str(axes)) > 0, f'{type(self).__name__}::axes_bounds - \'axes\' must be a non-empty str'
		bounds: list[tuple[float | None, float | None]] = []

		for axis in axes:
			assert axis in self.__axes__, f'{type(self).__name__}::axes_bounds - No such axis \'{axis}\''
			bounds.append(self.__axes__[axis][0])

		return tuple(bounds)

	def axis_minor_spacing(self, axis: str) -> float | None:
		"""
		:param axis: (str) The axis name
		:return: (float?) The axis minor spacing
		"""

		assert isinstance(axis, str) and len(axis := str(axis)) == 1, f'{type(self).__name__}::axis_minor_spacing - \'axis\' must be a single character str'
		assert axis in self.__axes__, f'{type(self).__name__}::axis_minor_spacing - No such axis \'{axis}\''
		return self.__axes__[axis][1]

	def axes_minor_spacing(self, axes: str) -> tuple[float | None, ...]:
		"""
		:param axes: (str) The axes' names
		:return: (tuple[float?]) The axes' minor spacing
		"""
		assert isinstance(axes, str) and len(axes := str(axes)) > 0, f'{type(self).__name__}::axes_minor_spacing - \'axes\' must be a non-empty str'
		minor_spacings: list[str | None] = []

		for axis in axes:
			assert axis in self.__axes__, f'{type(self).__name__}::axes_minor_spacing - No such axis \'{axis}\''
			minor_spacings.append(self.__axes__[axis][1])

		return tuple(minor_spacings)

	def axis_major_spacing(self, axis: str) -> int | None:
		"""
		:param axis: (str) The axis name
		:return: (float?) The axis major spacing
		"""

		assert isinstance(axis, str) and len(axis := str(axis)) == 1, f'{type(self).__name__}::axis_major_spacing - \'axis\' must be a single character str'
		assert axis in self.__axes__, f'{type(self).__name__}::axis_major_spacing - No such axis \'{axis}\''
		return self.__axes__[axis][2]

	def axes_major_spacing(self, axes: str) -> tuple[int | None, ...]:
		"""
		:param axes: (str) The axes' names
		:return: (tuple[float?]) The axes' major spacing
		"""
		assert isinstance(axes, str) and len(axes := str(axes)) > 0, f'{type(self).__name__}::axes_major_spacing - \'axes\' must be a non-empty str'
		major_spacings: list[str | None] = []

		for axis in axes:
			assert axis in self.__axes__, f'{type(self).__name__}::axes_major_spacing - No such axis \'{axis}\''
			major_spacings.append(self.__axes__[axis][2])

		return tuple(major_spacings)

	def axis_minor_spacings(self, axis: str) -> tuple[tuple[float, float], ...] | None:
		"""
		:param axis: (str) The axis name
		:return: (float?) The axis's last minor spacings
		"""

		assert isinstance(axis, str) and len(axis := str(axis)) == 1, f'{type(self).__name__}::axis_minor_spacings - \'axis\' must be a single character str'
		assert axis in self.__axes__, f'{type(self).__name__}::axis_minor_spacings - No such axis \'{axis}\''
		return self.__last_image_minor_spacing__[axis] if axis in self.__last_image_minor_spacing__ else None

	def axes_minor_spacings(self, axes: str) -> tuple[float | None, ...]:
		"""
		:param axes: (str) The axes' names
		:return: (tuple[float?]) The axes' minor spacing
		"""
		assert isinstance(axes, str) and len(axes := str(axes)) > 0, f'{type(self).__name__}::axes_minor_spacing - \'axes\' must be a non-empty str'
		minor_spacings: list[str | None] = []

		for axis in axes:
			assert axis in self.__axes__, f'{type(self).__name__}::axes_minor_spacing - No such axis \'{axis}\''
			minor_spacings.append(self.__axes__[axis][1])

		return tuple(minor_spacings)

	def axis_major_spacings(self, axis: str) -> int | None:
		"""
		:param axis: (str) The axis name
		:return: (float?) The axis major spacing
		"""

		assert isinstance(axis, str) and len(axis := str(axis)) == 1, f'{type(self).__name__}::axis_major_spacing - \'axis\' must be a single character str'
		assert axis in self.__axes__, f'{type(self).__name__}::axis_major_spacing - No such axis \'{axis}\''
		return self.__axes__[axis][2]

	def axes_major_spacings(self, axes: str) -> tuple[int | None, ...]:
		"""
		:param axes: (str) The axes' names
		:return: (tuple[float?]) The axes' major spacing
		"""
		assert isinstance(axes, str) and len(axes := str(axes)) > 0, f'{type(self).__name__}::axes_major_spacing - \'axes\' must be a non-empty str'
		major_spacings: list[str | None] = []

		for axis in axes:
			assert axis in self.__axes__, f'{type(self).__name__}::axes_major_spacing - No such axis \'{axis}\''
			major_spacings.append(self.__axes__[axis][2])

		return tuple(major_spacings)

	def axis_label(self, axis: str) -> str | None:
		"""
		:param axis: (str) The axis name
		:return: (str?) The axis label
		"""

		assert isinstance(axis, str) and len(axis := str(axis)) == 1, f'{type(self).__name__}::axis_label - \'axis\' must be a single character str'
		assert axis in self.__axes__, f'{type(self).__name__}::axis_label - No such axis \'{axis}\''
		return self.__axes__[axis][3]

	def axes_label(self, axes: str) -> tuple[str | None, ...]:
		"""
		:param axes: (str) The axes' names
		:return: (tuple[str?]) The axes' label
		"""
		assert isinstance(axes, str) and len(axes := str(axes)) > 0, f'{type(self).__name__}::axes_label - \'axes\' must be a non-empty str'
		labels: list[str | None] = []

		for axis in axes:
			assert axis in self.__axes__, f'{type(self).__name__}::axes_label - No such axis \'{axis}\''
			labels.append(self.__axes__[axis][3])

		return tuple(labels)

	def axis_format(self, axis: str, data: float | tuple[float, float]) -> str:
		"""
		:param axis: (str) The axis name
		:param data: (float | tuple[float, float) A single value or point
		:return: (str) The formatted value or point
		"""

		assert isinstance(axis, str) and len(axis := str(axis)) == 1, f'{type(self).__name__}::axis_format - \'axis\' must be a single character str'
		assert isinstance(data, (int, float)) or (isinstance(data, tuple) and len(data := tuple(data)) == 2 and all(isinstance(x, (int, float)) for x in data)), f'{type(self).__name__}::axis_format - \'data\' must be a float or tuple of two floats'
		assert axis in self.__axes__, f'{type(self).__name__}::axis_label - No such axis \'{axis}\''
		formatter: typing.Callable[[float, float], str] = self.__axes__[axis][4]
		return f'{data}' if formatter is None else formatter(float(data), None) if isinstance(data, (int, float)) else formatter(*[float(x) for x in data])

	def axes_format(self, axes: str, *data: float | tuple[float, float]) -> tuple[str, ...]:
		"""
		:param axes: (str) The axes' names
		:param data: (*float | *tuple[float, float) A single value or point; either one for all axes or one for each axis
		:return: (tuple[str?]) The axes' label
		"""
		assert isinstance(axes, str) and len(axes := str(axes)) > 0, f'{type(self).__name__}::axes_format - \'axes\' must be a non-empty str'
		assert len(data) == 1 or len(axes) == 1 or len(data) == len(axes), f'{type(self).__name__}::axes_format - Cannot map {len(data)} points to {len(axes)} {"axis" if axes == 1 else "axes"}'
		formatted: list[str] = []

		for i, axis in enumerate(axes):
			assert axis in self.__axes__, f'{type(self).__name__}::axes_format - No such axis \'{axis}\''
			point: float | tuple[float, float] = data[0] if len(data) == 1 or len(axis) == 1 else data[i]
			assert isinstance(point, (int, float)) or (isinstance(point, tuple) and len(point := tuple(point)) == 2 and all(isinstance(x, (int, float)) for x in point)), f'{type(self).__name__}::axes_format - \'data[{i}]\' must be a float or tuple of two floats'
			formatter: typing.Callable[[float, float], str] = self.__axes__[axis][4]
			result: str = f'{data}' if formatter is None else formatter(float(data), None) if isinstance(data, (int, float)) else formatter(*[float(x) for x in data])
			formatted.append(result)

		return tuple(formatted)

	@property
	def axes(self) -> str:
		return ''.join(self.__axes__.keys())


class Plot2D:
	"""
	[Plot2D] - Base class for a single-plot plotter
	"""
	__PLOT_SHAPE_MASKS: dict[str, np.ndarray] = {}

	def __init__(self):
		"""
		[Plot2D] - Base class for a single-plot plotter
		- Constructor -
		"""

		self.__points__: set[tuple[float, float]] = set()
		self.__plot_info__: dict[str, typing.Any] = {'color': 0xFFFFFF, 'label_points': False, 'point_size': 15, 'extra': {}}
		self.__scale__: float = 1

	@staticmethod
	def __generate_image_text__(src: np.ndarray, x: int | float, y: int | float, text: str, angle: float = 0, font: str = 'arial', font_size: int = 10, font_color: int = 0xFFFFFF) -> None:
		"""
		Generates text for an image modifying the image in-place
		:param src: (numpy.ndarray) The source image to modify
		:param x: (int) The x coordinate of the text
		:param y: (int) The y coordinate of the text
		:param text: (str) The text to generate
		:param angle: (float) The angle of the text in degrees
		:param font: (str) The font name of the text
		:param font_size: (int) The font size of the text
		:param font_color: (int) The 24-bit color of the text
		:return: (None)
		"""

		x: int = round(x)
		y: int = round(y)
		text_base: np.ndarray = np.dstack((np.zeros((512, 512, 3), dtype=np.uint8), np.full((512, 512, 1), 0xFF, dtype=np.uint8)))
		image: PIL.Image.Image = PIL.Image.fromarray(text_base, 'RGBA')
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)
		font: PIL.ImageFont.FreeTypeFont = PIL.ImageFont.truetype(f'{font.lower()}.ttf', font_size)
		drawer.text((256, 256), text, font=font, fill=(255, 255, 255, 255))
		text_base: np.ndarray = np.asarray(image)
		rotation_matrix: np.ndarray = cv2.getRotationMatrix2D((256, 256), angle, 1.0)
		text_base: np.ndarray = cv2.warpAffine(text_base, rotation_matrix, text_base.shape[1::-1], flags=cv2.INTER_LINEAR)
		alpha_mask: np.ndarray = ((np.mean(text_base[:, :, :3], axis=2) > 0x00) * 255).astype(np.uint8)
		text_base[:, :, 3] = alpha_mask
		borders: list[int] = [0, 0, 512, 512]

		for i in range(512):
			if np.any(alpha_mask[i, :] > 0):
				borders[0] = i
				break

		for i in range(512):
			if np.any(alpha_mask[:, i] > 0):
				borders[1] = i
				break

		for i in range(512, 0, -1):
			if np.any(alpha_mask[:, i - 1] > 0):
				borders[2] = i
				break

		for i in range(512, 0, -1):
			if np.any(alpha_mask[i - 1, :] > 0):
				borders[3] = i
				break

		text_base = text_base[borders[0]:borders[3], borders[1]:borders[2], :]
		black_ratio: np.ndarray = np.round(np.mean(text_base[:, :, :3], axis=2)).astype(np.uint8)
		red: np.ndarray = np.round(np.full(text_base.shape[:2], (font_color >> 16) & 0xFF) * (black_ratio / 0xFF)).astype(np.uint8)
		green: np.ndarray = np.round(np.full(text_base.shape[:2], (font_color >> 8) & 0xFF) * (black_ratio / 0xFF)).astype(np.uint8)
		blue: np.ndarray = np.round(np.full(text_base.shape[:2], font_color & 0xFF) * (black_ratio / 0xFF)).astype(np.uint8)
		text_base = np.dstack((red, green, blue, black_ratio))
		background: np.ndarray = src[y:y + text_base.shape[0], x:x + text_base.shape[1], :]
		text_base = cv2.addWeighted(background, 1, text_base[:background.shape[0], :background.shape[1], :], 1, 0)

		if text_base is not None:
			src[y:y + text_base.shape[0], x:x + text_base.shape[1], :] = text_base

	def __legend_image__(self, src: np.ndarray) -> np.ndarray:
		"""
		Generates the image for this plot including the legend
		:param src: (numpy.ndarray) The base image
		:return: (numpy.ndarray) The result image
		"""

		window_size_unit: int = round(1024 * self.__scale__)
		legend_window_size: tuple[int, int] = (round(50 * self.__scale__ * (len(self.__points__) + 0)), round(200 * self.__scale__))
		legend_padding: int = round(20 * self.__scale__)
		final_image_size: tuple[int, int] = (max(window_size_unit, legend_window_size[1]), window_size_unit + legend_window_size[1] + legend_padding)
		legend_base: np.ndarray = np.dstack((np.full((legend_window_size[0], legend_window_size[1], 3), 0x22, dtype=np.uint8), np.full((legend_window_size[0], legend_window_size[1], 1), 0xFF, dtype=np.uint8)))
		legend_padding = round(legend_padding / 2)
		start_y: int = 15
		start_x: int = 15
		legend_items: dict[str, tuple[int | None, typing.Any]] = self.__legend__()

		for i in range(legend_window_size[0]):
			legend_base[i, :2, :3] = np.uint8(0x66)
			legend_base[i, -2:, :3] = np.uint8(0x66)

		for i in range(legend_window_size[1]):
			legend_base[:2, i, :3] = np.uint8(0x66)
			legend_base[-2:, i, :3] = np.uint8(0x66)

		for point_name, (point_color, point_value) in legend_items.items():
			point_color = 0x222222 if not isinstance(point_color, int) else int(point_color)
			r: np.ndarray = np.full((20, 50, 1), (point_color >> 16) & 0xFF, dtype=np.uint8)
			g: np.ndarray = np.full((20, 50, 1), (point_color >> 8) & 0xFF, dtype=np.uint8)
			b: np.ndarray = np.full((20, 50, 1), point_color & 0xFF, dtype=np.uint8)
			rect: np.ndarray = np.dstack((r, g, b))

			for i in range(rect.shape[0]):
				rect[i, :2, :3] = np.uint8(0x66)
				rect[i, -2:, :3] = np.uint8(0x66)

			for i in range(rect.shape[1]):
				rect[:2, i, :3] = np.uint8(0x66)
				rect[-2:, i, :3] = np.uint8(0x66)

			Plot2D.__generate_image_text__(legend_base, start_x + 75, start_y + 5, f'{point_name} ... ({point_value})', font='Arial', font_size=round(16 * self.__scale__))
			legend_base[start_y:start_y + 20, start_x: start_x + 50, :3] = rect
			start_y += 50

		final_image: numpy.ndarray = np.dstack((np.full((final_image_size[0], final_image_size[1], 3), 0x22, dtype=np.uint8), np.full((final_image_size[0], final_image_size[1], 1), 0xFF, dtype=np.uint8)))
		final_image[:window_size_unit, :window_size_unit, :] = src
		final_image[legend_padding:legend_window_size[0] + legend_padding, -200 - legend_padding:-legend_padding, :] = legend_base
		return final_image

	def __image__(self) -> tuple[np.ndarray, tuple[int, int], tuple[float, float], int, int]:
		"""
		Generates the base image for this plot
		:return: (tuple[numpy.ndarray, tuple[int, int], tuple[float, float], int, int) A tuple containing the blank, base image, the draw size, the draw border, and the window and draw size units
		"""

		window_size_unit: int = round(1024 * self.__scale__)
		draw_size_unit: int = round(1000 * self.__scale__)

		base_image: np.ndarray = np.dstack((np.full((window_size_unit, window_size_unit, 3), 0x22, dtype=np.uint8), np.full((window_size_unit, window_size_unit, 1), 0xFF, dtype=np.uint8)))
		draw_size: tuple[int, int] = (draw_size_unit, draw_size_unit)
		draw_border: tuple[int, int] = (window_size_unit - draw_size_unit, window_size_unit - draw_size_unit)

		for i in range(window_size_unit):
			base_image[:2, i, :3] = np.uint8(0x66)
			base_image[i, :2, :3] = np.uint8(0x66)
			base_image[-2:, i, :3] = np.uint8(0x66)
			base_image[i, -2:, :3] = np.uint8(0x66)

		return base_image, draw_size, draw_border, window_size_unit, draw_size_unit

	def __show__(self, show_legend: bool = False) -> tuple[tk.Tk, tk.Toplevel | None]:
		"""
		Creates the Tkinter window and image to display this plot
		:param show_legend: (bool) If true, the legend will be shown
		:return: (tuple[tkinter.Tk, tkinter.Toplevel | None]) The tkinter window and legend top level if 'show_legend' otherwise false
		"""

		assert type(show_legend) is bool, f'{type(self).__name__}::show - \'show_legend\' must be a bool'

		def _zoom(e):
			nonlocal tk_image
			nonlocal scroll_stack

			direc: int = e.delta // abs(e.delta)
			old_x_min, old_x_max = self.__x_axis_size__
			old_y_min, old_y_max = self.__y_axis_size__

			if old_x_min is None or old_x_max is None or old_y_min is None or old_y_max is None:
				return

			delta_x = old_x_max - old_x_min
			delta_y = old_y_max - old_y_min

			if abs(delta_x) < 1e-6 or abs(delta_y) < 1e-6:
				return

			old_center_x: float = old_x_min + (delta_x / 2)
			old_center_y: float = old_y_min + (delta_y / 2)
			new_center_x: float = old_x_min + e.x / window_size[0] * delta_x
			new_center_y: float = old_y_min + e.y / window_size[1] * delta_y
			scroll_stack += 0.1 * direc
			scale: float = 1 - scroll_stack
			new_x_min: float = old_x_min * scale
			new_x_max: float = old_x_max * scale
			new_y_min: float = old_y_min * scale
			new_y_max: float = old_y_max * scale
			self.__x_axis_size__ = (new_x_min, new_x_max)
			self.__y_axis_size__ = (new_y_min, new_y_max)

			tk_image = PIL.ImageTk.PhotoImage(PIL.Image.fromarray(cv2.resize(self.as_image(show_legend=False), window_size, interpolation=cv2.INTER_AREA)))
			canvas.itemconfigure(image_id, image=tk_image)

			self.__x_axis_size__ = (old_x_min, old_x_max)
			self.__y_axis_size__ = (old_y_min, old_y_max)

		root = tk.Tk()
		root.geometry('800x800')
		root.title(f'{type(self).__name__}@{id(self)}')
		root.config(bg='#222222')
		root.resizable(False, False)
		root.bind('<Escape>', lambda e: root.destroy())
		window_size: tuple[float, float] = (775, 775)
		canvas = tk.Canvas(root, bg='#222222', bd=0, highlightthickness=2, highlightcolor='#444444', width=window_size[0], height=window_size[1])
		canvas.focus_set()
		canvas.place(relx=0.5, rely=0.5, anchor=tkc.CENTER)
		tk_image = PIL.ImageTk.PhotoImage(PIL.Image.fromarray(cv2.resize(self.as_image(show_legend=False), window_size, interpolation=cv2.INTER_AREA)))
		image_id: int = canvas.create_image(1, 1, image=tk_image, anchor=tkc.NW)
		root.bind('<MouseWheel>', _zoom)
		scroll_stack: float = 0
		legend: None | tk.Toplevel = None

		if show_legend:
			root.update()
			offset_x: int
			offset_y: int
			offset_x, offset_y = (int(x) for x in root.geometry().split('+')[1:])

			if offset_x < 200:
				offset_x = 200
				root.geometry(f'800x800+200+{offset_y}')

			legend = tk.Toplevel(root)
			legend.geometry(f'200x300+{offset_x - 200}+{offset_y + 100}')
			legend.title('Legend')
			legend.resizable(False, True)
			legend.overrideredirect(True)
			legend_canvas = tk.Canvas(legend, bg='#222222', bd=0, highlightthickness=2, highlightcolor='#444444', width=window_size[0], height=window_size[1])
			legend_canvas.place(x=0, y=0, relwidth=1, relheight=1, anchor=tkc.NW)

			start_x: int = 10
			start_y: int = 10
			legend_canvas: tk.Canvas = next(x for x in legend.winfo_children() if isinstance(x, tk.Canvas))
			legend_items: dict[str, tuple[int | None, typing.Any]] = self.__legend__()

			for i, point_name in enumerate(legend_items):
				point_color, point_value = legend_items[point_name]
				color: str = f'#{hex(point_color)[2:].zfill(6)}'
				legend_canvas.create_rectangle(start_x, start_y, start_x + 50, start_y + 20, outline='#eeeeee', fill=color)
				text: int = legend_canvas.create_text(start_x + 60, start_y + 10, fill=color, text='Default' if len(point_name) == 0 else point_name, font=('', 12), anchor=tkc.W)
				value: str = str(point_value)
				right: int = legend_canvas.bbox(text)[2]
				legend_canvas.create_text(right + 10, start_y + 10, fill='#ffffff', text=f'({" " * round(len(value) * 2)})', font=('', 10), anchor=tkc.W)
				legend_canvas.create_text(right + 16, start_y + 10, fill=color, text=value, font=('', 10), anchor=tkc.W)
				start_y += 30

			def _configure(event):
				nonlocal offset_x
				nonlocal offset_y

				offset_x, offset_y = (int(x) for x in root.geometry().split('+')[1:])

				if offset_x < 200:
					offset_x = 200
					root.geometry(f'800x800+200+{offset_y}')

				legend.geometry(f'200x300+{offset_x - 200}+{offset_y + 100}')

			root.bind('<Configure>', _configure)

		return root, legend

	def __legend__(self) -> dict[str, tuple[int | None, typing.Any]]:
		"""
		Generates the legend items used by Plot2D::legend_image
		:return: (dict[str, tuple[int | None, typing.Any]]) A dictionary - { item_name: (item_color, item_value) }
		"""

		return {}

	def plot_info(self, color: typing.Optional[tuple[int, int, int] | str | int] = ..., label_points: typing.Optional[bool] = ..., point_size: typing.Optional[int] = ..., extra: typing.Optional[dict] = ..., **extra_kwargs) -> None:
		"""
		Sets information for the plot
		:param color: (tuple[float | int]? or str? or int?) The color to use for plot points, either an rgb tuple, hex-string, or color integer
		:param label_points: (bool?) Whether to label points
		:param point_size: (int?) The size (in pixels) of points
		:param extra: Extra (dict?) metadata to save
		:param extra_kwargs: (**ANY) Extra metadata to save
		:return: (None)
		:raises AssertionError: If any arguments' type or value are incorrect
		"""

		assert color is None or color is ... or isinstance(color, (tuple, str, int)), f'{type(self).__name__}::plot_info - \'color\' must be a color str, int, or RGB tuple'
		assert color is None or color is ... or isinstance(color, (str, int)) or (len(color) == 3 and all(type(x) is int for x in color)), f'{type(self).__name__}::plot_info - \'color\' must be a color str, int, or RGB tuple'
		assert label_points is None or label_points is ... or isinstance(label_points, bool), f'{type(self).__name__}::plot_info - \'label_points\' must be a bool'
		assert point_size is None or point_size is ... or isinstance(point_size, int) and point_size > 0, f'{type(self).__name__}::plot_info - \'size\' must be an int greater than 0 or None'
		assert extra is None or extra is ... or isinstance(extra, dict), f'{type(self).__name__}::point_info - \'extra\' must be a dict or None'

		extra_data: dict = ({} if extra is None or extra is ... else extra) | extra_kwargs

		if color is not None and color is not ...:
			hex_color: int = 0

			if isinstance(color, tuple):
				color = tuple(color)
				hex_color |= ((color[0] << 16) & 0xFF)
				hex_color |= ((color[1] << 8) & 0xFF)
				hex_color |= (color[2] & 0xFF)
			elif isinstance(color, str):
				color = str(color)

				if color[0] == '#':
					hex_color = int(color[1:], 16)
				else:
					hex_color = int(color, 16)
			elif isinstance(color, int):
				hex_color = int(color) & 0xFFFFFF

			self.__plot_info__['color'] = hex_color

		if label_points is not None and label_points is not ...:
			self.__plot_info__['label_points'] = bool(label_points)

		if point_size is not None and point_size is not ...:
			self.__plot_info__['point_size'] = int(point_size)

		for k, v in extra_data.items():
			if v is not None and v is not ...:
				self.__plot_info__['extra'][k] = v

	def add_points(self, *points: tuple[float | int, float | int] | Vector.Vector) -> None:
		"""
		Adds points to the plot
		:param points: (*tuple[float | int] or *Vector) A variadic list of either 2D tuples or 2D vectors
		:return: (None)
		:raises AssertionError: If any arguments' type is incorrect
		"""

		for point in points:
			if type(point) is tuple and len(point) == 2 and all(type(x) in (float, int) for x in point):
				self.__points__.add(point)
			elif type(point) is Vector.Vector and point.dimension() == 2:
				self.__points__.add((point[0], point[1]))
			else:
				raise TypeError(f'{type(self).__name__}::add_points - \'*points\' point must be either a tuple of length 2 or a Math.Vector.Vector of dimension 2')

	def transformed(self, function: typing.Callable, *, handle_exceptions: tuple[type, ...] = (ValueError,)) -> set[tuple[float, float]]:
		"""
		Returns a list of the internal points passed through a transformer function
		:param function: (CALLABLE) The function to transform the points; should accept 2 floats and return a tuple of 2 floats
		:param handle_exceptions: (tuple[type]) A list of exceptions to catch
		:return: (set[tuple[float]]) The transformed points
		:raises AssertionError: If 'function' is not callable
		:raises ArithmeticError: If transforming a point failed
		"""

		assert callable(function), f'{type(self).__name__}::transform - \'function\' must be a callable accepting two floats and returning a tuple of two floats'

		transformed: set[tuple[float, float]] = set()

		for point in self.__points__:
			try:
				pair = function(*point)

				if pair is None:
					continue

				x, y = pair
				transformed.add((float(x), float(y)))
			except Exception as e:
				if isinstance(e, handle_exceptions):
					continue

				raise ArithmeticError(f'Point transformation failed at point {point}') from e

		return transformed

	def transform(self, function: typing.Callable, *, handle_exceptions: tuple[type, ...] = (ValueError,)) -> None:
		"""
		Transforms the internal list of points in-place via a transformer function
		:param function: (CALLABLE) The function to transform the points; should accept 2 floats and return a tuple of 2 floats
		:param handle_exceptions: (tuple[type]) A list of exceptions to catch
		:return: (None)
		:raises AssertionError: If 'function' is not callable
		:raises ArithmeticError: If transforming a point failed
		"""

		self.__points__ = self.transformed(function, handle_exceptions=handle_exceptions)

	def set_scale(self, scale: float = 1) -> None:
		"""
		Sets the output image scale
		Default output image size is 1024x1024
		:param scale: (float) The scale, which must be a value above 0 (defaults to 1)
		:return: (None)
		:raises AssertionError: If scale is not a float or int or scale is less than or equal to 0
		"""

		assert type(scale) in (int, float) and scale > 0, f'{type(self).__name__}::set_scale - \'scale\' must be a float or int greater than 0'
		self.__scale__ = scale

	def as_csv(self, filepath: str) -> None:
		"""
		Saves the internal list of points to a csv file
		:param filepath: (str) The filepath to save to
		:return: (None)
		:raises AssertionError: If 'filepath' is not a str
		"""

		assert type(filepath) is str, f'{type(self).__name__}::as_csv - \'filepath\' must be a string'

		file = FileSystem.File(filepath)

		if not file.exists():
			file.create()

		with file.open('w') as f:
			points_str: str = '\n'.join(f'{point[0]},{point[1]}' for point in self.__points__)
			f.write(f'x,y\n{points_str}\n\n')

	def as_image(self, show_legend: bool = False) -> np.ndarray:
		"""
		Returns this plot as an image
		:param show_legend: (bool) Whether to display the legend
		:return: (numpy.ndarray) The RGB image pixel array
		"""

		base_image: np.ndarray
		base_image, *_ = self.__image__()

		if show_legend:
			base_image = self.__legend_image__(base_image)

		return base_image

	def show(self, show_legend: bool = False) -> None:
		"""
		Shows the plot in a separate tkinter window
		:param show_legend: (bool) Whether to display the legend
		:return: (None)
		:raises AssertionError: If 'show_legend' is not a bool
		"""

		self.__show__(show_legend)[0].mainloop()

	def save(self, filepath: str, show_legend: bool = False) -> None:
		"""
		Saves the plot to an image file
		:param filepath: (str) The filepath to write to
		:param show_legend: (bool) Whether to show the legend
		:return: (None)
		:raises AssertionError: If 'show_legend' is not a bool or 'filepath' is not a str
		"""

		file = FileSystem.File(filepath)

		if not file.exists():
			file.create()

		assert type(show_legend) is bool, f'{type(self).__name__}::show - \'show_legend\' must be a bool'

		PIL.Image.fromarray(self.as_image(show_legend=show_legend)).save(file.filepath())

	def get_points(self, order: str | typing.Callable = None) -> tuple[tuple[float, float], ...] | set[tuple[float, float]]:
		"""
		Gets the internal list of points
		:param order: (str or CALLABLE) If 'x', orders points based on their x values; If 'y', orders points based on their 'y' values; if a callable, sorts based on that function; Otherwise returns unordered points
		:return: (tuple or set) A set if left unordered, otherwise an ordered tuple
		:raises AssertionError: If order is not a valid axis and order it not callable
		"""

		if order is None:
			return self.__points__.copy()
		else:
			if order == 'x':
				sorter: typing.Callable = lambda point: point[0]
			elif order == 'y':
				sorter: typing.Callable = lambda point: point[1]
			else:
				sorter: typing.Callable = order

			assert callable(sorter), f'{type(self).__name__}::get_points - \'order\' must be a callable, \'x\', \'y\', or None'

			return tuple(sorted(self.__points__, key=sorter))


class MultiPlot2D(Plot2D):
	"""
	[Plot2D] - Base class for a multi-plot plotter
	"""

	def __init__(self):
		"""
		[Plot2D] - Base class for a multi-plot plotter
		- Constructor -
		"""

		super().__init__()
		self.__points__: dict[str, set[tuple[float, float]]] = {'': set()}
		self.__plot_info__: dict[str, dict[str, typing.Any]] = {'': {'color': 0xFFFFFF, 'label_points': False, 'point_size': 15, 'extra': {}}}
		self.__current_plot__: str = ''

	def __image__(self, plot_names: tuple[str, ...] = (), *args, **kwargs) -> tuple[np.ndarray, tuple[int, int], tuple[float, float], int, int]:
		base_image: np.ndarray
		draw_size: tuple[int, int]
		draw_border: tuple[float, float]
		window_size_unit: int
		draw_size_unit: int
		base_image, draw_size, draw_border, window_size_unit, draw_size_unit = super().__image__()

		for plotname in plot_names:
			result: np.ndarray | None = self.__plot_image__(base_image, draw_size, draw_border, window_size_unit, draw_size_unit, plotname, *args, **kwargs)
			assert result is None or isinstance(result, np.ndarray), f'Invalid plot image result ({type(result)})'
			base_image = base_image if result is None else result

			if base_image.shape[2] == 1:
				base_image = cv2.cvtColor(base_image, cv2.COLOR_GRAY2RGBA)
			elif base_image.shape[2] == 3:
				base_image = cv2.cvtColor(base_image, cv2.COLOR_RGB2RGBA)

		return base_image, draw_size, draw_border, window_size_unit, draw_size_unit

	def __plot_image__(self, base_image: np.ndarray, draw_size: tuple[int, int], draw_border: tuple[float, float], window_size_unit: int, draw_size_unit: int, plotname: str, *args, **kwargs) -> np.ndarray | None:
		"""
		Generates an individual image for the specified plot
		:param base_image: (numpy.ndarray) The base image
		:param plotname: (str) The name of the plot
		:return: (numpy.ndarray | None) Nothing if image is modified in place, otherwise the new image
		"""

		return None

	def new_plot(self, name: str, *, color: tuple[float | int, float | int, float | int] | str | int = 0x000000, overwrite: bool = False, make_active: bool = True, label_points: bool = False, point_size: int = 15, extra: dict = None, **extra_kwargs) -> None:
		"""
		Creates a new plot for storing points
		:param name: (str) The name of the plot
		:param color: (tuple[float | int] or str or int) The color to use for plot points, either an rgb tuple, hex-string, or color integer
		:param overwrite: (bool) If true, overwrites all data instead of only updating data
		:param make_active: (bool) If true, sets this plot as the active plot
		:param label_points: (bool) Whether to label points
		:param point_size: (int) The size (in pixels) of points
		:param extra: Extra (dict) metadata to save
		:param extra_kwargs: (**ANY) Extra metadata to save
		:return: (None)
		:raises AssertionError: If any arguments' type or value are incorrect
		"""

		assert type(name) is str and len(name) > 0, f'{type(self).__name__}::new_plot - \'name\' must be a non-empty string'
		assert type(color) in (tuple, str, int), f'{type(self).__name__}::new_plot - \'color\' must be a color str, int, or RGB tuple'
		assert type(color) in (str, int) or (len(color) == 3 and all(type(x) in (int, float) for x in color)), f'{type(self).__name__}::new_plot - \'color\' must be a color str, int, or RGB tuple'
		assert type(overwrite) is bool, f'{type(self).__name__}::new_plot - \'overwrite\' must be a bool'
		assert type(make_active) is bool, f'{type(self).__name__}::new_plot - \'make_active\' must be a bool'
		assert type(label_points) is bool, f'{type(self).__name__}::new_plot - \'label_points\' must be a bool'
		assert type(point_size) is int and point_size > 0, f'{type(self).__name__}::point_info - \'size\' must be an int greater than 0 or None'
		assert extra is None or type(extra) is dict, f'{type(self).__name__}::point_info - \'extra\' must be a dict or None'

		extra_data: dict = ({} if extra is None else extra) | extra_kwargs
		hex_color: int = 0

		if type(color) is tuple:
			hex_color |= ((color[0] << 16) & 0xFF)
			hex_color |= ((color[1] << 8) & 0xFF)
			hex_color |= (color[2] & 0xFF)
		elif type(color) is str:
			if color[0] == '#':
				hex_color = int(color[1:], 16)
			else:
				hex_color = int(color, 16)
		elif type(color) is int:
			hex_color = color & 0xFFFFFF

		if name not in self.__points__ or overwrite:
			self.__points__[name] = set()
			self.__plot_info__[name] = {'color': hex_color, 'label_points': label_points, 'point_size': point_size, 'extra': extra_data}
		else:
			self.__plot_info__[name]['color'] = hex_color
			self.__plot_info__[name]['label_points'] = label_points
			self.__plot_info__[name]['point_size'] = point_size

			for k, v in extra_data.items():
				if k not in self.__plot_info__[name]['extra'] and v is not None:
					self.__plot_info__[name]['extra'][k] = v
				elif k in self.__plot_info__[name]['extra'] and v is None:
					del self.__plot_info__[name]['extra'][k]

		if make_active:
			self.__current_plot__ = name

	def plot_info(self, *plot_names: str, color: typing.Optional[tuple[float | int, float | int, float | int] | str | int] = ..., label_points: typing.Optional[bool] = ..., point_size: typing.Optional[int] = ..., extra: typing.Optional[dict] = ..., **extra_kwargs) -> None:
		"""
		Sets information for the specified plots
		:param plot_names: (*str) The names of the plots whose information to modify
		:param color: (tuple[float | int]? or str? or int?) The color to use for plot points, either an rgb tuple, hex-string, or color integer
		:param label_points: (bool?) Whether to label points
		:param point_size: (int?) The size (in pixels) of points
		:param extra: Extra (dict?) metadata to save
		:param extra_kwargs: (**ANY) Extra metadata to save
		:return: (None)
		:raises AssertionError: If any arguments' type or value are incorrect
		"""

		assert color is None or color is ... or isinstance(color, (tuple, str, int)), f'{type(self).__name__}::plot_info - \'color\' must be a color str, int, or RGB tuple'
		assert color is None or color is ... or isinstance(color, (str, int)) or (len(color) == 3 and all(type(x) in (int, float) for x in color)), f'{type(self).__name__}::plot_info - \'color\' must be a color str, int, or RGB tuple'
		assert label_points is None or label_points is ... or isinstance(label_points, bool), f'{type(self).__name__}::plot_info - \'label_points\' must be a bool'
		assert point_size is None or point_size is ... or isinstance(point_size, int) and point_size > 0, f'{type(self).__name__}::plot_info - \'size\' must be an int greater than 0 or None'
		assert extra is None or extra is ... or isinstance(extra, dict), f'{type(self).__name__}::point_info - \'extra\' must be a dict or None'

		plot_names: tuple[str, ...] = tuple(self.__plot_info__.keys()) if len(plot_names) == 0 else plot_names
		extra_data: dict = ({} if extra is None or extra is ... else extra) | extra_kwargs

		for plot_name in plot_names:
			assert type(plot_name) is str, f'{type(self).__name__}::plot_info - \'plot_name\' must be a string'
			assert plot_name in self.__plot_info__, f'Plot \'{plot_name}\' is not a plot in this plotter'

			if color is not None and color is not ...:
				hex_color: int = 0

				if isinstance(color, tuple):
					color = tuple(color)
					hex_color |= ((color[0] << 16) & 0xFF)
					hex_color |= ((color[1] << 8) & 0xFF)
					hex_color |= (color[2] & 0xFF)
				elif isinstance(color, str):
					color = str(color)

					if color[0] == '#':
						hex_color = int(color[1:], 16)
					else:
						hex_color = int(color, 16)
				elif isinstance(color, int):
					hex_color = int(color) & 0xFFFFFF

				self.__plot_info__[plot_name]['color'] = hex_color

			if label_points is not None and label_points is not ...:
				self.__plot_info__[plot_name]['label_points'] = bool(label_points)

			if point_size is not None and point_size is not ...:
				self.__plot_info__[plot_name]['point_size'] = int(point_size)

			for k, v in extra_data.items():
				if v is not None and v is not ...:
					self.__plot_info__[plot_name]['extra'][k] = v

	def active_plot(self, name: typing.Optional[str] = ...) -> str | None:
		"""
		Sets or gets the active plot
		:param name: (str?) The name of the plot to set
		:return: (None or str) The name of the active plot if no argument supplied otherwise None
		:raises AssertionError: If any arguments' type or value are incorrect
		"""

		assert name is None or name is ... or isinstance(name, str), f'{type(self).__name__}::active_plot - \'name\' must be a string or None'

		if name is None or name is ...:
			return self.__current_plot__
		elif (name := str(name)) in self.__points__:
			self.__current_plot__ = name
		else:
			raise NameError(f'Plot \'{name}\' is not a plot in this plotter')

	def transformed(self, function: typing.Callable, *, handle_exceptions: tuple[type, ...] = (ValueError,)) -> set[tuple[float, float]]:
		"""
		Returns a list of the internal points passed through a transformer function
		:param function: (CALLABLE) The function to transform the points; should accept 2 floats and return a tuple of 2 floats
		:param handle_exceptions: (tuple[type]) A list of exceptions to catch
		:return: (set[tuple[float]]) The transformed points
		:raises AssertionError: If 'function' is not callable
		:raises ArithmeticError: If transforming a point failed
		"""

		assert callable(function), f'{type(self).__name__}::transform - \'function\' must be a callable accepting two floats and returning a tuple of two floats'

		transformed: set[tuple[float, float]] = set()

		for point in self.__points__[self.__current_plot__]:
			try:
				pair = function(*point)

				if pair is None:
					continue

				x, y = pair
				transformed.add((float(x), float(y)))
			except Exception as e:
				if isinstance(e, handle_exceptions):
					continue

				raise ArithmeticError(f'Point transformation failed at point {point}') from e

		return transformed

	def transform(self, function: typing.Callable, *, handle_exceptions: tuple[type, ...] = (ValueError,)) -> None:
		"""
		Transforms the internal list of points in-place via a transformer function
		:param function: (CALLABLE) The function to transform the points; should accept 2 floats and return a tuple of 2 floats
		:param handle_exceptions: (tuple[type]) A list of exceptions to catch
		:return: (None)
		:raises AssertionError: If 'function' is not callable
		:raises ArithmeticError: If transforming a point failed
		"""

		self.__points__[self.__current_plot__] = self.transformed(function, handle_exceptions=handle_exceptions)

	def add_points(self, *points: tuple[float | int, float | int] | Vector.Vector, plot_name: typing.Optional[str] = ...) -> None:
		"""
		Adds points to the active plot
		:param points: (*tuple[float | int] or *Vector) A variadic list of either 2D tuples or 2D vectors
		:param plot_name: (str?) The plot name to add points to or the active plot if None
		:return: (None)
		:raises AssertionError: If any arguments' type is incorrect
		"""

		assert plot_name is None or plot_name is ... or isinstance(plot_name, str), f'{type(self).__name__}::add_points - \'plot_name\' must be a string or None'
		plot_name = self.__current_plot__ if plot_name is None or plot_name is ... else str(plot_name)

		if plot_name not in self.__points__:
			raise NameError(f'Plot \'{plot_name}\' is not a plot in this plotter')

		for point in points:
			if type(point) is tuple and len(point) == 2 and all(type(x) in (float, int) for x in point):
				self.__points__[plot_name].add(point)
			elif type(point) is Vector.Vector and point.dimension() == 2:
				self.__points__[plot_name].add((point[0], point[1]))
			else:
				raise TypeError(f'{type(self).__name__}::add_points - \'*points\' point must be either a tuple of length 2 or a Math.Vector.Vector of dimension 2')

	def as_csv(self, filepath: typing.Optional[str] = ..., *plot_names: str, **filepaths: str):
		"""
		Saves the internal list of points to a csv file
		:param filepath: (str?) The filepath to save to; Cannot be supplied with '**filepaths'
		:param plot_names (*str) The plots to save
		:param filepaths (**str) If supplied, maps each plot name to a separate file; Cannot be supplied with 'filepath'
		:return: (None)
		:raises AssertionError: If 'filepath' is not a str, one of '*plot_names' is not a str, one of '*plot_names' is not in this plotter
		"""

		assert (filepath is not None and filepath is not ...) or len(filepaths) > 0, f'{type(self).__name__}::as_csv - Missing either \'filepath\' or \'filepaths\''
		assert (filepath is not None and filepath is not ... and len(filepaths) == 0) or ((filepath is None or filepath is ...) and len(filepaths) > 0), f'{type(self).__name__}::as_csv - Cannot supply both \'filepath\' and \'filepaths\''

		if filepath is None or filepath is ...:
			assert len(plot_names) == 0, 'Plot names to be supplied in \'filepaths\''

			for filepath, plot_name in filepaths:
				assert type(plot_name) is str, f'{type(self).__name__}::plot_info - \'plot_name\' must be a string'
				assert plot_name in self.__plot_info__, f'Plot \'{plot_name}\' is not a plot in this plotter'

				file = FileSystem.File(filepath)

				if not file.exists():
					file.create()

				with file.open('w') as f:
					points_str: str = '\n'.join(f'{point[0]},{point[1]}' for point in self.__points__[plot_name])
					f.write(f'{plot_name}::x,{plot_name}::y\n{points_str}\n\n')
		else:
			file = FileSystem.File(filepath)

			if not file.exists():
				file.create()

			with file.open('w') as f:
				for plot_name, points in self.__points__.items():
					points_str: str = '\n'.join(f'{point[0]},{point[1]}' for point in points)
					f.write(f'{plot_name}::x,{plot_name}::y\n{points_str}\n\n')

	def as_image(self, *plot_names: str, show_legend: bool = False) -> np.ndarray:
		"""
		Returns this plot as an image
		:param plot_names (*str) The plots to show
		:param show_legend: (bool) Whether to display the legend
		:return: (numpy.ndarray) The RGB image pixel array
		"""

		base_image: np.ndarray
		base_image, *_ = self.__image__(plot_names if len(plot_names) else tuple(self.__plot_info__.keys()))
		return self.__legend_image__(base_image) if show_legend else base_image

	def save(self, filepath: str, *plot_names: str, show_legend: bool = False) -> None:
		"""
		Saves the plot to an image file
		:param filepath: (str) The filepath to write to
		:param plot_names (*str) The plots to save
		:param show_legend: (bool) Whether to show the legend
		:return: (None)
		:raises AssertionError: If 'show_legend' is not a bool or 'filepath' is not a str
		"""

		file = FileSystem.File(filepath)

		if not file.exists():
			file.create()

		assert type(show_legend) is bool, f'{type(self).__name__}::show - \'show_legend\' must be a bool'

		PIL.Image.fromarray(self.as_image(*plot_names, show_legend=show_legend)).save(file.filepath())

	def get_points(self, order: typing.Optional[str | typing.Callable] = None) -> tuple[tuple[float, float], ...] | set[tuple[float, float]]:
		"""
		Gets the internal list of points from the active plot
		:param order: (str or CALLABLE) If 'x', orders points based on their x values; If 'y', orders points based on their 'y' values; if a callable, sorts based on that function; Otherwise returns unordered points
		:return: (tuple or set) A set if left unordered, otherwise an ordered tuple
		:raises AssertionError: If order is not a valid axis and order it not callable
		"""

		if order is None or order is ...:
			return self.__points__[self.__current_plot__].copy()
		else:
			if order == 'x':
				sorter: typing.Callable = lambda point: point[0]
			elif order == 'y':
				sorter: typing.Callable = lambda point: point[1]
			else:
				sorter: typing.Callable = order

			assert callable(sorter), f'{type(self).__name__}::get_points - \'order\' must be a callable, \'x\', \'y\', or None'

			return tuple(sorted(self.__points__[self.__current_plot__], key=sorter))


class CartesianScatterPlot2D(MultiPlot2D, AxisPlot2D):
	"""
	[CartesianScatterPlot2D(MultiPlot2D, AxisPlot2D)] - Plotter plotting various points in 2D cartesian space
	"""

	__POLY_FIT_METHODS: dict[str, typing.Callable] = {
		'poly': np.polynomial.polynomial.polyfit,
		'polynomial': np.polynomial.polynomial.polyfit,
		'chebyshev': np.polynomial.chebyshev.chebfit,
		'hermite': np.polynomial.hermite.hermfit,
		'hermite_e': np.polynomial.hermite_e.hermefit,
		'laguerre': np.polynomial.laguerre.lagfit,
		'legendre': np.polynomial.legendre.legfit
	}

	def __init__(self):
		"""
		[CartesianScatterPlot2D(MultiPlot2D, AxisPlot2D)] - Plotter plotting various points in 2D cartesian space
		- Constructor -
		"""

		MultiPlot2D.__init__(self)
		AxisPlot2D.__init__(self)
		self.__plot_info__['']['extra']['point_shape'] = 'square'
		self.__plot_info__['']['extra']['line_join_width'] = 1
		self.__plot_info__['']['extra']['line_join_type'] = None
		self.__add_axis__('xy')

	def __plot_image__(self, base_image: np.ndarray, draw_size: tuple[int, int], draw_border: tuple[float, float], window_size_unit: int, draw_size_unit: int, plot_name: str, *args, **kwargs) -> np.ndarray | None:
		border: tuple[float, float] = (draw_border[0] / 2, draw_border[1] / 2)
		min_x, max_x, min_y, max_y, *_ = args
		plot: tuple[tuple[float, float], ...] = tuple(sorted(self.__points__[plot_name], key=lambda p: p[0]))
		plot_info: dict[str, typing.Any] = self.__plot_info__[plot_name]
		smallest: tuple[int, ...] = tuple(i for i, point in enumerate(plot) if point[0] >= min_x)
		largest: tuple[int, ...] = tuple(i for i, point in enumerate(plot) if point[0] <= max_x)
		side_counts: dict[str, int] = {
			'triangle': 3,
			'square': 4,
			'pentagon': 5,
			'hexagon': 6,
			'septagon': 7,
			'octogon': 8,
			'nonogon': 9,
			'decagon': 10
		}
		side_count: int = 0

		if len(smallest) == 0 or len(largest) == 0:
			return

		if (point_shape := plot_info['extra']['point_shape'].lower()) in side_counts:
			side_count = side_counts[point_shape]

		small: int = smallest[0] if smallest[0] == 0 else plot[smallest[0] - 1]
		large: int = largest[-1] if largest[-1] == len(plot) - 1 else plot[largest[-1] + 1]
		color: str = f'#{hex(plot_info["color"])[2:].rjust(6, "0")}'
		points: list[tuple[float, float]] = []
		size: float = plot_info['point_size'] * 1.5

		w, h, d = base_image.shape
		layer: np.ndarray = np.full((w, h, d), 0x00, dtype=np.uint8)
		pilimage: PIL.Image.Image = PIL.Image.fromarray(layer)
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(pilimage)

		for point in (plot[x] for x in range(small, large + 1)):
			xratio: float = (point[0] - min_x) / (max_x - min_x)
			yratio: float = (point[1] - min_y) / (max_y - min_y)
			screenx: int = round(xratio * draw_size[0] + border[0])
			screeny: int = round((1 - yratio) * draw_size[1] + border[1])
			points.append((screenx, screeny))

			if plot_info['label_points']:
				labelx, labely = self.axes_format('xy', point[0], point[1])
				label: str = f'({labelx}, {labely})'
				labelpos: float = screenx + size
				bbox: tuple[int, int, int, int] = drawer.textbbox((0, 0), label, anchor='lm', font_size=size)
				width: int = bbox[2] - bbox[0]
				drawer.multiline_text((labelpos if labelpos + width < draw_size[0] else screenx - size - width, screeny), label, color, font_size=size, anchor='lm')

			if side_count >= 3:
				drawer.regular_polygon((screenx, screeny, plot_info['point_size']), side_count, 0, color)

		drawer.line(points, color, plot_info['extra']['line_join_width'], plot_info['extra']['line_join_type'])
		result: np.ndarray = np.asarray(pilimage)
		return cv2.addWeighted(base_image, 1, result, 1, 0)

	def __image__(self, plot_names: tuple[str, ...] = (), *args, **kwargs) -> tuple[np.ndarray, tuple[int, int], tuple[float, float], int, int]:
		base_image: np.ndarray
		draw_size: tuple[int, int]
		draw_border: tuple[float, float]
		window_size_unit: int
		draw_size_unit: int
		(min_x, max_x), (min_y, max_y) = self.axes_bounds('xy')
		x_bounding, y_bounding = self.axes_bounding('xy')
		x_haslowerbound = x_bounding == AxisPlot2D.AxisBounding.BOUND or x_bounding == AxisPlot2D.AxisBounding.LOWER
		x_hasupperbound = x_bounding == AxisPlot2D.AxisBounding.BOUND or x_bounding == AxisPlot2D.AxisBounding.UPPER
		y_haslowerbound = y_bounding == AxisPlot2D.AxisBounding.BOUND or y_bounding == AxisPlot2D.AxisBounding.LOWER
		y_hasupperbound = y_bounding == AxisPlot2D.AxisBounding.BOUND or y_bounding == AxisPlot2D.AxisBounding.UPPER

		for plot_name in plot_names:
			plot: set[tuple[float, float]] = self.__points__[plot_name]

			if len(plot):
				min_x = min(min_x, min(x[0] for x in plot)) if not x_haslowerbound else min_x
				max_x = max(max_x, max(x[0] for x in plot)) if not x_hasupperbound else max_x
				min_y = min(min_y, min(y[1] for y in plot)) if not y_haslowerbound else min_y
				max_y = max(max_y, max(y[1] for y in plot)) if not y_hasupperbound else max_y

		base_image, draw_size, draw_border, window_size_unit, draw_size_unit = super().__image__(plot_names, min_x, max_x, min_y, max_y)
		border: tuple[float, float] = (draw_border[0] / 2, draw_border[1] / 2)

		xratio: float = (0 - min_x) / (max_x - min_x)
		yratio: float = (0 - min_y) / (max_y - min_y)
		axisx: int = round(xratio * draw_size[0] + border[0])
		axisy: int = round((1 - yratio) * draw_size[1] + border[1])
		x_label: str | None = self.axis_label('x')
		self.__draw_linear_axis__('x', base_image, draw_size, draw_border, (axisx, axisy), label_font_size=24, label_pos=(draw_size[0] - draw_border[0] - (0 if x_label is None else (12 * len(x_label))), axisy + 24))
		self.__draw_linear_axis__('y', base_image, draw_size, draw_border, (axisx, axisy), label_font_size=24, angle=90, label_pos=(axisx - 32, draw_border[1]), label_angle=270)

		return base_image, draw_size, draw_border, window_size_unit, draw_size_unit

	def __legend__(self, plot_names: tuple[str, ...] = ()) -> dict[str, tuple[int, int | float | complex | None]]:
		return {plot_name: (self.__plot_info__[plot_name]['color'], None) for plot_name in (plot_names if len(plot_names) else self.__plot_info__.keys())}

	@staticmethod
	def polyfits(*_) -> tuple[str, ...]:
		"""
		Returns the various fit function names used in ScatterPlot2D.polynomial_regression
		:param _: NOT USED
		:return: (tuple[str]) The names of the fit functions
		"""

		return tuple(CartesianScatterPlot2D.__POLY_FIT_METHODS.keys())

	def new_plot(self, name: str, *, color: tuple[float | int, float | int, float | int] | str | int = 0x000000, overwrite: bool = False, make_active: bool = True, label_points: bool = False, point_size: int = 15, point_shape: str = 'square', line_join_type: str = None, line_join_width: int = 1, extra: dict = None, **extra_kwargs) -> None:
		"""
		Creates a new plot for storing points
		:param name: (str) The name of the plot
		:param color: (tuple[float | int] or str or int) The color to use for plot points, either an rgb tuple, hex-string, or color integer
		:param overwrite: (bool) If true, overwrites all data instead of only updating data
		:param make_active: (bool) If true, sets this plot as the active plot
		:param label_points: (bool) Whether to label points
		:param point_size: (int) The size (in pixels) of points
		:param point_shape: (str) The shape of the point when plotting
		:param line_join_type: (str) How to join points (either 'curve' or 'straight')
		:param line_join_width: (int) Width of the line between points
		:param extra: Extra (dict) metadata to save
		:param extra_kwargs: (**ANY) Extra metadata to save
		:return: (None)
		:raises AssertionError: If any arguments' type or value are incorrect
		"""

		assert line_join_type in (None, 'curve', 'straight'), f'{type(self).__name__}::new_plot - \'line_join_type\' must be either None, \'curve\', or \'straight\''
		assert type(line_join_width) is int and line_join_width >= 0, f'{type(self).__name__}::new_plot - \'line_join_width\' must be an integer greater than or equal to 0'
		assert type(point_shape) is str and len(point_shape) > 0, f'{type(self).__name__}::new_plot - \'point_shape\' must be a non-empty string'
		super().new_plot(name, color=color, overwrite=overwrite, make_active=make_active, label_points=label_points, point_size=point_size, extra=extra, point_shape=point_shape, line_join_type=line_join_type, line_join_width=line_join_width, **extra_kwargs)

	def plot_info(self, *plot_names: str, color: typing.Optional[tuple[float | int, float | int, float | int] | str | int] = ..., label_points: typing.Optional[bool] = ..., point_shape: typing.Optional[str] = ..., point_size: typing.Optional[int] = ..., line_join_type: typing.Optional[str] = ..., line_join_width: typing.Optional[int] = ..., extra: typing.Optional[dict] = None, **extra_kwargs) -> None:
		"""
		Sets information for the specified plots
		:param plot_names: (*str) The names of the plots whose information to modify
		:param color: (tuple[float | int]? or str? or int?) The color to use for plot points, either an rgb tuple, hex-string, or color integer
		:param label_points: (bool?) Whether to label points
		:param point_size: (int?) The size (in pixels) of points
		:param point_shape: (str?) The shape of the point when plotting
		:param line_join_type: (str?) How to join points (either 'curve' or 'straight')
		:param line_join_width: (int?) Width of the line between points
		:param extra: Extra (dict) metadata to save
		:param extra_kwargs: (**ANY) Extra metadata to save
		:return: (None)
		:raises AssertionError: If any arguments' type or value are incorrect
		"""

		assert line_join_type in (None, ..., 'curve', 'straight'), f'{type(self).__name__}::new_plot - \'line_join_type\' must be either None, \'curve\', or \'straight\''
		assert line_join_width is None or line_join_width is ... or type(line_join_width) is int and line_join_width >= 0, f'{type(self).__name__}::new_plot - \'line_join_width\' must be an integer greater than or equal to 0'
		assert point_shape is None or point_shape is ... or type(point_shape) is str and len(point_shape) > 0, f'{type(self).__name__}::new_plot - \'point_shape\' must be a non-empty string'
		super().plot_info(*plot_names, color=color, label_points=label_points, point_size=point_size, extra=extra, point_shape=point_shape, line_join_type=line_join_type, line_join_width=line_join_width, **extra_kwargs)

	def graph(self, function: typing.Callable, *args, step: typing.Optional[float] = None, **kwargs) -> None:
		"""
		Plots points to the active plot using a graphing function
		Graph bounds must be set with 'ScatterPlot2D.plot_info'
		:param function: (CALLABLE) The graphing function; A function accepting a float for its first argument
		:param args: (*ANY) Extra arguments to the graphing function
		:param step: (float) The step used between x values
		:param kwargs: (**ANY) Extra keyword arguments to the graphing function
		:return: (None)
		:raises AssertionError: If any arguments' type or value are incorrect, the function is not callable, or minimum and maximum axis values have not been set
		"""

		assert callable(function), f'{type(self).__name__}::graph - \'function\' must be a callable accepting one float and returning one float'
		assert step is None or step is ... or type(step) in (float, int) and step > 0, f'{type(self).__name__}::graph - \'step\' must be a float or int greater than 0'
		assert self.axes_bounded('x'), 'X-Axis minimum and maximum values must be set'
		assert self.axes_bounded('y'), 'Y-Axis minimum and maximum values must be set'

		min_, max_ = self.axis_bounds('x')
		x: float = min_
		step = (max_ - min_) / 1e3 if step is None else step

		while x <= max_:
			try:
				y = float(function(x, *args, **kwargs))
				self.__points__[self.__current_plot__].add((x, y))
			except Exception:
				pass

			x += step

	def graph_normal(self, mean: float, standard_deviation: float) -> None:
		pass

	def linear_regression(self) -> tuple[str | None, float | None, typing.Callable]:
		"""
		Calculates the best fit linear regression for the active plot's points
		:return: (tuple[str, float, CALLABLE]) Either a tuple of None if the graph is empty or a tuple -> (equation: str, r_squared: float, graph_function: CALLABLE)
		"""

		points: set[tuple[float, float]] = self.__points__[self.__current_plot__]

		if len(points) == 0:
			return None, None, lambda x: None

		_x: float = sum(point[0] for point in points) / len(points)
		_y: float = sum(point[1] for point in points) / len(points)
		_a: float = sum((point[1] - _y) * (point[0] - _x) for point in points) / sum((point[0] - _x) ** 2 for point in points)
		_b: float = _y - _a * _x
		r2: float = 1 - sum((point[1] - (_a * point[0] + _b)) ** 2 for point in points) / sum((point[1] - _y) ** 2 for point in points)
		return f'y={_a}x+{_b}; r²={r2}', r2, lambda x, m=_a, b=_b: m * x + b

	def exponential_regression(self) -> tuple[str | None, float | None, typing.Callable]:
		"""
		Calculates the best fit exponential regression for the active plot's points
		:return: (tuple[str, float, CALLABLE]) Either a tuple of None if the graph is empty or a tuple -> (equation: str, r_squared: float, graph_function: CALLABLE)
		"""

		points: set[tuple[float, float]] = {(x, math.log(y, math.e)) for x, y in self.__points__[self.__current_plot__] if y > 0}

		if len(points) == 0:
			return None, None, lambda x: None

		_x: float = sum(point[0] for point in points) / len(points)
		_y: float = sum(point[1] for point in points) / len(points)
		_a: float = sum((point[1] - _y) * (point[0] - _x) for point in points) / sum((point[0] - _x) ** 2 for point in points)
		_b: float = _y - _a * _x
		r2: float = 1 - sum((point[1] - (_a * point[0] + _b)) ** 2 for point in points) / sum(point[1] - _y for point in points)
		return f'y=e^({_a}x+{_b}); r²={r2}', r2, lambda x: pow(math.e, _a * x + _b)

	def polynomial_regression(self, degree: int = None, max_degree: int = None, fit_method='poly'):
		"""
		Calculates the best fit polynomial regression for the active plot's points
		Calculates an equation of degree 'degree' if 'max_degree' is None otherwise returns the best fit from equations between 'degree' and 'max_degree'
		:param degree: (int) The degree (or minimum degree if 'max_degree' is not None) to test
		:param max_degree: (int) The maximum degree to test
		:param fit_method: (str) The method used to fit the data, one of the values returned from 'ScatterPlot2D::polyfits'
		:return: (tuple[str, float, CALLABLE]) Either a tuple of None if the graph is empty or a tuple -> (equation: str, r_squared: float, graph_function: CALLABLE)
		:raises AssertionError: If any arguments' type or value are incorrect, 'fit_method' is invalid, 'max_degree' is less than 'degree'
		"""

		assert degree is None or type(degree) is int and degree > 0, f'{type(self).__name__}::polynomial_regression - \'degree\' must be an int greater than 0'
		assert max_degree is None or type(max_degree) is int and max_degree > 0, f'{type(self).__name__}::polynomial_regression - \'max_degree\' must be an int greater than 0'
		assert fit_method is None or fit_method.lower() in CartesianScatterPlot2D.__POLY_FIT_METHODS, f'{type(self).__name__}::polynomial_regression - \'fit_method\' must be one of {tuple(CartesianScatterPlot2D.__POLY_FIT_METHODS.keys())}'

		stop_at_rank: bool = degree is None and max_degree is None
		max_degree = max_degree if max_degree is not None else 32 if degree is None else degree
		degree = 1 if degree is None else degree - 1
		points: set[tuple[float, float]] = self.__points__[self.__current_plot__]
		factors: tuple[float, ...] = ()
		r2: float = 0
		degree_error: int = 0
		fit_methods: tuple[str, ...] = self.polyfits() if fit_method is None else (fit_method,)

		if len(points) == 0:
			return None, None, lambda x: None

		assert max_degree >= degree, f'{type(self).__name__}::polynomial_regression - \'max_degree\' must be equal to or greater than \'degree\''

		for n in range(degree, max_degree):
			for fit in fit_methods:
				x = np.array([point[0] for point in points])
				y = np.array([point[1] for point in points])

				if degree_error == 0:
					with warnings.catch_warnings():
						warnings.simplefilter('error', np.polynomial.polyutils.RankWarning)

						try:
							factors_local = tuple(CartesianScatterPlot2D.__POLY_FIT_METHODS[fit.lower()](x, y, n + 1))
						except np.polynomial.polyutils.RankWarning:
							if stop_at_rank:
								break
							else:
								with warnings.catch_warnings():
									warnings.simplefilter('ignore', np.polynomial.polyutils.RankWarning)
									factors_local = tuple(CartesianScatterPlot2D.__POLY_FIT_METHODS[fit.lower()](x, y, n + 1))

								degree_error = n + 1
				else:
					with warnings.catch_warnings():
						warnings.simplefilter('ignore', np.polynomial.polyutils.RankWarning)
						factors_local = tuple(CartesianScatterPlot2D.__POLY_FIT_METHODS[fit.lower()](x, y, n + 1))

				_y: float = sum(point[1] for point in points) / len(points)
				r2_local: float = 1 - sum((point[1] - sum((m * point[0] ** (len(factors_local) - b - 1)) for b, m in enumerate(factors_local))) ** 2 for point in points) / sum((point[1] - _y) ** 2 for point in points)

				if abs(r2_local - 1) < abs(r2 - 1) or len(factors) == 0:
					r2 = r2_local
					factors = factors_local

		if degree_error > 0:
			sys.stderr.write(f'[RankWarning]: numpy marked potential fit error from high polynomial degree (started at degree {degree_error})\n')
			sys.stderr.flush()

		equation: str = ''.join(f'{"+" if m >= 0 and b > 0 else ""}{m}x^{(len(factors) - b - 1)}' for b, m in enumerate(factors))
		return (f'y={equation}; r²={r2}', r2, lambda x, f=factors: sum(m * x ** (len(f) - b - 1) for b, m in enumerate(f))) if len(factors) > 0 else (None, None, lambda x: None)

	def sinusoidal_regression(self) -> tuple[str | None, float | None, typing.Callable]:
		"""
		Calculates the best fit sinusoidal regression for the active plot's points
		:return: (tuple[str, float, CALLABLE]) Either a tuple of None if the graph is empty or a tuple -> (equation: str, r_squared: float, graph_function: CALLABLE)
		"""

		points: set[tuple[float, float]] = self.__points__[self.__current_plot__]

		if len(points) == 0:
			return None, None, lambda x: None

		sorted_points: tuple[tuple[float, float]] = tuple(sorted(points, key=lambda p: p[0]))
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


class PolarScatterPlot2D(MultiPlot2D, AxisPlot2D):
	"""
	[PolarScatterPlot2D(MultiPlot2D, AxisPlot2D)] - Plotter plotting various points in 2D polar space
	"""

	def __init__(self):
		"""
		[PolarScatterPlot2D(MultiPlot2D, AxisPlot2D)] - Plotter plotting various points in 2D polar space
		- Constructor -
		"""

		MultiPlot2D.__init__(self)
		AxisPlot2D.__init__(self)
		self.__plot_info__['']['extra']['point_shape'] = 'square'
		self.__plot_info__['']['extra']['line_join_width'] = 1
		self.__plot_info__['']['extra']['line_join_type'] = None
		self.__add_axis__('xyt')

	def __plot_image__(self, base_image: np.ndarray, draw_size: tuple[int, int], draw_border: tuple[float, float], window_size_unit: int, draw_size_unit: int, plot_name: str, *args, **kwargs) -> np.ndarray | None:
		border: tuple[float, float] = (draw_border[0] / 2, draw_border[1] / 2)
		min_x, max_x, min_y, max_y, *_ = args
		plot: tuple[tuple[float, float], ...] = tuple(sorted(self.__points__[plot_name], key=lambda p: p[0]))
		plot_info: dict[str, typing.Any] = self.__plot_info__[plot_name]
		side_counts: dict[str, int] = {
			'triangle': 3,
			'square': 4,
			'pentagon': 5,
			'hexagon': 6,
			'septagon': 7,
			'octogon': 8,
			'nonogon': 9,
			'decagon': 10
		}
		side_count: int = 0

		if (point_shape := plot_info['extra']['point_shape'].lower()) in side_counts:
			side_count = side_counts[point_shape]

		color: str = f'#{hex(plot_info["color"])[2:].rjust(6, "0")}'
		points: list[tuple[float, float]] = []
		size: float = plot_info['point_size'] * 1.5

		w, h, d = base_image.shape
		layer: np.ndarray = np.full((w, h, d), 0x00, dtype=np.uint8)
		pilimage: PIL.Image.Image = PIL.Image.fromarray(layer)
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(pilimage)

		for point in plot:
			polar_point: tuple[float, float] = point[1] * math.cos(point[0]), point[1] * math.sin(point[0])
			xratio: float = (polar_point[0] - min_x) / (max_x - min_x)
			yratio: float = (polar_point[1] - min_y) / (max_y - min_y)
			screenx: int = round(xratio * draw_size[0] + border[0])
			screeny: int = round((1 - yratio) * draw_size[1] + border[1])
			points.append((screenx, screeny))

			if plot_info['label_points']:
				labelx, labely = self.axes_format('xy', point[0], point[1])
				label: str = f'({labelx}, {labely})'
				labelpos: float = screenx + size
				bbox: tuple[int, int, int, int] = drawer.textbbox((0, 0), label, anchor='lm', font_size=size)
				width: int = bbox[2] - bbox[0]
				drawer.multiline_text((labelpos if labelpos + width < draw_size[0] else screenx - size - width, screeny), label, color, font_size=size, anchor='lm')

			if side_count >= 3:
				drawer.regular_polygon((screenx, screeny, plot_info['point_size']), side_count, 0, color)

		drawer.line(points, color, plot_info['extra']['line_join_width'], plot_info['extra']['line_join_type'])
		result: np.ndarray = np.asarray(pilimage)
		return cv2.addWeighted(base_image, 1, result, 1, 0)

	def __image__(self, plot_names: tuple[str, ...] = (), *args, **kwargs) -> tuple[np.ndarray, tuple[int, int], tuple[float, float], int, int]:
		base_image: np.ndarray
		draw_size: tuple[int, int]
		draw_border: tuple[float, float]
		window_size_unit: int
		draw_size_unit: int
		(min_x, max_x), (min_y, max_y) = self.axes_bounds('xy')
		x_bounding, y_bounding = self.axes_bounding('xy')
		x_haslowerbound = x_bounding == AxisPlot2D.AxisBounding.BOUND or x_bounding == AxisPlot2D.AxisBounding.LOWER
		x_hasupperbound = x_bounding == AxisPlot2D.AxisBounding.BOUND or x_bounding == AxisPlot2D.AxisBounding.UPPER
		y_haslowerbound = y_bounding == AxisPlot2D.AxisBounding.BOUND or y_bounding == AxisPlot2D.AxisBounding.LOWER
		y_hasupperbound = y_bounding == AxisPlot2D.AxisBounding.BOUND or y_bounding == AxisPlot2D.AxisBounding.UPPER

		for plot_name in plot_names:
			plot: set[tuple[float, float]] = self.__points__[plot_name]

			if len(plot):
				min_x = min(min_x, min(x[0] for x in plot)) if not x_haslowerbound else min_x
				max_x = max(max_x, max(x[0] for x in plot)) if not x_hasupperbound else max_x
				min_y = min(min_y, min(y[1] for y in plot)) if not y_haslowerbound else min_y
				max_y = max(max_y, max(y[1] for y in plot)) if not y_hasupperbound else max_y

		base_image, draw_size, draw_border, window_size_unit, draw_size_unit = super().__image__(plot_names, min_x, max_x, min_y, max_y)
		border: tuple[float, float] = (draw_border[0] / 2, draw_border[1] / 2)

		xratio: float = (0 - min_x) / (max_x - min_x)
		yratio: float = (0 - min_y) / (max_y - min_y)
		axisx: int = round(xratio * draw_size[0] + border[0])
		axisy: int = round((1 - yratio) * draw_size[1] + border[1])
		x_label: str | None = self.axis_label('x')
		self.__draw_linear_axis__('x', base_image, draw_size, draw_border, (axisx, axisy), label_font_size=24, label_pos=(draw_size[0] - draw_border[0] - (0 if x_label is None else (12 * len(x_label))), axisy + 24))
		self.__draw_linear_axis__('y', base_image, draw_size, draw_border, (axisx, axisy), label_font_size=24, angle=90, label_pos=(axisx - 32, draw_border[1]), label_angle=270)
		self.__draw_polar_axis__('t', base_image, draw_size, draw_border, (axisx, axisy), label_font_size=24, label_pos=(draw_border[0], axisy - 92))

		return base_image, draw_size, draw_border, window_size_unit, draw_size_unit

	def __legend__(self, plot_names: tuple[str, ...] = ()) -> dict[str, tuple[int, int | float | complex | None]]:
		return {plot_name: (self.__plot_info__[plot_name]['color'], None) for plot_name in (plot_names if len(plot_names) else self.__plot_info__.keys())}

	def new_plot(self, name: str, *, color: tuple[float | int, float | int, float | int] | str | int = 0x000000, overwrite: bool = False, make_active: bool = True, label_points: bool = False, point_size: int = 15, point_shape: str = 'square', line_join_type: str = None, line_join_width: int = 1, extra: dict = None, **extra_kwargs) -> None:
		"""
		Creates a new plot for storing points
		:param name: (str) The name of the plot
		:param color: (tuple[float | int] or str or int) The color to use for plot points, either an rgb tuple, hex-string, or color integer
		:param overwrite: (bool) If true, overwrites all data instead of only updating data
		:param make_active: (bool) If true, sets this plot as the active plot
		:param label_points: (bool) Whether to label points
		:param point_size: (int) The size (in pixels) of points
		:param point_shape: (str) The shape of the point when plotting
		:param line_join_type: (str) How to join points (either 'curve' or 'straight')
		:param line_join_width: (int) Width of the line between points
		:param extra: Extra (dict) metadata to save
		:param extra_kwargs: (**ANY) Extra metadata to save
		:return: (None)
		:raises AssertionError: If any arguments' type or value are incorrect
		"""

		assert line_join_type in (None, 'curve', 'straight'), f'{type(self).__name__}::new_plot - \'line_join_type\' must be either None, \'curve\', or \'straight\''
		assert type(line_join_width) is int and line_join_width >= 0, f'{type(self).__name__}::new_plot - \'line_join_width\' must be an integer greater than or equal to 0'
		assert type(point_shape) is str and len(point_shape) > 0, f'{type(self).__name__}::new_plot - \'point_shape\' must be a non-empty string'
		super().new_plot(name, color=color, overwrite=overwrite, make_active=make_active, label_points=label_points, point_size=point_size, extra=extra, point_shape=point_shape, line_join_type=line_join_type, line_join_width=line_join_width, **extra_kwargs)

	def plot_info(self, *plot_names: str, color: typing.Optional[tuple[float | int, float | int, float | int] | str | int] = ..., label_points: typing.Optional[bool] = ..., point_shape: typing.Optional[str] = ..., point_size: typing.Optional[int] = ..., line_join_type: typing.Optional[str] = ..., line_join_width: typing.Optional[int] = ..., extra: typing.Optional[dict] = None, **extra_kwargs) -> None:
		"""
		Sets information for the specified plots
		:param plot_names: (*str) The names of the plots whose information to modify
		:param color: (tuple[float | int]? or str? or int?) The color to use for plot points, either an rgb tuple, hex-string, or color integer
		:param label_points: (bool?) Whether to label points
		:param point_size: (int?) The size (in pixels) of points
		:param point_shape: (str?) The shape of the point when plotting
		:param line_join_type: (str?) How to join points (either 'curve' or 'straight')
		:param line_join_width: (int?) Width of the line between points
		:param extra: Extra (dict) metadata to save
		:param extra_kwargs: (**ANY) Extra metadata to save
		:return: (None)
		:raises AssertionError: If any arguments' type or value are incorrect
		"""

		assert line_join_type in (None, ..., 'curve', 'straight'), f'{type(self).__name__}::new_plot - \'line_join_type\' must be either None, \'curve\', or \'straight\''
		assert line_join_width is None or line_join_width is ... or type(line_join_width) is int and line_join_width >= 0, f'{type(self).__name__}::new_plot - \'line_join_width\' must be an integer greater than or equal to 0'
		assert point_shape is None or point_shape is ... or type(point_shape) is str and len(point_shape) > 0, f'{type(self).__name__}::new_plot - \'point_shape\' must be a non-empty string'
		super().plot_info(*plot_names, color=color, label_points=label_points, point_size=point_size, extra=extra, point_shape=point_shape, line_join_type=line_join_type, line_join_width=line_join_width, **extra_kwargs)

	def graph(self, function: typing.Callable, *args, step: typing.Optional[float] = None, bounds: tuple[float, float] = (0, 360), **kwargs) -> None:
		"""
		Plots points to the active plot using a graphing function
		:param function: (CALLABLE) The graphing function; A function accepting a float for its first argument
		:param args: (*ANY) Extra arguments to the graphing function
		:param step: (float) The step used between theta values in degrees
		:param bounds: (tuple[float, float]) The angular bounds of the graph in degrees
		:param kwargs: (**ANY) Extra keyword arguments to the graphing function
		:return: (None)
		:raises AssertionError: If any arguments' type or value are incorrect, the function is not callable, or minimum and maximum axis values have not been set
		"""

		assert callable(function), f'{type(self).__name__}::graph - \'function\' must be a callable accepting one float and returning one float'
		assert step is None or step is ... or type(step) in (float, int) and step > 0, f'{type(self).__name__}::graph - \'step\' must be a float or int greater than 0'
		assert isinstance(bounds, (tuple, list)) and len(bounds := tuple(bounds)) == 2 and all(isinstance(x, (int, float)) for x in bounds), f'{type(self).__name__}::graph - \'bounds\' must be a tuple or list of two floats'

		min_, max_ = tuple(float(x) * (math.pi / 180) for x in bounds)
		theta: float = min_
		step = ((max_ - min_) / 1e3) if step is None or step is ... else (step * (math.pi / 180))

		while theta <= max_:
			try:
				radius = float(function(theta, *args, **kwargs))
				self.__points__[self.__current_plot__].add((theta, radius))
			except Exception:
				pass

			theta += step


class PiePlot2D(Plot2D):
	"""
	[PiePlot2D(Plot2D)] - Plotter plotting relational values in 2D space
	"""

	def __init__(self):
		"""
		[PiePlot2D(Plot2D)] - Plotter plotting relational values in 2D space
		- Constructor -
		"""

		super().__init__()
		self.__points__: dict[typing.Any, float] = {}
		self.__point_colors__: dict[typing.Any, int] = {}
		self.__total__: float | None = None

	def __legend__(self) -> dict[str, tuple[int, int | float | complex | None]]:
		return {point_name: (self.__point_colors__[point_name], point_value) for point_name, point_value in self.__points__.items()}

	def __image__(self) -> tuple[np.ndarray, tuple[int, int], tuple[float, float], int, int]:
		base_image: np.ndarray
		draw_size: tuple[int, int]
		draw_border: tuple[float, float]
		window_size_unit: int
		draw_size_unit: int
		base_image, draw_size, draw_border, window_size_unit, draw_size_unit = super().__image__()
		border: tuple[float, float] = (draw_border[0] / 2, draw_border[1] / 2)
		image = PIL.Image.fromarray(base_image)
		drawer = PIL.ImageDraw.Draw(image)
		bounds: tuple[int, int, int, int] = (round(border[0]), round(border[1]), round(border[0] + draw_size[0]), round(border[1] + draw_size[1]))
		start: float = 0

		for key, val in self.get_rel_portions().items():
			color: int = self.__point_colors__[key]
			deg: float = 360 * val
			r = (color >> 16) & 0xFF
			g = (color >> 8) & 0xFF
			b = color & 0xFF
			drawer.pieslice(bounds, start, start + deg, fill=(r, g, b))
			start += deg

		start = 0

		for key, val in self.get_rel_portions().items():
			deg: float = 360 * val
			drawer.pieslice(bounds, start, start + deg, outline=(255, 255, 255), width=2)
			start += deg

		base_image = np.array(image)
		return base_image, draw_size, draw_border, window_size_unit, draw_size_unit

	def total(self, new_total: float | int = None, squash: bool = False) -> float | None:
		"""
		Gets or sets the total value of the plot
		The natural total is the sum of all stored points
		:param new_total: (float or int) The new total. If less than or equal to zero, or not a float or int, total becomes the natural total
		:param squash: (bool) If true, updates the internal points to expand to meet the new total
		:return: (float or None) 'float' if getting the current total, None if setting
		"""

		if new_total is None:
			return sum(self.__points__.values()) if self.__total__ is None else self.__total__
		elif self.__total__ is None and new_total < (natural_total := self.total()):
			if not squash:
				raise ValueError(f'New total less than natural total: {natural_total}')

			for key, val in self.__points__.items():
				ratio = val / natural_total
				self.__points__[key] = new_total * ratio
		elif squash:
			natural_total: float = self.total()

			for key, val in self.__points__.items():
				ratio = val / natural_total
				self.__points__[key] = new_total * ratio
		else:
			self.__total__ = None if type(new_total) not in (float, int) or new_total <= 0 else new_total

	def add_points(self, *points: tuple[typing.Any, float | int] | tuple[typing.Any, float | int, int | str | tuple[int, int, int]] | Vector.Vector, **bound_points: float | int | tuple[float | int, int | str | tuple[int, int, int]]) -> None:
		"""
		Adds points to the plot
		For 3D tuples and 3D vectors, the 3rd value must be either an rgb color tuple, hex-string, or color-int
		For all tuples and vectors, the first value will be used as the key
		:param points: (*tuple[float | int] or *Vector) A variadic list of either 2D tuples, 3D tuples, 2D vectors, or 3D vectors
		:return: (None)
		:raises AssertionError: If any arguments' type is incorrect
		:raises TypeError: If a point is invalid
		"""

		for point in points:
			if type(point) is tuple and 2 <= len(point) <= 3 and type(point[1]) in (float, int):
				color: str | int | tuple[int, int, int] = point[2] if len(point) == 3 else 0xFFFFFF

				if type(color) is str:
					color = color[1:] if color[0] == '#' else color
					color = ((int(color[0:2], 16) & 0xFF) << 16) | ((int(color[2:4], 16) & 0xFF) << 8) | (int(color[4:6], 16) & 0xFF)
				elif type(color) is tuple and len(color) == 3:
					color = ((color[0] & 0xFF) << 16) | ((color[1] & 0xFF) << 8) | (color[2] & 0xFF)
				elif type(color) is not int:
					raise ValueError(f'Unexpected color value: \'{color}\'')

				assert point[1] > 0, 'Pie value cannot be less than or equal to 0'
				self.__points__[point[0]] = point[1]
				self.__point_colors__[point[0]] = color & 0xFFFFFF
			elif type(point) is Vector.Vector and 2 <= point.dimension() <= 3:
				assert point[1] > 0, 'Pie value cannot be less than or equal to 0'
				self.__points__[point[0]] = point[1]
				self.__point_colors__[point[0]] = (point[2] & 0xFFFFFF) if point.dimension() == 3 else 0xFFFFFF
			else:
				raise TypeError(f'{type(self).__name__}::add_points - \'*points\' point must be either a tuple of length 2 or a Math.Vector.Vector of dimension 2')

		for key, value in bound_points.items():
			key = key.replace('_', ' ')

			if type(value) in (int, float):
				assert value > 0, 'Pie value cannot be less than or equal to 0'
				self.__points__[key] = value
				self.__point_colors__[key] = 0xFFFFFF
			elif type(value) is tuple and type(value[0]) in (int, float):
				color: str | int | tuple[int, int, int] = value[1] if len(value) == 2 else 0xFFFFFF

				if type(color) is str:
					color = color[1:] if color[0] == '#' else color
					color = ((int(color[0:2], 16) & 0xFF) << 16) | ((int(color[2:4], 16) & 0xFF) << 8) | (int(color[4:6], 16) & 0xFF)
				elif type(color) is tuple and len(color) == 3:
					color = ((color[0] & 0xFF) << 16) | ((color[1] & 0xFF) << 8) | (color[2] & 0xFF)
				elif type(color) is not int:
					raise ValueError(f'Unexpected color value: \'{color}\'')

				assert value[0] > 0, 'Pie value cannot be less than or equal to 0'
				self.__points__[key] = value[0]
				self.__point_colors__[key] = color & 0xFFFFFF
			else:
				raise TypeError(f'{type(self).__name__}::add_points - \'**bound_points\' point must be a float, int, or tuple containing a float or int and a color')

	def get_points(self, order: str | typing.Callable = None) -> tuple[tuple[typing.Any, float], ...] | set[tuple[typing.Any, float]]:
		"""
		Gets the internal list of points
		:param order: (str or CALLABLE) If 'x', orders points based on their x values; If 'y', orders points based on their 'y' values; if a callable, sorts based on that function; Otherwise returns unordered points
		:return: (tuple or set) A set if left unordered, otherwise an ordered tuple
		:raises AssertionError: If order is not a valid axis and order it not callable
		"""

		if order is None:
			return {(k, v) for k, v in self.__points__.items()}
		else:
			if order == 'x':
				sorter: typing.Callable = lambda point: point[0]
			elif order == 'y':
				sorter: typing.Callable = lambda point: point[1]
			else:
				sorter: typing.Callable = order

			assert callable(sorter), f'{type(self).__name__}::get_points - \'order\' must be a callable, \'x\', \'y\', or None'

			return tuple(sorted(((k, v) for k, v in self.__points__.items()), key=sorter))

	def get_portions(self) -> dict[typing.Any, float]:
		"""
		Gets the internal list of points
		:return: (dict[ANY, float]) A dict mapping each point to its value
		"""

		return self.__points__.copy()

	def get_rel_portions(self) -> dict[typing.Any, float]:
		"""
		Gets the internal list of points normalized to the total of this graph
		:return: (dict[ANY, float]) A dict mapping each point to its value divided by the total
		"""

		total: float = self.total()
		return {k: v / total for k, v in self.__points__.items()}


class BarPlot2D(Plot2D, AxisPlot2D):
	"""
	[BarPlot2D(Plot2D, AxisPlot2D)] - Bar Graph Plotter plotting values in 2D space
	"""

	def __init__(self):
		"""
		[BarPlot2D(Plot2D, AxisPlot2D)] - Bar Graph Plotter plotting values in 2D space
		- Constructor -
		"""

		Plot2D.__init__(self)
		AxisPlot2D.__init__(self)
		self.__points__: dict[typing.Any, float] = {}
		self.__point_colors__: dict[typing.Any, int] = {}
		self.__add_axis__('xy', min_=0, max_=10, minor_spacing=1)

	def __legend__(self) -> dict[str, tuple[int, int | float | complex | None]]:
		return {point_name: (self.__point_colors__[point_name], point_value) for point_name, point_value in self.__points__.items()}

	def __image__(self) -> tuple[np.ndarray, tuple[int, int], tuple[float, float], int, int]:
		base_image: np.ndarray
		draw_size: tuple[int, int]
		draw_border: tuple[float, float]
		window_size_unit: int
		draw_size_unit: int
		base_image, draw_size, draw_border, window_size_unit, draw_size_unit = super().__image__()
		border: tuple[float, float] = (draw_border[0] / 2, draw_border[1] / 2)
		bounds: tuple[int, int, int, int] = (round(border[0]), round(border[1]), round(border[0] + draw_size[0]), round(border[1] + draw_size[1]))
		max_x: int = len(self.__points__)
		max_y: float | None = max(point[1] for point in self.__points__.items()) + 1 if max_x else None
		min_y: float | None = min(point[1] for point in self.__points__.items()) - 1 if max_x else None

		if max_x > 0 and max_y is not None and min_y is not None:
			self.axis_info('x', min_=0, max_=max_x, minor_spacing=1, major_spacing=1)
			self.axis_info('y', min_=min_y, max_=max_y, minor_spacing=1, major_spacing=1)

		spacing: int = (round(draw_size[0] / 2 / max_x)) if (max_x % 2 == 0) else 0
		image = PIL.Image.fromarray(base_image)
		drawer = PIL.ImageDraw.Draw(image)
		general_width_pc: float = 0.9
		rect_width: int = round(draw_size[0] / max_x)
		rect_outer_width: float = rect_width * (1 - general_width_pc)
		rect_inner_width: float = rect_width * general_width_pc
		y2: int = draw_size[1] - round(draw_size[1] * ((-min_y) / (max_y - min_y)))

		for index, (point_name, point_value) in enumerate(self.__points__.items()):
			x1: int = round((rect_width * index) + rect_outer_width)
			x2: int = round(x1 + rect_inner_width)
			y1: int = y2 - round(draw_size[1] / (max_y - min_y) * point_value)
			sy: int = y1 if y1 <= y2 else y2
			ly: int = y1 if y1 > y2 else y2
			drawer.rectangle((x1, sy, x2, ly), fill=f'#{hex(self.__point_colors__[point_name])[2:].zfill(6)}', outline='#eeeeee', width=2)

		base_image = np.array(image)
		self.__draw_linear_axis__('x', base_image, draw_size, draw_border, (draw_size[0] // 2 - spacing, y2))
		self.__draw_linear_axis__('y', base_image, draw_size, draw_border, (0, y2), angle=90)
		return base_image, draw_size, draw_border, window_size_unit, draw_size_unit

	def add_points(self, *points: tuple[typing.Any, float | int] | tuple[typing.Any, float | int, int | str | tuple[int, int, int]] | Vector.Vector, **bound_points: float | int | tuple[float | int, int | str | tuple[int, int, int]]) -> None:
		"""
		Adds points to the plot
		For 3D tuples and 3D vectors, the 3rd value must be either an rgb color tuple, hex-string, or color-int
		For all tuples and vectors, the first value will be used as the key
		:param points: (*tuple[float | int] or *Vector) A variadic list of either 2D tuples, 3D tuples, 2D vectors, or 3D vectors
		:return: (None)
		:raises AssertionError: If any arguments' type is incorrect
		:raises TypeError: If a point is invalid
		"""

		for point in points:
			if type(point) is tuple and 2 <= len(point) <= 3 and type(point[1]) in (float, int):
				color: str | int | tuple[int, int, int] = point[2] if len(point) == 3 else 0xFFFFFF

				if type(color) is str:
					color = color[1:] if color[0] == '#' else color
					color = ((int(color[0:2], 16) & 0xFF) << 16) | ((int(color[2:4], 16) & 0xFF) << 8) | (int(color[4:6], 16) & 0xFF)
				elif type(color) is tuple and len(color) == 3:
					color = ((color[0] & 0xFF) << 16) | ((color[1] & 0xFF) << 8) | (color[2] & 0xFF)
				elif type(color) is not int:
					raise ValueError(f'Unexpected color value: \'{color}\'')

				assert point[1] > 0, 'Pie value cannot be less than or equal to 0'
				self.__points__[point[0]] = point[1]
				self.__point_colors__[point[0]] = color & 0xFFFFFF
			elif type(point) is Vector.Vector and 2 <= point.dimension() <= 3:
				assert point[1] > 0, 'Pie value cannot be less than or equal to 0'
				self.__points__[point[0]] = point[1]
				self.__point_colors__[point[0]] = (point[2] & 0xFFFFFF) if point.dimension() == 3 else 0xFFFFFF
			else:
				raise TypeError(f'{type(self).__name__}::add_points - \'*points\' point must be either a tuple of length 2 or a Math.Vector.Vector of dimension 2')

		for key, value in bound_points.items():
			key = key.replace('_', ' ')

			if type(value) in (int, float):
				#assert value > 0, 'Pie value cannot be less than or equal to 0'
				self.__points__[key] = value
				self.__point_colors__[key] = 0xFFFFFF
			elif type(value) is tuple and type(value[0]) in (int, float):
				color: str | int | tuple[int, int, int] = value[1] if len(value) == 2 else 0xFFFFFF

				if type(color) is str:
					color = color[1:] if color[0] == '#' else color
					color = ((int(color[0:2], 16) & 0xFF) << 16) | ((int(color[2:4], 16) & 0xFF) << 8) | (int(color[4:6], 16) & 0xFF)
				elif type(color) is tuple and len(color) == 3:
					color = ((color[0] & 0xFF) << 16) | ((color[1] & 0xFF) << 8) | (color[2] & 0xFF)
				elif type(color) is not int:
					raise ValueError(f'Unexpected color value: \'{color}\'')

				#assert value[0] > 0, 'Pie value cannot be less than or equal to 0'
				self.__points__[key] = value[0]
				self.__point_colors__[key] = color & 0xFFFFFF
			else:
				raise TypeError(f'{type(self).__name__}::add_points - \'**bound_points\' point must be a float, int, or tuple containing a float or int and a color')

	def get_points(self, order: str | typing.Callable = None) -> tuple[tuple[typing.Any, float], ...] | set[tuple[typing.Any, float]]:
		"""
		Gets the internal list of points
		:param order: (str or CALLABLE) If 'x', orders points based on their x values; If 'y', orders points based on their 'y' values; if a callable, sorts based on that function; Otherwise returns unordered points
		:return: (tuple or set) A set if left unordered, otherwise an ordered tuple
		:raises AssertionError: If order is not a valid axis and order it not callable
		"""

		if order is None:
			return {(k, v) for k, v in self.__points__.items()}
		else:
			if order == 'x':
				sorter: typing.Callable = lambda point: point[0]
			elif order == 'y':
				sorter: typing.Callable = lambda point: point[1]
			else:
				sorter: typing.Callable = order

			assert callable(sorter), f'{type(self).__name__}::get_points - \'order\' must be a callable, \'x\', \'y\', or None'

			return tuple(sorted(((k, v) for k, v in self.__points__.items()), key=sorter))


class HistogramPlot2D(Plot2D, AxisPlot2D):
	"""
	[HistogramPlot2D(Plot2D, AxisPlot2D)] - Histogram Graph Plotter plotting values in 2D space
	"""

	def __init__(self, bin_count: int = 1):
		"""
		[HistogramPlot2D(Plot2D, AxisPlot2D)] - Histogram Graph Plotter plotting values in 2D space
		- Constructor -
		"""

		if bin_count < 1:
			raise ValueError(f'{type(self).__name__}::__init__ - \'bin_count\' must be an integer greater than or equal to one')

		Plot2D.__init__(self)
		AxisPlot2D.__init__(self)
		self.__points__: list[float] = []
		self.__bin_count__: int = int(bin_count)
		self.__add_axis__('xy', min_=0, max_=10, minor_spacing=1, major_spacing=None)

	def __legend__(self) -> dict[str, tuple[int, int | float | complex | None]]:
		return {str(a): (self.__plot_info__['color'], b) for a, b in self.get_bin_counts().items()}

	def __image__(self) -> tuple[np.ndarray, tuple[int, int], tuple[float, float], int, int]:
		base_image: np.ndarray
		draw_size: tuple[int, int]
		draw_border: tuple[float, float]
		window_size_unit: int
		draw_size_unit: int
		base_image, draw_size, draw_border, window_size_unit, draw_size_unit = super().__image__()
		border: tuple[float, float] = (draw_border[0] / 2, draw_border[1] / 2)
		bounds: tuple[int, int, int, int] = (round(border[0]), round(border[1]), round(border[0] + draw_size[0]), round(border[1] + draw_size[1]))
		bins: dict[int, int] = self.get_bin_counts()
		max_x: int = len(bins) + 2
		max_y: float | None = max(bins.values()) + 1 if max_x else None
		min_y: float | None = min(bins.values()) - 1 if max_x else None

		if max_x > 0 and max_y is not None and min_y is not None:
			self.axis_info('x', min_=0, max_=max_x)
			self.axis_info('y', min_=min_y, max_=max_y)

		spacing: int = (round(draw_size[0] / 2 / max_x)) if (max_x % 2 == 0) else 0
		image = PIL.Image.fromarray(base_image)
		drawer = PIL.ImageDraw.Draw(image)
		rect_width: int = round(draw_size[0] / max_x)
		y2: int = draw_size[1] - round(draw_size[1] * ((-min_y) / (max_y - min_y)))

		for bindex, count in bins.items():
			x1: int = round(rect_width * (bindex + 1))
			x2: int = round(x1 + rect_width)
			y1: int = y2 - round(draw_size[1] / (max_y - min_y) * count)
			sy: int = y1 if y1 <= y2 else y2
			ly: int = y1 if y1 > y2 else y2
			drawer.rectangle((x1, sy, x2, ly), fill=f'#{hex(self.__plot_info__['color'])[2:].zfill(6)}', outline='#eeeeee', width=2)

		base_image = np.array(image)
		self.__draw_linear_axis__('x', base_image, draw_size, draw_border, (draw_size[0] // 2 - spacing, y2))
		self.__draw_linear_axis__('y', base_image, draw_size, draw_border, (0, y2), angle=90)
		return base_image, draw_size, draw_border, window_size_unit, draw_size_unit

	def add_points(self, *points: float | int) -> None:
		"""
		Adds points to the plot
		:param points: (*float or *int) A variadic list of integers or floats
		:return: (None)
		:raises AssertionError: If any arguments' type is incorrect
		:raises TypeError: If a point is invalid
		"""

		self.__points__.extend(float(x) for x in points)

	def get_points(self, order: typing.Optional[typing.Callable] = None) -> tuple[float, ...]:
		"""
		Gets the internal list of points
		:param order: (str or CALLABLE) If 'x', orders points based on their x values; If 'y', orders points based on their 'y' values; if a callable, sorts based on that function; Otherwise returns unordered points
		:return: (tuple or set) A set if left unordered, otherwise an ordered tuple
		:raises AssertionError: If order is not a valid axis and order it not callable
		"""

		if order is None:
			return tuple(self.__points__)
		else:
			assert callable(order), f'{type(self).__name__}::get_points - \'order\' must be a callable, \'x\', \'y\', or None'
			return tuple(sorted(self.__points__, key=order))

	def get_bin_counts(self) -> dict[int, int]:
		"""
		Gets the number of items in each bin
		:return: (dict[int, int]) A dictionary mapping a bin number to the number of elements it contains
		"""

		return {a: len(b) for a, b in self.get_bin_values().items()}

	def get_bin_totals(self) -> dict[int, float]:
		"""
		Gets the sum of items in each bin
		:return: (dict[int, float]) A dictionary mapping a bin number to the total of elements it contains
		"""

		return {a: sum(b) if len(b) else 0 for a, b in self.get_bin_values().items()}

	def get_bin_values(self) -> dict[int, tuple[float, ...]]:
		"""
		Gets the items in each bin
		:return: (dict[int, tuple[float, ...]]) A dictionary mapping a bin number to the elements it contains
		"""

		if len(self.__points__) == 0:
			return {}

		vmin: float
		vmax: float
		vmin, vmax = minmax(self.__points__)
		bin_width: float = (vmax - vmin) / self.__bin_count__
		bins: dict[int, list[float]] = {}

		for value in self.__points__:
			bindex: int = math.floor(value / bin_width) - 1

			if bindex in bins:
				bins[bindex].append(value)
			else:
				bins[bindex] = [value]

		kmin: int
		kmax: int
		kmin, kmax = minmax(bins.keys())
		return {i: tuple(bins[i]) if i in bins else () for i in range(kmin, kmax + 1)}

	@property
	def bins(self) -> int:
		"""
		Gets the bin count of this histogram
		:return: (int) Bin count
		"""

		return self.__bin_count__

	@bins.setter
	def bins(self, value: int) -> None:
		"""
		Sets the bin count of this histogram
		:param value: (int) The new bin count
		:return: (None)
		:raises ValueError: If the specified value is less than one
		"""

		if value < 1:
			raise ValueError(f'{type(self).__name__}::bins.setter - \'value\' must be an integer greater than or equal to one')

		self.__bin_count__ = int(value)


class DensityPlot2D(HistogramPlot2D):
	def __image__(self) -> tuple[np.ndarray, tuple[int, int], tuple[float, float], int, int]:
		base_image: np.ndarray
		draw_size: tuple[int, int]
		draw_border: tuple[float, float]
		window_size_unit: int
		draw_size_unit: int
		base_image, draw_size, draw_border, window_size_unit, draw_size_unit = Plot2D.__image__(self)
		border: tuple[float, float] = (draw_border[0] / 2, draw_border[1] / 2)
		bounds: tuple[int, int, int, int] = (round(border[0]), round(border[1]), round(border[0] + draw_size[0]), round(border[1] + draw_size[1]))
		bins: dict[int, int] = self.get_bin_counts()
		max_x: int = len(bins) + 2
		max_y: float | None = max(bins.values()) + 1 if max_x else None
		min_y: float | None = min(bins.values()) - 1 if max_x else None

		if max_x > 0 and max_y is not None and min_y is not None:
			self.axis_info('x', min_=0, max_=max_x)
			self.axis_info('y', min_=min_y, max_=max_y)

		spacing: int = (round(draw_size[0] / 2 / max_x)) if (max_x % 2 == 0) else 0
		rect_width: int = round(draw_size[0] / max_x)
		y2: int = draw_size[1] - round(draw_size[1] * ((-min_y) / (max_y - min_y)))
		line: list[tuple[int, int]] = [(0, y2)]
		point_size: int = self.__plot_info__['point_size']
		point_color: str = f'#{hex(self.__plot_info__['color'])[2:].zfill(6)}'

		for bindex, count in bins.items():
			x1: int = round(rect_width * (bindex + 1))
			x2: int = round(x1 + rect_width)
			x: int = round((x1 + x2) / 2)
			y: int = y2 - round(draw_size[1] / (max_y - min_y) * count)
			line.append((x, y))

		line.append((draw_size[1], y2))
		line_x: tuple[int, ...] = tuple(point[0] for point in line)
		line_y: tuple[int, ...] = tuple(point[1] for point in line)
		interpolator: typing.Callable = scipy.interpolate.interp1d(line_x, line_y, kind=2)
		line_x: np.ndarray = np.linspace(*minmax(line_x), num=100)
		line_y: np.ndarray = interpolator(line_x)
		image: PIL.Image.Image = PIL.Image.fromarray(base_image)
		drawer: PIL.ImageDraw.ImageDraw = PIL.ImageDraw.ImageDraw(image)

		for i in range(len(line_x) - 1):
			point1: tuple[int, int] = (int(line_x[i]), int(line_y[i]))
			point2: tuple[int, int] = (int(line_x[i + 1]), int(line_y[i + 1]))
			drawer.line((point1, point2), fill=point_color, width=max(1, point_size // 4))

		for x, y in line:
			drawer.circle((x, y), point_size // 2, fill=point_color, width=2, outline='#eeeeee')

		base_image = np.array(image)

		self.__draw_linear_axis__('x', base_image, draw_size, draw_border, (draw_size[0] // 2 - spacing, y2))
		self.__draw_linear_axis__('y', base_image, draw_size, draw_border, (0, y2), angle=90)
		return base_image, draw_size, draw_border, window_size_unit, draw_size_unit


class DotPlot2D(HistogramPlot2D):
	def __legend__(self) -> dict[str, tuple[int, int | float | complex | None]]:
		legend: dict[str, tuple[int, int | float | complex | None]] = {}
		bins: dict[int, int] = self.get_bin_counts()
		highest_count: float = max(bins.values())
		point_color: int = self.__plot_info__['color']
		r: int = point_color >> 16 & 0xFF
		g: int = point_color >> 8 & 0xFF
		b: int = point_color & 0xFF
		h, l, s = colorsys.rgb_to_hls(r, g, b)

		for bindex, count in bins.items():
			local_l: float = l * (count / highest_count)
			r, g, b = colorsys.hls_to_rgb(h, local_l, s)
			color_int: int = (int(r) << 16) | (int(g) << 8) | int(b)
			legend[str(bindex)] = (color_int, count)

		return legend

	def __image__(self) -> tuple[np.ndarray, tuple[int, int], tuple[float, float], int, int]:
		base_image: np.ndarray
		draw_size: tuple[int, int]
		draw_border: tuple[float, float]
		window_size_unit: int
		draw_size_unit: int
		base_image, draw_size, draw_border, window_size_unit, draw_size_unit = Plot2D.__image__(self)
		border: tuple[float, float] = (draw_border[0] / 2, draw_border[1] / 2)
		bins: dict[int, int] = self.get_bin_counts()
		max_x: int = len(bins)
		max_y: float | None = max(bins.values()) + 1 if max_x else None
		min_y: float | None = min(bins.values()) - 1 if max_x else None

		if max_x > 0 and max_y is not None and min_y is not None:
			self.axis_info('x', min_=0, max_=max_x)
			self.axis_info('y', min_=min_y, max_=max_y)

		spacing: int = (round(draw_size[0] / 2 / max_x)) if (max_x % 2 == 0) else 0
		image = PIL.Image.fromarray(base_image)
		drawer = PIL.ImageDraw.Draw(image)
		highest_count: float = max(bins.values())
		point_radius: int = round(self.__plot_info__['point_size'] / 2)
		point_color: int = self.__plot_info__['color']
		r: int = point_color >> 16 & 0xFF
		g: int = point_color >> 8 & 0xFF
		b: int = point_color & 0xFF
		h, l, s = colorsys.rgb_to_hls(r, g, b)
		rect_width: float = draw_size[0] / max_x
		rect_half_width: float = draw_size[0] / max_x / 2
		y: int = round(draw_size[1] / 2)

		for bindex, count in bins.items():
			local_l: float = l * (count / highest_count)
			r, g, b = colorsys.hls_to_rgb(h, local_l, s)
			x: int = round(rect_width * bindex + rect_half_width)
			color_int: int = (int(r) << 16) | (int(g) << 8) | int(b)
			drawer.circle((x, y), point_radius, fill=f'#{hex(color_int)[2:].zfill(6)}', outline='#eeeeee', width=2)

		base_image = np.array(image)
		self.__draw_linear_axis__('x', base_image, draw_size, draw_border, (draw_size[0] // 2 - spacing, draw_size[1]))
		return base_image, draw_size, draw_border, window_size_unit, draw_size_unit


class StackedDotPlot2D(Plot2D, AxisPlot2D):
	pass


class BoxPlot(MultiPlot2D, AxisPlot2D):
	pass
