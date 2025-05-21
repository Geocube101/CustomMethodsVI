from __future__ import annotations

import curses
import importlib.util
import os
import sys
import typing
import types


class MouseInfo:
	def __init__(self, __id: int, x: int, y: int, z: int, bstate: int):
		self.__info__: tuple[int, int, int, int, int] = (__id, x, y, z, bstate)

	def __iter__(self):
		return iter(self.__info__)

	@property
	def alt_pressed(self) -> bool:
		return (self.__info__[4] & curses.BUTTON_ALT) != 0

	@property
	def shift_pressed(self) -> bool:
		return (self.__info__[4] & curses.BUTTON_SHIFT) != 0

	@property
	def crtl_pressed(self) -> bool:
		return (self.__info__[4] & curses.BUTTON_CTRL) != 0

	@property
	def left_clicked(self) -> bool:
		return self.left_sngl_clicked or self.left_dbl_clicked or self.left_trpl_clicked

	@property
	def middle_clicked(self) -> bool:
		return self.middle_sngl_clicked or self.middle_dbl_clicked or self.middle_trpl_clicked

	@property
	def right_clicked(self) -> bool:
		return self.right_sngl_clicked or self.right_dbl_clicked or self.right_trpl_clicked

	@property
	def scroll_up_clicked(self) -> bool:
		return self.scroll_up_sngl_clicked or self.scroll_up_dbl_clicked or self.scroll_up_trpl_clicked

	@property
	def scroll_down_clicked(self) -> bool:
		return self.scroll_down_sngl_clicked or self.scroll_down_dbl_clicked or self.scroll_down_trpl_clicked

	@property
	def left_sngl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON1_CLICKED) != 0

	@property
	def middle_sngl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON2_CLICKED) != 0

	@property
	def right_sngl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON3_CLICKED) != 0

	@property
	def scroll_up_sngl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON4_CLICKED) != 0

	@property
	def scroll_down_sngl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON5_CLICKED) != 0

	@property
	def left_dbl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON1_DOUBLE_CLICKED) != 0

	@property
	def middle_dbl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON2_DOUBLE_CLICKED) != 0

	@property
	def right_dbl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON3_DOUBLE_CLICKED) != 0

	@property
	def scroll_up_dbl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON4_DOUBLE_CLICKED) != 0

	@property
	def scroll_down_dbl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON5_DOUBLE_CLICKED) != 0

	@property
	def left_trpl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON1_TRIPLE_CLICKED) != 0

	@property
	def middle_trpl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON2_TRIPLE_CLICKED) != 0

	@property
	def right_trpl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON3_TRIPLE_CLICKED) != 0

	@property
	def scroll_up_trpl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON4_TRIPLE_CLICKED) != 0

	@property
	def scroll_down_trpl_clicked(self) -> bool:
		return (self.__info__[4] & curses.BUTTON5_TRIPLE_CLICKED) != 0

	@property
	def left_pressed(self) -> bool:
		return (self.__info__[4] & curses.BUTTON1_PRESSED) != 0

	@property
	def middle_pressed(self) -> bool:
		return (self.__info__[4] & curses.BUTTON2_PRESSED) != 0

	@property
	def right_pressed(self) -> bool:
		return (self.__info__[4] & curses.BUTTON3_PRESSED) != 0

	@property
	def scroll_up_pressed(self) -> bool:
		return (self.__info__[4] & curses.BUTTON4_PRESSED) != 0

	@property
	def scroll_down_pressed(self) -> bool:
		return (self.__info__[4] & curses.BUTTON5_PRESSED) != 0

	@property
	def left_released(self) -> bool:
		return (self.__info__[4] & curses.BUTTON1_RELEASED) != 0

	@property
	def middle_released(self) -> bool:
		return (self.__info__[4] & curses.BUTTON2_RELEASED) != 0

	@property
	def right_released(self) -> bool:
		return (self.__info__[4] & curses.BUTTON3_RELEASED) != 0

	@property
	def scroll_up_released(self) -> bool:
		return (self.__info__[4] & curses.BUTTON4_RELEASED) != 0

	@property
	def scroll_down_released(self) -> bool:
		return (self.__info__[4] & curses.BUTTON5_RELEASED) != 0

	@property
	def mouse_id(self) -> int:
		return self.__info__[0]

	@property
	def bstate(self) -> int:
		return self.__info__[4]

	@property
	def pos_x(self) -> int:
		return self.__info__[1]

	@property
	def pos_y(self) -> int:
		return self.__info__[2]

	@property
	def pos_z(self) -> int:
		return self.__info__[3]

	@property
	def position(self) -> tuple[int, int, int]:
		return self.pos_x, self.pos_y, self.pos_z


