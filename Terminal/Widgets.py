from __future__ import annotations

import typing
import types
import curses
import _curses
import curses.ascii
import time
import math
import PIL.Image
import numpy
import cv2

import CustomMethodsVI.Terminal.Terminal
import CustomMethodsVI.Terminal.Enums as Enums

from CustomMethodsVI.Terminal.Struct import Color, MouseInfo, BorderInfo, AnsiStr
from CustomMethodsVI.Exceptions import InvalidArgumentException
from CustomMethodsVI.Iterable import SpinQueue
from CustomMethodsVI.Concurrent import ThreadedPromise, Promise
from CustomMethodsVI.Connection import WinNamedPipe

try:
	import Terminal.Terminal as Terminal
except ImportError:
	import CustomMethodsVI.Terminal.Terminal as Terminal


def parse_color(color: Enums.Color_T, error: typing.Optional[BaseException] = ...) -> Color | None:
	if isinstance(color, (types.NoneType, Color)):
		return color
	elif isinstance(color, int) and 0 <= int(color) <= 0xFFFFFF:
		return Color(int(color))
	elif isinstance(color, int) and color < 0:
		return Color.fromcurses(-int(color))
	elif isinstance(color, int):
		raise ValueError(f'Integer value \'{color}\' must either be a curses color or RGB value in range 0x000000 to 0xFFFFFF')
	elif isinstance(color, (tuple, list)) and len(color) == 3 and all(isinstance(x, int) and 0 <= int(x) <= 0xFF for x in color):
		return Color.fromrgb(*color)
	elif isinstance(color, (tuple, list)) and len(color) == 3 and all(isinstance(x, int) and 0 <= int(x) <= 1000 for x in color):
		return Color.fromcursesrgb(*color)
	elif isinstance(color, str) and color[0] == '#':
		return Color.fromhex(color)
	elif color is None or color is ...:
		return None
	elif isinstance(error, BaseException):
		raise error
	else:
		return None

WIDGET_T = typing.TypeVar('WIDGET_T', bound='Widget')

### Standard Widgets1
class Widget:
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, z: int, width: int, height: int, *,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):
		assert isinstance(parent, (CustomMethodsVI.Terminal.Terminal.Terminal, Terminal.Terminal, SubTerminal)), f'Not a terminal or sub-terminal - {type(parent)}'

		if not isinstance(x, int):
			raise InvalidArgumentException(Widget.__init__, 'x', type(x), (int,))
		if not isinstance(y, int):
			raise InvalidArgumentException(Widget.__init__, 'y', type(y), (int,))
		if not isinstance(z, int):
			raise InvalidArgumentException(Widget.__init__, 'z', type(z), (int,))
		if not isinstance(width, int):
			raise InvalidArgumentException(Widget.__init__, 'width', type(width), (int,))
		if not isinstance(height, int):
			raise InvalidArgumentException(Widget.__init__, 'height', type(height), (int,))

		self.__terminal__: Terminal.Terminal | SubTerminal = parent
		self.__position__: list[int] = [int(x), int(y), int(z), int(width), int(height)]
		self.__hidden__: bool = False
		self.__hovering__: bool = False
		self.__hovering_top__: bool = False
		self.__pressed__: bool = False
		self.__focused__: bool = False
		self.__closed__: bool = False
		self.__tick__: int = 0
		self.__general_callback__: typing.Optional[typing.Callable[[Widget, str, ...], None]] = callback
		self.__focus_callback__: list[typing.Callable[[Widget], None]] = [on_focus, off_focus]
		self.__mouse_callback__: list[typing.Callable[[Widget, MouseInfo], None]] = [on_mouse_enter, on_mouse_leave, on_mouse_press, on_mouse_release, on_mouse_click]
		self.__on_tick__: typing.Callable[[Widget, int], None] = on_tick
		self.__on_close__: typing.Callable[[Widget], None] = on_close

	def __reduce__(self) -> tuple[typing.Callable, tuple, dict]:
		topmost: Terminal.WindowTerminal.SubprocessTerminal = self.topmost_parent()
		assert isinstance(topmost, Terminal.WindowTerminal.SubprocessTerminal), 'Cannot pickle main process widget'
		serialized: SerializedWidget = SerializedWidget(topmost.__widget_pipe__, self)
		return SerializedWidget.__expand__, (), serialized.__getstate__()

	def __focus__(self) -> None:
		self.__focused__ = True

		if callable(self.__focus_callback__[0]):
			self.__focus_callback__[0](self)
		if callable(self.__general_callback__):
			self.__general_callback__(self, 'focus')

	def __unfocus__(self) -> None:
		self.__focused__ = False
		self.__pressed__ = False
		self.__hovering__ = False

		if callable(self.__focus_callback__[1]):
			self.__focus_callback__[1](self)
		if callable(self.__general_callback__):
			self.__general_callback__(self, 'unfocus')

	def __wordwrap__(self, text: AnsiStr, lines: list[AnsiStr], word_wrap: int, width: typing.Optional[int] = ..., height: typing.Optional[int] = ...) -> None:
		width: int = self.width if width is None or width is ... else int(width)
		height: int = self.height if height is None or height is ... else int(height)

		if word_wrap == Enums.WORDWRAP_ALL:
			line: list[tuple[str, AnsiStr.AnsiFormat]] = []

			for char, _ansi in text.pairs():
				if char == '\n':
					lines.append(AnsiStr.from_pairs(line))
					line.clear()
				elif len(line) < width:
					line.append((char, _ansi))
				elif len(lines) >= height:
					break
				else:
					lines.append(AnsiStr.from_pairs(line))
					line.clear()
					line.append((char, _ansi))

			if len(line) and len(lines) < height:
				lines.append(AnsiStr.from_pairs(line))

		elif word_wrap == Enums.WORDWRAP_WORD:
			word: list[tuple[str, AnsiStr.AnsiFormat]] = []
			_text: list[list[AnsiStr | str]] = [[]]
			length: int = 0

			for char, _ansi in text.pairs():
				if char.isspace() and len(word):
					if length + len(word) <= width:
						_word: AnsiStr = AnsiStr.from_pairs(word)
						_text[-1].append(_word)
						length += len(_word)
						word.clear()
					else:
						_word: AnsiStr = AnsiStr.from_pairs(word)
						_text.append([_word])
						length = len(_word)
						word.clear()

					if char == '\n':
						_text.append([])
						length = 0
					else:
						_text[-1].append(char)
						length += 1
				elif not char.isspace():
					word.append((char, _ansi))

			if len(word) and length + len(word) <= width:
				_text[-1].append(AnsiStr.from_pairs(word))
			elif len(word):
				_text.append([AnsiStr.from_pairs(word)])

			lines.extend(AnsiStr(''.join(str(x) for x in line))[:width] for i, line in enumerate(_text) if i < height)
		elif word_wrap == Enums.WORDWRAP_NONE:
			line: list[tuple[str, AnsiStr.AnsiFormat]] = []

			for char, _ansi in text.pairs():
				if char == '\n':
					lines.append(AnsiStr.from_pairs(line))
					line.clear()
				elif len(line) <= width:
					line.append((char, _ansi))
				elif len(lines) >= height:
					break

			if len(line) and len(lines) < height:
				lines.append(AnsiStr.from_pairs(line))
		else:
			raise RuntimeError(f'Invalid word wrap: \'{word_wrap}\'')

	def close(self) -> None:
		if not self.__closed__ and callable(self.__on_close__):
			self.__on_close__(self)

		if not self.__closed__ and callable(self.__general_callback__):
			self.__general_callback__(self, 'close')

		self.__closed__ = True

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> None:

		if x is not ... and x is not None and not isinstance(x, int):
			raise InvalidArgumentException(Widget.configure, 'x', type(x), (int,))
		if y is not ... and y is not None and not isinstance(y, int):
			raise InvalidArgumentException(Widget.configure, 'y', type(y), (int,))
		if z is not ... and z is not None and not isinstance(z, int):
			raise InvalidArgumentException(Widget.configure, 'z', type(z), (int,))
		if width is not ... and width is not None and not isinstance(width, int):
			raise InvalidArgumentException(Widget.configure, 'width', type(width), (int,))
		if height is not ... and height is not None and not isinstance(height, int):
			raise InvalidArgumentException(Widget.configure, 'height', type(height), (int,))

		self.__position__[0] = self.__position__[0] if x is ... or x is None else int(x)
		self.__position__[1] = self.__position__[1] if y is ... or y is None else int(y)
		self.__position__[2] = self.__position__[2] if z is ... or z is None else int(z)
		self.__position__[3] = self.__position__[3] if width is ... or width is None else int(width)
		self.__position__[4] = self.__position__[4] if height is ... or height is None else int(height)

		self.__general_callback__: typing.Optional[typing.Callable[[Widget, str, ...], None]] = self.__general_callback__ if callback is ... else callback
		self.__focus_callback__[0] = self.__focus_callback__[0] if on_focus is ... else on_focus
		self.__focus_callback__[1] = self.__focus_callback__[1] if off_focus is ... else off_focus

		self.__mouse_callback__[0] = self.__mouse_callback__[0] if on_mouse_enter is ... else on_mouse_enter
		self.__mouse_callback__[1] = self.__mouse_callback__[1] if on_mouse_leave is ... else on_mouse_leave
		self.__mouse_callback__[2] = self.__mouse_callback__[2] if on_mouse_press is ... else on_mouse_press
		self.__mouse_callback__[3] = self.__mouse_callback__[3] if on_mouse_release is ... else on_mouse_release
		self.__mouse_callback__[4] = self.__mouse_callback__[4] if on_mouse_click is ... else on_mouse_click

		self.__on_tick__: typing.Callable[[Widget, int], None] = self.__on_tick__ if on_tick is ... else on_tick
		self.__on_close__: typing.Callable[[Widget], None] = self.__on_close__ if on_close is ... else on_close

	def set_position(self, x: typing.Optional[int], y: typing.Optional[int]) -> None:
		if x is not None and x is not ... and not isinstance(x, int):
			raise InvalidArgumentException(Widget.set_position, 'x', type(x), ('int',))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise InvalidArgumentException(Widget.set_position, 'y', type(y), ('int',))
		else:
			self.__position__[0] = self.__position__[0] if x is None or x is ... else int(x)
			self.__position__[1] = self.__position__[1] if y is None or y is ... else int(y)

	def move(self, x: typing.Optional[int], y: typing.Optional[int] = ...) -> None:
		if x is not None and x is not ... and not isinstance(x, int):
			raise InvalidArgumentException(Widget.set_position, 'x', type(x), ('int',))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise InvalidArgumentException(Widget.set_position, 'y', type(y), ('int',))
		else:
			self.__position__[0] += 0 if x is None or x is ... else int(x)
			self.__position__[1] += 0 if y is None or y is ... else int(y)

	def draw(self) -> None:
		self.__tick__ += 1

		if callable(self.__on_tick__):
			self.__on_tick__(self, self.__tick__)

		if callable(self.__general_callback__):
			self.__general_callback__(self, 'tick', self.__tick__)

		mouse_info: MouseInfo = self.parent.mouse
		mouse_x: int = mouse_info.pos_x
		mouse_y: int = mouse_info.pos_y
		mouse_over: bool = self.has_coord(mouse_x, mouse_y)
		mouse_inside: bool = mouse_over and self.__terminal__.get_topmost_child_at(mouse_x, mouse_y) is self
		mouse_enter: typing.Callable[[Widget, MouseInfo], None]
		mouse_leave: typing.Callable[[Widget, MouseInfo], None]
		mouse_press: typing.Callable[[Widget, MouseInfo], None]
		mouse_release: typing.Callable[[Widget, MouseInfo], None]
		mouse_click: typing.Callable[[Widget, MouseInfo], None]
		mouse_enter, mouse_leave, mouse_press, mouse_release, mouse_click = self.__mouse_callback__

		if mouse_over and not self.__hovering__:
			if callable(mouse_enter):
				mouse_enter(self, mouse_info)
			if callable(self.__general_callback__):
				self.__general_callback__(self, 'mouse_enter', mouse_info)
		elif not mouse_over and self.__hovering__:
			if callable(mouse_leave):
				mouse_leave(self, mouse_info)
			if callable(self.__general_callback__):
				self.__general_callback__(self, 'mouse_leave', mouse_info)

		if mouse_inside and not self.__pressed__ and (mouse_info.left_pressed or mouse_info.middle_pressed or mouse_info.right_pressed or mouse_info.scroll_up_pressed or mouse_info.scroll_down_pressed):
			self.__pressed__ = True

			if callable(mouse_press):
				mouse_press(self, mouse_info)
			if callable(self.__general_callback__):
				self.__general_callback__(self, 'mouse_press', mouse_info)
		elif mouse_inside and self.__pressed__ and (mouse_info.left_released or mouse_info.middle_released or mouse_info.right_released or mouse_info.scroll_up_released or mouse_info.scroll_down_released):
			self.__pressed__ = False
			scrolled: bool = mouse_info.scroll_up_released or mouse_info.scroll_down_released

			if callable(mouse_release):
				mouse_release(self, mouse_info)
			if callable(self.__general_callback__):
				self.__general_callback__(self, 'mouse_release', mouse_info)

			if not scrolled and callable(mouse_click):
				mouse_click(self, mouse_info)
			if not scrolled and callable(self.__general_callback__):
				self.__general_callback__(self, 'mouse_click', mouse_info)

		if mouse_inside and (mouse_info.left_clicked or mouse_info.middle_clicked or mouse_info.right_clicked or mouse_info.scroll_up_clicked or mouse_info.scroll_down_clicked):
			if callable(mouse_click):
				mouse_click(self, mouse_info)
			if callable(self.__general_callback__):
				self.__general_callback__(self, 'mouse_click', mouse_info)

		self.__hovering__ = mouse_over
		self.__hovering_top__ = mouse_inside

	def redraw(self) -> None:
		pass

	def show(self) -> None:
		self.__hidden__ = False

	def hide(self) -> None:
		self.__hidden__ = True

		if self.focused:
			self.parent.set_focus(None)

	def focus(self) -> None:
		if not self.focused:
			self.parent.set_focus(self)

	def unfocus(self) -> None:
		if self.focused:
			self.parent.set_focus(None)

	def draw_border(self, border: BorderInfo | None) -> None:
		if border is None:
			return
		elif not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Widget.draw_border, 'border', type(border), (BorderInfo,))

		width, height = self.size
		self.__terminal__.putstr(border.top * (width - 2), self.__position__[0] + 1, self.__position__[1], width - 2)
		self.__terminal__.putstr(border.bottom * (width - 2), self.__position__[0] + 1, self.__position__[1] + height - 1, width - 2)

		for i in range(1, height - 1):
			self.__terminal__.putstr(border.left, self.__position__[0], self.__position__[1] + i, 1)
			self.__terminal__.putstr(border.right, self.__position__[0] + width - 1, self.__position__[1] + i, 1)

		self.__terminal__.putstr(border.top_left, self.__position__[0], self.__position__[1], 1)
		self.__terminal__.putstr(border.top_right, self.__position__[0] + width - 1, self.__position__[1], 1)
		self.__terminal__.putstr(border.bottom_left, self.__position__[0], self.__position__[1] + height - 1, 1)
		self.__terminal__.putstr(border.bottom_right, self.__position__[0] + width - 1, self.__position__[1] + height - 1, 1)

	def has_coord(self, x: int, y: int) -> bool:
		cx, cy, _, w, h = self.__position__
		return cx <= x < cx + w and cy <= y < cy + h

	def parent_stack(self) -> tuple[SubTerminal | Terminal.Terminal]:
		parents: list[SubTerminal | Terminal.Terminal] = [self.__terminal__]

		while isinstance(parents[-1], SubTerminal):
			parents.append(parents[-1].parent)

		return tuple(parents)

	def topmost_parent(self) -> Terminal.Terminal:
		parent: Terminal.Terminal | SubTerminal = self.__terminal__

		while isinstance(parent, SubTerminal):
			parent = parent.parent

		return parent

	def global_pos(self) -> tuple[int, int]:
		x = self.x
		y = self.y

		for parent in self.parent_stack():
			if isinstance(parent, SubTerminal):
				x += parent.x
				y += parent.y

		return x, y

	@property
	def closed(self) -> bool:
		return self.__closed__

	@property
	def hidden(self) -> bool:
		return self.__hidden__

	@property
	def id(self) -> int:
		return id(self)

	@property
	def x(self) -> int:
		return self.__position__[0]

	@property
	def y(self) -> int:
		return self.__position__[1]

	@property
	def width(self) -> int:
		return self.__position__[3]

	@property
	def height(self) -> int:
		return self.__position__[4]

	@property
	def z_index(self) -> int:
		return self.__position__[2]

	@property
	def position(self) -> tuple[int, int]:
		return self.__position__[0], self.__position__[1]

	@property
	def size(self) -> tuple[int, int]:
		return self.__position__[3], self.__position__[4]

	@property
	def parent(self) -> Terminal.Terminal | SubTerminal:
		return self.__terminal__

	@property
	def is_mouse_pressed(self) -> bool:
		return self.__pressed__

	@property
	def is_mouse_over(self) -> bool:
		return self.__hovering__

	@property
	def is_mouse_inside(self) -> bool:
		return self.__hovering_top__

	@property
	def focused(self) -> bool:
		return self.__focused__


class Button(Widget):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, width: int, height: int, text: str | AnsiStr, *, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_NONE,
				 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'active_border', type(active_border), (BorderInfo,))

		if width <= 2 or height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		color_bg = parse_color(color_bg, InvalidArgumentException(Button.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = parse_color(highlight_color_bg, InvalidArgumentException(Button.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = parse_color(active_color_bg, InvalidArgumentException(Button.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = parse_color(color_fg, InvalidArgumentException(Button.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = parse_color(highlight_color_fg, InvalidArgumentException(Button.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = parse_color(active_color_fg, InvalidArgumentException(Button.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		border = None if border is None else BorderInfo('', ']', '', '[', '', '', '', '') if border is ... and height == 1 else BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		super().__init__(parent, x, y, z_index, width, height,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__text__: AnsiStr = AnsiStr(text)
		self.__justify__: int = int(justify)
		self.__word_wrap__: int = int(word_wrap)
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)

	def __draw1(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb

		if border is not None:
			self.__terminal__.putstr(border.left, self.x, self.y, 1)
			self.__terminal__.putstr(border.right, self.x + self.width - 1, self.y, 1)

		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)

		if (self.__justify__ & Enums.EAST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif (self.__justify__ & Enums.WEST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Enums.CENTER or self.__justify__ == Enums.NORTH or self.__justify__ == Enums.SOUTH:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw2(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		self.draw_border(border)
		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + 1)

		if self.__justify__ == Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif self.__justify__ == Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.WEST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + delta + i, self.width - 2)

		elif self.__justify__ == Enums.EAST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + delta + i, self.width - 2)

		elif self.__justify__ == Enums.CENTER:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw3(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		self.draw_border(border)
		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2, self.height - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		for i in range(1, self.height - 1):
			self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + i)

		if self.__justify__ == Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.WEST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Enums.EAST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Enums.CENTER:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + 1 + delta + i, self.width - 2)

	def __draw(self, mode: int) -> None:
		height: int = self.size[1]

		if height == 1:
			self.__draw1(mode)
		elif height == 2:
			self.__draw2(mode)
		else:
			self.__draw3(mode)

	def draw(self) -> None:
		super().draw()
		self.__draw(2 if self.is_mouse_pressed else 1 if self.is_mouse_inside else 0)

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  text: str | AnsiStr = None, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_WORD,
				  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:
		super().configure(x=x, y=y, z=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		border = self.__border__[0] if border is ... or border is None else border
		highlight_border = self.__border__[1] if highlight_border is ... or highlight_border is None else highlight_border
		active_border = self.__border__[2] if active_border is ... or active_border is None else active_border

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'active_border', type(active_border), (BorderInfo,))

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		color_bg = self.__bg_color__[0] if color_bg is ... or color_bg is None else parse_color(color_bg, InvalidArgumentException(Button.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = self.__bg_color__[1] if highlight_color_bg is ... or highlight_color_bg is None else parse_color(highlight_color_bg, InvalidArgumentException(Button.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = self.__bg_color__[2] if active_color_bg is ... or active_color_bg is None else parse_color(active_color_bg, InvalidArgumentException(Button.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = self.__bg_color__[0] if color_fg is ... or color_fg is None else parse_color(color_fg, InvalidArgumentException(Button.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = self.__bg_color__[1] if highlight_color_fg is ... or highlight_color_fg is None else parse_color(highlight_color_fg, InvalidArgumentException(Button.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = self.__bg_color__[2] if active_color_fg is ... or active_color_fg is None else parse_color(active_color_fg, InvalidArgumentException(Button.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		border = None if border is None else BorderInfo('', ']', '', '[', '', '', '', '') if border is ... and height == 1 else BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		self.__text__: AnsiStr = self.__text__ if text is ... or text is None else AnsiStr(text)
		self.__justify__: int = int(justify)
		self.__word_wrap__: int = self.__word_wrap__ if word_wrap is ... or word_wrap is None else int(word_wrap)
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)

	@property
	def text(self) -> AnsiStr:
		return AnsiStr(self.__text__)

	@property
	def justify(self) -> int:
		return self.__justify__

	@property
	def fg_color(self) -> Color:
		return self.__fg_color__[0]

	@property
	def highlight_fg_color(self) -> Color:
		return self.__fg_color__[1]

	@property
	def active_fg_color(self) -> Color:
		return self.__fg_color__[2]

	@property
	def bg_color(self) -> Color:
		return self.__bg_color__[0]

	@property
	def highlight_bg_color(self) -> Color:
		return self.__bg_color__[1]

	@property
	def active_bg_color(self) -> Color:
		return self.__bg_color__[2]

	@property
	def border(self) -> BorderInfo:
		return self.__border__[0]

	@property
	def highlight_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def active_border(self) -> BorderInfo:
		return self.__border__[1]


class ToggleButton(Button):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, width: int, height: int, text: str | AnsiStr, *, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_NONE,
				 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):
		super().__init__(parent, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__state__: bool = False

	def __draw1(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb

		if border is not None:
			self.__terminal__.putstr(border.left, self.x, self.y, 1)
			self.__terminal__.putstr(border.right, self.x + self.width - 1, self.y, 1)

		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)

		if (self.__justify__ & Enums.EAST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif (self.__justify__ & Enums.WEST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Enums.CENTER or self.__justify__ == Enums.NORTH or self.__justify__ == Enums.SOUTH:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw2(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		self.draw_border(border)
		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + 1)

		if self.__justify__ == Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif self.__justify__ == Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.WEST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + delta + i, self.width - 2)

		elif self.__justify__ == Enums.EAST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + delta + i, self.width - 2)

		elif self.__justify__ == Enums.CENTER:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw3(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		self.draw_border(border)
		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2, self.height - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		for i in range(1, self.height - 1):
			self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + i)

		if self.__justify__ == Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.WEST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Enums.EAST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Enums.CENTER:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + 1 + delta + i, self.width - 2)

	def __draw(self, mode: int) -> None:
		height: int = self.size[1]

		if height == 1:
			self.__draw1(mode)
		elif height == 2:
			self.__draw2(mode)
		else:
			self.__draw3(mode)

	def draw(self) -> None:
		super().draw()
		mouse_info: MouseInfo = self.__terminal__.mouse
		self.__draw(2 if self.is_mouse_pressed else 1 if self.is_mouse_inside else 0)
		self.__state__ = not self.__state__ if self.is_mouse_inside and (mouse_info.left_released or mouse_info.left_clicked) else self.__state__

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  text: str | AnsiStr = None, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_WORD,
				  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:
		super().configure(x=x, y=y, z_index=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close,
						  text=text, justify=justify, word_wrap=word_wrap, border=border, highlight_border=highlight_border, active_border=active_border, color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg)

	@property
	def text(self) -> AnsiStr:
		return AnsiStr(self.__text__)

	@property
	def justify(self) -> int:
		return self.__justify__

	@property
	def fg_color(self) -> Color:
		return self.__fg_color__[0]

	@property
	def highlight_fg_color(self) -> Color:
		return self.__fg_color__[1]

	@property
	def active_fg_color(self) -> Color:
		return self.__fg_color__[2]

	@property
	def bg_color(self) -> Color:
		return self.__bg_color__[0]

	@property
	def highlight_bg_color(self) -> Color:
		return self.__bg_color__[1]

	@property
	def active_bg_color(self) -> Color:
		return self.__bg_color__[2]

	@property
	def border(self) -> BorderInfo:
		return self.__border__[0]

	@property
	def highlight_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def active_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def toggled(self) -> bool:
		return self.__state__

	@toggled.setter
	def toggled(self, state: bool) -> None:
		self.__state__ = bool(state)


class Checkbox(Widget):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, *, z_index: int = 0, text: str | AnsiStr = '', active_text: str | AnsiStr = 'X',
				 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Checkbox.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Checkbox.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Checkbox.__init__, 'active_border', type(active_border), (BorderInfo,))

		text: AnsiStr = AnsiStr(text)
		active_text: AnsiStr = AnsiStr(active_text)

		if len(text) > 1:
			raise ValueError('Text must be an empty string or single character')

		if len(active_text) > 1:
			raise ValueError('Text must be an empty string or single character')

		color_bg = parse_color(color_bg, InvalidArgumentException(Checkbox.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = parse_color(highlight_color_bg, InvalidArgumentException(Checkbox.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = parse_color(active_color_bg, InvalidArgumentException(Checkbox.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = parse_color(color_fg, InvalidArgumentException(Checkbox.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = parse_color(highlight_color_fg, InvalidArgumentException(Checkbox.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = parse_color(active_color_fg, InvalidArgumentException(Checkbox.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		border = None if border is None else BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		super().__init__(parent, x, y, z_index, 3, 3,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__text__: tuple[AnsiStr, AnsiStr] = (text, active_text)
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)
		self.__state__: bool = False

	def draw(self) -> None:
		super().draw()
		mouse_info: MouseInfo = self.__terminal__.mouse
		text: str | AnsiStr = ' ' if len(self.__text__[self.__state__]) == 0 else self.__text__[self.__state__]
		bg_color_index: int = 1 if self.is_mouse_inside else 2 if self.__state__ else 0
		fg_color_index: int = 1 if self.is_mouse_inside else 2 if self.__state__ else 0
		bg_color: Color = self.__bg_color__[bg_color_index]
		fg_color: Color = self.__fg_color__[fg_color_index]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		while bg_color is None and bg_color_index > 0:
			bg_color_index -= 1
			bg_color = self.__bg_color__[bg_color_index]

		if bg_color is None:
			bg_color = self.parent.default_bg

		while fg_color is None and fg_color_index > 0:
			fg_color_index -= 1
			fg_color = self.__fg_color__[fg_color_index]

		if fg_color is None:
			fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb

		self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if not self.is_mouse_inside or (null_bg_color and null_fg_color) else ";7"}m{text}', self.x + 1, self.y + 1, 1)
		self.draw_border(self.__border__[self.is_mouse_inside])
		self.__state__ = not self.__state__ if self.is_mouse_inside and (mouse_info.left_released or mouse_info.left_clicked) else self.__state__

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  text: str | AnsiStr = None, active_text: str | AnsiStr = None,
				  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:
		super().configure(x=x, y=y, z=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		border = self.__border__[0] if border is ... else border
		highlight_border = self.__border__[1] if highlight_border is ... else highlight_border
		active_border = self.__border__[2] if active_border is ... else active_border

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'active_border', type(active_border), (BorderInfo,))

		text: AnsiStr = AnsiStr(text)
		active_text: AnsiStr = AnsiStr(active_text)

		if text is ... or text is None:
			text = self.__text__[0]
		else:
			if len(text) > 1:
				raise ValueError('Text must be an empty string or single character')

		if active_text is ... or active_text is None:
			active_text = self.__text__[1]
		else:
			if len(active_text) > 1:
				raise ValueError('Text must be an empty string or single character')

		color_bg = self.__bg_color__[0] if color_bg is ... else parse_color(color_bg, InvalidArgumentException(Button.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = self.__bg_color__[1] if highlight_color_bg is ... else parse_color(highlight_color_bg, InvalidArgumentException(Button.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = self.__bg_color__[2] if active_color_bg is ... else parse_color(active_color_bg, InvalidArgumentException(Button.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = self.__bg_color__[0] if color_fg is ... else parse_color(color_fg, InvalidArgumentException(Button.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = self.__bg_color__[1] if highlight_color_fg is ... else parse_color(highlight_color_fg, InvalidArgumentException(Button.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = self.__bg_color__[2] if active_color_fg is ... else parse_color(active_color_fg, InvalidArgumentException(Button.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		border = self.__border__[0] if border is ... else None if border is None else border
		highlight_border = self.__border__[1] if highlight_border is ... else None if highlight_border is None else highlight_border
		active_border = self.__border__[2] if active_border is ... else None if active_border is None else active_border

		self.__text__: tuple[AnsiStr, AnsiStr] = (text, active_text)
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)

	@property
	def text(self) -> AnsiStr:
		return AnsiStr(self.__text__[0])

	@property
	def active_text(self) -> AnsiStr:
		return AnsiStr(self.__text__[1])

	@property
	def fg_color(self) -> Color:
		return self.__fg_color__[0]

	@property
	def highlight_fg_color(self) -> Color:
		return self.__fg_color__[1]

	@property
	def active_fg_color(self) -> Color:
		return self.__fg_color__[2]

	@property
	def bg_color(self) -> Color:
		return self.__bg_color__[0]

	@property
	def highlight_bg_color(self) -> Color:
		return self.__bg_color__[1]

	@property
	def active_bg_color(self) -> Color:
		return self.__bg_color__[2]

	@property
	def border(self) -> BorderInfo:
		return self.__border__[0]

	@property
	def highlight_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def active_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def checked(self) -> bool:
		return self.__state__

	@checked.setter
	def checked(self, checked: bool) -> None:
		self.__state__ = bool(checked)


class InlineCheckbox(Widget):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, *, z_index: int = 0, text: str | AnsiStr = '', active_text: str | AnsiStr = 'X',
				 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Checkbox.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Checkbox.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Checkbox.__init__, 'active_border', type(active_border), (BorderInfo,))

		text: AnsiStr = AnsiStr(text)
		active_text: AnsiStr = AnsiStr(active_text)

		if len(text) > 1:
			raise ValueError('Text must be an empty string or single character')

		if len(active_text) > 1:
			raise ValueError('Text must be an empty string or single character')

		color_bg = parse_color(color_bg, InvalidArgumentException(InlineCheckbox.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = parse_color(highlight_color_bg, InvalidArgumentException(InlineCheckbox.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = parse_color(active_color_bg, InvalidArgumentException(InlineCheckbox.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = parse_color(color_fg, InvalidArgumentException(InlineCheckbox.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = parse_color(highlight_color_fg, InvalidArgumentException(InlineCheckbox.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = parse_color(active_color_fg, InvalidArgumentException(InlineCheckbox.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		border = None if border is None else BorderInfo('', ']', '', '[', '', '', '', '') if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... else active_border

		super().__init__(parent, x, y, z_index, 3, 1,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__text__: tuple[AnsiStr, AnsiStr] = (text, active_text)
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)
		self.__state__: bool = False
		self.__state__: bool = False

	def draw(self) -> None:
		super().draw()
		mouse_info: MouseInfo = self.__terminal__.mouse
		text: str | AnsiStr = ' ' if len(self.__text__[self.__state__]) == 0 else self.__text__[self.__state__]
		bg_color_index: int = 1 if self.is_mouse_inside else 2 if self.__state__ else 0
		fg_color_index: int = 1 if self.is_mouse_inside else 2 if self.__state__ else 0
		bg_color: Color = self.__bg_color__[bg_color_index]
		fg_color: Color = self.__fg_color__[fg_color_index]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		while bg_color is None and bg_color_index > 0:
			bg_color_index -= 1
			bg_color = self.__bg_color__[bg_color_index]

		if bg_color is None:
			bg_color = self.parent.default_bg

		while fg_color is None and fg_color_index > 0:
			fg_color_index -= 1
			fg_color = self.__fg_color__[fg_color_index]

		if fg_color is None:
			fg_color = self.parent.default_fg

		border: BorderInfo = self.__border__[2 if self.is_mouse_pressed else 1 if self.is_mouse_inside else 0]
		self.__terminal__.putstr(border.left, self.x, self.y)
		self.__terminal__.putstr(border.right, self.x + 2, self.y)
		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if not self.is_mouse_inside or (null_bg_color and null_fg_color) else ";7"}m{text}', self.x + 1, self.y)
		self.__state__ = not self.__state__ if self.is_mouse_inside and (mouse_info.left_released or mouse_info.left_clicked) else self.__state__

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  text: str | AnsiStr = None, active_text: str | AnsiStr = None,
				  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:
		super().configure(x=x, y=y, z=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		border = self.__border__[0] if border is ... else border
		highlight_border = self.__border__[1] if highlight_border is ... else highlight_border
		active_border = self.__border__[2] if active_border is ... else active_border

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'active_border', type(active_border), (BorderInfo,))

		text: AnsiStr = AnsiStr(text)
		active_text: AnsiStr = AnsiStr(active_text)

		if text is ... or text is None:
			text = self.__text__[0]
		else:
			if len(text) > 1:
				raise ValueError('Text must be an empty string or single character')

		if active_text is ... or active_text is None:
			active_text = self.__text__[1]
		else:
			if len(active_text) > 1:
				raise ValueError('Text must be an empty string or single character')

		color_bg = self.__bg_color__[0] if color_bg is ... else parse_color(color_bg, InvalidArgumentException(Button.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = self.__bg_color__[1] if highlight_color_bg is ... else parse_color(highlight_color_bg, InvalidArgumentException(Button.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = self.__bg_color__[2] if active_color_bg is ... else parse_color(active_color_bg, InvalidArgumentException(Button.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = self.__bg_color__[0] if color_fg is ... else parse_color(color_fg, InvalidArgumentException(Button.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = self.__bg_color__[1] if highlight_color_fg is ... else parse_color(highlight_color_fg, InvalidArgumentException(Button.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = self.__bg_color__[2] if active_color_fg is ... else parse_color(active_color_fg, InvalidArgumentException(Button.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		border = self.__border__[0] if border is ... else None if border is None else border
		highlight_border = self.__border__[1] if highlight_border is ... else None if highlight_border is None else highlight_border
		active_border = self.__border__[2] if active_border is ... else None if active_border is None else active_border

		self.__text__: tuple[AnsiStr, AnsiStr] = (text, active_text)
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)

	@property
	def text(self) -> AnsiStr:
		return AnsiStr(self.__text__[0])

	@property
	def active_text(self) -> AnsiStr:
		return AnsiStr(self.__text__[1])

	@property
	def fg_color(self) -> Color:
		return self.__fg_color__[0]

	@property
	def highlight_fg_color(self) -> Color:
		return self.__fg_color__[1]

	@property
	def active_fg_color(self) -> Color:
		return self.__fg_color__[2]

	@property
	def bg_color(self) -> Color:
		return self.__bg_color__[0]

	@property
	def highlight_bg_color(self) -> Color:
		return self.__bg_color__[1]

	@property
	def active_bg_color(self) -> Color:
		return self.__bg_color__[2]

	@property
	def border(self) -> BorderInfo:
		return self.__border__[0]

	@property
	def highlight_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def active_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def checked(self) -> bool:
		return self.__state__

	@checked.setter
	def checked(self, checked: bool) -> None:
		self.__state__ = bool(checked)


class RadialSpinner(Widget):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, *, z_index: int = 0, phases: typing.Iterable[str | AnsiStr] = ('--', '\\', '|', '/'), bg_phase_colors: typing.Optional[Enums.Color_T] | typing.Iterable[typing.Optional[Enums.Color_T]] = Color(0xFFFFFF), fg_phase_colors: typing.Optional[Enums.Color_T] | typing.Iterable[typing.Optional[Enums.Color_T]] = Color(0xFFFFFF),
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):
		super().__init__(parent, x, y, z_index, 1, 1,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__phases__: tuple[AnsiStr, ...] = tuple(AnsiStr(x) for x in phases)
		self.__spin__: int = 0
		self.__spin_mod__: int = 0
		self.__last_frame__: int = 0

		bg_phase_color: Color = parse_color(bg_phase_colors)
		fg_phase_color: Color = parse_color(fg_phase_colors)
		root: Terminal.Terminal = self.topmost_parent()

		if bg_phase_color is None and hasattr(bg_phase_colors, '__iter__'):
			self.__bg_colors__: tuple[Color, ...] = tuple(parse_color(color, InvalidArgumentException(RadialSpinner.__init__, 'bg_phase_colors[i]', type(color), (Color,))) for i, color in enumerate(bg_phase_colors))
		elif bg_phase_colors is ... or bg_phase_colors is None:
			self.__bg_colors__: tuple[Color, ...] = (root.default_bg,)
		elif bg_phase_color is None:
			raise InvalidArgumentException(RadialSpinner.__init__, 'bg_phase_colors', type(bg_phase_colors), (Color,))
		else:
			self.__bg_colors__: tuple[Color, ...] = (bg_phase_color,)

		if fg_phase_color is None and hasattr(fg_phase_colors, '__iter__'):
			self.__fg_colors__: tuple[Color, ...] = tuple(parse_color(color, InvalidArgumentException(RadialSpinner.__init__, 'fg_phase_colors[i]', type(color), (Color,))) for i, color in enumerate(fg_phase_colors))
		elif fg_phase_colors is ... or fg_phase_colors is None:
			self.__fg_colors__: tuple[Color, ...] = (root.default_fg,)
		elif fg_phase_color is None:
			raise InvalidArgumentException(RadialSpinner.__init__, 'fg_phase_colors', type(fg_phase_colors), (Color,))
		else:
			self.__fg_colors__: tuple[Color, ...] = (fg_phase_color,)

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  phases: typing.Iterable[str | AnsiStr] = ..., bg_phase_colors: typing.Optional[Enums.Color_T] | typing.Iterable[typing.Optional[Enums.Color_T]] = ..., fg_phase_colors: typing.Optional[Enums.Color_T] | typing.Iterable[typing.Optional[Enums.Color_T]] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:
		super().configure(x=x, y=y, z=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__phases__: tuple[AnsiStr, ...] = self.__phases__ if phases is ... or phases is None else tuple(AnsiStr(x) for x in phases)
		root: Terminal.Terminal = self.topmost_parent()

		if self.__bg_colors__ is not None and self.__bg_colors__ is not ...:
			bg_phase_color: Color = parse_color(bg_phase_colors)

			if bg_phase_color is None and hasattr(bg_phase_colors, '__iter__'):
				self.__bg_colors__: tuple[Color, ...] = tuple(parse_color(color, InvalidArgumentException(RadialSpinner.__init__, 'bg_phase_colors[i]', type(color), (Color,))) for i, color in enumerate(bg_phase_colors))
			elif bg_phase_colors is ... or bg_phase_colors is None:
				self.__bg_colors__: tuple[Color, ...] = (root.default_bg,)
			elif bg_phase_color is None:
				raise InvalidArgumentException(RadialSpinner.__init__, 'bg_phase_colors', type(bg_phase_colors), (Color,))
			else:
				self.__bg_colors__: tuple[Color, ...] = (bg_phase_color,)

		if self.__bg_colors__ is not None and self.__bg_colors__ is not ...:
			fg_phase_color: Color = parse_color(fg_phase_colors)
			if fg_phase_color is None and hasattr(fg_phase_colors, '__iter__'):
				self.__fg_colors__: tuple[Color, ...] = tuple(parse_color(color, InvalidArgumentException(RadialSpinner.__init__, 'fg_phase_colors[i]', type(color), (Color,))) for i, color in enumerate(fg_phase_colors))
			elif fg_phase_colors is ... or fg_phase_colors is None:
				self.__fg_colors__: tuple[Color, ...] = (root.default_fg,)
			elif fg_phase_color is None:
				raise InvalidArgumentException(RadialSpinner.__init__, 'fg_phase_colors', type(fg_phase_colors), (Color,))
			else:
				self.__fg_colors__: tuple[Color, ...] = (fg_phase_color,)

	@property
	def fg_colors(self) -> tuple[Color, ...]:
		return self.__fg_colors__

	@property
	def bg_colors(self) -> tuple[Color, ...]:
		return self.__bg_colors__

	@property
	def phases(self) -> tuple[AnsiStr, ...]:
		return self.__phases__

	def draw(self) -> None:
		super().draw()
		max_spin: int = self.__spin_mod__ * len(self.__phases__)
		spin_ratio: float = self.__spin__ / max_spin
		frame: int = self.__last_frame__ if self.__spin_mod__ == 0 else (self.__spin__ // self.__spin_mod__)
		index: int = frame % len(self.__phases__)
		symbol: AnsiStr = self.__phases__[index]

		if len(self.__bg_colors__):
			color_index: int = round(spin_ratio * (len(self.__bg_colors__) - 1))
			bg_color: Color = self.__bg_colors__[color_index]
		else:
			bg_color: Color = self.parent.default_bg

		if len(self.__fg_colors__):
			color_index: int = round(spin_ratio * (len(self.__fg_colors__) - 1))
			fg_color: Color = self.__fg_colors__[color_index]
		else:
			fg_color: Color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb

		self.__last_frame__ = frame
		self.__spin__ = 0 if self.__spin__ >= max_spin else self.__spin__ + 1
		self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}m{symbol}', self.x, self.y)

	def spin(self, tick_rate: int) -> None:
		self.__spin_mod__ = max(0, tick_rate)


class HorizontalSlider(Widget):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, width: int, height: int, *, z_index: int = 0, step: float = 1, fill_char: str | AnsiStr = '|', _max: float = 10, _min: float = 0, on_input: typing.Optional[typing.Callable[[HorizontalSlider], None]] = ...,
				 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(HorizontalSlider.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(HorizontalSlider.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(HorizontalSlider.__init__, 'active_border', type(active_border), (BorderInfo,))

		if width <= 2 or height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		color_bg = parse_color(color_bg, InvalidArgumentException(HorizontalSlider.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = parse_color(highlight_color_bg, InvalidArgumentException(HorizontalSlider.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = parse_color(active_color_bg, InvalidArgumentException(HorizontalSlider.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = parse_color(color_fg, InvalidArgumentException(HorizontalSlider.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = parse_color(highlight_color_fg, InvalidArgumentException(HorizontalSlider.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = parse_color(active_color_fg, InvalidArgumentException(HorizontalSlider.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		border = None if border is None else BorderInfo('', ']', '', '[', '', '', '', '') if border is ... and height == 1 else BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		super().__init__(parent, x, y, z_index, width, height,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__fill_char__: AnsiStr = AnsiStr(fill_char)[0]
		self.__range__: tuple[float, float, float] = (float(_min), float(_max), float(step))
		self.__value__: float = 0
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)
		self.__callback__: typing.Callable[[HorizontalSlider], None] = on_input

	def __draw1(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb

		if border is not None:
			self.__terminal__.putstr(border.left, self.x, self.y, 1)
			self.__terminal__.putstr(border.right, self.x + self.width - 1, self.y, 1)

		percent: float = self.percentage
		_min: int = 0
		_max: int = self.width - 2
		lx: int = round((_max - _min) * percent + _min)
		fill: str = f'{self.__fill_char__ * lx}{" " * (_max - lx)}'
		self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}m{fill}', self.x + 1, self.y)

	def __draw2(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		self.draw_border(border)
		percent: float = self.percentage
		_min: int = 0
		_max: int = self.width - 2
		lx: int = round((_max - _min) * percent + _min)
		fill: str = f'{self.__fill_char__ * lx}{" " * (_max - lx)}'

		for y in range(self.y, self.y + self.height):
			self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}m{fill}', self.x + 1, y)

	def __draw3(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb

		for i in range(1, self.height - 1):
			self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_fg_color and null_bg_color) else ";7"}m{" " * (self.width - 2)}', self.x + 1, self.y + i)

		percent: float = self.percentage
		_min: int = 0
		_max: int = self.width - 2
		lx: int = round((_max - _min) * percent + _min)
		fill: str = f'{self.__fill_char__ * lx}{" " * (_max - lx)}'

		for y in range(self.y + 1, self.y + self.height):
			self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}m{fill}', self.x + 1, y)

		self.draw_border(border)

	def __draw__(self, mode: int) -> None:
		height: int = self.size[1]

		if height == 1:
			self.__draw1(mode)
		elif height == 2:
			self.__draw2(mode)
		else:
			self.__draw3(mode)

	def draw(self) -> None:
		super().draw()
		mouse_info: MouseInfo = self.__terminal__.mouse

		if self.is_mouse_inside:
			if mouse_info.left_pressed:
				self.__draw__(2)
			else:
				if mouse_info.left_released:
					_min: int = self.x
					_max: int = self.x + self.width - 2
					percent: float = (mouse_info.pos_x - _min) / (_max - _min)
					self.percentage = 0 if percent < 0 else 1 if percent > 1 else percent

					if callable(self.__callback__):
						self.__callback__(self)
					if callable(self.__general_callback__):
						self.__general_callback__(self, 'input')

				elif mouse_info.scroll_up_pressed:
					_min, _max, step = self.__range__
					value = self.__value__ + step
					self.__value__ = _min if value < _min else _max if value > _max else value

					if callable(self.__callback__):
						self.__callback__(self)
					if callable(self.__general_callback__):
						self.__general_callback__(self, 'input')

				elif mouse_info.scroll_down_pressed:
					_min, _max, step = self.__range__
					value = self.__value__ - step
					self.__value__ = _min if value < _min else _max if value > _max else value

					if callable(self.__callback__):
						self.__callback__(self)
					if callable(self.__general_callback__):
						self.__general_callback__(self, 'input')

				self.__draw__(1)
		else:
			self.__draw__(0)

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  step: float = 1, fill_char: str | AnsiStr = '|', _max: float = 10, _min: float = 0, on_input: typing.Optional[typing.Callable[[HorizontalSlider], None]] = ...,
				  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:
		super().configure(x=x, y=y, z=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		border = self.__border__[0] if border is ... else border
		highlight_border = self.__border__[1] if highlight_border is ... else highlight_border
		active_border = self.__border__[2] if active_border is ... else active_border

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'active_border', type(active_border), (BorderInfo,))

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		color_bg = self.__bg_color__[0] if color_bg is ... else parse_color(color_bg, InvalidArgumentException(Button.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = self.__bg_color__[1] if highlight_color_bg is ... else parse_color(highlight_color_bg, InvalidArgumentException(Button.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = self.__bg_color__[2] if active_color_bg is ... else parse_color(active_color_bg, InvalidArgumentException(Button.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = self.__bg_color__[0] if color_fg is ... else parse_color(color_fg, InvalidArgumentException(Button.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = self.__bg_color__[1] if highlight_color_fg is ... else parse_color(highlight_color_fg, InvalidArgumentException(Button.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = self.__bg_color__[2] if active_color_fg is ... else parse_color(active_color_fg, InvalidArgumentException(Button.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		_min = self.__range__[0] if _min is ... or _min is None else float(_min)
		_max = self.__range__[1] if _max is ... or _max is None else float(_max)
		step = self.__range__[2] if step is ... or step is None else float(step)

		self.__fill_char__: AnsiStr = self.__fill_char__ if fill_char is ... or fill_char is None else AnsiStr(fill_char)[0]
		self.__range__: tuple[float, float, float] = (_min, _max, step)
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)

	@property
	def min(self) -> float:
		return self.__range__[0]

	@property
	def max(self) -> float:
		return self.__range__[1]

	@property
	def step(self) -> float:
		return self.__range__[2]

	@property
	def fill(self) -> AnsiStr:
		return self.__fill_char__

	@property
	def fg_color(self) -> Color:
		return self.__fg_color__[0]

	@property
	def highlight_fg_color(self) -> Color:
		return self.__fg_color__[1]

	@property
	def active_fg_color(self) -> Color:
		return self.__fg_color__[2]

	@property
	def bg_color(self) -> Color:
		return self.__bg_color__[0]

	@property
	def highlight_bg_color(self) -> Color:
		return self.__bg_color__[1]

	@property
	def active_bg_color(self) -> Color:
		return self.__bg_color__[2]

	@property
	def border(self) -> BorderInfo:
		return self.__border__[0]

	@property
	def highlight_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def active_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def value(self) -> float:
		return self.__value__

	@value.setter
	def value(self, value: float) -> None:
		value = float(value)
		assert self.__range__[0] <= value <= self.__range__[1]
		self.__value__ = value

	@property
	def percentage(self) -> float:
		_min, _max, _ = self.__range__
		return (self.__value__ - _min) / (_max - _min)

	@percentage.setter
	def percentage(self, percent: float) -> None:
		percent = float(percent)
		assert 0 <= percent <= 1
		_min, _max, _ = self.__range__
		self.__value__ = (_max - _min) * percent + _min


class VerticalSlider(Widget):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, width: int, height: int, *, z_index: int = 0, step: float = 1, fill_char: str | AnsiStr = '=', _max: float = 10, _min: float = 0, on_input: typing.Optional[typing.Callable[[VerticalSlider], None]] = ...,
				 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(HorizontalSlider.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(HorizontalSlider.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(HorizontalSlider.__init__, 'active_border', type(active_border), (BorderInfo,))

		if width < 1 or height <= 2:
			raise ValueError('Dimensions too small (width >= 1; height > 2)')

		color_bg = parse_color(color_bg, InvalidArgumentException(VerticalSlider.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = parse_color(highlight_color_bg, InvalidArgumentException(VerticalSlider.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = parse_color(active_color_bg, InvalidArgumentException(VerticalSlider.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = parse_color(color_fg, InvalidArgumentException(VerticalSlider.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = parse_color(highlight_color_fg, InvalidArgumentException(VerticalSlider.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = parse_color(active_color_fg, InvalidArgumentException(VerticalSlider.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		border = None if border is None else BorderInfo('┴', '', '┬', '', '', '', '', '') if border is ... and width == 1 else BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('╩', '', '╦', '', '', '', '', '') if highlight_border is ... and width == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('╩', '', '╦', '', '', '', '', '') if active_border is ... and width == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		super().__init__(parent, x, y, z_index, width, height,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__fill_char__: AnsiStr = AnsiStr(fill_char)[0]
		self.__range__: tuple[float, float, float] = (float(_min), float(_max), float(step))
		self.__value__: float = 0
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)
		self.__callback__: typing.Callable[[VerticalSlider], None] = on_input

	def __draw1(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb

		if border is not None:
			self.__terminal__.putstr(border.top, self.x, self.y, 1)
			self.__terminal__.putstr(border.bottom, self.x, self.y + self.height - 1, 1)

		percent: float = self.percentage
		_min: int = 0
		_max: int = self.height - 2
		lx: int = round((_max - _min) * percent + _min)
		maxy: int = self.y + 1 + lx

		for y in range(self.y + 1, self.y + 1 + self.height - 2):
			self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}m{self.__fill_char__ if y < maxy else " "}', self.x, y)

	def __draw2(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		self.draw_border(border)
		percent: float = self.percentage
		_min: int = 0
		_max: int = self.height - 2
		lx: int = round((_max - _min) * percent + _min)
		maxy: int = self.y + 1 + lx

		for y in range(self.y + 1, self.y + 1 + self.height - 2):
			fill: str = (self.__fill_char__ if y < maxy else " ") * self.width
			self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}m{fill}', self.x, y)

	def __draw3(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb

		for i in range(1, self.height - 1):
			self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}m{" " * (self.width - 2)}', self.x + 1, self.y + i)

		percent: float = self.percentage
		_min: int = 0
		_max: int = self.height - 2
		lx: int = round((_max - _min) * percent + _min)
		maxy: int = self.y + 1 + lx

		for y in range(self.y + 1, self.y + 1 + lx):
			fill: str = (self.__fill_char__ if y < maxy else " ") * (self.width - 2)
			self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}m{fill}', self.x, y)

		self.draw_border(border)

	def __draw__(self, mode: int) -> None:
		if self.width == 1:
			self.__draw1(mode)
		elif self.width == 2:
			self.__draw2(mode)
		else:
			self.__draw3(mode)

	def draw(self) -> None:
		super().draw()
		mouse_info: MouseInfo = self.__terminal__.mouse

		if self.is_mouse_inside:
			if mouse_info.left_pressed:
				self.__draw__(2)
			else:
				if mouse_info.left_released:
					_min: int = self.y
					_max: int = self.y + self.height - 2
					percent: float = (mouse_info.pos_y - _min) / (_max - _min)
					self.percentage = 0 if percent < 0 else 1 if percent > 1 else percent

					if callable(self.__callback__):
						self.__callback__(self)
					if callable(self.__general_callback__):
						self.__general_callback__(self, 'input')

				elif mouse_info.scroll_up_pressed:
					_min, _max, step = self.__range__
					value = self.__value__ + step
					self.__value__ = _min if value < _min else _max if value > _max else value

					if callable(self.__callback__):
						self.__callback__(self)
					if callable(self.__general_callback__):
						self.__general_callback__(self, 'input')

				elif mouse_info.scroll_down_pressed:
					_min, _max, step = self.__range__
					value = self.__value__ - step
					self.__value__ = _min if value < _min else _max if value > _max else value

					if callable(self.__callback__):
						self.__callback__(self)
					if callable(self.__general_callback__):
						self.__general_callback__(self, 'input')

				self.__draw__(1)
		else:
			self.__draw__(0)

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  step: float = 1, fill_char: str | AnsiStr = '|', _max: float = 10, _min: float = 0, on_input: typing.Optional[typing.Callable[[HorizontalSlider], None]] = ...,
				  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:
		super().configure(x=x, y=y, z=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		border = self.__border__[0] if border is ... else border
		highlight_border = self.__border__[1] if highlight_border is ... else highlight_border
		active_border = self.__border__[2] if active_border is ... else active_border

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'active_border', type(active_border), (BorderInfo,))

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		color_bg = self.__bg_color__[0] if color_bg is ... else parse_color(color_bg, InvalidArgumentException(Button.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = self.__bg_color__[1] if highlight_color_bg is ... else parse_color(highlight_color_bg, InvalidArgumentException(Button.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = self.__bg_color__[2] if active_color_bg is ... else parse_color(active_color_bg, InvalidArgumentException(Button.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = self.__bg_color__[0] if color_fg is ... else parse_color(color_fg, InvalidArgumentException(Button.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = self.__bg_color__[1] if highlight_color_fg is ... else parse_color(highlight_color_fg, InvalidArgumentException(Button.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = self.__bg_color__[2] if active_color_fg is ... else parse_color(active_color_fg, InvalidArgumentException(Button.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		_min = self.__range__[0] if _min is ... or _min is None else float(_min)
		_max = self.__range__[1] if _max is ... or _max is None else float(_max)
		step = self.__range__[2] if step is ... or step is None else float(step)

		self.__fill_char__: AnsiStr = self.__fill_char__ if fill_char is ... or fill_char is None else AnsiStr(fill_char)[0]
		self.__range__: tuple[float, float, float] = (_min, _max, step)
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)

	@property
	def min(self) -> float:
		return self.__range__[0]

	@property
	def max(self) -> float:
		return self.__range__[1]

	@property
	def step(self) -> float:
		return self.__range__[2]

	@property
	def fill(self) -> AnsiStr:
		return self.__fill_char__

	@property
	def fg_color(self) -> Color:
		return self.__fg_color__[0]

	@property
	def highlight_fg_color(self) -> Color:
		return self.__fg_color__[1]

	@property
	def active_fg_color(self) -> Color:
		return self.__fg_color__[2]

	@property
	def bg_color(self) -> Color:
		return self.__bg_color__[0]

	@property
	def highlight_bg_color(self) -> Color:
		return self.__bg_color__[1]

	@property
	def active_bg_color(self) -> Color:
		return self.__bg_color__[2]

	@property
	def border(self) -> BorderInfo:
		return self.__border__[0]

	@property
	def highlight_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def active_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def value(self) -> float:
		return self.__value__

	@value.setter
	def value(self, value: float) -> None:
		value = float(value)
		assert self.__range__[0] <= value <= self.__range__[1]
		self.__value__ = value

	@property
	def percentage(self) -> float:
		_min, _max, _ = self.__range__
		return (self.__value__ - _min) / (_max - _min)

	@percentage.setter
	def percentage(self, percent: float) -> None:
		percent = float(percent)
		assert 0 <= percent <= 1
		_min, _max, _ = self.__range__
		self.__value__ = (_max - _min) * percent + _min


class HorizontalProgressBar(HorizontalSlider):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | AnsiStr = '|', _max: float = 10, _min: float = 0,
				 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):
		super().__init__(parent, x, y, width, height, z_index=z_index, fill_char=fill_char, step=-1, _max=_max, _min=_min,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

	def draw(self) -> None:
		super(HorizontalSlider, self).draw()
		mouse_info: MouseInfo = self.__terminal__.mouse
		is_inside: bool = self.is_mouse_inside
		mode: int = 2 if is_inside and mouse_info.left_pressed else 1 if is_inside else 0
		self.__draw__(mode)


class VerticalProgressBar(VerticalSlider):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | AnsiStr = '=', _max: float = 10, _min: float = 0,
				 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):
		super().__init__(parent, x, y, width, height, z_index=z_index, fill_char=fill_char, step=-1, _max=_max, _min=_min,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

	def draw(self) -> None:
		super(VerticalSlider, self).draw()
		mouse_info: MouseInfo = self.__terminal__.mouse
		is_inside: bool = self.is_mouse_inside
		mode: int = 2 if is_inside and mouse_info.left_pressed else 1 if is_inside else 0
		self.__draw__(mode)


class Text(Widget):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, width: int, height: int, text: str | AnsiStr, *, z_index: int = 0, justify: int = Enums.NORTH_WEST, word_wrap: int = Enums.WORDWRAP_NONE,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):

		text: AnsiStr = AnsiStr(text)
		raw_text: str = text.raw

		color_bg = parse_color(color_bg, InvalidArgumentException(Text.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = parse_color(highlight_color_bg, InvalidArgumentException(Text.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = parse_color(active_color_bg, InvalidArgumentException(Text.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = parse_color(color_fg, InvalidArgumentException(Text.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = parse_color(highlight_color_fg, InvalidArgumentException(Text.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = parse_color(active_color_fg, InvalidArgumentException(Text.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		self.__true_size__: tuple[int, int] = (width, height)

		if width <= 0 and len(raw_text):
			width = max(len(line) for line in raw_text.split('\n'))

		if height <= 0 and len(raw_text):
			height = raw_text.count('\n') + 1

		if width < 1 or height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		super().__init__(parent, x, y, z_index, width, height,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__text__: AnsiStr = text
		self.__justify__: int = int(justify)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)
		self.__word_wrap__: int = int(word_wrap)

	def __draw1(self, mode: int):
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []

		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		if not null_bg_color or not null_fg_color:
			self.__terminal__.putstr(f'{ansi}m{" " * self.width}', self.x, self.y)

		if (self.__justify__ & Enums.EAST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + i, self.width)

		elif (self.__justify__ & Enums.WEST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + i, self.width)

		elif self.__justify__ == Enums.CENTER or self.__justify__ == Enums.NORTH or self.__justify__ == Enums.SOUTH:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width)

	def __draw2(self, mode: int):
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		if not null_bg_color or not null_fg_color:
			self.__terminal__.putstr(f'{ansi}m{" " * self.width}', self.x, self.y)
			self.__terminal__.putstr(f'{ansi}m{" " * self.width}', self.x, self.y + 1)

		if self.__justify__ == Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + i, self.width)

		elif self.__justify__ == Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + i, self.width)

		elif self.__justify__ == Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + i, self.width)

		elif self.__justify__ == Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Enums.WEST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + delta + i, self.width)

		elif self.__justify__ == Enums.EAST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + delta + i, self.width)

		elif self.__justify__ == Enums.CENTER:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width)

	def __draw3(self, mode: int):
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		if not null_bg_color or not null_fg_color:
			for i in range(self.height):
				self.__terminal__.putstr(f'{ansi}m{" " * self.width}', self.x, self.y + i)

		if self.__justify__ == Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + i, self.width)

		elif self.__justify__ == Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + i, self.width)

		elif self.__justify__ == Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + i, self.width)

		elif self.__justify__ == Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Enums.WEST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + delta + i, self.width)

		elif self.__justify__ == Enums.EAST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + delta + i, self.width)

		elif self.__justify__ == Enums.CENTER:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width)

	def __draw(self, mode: int) -> None:
		height: int = self.size[1]

		if height == 1:
			self.__draw1(mode)
		elif height == 2:
			self.__draw2(mode)
		else:
			self.__draw3(mode)

	def draw(self) -> None:
		super().draw()
		self.__draw(2 if self.is_mouse_pressed else 1 if self.is_mouse_inside else 0)

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  text: typing.Optional[str | AnsiStr] = ..., justify: typing.Optional[int] = ..., word_wrap: typing.Optional[int] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:
		text: AnsiStr = self.__text__ if text is None or text is ... else AnsiStr(text)
		raw_text: str = text.raw
		width = self.__true_size__[0] if width is ... or width is None else width
		height = self.__true_size__[1] if height is ... or height is None else height

		if isinstance(width, int) and width <= 0 and len(raw_text):
			width = max(len(line) for line in raw_text.split('\n'))

		if isinstance(height, int) and height <= 0 and len(raw_text):
			height = raw_text.count('\n') + 1

		super().configure(x=x, y=y, z=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		if self.width < 1 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		color_bg = self.__bg_color__[0] if color_bg is ... or color_bg is None else parse_color(color_bg, InvalidArgumentException(Button.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = self.__bg_color__[1] if highlight_color_bg is ... or highlight_color_bg is None else parse_color(highlight_color_bg, InvalidArgumentException(Button.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = self.__bg_color__[2] if active_color_bg is ... or active_color_bg is None else parse_color(active_color_bg, InvalidArgumentException(Button.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = self.__fg_color__[0] if color_fg is ... or color_fg is None else parse_color(color_fg, InvalidArgumentException(Button.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = self.__fg_color__[1] if highlight_color_fg is ... or highlight_color_fg is None else parse_color(highlight_color_fg, InvalidArgumentException(Button.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = self.__fg_color__[2] if active_color_fg is ... or active_color_fg is None else parse_color(active_color_fg, InvalidArgumentException(Button.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		self.__text__: AnsiStr = self.__text__ if text is ... or text is None else AnsiStr(text)
		self.__justify__: int = self.__justify__ if justify is ... or justify is None else int(justify)
		self.__word_wrap__: int = self.__word_wrap__ if word_wrap is ... or word_wrap is None else int(word_wrap)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)

	@property
	def text(self) -> AnsiStr:
		return AnsiStr(self.__text__)

	@property
	def justify(self) -> int:
		return self.__justify__

	@property
	def fg_color(self) -> Color:
		return self.__fg_color__[0]

	@property
	def highlight_fg_color(self) -> Color:
		return self.__fg_color__[1]

	@property
	def active_fg_color(self) -> Color:
		return self.__fg_color__[2]

	@property
	def bg_color(self) -> Color:
		return self.__bg_color__[0]

	@property
	def highlight_bg_color(self) -> Color:
		return self.__bg_color__[1]

	@property
	def active_bg_color(self) -> Color:
		return self.__bg_color__[2]


class Dropdown(Widget):
	class __Option(Button):
		def __init__(self, parent: Terminal.Terminal | SubTerminal, dropdown: Dropdown, x: int, y: int, width: int, height: int, text: str | AnsiStr, *, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_NONE,
					 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
					 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):
			super().__init__(parent, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
							 border=border, highlight_border=highlight_border, active_border=active_border,
							 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
							 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
			self.__dropdown__: Dropdown = dropdown
			self.hide()

	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, width: int, height: int, choices: tuple[str | AnsiStr, ...], *, z_index: int = 0, justify: int = Enums.CENTER,
				 display_count: int | None = None, word_wrap: int = Enums.WORDWRAP_WORD, allow_scroll_rollover: bool = False, on_select: typing.Optional[typing.Callable[[WIDGET_T, bool], bool | None]] = ...,
				 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'active_border', type(active_border), (BorderInfo,))

		if width <= 2 or height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')
		elif len(choices) == 0:
			raise ValueError('Dropbox is empty')

		color_bg = parse_color(color_bg, InvalidArgumentException(Button.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = parse_color(highlight_color_bg, InvalidArgumentException(Button.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = parse_color(active_color_bg, InvalidArgumentException(Button.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = parse_color(color_fg, InvalidArgumentException(Button.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = parse_color(highlight_color_fg, InvalidArgumentException(Button.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = parse_color(active_color_fg, InvalidArgumentException(Button.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		border = None if border is None else BorderInfo('', ']', '', '[', '', '', '', '') if border is ... and height == 1 else BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		super().__init__(parent, x, y, z_index, width, height,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__choices__: tuple[AnsiStr, ...] = tuple(AnsiStr(text) for text in choices)
		self.__options__: tuple[Dropdown.__Option] = tuple(parent.add_widget(Dropdown.__Option, parent, self.x, self.y + (i + 1) * self.height, self.width, self.height, choice, z_index=z_index + 1, justify=justify, word_wrap=word_wrap, border=border, highlight_border=highlight_border, active_border=active_border, color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg, color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg, on_mouse_click=lambda _1, mouse, index=i: self.__select_choice__(index, mouse)) for i, choice in enumerate(self.__choices__))
		self.__option_callback__: typing.Callable[[int, MouseInfo], None] = None
		self.__choice_override__: AnsiStr | None = None
		self.__selected__: int = 0
		self.__ghost_selected__: int = 0
		self.__word_wrap__: int = int(word_wrap)
		self.__scroll_rollover__: bool = bool(allow_scroll_rollover)
		self.__display_count__: int | None = None if display_count is None else max(0, int(display_count))
		self.__justify__: int = int(justify)
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)
		self.__state__: bool = False
		self.__displayed__: bool = False
		self.__on_select__: typing.Callable[[WIDGET_T, bool], bool | None] = on_select
		self.__selection_changed__: bool = False

	def __draw1(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb

		if border is not None:
			self.__terminal__.putstr(border.left, self.x, self.y, 1)
			self.__terminal__.putstr(border.right, self.x + self.width - 1, self.y, 1)

		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.selected, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)

		if (self.__justify__ & Enums.EAST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 1 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif (self.__justify__ & Enums.WEST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Enums.CENTER or self.__justify__ == Enums.NORTH or self.__justify__ == Enums.SOUTH:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw2(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		self.draw_border(border)
		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.selected, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + 1)

		if self.__justify__ == Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif self.__justify__ == Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.WEST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + delta + i, self.width - 2)

		elif self.__justify__ == Enums.EAST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + delta + i, self.width - 2)

		elif self.__justify__ == Enums.CENTER:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw3(self, mode: int):
		border: BorderInfo = self.__border__[mode]
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		self.draw_border(border)
		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.selected, lines, self.__word_wrap__, self.width - 2, self.height - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		for i in range(1, self.height - 1):
			self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + i)

		if self.__justify__ == Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Enums.WEST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Enums.EAST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Enums.CENTER:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + 1 + delta + i, self.width - 2)

	def __draw(self, mode: int) -> None:
		height: int = self.size[1]

		if height == 1:
			self.__draw1(mode)
		elif height == 2:
			self.__draw2(mode)
		else:
			self.__draw3(mode)

	def __select_choice__(self, index: int, mouse: MouseInfo) -> None:
		if callable(self.__option_callback__):
			self.__option_callback__(index, mouse)

		old_selection: int = self.__selected__
		self.__selected__ = (index % len(self.__choices__)) if self.__scroll_rollover__ else min(len(self.__choices__) - 1, index)
		self.__selection_changed__ = False
		accept: bool = True

		if callable(self.__on_select__):
			result: bool | None = self.__on_select__(self, True)
			accept = True if result or result is None else False
		elif callable(self.__general_callback__):
			result: bool | None = self.__general_callback__(self, 'select', True)
			accept = True if result or result is None else False

		if not self.__selection_changed__:
			self.__selected__ = self.__selected__ if accept else old_selection
			self.__choice_override__ = None if accept else self.__choice_override__

	def draw(self) -> None:
		super().draw()
		self.__draw(2 if self.is_mouse_pressed or self.__state__ else 1 if self.is_mouse_inside or self.__displayed__ else 0)

		if self.is_mouse_inside and (self.__terminal__.mouse.scroll_up_pressed or self.__terminal__.mouse.scroll_down_pressed):
			self.focus()

		if self.__terminal__.mouse.left_released and self.is_mouse_inside and self.is_mouse_pressed:
			self.__state__ = not self.__state__

		if not self.focused:
			self.__state__ = False
		else:
			if self.__terminal__.mouse.scroll_up_pressed:
				old_selection: int = self.__selected__
				self.__selected__ = ((self.__selected__ - 1) % len(self.__choices__)) if self.__scroll_rollover__ else max(0, self.__selected__ - 1)
				self.__selection_changed__ = False
				accept: bool = True

				if callable(self.__on_select__):
					result: bool | None = self.__on_select__(self, False)
					accept = True if result or result is None else False
				elif callable(self.__general_callback__):
					result: bool | None = self.__general_callback__(self, 'select', False)
					accept = True if result or result is None else False

				if not self.__selection_changed__:
					self.__selected__ = self.__selected__ if accept else old_selection
					self.__choice_override__ = None if accept else self.__choice_override__
			elif self.__terminal__.mouse.scroll_down_pressed:
				old_selection: int = self.__selected__
				self.__selected__ = ((self.__selected__ + 1) % len(self.__choices__)) if self.__scroll_rollover__ else min(len(self.__choices__) - 1, self.__selected__ + 1)
				self.__selection_changed__ = False
				accept: bool = True

				if callable(self.__on_select__):
					result: bool | None = self.__on_select__(self, False)
					accept = True if result or result is None else False
				elif callable(self.__general_callback__):
					result: bool | None = self.__general_callback__(self, 'select', False)
					accept = True if result or result is None else False

				if not self.__selection_changed__:
					self.__selected__ = self.__selected__ if accept else old_selection
					self.__choice_override__ = None if accept else self.__choice_override__

		x, y, _ = self.__terminal__.mouse.position
		self.__displayed__ = self.focused or self.is_mouse_inside or any(not option.hidden and option.has_coord(x, y) and self.__terminal__.get_topmost_child_at(x, y) is option for option in self.__options__)

		for i, option in enumerate(self.__options__):
			if self.__display_count__ is not None and i >= self.__display_count__:
				break

			if self.__displayed__:
				option.show()
			else:
				option.hide()

	def hide(self) -> None:
		super().hide()

		for option in self.__options__:
			option.hide()

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  choices: typing.Optional[tuple[str | AnsiStr, ...]] = ..., display_count: typing.Optional[int | None] = ..., justify: int = Enums.CENTER, allow_scroll_rollover: bool = False, word_wrap: int = Enums.WORDWRAP_WORD, on_select: typing.Optional[typing.Callable[[WIDGET_T], bool | None]] = ...,
				  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:
		super().configure(x=x, y=y, z=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		border = self.__border__[0] if border is ... or border is None else border
		highlight_border = self.__border__[1] if highlight_border is ... or highlight_border is None else highlight_border
		active_border = self.__border__[2] if active_border is ... or active_border is None else active_border
		self.__choices__: tuple[AnsiStr, ...] = self.__choices__ if choices is None or choices is ... else tuple(AnsiStr(text) for text in choices)

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'active_border', type(active_border), (BorderInfo,))

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')
		elif len(self.__choices__) == 0:
			raise ValueError('Dropbox is empty')

		color_bg = self.__bg_color__[0] if color_bg is ... or color_bg is None else parse_color(color_bg, InvalidArgumentException(Button.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = self.__bg_color__[1] if highlight_color_bg is ... or highlight_color_bg is None else parse_color(highlight_color_bg, InvalidArgumentException(Button.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = self.__bg_color__[2] if active_color_bg is ... or active_color_bg is None else parse_color(active_color_bg, InvalidArgumentException(Button.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = self.__bg_color__[0] if color_fg is ... or color_fg is None else parse_color(color_fg, InvalidArgumentException(Button.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = self.__bg_color__[1] if highlight_color_fg is ... or highlight_color_fg is None else parse_color(highlight_color_fg, InvalidArgumentException(Button.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = self.__bg_color__[2] if active_color_fg is ... or active_color_fg is None else parse_color(active_color_fg, InvalidArgumentException(Button.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		border = None if border is None else BorderInfo('', ']', '', '[', '', '', '', '') if border is ... and height == 1 else BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		self.__display_count__: int = self.__display_count__ if display_count is ... else None if display_count is None else max(0, int(display_count))
		self.__justify__: int = int(justify)
		self.__word_wrap__: int = self.__word_wrap__ if word_wrap is ... or word_wrap is None else int(word_wrap)
		self.__scroll_rollover__ = self.__scroll_rollover__ if allow_scroll_rollover is None or allow_scroll_rollover is ... else bool(allow_scroll_rollover)
		self.__on_select__ = None if on_select is None else self.__on_select__ if on_select is ... else on_select
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)



	def option_configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  text: str | AnsiStr = None, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_WORD,
				  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:

		self.__option_callback__ = self.__option_callback__ if on_mouse_click is ... else on_mouse_click

		for option in self.__options__:
			option.configure(x=x, y=y, z_index=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_tick=on_tick, on_close=on_close,
						  text=text, justify=justify, word_wrap=word_wrap, border=border, highlight_border=highlight_border, active_border=active_border, color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg)

	def close(self) -> None:
		for option in self.__options__:
			self.parent.del_widget(option.id)
		super().close()

	@property
	def justify(self) -> int:
		return self.__justify__

	@property
	def fg_color(self) -> Color:
		return self.__fg_color__[0]

	@property
	def highlight_fg_color(self) -> Color:
		return self.__fg_color__[1]

	@property
	def active_fg_color(self) -> Color:
		return self.__fg_color__[2]

	@property
	def bg_color(self) -> Color:
		return self.__bg_color__[0]

	@property
	def highlight_bg_color(self) -> Color:
		return self.__bg_color__[1]

	@property
	def active_bg_color(self) -> Color:
		return self.__bg_color__[2]

	@property
	def border(self) -> BorderInfo:
		return self.__border__[0]

	@property
	def highlight_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def active_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def selected_index(self) -> int:
		return self.__selected__

	@selected_index.setter
	def selected_index(self, index: int) -> None:
		if not isinstance(index, (int,)):
			raise InvalidArgumentException(Dropdown.selected_index.setter, 'index', type(index), (int,))

		index = int(index)

		if index < 0 or index >= len(self.__choices__):
			raise IndexError(f'Index out of range for selected choices - 0 <= {index} < {len(self.__choices__)}')
		else:
			self.__selected__ = index
			self.__choice_override__ = None
			self.__selection_changed__ = True

	@property
	def selected(self) -> AnsiStr:
		return self.__choices__[self.__selected__] if self.__choice_override__ is None else self.__choice_override__

	@selected.setter
	def selected(self, value: AnsiStr | str | int) -> None:
		if not isinstance(value, (str, AnsiStr, int)):
			raise InvalidArgumentException(Dropdown.selected.setter, 'value', type(value), (str, AnsiStr, int))
		elif isinstance(value, int):
			self.selected_index = int(value)
		else:
			raw: str = value if isinstance(value, str) else value.raw

			for i, choice in enumerate(self.__choices__):
				if choice.raw == raw:
					self.__choice_override__ = None
					self.__selected__ = i
					return

			self.__choice_override__ = AnsiStr(value)
			self.__selection_changed__ = True

	@property
	def options_displayed(self) -> bool:
		return self.__displayed__


class Entry(Widget):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, width: int, height: int, *, z_index: int = 0, word_wrap: int = Enums.WORDWRAP_WORD, justify: int = Enums.NORTH_WEST, replace_chars: str | AnsiStr = '', placeholder: typing.Optional[str | AnsiStr] = ..., cursor_blink_speed: int = 0, on_text: typing.Optional[typing.Callable[[Entry, bool], bool | AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[Entry, AnsiStr, int], bool | str | AnsiStr | None]] = ...,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):
		if width <= 2 or height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')
		elif replace_chars is not ... and replace_chars is not None and not isinstance(replace_chars, (str, AnsiStr)):
			raise InvalidArgumentException(Entry.__init__, 'replace_char', type(replace_chars), (type(None), type(...), (str, AnsiStr)))

		color_bg = parse_color(color_bg, InvalidArgumentException(Entry.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = parse_color(highlight_color_bg, InvalidArgumentException(Entry.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = parse_color(active_color_bg, InvalidArgumentException(Entry.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = parse_color(color_fg, InvalidArgumentException(Entry.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = parse_color(highlight_color_fg, InvalidArgumentException(Entry.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = parse_color(active_color_fg, InvalidArgumentException(Entry.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		replace_chars = '' if replace_chars is None or replace_chars is ... else AnsiStr(replace_chars)

		super().__init__(parent, x, y, z_index, width, height,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__justify__: int = int(justify)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)
		self.__text_index__: int = 0
		self.__placeholder__: AnsiStr | None = None if placeholder is ... or placeholder is None or len(placeholder) == 0 else AnsiStr(placeholder)
		self.__text__: list[tuple[str, AnsiStr.AnsiFormat]] = []
		self.__old_text__: list[tuple[str, AnsiStr.AnsiFormat]] = []
		self.__blink__: int = max(0, int(cursor_blink_speed))
		self.__start_blink__: int = 0
		self.__word_wrap__: int = int(word_wrap)
		self.__replace_chars__: AnsiStr = replace_chars
		self.__text_callback__: typing.Callable[[Entry, bool], bool | str | None] = on_text
		self.__input_callback___: typing.Callable[[Entry, str | AnsiStr, int], bool | str | AnsiStr | None] = on_input

	def __draw(self, mode: int) -> None:
		bg_color: Color = self.__bg_color__[mode]
		fg_color: Color = self.__fg_color__[mode]
		null_bg_color: bool = bg_color is None
		null_fg_color: bool = fg_color is None

		if null_bg_color:
			m: int = mode

			while (m := m - 1) >= 0 and bg_color is None:
				bg_color = self.__bg_color__[m]

			if m <= 0 and bg_color is None:
				bg_color = self.parent.default_bg

		if null_fg_color:
			m: int = mode

			while (m := m - 1) >= 0 and fg_color is None:
				fg_color = self.__fg_color__[m]

			if m <= 0 and fg_color is None:
				fg_color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'

		for i in range(self.height):
			self.__terminal__.putstr(f'{ansi}m{" " * self.width}', self.x, self.y + i)

		ansi_lines: list[str] = []
		lines: list[AnsiStr] = []
		cursor: tuple[int, int] | None = None
		text_index: int = self.__text_index__
		self.__wordwrap__(self.__placeholder__ if self.__placeholder__ is not None and len(self.__text__) == 0 and not self.focused else self.text, lines, self.__word_wrap__)

		if len(self.__replace_chars__):
			ansi_lines.extend(f'{ansi}m{(self.__replace_chars__ * (math.ceil(len(line) / len(self.__replace_chars__))))[:len(line)]}' for line in lines)
		else:
			ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		if self.__justify__ == Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				if text_index >= 0:
					text_index -= len(lines[i])

				xpos: int = self.x + self.width - min(len(lines[i]), self.width - 1)
				ypos: int = self.y + i

				if cursor is None and text_index < 0:
					cursor = (xpos + (len(lines[i]) + text_index), ypos)
				elif cursor is None and i + 1 == len(ansi_lines):
					cursor = (xpos + len(lines[i]), ypos)

				self.__terminal__.putstr(ansi_line, xpos, ypos, self.width)

			if cursor is None:
				cursor = (self.x + self.width, self.y)
		elif self.__justify__ == Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				if text_index >= 0:
					text_index -= len(lines[i])

				xpos: int = self.x
				ypos: int = self.y + i

				if cursor is None and text_index < 0:
					cursor = (xpos + (len(lines[i]) + text_index), ypos)
				elif cursor is None and i + 1 == len(ansi_lines):
					cursor = (xpos + len(lines[i]), ypos)

				self.__terminal__.putstr(ansi_line, xpos, ypos, self.width)

			if cursor is None:
				cursor = (self.x, self.y)
		elif self.__justify__ == Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				if text_index >= 0:
					text_index -= len(lines[i])

				xpos: int = self.x + self.width - min(len(lines[i]), self.width)
				ypos: int = self.y + self.height - (len(lines) - i)

				if cursor is None and text_index < 0:
					cursor = (xpos + (len(lines[i]) + text_index), ypos)
				elif cursor is None and i + 1 == len(ansi_lines):
					cursor = (xpos + len(lines[i]), ypos)

				self.__terminal__.putstr(ansi_line, xpos, ypos, self.width)

			if cursor is None:
				cursor = (self.x + self.width, self.y + self.height - 1)
		elif self.__justify__ == Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				if text_index >= 0:
					text_index -= len(lines[i])

				xpos: int = self.x
				ypos: int = self.y + self.height - (len(lines) - i)

				if cursor is None and text_index < 0:
					cursor = (xpos + (len(lines[i]) + text_index), ypos)
				elif cursor is None and i + 1 == len(ansi_lines):
					cursor = (xpos + len(lines[i]), ypos)

				self.__terminal__.putstr(ansi_line, xpos, ypos, self.width)

			if cursor is None:
				cursor = (self.x, self.y + self.height - 1)
		elif self.__justify__ == Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				if text_index >= 0:
					text_index -= len(lines[i])

				xpos: int = self.x + middle - len(lines[i]) // 2
				ypos: int = self.y + i

				if cursor is None and text_index < 0:
					cursor = (xpos + (len(lines[i]) + text_index), ypos)
				elif cursor is None and i + 1 == len(ansi_lines):
					cursor = (xpos + len(lines[i]), ypos)

				self.__terminal__.putstr(ansi_line, xpos, ypos, self.width)

			if cursor is None:
				cursor = (self.x + middle, self.y)
		elif self.__justify__ == Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				if text_index >= 0:
					text_index -= len(lines[i])

				xpos: int = self.x + middle - len(lines[i]) // 2
				ypos: int = self.y + self.height - (len(lines) - i)

				if cursor is None and text_index < 0:
					cursor = (xpos + (len(lines[i]) + text_index), ypos)
				elif cursor is None and i + 1 == len(ansi_lines):
					cursor = (xpos + len(lines[i]), ypos)

				self.__terminal__.putstr(ansi_line, xpos, ypos, self.width)

			if cursor is None:
				cursor = (self.x + middle, self.y + self.height - 1)
		elif self.__justify__ == Enums.WEST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				if text_index >= 0:
					text_index -= len(lines[i])

				xpos: int = self.x
				ypos: int = self.y + delta + i

				if cursor is None and text_index < 0:
					cursor = (xpos + (len(lines[i]) + text_index), ypos)
				elif cursor is None and i + 1 == len(ansi_lines):
					cursor = (xpos + len(lines[i]), ypos)

				self.__terminal__.putstr(ansi_line, xpos, ypos, self.width)

			if cursor is None:
				cursor = (self.x, self.y + delta)
		elif self.__justify__ == Enums.EAST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				if text_index >= 0:
					text_index -= len(lines[i])

				xpos: int = self.x + self.width - min(len(lines[i]), self.width)
				ypos: int = self.y + delta + i

				if cursor is None and text_index < 0:
					cursor = (xpos + (len(lines[i]) + text_index), ypos)
				elif cursor is None and i + 1 == len(ansi_lines):
					cursor = (xpos + len(lines[i]), ypos)

				self.__terminal__.putstr(ansi_line, xpos, ypos, self.width)

			if cursor is None:
				cursor = (self.x + self.width, self.y + delta)
		elif self.__justify__ == Enums.CENTER:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				if text_index >= 0:
					text_index -= len(lines[i])

				xpos: int = self.x + middle - len(lines[i]) // 2
				ypos: int = self.y + delta + i

				if cursor is None and text_index < 0:
					cursor = (xpos + (len(lines[i]) + text_index), ypos)
				elif cursor is None and i + 1 == len(ansi_lines):
					cursor = (xpos + len(lines[i]), ypos)

				self.__terminal__.putstr(ansi_line, xpos, ypos, self.width)

			if cursor is None:
				cursor = (self.x + middle, self.y + delta)

		if self.focused and cursor is not None:
			cursor_blink: bool = self.__blink__ <= 0 or (self.__terminal__.current_tick - self.__start_blink__) % (self.__blink__ * 2) <= self.__blink__
			cx, cy = cursor
			cx -= self.x
			cy -= self.y
			char: str | AnsiStr = self.__replace_chars__[self.__text_index__ % len(self.__replace_chars__)] if self.__text_index__ < len(self.__text__) and len(self.__replace_chars__) else AnsiStr.from_pairs((self.__text__[self.__text_index__],)) if self.__text_index__ < len(self.__text__) else ' '
			ansi = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{";7" if cursor_blink else ""}'
			self.__terminal__.putstr(f'{ansi}m{char}', self.x + cx, self.y + cy)

	def __check_key(self, keycode: int | None) -> int | None:
		if keycode is None:
			return None
		elif keycode == 530:
			return ord('\'')
		elif keycode == 460:
			return ord('"')
		else:
			return keycode

	def draw(self) -> None:
		super().draw()
		mouse_info: MouseInfo = self.__terminal__.mouse
		max_index: int = min(len(self.__text__), self.width * self.height)
		self.__text_index__ = 0 if self.__text_index__ < 0 else max_index if self.__text_index__ > max_index else self.__text_index__
		self.__draw(2 if self.is_mouse_inside and self.is_mouse_pressed else 1 if self.is_mouse_inside else 0)

		if mouse_info.left_released:
			self.__text_index__ = len(self.__text__)
			self.__start_blink__ = self.__terminal__.current_tick

			if not self.is_mouse_inside or not self.focused:
				accept_text: bool | str = False
				value: bool | str | None = None

				if callable(self.__text_callback__):
					value = self.__text_callback__(self, False)
				elif callable(self.__general_callback__):
					value = self.__general_callback__(self, 'input', False)

				if isinstance(value, str):
					accept_text = str(value)
				elif value is not None:
					accept_text = bool(value)

				if isinstance(accept_text, str):
					self.__text__.clear()
					self.__old_text__.clear()
					self.__text__.extend(accept_text)
					self.__old_text__.extend(accept_text)
				elif accept_text:
					self.__old_text__.clear()
					self.__old_text__.extend(self.__text__)
				else:
					self.__text__.clear()
					self.__text__.extend(self.__old_text__)

		if self.focused:
			c: int | None = self.__check_key(self.__terminal__.getch())

			if c is not None:
				self.__start_blink__ = self.__terminal__.current_tick
				# print(c)

			if c is not None and curses.ascii.isprint(c) and len(self.__text__) < self.width * self.height:
				char: AnsiStr = AnsiStr(chr(c))
				endpoint: bool = self.__text_index__ == len(self.__text__)
				value: bool | AnsiStr | None = True

				if callable(self.__input_callback___):
					value = self.__input_callback___(self, char, -1 if endpoint else self.__text_index__)
				elif callable(self.__general_callback__):
					value = self.__general_callback__(self, 'input', char, -1 if endpoint else self.__text_index__)
					value = True if value is None else value

				if isinstance(value, (str, AnsiStr)):
					value = AnsiStr(value)

					if len(value) > 1:
						raise ValueError(f'Expected single character - got string of length {len(value)}')
					elif len(value) == 0 or not curses.ascii.isprint(value if isinstance(value, str) else value.raw):
						return

					char = value
				elif value is not None and not value:
					return

				pair = next(char.pairs())

				if endpoint:
					self.__text__.append(pair)
				else:
					self.__text__.insert(self.__text_index__, pair)

				self.__text_index__ += 1

			elif (c == curses.KEY_BACKSPACE or c == 8) and self.__text_index__ > 0:
				if self.__text_index__ == len(self.__text__):
					self.__text__.pop()
				else:
					self.__text__.pop(self.__text_index__ - 1)

				self.__text_index__ -= 1

			elif c == 330 and len(self.__text__) > 0 and self.__text_index__ < len(self.__text__):
				self.__text__.pop(self.__text_index__)
				self.__text_index__ -= 1

			elif c == curses.KEY_UP:
				self.__text_index__ -= self.width
			elif c == curses.KEY_DOWN:
				self.__text_index__ += self.width

			elif c == curses.KEY_LEFT and self.__text_index__ > 0:
				self.__text_index__ -= 1
			elif c == curses.KEY_RIGHT and self.__text_index__ < len(self.__text__):
				self.__text_index__ += 1

			elif c == curses.CTL_HOME or c == curses.KEY_HOME:
				self.__text_index__ = 0
			elif c == curses.CTL_END or c == curses.KEY_END:
				self.__text_index__ = len(self.__text__)

			elif c == curses.SHF_PADENTER or c == curses.CTL_ENTER:
				char: AnsiStr = AnsiStr('\n')
				endpoint: bool = self.__text_index__ == len(self.__text__)
				value: bool |  AnsiStr | None = True

				if callable(self.__input_callback___):
					value = self.__input_callback___(self, char, -1 if endpoint else self.__text_index__)
				elif callable(self.__general_callback__):
					value = self.__general_callback__(self, 'input', char, -1 if endpoint else self.__text_index__)
					value = True if value is None else value

				if isinstance(value, (str, AnsiStr)):
					value = AnsiStr(value)

					if len(value) > 1:
						raise ValueError(f'Expected single character - got string of length {len(value)}')
					elif len(value) == 0 or not curses.ascii.isprint(value if isinstance(value, str) else value.raw):
						return

					char = value
				elif value is not None and not value:
					return

				pair = next(char.pairs())

				if endpoint:
					self.__text__.append(pair)
				else:
					self.__text__.insert(self.__text_index__, pair)

				self.__text_index__ += 1
			elif c == 10 or c == 13 or c == curses.KEY_ENTER or c == 459:
				accept_text: bool | str = True
				value: bool | str | None = None

				if callable(self.__text_callback__):
					value = self.__text_callback__(self, True)
				elif callable(self.__general_callback__):
					value = self.__general_callback__(self, 'input', True)

				if isinstance(value, str):
					accept_text = str(value)
				elif value is not None:
					accept_text = bool(value)

				if isinstance(accept_text, str):
					self.__text__.clear()
					self.__old_text__.clear()
					self.__text__.extend(accept_text)
					self.__old_text__.extend(accept_text)
				elif accept_text:
					self.__old_text__.clear()
					self.__old_text__.extend(self.__text__)
				else:
					self.__text__.clear()
					self.__text__.extend(self.__old_text__)

				self.unfocus()

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  word_wrap: int = Enums.WORDWRAP_WORD, justify: typing.Optional[int] = ..., replace_chars: typing.Optional[str | AnsiStr] = ..., placeholder: typing.Optional[str | AnsiStr] = ..., cursor_blink_speed: typing.Optional[int] = ..., on_text: typing.Optional[typing.Callable[[Entry, bool], bool | AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[Entry, AnsiStr, int], bool | str | AnsiStr | None]] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:
		super().configure(x=x, y=y, z=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		replace_chars: str | AnsiStr = self.__replace_chars__ if replace_chars is ... else replace_chars

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')
		elif replace_chars is not ... and replace_chars is not None and not isinstance(replace_chars, (str, AnsiStr)):
			raise InvalidArgumentException(Entry.__init__, 'replace_char', type(replace_chars), (type(None), type(...), (str, AnsiStr)))

		color_bg = self.__bg_color__[0] if color_bg is ... or color_bg is None else parse_color(color_bg, InvalidArgumentException(Button.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = self.__bg_color__[1] if highlight_color_bg is ... or highlight_color_bg is None else parse_color(highlight_color_bg, InvalidArgumentException(Button.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = self.__bg_color__[2] if active_color_bg is ... or active_color_bg is None else parse_color(active_color_bg, InvalidArgumentException(Button.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		color_fg = self.__fg_color__[0] if color_fg is ... or color_fg is None else parse_color(color_fg, InvalidArgumentException(Button.__init__, 'color_fg', type(color_fg), (Color,)))
		highlight_color_fg = self.__fg_color__[1] if highlight_color_fg is ... or highlight_color_fg is None else parse_color(highlight_color_fg, InvalidArgumentException(Button.__init__, 'highlight_color_fg', type(highlight_color_fg), (Color,)))
		active_color_fg = self.__fg_color__[2] if active_color_fg is ... or active_color_fg is None else parse_color(active_color_fg, InvalidArgumentException(Button.__init__, 'active_color_fg', type(active_color_fg), (Color,)))

		replace_chars = '' if replace_chars is None or replace_chars is ... else AnsiStr(replace_chars)

		self.__justify__: int = self.__justify__ if justify is ... or justify is None else int(justify)
		self.__replace_chars__: AnsiStr = replace_chars
		self.__placeholder__: AnsiStr | None = self.__placeholder__ if placeholder is ... else None if placeholder is None or len(placeholder) == 0 else AnsiStr(placeholder)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Color, Color, Color] = (color_fg, highlight_color_fg, active_color_fg)
		self.__blink__: int = self.__blink__ if cursor_blink_speed is ... or cursor_blink_speed is None else max(0, int(cursor_blink_speed))
		self.__word_wrap__: int = self.__word_wrap__ if word_wrap is ... or word_wrap is None else int(word_wrap)
		self.__text_callback__: typing.Callable[[Entry, bool], bool | str | None] = self.__text_callback__ if on_text is ... else on_text
		self.__input_callback___: typing.Callable[[Entry, str | AnsiStr, int], bool | str | AnsiStr | None] = self.__input_callback___ if on_input is ... else on_input

	@property
	def justify(self) -> int:
		return self.__justify__

	@property
	def fg_color(self) -> Color:
		return self.__fg_color__[0]

	@property
	def highlight_fg_color(self) -> Color:
		return self.__fg_color__[1]

	@property
	def active_fg_color(self) -> Color:
		return self.__fg_color__[2]

	@property
	def bg_color(self) -> Color:
		return self.__bg_color__[0]

	@property
	def highlight_bg_color(self) -> Color:
		return self.__bg_color__[1]

	@property
	def active_bg_color(self) -> Color:
		return self.__bg_color__[2]

	@property
	def text(self) -> AnsiStr:
		return AnsiStr.from_pairs(self.__text__)

	@text.setter
	def text(self, text: str | AnsiStr) -> None:
		if not isinstance(text, (str, AnsiStr)):
			raise InvalidArgumentException(Entry.text.setter, 'text', type(text), (str, AnsiStr))

		self.__text__.clear()
		self.__old_text__.clear()
		self.__text__.extend(AnsiStr(text).pairs())
		self.__old_text__.extend(AnsiStr(text).pairs())

	@property
	def cursor(self) -> int:
		return self.__text_index__

	@cursor.setter
	def cursor(self, cursor: int) -> None:
		if (cursor := int(cursor)) >= 0:
			self.__text_index__ = min(int(cursor), len(self.__text__) + 1)
		else:
			self.__text_index__ = max(0, len(self.__text__) + cursor + 1)


class Image(Widget):
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, width: int, height: int, image: str | AnsiStr | numpy.ndarray | PIL.Image.Image | None, *, div: typing.Optional[int] = ..., use_subpad: bool = True, z_index: int = 0,
				 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				 color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Image.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Image.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Image.__init__, 'active_border', type(active_border), (BorderInfo,))

		if width < 3 or height < 3:
			raise ValueError('Dimensions too small (width >= 3; height >= 3)')

		color_bg = parse_color(color_bg, InvalidArgumentException(Image.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = parse_color(highlight_color_bg, InvalidArgumentException(Image.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = parse_color(active_color_bg, InvalidArgumentException(Image.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		border = None if border is None else BorderInfo('', ']', '', '[', '', '', '', '') if border is ... and height == 1 else BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		super().__init__(parent, x, y, z_index, width, height,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		self.__do_subpad__: bool = bool(use_subpad)
		self.__window__: _curses.window | None = None
		self.__pixel_div__: tuple[int, typing.Optional[int]] = (-1, div)
		self.__update_draw_image__(image, div, width - 2, height - 2)
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)

	def __update_draw_image__(self, image: str | AnsiStr | numpy.ndarray | PIL.Image.Image, div: typing.Optional[int], width: int, height: int) -> None:
		if image is not None:
			try:
				pilimage: PIL.Image.Image

				if isinstance(image, str):
					pilimage = PIL.Image.open(image).convert('RGB')
				elif isinstance(image, AnsiStr):
					pilimage = PIL.Image.open(image.raw).convert('RGB')
				elif isinstance(image, numpy.ndarray):
					pilimage = PIL.Image.fromarray(image).convert('RGB')
				elif isinstance(image, PIL.Image.Image):
					pilimage = image.convert('RGB')
				else:
					raise InvalidArgumentException(Image.__init__, 'image', type(image), (str, AnsiStr, numpy.ndarray, PIL.Image.Image))

				self.__img_actual__: str | AnsiStr | numpy.ndarray | PIL.Image.Image = image
				image: numpy.ndarray = numpy.array(pilimage).astype(numpy.uint8)
				image = cv2.resize(image, dsize=(width, height), interpolation=cv2.INTER_CUBIC)
				true_div: int = -1

				if div is None or div is ...:
					divs: tuple[int, ...] = (4, 8, 16, 32, 64, 128)
					topmost: Terminal.Terminal = self.topmost_parent()
					available: int = min(curses.COLORS - len(topmost.__colors__), curses.COLOR_PAIRS - len(topmost.__color_pairs__))

					for true_div in divs:
						div_image: numpy.ndarray = image if true_div <= 0 else (image // true_div * true_div + true_div // 2)
						r: numpy.ndarray = div_image[:, :, 0].astype(numpy.uint32)
						g: numpy.ndarray = div_image[:, :, 1].astype(numpy.uint32)
						b: numpy.ndarray = div_image[:, :, 2].astype(numpy.uint32)
						pixels: numpy.ndarray = (r << 16) | (g << 8) | b
						colors: set[int] = set(pixels.flatten())

						if len(colors) <= available:
							break
				else:
					true_div: int = int(div)

				image = image if true_div <= 0 else (image // true_div * true_div + true_div // 2)
				grayscale: numpy.ndarray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
				chars: tuple[str, ...] = (' ', '`', '.', '-', '~', '+', '*', '<', '>', ':', '!', ';', '|', '/', '%', '?', '#', '$', '@')
				image_str: list[str] = []

				for y in range(height):
					for x in range(width):
						if true_div > 0:
							r, g, b = image[y, x, :]
							image_str.append(f'\033[38;2;{int(r)};{int(g)};{int(b)}m█')
						elif true_div == 0:
							l: int = grayscale[y, x]
							image_str.append(f'\033[38;2;{int(l)};{int(l)};{int(l)}m█')
						else:
							brightness: int = int(grayscale[y, x] / 255 * (len(chars) - 1))
							char: str = chars[brightness]
							image_str.append(char)
					image_str.append('\n')

				self.__image__ = AnsiStr(''.join(image_str))
				self.__raw_image__ = (image, grayscale)
				self.__pixel_div__ = (true_div, div)
			except (IOError, OSError):
				self.__image__: AnsiStr = AnsiStr('')
				self.__raw_image__ = None
		else:
			self.__image__ = AnsiStr('')
			self.__raw_image__ = None

		if not self.__do_subpad__:
			return

		if self.__window__ is None:
			self.__window__ = curses.newpad(height, width)
		else:
			self.__window__.clear()

		self.__window__.move(0, 0)
		my, mx = height, width
		cx, cy = 0, 0
		ix: int = cx
		iy: int = cy
		true_count: int = 0
		char_count: int = 0
		line_count: int = 0
		root: Terminal.Terminal = self.topmost_parent()
		root.__touched_cols_rows__[0] = min(ix, root.__touched_cols_rows__[0])
		root.__touched_cols_rows__[2] = min(iy, root.__touched_cols_rows__[2])

		for segment, ansi in self.__image__.format_groups('\n', keep_delimiter=True):
			attributes: int = 0

			if ansi.bold:
				attributes |= curses.A_BOLD
			if ansi.dim:
				attributes |= curses.A_DIM
			if ansi.italic:
				attributes |= curses.A_ITALIC
			if ansi.underline:
				attributes |= curses.A_UNDERLINE
			if ansi.blink:
				attributes |= curses.A_BLINK
			if ansi.reverse:
				attributes |= curses.A_REVERSE
			if ansi.invis:
				attributes |= curses.A_INVIS
			if ansi.protect:
				attributes |= curses.A_PROTECT

			fg: int = 7 if ansi.foreground_color is None else root.get_color(ansi.foreground_color)
			bg: int = 0 if ansi.background_color is None else root.get_color(ansi.background_color)
			color_pair: int = root.get_color_pair(fg, bg)
			attributes |= curses.color_pair(color_pair)
			char_x: int = ix + char_count
			char_y: int = iy + line_count

			root.__touched_cols_rows__[1] = min(char_x, root.__touched_cols_rows__[1])
			root.__touched_cols_rows__[3] = min(char_y, root.__touched_cols_rows__[3])

			if segment == '\n':
				true_count += 1
				line_count += 1
				char_count = 0
				self.__window__.move(char_y, ix)
			elif 0 <= (x := ix + char_count) < mx and 0 <= (y := iy + line_count) < my and len(segment):
				try:
					max_width: int = mx - x
					self.__window__.addstr(y, x, segment[:max_width], attributes)
				except _curses.error:
					pass

				true_count += len(segment)
				char_count += len(segment)

	def draw(self) -> None:
		super().draw()
		mode: int = 2 if self.is_mouse_pressed else 1 if self.is_mouse_inside else 0
		border: BorderInfo | None = self.__border__[mode]
		self.draw_border(border)

		if not self.__do_subpad__:
			self.__terminal__.putstr(self.__image__, self.x + 1, self.y + 1)
			return

		my, mx = self.__terminal__.screen.getmaxyx()
		sx, sy = self.__terminal__.scroll()
		x: int = self.x - sx
		y: int = self.y - sy
		uy: int = min(my - 1, y + self.height - 2)
		ux: int = min(mx - 1, x + self.width - 2)
		ly: int = max(y + 1, 0)
		lx: int = max(x + 1, 0)
		sy: int = 0 if y >= 0 else -y
		sx: int = 0 if x >= 0 else -x
		self.__window__.overwrite(self.__terminal__.screen, sy, sx, ly, lx, uy, ux)

	def redraw(self) -> None:
		super().redraw()

		if self.__raw_image__ is not None:
			width, height = self.size
			self.__update_draw_image__(self.__img_actual__, self.__pixel_div__, width - 2, height - 2)

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  image: typing.Optional[str | AnsiStr | numpy.ndarray | PIL.Image.Image] = ..., div: typing.Optional[int] = ..., use_subpad: typing.Optional[bool] = ...,
				  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ...,
				  ) -> None:
		super().configure(x=x, y=y, z=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		border = self.__border__[0] if border is ... or border is None else border
		highlight_border = self.__border__[1] if highlight_border is ... or highlight_border is None else highlight_border
		active_border = self.__border__[2] if active_border is ... or active_border is None else active_border

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'active_border', type(active_border), (BorderInfo,))

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		color_bg = self.__bg_color__[0] if color_bg is ... or color_bg is None else parse_color(color_bg, InvalidArgumentException(Button.__init__, 'color_bg', type(color_bg), (Color,)))
		highlight_color_bg = self.__bg_color__[1] if highlight_color_bg is ... or highlight_color_bg is None else parse_color(highlight_color_bg, InvalidArgumentException(Button.__init__, 'highlight_color_bg', type(highlight_color_bg), (Color,)))
		active_color_bg = self.__bg_color__[2] if active_color_bg is ... or active_color_bg is None else parse_color(active_color_bg, InvalidArgumentException(Button.__init__, 'active_color_bg', type(active_color_bg), (Color,)))

		border = None if border is None else BorderInfo('', ']', '', '[', '', '', '', '') if border is ... and height == 1 else BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		if image is not ... or div != self.__pixel_div__[1]:
			image = self.__img_actual__ if image is None or image is ... else image
			w, h = self.size
			self.__update_draw_image__(image, self.__pixel_div__ if div is ... else None if div is None else int(div), w - 2, h - 2)

		self.__do_subpad__: bool = self.__do_subpad__ if use_subpad is ... or use_subpad is None else bool(use_subpad)
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Color, Color, Color] = (color_bg, highlight_color_bg, active_color_bg)

	@property
	def bg_color(self) -> Color:
		return self.__bg_color__[0]

	@property
	def highlight_bg_color(self) -> Color:
		return self.__bg_color__[1]

	@property
	def active_bg_color(self) -> Color:
		return self.__bg_color__[2]

	@property
	def border(self) -> BorderInfo:
		return self.__border__[0]

	@property
	def highlight_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def active_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def div(self) -> tuple[int, typing.Optional[int]]:
		return self.__pixel_div__

	@property
	def image(self) -> numpy.ndarray:
		return self.__raw_image__[0]

	@property
	def grayscale(self) -> numpy.ndarray:
		return self.__raw_image__[1]

	@property
	def raw_image(self) -> str | AnsiStr | numpy.ndarray | PIL.Image.Image:
		return self.__img_actual__ if hasattr(self, '__img_actual__') else None


class SubTerminal(Widget):
	### Magic methods
	def __init__(self, parent: Terminal.Terminal | SubTerminal, x: int, y: int, width: int, height: int, name: str = '', *, z_index: int = 0, transparent: bool = False,
				 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...):

		super().__init__(parent, x, y, z_index, width, height,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		assert width >= 3, 'Width must be greater than 2'
		assert height >= 3, 'Height must be greater than 2'

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(SubTerminal.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(SubTerminal.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(SubTerminal.__init__, 'active_border', type(active_border), (BorderInfo,))

		border = None if border is None else BorderInfo('', ']', '', '[', '', '', '', '') if border is ... and height == 1 else BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)
		self.__widgets__: dict[int, dict[int, typing.Type[WIDGET_T | Widget]]] = {}
		self.__pages__: dict[int, dict[int, SubTerminal]] = {}
		self.__previous_inputs__: list[str] = []
		self.__title__ = str(name) if isinstance(name, str) else ''
		self.__transparent__: bool = bool(transparent)

		self.__scroll__: list[int, int] = [0, 0]
		self.__cursor__: tuple[int, int, int, int] = (0, 0, 0, 0)
		self.__last_mouse_info__: MouseInfo = MouseInfo(-1, 0, 0, 0, 0)
		self.__event_queue__: SpinQueue[int] = SpinQueue(10)
		self.__auto_scroll__: int = 10
		self.__tab_size__: int = 4
		self.__active_page__: SubTerminal | None = None
		self.__erase_refresh__: bool = True

		self.__stdscr__: _curses.window = curses.newpad(height, width)
		self.__stdscr__.keypad(True)
		self.__stdscr__.idlok(True)
		self.__stdscr__.idcok(True)
		self.__stdscr__.nodelay(True)
		self.__stdscr__.immedok(False)
		self.__stdscr__.leaveok(True)
		self.__stdscr__.scrollok(False)

	### Internal methods
	def __move__(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> bool | tuple[int, int]:
		if (x is None or x is ...) and (y is None or y is ...):
			y, x = self.__stdscr__.getyx()
			return x, y
		elif x is not None and x is not ... and not isinstance(x, int):
			raise InvalidArgumentException(SubTerminal.__move__, 'x', type(x), ('int',))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise InvalidArgumentException(SubTerminal.__move__, 'y', type(y), ('int',))
		else:
			cy, cx = self.__stdscr__.getyx()
			my, mx = self.__stdscr__.getmaxyx()
			sx, sy = self.__scroll__
			new_x: int = (cx if x is None or x is ... else int(x)) - sx
			new_y: int = (cy if y is None or y is ... else int(y)) - sy

			if 0 <= new_y < my and 0 <= new_x < mx:
				self.__stdscr__.move(new_y, new_x)
				return True
			else:
				return False

	def __on_focus__(self, local_x: int, local_y: int) -> None:
		topmost: Widget | None = self.get_topmost_child_at(local_x, local_y)
		self.set_focus(topmost)

		if isinstance(topmost, SubTerminal):
			self.__active_page__ = topmost
			self.__active_page__.__on_focus__(local_x - self.__active_page__.x, local_y - self.__active_page__.y)
		elif self.__active_page__ is not None:
			self.__active_page__.unfocus()
			self.__active_page__ = None

	def __total_scroll__(self) -> tuple[int, int]:
		sx, sy = self.__scroll__

		for parent in self.parent_stack():
			_sx, _sy = parent.__scroll__
			sx += _sx
			sy += _sy

		return sx, sy

	def draw_border(self, border: BorderInfo | None) -> None:
		if border is None:
			return
		elif not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Widget.draw_border, 'border', type(border), (BorderInfo,))

		width, height = self.size
		self.__terminal__.putstr(border.top * (width - 2), self.__position__[0] + 1, self.__position__[1], width - 2)
		self.__terminal__.putstr(border.bottom * (width - 2), self.__position__[0] + 1, self.__position__[1] + height - 1, width - 2)

		for i in range(1, height - 1):
			self.__terminal__.putstr(border.left, self.__position__[0], self.__position__[1] + i, 1)
			self.__terminal__.putstr(border.right, self.__position__[0] + width - 1, self.__position__[1] + i, 1)

		self.__terminal__.putstr(border.top_left, self.__position__[0], self.__position__[1], 1)
		self.__terminal__.putstr(border.top_right, self.__position__[0] + width - 1, self.__position__[1], 1)
		self.__terminal__.putstr(border.bottom_left, self.__position__[0], self.__position__[1] + height - 1, 1)
		self.__terminal__.putstr(border.bottom_right, self.__position__[0] + width - 1, self.__position__[1] + height - 1, 1)

	def draw(self) -> None:
		raise NotImplementedError()

	def update(self) -> None:
		if self.__erase_refresh__:
			self.__stdscr__.erase()

		super().draw()

		# Draw border
		self.draw_border(self.__border__[2 if self.__terminal__.selected_subterminal is self else 1 if self.is_mouse_inside else 0])

		title_offset: int = round(self.width * 0.1)

		if len(self.__title__) and title_offset > 0 and self.width >= title_offset + len(self.__title__):
			self.__terminal__.putstr(f'[ {self.__title__} ]', self.__position__[0] + title_offset, self.__position__[1])

		# Update mouse
		root: Terminal.Terminal = self.topmost_parent()
		_id, x, y, z, bstate = root.mouse
		scroll_x, scroll_y = self.__scroll__
		gx, gy = self.global_pos()
		self.__last_mouse_info__ = MouseInfo(_id, x - gx + scroll_x, y - gy + scroll_y, z, bstate)
		cx: int = self.__last_mouse_info__.pos_x
		cy: int = self.__last_mouse_info__.pos_y
		topmost: Widget | None = self.get_topmost_child_at(cx, cy)

		if self.__last_mouse_info__.scroll_up_pressed and self.__auto_scroll__ > 0 and topmost is None and self.is_mouse_inside:
			self.__scroll__[not self.__last_mouse_info__.alt_pressed] -= self.__auto_scroll__

		if self.__last_mouse_info__.scroll_down_pressed and self.__auto_scroll__ > 0 and topmost is None and self.is_mouse_inside:
			self.__scroll__[not self.__last_mouse_info__.alt_pressed] += self.__auto_scroll__

		if self.__last_mouse_info__.left_pressed or self.__last_mouse_info__.middle_pressed or self.__last_mouse_info__.right_pressed:
			if isinstance(topmost, SubTerminal):
				self.__active_page__ = topmost
				self.__active_page__.__on_focus__(cx - self.__active_page__.x, cy - self.__active_page__.y)
			else:
				self.__active_page__ = None

		# Draw children
		for z_index in sorted(self.__widgets__.keys()):
			for widget in tuple(self.__widgets__[z_index].values()):
				if not widget.hidden:
					widget.draw()

		for z_index in sorted(self.__pages__.keys()):
			for sub_terminal in tuple(self.__pages__[z_index].values()):
				if not sub_terminal.hidden:
					sub_terminal.update()

		# Calculate scrolling
		my, mx = root.__root__.getmaxyx()

		# Draw window to root
		if self.__transparent__:
			self.__stdscr__.overlay(self.__terminal__.screen, 1, 1, self.y + 1, self.x + 1, min(self.y + self.height - 2, my - 1), min(self.x + self.width - 2, mx - 1))
		else:
			self.__stdscr__.overwrite(self.__terminal__.screen, 1, 1, self.y + 1, self.x + 1, min(self.y + self.height - 2, my - 1), min(self.x + self.width - 2, mx - 1))

	### Standard methods
	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...,
				  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				  ) -> None:
		super().configure(x=x, y=y, z=z_index, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		border = self.__border__[0] if border is ... or border is None else border
		highlight_border = self.__border__[1] if highlight_border is ... or highlight_border is None else highlight_border
		active_border = self.__border__[2] if active_border is ... or active_border is None else active_border

		if border is not None and border is not ... and not isinstance(border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'border', type(border), (BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'highlight_border', type(highlight_border), (BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, BorderInfo):
			raise InvalidArgumentException(Button.__init__, 'active_border', type(active_border), (BorderInfo,))

		assert self.width >= 3, 'Width must be greater than 2'
		assert self.height >= 3, 'Height must be greater than 2'

		border = None if border is None else BorderInfo('', ']', '', '[', '', '', '', '') if border is ... and height == 1 else BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... and height == 1 else BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border
		self.__border__: tuple[BorderInfo | None, BorderInfo | None, BorderInfo | None] = (border, highlight_border, active_border)

	@property
	def border(self) -> BorderInfo:
		return self.__border__[0]

	@property
	def highlight_border(self) -> BorderInfo:
		return self.__border__[1]

	@property
	def active_border(self) -> BorderInfo:
		return self.__border__[1]

	def putstr(self, msg: str | AnsiStr, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., n: typing.Optional[int] = ...) -> None:
		if not isinstance(msg, (str, AnsiStr)):
			raise InvalidArgumentException(SubTerminal.putstr, 'msg', type(msg), (str, AnsiStr))
		elif x is not ... and x is not None and not isinstance(x, int):
			raise InvalidArgumentException(SubTerminal.putstr, 'x', type(x), (int,))
		elif y is not ... and y is not None and not isinstance(y, int):
			raise InvalidArgumentException(SubTerminal.putstr, 'y', type(y), (int,))
		elif n is not ... and n is not None and not isinstance(n, int):
			raise InvalidArgumentException(SubTerminal.putstr, 'n', type(n), (int,))

		n = None if n is None or n is ... else int(n)

		if n is not None and n <= 0:
			return

		msg = msg if isinstance(msg, AnsiStr) else AnsiStr(msg)
		root: Terminal.Terminal = self.topmost_parent()
		my, mx = self.__stdscr__.getmaxyx()
		cx, cy = self.__move__()
		sx, sy = self.__total_scroll__()
		ix: int = cx if x is ... or x is None else (int(x) - sx)
		iy: int = cy if y is ... or y is None else (int(y) - sy)
		true_count: int = 0
		char_count: int = 0
		line_count: int = 0

		for segment, ansi in msg.format_groups('\n\b\t', keep_delimiter=True):
			attributes: int = 0

			if ansi.bold:
				attributes |= curses.A_BOLD
			if ansi.dim:
				attributes |= curses.A_DIM
			if ansi.italic:
				attributes |= curses.A_ITALIC
			if ansi.underline:
				attributes |= curses.A_UNDERLINE
			if ansi.blink:
				attributes |= curses.A_BLINK
			if ansi.reverse:
				attributes |= curses.A_REVERSE
			if ansi.invis:
				attributes |= curses.A_INVIS
			if ansi.protect:
				attributes |= curses.A_PROTECT

			fg: int = 7 if ansi.foreground_color is None else root.get_color(ansi.foreground_color)
			bg: int = 0 if ansi.background_color is None else root.get_color(ansi.background_color)
			color_pair: int = root.get_color_pair(fg, bg)
			attributes |= curses.color_pair(color_pair)
			char_x: int = ix + char_count
			char_y: int = iy + line_count

			if n is not None and 0 <= n <= true_count:
				break
			elif segment == '\n':
				true_count += 1
				line_count += 1
				char_count = 0
				self.__move__(ix, char_y)
			elif segment == '\b':
				true_count += 1
				char_count -= 1

				if 0 <= char_x - 1 < mx and 0 <= char_y < my:
					self.__stdscr__.delch(char_y, char_x - 1)
			elif segment == '\t':
				if 0 <= char_x < mx and 0 <= char_y < my:
					self.__stdscr__.addstr(char_y, char_x, ' ' * self.__tab_size__, attributes)

				true_count += 1
				char_count += self.__tab_size__
			elif 0 <= (x := ix + char_count) < mx and 0 <= (y := iy + line_count) < my and len(segment):
				try:
					max_width: int = mx - x
					self.__stdscr__.addstr(y, x, segment[:max_width], attributes)
				except _curses.error:
					pass

				true_count += len(segment)
				char_count += len(segment)

	def del_widget(self, _id: int) -> None:
		for alloc in self.__widgets__.values():
			if _id in alloc:
				del alloc[_id]
				break

	def del_sub_terminal(self, _id: int) -> None:
		for alloc in self.__pages__.values():
			if _id in alloc:
				del alloc[_id]
				break

	def cancel(self, _id: int) -> None:
		self.__terminal__.cancel(_id)

	def cursor_visibility(self, visibility: int) -> None:
		cx, cy, _, rt = self.__cursor__
		self.__cursor__ = (cx, cy, visibility, rt)

	def cursor_flash(self, flash_rate: int) -> None:
		cx, cy, vs, _ = self.__cursor__
		self.__cursor__ = (cx, cy, vs, flash_rate)

	def set_focus(self, widget: Widget | None) -> None:
		if widget is not None and not isinstance(widget, Widget):
			raise InvalidArgumentException(SubTerminal.set_focus, 'widget', type(widget), (Widget,))
		elif widget is None or widget.parent is self:
			child: Widget
			old_page: SubTerminal = self.__active_page__

			if widget is not None:
				subterminals: tuple[SubTerminal, ...] = self.subterminals()

				if widget in subterminals:
					self.__active_page__ = widget
				elif widget.parent in subterminals:
					self.__active_page__ = widget.parent
				else:
					self.__active_page__ = None
			else:
				self.__active_page__ = None

			if old_page is not None and self.__active_page__ is not old_page:
				old_page.__unfocus__()

			for child in (*self.widgets(), *self.subterminals()):
				if child is not widget:
					child.__unfocus__()

			if widget is not None and not widget.focused:
				widget.__focus__()
				self.parent.set_focus(self)
		elif (topmost_b := widget.topmost_parent()) is not (topmost_a := self.topmost_parent()):
			raise ValueError(f'The specified widget is not a child of this terminal - {hex(id(topmost_b))} != {hex(id(topmost_a))} (topmost)')
		else:
			widget.parent.set_focus(widget)

	def ungetch(self, key: int) -> None:
		self.__event_queue__.append(int(key))

	def ungetgch(self, key: int) -> None:
		self.topmost_parent().ungetgch(key)

	def erase_refresh(self, flag: bool) -> None:
		self.__erase_refresh__ = bool(flag)

	def redraw(self) -> None:
		super().redraw()

		for alloc in self.__widgets__.values():
			for widget in alloc.values():
				if not widget.hidden:
					widget.redraw()

		for alloc in self.__pages__.values():
			for subterm in alloc.values():
				if not subterm.hidden:
					subterm.redraw()

	def getch(self) -> int | None:
		return self.__event_queue__.pop() if len(self.__event_queue__) else None

	def peekch(self) -> int | None:
		return self.__event_queue__[-1] if len(self.__event_queue__) else None

	def getgch(self) -> int | None:
		return self.topmost_parent().getgch()

	def peekgch(self) -> int | None:
		return self.topmost_parent().peekgch()

	def scroll_speed(self, scroll: typing.Optional[int] = ...) -> None | int:
		if scroll is None or scroll is ...:
			return self.__auto_scroll__
		else:
			self.__auto_scroll__ = int(scroll)

	def after(self, ticks: int, callback: typing.Callable, *args, __threaded: bool = True, **kwargs) -> int:
		return self.__terminal__.after(ticks, callback, *args, __threaded=__threaded, **kwargs)

	def cursor(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> None | tuple[int, int]:
		if (x is None or x is ...) and (y is None or y is ...):
			return self.__cursor__[:2]
		elif x is not None and x is not ... and not isinstance(x, int):
			raise InvalidArgumentException(SubTerminal.cursor, 'x', type(x), (int,))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise InvalidArgumentException(SubTerminal.cursor, 'y', type(y), (int,))
		else:
			cy, cx = self.__stdscr__.getyx()
			_, _, visibility, rate = self.__cursor__
			self.__cursor__ = (cx if x is None or x is ... else int(x), cy if y is None or y is ... else int(y), visibility, rate)

	def scroll(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> None | tuple[int, int]:
		if (x is None or x is ...) and (y is None or y is ...):
			x, y = self.__scroll__
			return x, y
		elif x is not None and x is not ... and not isinstance(x, int):
			raise InvalidArgumentException(SubTerminal.scroll, 'x', type(x), (int,))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise InvalidArgumentException(SubTerminal.scroll, 'y', type(y), (int,))
		else:
			self.__scroll__[0] = self.__scroll__[0] if x is None or x is ... else int(x)
			self.__scroll__[1] = self.__scroll__[1] if y is None or y is ... else int(y)

	def first_empty_row(self) -> int:
		my, mx = self.__stdscr__.getmaxyx()
		bg = self.__stdscr__.getbkgd()

		for y in range(0, my):
			line: bytes = self.__stdscr__.instr(y, 0, mx)

			if len(tuple(x for x in line if x != bg)) == 0:
				return y

		return -1

	def last_empty_row(self) -> int:
		my, mx = self.__stdscr__.getmaxyx()
		bg = self.__stdscr__.getbkgd()
		last_y: int = my

		for y in range(my - 1, -1, -1):
			line: bytes = self.__stdscr__.instr(y, 0, mx)

			if len(tuple(x for x in line if x != bg)) != 0:
				return last_y

			last_y = y

		return -1

	def first_empty_column(self) -> int:
		my, mx = self.__stdscr__.getmaxyx()
		bg = self.__stdscr__.getbkgd()
		last_x: int = mx

		for x in range(mx):
			for y in range(my):
				if self.__stdscr__.instr(y, x, 1)[0] != bg:
					return last_x

			last_x = x

		return -1

	def last_empty_column(self) -> int:
		my, mx = self.__stdscr__.getmaxyx()
		bg = self.__stdscr__.getbkgd()
		last_x: int = mx

		for x in range(mx - 1, -1, -1):
			for y in range(my):
				if self.__stdscr__.instr(y, x, 1)[0] != bg:
					return last_x

			last_x = x

		return -1

	def tab_size(self, size: typing.Optional[int] = ...) -> int | None:
		if size is None or size is ...:
			return self.__tab_size__
		elif not isinstance(size, int):
			raise InvalidArgumentException(SubTerminal.tab_size, 'size', type(size), (int,))
		elif size < 0:
			raise ValueError('Tab size cannot be less than zero')
		else:
			self.__tab_size__ = int(size)

	def chat(self, x: int, y: int) -> tuple[int, int]:
		full: int = self.__stdscr__.inch(x, y)
		char: int = full & 0xFF
		attr: int = (full >> 8) & 0xFF
		return char, attr

	def to_fixed(self, x: int, y: int) -> tuple[int, int]:
		sx, sy = self.__scroll__
		return x + sx, y + sy

	def from_fixed(self, x: int, y: int) -> tuple[int, int]:
		sx, sy = self.__scroll__
		return x - sx, y - sy

	def getline(self, replace_char: typing.Optional[str] = ..., prompt: typing.Optional[str] = '', x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> str:
		assert (replace_char is None or replace_char is ...) or (isinstance(replace_char, str) and len(replace_char) == 1), 'Invalid replacement character'
		chars: list[str] = []
		__chars: list[str] = []
		xoffset: int = -1
		__xoffset: int = -1
		yoffset: int = -1
		cy, cx = self.__stdscr__.getyx()
		y: int = cy if y is ... or y is None else int(y)
		x: int = cx if x is ... or x is None else int(x)
		self.putstr(prompt, x, y)
		cy, cx = self.__stdscr__.getyx()
		t1: float = time.perf_counter_ns()
		self.__terminal__.__root__.move(cy, cx)

		while (c := self.__stdscr__.getch(cy, cx + xoffset)) != 10 and c != 459 and c != 13:
			if curses.ascii.isprint(c):
				display_char: str = chr(c) if replace_char is None or replace_char is ... else replace_char

				if xoffset == -1:
					self.__stdscr__.addch(cy, cx + len(chars), display_char)
					chars.append(chr(c))
				else:
					chars.insert(xoffset, chr(c))

					for i in range(xoffset, len(chars)):
						self.__stdscr__.addch(cy, cx + i, chars[i] if replace_char is None or replace_char is ... else replace_char)

					xoffset += 1
					self.__stdscr__.move(cy, cx + xoffset)

			elif c == curses.KEY_BACKSPACE or c == 8 and len(chars):
				self.__stdscr__.delch(cy, cx + len(chars) - 1)

				if xoffset == -1:
					chars.pop()
				elif xoffset > 0:
					xoffset -= 1
					chars.pop(xoffset)

					for i in range(xoffset, len(chars)):
						self.__stdscr__.addch(cy, cx + i, chars[i] if replace_char is None or replace_char is ... else replace_char)

					self.__stdscr__.move(cy, cx + xoffset)

			elif c == curses.KEY_LEFT and (xoffset > 0 or xoffset == -1):
				_offset: int = len(chars) if xoffset == -1 else xoffset
				_char: int = self.__stdscr__.inch(cy, cx + _offset)
				char: str = chr(_char & 0xFF)
				attr: int = (_char >> 8) & 0xFF
				self.__stdscr__.addch(cy, cx + _offset, char, attr & ~curses.A_REVERSE)

				xoffset = max(0, (len(chars) - 1) if xoffset == -1 else xoffset - 1)
				xoffset = -1 if xoffset >= len(chars) else xoffset
				self.__stdscr__.move(cy, cx + (len(chars) if xoffset == -1 else xoffset))

			elif c == curses.KEY_RIGHT and xoffset != -1:
				_offset: int = len(chars) if xoffset == -1 else xoffset
				_char: int = self.__stdscr__.inch(cy, cx + _offset)
				char: str = chr(_char & 0xFF)
				attr: int = (_char >> 8) & 0xFF
				self.__stdscr__.addch(cy, cx + _offset, char, attr & ~curses.A_REVERSE)

				xoffset = min(len(chars), xoffset + 1)
				xoffset = -1 if xoffset >= len(chars) else xoffset
				self.__stdscr__.move(cy, cx + (len(chars) if xoffset == -1 else xoffset))

			elif c == curses.KEY_UP and (yoffset > 0 or yoffset == -1) and len(self.__previous_inputs__):
				_offset: int = len(chars) if xoffset == -1 else xoffset
				_char: int = self.__stdscr__.inch(cy, cx + _offset)
				char: str = chr(_char & 0xFF)
				attr: int = (_char >> 8) & 0xFF
				self.__stdscr__.addch(cy, cx + _offset, char, attr & ~curses.A_REVERSE)

				for _ in range(len(chars)):
					self.__stdscr__.delch(cy, cx)

				if yoffset == -1:
					__chars.extend(chars)
					__xoffset = xoffset
					xoffset = -1
					yoffset = len(self.__previous_inputs__) - 1
					chars.clear()
					chars.extend(self.__previous_inputs__[yoffset])
				else:
					xoffset = -1
					yoffset -= 1
					chars.clear()
					chars.extend(self.__previous_inputs__[yoffset])

				for i in range(len(chars)):
					self.__stdscr__.addch(cy, cx + i, chars[i])

				self.__stdscr__.move(cy, cx + len(chars))

			elif c == curses.KEY_DOWN and yoffset != -1 and len(self.__previous_inputs__):
				_offset: int = len(chars) if xoffset == -1 else xoffset
				_char: int = self.__stdscr__.inch(cy, cx + _offset)
				char: str = chr(_char & 0xFF)
				attr: int = (_char >> 8) & 0xFF
				self.__stdscr__.addch(cy, cx + _offset, char, attr & ~curses.A_REVERSE)

				for _ in range(len(chars)):
					self.__stdscr__.delch(cy, cx)

				yoffset += 1

				if yoffset == len(self.__previous_inputs__):
					yoffset = -1
					xoffset = __xoffset
					chars.clear()
					chars.extend(__chars)
					__chars.clear()
				else:
					xoffset = -1
					chars.clear()
					chars.extend(self.__previous_inputs__[yoffset])

				for i in range(len(chars)):
					self.__stdscr__.addch(cy, cx + i, chars[i])

				self.__stdscr__.move(cy, cx + (len(chars) if xoffset == -1 else xoffset))

			elif c == 27:
				return ''

			t2 = time.perf_counter_ns()
			delta: float = (t2 - t1) * 1e-9
			inverse: bool = delta % 1 > 0.5
			_offset: int = len(chars) if xoffset == -1 else xoffset
			_char: int = self.__stdscr__.inch(cy, cx + _offset)
			char: str = chr(_char & 0xFF)
			self.putstr(f'{"\033[7m" if inverse else ""}{char}', cx + _offset, cy)
			my, mx = self.__terminal__.__root__.getmaxyx()
			self.__stdscr__.refresh(self.__scroll__[1], self.__scroll__[0], 0, 0, my - 1, mx - 1)

		result: str = ''.join(chars)

		if len(result):
			self.__previous_inputs__.append(result)

		return result

	def get_topmost_child_at(self, x: int, y: int) -> Widget | None:
		for z_index in sorted(self.__pages__.keys(), reverse=True):
			for _id, widget in self.__pages__[z_index].items():
				if not widget.hidden and widget.has_coord(x, y):
					return widget

		for z_index in sorted(self.__widgets__.keys(), reverse=True):
			for _id, widget in self.__widgets__[z_index].items():
				if not widget.hidden and widget.has_coord(x, y):
					return widget

		return None

	def get_focus(self) -> Widget | None:
		child: Widget

		for child in (*self.widgets(), *self.subterminals()):
			if child.focused:
				return child

		return None

	def active_subterminal(self) -> SubTerminal | None:
		page: SubTerminal | None = self.__active_page__

		if page is None or page.hidden:
			return None

		while page.selected_subterminal is not None and not page.selected_subterminal.hidden:
			page = page.selected_subterminal

		return page

	def get_widget(self, _id: int) -> typing.Type[WIDGET_T]:
		for z_index, widgets in self.__widgets__.items():
			if _id in widgets:
				return widgets[_id]

		raise KeyError(f'No such widget - {_id}')

	def get_sub_terminal(self, _id: int) -> SubTerminal:
		for z_index, sub_terminals in self.__pages__.items():
			if _id in sub_terminals:
				return sub_terminals[_id]

		raise KeyError(f'No such widget - {_id}')

	def get_children_at(self, x: int, y: int) -> tuple[Widget, ...]:
		children: list[Widget] = []

		for z_index in sorted(self.__pages__.keys(), reverse=True):
			for _id, widget in self.__pages__[z_index].items():
				if widget.has_coord(x, y):
					children.append(widget)

		for z_index in sorted(self.__widgets__.keys(), reverse=True):
			for _id, widget in self.__widgets__[z_index].items():
				if widget.has_coord(x, y):
					children.append(widget)

		return tuple(children)

	def widgets(self) -> tuple[Widget]:
		ids: list[Widget] = []

		for alloc in self.__widgets__.values():
			ids.extend(alloc.values())

		return tuple(ids)

	def subterminals(self) -> tuple[SubTerminal]:
		ids: list[SubTerminal] = []

		for alloc in self.__pages__.values():
			ids.extend(alloc.values())

		return tuple(ids)

	def children(self) -> dict[int, Widget]:
		children: dict[int, Widget] = {}

		for alloc in self.__pages__.values():
			children.update(alloc)

		for alloc in self.__widgets__.values():
			children.update(alloc)

		return children

	### Widget methods
	def add_button(self, x: int, y: int, width: int, height: int, text: str, *, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_NONE,
				   border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				   color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> Button:
		widget: Button = Button(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
												border=border, highlight_border=highlight_border, active_border=active_border,
												color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_toggle_button(self, x: int, y: int, width: int, height: int, text: str, *, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_NONE,
						  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
						  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
						  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> ToggleButton:
		widget: ToggleButton = ToggleButton(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
												border=border, highlight_border=highlight_border, active_border=active_border,
												color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str = '', active_text: str = 'X',
					 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
					 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> Checkbox:
		widget: Checkbox = Checkbox(self, x, y, z_index=z_index, text=text, active_text=active_text,
													border=border, highlight_border=highlight_border, active_border=active_border,
													color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
													callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_inline_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str = '', active_text: str = 'X',
							border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
							callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> InlineCheckbox:
		widget: InlineCheckbox = InlineCheckbox(self, x, y, z_index=z_index, text=text, active_text=active_text,
																border=border, highlight_border=highlight_border, active_border=active_border,
																color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_radial_spinner(self, x: int, y: int, *, z_index: int = 0, phases: typing.Iterable[str] = ('--', '\\', '|', '/'), bg_phase_colors: typing.Optional[Enums.Color_T] | typing.Iterable[typing.Optional[Enums.Color_T]] = ..., fg_phase_colors: typing.Optional[Enums.Color_T] | typing.Iterable[typing.Optional[Enums.Color_T]] = Color(0xFFFFFF),
						   callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> RadialSpinner:
		widget: RadialSpinner = RadialSpinner(self, x, y, z_index=z_index, phases=phases, bg_phase_colors=bg_phase_colors, fg_phase_colors=fg_phase_colors,
															  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_horizontal_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str = '|', _max: float = 10, _min: float = 0, on_input: typing.Callable[[HorizontalSlider], None] = ...,
							  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
							  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> HorizontalSlider:
		widget: HorizontalSlider = HorizontalSlider(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
																	border=border, highlight_border=highlight_border, active_border=active_border,
																	color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																	callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_vertical_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str = '=', _max: float = 10, _min: float = 0, on_input: typing.Callable[[VerticalSlider], None] = ...,
							border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
							callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> VerticalSlider:
		widget: VerticalSlider = VerticalSlider(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
																border=border, highlight_border=highlight_border, active_border=active_border,
																color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_horizontal_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str = '|', _max: float = 10, _min: float = 0,
							border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
							callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> HorizontalProgressBar:
		widget: HorizontalProgressBar = HorizontalProgressBar(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
																border=border, highlight_border=highlight_border, active_border=active_border,
																color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_vertical_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str = '=', _max: float = 10, _min: float = 0,
							border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
							callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> VerticalProgressBar:
		widget: VerticalProgressBar = VerticalProgressBar(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
																border=border, highlight_border=highlight_border, active_border=active_border,
																color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_text(self, x: int, y: int, width: int, height: int, text: str, *, z_index: int = 0, justify: int = Enums.NORTH_WEST, word_wrap: int = Enums.WORDWRAP_NONE,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> Text:
		widget: Text = Text(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
											color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
											callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_dropdown(self, x: int, y: int, width: int, height: int, choices: tuple[str | AnsiStr, ...], *, display_count: int | None = None, allow_scroll_rollover: bool = False, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_WORD, on_select: typing.Optional[typing.Callable[[WIDGET_T], bool | None]] = ...,
				   border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				   color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> Dropdown:
		widget: Dropdown = Dropdown(self, x, y, width, height, choices, display_count=display_count, allow_scroll_rollover=allow_scroll_rollover, z_index=z_index, justify=justify, word_wrap=word_wrap, on_select=on_select,
												border=border, highlight_border=highlight_border, active_border=active_border,
												color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_entry(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, word_wrap: int = Enums.WORDWRAP_WORD, justify: int = Enums.NORTH_WEST, replace_chars: str = '', placeholder: typing.Optional[str | AnsiStr] = ..., cursor_blink_speed: int = 0, on_text: typing.Optional[typing.Callable[[Entry, bool], bool | str | AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[Entry, AnsiStr], bool | str | AnsiStr | None]] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> Entry:
		widget: Entry = Entry(self, x, y, width, height, z_index=z_index, word_wrap=word_wrap, justify=justify, replace_chars=replace_chars, placeholder=placeholder, cursor_blink_speed=cursor_blink_speed, on_text=on_text, on_input=on_input,
											  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
											  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_image(self, x: int, y: int, width: int, height: int, image: str | AnsiStr | numpy.ndarray | PIL.Image.Image, *, z_index: int = 0, div: typing.Optional[int] = ..., use_subpad: bool = True,
				   border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				   color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> Image:
		widget: Image = Image(self, x, y, width, height, image, z_index=z_index, div=div, use_subpad=use_subpad,
												border=border, highlight_border=highlight_border, active_border=active_border,
												color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_sub_terminal(self, x: int, y: int, width: int, height: int, *, title: typing.Optional[str] = ..., z_index: int = 0, transparent: bool = False,
						 border: BorderInfo = ..., highlight_border: BorderInfo = ..., active_border: BorderInfo = ...,
						 callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> SubTerminal:
		terminal: SubTerminal = SubTerminal(self, x, y, width, height, title, z_index=z_index, transparent=transparent,
															border=border, highlight_border=highlight_border, active_border=active_border,
															callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(terminal)

		if z_index in self.__pages__:
			self.__pages__[z_index][_id] = terminal
		else:
			self.__pages__[z_index] = {_id: terminal}

		return terminal

	def add_widget(self, cls: WIDGET_T, *args, z_index: int = 0, **kwargs) -> WIDGET_T:
		assert issubclass(cls, Widget)
		widget: WIDGET_T = cls(self, *args, **kwargs)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	### Properties
	@property
	def screen(self) -> _curses.window:
		return self.__stdscr__

	@property
	def enabled(self) -> bool:
		return self.__terminal__.enabled

	@property
	def exit_code(self) -> int | None:
		return self.__terminal__.exit_code

	@property
	def current_tick(self) -> int:
		return self.__terminal__.current_tick

	@property
	def mouse(self) -> MouseInfo:
		return self.__last_mouse_info__

	@property
	def transparent(self) -> bool:
		return self.__transparent__

	@transparent.setter
	def transparent(self, transparent: bool) -> None:
		self.__transparent__ = bool(transparent)

	@property
	def title(self) -> str:
		return self.__title__

	@title.setter
	def title(self, title: str) -> None:
		self.__title__ = str(title)

	@property
	def selected_subterminal(self) -> SubTerminal | None:
		return self.__active_page__

	@property
	def default_bg(self) -> Color:
		return Color.fromcursesrgb(*curses.color_content(0))

	@property
	def default_fg(self) -> Color:
		return Color.fromcursesrgb(*curses.color_content(7))


### Serialized Widgets
class SerializedWidget:
	@classmethod
	def __expand__(cls) -> SerializedWidget:
		return SerializedWidget.__new__(cls)

	def __init__(self, conn: WinNamedPipe, widget: Widget | None):
		assert not conn.closed, 'The pipe is closed'

		self.__conn__: WinNamedPipe = conn
		self.__next_id__: int = -1
		self.__widget__: Widget | None = widget
		self.__wid__: int = -1 if widget is None else widget.id
		self.__closed_ids__: list[int] = []
		self.__events__: dict[int, Promise] = {}
		self.__state__: bool = True

	def __del__(self):
		self.__state__ = False

	def __setstate__(self, state: dict[str, typing.Any]) -> None:
		self.__init__(state['__conn__'], None)
		self.__wid__ = state['__wid__']

	def __getstate__(self) -> dict[str, typing.Any]:
		attributes: dict[str, typing.Any] = self.__dict__.copy()
		del attributes['__next_id__']
		del attributes['__widget__']
		del attributes['__closed_ids__']
		del attributes['__events__']
		return attributes

	def __fulfill__(self, _id: int, success: bool, data: typing.Any) -> None:
		if _id in self.__events__:
			promise = self.__events__[_id]

			if success:
				promise.resolve(data)
			else:
				promise.throw(data)

			del self.__events__[_id]
			self.__closed_ids__.append(_id)

	def send(self, method_name: str, *args, **kwargs) -> ThreadedPromise | Promise:
		if self.__conn__.closed:
			raise IOError('The pipe is closed')
		elif not isinstance(method_name, str):
			raise InvalidArgumentException(SerializedWidget.send, 'method_name', type(method_name), (str,))

		try:
			_id: int

			if len(self.__closed_ids__):
				_id = self.__closed_ids__.pop()
			else:
				_id: int = self.__next_id__
				self.__next_id__ -= 1

			promise: Promise = Promise()
			self.__events__[_id] = promise
			self.__conn__.send((self.__wid__, str(method_name), _id, args, kwargs))
			return promise
		except IOError as e:
			pseudo: Promise = Promise()
			pseudo.throw(e)
			return pseudo

	def close(self) -> ThreadedPromise:
		return self.send('close()')

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[WIDGET_T], None]] = ...) -> ThreadedPromise:
		return self.send('configure()', x=x, y=y, z=z, width=width, height=height, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

	def set_position(self, x: typing.Optional[int], y: typing.Optional[int]) -> ThreadedPromise:
		return self.send('set_position()', x, y)

	def move(self, x: typing.Optional[int], y: typing.Optional[int] = ...) -> ThreadedPromise:
		return self.send('move()', x, y)

	def draw(self) -> ThreadedPromise:
		return self.send('draw()')

	def show(self) -> ThreadedPromise:
		return self.send('show()')

	def hide(self) -> ThreadedPromise:
		return self.send('hide()')

	def focus(self) -> ThreadedPromise:
		return self.send('focus()')

	def unfocus(self) -> ThreadedPromise:
		return self.send('unfocus()')

	def draw_border(self, border: BorderInfo | None) -> ThreadedPromise:
		return self.send('draw_border()', border)

	def has_coord(self, x: int, y: int) -> ThreadedPromise:
		return self.send('has_coord()', x, y)

	def parent_stack(self) -> ThreadedPromise:
		return self.send('parent_stack()')

	def topmost_parent(self) -> ThreadedPromise:
		return self.send('topmost_parent()')

	def global_pos(self) -> ThreadedPromise:
		return self.send('global_pos()')

	@property
	def closed(self) -> ThreadedPromise:
		return self.send('closed')

	@property
	def hidden(self) -> ThreadedPromise:
		return self.send('hidden')

	@property
	def id(self) -> int:
		return self.__wid__

	@property
	def x(self) -> ThreadedPromise:
		return self.send('x')

	@property
	def y(self) -> ThreadedPromise:
		return self.send('y')

	@property
	def width(self) -> ThreadedPromise:
		return self.send('width')

	@property
	def height(self) -> ThreadedPromise:
		return self.send('height')

	@property
	def z_index(self) -> ThreadedPromise:
		return self.send('z_index')

	@property
	def position(self) -> ThreadedPromise:
		return self.send('position')

	@property
	def size(self) -> ThreadedPromise:
		return self.send('size')

	@property
	def parent(self) -> ThreadedPromise:
		return self.send('parent')

	@property
	def is_mouse_pressed(self) -> ThreadedPromise:
		return self.send('is_mouse_pressed')

	@property
	def is_mouse_inside(self) -> ThreadedPromise:
		return self.send('is_mouse_inside')

	@property
	def focused(self) -> ThreadedPromise:
		return self.send('focused')

'''
		if self.__word_wrap__ == Enums.WORDWRAP_ALL:
			line: list[tuple[str, AnsiStr.AnsiFormat]] = []

			for char, _ansi in self.__text__:
				if char == '\n':
					lines.append(AnsiStr.from_pairs(line))
					line.clear()
				elif len(line) < self.width:
					line.append((char, _ansi))
				elif len(lines) >= self.height:
					break
				else:
					lines.append(AnsiStr.from_pairs(line))
					line.clear()
					line.append((char, _ansi))

			if len(line) and len(lines) < self.height:
				lines.append(AnsiStr.from_pairs(line))

		elif self.__word_wrap__ == Enums.WORDWRAP_WORD:
			word: list[tuple[str, AnsiStr.AnsiFormat]] = []
			text: list[list[AnsiStr]] = [[]]
			length: int = 0

			for char, _ansi in self.__text__:
				if char.isspace() and len(word):
					if length + len(word) <= self.width:
						_word: AnsiStr = AnsiStr.from_pairs(word)
						text[-1].append(_word)
						length += len(_word)
						word.clear()
					else:
						_word: AnsiStr = AnsiStr.from_pairs(word)
						text.append([_word])
						length = len(_word)
						word.clear()

					if char == '\n':
						text.append([])
						length = 0
					else:
						text[-1].append(char)
						length += 1
				elif not char.isspace():
					word.append((char, _ansi))

			if len(word) and length + len(word) <= self.width:
				text[-1].append(AnsiStr.from_pairs(word))
			elif len(word):
				text.append([AnsiStr.from_pairs(word)])

			lines.extend(AnsiStr(''.join(str(x) for x in line))[:self.width] for i, line in enumerate(text) if i < self.height)
		elif self.__word_wrap__ == Enums.WORDWRAP_NONE:
			line: list[tuple[str, AnsiStr.AnsiFormat]] = []

			for char, _ansi in self.__text__:
				if char == '\n':
					lines.append(AnsiStr.from_pairs(line))
					line.clear()
				elif len(line) <= self.width:
					line.append((char, _ansi))
				elif len(lines) >= self.height:
					break

			if len(line) and len(lines) < self.height:
				lines.append(AnsiStr.from_pairs(line))
		else:
			raise RuntimeError(f'Invalid word wrap: \'{self.__word_wrap__}\'')
'''