class BorderInfo:
	@classmethod
	def EmptyBorder(cls) -> BorderInfo:
		return cls('', '', '', '', '', '', '', '')

	def __init__(self, t: str = '─', r: str = '│', b: str = '─', l: str = '│', tr: str = '┐', br: str = '┘', bl: str = '└', tl: str = '┌'):
		self.__border__: tuple[str, str, str, str, str, str, str, str] = (t, r, b, l, tr, br, bl, tl)
		assert all(isinstance(x, str) and len(x) <= 1 for x in self.__border__), 'One or more border values are incorrect (not a string or len(x) > 1)'

	@property
	def top(self) -> str:
		return self.__border__[0]

	@property
	def right(self) -> str:
		return self.__border__[1]

	@property
	def bottom(self) -> str:
		return self.__border__[2]

	@property
	def left(self) -> str:
		return self.__border__[3]

	@property
	def top_right(self) -> str:
		return self.__border__[4]

	@property
	def bottom_right(self) -> str:
		return self.__border__[5]

	@property
	def bottom_left(self) -> str:
		return self.__border__[6]

	@property
	def top_left(self) -> str:
		return self.__border__[7]


class Color:
	@classmethod
	def fromhex(cls, hexstring: str) -> Color:
		return cls(int(hexstring.lstrip('#').rjust(6, '0'), 16))

	@classmethod
	def fromrgb(cls, r: int, g: int, b: int) -> Color:
		assert 0 <= r < 256, 'Red out of range'
		assert 0 <= g < 256, 'Green out of range'
		assert 0 <= b < 256, 'Blue out of range'
		return cls((r << 16) | (g << 8) | b)

	@classmethod
	def fromcurses(cls, color: int) -> Color:
		r, g, b = curses.color_content(color)
		return cls.fromrgb(round(r / 1000 * 255), round(g / 1000 * 255), round(b / 1000 * 255))

	@classmethod
	def fromcursesrgb(cls, r: int, g: int, b: int) -> Color:
		return cls.fromrgb(round(r / 1000 * 255), round(g / 1000 * 255), round(b / 1000 * 255))

	def __init__(self, color: int):
		assert 0 <= color <= 0xFFFFFF, 'Invalid color'
		self.__color__: int = int(color)

	def __eq__(self, other: Color) -> bool:
		return self.__color__ == other.__color__ if isinstance(other, type(self)) else NotImplemented

	def __hash__(self) -> int:
		return hash(self.__color__)

	def __int__(self) -> int:
		return self.__color__

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return f'<Color[{self.__color__}]> @ {hex(id(self))}>'

	@property
	def color(self) -> int:
		return self.__color__

	@property
	def rgb(self) -> tuple[int, int, int]:
		return (self.__color__ >> 16) & 0xFF, (self.__color__ >> 8) & 0xFF, self.__color__ & 0xFF

	@property
	def curses_rgb(self) -> tuple[int, int, int]:
		return round(((self.__color__ >> 16) & 0xFF) / 255 * 1000), round(((self.__color__ >> 8) & 0xFF) / 255 * 1000), round((self.__color__ & 0xFF) / 255 * 1000)

	@property
	def hex(self) -> str:
		r, g, b = self.rgb
		return f'#{r:02X}{g:02X}{b:02X}'


class AnsiStr:
	class AnsiFormat:
		@classmethod
		def default(cls) -> AnsiStr.AnsiFormat:
			ansi: AnsiStr.AnsiFormat = AnsiStr.AnsiFormat()
			ansi.reset = False
			ansi.bold = False
			ansi.dim = False
			ansi.italic = False
			ansi.underline = False
			ansi.blink = False
			ansi.reverse = False
			ansi.invis = False
			ansi.protect = False
			return ansi

		def __init__(self):
			self.reset: bool | None = None
			self.bold: bool | None = None
			self.dim: bool | None = None
			self.italic: bool | None = None
			self.underline: bool | None = None
			self.blink: bool | None = None
			self.reverse: bool | None = None
			self.invis: bool | None = None
			self.protect: bool | None = None
			self.foreground_color: Color | int | None = None
			self.background_color: Color | int | None = None

		def __eq__(self, other: AnsiStr) -> bool:
			if not isinstance(other, type(self)):
				return NotImplemented

			return self.reset == other.reset and self.bold == other.bold and self.dim == other.dim and self.italic == other.italic and self.underline == other.underline and self.blink == other.blink and self.reverse == other.reverse and self.invis == other.invis and self.protect == other.protect and self.foreground_color == other.foreground_color and self.background_color == other.background_color

		def __str__(self) -> str:
			base: list[str] = ['\033[']

			if self.reset:
				base.append('0;')
			if self.bold:
				base.append('1;')
			if self.dim:
				base.append('2;')
			if self.italic:
				base.append('3;')
			if self.underline:
				base.append('4;')
			if self.blink:
				base.append('5;')
			if self.reverse:
				base.append('7;')
			if self.invis:
				base.append('8;')
			if self.protect:
				base.append('9;')

			if isinstance(self.foreground_color, int):
				base.append(f'38;5;{int(self.foreground_color)};')
			elif isinstance(self.foreground_color, Color):
				r, g, b = self.foreground_color.rgb
				base.append(f'38;2;{r};{g};{b};')

			if isinstance(self.background_color, int):
				base.append(f'48;5;{int(self.background_color)};')
			elif isinstance(self.background_color, Color):
				r, g, b = self.background_color.rgb
				base.append(f'48;2;{r};{g};{b};')

			return f'{"".join(base).rstrip(";")}m'

		def __repr__(self) -> str:
			return repr(str(self))

		def copy(self) -> AnsiStr.AnsiFormat:
			copy: AnsiStr.AnsiFormat = AnsiStr.AnsiFormat()
			copy.reset = False
			copy.bol = self.bold
			copy.dim = self.dim
			copy.italic = self.italic
			copy.underline = self.underline
			copy.blink = self.blink
			copy.reverse = self.reverse
			copy.invis = self.invis
			copy.protect = self.protect
			copy.foreground_color = self.foreground_color
			copy.background_color = self.background_color
			return copy

		def overlay(self, ansi: AnsiStr.AnsiFormat) -> AnsiStr.AnsiFormat:
			defaults: AnsiStr.AnsiFormat = AnsiStr.AnsiFormat.default()
			overlay: AnsiStr.AnsiFormat = AnsiStr.AnsiFormat()
			overlay.reset = False
			overlay.bold = defaults.bold if ansi.reset and self.bold is None else self.bold if ansi.bold is None and not ansi.reset else ansi.bold
			overlay.dim = defaults.dim if ansi.reset and self.dim is None else self.dim if ansi.dim is None and not ansi.reset else ansi.dim
			overlay.italic = defaults.italic if ansi.reset and self.italic is None else self.italic if ansi.italic is None and not ansi.reset else ansi.italic
			overlay.underline = defaults.underline if ansi.reset and self.underline is None else self.underline if ansi.underline is None and not ansi.reset else ansi.underline
			overlay.blink = defaults.blink if ansi.reset and self.blink is None else self.blink if ansi.blink is None and not ansi.reset else ansi.blink
			overlay.reverse = defaults.reverse if ansi.reset and self.reverse is None else self.reverse if ansi.reverse is None and not ansi.reset else ansi.reverse
			overlay.invis = defaults.invis if ansi.reset and self.invis is None else self.invis if ansi.invis is None and not ansi.reset else ansi.invis
			overlay.protect = defaults.protect if ansi.reset and self.protect is None else self.protect if ansi.protect is None and not ansi.reset else ansi.protect
			overlay.foreground_color = defaults.foreground_color if ansi.reset and self.foreground_color is None else self.foreground_color if ansi.foreground_color is None and not ansi.reset else ansi.foreground_color
			overlay.background_color = defaults.background_color if ansi.reset and self.background_color is None else self.background_color if ansi.background_color is None and not ansi.reset else ansi.background_color
			return overlay

	@classmethod
	def from_pairs(cls, pairs: typing.Iterable[tuple[str, AnsiStr.AnsiFormat]]) -> AnsiStr:
		ansi_str: AnsiStr = cls('')
		last_format: AnsiStr.AnsiFormat = AnsiStr.AnsiFormat()
		raw_string: list[str] = []

		for i, (char, ansi) in enumerate(pairs):
			raw_string.append(char)

			if ansi != last_format:
				last_format = ansi
				ansi_str.__ansi_format__[i] = ansi

		ansi_str.__raw_string__ = ''.join(raw_string)
		return ansi_str

	def __init__(self, string: str | AnsiStr):
		if isinstance(string, AnsiStr):
			self.__raw_string__ = string.__raw_string__
			self.__ansi_format__ = {an: si.copy() for an, si in string.__ansi_format__.items()}
			self.__pairs__: tuple[tuple[str, AnsiStr.AnsiFormat]] | None = string.__pairs__
			self.__groups__: tuple[tuple[str, AnsiStr.AnsiFormat]] | None = string.__groups__
			return

		raw_string: list[str] = []
		ansi_format: AnsiStr.AnsiFormat = AnsiStr.AnsiFormat.default()
		ansi_attrs: dict[int, AnsiStr.AnsiFormat] = {}
		skip: int = 0
		true_index: int = 0

		for i, char in enumerate(string):
			if skip > 0:
				skip -= 1
				continue

			if char == '\033' and i + 1 < len(string) and string[i + 1] == '[':
				try:
					duplicate: AnsiStr.AnsiFormat = ansi_format.copy()
					end: int = string.find('m', i + 2)
					skip = end - i
					ansi: str = string[i + 2:end]

					if len(ansi) == 0:
						continue

					payload: list[int] = [int(x) for x in ansi.split(';')]
					_skip: int = 0

					for an, si in enumerate(payload):
						if _skip > 0:
							_skip -= 1
							continue

						if si == 0:
							duplicate = AnsiStr.AnsiFormat()
							duplicate.reset = True
						elif si == 1:
							duplicate.bold = True
						elif si == 2:
							duplicate.dim = True
						elif si == 3:
							duplicate.italic = True
						elif si == 4:
							duplicate.underline = True
						elif si == 5:
							duplicate.blink = True
						elif si == 7:
							duplicate.reverse = True
						elif si == 8:
							duplicate.invis = True
						elif si == 9:
							duplicate.protect = True
						elif si == 21:
							duplicate.bold = False
						elif si == 22:
							duplicate.bold = False
							duplicate.dim = False
						elif si == 23:
							duplicate.italic = False
						elif si == 24:
							duplicate.underline = False
						elif si == 25:
							duplicate.blink = False
						elif si == 27:
							duplicate.reverse = False
						elif si == 28:
							duplicate.invis = False
						elif si == 29:
							duplicate.protect = False
						elif si == 38 and payload[an + 1] == 2:
							r, g, b = payload[an + 2:an + 5]
							duplicate.foreground_color = Color.fromrgb(r, g, b)
							_skip = 4
						elif si == 38 and payload[an + 1] == 5:
							duplicate.foreground_color = payload[an + 2]
							_skip = 2
						elif si == 48 and payload[an + 1] == 2:
							r, g, b = payload[an + 2:an + 5]
							duplicate.background_color = Color.fromrgb(r, g, b)
							_skip = 4
						elif si == 48 and payload[an + 1] == 5:
							duplicate.background_color = payload[an + 2]
							_skip = 2
						elif si == 39:
							duplicate.foreground_color = 7
						elif si == 49:
							duplicate.background_color = 0

					if ansi_format != duplicate:
						ansi_attrs[true_index] = duplicate

					ansi_format = duplicate
				except (IndexError, ValueError) as e:
					raise ValueError(f'Malformed ANSI escape sequence - \'{repr(string)}\'') from e
			else:
				raw_string.append(char)
				true_index += 1

		self.__raw_string__: str = ''.join(raw_string)
		self.__ansi_format__: dict[int, AnsiStr.AnsiFormat] = ansi_attrs
		self.__pairs__: tuple[tuple[str, AnsiStr.AnsiFormat]] | None = None
		self.__groups__: tuple[tuple[str, AnsiStr.AnsiFormat]] | None = None

	def __contains__(self, substr: str | AnsiStr) -> bool:
		return (substr.__raw_string__ if isinstance(substr, type(self)) else substr) in self.__raw_string__

	def __repr__(self) -> str:
		return repr(str(self))

	def __str__(self) -> str:
		output: list[str] = []

		for i, char in enumerate(self.__raw_string__):
			if i in self.__ansi_format__:
				output.append(str(self.__ansi_format__[i]))
			output.append(char)

		for index, ansi in self.__ansi_format__.items():
			if index >= len(self.__raw_string__):
				output.append(str(ansi))

		return ''.join(output)

	def __format__(self, format_spec: str) -> str:
		return f'{str(self):{format_spec}}'

	def __iter__(self) -> typing.Iterator[str]:
		return iter(self.__raw_string__)

	def __len__(self) -> int:
		return max(len(self.__raw_string__), *tuple(x + 1 for x in self.__ansi_format__.keys())) if len(self.__ansi_format__) else len(self.__raw_string__)

	def __getitem__(self, index: int | slice) -> AnsiStr:
		copy: AnsiStr = AnsiStr('')
		copy.__raw_string__ = self.__raw_string__[index]
		indices: tuple[int] = (int(index),) if isinstance(index, int) else tuple(range(0 if index.start is None else int(index.start), len(self) if index.stop is None else int(index.stop), 1 if index.step is None else int(index.step))) if isinstance(index, slice) else None

		if indices is None:
			raise TypeError(f'AnsiStr indices must be integers, not \'{type(index).__name__}\'')
		elif len(indices) == 0:
			return AnsiStr('')

		smallest_index: int = min(indices)
		available_format_indices: tuple[int, ...] = tuple(i for i in self.__ansi_format__.keys() if i <= smallest_index)
		first_format_index: int = max(available_format_indices) if len(available_format_indices) else -1
		copy.__ansi_format__.update({an - smallest_index: si.copy() for an, si in self.__ansi_format__.items() if an in indices})

		if first_format_index != -1:
			copy.__ansi_format__[0] = self.__ansi_format__[first_format_index].copy()

		return copy

	def __mul__(self, other: int) -> AnsiStr:
		return AnsiStr(str(self) * int(other)) if isinstance(other, int) else NotImplemented

	def __rmul__(self, other: int) -> AnsiStr:
		return AnsiStr(str(self) * int(other)) if isinstance(other, int) else NotImplemented

	def __add__(self, other: AnsiStr | str) -> AnsiStr:
		return AnsiStr(str(self) + str(other)) if isinstance(other, (str, AnsiStr)) else NotImplemented

	def __radd__(self, other: AnsiStr | str) -> str:
		return str(self) + str(other) if isinstance(other, (str, AnsiStr)) else NotImplemented

	def index(self, substr: str | AnsiStr, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		return self.__raw_string__.index(substr.__raw_string__ if isinstance(substr, type(self)) else substr, start, stop)

	def rindex(self, substr: str | AnsiStr, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		return self.__raw_string__.rindex(substr.__raw_string__ if isinstance(substr, type(self)) else substr, start, stop)

	def find(self, substr: str | AnsiStr, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		return self.__raw_string__.find(substr.__raw_string__ if isinstance(substr, type(self)) else substr, start, stop)

	def pairs(self) -> typing.Iterator[tuple[str, AnsiStr.AnsiFormat]]:
		if self.__pairs__ is not None:
			for ansi in self.__pairs__:
				yield ansi
			return

		last_format: AnsiStr.AnsiFormat = AnsiStr.AnsiFormat.default()
		pairs: list[tuple[str, AnsiStr.AnsiFormat]] = []

		for i in range(len(self)):
			char: str = self.__raw_string__[i] if i < len(self.__raw_string__) else ''

			if i in self.__ansi_format__:
				last_format = last_format.overlay(self.__ansi_format__[i])

			pairs.append((char, last_format))
			yield char, last_format.copy()

		self.__pairs__ = tuple(pairs)

	def format_groups(self, delimiter: str = '', keep_delimiter: bool = False) -> typing.Iterator[tuple[str, AnsiStr.AnsiFormat]]:
		if self.__pairs__ is not None:
			for ansi in self.__pairs__:
				yield ansi
			return

		last_format: AnsiStr.AnsiFormat = AnsiStr.AnsiFormat.default()
		groups: list[tuple[str, AnsiStr.AnsiFormat]] = []
		string: list[str] = []
		delimiter: tuple[str, ...] = tuple(delimiter)

		for i in range(len(self)):
			char: str = self.__raw_string__[i] if i < len(self.__raw_string__) else ''

			if i in self.__ansi_format__ or char in delimiter:
				_string: str = ''.join(string)
				string.clear()
				groups.append((_string, last_format))
				yield _string, last_format
				last_format = last_format if i not in self.__ansi_format__ else last_format.overlay(self.__ansi_format__[i])

				if char in delimiter and keep_delimiter:
					groups.append((char, last_format))
					yield char, last_format
				elif char not in delimiter:
					string.append(char)
			else:
				string.append(char)

		if len(string):
			_string: str = ''.join(string)
			groups.append((_string, last_format))
			yield _string, last_format

		if len(delimiter) == 0:
			self.__groups__ = tuple(groups)

	def split(self, separator: typing.Optional[str] = ..., max_split: int = -1) -> list[AnsiStr]:
		if max_split == 0:
			return [AnsiStr(self)]

		delimiter: tuple[str, ...] = (' ', '\t', '\n') if separator is ... or separator is None else (str(separator),)
		indices: list[int] = [0]
		spacing: dict[int, int] = {0: 0}

		for delim in delimiter:
			index: int = -1
			_indices: list[int] = []

			while (index := self.__raw_string__.find(delim, index + 1)) != -1:
				_indices.append(index)
				old_space: int = spacing[index] if index in spacing else 0
				spacing[index] = max(len(delim), old_space)

			indices.extend(i for i in _indices if i not in indices)

		if 0 < max_split < len(indices) - 1:
			del indices[-(len(indices) - max_split - 1):]

		indices.append(len(self))
		return [self[indices[i] + spacing[indices[i]]:indices[i + 1]] for i in range(len(indices) - 1)]

	@property
	def raw(self) -> str:
		return self.__raw_string__


class Font:
	def __init__(self, font_name: str, font_size: tuple[int, int], font_weight: int):
		self.__font__: tuple[str, int, int, int] = (font_name, font_size[0], font_size[1], font_weight)

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		size: tuple[int, int] = self.fontsize
		return f'<Font["{self.fontname}".{size[0]}x{size[1]}w{self.fontweight}] @ {hex(id(self))}>'

	@property
	def fontname(self) -> str:
		return self.__font__[0]

	@property
	def fontsize(self) -> tuple[int, int]:
		return self.__font__[1], self.__font__[2]

	@property
	def fontweight(self) -> int:
		return self.__font__[3]

	@fontname.setter
	def fontname(self, font_name: str) -> None:
		_, b, c, d = self.__font__
		self.__font__ = (str(font_name), b, c, d)

	@fontsize.setter
	def fontsize(self, font_size: tuple[int, int]) -> None:
		a, _1, _2, d = self.__font__
		self.__font__ = (a, int(font_size[0]), int(font_size[1]), d)

	@fontweight.setter
	def fontweight(self, font_weight: int) -> None:
		a, b, c, _ = self.__font__
		self.__font__ = (a, b, c, int(font_weight))


class WidgetStruct:
	def __init__(self, widget: int):
		self.__wid__: int = widget


class SerializableCallable:
	def __init__(self, global_callable: typing.Callable):
		assert callable(global_callable)
		module: types.ModuleType = sys.modules[global_callable.__module__]
		self.__module_file__: str = module.__file__
		self.__module_name__: str = module.__name__
		self.__callable_name__: str = global_callable.__name__
		self.__callable__: 'typing.Callable | None' = None

	def __setstate__(self, state: dict[str, typing.Any]) -> None:
		self.__dict__.update(state)

	def __getstate__(self) -> dict[str, typing.Any]:
		state: dict[str, typing.Any] = self.__dict__.copy()
		state['__callable__'] = None
		return state

	def __call__(self, *args, **kwargs) -> typing.Any:
		if self.__callable__ is None:
			temp_module: str = f'{hex(id(self))[2:]}_MODULE'
			spec = importlib.util.spec_from_file_location(temp_module, self.__module_file__)
			module: types.ModuleType = importlib.util.module_from_spec(spec)
			sys.modules[temp_module] = module
			spec.loader.exec_module(module)
			function: typing.Callable = getattr(module, self.__callable_name__)

			if callable(function):
				self.__callable__ = function
			else:
				raise TypeError(f'The listed variable is not callable @ \'{self.__module_file__}\'::\'{self.__callable_name__}\'')

			if temp_module in sys.modules:
				del sys.modules[temp_module]

		return self.__callable__(*args, **kwargs)


if os.name == 'nt':
	import ctypes.wintypes

	class COORD(ctypes.Structure):
		_fields_ = [
			("X", ctypes.wintypes.SHORT),
			("Y", ctypes.wintypes.SHORT),
		]


	class FontInfoEx(ctypes.Structure):
		_fields_ = (
			("cbSize", ctypes.wintypes.ULONG),
			("nFont", ctypes.wintypes.DWORD),
			("dwFontSize", COORD),
			("FontFamily", ctypes.wintypes.UINT),
			("FontWeight", ctypes.wintypes.UINT),
			("FaceName", ctypes.wintypes.WCHAR * 32)
		)


	class SECURITY_ATTRIBUTES(ctypes.Structure):
		_fields_ = (
			('nLength', ctypes.wintypes.DWORD),
			('lpSecurityDescriptor', ctypes.wintypes.LPVOID),
			('bInheritHandle', ctypes.wintypes.BOOL)
		)
else:
	class FontInfoEx:
		pass