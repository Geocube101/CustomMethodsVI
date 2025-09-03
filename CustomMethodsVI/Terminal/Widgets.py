from __future__ import annotations

import os
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

from .. import Concurrent
from .. import Connection
from .. import Exceptions
from .. import Iterable
from .. import Misc
from .. import Terminal


def parse_color(color: Terminal.Enums.Color_T, error: typing.Optional[BaseException] = ...) -> typing.Optional[Terminal.Enums]:
	if isinstance(color, (types.NoneType, Terminal.Enums.Color)):
		return color
	elif isinstance(color, int) and 0 <= int(color) <= 0xFFFFFF:
		return Terminal.Enums.Color(int(color))
	elif isinstance(color, int) and color < 0:
		return Terminal.Enums.Color.fromcurses(-int(color))
	elif isinstance(color, int):
		raise ValueError(f'Integer value \'{color}\' must either be a curses color or RGB value in range 0x000000 to 0xFFFFFF')
	elif isinstance(color, (tuple, list)) and len(color) == 3 and all(isinstance(x, int) and 0 <= int(x) <= 0xFF for x in color):
		return Terminal.Enums.Color.fromrgb(*color)
	elif isinstance(color, (tuple, list)) and len(color) == 3 and all(isinstance(x, int) and 0 <= int(x) <= 1000 for x in color):
		return Terminal.Enums.Color.fromcursesrgb(*color)
	elif isinstance(color, str) and color[0] == '#':
		return Terminal.Enums.Color.fromhex(color)
	elif color is None or color is ...:
		return None
	elif isinstance(error, BaseException):
		raise error
	else:
		return None

### Standard Widgets
class MyWidget:
	"""
	Base Widget class
	"""

	class MySerializedWidget:
		"""
		Base SerializedWidget class
		"""

		@classmethod
		def __expand__(cls) -> MyWidget.MySerializedWidget:
			return MyWidget.MySerializedWidget.__new__(cls)

		def __init__(self, conn: Connection.NamedPipe, widget: typing.Optional[MyWidget]):
			"""
			Base SerializedWidget class
			:param conn: The IPC pipe
			:param widget: The widget to serialize
			:raises AssertionError: If 'conn' is not a Connection.NamedPipe instance
			:raises AssertionError: If 'widget' is not a Widget instance
			:raises AssertionError: If 'conn' is closed
			"""

			assert isinstance(conn, Connection.NamedPipe), 'Not a Connection.NamedPipe instance'
			assert not conn.closed, 'The pipe is closed'
			assert widget is None or isinstance(widget, MyWidget), 'Not a widget'

			self.__conn__: Connection.NamedPipe = conn
			self.__next_id__: int = -1
			self.__widget__: typing.Optional[MyWidget] = widget
			self.__wid__: int = -1 if widget is None else widget.id
			self.__closed_ids__: list[int] = []
			self.__events__: dict[int, Concurrent.Promise] = {}
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
			"""
			Sends a response to this widget's query
			:param _id: The response ID
			:param success: Whether response was successfull
			:param data: The response data or error
			"""

			if _id in self.__events__:
				promise = self.__events__[_id]

				if success:
					promise.resolve(data)
				else:
					promise.throw(data)

				del self.__events__[_id]
				self.__closed_ids__.append(_id)

		def send(self, method_name: str, *args, **kwargs) -> Concurrent.ThreadedPromise[typing.Any] | Concurrent.Promise[typing.Any]:
			"""
			Sends a request to the remote window's widget
			:param method_name: The method or attribute name
			:param args: The method positional arguments
			:param kwargs: The method keyword arguments
			:return: A promise with the response
			:raises InvalidArgumentException: If 'method_name' is not a string
			"""

			if self.__conn__.closed:
				raise IOError('The pipe is closed')
			elif not isinstance(method_name, str):
				raise Exceptions.InvalidArgumentException(MyWidget.MySerializedWidget.send, 'method_name', type(method_name), (str,))

			try:
				_id: int

				if len(self.__closed_ids__):
					_id = self.__closed_ids__.pop()
				else:
					_id: int = self.__next_id__
					self.__next_id__ -= 1

				promise: Concurrent.Promise = Concurrent.Promise()
				self.__events__[_id] = promise
				self.__conn__.send((self.__wid__, str(method_name), _id, args, kwargs))
				return promise
			except IOError as e:
				pseudo: Concurrent.Promise = Concurrent.Promise()
				pseudo.throw(e)
				return pseudo

		def close(self) -> Concurrent.ThreadedPromise[None]:
			"""
			Destroys this widget
			:return: A promise
			"""

			return self.send('close()')

		def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
					  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], typing.Any]] = ...,
					  on_focus: typing.Optional[typing.Callable[[MyWidget], typing.Any]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], typing.Any]] = ...,
					  on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], typing.Any]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], typing.Any]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], typing.Any]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], typing.Any]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], typing.Any]] = ...,
					  on_tick: typing.Optional[typing.Callable[[MyWidget, int], typing.Any]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], typing.Any]] = ...) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this widget
			Any value not supplied will not be updated
			:param x: The widget's x position
			:param y: The widget's y position
			:param z: The widget's z-index, higher is drawn last
			:param width: The widget's width in characters
			:param height: The widget's height in characters
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:return: A promise
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If 'width' is not an integer
			:raises InvalidArgumentException: If 'height' is not an integer
			:raises InvalidArgumentException: If any supplied callback is not callable
			"""

			return self.send('configure()', x=x, y=y, z=z, width=width, height=height,
							 callback=callback,
							 on_focus=on_focus, off_focus=off_focus,
							 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							 on_tick=on_tick, on_close=on_close)

		def set_position(self, x: typing.Optional[int], y: typing.Optional[int]) -> Concurrent.ThreadedPromise[None]:
			"""
			Sets this widget's position
			:param x: The widget's x position
			:param y: The widget's y position
			:return: A promise
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			"""

			return self.send('set_position()', x, y)

		def move(self, x: typing.Optional[int], y: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[None]:
			"""
			Moves this widget
			:param x: The amount to move in x direction
			:param y: The amount to move in y direction
			:return: A promise
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			"""

			return self.send('move()', x, y)

		def draw(self) -> Concurrent.ThreadedPromise[None]:
			"""
			Draws this widget
			Called internally by widget's parent
			:return: A promise
			"""

			return self.send('draw()')

		def show(self) -> Concurrent.ThreadedPromise[None]:
			"""
			Shows this widget
			:return: A promise
			"""

			return self.send('show()')

		def hide(self) -> Concurrent.ThreadedPromise[None]:
			"""
			Hides this widget
			:return: A promise
			"""

			return self.send('hide()')

		def focus(self) -> Concurrent.ThreadedPromise[None]:
			"""
			Focuses this widget
			:return: A promise
			"""

			return self.send('focus()')

		def unfocus(self) -> Concurrent.ThreadedPromise[None]:
			"""
			Unfocuses this widget
			If focused, focus is reverted to parent
			:return: A promise
			"""

			return self.send('unfocus()')

		def draw_border(self, border: typing.Optional[Terminal.Struct.BorderInfo]) -> Concurrent.ThreadedPromise[None]:
			"""
			Draws this widget's border if applicable
			:param border: The border to draw
			:return: A promise
			"""

			return self.send('draw_border()', border)

		def has_coord(self, x: int, y: int) -> Concurrent.ThreadedPromise[bool]:
			"""
			:param x: The x position to check
			:param y: The y position to check
			:return: A promise with whether the specified point is within this widget's bounds
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			"""

			return self.send('has_coord()', x, y)

		def parent_stack(self) -> Concurrent.ThreadedPromise[tuple[MySubTerminal.MySerializedSubTerminal | Terminal.WindowTerminal, ...]]:
			"""
			:return: A promise with all terminals and sub-terminals this widget is bound to
			"""

			return self.send('parent_stack()')

		def topmost_parent(self) -> Concurrent.ThreadedPromise[Terminal.WindowTerminal]:
			"""
			:return: A promise with this widget's topmost parent
			"""

			return self.send('topmost_parent()')

		def global_pos(self) -> Concurrent.ThreadedPromise[tuple[int, int]]:
			"""
			:return: A promise with this widget's coordinates relative to its topmost parent
			"""

			return self.send('global_pos()')

		@property
		def closed(self) -> Concurrent.ThreadedPromise[bool]:
			"""
			:return: A promise with whether this widget is destroyed
			"""

			return self.send('closed')

		@property
		def hidden(self) -> Concurrent.ThreadedPromise[bool]:
			"""
			:return: A promise with whether this widget is hidden
			"""

			return self.send('hidden')

		@property
		def id(self) -> int:
			"""
			:return: This widget's ID
			"""

			return self.__wid__

		@property
		def x(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with this widget's x position
			"""

			return self.send('x')

		@property
		def y(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with this widget's y position
			"""

			return self.send('y')

		@property
		def width(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with this widget's width
			"""

			return self.send('width')

		@property
		def height(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with this widget's width
			"""

			return self.send('height')

		@property
		def z_index(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with this widget's z-index
			"""

			return self.send('z_index')

		@property
		def position(self) -> Concurrent.ThreadedPromise[tuple[int, int]]:
			"""
			:return: A promise with this widget's x and y position
			"""

			return self.send('position')

		@property
		def size(self) -> Concurrent.ThreadedPromise[tuple[int, int]]:
			"""
			:return: A promise with this widget's width and height
			"""

			return self.send('size')

		@property
		def parent(self) -> Concurrent.ThreadedPromise[Terminal.WindowTerminal | MySubTerminal.MySerializedSubTerminal]:
			"""
			:return: A promise with this widget's parent
			"""

			return self.send('parent')

		@property
		def is_mouse_pressed(self) -> Concurrent.ThreadedPromise[bool]:
			"""
			:return: A promise with whether the mouse is pressed within this widget's bounds
			"""

			return self.send('is_mouse_pressed')

		@property
		def is_mouse_inside(self) -> Concurrent.ThreadedPromise[bool]:
			"""
			:return: A promise with whether the mouse is within this widget's bounds and this widget is the topmost widget
			"""

			return self.send('is_mouse_inside')

		@property
		def focused(self) -> Concurrent.ThreadedPromise[bool]:
			"""
			:return: A promise with whether this widget has focus
			"""

			return self.send('focused')

	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, z: int, width: int, height: int, *,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], typing.Any]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], typing.Any]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], typing.Any]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], typing.Any]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], typing.Any]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], typing.Any]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], typing.Any]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], typing.Any]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], typing.Any]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], typing.Any]] = ...):
		"""
		Base Widget class
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: The widget's x position
		:param y: The widget's y position
		:param z: The widget's z-index, higher is drawn last
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If any supplied callback is not callable
		"""

		if not isinstance(parent, (Terminal.Terminal.Terminal, MySubTerminal)):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'parent', type(parent), (Terminal.Terminal, MySubTerminal))
		if not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'x', type(x), (int,))
		if not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'y', type(y), (int,))
		if not isinstance(z, int):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'z', type(z), (int,))
		if not isinstance(width, int):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'width', type(width), (int,))
		if not isinstance(height, int):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'height', type(height), (int,))

		if callback is not None and callback is not ... and not callable(callback):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'callback', type(callback))
		elif on_focus is not None and on_focus is not ... and not callable(on_focus):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'on_focus', type(on_focus))
		elif off_focus is not None and off_focus is not ... and not callable(off_focus):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'off_focus', type(off_focus))
		elif on_mouse_enter is not None and on_mouse_enter is not ... and not callable(on_mouse_enter):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'on_mouse_enter', type(on_mouse_enter))
		elif on_mouse_leave is not None and on_mouse_leave is not ... and not callable(on_mouse_leave):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'on_mouse_leave', type(on_mouse_leave))
		elif on_mouse_press is not None and on_mouse_press is not ... and not callable(on_mouse_press):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'on_mouse_press', type(on_mouse_press))
		elif on_mouse_release is not None and on_mouse_release is not ... and not callable(on_mouse_release):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'on_mouse_release', type(on_mouse_release))
		elif on_mouse_click is not None and on_mouse_click is not ... and not callable(on_mouse_click):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'on_mouse_click', type(on_mouse_click))
		elif on_tick is not None and on_tick is not ... and not callable(on_tick):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'on_tick', type(on_tick))
		elif on_close is not None and on_close is not ... and not callable(on_close):
			raise Exceptions.InvalidArgumentException(MyWidget.__init__, 'on_close', type(on_close))

		self.__terminal__: Terminal.Terminal.Terminal | MySubTerminal = parent
		self.__position__: list[int] = [int(x), int(y), int(z), int(width), int(height)]
		self.__hidden__: bool = False
		self.__hovering__: bool = False
		self.__hovering_top__: bool = False
		self.__pressed__: bool = False
		self.__focused__: bool = False
		self.__closed__: bool = False
		self.__tick__: int = 0
		self.__general_callback__: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = callback
		self.__focus_callback__: list[typing.Callable[[MyWidget], None]] = [on_focus, off_focus]
		self.__mouse_callback__: list[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = [on_mouse_enter, on_mouse_leave, on_mouse_press, on_mouse_release, on_mouse_click]
		self.__on_tick__: typing.Callable[[MyWidget, int], None] = on_tick
		self.__on_close__: typing.Callable[[MyWidget], None] = on_close

	def __reduce__(self) -> tuple[typing.Callable, tuple, dict]:
		topmost: Terminal.Terminal.WindowTerminal.SubprocessTerminal | Terminal.Terminal.Terminal = self.topmost_parent()
		assert isinstance(topmost, Terminal.Terminal.WindowTerminal.SubprocessTerminal), 'Cannot pickle main process widget'
		serializer: type[MyWidget.MySerializedWidget] = self.__serializer__
		assert isinstance(serializer, type) and issubclass(serializer, MyWidget.MySerializedWidget), 'Serializer is not a type or not a subclass of MySerializedWidget'
		serialized: MyWidget.MySerializedWidget = serializer(topmost.__widget_pipe__, self)
		return serializer.__expand__, (), serialized.__getstate__()

	def __hash__(self) -> int:
		return id(self)

	def __eq__(self, other):
		return other is self

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

	def __wordwrap__(self, text: Terminal.Struct.AnsiStr, lines: list[Terminal.Struct.AnsiStr], word_wrap: int, width: typing.Optional[int] = ..., height: typing.Optional[int] = ...) -> None:
		width: int = self.width if width is None or width is ... else int(width)
		height: int = self.height if height is None or height is ... else int(height)

		if word_wrap == Terminal.Enums.WORDWRAP_ALL:
			line: list[tuple[str, Terminal.Struct.AnsiStr.AnsiFormat]] = []

			for char, _ansi in text.pairs():
				if char == '\n':
					lines.append(Terminal.Struct.AnsiStr.from_pairs(line))
					line.clear()
				elif len(line) < width:
					line.append((char, _ansi))
				elif len(lines) >= height:
					break
				else:
					lines.append(Terminal.Struct.AnsiStr.from_pairs(line))
					line.clear()
					line.append((char, _ansi))

			if len(line) and len(lines) < height:
				lines.append(Terminal.Struct.AnsiStr.from_pairs(line))

		elif word_wrap == Terminal.Enums.WORDWRAP_WORD:
			word: list[tuple[str, Terminal.Struct.AnsiStr.AnsiFormat]] = []
			_text: list[list[Terminal.Struct.AnsiStr | str]] = [[]]
			length: int = 0

			for char, _ansi in text.pairs():
				if char.isspace() and len(word):
					if length + len(word) <= width:
						_word: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr.from_pairs(word)
						_text[-1].append(_word)
						length += len(_word)
						word.clear()
					else:
						_word: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr.from_pairs(word)
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
				_text[-1].append(Terminal.Struct.AnsiStr.from_pairs(word))
			elif len(word):
				_text.append([Terminal.Struct.AnsiStr.from_pairs(word)])

			lines.extend(Terminal.Struct.AnsiStr(''.join(str(x) for x in line))[:width] for i, line in enumerate(_text) if i < height)
		elif word_wrap == Terminal.Enums.WORDWRAP_NONE:
			line: list[tuple[str, Terminal.Struct.AnsiStr.AnsiFormat]] = []

			for char, _ansi in text.pairs():
				if char == '\n':
					lines.append(Terminal.Struct.AnsiStr.from_pairs(line))
					line.clear()
				elif len(line) <= width:
					line.append((char, _ansi))
				elif len(lines) >= height:
					break

			if len(line) and len(lines) < height:
				lines.append(Terminal.Struct.AnsiStr.from_pairs(line))
		else:
			raise RuntimeError(f'Invalid word wrap: \'{word_wrap}\'')

	def close(self) -> None:
		"""
		Destroys this widget
		"""

		if not self.__closed__ and callable(self.__on_close__):
			self.__on_close__(self)

		if not self.__closed__ and callable(self.__general_callback__):
			self.__general_callback__(self, 'close')

		self.__closed__ = True

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param z: The widget's z-index, higher is drawn last
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If any supplied callback is not callable
		"""

		if x is not ... and x is not None and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'x', type(x), (int,))
		if y is not ... and y is not None and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'y', type(y), (int,))
		if z is not ... and z is not None and not isinstance(z, int):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'z', type(z), (int,))
		if width is not ... and width is not None and not isinstance(width, int):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'width', type(width), (int,))
		if height is not ... and height is not None and not isinstance(height, int):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'height', type(height), (int,))

		if callback is not None and callback is not ... and not callable(callback):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'callback', type(callback))
		elif on_focus is not None and on_focus is not ... and not callable(on_focus):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'on_focus', type(on_focus))
		elif off_focus is not None and off_focus is not ... and not callable(off_focus):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'off_focus', type(off_focus))
		elif on_mouse_enter is not None and on_mouse_enter is not ... and not callable(on_mouse_enter):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'on_mouse_enter', type(on_mouse_enter))
		elif on_mouse_leave is not None and on_mouse_leave is not ... and not callable(on_mouse_leave):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'on_mouse_leave', type(on_mouse_leave))
		elif on_mouse_press is not None and on_mouse_press is not ... and not callable(on_mouse_press):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'on_mouse_press', type(on_mouse_press))
		elif on_mouse_release is not None and on_mouse_release is not ... and not callable(on_mouse_release):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'on_mouse_release', type(on_mouse_release))
		elif on_mouse_click is not None and on_mouse_click is not ... and not callable(on_mouse_click):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'on_mouse_click', type(on_mouse_click))
		elif on_tick is not None and on_tick is not ... and not callable(on_tick):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'on_tick', type(on_tick))
		elif on_close is not None and on_close is not ... and not callable(on_close):
			raise Exceptions.InvalidArgumentException(MyWidget.configure, 'on_close', type(on_close))

		self.__position__[0] = self.__position__[0] if x is ... or x is None else int(x)
		self.__position__[1] = self.__position__[1] if y is ... or y is None else int(y)
		self.__position__[2] = self.__position__[2] if z is ... or z is None else int(z)
		self.__position__[3] = self.__position__[3] if width is ... or width is None else int(width)
		self.__position__[4] = self.__position__[4] if height is ... or height is None else int(height)

		self.__general_callback__: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = self.__general_callback__ if callback is ... else callback
		self.__focus_callback__[0] = self.__focus_callback__[0] if on_focus is ... else on_focus
		self.__focus_callback__[1] = self.__focus_callback__[1] if off_focus is ... else off_focus

		self.__mouse_callback__[0] = self.__mouse_callback__[0] if on_mouse_enter is ... else on_mouse_enter
		self.__mouse_callback__[1] = self.__mouse_callback__[1] if on_mouse_leave is ... else on_mouse_leave
		self.__mouse_callback__[2] = self.__mouse_callback__[2] if on_mouse_press is ... else on_mouse_press
		self.__mouse_callback__[3] = self.__mouse_callback__[3] if on_mouse_release is ... else on_mouse_release
		self.__mouse_callback__[4] = self.__mouse_callback__[4] if on_mouse_click is ... else on_mouse_click

		self.__on_tick__: typing.Callable[[MyWidget, int], None] = self.__on_tick__ if on_tick is ... else on_tick
		self.__on_close__: typing.Callable[[MyWidget], None] = self.__on_close__ if on_close is ... else on_close

	def set_position(self, x: typing.Optional[int], y: typing.Optional[int]) -> None:
		"""
		Sets this widget's position
		:param x: The widget's x position
		:param y: The widget's y position
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		if x is not None and x is not ... and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(MyWidget.set_position, 'x', type(x), (int,))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(MyWidget.set_position, 'y', type(y), (int,))
		else:
			self.__position__[0] = self.__position__[0] if x is None or x is ... else int(x)
			self.__position__[1] = self.__position__[1] if y is None or y is ... else int(y)

	def move(self, x: typing.Optional[int], y: typing.Optional[int] = ...) -> None:
		"""
		Moves this widget
		:param x: The amount to move in x direction
		:param y: The amount to move in y direction
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		if x is not None and x is not ... and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(MyWidget.set_position, 'x', type(x), (int,))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(MyWidget.set_position, 'y', type(y), (int,))
		else:
			self.__position__[0] += 0 if x is None or x is ... else int(x)
			self.__position__[1] += 0 if y is None or y is ... else int(y)

	def draw(self) -> None:
		"""
		Draws this widget
		Called internally by widget's parent
		"""

		self.__tick__ += 1

		if callable(self.__on_tick__):
			self.__on_tick__(self, self.__tick__)

		if callable(self.__general_callback__):
			self.__general_callback__(self, 'tick', self.__tick__)

		mouse_info: Terminal.Struct.MouseInfo = self.parent.mouse
		mouse_x: int = mouse_info.pos_x
		mouse_y: int = mouse_info.pos_y
		mouse_over: bool = self.has_coord(mouse_x, mouse_y)
		mouse_inside: bool = mouse_over and self.__terminal__.get_topmost_child_at(mouse_x, mouse_y) is self
		mouse_enter: typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]
		mouse_leave: typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]
		mouse_press: typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]
		mouse_release: typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]
		mouse_click: typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]
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
		"""
		Redraws this widget after terminal color clear
		This method can be used for initial drawing of a widget
		"""

		pass

	def show(self) -> None:
		"""
		Shows this widget
		"""

		self.__hidden__ = False

	def hide(self) -> None:
		"""
		Hides this widget
		If focused, focus is reverted to parent
		"""

		self.__hidden__ = True

		if self.focused:
			self.parent.set_focus(None)

	def focus(self) -> None:
		"""
		Focuses this widget
		"""

		if not self.focused:
			self.parent.set_focus(self)

	def unfocus(self) -> None:
		"""
		Unfocuses this widget
		If focused, focus is reverted to parent
		"""

		if self.focused:
			self.parent.set_focus(None)

	def draw_border(self, border: typing.Optional[Terminal.Struct.BorderInfo]) -> None:
		"""
		Draws this widget's border if applicable
		:param border: The border to draw
		"""

		if border is None:
			return
		elif border is ...:
			border = Terminal.Struct.BorderInfo()
		elif not isinstance(border, Terminal.Struct.BorderInfo):
			raise Exceptions.InvalidArgumentException(MyWidget.draw_border, 'border', type(border), (Terminal.Struct.BorderInfo,))

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
		"""
		:param x: The x position to check
		:param y: The y position to check
		:return: Whether the specified point is within this widget's bounds
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		if not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(MyWidget.set_position, 'x', type(x), (int,))
		elif not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(MyWidget.set_position, 'y', type(y), (int,))

		cx, cy, _, w, h = self.__position__
		return cx <= x < cx + w and cy <= y < cy + h

	def parent_stack(self) -> tuple[MySubTerminal | Terminal.Terminal, ...]:
		"""
		:return: All terminals and sub-terminals this widget is bound to
		"""

		parents: list[MySubTerminal | Terminal.Terminal] = [self.__terminal__]

		while isinstance(parents[-1], MySubTerminal):
			parents.append(parents[-1].parent)

		return tuple(parents)

	def topmost_parent(self) -> Terminal.Terminal:
		"""
		:return: The topmost terminal this widget is bound to
		"""

		parent: Terminal.Terminal.Terminal | MySubTerminal = self.__terminal__

		while isinstance(parent, MySubTerminal):
			parent = parent.parent

		return parent

	def global_pos(self) -> tuple[int, int]:
		"""
		:return: This widget's coordinates relative to its topmost parent
		"""

		x = self.x
		y = self.y

		for parent in self.parent_stack():
			if isinstance(parent, MySubTerminal):
				x += parent.x
				y += parent.y

		return x, y

	@property
	def closed(self) -> bool:
		"""
		:return: Whether this widget is destroyed
		"""

		return self.__closed__

	@property
	def hidden(self) -> bool:
		"""
		:return: Whether this widget is hidden
		"""

		return self.__hidden__

	@property
	def id(self) -> int:
		"""
		:return: This widget's ID
		"""

		return id(self)

	@property
	def x(self) -> int:
		"""
		:return: This widget's x position
		"""

		return self.__position__[0]

	@property
	def y(self) -> int:
		"""
		:return: This widget's y position
		"""

		return self.__position__[1]

	@property
	def width(self) -> int:
		"""
		:return: This widget's width
		"""

		return self.__position__[3]

	@property
	def height(self) -> int:
		"""
		:return: This widget's height
		"""

		return self.__position__[4]

	@property
	def z_index(self) -> int:
		"""
		:return: This widget's z-index
		"""

		return self.__position__[2]

	@property
	def position(self) -> tuple[int, int]:
		"""
		:return: This widget's x and y position
		"""

		return self.__position__[0], self.__position__[1]

	@property
	def size(self) -> tuple[int, int]:
		"""
		:return: This widget's width and height
		"""

		return self.__position__[3], self.__position__[4]

	@property
	def parent(self) -> Terminal.Terminal.Terminal | MySubTerminal:
		"""
		:return: This widget's immediate parent
		"""

		return self.__terminal__

	@property
	def is_mouse_pressed(self) -> bool:
		"""
		:return: Whether the mouse is pressed within this widget's bounds
		"""

		return self.__pressed__

	@property
	def is_mouse_over(self) -> bool:
		"""
		:return: Whether the mouse is within this widget's bounds
		"""

		return self.__hovering__

	@property
	def is_mouse_inside(self) -> bool:
		"""
		:return: Whether the mouse is within this widget's bounds and this widget is the topmost widget
		"""

		return self.__hovering_top__

	@property
	def focused(self) -> bool:
		"""
		:return: Whether this widget has focus
		"""

		return self.__focused__

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		"""
		:return: The serializer class used to serialize this widget
		"""

		return MyWidget.MySerializedWidget


class MyActivatableWidget(MyWidget):
	"""
	Base ActivatableWidget class
	Supports highlight and active colors and borders
	"""

	class MySerializedActivatableWidget(MyWidget.MySerializedWidget):
		def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
					  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
					  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
					  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					  ) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this widget
			Any value not supplied will not be updated
			:param x: The widget's x position
			:param y: The widget's y position
			:param z: The widget's z-index, higher is drawn last
			:param width: The widget's width in characters
			:param height: The widget's height in characters
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If 'width' is not an integer
			:raises InvalidArgumentException: If 'height' is not an integer
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises ValueError: If 'width' <= 2 or 'height' < 1
			"""

			return self.send('configure()', x=x, y=y, z=z, width=width, height=height,
							 border=border, highlight_border=highlight_border, active_border=active_border,
							 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
							 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
							 callback=callback,
							 on_focus=on_focus, off_focus=off_focus,
							 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							 on_tick=on_tick, on_close=on_close)

		@property
		def mode(self) -> Concurrent.ThreadedPromise[int]:
			"""
			2 if active (clicked)
			1 if hovered (mouse inside)
			0 if normal
			:return: A promise with the mode of this widget
			"""

			return self.send('fg_color')

		@property
		def fg_color(self) -> Concurrent.ThreadedPromise[Terminal.Struct.Color]:
			"""
			:return: A promise with this button's foreground color
			"""

			return self.send('fg_color')

		@property
		def highlight_fg_color(self) -> Concurrent.ThreadedPromise[Terminal.Struct.Color]:
			"""
			:return: A promise with this button's foreground color when hovered
			"""

			return self.send('highlight_fg_color')

		@property
		def active_fg_color(self) -> Concurrent.ThreadedPromise[Terminal.Struct.Color]:
			"""
			:return: A promise with this button's foreground color when clicked
			"""

			return self.send('active_fg_color')

		@property
		def bg_color(self) -> Concurrent.ThreadedPromise[Terminal.Struct.Color]:
			"""
			:return: A promise with this button's background color
			"""

			return self.send('bg_color')

		@property
		def highlight_bg_color(self) -> Concurrent.ThreadedPromise[Terminal.Struct.Color]:
			"""
			:return: A promise with this button's background color when hovered
			"""

			return self.send('highlight_bg_color')

		@property
		def active_bg_color(self) -> Concurrent.ThreadedPromise[Terminal.Struct.Color]:
			"""
			:return: A promise with this button's background color when clicked
			"""

			return self.send('active_bg_color')

		@property
		def border(self) -> Concurrent.ThreadedPromise[Terminal.Struct.BorderInfo]:
			"""
			:return: A promise with this button's border
			"""

			return self.send('border')

		@property
		def highlight_border(self) -> Concurrent.ThreadedPromise[Terminal.Struct.BorderInfo]:
			"""
			:return: A promise with this button's border when hovered
			"""

			return self.send('highlight_border')

		@property
		def active_border(self) -> Concurrent.ThreadedPromise[Terminal.Struct.BorderInfo]:
			"""
			:return: A promise with this button's border when clicked
			"""

			return self.send('active_border')

	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, z: int, width: int, height: int, *,
				 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
		"""
		Base ActivatableWidget class
		Supports highlight and active colors and borders
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: The widget's x position
		:param y: The widget's y position
		:param z: The widget's z-index, higher is drawn last
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		"""

		if border is not None and border is not ... and not isinstance(border, Terminal.Struct.BorderInfo):
			raise Exceptions.InvalidArgumentException(MyActivatableWidget.__init__, 'border', type(border), (Terminal.Struct.BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, Terminal.Struct.BorderInfo):
			raise Exceptions.InvalidArgumentException(MyActivatableWidget.__init__, 'highlight_border', type(highlight_border), (Terminal.Struct.BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, Terminal.Struct.BorderInfo):
			raise Exceptions.InvalidArgumentException(MyActivatableWidget.__init__, 'active_border', type(active_border), (Terminal.Struct.BorderInfo,))

		color_bg = parse_color(color_bg, Exceptions.InvalidArgumentException(MyActivatableWidget.__init__, 'color_bg', type(color_bg), (Terminal.Struct.Color,)))
		highlight_color_bg = parse_color(highlight_color_bg, Exceptions.InvalidArgumentException(MyActivatableWidget.__init__, 'highlight_color_bg', type(highlight_color_bg), (Terminal.Struct.Color,)))
		active_color_bg = parse_color(active_color_bg, Exceptions.InvalidArgumentException(MyActivatableWidget.__init__, 'active_color_bg', type(active_color_bg), (Terminal.Struct.Color,)))

		color_fg = parse_color(color_fg, Exceptions.InvalidArgumentException(MyActivatableWidget.__init__, 'color_fg', type(color_fg), (Terminal.Struct.Color,)))
		highlight_color_fg = parse_color(highlight_color_fg, Exceptions.InvalidArgumentException(MyActivatableWidget.__init__, 'highlight_color_fg', type(highlight_color_fg), (Terminal.Struct.Color,)))
		active_color_fg = parse_color(active_color_fg, Exceptions.InvalidArgumentException(MyActivatableWidget.__init__, 'active_color_fg', type(active_color_fg), (Terminal.Struct.Color,)))

		border = None if border is None else Terminal.Struct.BorderInfo('', ']', '', '[', '', '', '', '') if border is ... and height == 1 else Terminal.Struct.BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else Terminal.Struct.BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... and height == 1 else Terminal.Struct.BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else Terminal.Struct.BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... and height == 1 else Terminal.Struct.BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		super().__init__(parent, x, y, z, width, height,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)
		self.__border__: tuple[Terminal.Struct.BorderInfo | None, Terminal.Struct.BorderInfo | None, Terminal.Struct.BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Terminal.Struct.Color, Terminal.Struct.Color, Terminal.Struct.Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Terminal.Struct.Color, Terminal.Struct.Color, Terminal.Struct.Color] = (color_fg, highlight_color_fg, active_color_fg)

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param z: The widget's z-index, higher is drawn last
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises ValueError: If 'width' <= 2 or 'height' < 1
		"""

		super().configure(x=x, y=y, z=z, width=width, height=height,
						  callback=callback,
						  on_focus=on_focus, off_focus=off_focus,
						  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						  on_tick=on_tick, on_close=on_close)
		border = self.__border__[0] if border is ... or border is None else border
		highlight_border = self.__border__[1] if highlight_border is ... or highlight_border is None else highlight_border
		active_border = self.__border__[2] if active_border is ... or active_border is None else active_border

		if border is not None and border is not ... and not isinstance(border, Terminal.Struct.BorderInfo):
			raise Exceptions.InvalidArgumentException(MyActivatableWidget.configure, 'border', type(border), (Terminal.Struct.BorderInfo,))
		elif highlight_border is not None and highlight_border is not ... and not isinstance(highlight_border, Terminal.Struct.BorderInfo):
			raise Exceptions.InvalidArgumentException(MyActivatableWidget.configure, 'highlight_border', type(highlight_border), (Terminal.Struct.BorderInfo,))
		elif active_border is not None and active_border is not ... and not isinstance(active_border, Terminal.Struct.BorderInfo):
			raise Exceptions.InvalidArgumentException(MyActivatableWidget.configure, 'active_border', type(active_border), (Terminal.Struct.BorderInfo,))

		color_bg = self.__bg_color__[0] if color_bg is ... or color_bg is None else parse_color(color_bg, Exceptions.InvalidArgumentException(MyActivatableWidget.configure, 'color_bg', type(color_bg), (Terminal.Struct.Color,)))
		highlight_color_bg = self.__bg_color__[1] if highlight_color_bg is ... or highlight_color_bg is None else parse_color(highlight_color_bg, Exceptions.InvalidArgumentException(MyActivatableWidget.configure, 'highlight_color_bg', type(highlight_color_bg), (Terminal.Struct.Color,)))
		active_color_bg = self.__bg_color__[2] if active_color_bg is ... or active_color_bg is None else parse_color(active_color_bg, Exceptions.InvalidArgumentException(MyActivatableWidget.configure, 'active_color_bg', type(active_color_bg), (Terminal.Struct.Color,)))

		color_fg = self.__bg_color__[0] if color_fg is ... or color_fg is None else parse_color(color_fg, Exceptions.InvalidArgumentException(MyActivatableWidget.configure, 'color_fg', type(color_fg), (Terminal.Struct.Color,)))
		highlight_color_fg = self.__bg_color__[1] if highlight_color_fg is ... or highlight_color_fg is None else parse_color(highlight_color_fg, Exceptions.InvalidArgumentException(MyActivatableWidget.configure, 'highlight_color_fg', type(highlight_color_fg), (Terminal.Struct.Color,)))
		active_color_fg = self.__bg_color__[2] if active_color_fg is ... or active_color_fg is None else parse_color(active_color_fg, Exceptions.InvalidArgumentException(MyActivatableWidget.configure, 'active_color_fg', type(active_color_fg), (Terminal.Struct.Color,)))

		border = None if border is None else Terminal.Struct.BorderInfo('', ']', '', '[', '', '', '', '') if border is ... and height == 1 else Terminal.Struct.BorderInfo() if border is ... else border
		highlight_border = None if highlight_border is None else Terminal.Struct.BorderInfo('', ']', '', '[', '', '', '', '') if highlight_border is ... and height == 1 else Terminal.Struct.BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if highlight_border is ... else highlight_border
		active_border = None if active_border is None else Terminal.Struct.BorderInfo('', ']', '', '[', '', '', '', '') if active_border is ... and height == 1 else Terminal.Struct.BorderInfo('═', '║', '═', '║', '╗', '╝', '╚', '╔') if active_border is ... else active_border

		self.__border__: tuple[Terminal.Struct.BorderInfo | None, Terminal.Struct.BorderInfo | None, Terminal.Struct.BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Terminal.Struct.Color, Terminal.Struct.Color, Terminal.Struct.Color] = (color_bg, highlight_color_bg, active_color_bg)
		self.__fg_color__: tuple[Terminal.Struct.Color, Terminal.Struct.Color, Terminal.Struct.Color] = (color_fg, highlight_color_fg, active_color_fg)

	@property
	def mode(self) -> int:
		"""
		2 if active (clicked)
		1 if hovered (mouse inside)
		0 if normal
		:return: The mode of this widget
		"""

		return 2 if self.is_mouse_pressed else 1 if self.is_mouse_inside else 0

	@property
	def fg_color(self) -> Terminal.Struct.Color:
		"""
		:return: This button's foreground color
		"""

		return self.__fg_color__[0]

	@property
	def highlight_fg_color(self) -> Terminal.Struct.Color:
		"""
		:return: This button's foreground color when hovered
		"""

		return self.__fg_color__[1]

	@property
	def active_fg_color(self) -> Terminal.Struct.Color:
		"""
		:return: This button's foreground color when clicked
		"""

		return self.__fg_color__[2]

	@property
	def bg_color(self) -> Terminal.Struct.Color:
		"""
		:return: This button's background color
		"""

		return self.__bg_color__[0]

	@property
	def highlight_bg_color(self) -> Terminal.Struct.Color:
		"""
		:return: This button's background color when hovered
		"""

		return self.__bg_color__[1]

	@property
	def active_bg_color(self) -> Terminal.Struct.Color:
		"""
		:return: This button's background color when clicked
		"""

		return self.__bg_color__[2]

	@property
	def border(self) -> Terminal.Struct.BorderInfo:
		"""
		:return: This button's border
		"""

		return self.__border__[0]

	@property
	def highlight_border(self) -> Terminal.Struct.BorderInfo:
		"""
		:return: This button's border when hovered
		"""

		return self.__border__[1]

	@property
	def active_border(self) -> Terminal.Struct.BorderInfo:
		"""
		:return: This button's border when clicked
		"""

		return self.__border__[1]

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyActivatableWidget.MySerializedActivatableWidget


class MyButton(MyActivatableWidget):
	"""
	Widget class representing a button
	"""

	class MySerializedButton(MyActivatableWidget.MySerializedActivatableWidget):
		def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
					  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
					  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
					  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  text: str | Terminal.Struct.AnsiStr | Iterable.String = None, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_WORD,
					  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					  ) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this widget
			Any value not supplied will not be updated
			:param x: The widget's x position
			:param y: The widget's y position
			:param width: The widget's width in characters
			:param height: The widget's height in characters
			:param text: Display text
			:param z_index: The widget's z-index, higher is drawn last
			:param justify: Text justification (one of the cardinal direction enums)
			:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If 'width' is not an integer
			:raises InvalidArgumentException: If 'height' is not an integer
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises ValueError: If 'width' <= 2 or 'height' < 1
			"""

			return self.send('configure()', x=x, y=y, z=z_index, width=width, height=height,
							  text=text, justify=justify, word_wrap=word_wrap,
							  border=border, highlight_border=highlight_border, active_border=active_border,
							  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
							  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
							  callback=callback,
							  on_focus=on_focus, off_focus=off_focus,
							  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							  on_tick=on_tick, on_close=on_close)

		@property
		def text(self) -> Concurrent.ThreadedPromise[Terminal.Struct.AnsiStr]:
			"""
			:return: A promise with this button's text
			"""

			return self.send('text')

		@property
		def justify(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with this button's text justification
			"""

			return self.send('justify')

	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, width: int, height: int, text: str | Terminal.Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_NONE,
				 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
		"""
		Widget class representing a button
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param text: Display text
		:param z_index: The widget's z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises ValueError: If 'width' <= 2 or 'height' < 1
		"""

		if not isinstance(text, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyButton.__init__, 'text', type(text), (str, Terminal.Struct.AnsiStr, Iterable.String))

		super().__init__(parent, x, y, z_index, width, height,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus,
						 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)
		self.__text__: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr(text)
		self.__justify__: int = int(justify)
		self.__word_wrap__: int = int(word_wrap)

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

	def __draw1(self, mode: int):
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)

		if (self.__justify__ & Terminal.Enums.EAST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif (self.__justify__ & Terminal.Enums.WEST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.CENTER or self.__justify__ == Terminal.Enums.NORTH or self.__justify__ == Terminal.Enums.SOUTH:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw2(self, mode: int):
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + 1)

		if self.__justify__ == Terminal.Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.WEST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.EAST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.CENTER:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw3(self, mode: int):
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2, self.height - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		for i in range(1, self.height - 1):
			self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + i)

		if self.__justify__ == Terminal.Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.WEST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.EAST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.CENTER:
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
		self.__draw(self.mode)

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  text: str | Terminal.Struct.AnsiStr | Iterable.String = None, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_WORD,
				  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param text: Display text
		:param z_index: The widget's z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises ValueError: If 'width' <= 2 or 'height' < 1
		"""
	
		super().configure(x=x, y=y, z=z_index, width=width, height=height,
						  border=border, highlight_border=highlight_border, active_border=active_border,
						  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						  callback=callback,
						  on_focus=on_focus, off_focus=off_focus,
						  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						  on_tick=on_tick, on_close=on_close)

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		self.__text__: Terminal.Struct.AnsiStr = self.__text__ if text is ... or text is None else Terminal.Struct.AnsiStr(text)
		self.__justify__: int = int(justify)
		self.__word_wrap__: int = self.__word_wrap__ if word_wrap is ... or word_wrap is None else int(word_wrap)

	@property
	def text(self) -> Terminal.Struct.AnsiStr:
		"""
		:return: This button's text 
		"""
		
		return Terminal.Struct.AnsiStr(self.__text__)

	@property
	def justify(self) -> int:
		"""
		:return: This button's text justification
		"""
		
		return self.__justify__

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyButton.MySerializedButton


class MyToggleButton(MyButton):
	"""
	Widget class representing a toggle button
	"""
	
	class MySerializedToggleButton(MyButton.MySerializedButton):
		@property
		def toggled(self) -> Concurrent.ThreadedPromise[bool]:
			return self.send('toggled')

		@toggled.setter
		def toggled(self, state: bool) -> None:
			self.send('toggled', state)
	
	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, width: int, height: int, text: str | Terminal.Struct.AnsiStr, *, z_index: int = 0, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_NONE,
				 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
		super().__init__(parent, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__state__: bool = False

	def __draw1(self, mode: int):
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)

		if (self.__justify__ & Terminal.Enums.EAST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif (self.__justify__ & Terminal.Enums.WEST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.CENTER or self.__justify__ == Terminal.Enums.NORTH or self.__justify__ == Terminal.Enums.SOUTH:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw2(self, mode: int):
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + 1)

		if self.__justify__ == Terminal.Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.WEST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.EAST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.CENTER:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw3(self, mode: int):
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__, self.width - 2, self.height - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		for i in range(1, self.height - 1):
			self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + i)

		if self.__justify__ == Terminal.Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.WEST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.EAST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.CENTER:
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
		mouse_info: Terminal.Struct.MouseInfo = self.__terminal__.mouse
		self.__draw(2 if self.is_mouse_pressed else 1 if self.is_mouse_inside else 0)
		self.__state__ = not self.__state__ if self.is_mouse_inside and (mouse_info.left_released or mouse_info.left_clicked) else self.__state__

	@property
	def toggled(self) -> bool:
		return self.__state__

	@toggled.setter
	def toggled(self, state: bool) -> None:
		Misc.raise_ifn(isinstance(state, bool), Exceptions.InvalidArgumentException(MyToggleButton.toggled.setter, 'state', type(state), (bool,)))
		self.__state__ = bool(state)

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyToggleButton.MySerializedToggleButton


class MyCheckbox(MyActivatableWidget):
	"""
	Widget class representing a checkbox button
	"""

	class MySerializedCheckbox(MyActivatableWidget.MySerializedActivatableWidget):
		def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ...,
					  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_checked: typing.Optional[typing.Callable[[MyWidget, bool], None]] = ...,
					  text: str | Terminal.Struct.AnsiStr | Iterable.String = None, active_text: str | Terminal.Struct.AnsiStr | Iterable.String = None,
					  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					  ) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this widget
			Any value not supplied will not be updated
			:param x: The widget's x position
			:param y: The widget's y position
			:param z_index: The widget's z-index, higher is drawn last
			:param text: The text to display when off
			:param active_text: The text to display when on
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If 'active_text' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If any supplied border is not a border instance
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises ValueError: If 'text' is more than a single character
			:raises ValueError: If 'active_text' is more than a single character
			"""

			return self.send('configure()', x=x, y=y, z=z_index,
							  text=text, on_checked=on_checked,
							  border=border, highlight_border=highlight_border, active_border=active_border,
							  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
							  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
							  callback=callback,
							  on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							  on_tick=on_tick, on_close=on_close)

		@property
		def text(self) -> Concurrent.ThreadedPromise[Terminal.Struct.AnsiStr]:
			"""
			:return: A promise with this checkbox's off text
			"""

			return self.send('text')

		@property
		def active_text(self) -> Concurrent.ThreadedPromise[Terminal.Struct.AnsiStr]:
			"""
			:return: A promise with this checkbox's on text
			"""

			return self.send('active_text')

		@property
		def checked(self) -> Concurrent.ThreadedPromise[bool]:
			"""
			:return: Whether this checkbox is checked
			"""

			return self.send('checked')

		@checked.setter
		def checked(self, checked: bool) -> None:
			"""
			:param checked: Sets this checkbox's checked state
			"""


			self.send('checked', checked)

	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, *, z_index: int = 0, text: str | Terminal.Struct.AnsiStr = '', active_text: str | Terminal.Struct.AnsiStr = 'X',
				 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				 on_checked: typing.Optional[typing.Callable[[MyWidget, bool], None]] = ...):
		"""
		Widget class representing a checkbox button
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: The widget's x position
		:param y: The widget's y position
		:param z_index: The widget's z-index, higher is drawn last
		:param text: The text to display when off
		:param active_text: The text to display when on
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:param on_checked: The callback to call once the widget is checked taking this widget and the new checked state as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'active_text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises ValueError: If 'text' is more than a single character
		:raises ValueError: If 'active_text' is more than a single character
		"""

		if not isinstance(text, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyCheckbox.__init__, 'text', type(text), (str, Terminal.Struct.AnsiStr, Iterable.String))
		elif not isinstance(active_text, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyCheckbox.__init__, 'active_text', type(active_text), (str, Terminal.Struct.AnsiStr, Iterable.String))

		if on_checked is not None and on_checked is not ... and not callable(on_checked):
			raise Exceptions.InvalidArgumentException(MyCheckbox.__init__, 'on_checked', type(on_checked))

		text: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr(text)
		active_text: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr(active_text)

		if len(text) > 1:
			raise ValueError('Text must be an empty string or single character')

		if len(active_text) > 1:
			raise ValueError('Text must be an empty string or single character')

		super().__init__(parent, x, y, z_index, 3, 3,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)
		self.__text__: tuple[Terminal.Struct.AnsiStr, Terminal.Struct.AnsiStr] = (text, active_text)
		self.__state__: bool = False
		self.__on_checked__: typing.Optional[typing.Callable[[MyWidget, bool], None]] = on_checked

	def draw(self) -> None:
		super().draw()
		mouse_info: Terminal.Struct.MouseInfo = self.__terminal__.mouse
		text: str | Terminal.Struct.AnsiStr = ' ' if len(self.__text__[self.__state__]) == 0 else self.__text__[self.__state__]
		bg_color_index: int = 1 if self.is_mouse_inside else 2 if self.__state__ else 0
		fg_color_index: int = 1 if self.is_mouse_inside else 2 if self.__state__ else 0
		bg_color: Terminal.Struct.Color = self.__bg_color__[bg_color_index]
		fg_color: Terminal.Struct.Color = self.__fg_color__[fg_color_index]
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
		state: bool = not self.__state__ if self.is_mouse_inside and (mouse_info.left_released or mouse_info.left_clicked) else self.__state__

		if state != self.__state__:
			if callable(self.__on_checked__):
				self.__on_checked__(self, state)
			if callable(self.__general_callback__):
				self.__general_callback__(self, 'checked', state)

		self.__state__ = state

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_checked: typing.Optional[typing.Callable[[MyWidget, bool], None]] = ...,
				  text: str | Terminal.Struct.AnsiStr | Iterable.String = None, active_text: str | Terminal.Struct.AnsiStr | Iterable.String = None,
				  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param z_index: The widget's z-index, higher is drawn last
		:param text: The text to display when off
		:param active_text: The text to display when on
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'active_text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises ValueError: If 'text' is more than a single character
		:raises ValueError: If 'active_text' is more than a single character
		"""

		super().configure(x=x, y=y, z=z_index,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						  callback=callback,
						  on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						  on_tick=on_tick, on_close=on_close)
		if text is not None and text is not ... and not isinstance(text, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyCheckbox.configure, 'text', type(text), (str, Terminal.Struct.AnsiStr, Iterable.String))
		elif active_text is not None and active_text is not ... and not isinstance(active_text, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyCheckbox.configure, 'active_text', type(active_text), (str, Terminal.Struct.AnsiStr, Iterable.String))

		if on_checked is not None and on_checked is not ... and not callable(on_checked):
			raise Exceptions.InvalidArgumentException(MyCheckbox.configure, 'on_checked', type(on_checked))

		text: Terminal.Struct.AnsiStr = None if text is None or text is ... else Terminal.Struct.AnsiStr(text)
		active_text: Terminal.Struct.AnsiStr = None if active_text is None or active_text is ... else Terminal.Struct.AnsiStr(active_text)

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

		self.__text__: tuple[Terminal.Struct.AnsiStr, Terminal.Struct.AnsiStr] = (text, active_text)
		self.__on_checked__: typing.Optional[typing.Callable[[MyWidget, bool], None]] = self.__on_checked__ if on_checked is ... else on_checked

	@property
	def text(self) -> Terminal.Struct.AnsiStr:
		"""
		:return: Checkbox off text
		"""

		return Terminal.Struct.AnsiStr(self.__text__[0])

	@property
	def active_text(self) -> Terminal.Struct.AnsiStr:
		"""
		:return: Checkbox on text
		"""

		return Terminal.Struct.AnsiStr(self.__text__[1])

	@property
	def checked(self) -> bool:
		"""
		:return: Whether this checkbox is checked
		"""

		return self.__state__

	@checked.setter
	def checked(self, checked: bool) -> None:
		"""
		:param checked: Sets this checkbox's checked state
		"""

		Misc.raise_ifn(isinstance(checked, bool), Exceptions.InvalidArgumentException(MyCheckbox.checked.setter, 'checked', type(checked), (bool,)))
		self.__state__ = bool(checked)

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyCheckbox.MySerializedCheckbox


class MyInlineCheckbox(MyActivatableWidget):
	"""
	Widget class representing an inline checkbox button
	"""

	class MySerializedInlineCheckbox(MyCheckbox.MySerializedCheckbox):
		pass

	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, *, z_index: int = 0, text: str | Terminal.Struct.AnsiStr | Iterable.String = '', active_text: str | Terminal.Struct.AnsiStr = 'X',
				 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_checked: typing.Optional[typing.Callable[[MyWidget, bool], None]] = ...):
		"""
		Widget class representing an inline checkbox button
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: The widget's x position
		:param y: The widget's y position
		:param z_index: The widget's z-index, higher is drawn last
		:param text: The text to display when off
		:param active_text: The text to display when on
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:param on_checked: The callback to call once the widget is checked taking this widget and the new checked state as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'active_text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises ValueError: If 'text' is more than a single character
		:raises ValueError: If 'active_text' is more than a single character
		"""

		if not isinstance(text, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyInlineCheckbox.__init__, 'text', type(text), (str, Terminal.Struct.AnsiStr, Iterable.String))
		elif not isinstance(active_text, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyInlineCheckbox.__init__, 'active_text', type(active_text), (str, Terminal.Struct.AnsiStr, Iterable.String))

		if on_checked is not None and on_checked is not ... and not callable(on_checked):
			raise Exceptions.InvalidArgumentException(MyInlineCheckbox.__init__, 'on_checked', type(on_checked))

		text: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr(text)
		active_text: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr(active_text)

		if len(text) > 1:
			raise ValueError('Text must be an empty string or single character')

		if len(active_text) > 1:
			raise ValueError('Text must be an empty string or single character')

		super().__init__(parent, x, y, z_index, 3, 1,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)
		self.__text__: tuple[Terminal.Struct.AnsiStr, Terminal.Struct.AnsiStr] = (text, active_text)
		self.__state__: bool = False
		self.__on_checked__: typing.Optional[typing.Callable[[MyWidget, bool], None]] = on_checked

	def draw(self) -> None:
		super().draw()
		mouse_info: Terminal.Struct.MouseInfo = self.__terminal__.mouse
		text: str | Terminal.Struct.AnsiStr = ' ' if len(self.__text__[self.__state__]) == 0 else self.__text__[self.__state__]
		bg_color_index: int = 1 if self.is_mouse_inside else 2 if self.__state__ else 0
		fg_color_index: int = 1 if self.is_mouse_inside else 2 if self.__state__ else 0
		bg_color: Terminal.Struct.Color = self.__bg_color__[bg_color_index]
		fg_color: Terminal.Struct.Color = self.__fg_color__[fg_color_index]
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

		border: Terminal.Struct.BorderInfo = self.__border__[2 if self.is_mouse_pressed else 1 if self.is_mouse_inside else 0]
		self.__terminal__.putstr(border.left, self.x, self.y)
		self.__terminal__.putstr(border.right, self.x + 2, self.y)
		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb
		self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if not self.is_mouse_inside or (null_bg_color and null_fg_color) else ";7"}m{text}', self.x + 1, self.y)
		state: bool = not self.__state__ if self.is_mouse_inside and (mouse_info.left_released or mouse_info.left_clicked) else self.__state__

		if state != self.__state__:
			if callable(self.__on_checked__):
				self.__on_checked__(self, state)
			if callable(self.__general_callback__):
				self.__general_callback__(self, 'checked', state)

		self.__state__ = state

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ...,
				  text: str | Terminal.Struct.AnsiStr = None, active_text: str | Terminal.Struct.AnsiStr = None,
				  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ...,
				  on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_checked: typing.Optional[typing.Callable[[MyWidget, bool], None]] = ...,
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param z_index: The widget's z-index, higher is drawn last
		:param text: The text to display when off
		:param active_text: The text to display when on
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:param on_checked: The callback to call once the widget is checked taking this widget and the new checked state as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'active_text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises ValueError: If 'text' is more than a single character
		:raises ValueError: If 'active_text' is more than a single character
		"""

		if on_checked is not None and on_checked is not ... and not callable(on_checked):
			raise Exceptions.InvalidArgumentException(MyInlineCheckbox.configure, 'on_checked', type(on_checked))

		super().configure(x=x, y=y, z=z_index,
						  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						  on_tick=on_tick, on_close=on_close)
		text: Terminal.Struct.AnsiStr = None if text is None or text is ... else Terminal.Struct.AnsiStr(text)
		active_text: Terminal.Struct.AnsiStr = None if active_text is None or active_text is ... else Terminal.Struct.AnsiStr(active_text)

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

		self.__text__: tuple[Terminal.Struct.AnsiStr, Terminal.Struct.AnsiStr] = (text, active_text)
		self.__on_checked__: typing.Optional[typing.Callable[[MyWidget, bool], None]] = self.__on_checked__ if on_checked is ... else on_checked

	@property
	def text(self) -> Terminal.Struct.AnsiStr:
		"""
		:return: Checkbox off text
		"""

		return Terminal.Struct.AnsiStr(self.__text__[0])

	@property
	def active_text(self) -> Terminal.Struct.AnsiStr:
		"""
		:return: Checkbox on text
		"""

		return Terminal.Struct.AnsiStr(self.__text__[1])

	@property
	def checked(self) -> bool:
		"""
		:return: Whether this checkbox is checked
		"""

		return self.__state__

	@checked.setter
	def checked(self, checked: bool) -> None:
		"""
		:param checked: Sets this checkbox's checked state
		"""

		Misc.raise_ifn(isinstance(checked, bool), Exceptions.InvalidArgumentException(MyInlineCheckbox.checked.setter, 'checked', type(checked), (bool,)))
		self.__state__ = bool(checked)

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyInlineCheckbox.MySerializedInlineCheckbox


class MyRadialSpinner(MyWidget):
	"""
	Widget class representing a loader spinner
	"""

	class MySerializedRadialSpinner(MyWidget.MySerializedWidget):
		def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ...,
					  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
					  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
					  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  phases: typing.Iterable[str | Terminal.Struct.AnsiStr] = ..., bg_phase_colors: typing.Optional[Terminal.Enums.Color_T] | typing.Iterable[typing.Optional[Terminal.Enums.Color_T]] = ..., fg_phase_colors: typing.Optional[Terminal.Enums.Color_T] | typing.Iterable[typing.Optional[Terminal.Enums.Color_T]] = ...
					  ) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this widget
			Any value not supplied will not be updated
			:param x: The widget's x position
			:param y: The widget's y position
			:param z_index: The widget's z-index, higher is drawn last
			:param phases: A list of text to cycle through
			:param bg_phase_colors: A single background color or list of background colors this spinner cycles through
			:param fg_phase_colors: A single foreground color or list of foreground colors this spinner cycles through
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises ValueError: If one or more phases is not a string, AnsiStr, or String instance or is not a single character
			"""

			return self.send('configure()', x=x, y=y, z=z_index,
							 phases=phases, bg_phase_colors=bg_phase_colors, fg_phase_colors=fg_phase_colors,
							 callback=callback,
							 on_focus=on_focus, off_focus=off_focus,
							 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							 on_tick=on_tick, on_close=on_close)

		def spin(self, tick_rate: int) -> Concurrent.ThreadedPromise[None]:
			"""
			Spins the spinner at the specified rate
			:param tick_rate: The rate of spin - steps phase once every 'tick_rate' terminal ticks
			:return: A promise
			:raises InvalidArgumentException: If 'tick_rate' is not an integer
			"""

			Misc.raise_ifn(isinstance(tick_rate, int), Exceptions.InvalidArgumentException(MyRadialSpinner.spin, 'tick_rate', type(tick_rate), (int,)))
			return self.send('spin()', int(tick_rate))

		@property
		def fg_colors(self) -> Concurrent.ThreadedPromise[tuple[Terminal.Struct.Color, ...]]:
			"""
			:return: A promise with this spinner's foreground colors
			"""

			return self.send('fg_colors')

		@property
		def bg_colors(self) -> Concurrent.ThreadedPromise[tuple[Terminal.Struct.Color, ...]]:
			"""
			:return: A promise with this spinner's background colors
			"""

			return self.send('bg_colors')

		@property
		def phases(self) -> Concurrent.ThreadedPromise[tuple[Terminal.Struct.AnsiStr, ...]]:
			"""
			:return: A promise with this spinner's list of phase texts
			"""

			return self.send('phases')

	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, *, z_index: int = 0, phases: typing.Iterable[str | Terminal.Struct.AnsiStr | Iterable.String] = ('--', '\\', '|', '/'), bg_phase_colors: typing.Optional[Terminal.Enums.Color_T] | typing.Iterable[typing.Optional[Terminal.Enums.Color_T]] = Terminal.Struct.Color(0xFFFFFF), fg_phase_colors: typing.Optional[Terminal.Enums.Color_T] | typing.Iterable[typing.Optional[Terminal.Enums.Color_T]] = Terminal.Struct.Color(0xFFFFFF),
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
		"""
		Widget class representing a loader spinner
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: The widget's x position
		:param y: The widget's y position
		:param z_index: The widget's z-index, higher is drawn last
		:param phases: A list of text to cycle through
		:param bg_phase_colors: A single background color or list of background colors this spinner cycles through
		:param fg_phase_colors: A single foreground color or list of foreground colors this spinner cycles through
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises ValueError: If one or more phases is not a string, AnsiStr, or String instance or is not a single character
		"""

		Misc.raise_ifn(all(isinstance(x, (str, Terminal.Struct.AnsiStr, Iterable.String)) for x in phases), ValueError('One or more phase strings is not a string, AnsiStr instance, or String instance'))
		super().__init__(parent, x, y, z_index, 1, 1,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus,
						 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)
		self.__phases__: tuple[Terminal.Struct.AnsiStr, ...] = tuple(Terminal.Struct.AnsiStr(x) for x in phases)
		self.__spin__: int = 0
		self.__spin_mod__: int = 0
		self.__last_frame__: int = 0

		bg_phase_color: Terminal.Struct.Color = parse_color(bg_phase_colors)
		fg_phase_color: Terminal.Struct.Color = parse_color(fg_phase_colors)
		root: Terminal.Terminal.Terminal = self.topmost_parent()

		if bg_phase_color is None and hasattr(bg_phase_colors, '__iter__'):
			self.__bg_colors__: tuple[Terminal.Struct.Color, ...] = tuple(parse_color(color, Exceptions.InvalidArgumentException(MyRadialSpinner.__init__, 'bg_phase_colors[i]', type(color), (Terminal.Struct.Color,))) for i, color in enumerate(bg_phase_colors))
		elif bg_phase_colors is ... or bg_phase_colors is None:
			self.__bg_colors__: tuple[Terminal.Struct.Color, ...] = (root.default_bg,)
		elif bg_phase_color is None:
			raise Exceptions.InvalidArgumentException(MyRadialSpinner.__init__, 'bg_phase_colors', type(bg_phase_colors), (Terminal.Struct.Color,))
		else:
			self.__bg_colors__: tuple[Terminal.Struct.Color, ...] = (bg_phase_color,)

		if fg_phase_color is None and hasattr(fg_phase_colors, '__iter__'):
			self.__fg_colors__: tuple[Terminal.Struct.Color, ...] = tuple(parse_color(color, Exceptions.InvalidArgumentException(MyRadialSpinner.__init__, 'fg_phase_colors[i]', type(color), (Terminal.Struct.Color,))) for i, color in enumerate(fg_phase_colors))
		elif fg_phase_colors is ... or fg_phase_colors is None:
			self.__fg_colors__: tuple[Terminal.Struct.Color, ...] = (root.default_fg,)
		elif fg_phase_color is None:
			raise Exceptions.InvalidArgumentException(MyRadialSpinner.__init__, 'fg_phase_colors', type(fg_phase_colors), (Terminal.Struct.Color,))
		else:
			self.__fg_colors__: tuple[Terminal.Struct.Color, ...] = (fg_phase_color,)

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  phases: typing.Iterable[str | Terminal.Struct.AnsiStr] = ..., bg_phase_colors: typing.Optional[Terminal.Enums.Color_T] | typing.Iterable[typing.Optional[Terminal.Enums.Color_T]] = ..., fg_phase_colors: typing.Optional[Terminal.Enums.Color_T] | typing.Iterable[typing.Optional[Terminal.Enums.Color_T]] = ...
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param z_index: The widget's z-index, higher is drawn last
		:param phases: A list of text to cycle through
		:param bg_phase_colors: A single background color or list of background colors this spinner cycles through
		:param fg_phase_colors: A single foreground color or list of foreground colors this spinner cycles through
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises ValueError: If one or more phases is not a string, AnsiStr, or String instance or is not a single character
		"""

		super().configure(x=x, y=y, z=z_index, callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		self.__phases__: tuple[Terminal.Struct.AnsiStr, ...] = self.__phases__ if phases is ... or phases is None else tuple(Terminal.Struct.AnsiStr(x) for x in phases)
		root: Terminal.Terminal.Terminal = self.topmost_parent()

		if self.__bg_colors__ is not None and self.__bg_colors__ is not ...:
			bg_phase_color: Terminal.Struct.Color = parse_color(bg_phase_colors)

			if bg_phase_color is None and hasattr(bg_phase_colors, '__iter__'):
				self.__bg_colors__: tuple[Terminal.Struct.Color, ...] = tuple(parse_color(color, Exceptions.InvalidArgumentException(MyRadialSpinner.__init__, 'bg_phase_colors[i]', type(color), (Terminal.Struct.Color,))) for i, color in enumerate(bg_phase_colors))
			elif bg_phase_colors is ... or bg_phase_colors is None:
				self.__bg_colors__: tuple[Terminal.Struct.Color, ...] = (root.default_bg,)
			elif bg_phase_color is None:
				raise Exceptions.InvalidArgumentException(MyRadialSpinner.__init__, 'bg_phase_colors', type(bg_phase_colors), (Terminal.Struct.Color,))
			else:
				self.__bg_colors__: tuple[Terminal.Struct.Color, ...] = (bg_phase_color,)

		if self.__bg_colors__ is not None and self.__bg_colors__ is not ...:
			fg_phase_color: Terminal.Struct.Color = parse_color(fg_phase_colors)
			if fg_phase_color is None and hasattr(fg_phase_colors, '__iter__'):
				self.__fg_colors__: tuple[Terminal.Struct.Color, ...] = tuple(parse_color(color, Exceptions.InvalidArgumentException(MyRadialSpinner.__init__, 'fg_phase_colors[i]', type(color), (Terminal.Struct.Color,))) for i, color in enumerate(fg_phase_colors))
			elif fg_phase_colors is ... or fg_phase_colors is None:
				self.__fg_colors__: tuple[Terminal.Struct.Color, ...] = (root.default_fg,)
			elif fg_phase_color is None:
				raise Exceptions.InvalidArgumentException(MyRadialSpinner.__init__, 'fg_phase_colors', type(fg_phase_colors), (Terminal.Struct.Color,))
			else:
				self.__fg_colors__: tuple[Terminal.Struct.Color, ...] = (fg_phase_color,)

	def draw(self) -> None:
		super().draw()
		max_spin: int = self.__spin_mod__ * len(self.__phases__)
		spin_ratio: float = self.__spin__ / max_spin
		frame: int = self.__last_frame__ if self.__spin_mod__ == 0 else (self.__spin__ // self.__spin_mod__)
		index: int = frame % len(self.__phases__)
		symbol: Terminal.Struct.AnsiStr = self.__phases__[index]

		if len(self.__bg_colors__):
			color_index: int = round(spin_ratio * (len(self.__bg_colors__) - 1))
			bg_color: Terminal.Struct.Color = self.__bg_colors__[color_index]
		else:
			bg_color: Terminal.Struct.Color = self.parent.default_bg

		if len(self.__fg_colors__):
			color_index: int = round(spin_ratio * (len(self.__fg_colors__) - 1))
			fg_color: Terminal.Struct.Color = self.__fg_colors__[color_index]
		else:
			fg_color: Terminal.Struct.Color = self.parent.default_fg

		br, bg, bb = bg_color.rgb
		fr, fg, fb = fg_color.rgb

		self.__last_frame__ = frame
		self.__spin__ = 0 if self.__spin__ >= max_spin else self.__spin__ + 1
		self.__terminal__.putstr(f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}m{symbol}', self.x, self.y)

	def spin(self, tick_rate: int) -> None:
		"""
		Spins the spinner at the specified rate
		:param tick_rate: The rate of spin - steps phase once every 'tick_rate' terminal ticks
		:raises InvalidArgumentException: If 'tick_rate' is not an integer
		"""

		Misc.raise_ifn(isinstance(tick_rate, int), Exceptions.InvalidArgumentException(MyRadialSpinner.spin, 'tick_rate', type(tick_rate), (int,)))
		self.__spin_mod__ = max(0, int(tick_rate))

	@property
	def fg_colors(self) -> tuple[Terminal.Struct.Color, ...]:
		"""
		:return: This spinner's foreground colors
		"""

		return self.__fg_colors__

	@property
	def bg_colors(self) -> tuple[Terminal.Struct.Color, ...]:
		"""
		:return: This spinner's background colors
		"""

		return self.__bg_colors__

	@property
	def phases(self) -> tuple[Terminal.Struct.AnsiStr, ...]:
		"""
		:return: This spinner's list of phase texts
		"""

		return self.__phases__

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyRadialSpinner.MySerializedRadialSpinner


class MyHorizontalSlider(MyActivatableWidget):
	"""
	Widget class representing a horizontal scrollbar
	"""

	class MySerializedHorizontalSlider(MyActivatableWidget.MySerializedActivatableWidget):
		def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
					  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
					  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
					  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  step: float = 1, fill_char: str | Terminal.Struct.AnsiStr = '|', _max: float = 10, _min: float = 0, on_input: typing.Optional[typing.Callable[[MyHorizontalSlider], None]] = ...,
					  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					  ) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this widget
			Any value not supplied will not be updated
			:param x: The widget's x position
			:param y: The widget's y position
			:param width: The widget's width in characters
			:param height: The widget's height in characters
			:param z_index: The widget's z-index, higher is drawn last
			:param step: The amount to increment by per scroll
			:param fill_char: The character to use to show value
			:param _max: The maximum value of this slider
			:param _min: The minimum value of this slider
			:param on_input: The callback to call once the mouse enters this widget taking this widget as an argument
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If 'width' is not an integer
			:raises InvalidArgumentException: If 'height' is not an integer
			:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises InvalidArgumentException: If any supplied border is not a border instance
			:raises ValueError: If 'width' is <= 2 or 'height' < 1
			"""

			return self.send('configure()', x=x, y=y, z=z_index, width=width, height=height,
							  step=step, _max=_max, _min=_min, fill_char=fill_char, on_input=on_input,
							  border=border, highlight_border=highlight_border, active_border=active_border,
							  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
							  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
							  callback=callback,
							  on_focus=on_focus, off_focus=off_focus,
							  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							  on_tick=on_tick, on_close=on_close)

		@property
		def min(self) -> Concurrent.ThreadedPromise[float]:
			"""
			:return: A promise with the minimum slider value
			"""

			return self.send('min')

		@property
		def max(self) -> Concurrent.ThreadedPromise[float]:
			"""
			:return: A promise with the maximum slider value
			"""

			return self.send('max')

		@property
		def step(self) -> Concurrent.ThreadedPromise[float]:
			"""
			:return: A promise with the slider step per scroll
			"""

			return self.send('step')

		@property
		def fill(self) -> Concurrent.ThreadedPromise[Terminal.Struct.AnsiStr]:
			"""
			:return: A promise with the slider's fill character
			"""

			return self.send('fill')

		@property
		def value(self) -> Concurrent.ThreadedPromise[float]:
			"""
			:return: A promise with the slider's current value
			"""

			return self.send('value')

		@value.setter
		def value(self, value: float) -> None:
			"""
			Sets the slider's current value
			:raises InvalidArgumentException: If 'value' is not a number
			:raises ValueError: If 'value' is outside the range of this slider
			"""

			self.send('percentage', value)

		@property
		def percentage(self) -> Concurrent.ThreadedPromise[float]:
			"""
			:return: A promise with the slider's current percentage
			"""

			return self.send('percentage')

		@percentage.setter
		def percentage(self, percent: float) -> None:
			"""
			Sets the slider's current percentage
			:raises InvalidArgumentException: If 'value' is not a number
			:raises ValueError: If 'value' is outside the range of this slider
			"""

			self.send('percentage', percent)

	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, width: int, height: int, *, z_index: int = 0, step: float = 1, fill_char: str | Terminal.Struct.AnsiStr = '|', _max: float = 10, _min: float = 0, on_input: typing.Optional[typing.Callable[[MyHorizontalSlider], None]] = ...,
				 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
		"""
		Widget class representing a horizontal scrollbar
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param z_index: The widget's z-index, higher is drawn last
		:param step: The amount to increment by per scroll
		:param fill_char: The character to use to show value
		:param _max: The maximum value of this slider
		:param _min: The minimum value of this slider
		:param on_input: The callback to call once the mouse enters this widget taking this widget as an argument
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises ValueError: If 'width' is <= 2 or 'height' < 1
		"""

		if on_input is not None and on_input is not ... and not callable(on_input):
			raise Exceptions.InvalidArgumentException(MyHorizontalSlider.__init__, 'on_input', type(on_input))

		super().__init__(parent, x, y, z_index, width, height,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus,
						 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)
		self.__fill_char__: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr(fill_char)[0]
		self.__range__: tuple[float, float, float] = (float(_min), float(_max), float(step))
		self.__value__: float = 0
		self.__callback__: typing.Callable[[MyHorizontalSlider], None] = on_input

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

	def __draw1(self, mode: int):
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		mouse_info: Terminal.Struct.MouseInfo = self.__terminal__.mouse

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
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  step: float = 1, fill_char: str | Terminal.Struct.AnsiStr = '|', _max: float = 10, _min: float = 0, on_input: typing.Optional[typing.Callable[[MyHorizontalSlider], None]] = ...,
				  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param z_index: The widget's z-index, higher is drawn last
		:param step: The amount to increment by per scroll
		:param fill_char: The character to use to show value
		:param _max: The maximum value of this slider
		:param _min: The minimum value of this slider
		:param on_input: The callback to call once the mouse enters this widget taking this widget as an argument
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises ValueError: If 'width' is <= 2 or 'height' < 1
		"""

		if on_input is not None and on_input is not ... and not callable(on_input):
			raise Exceptions.InvalidArgumentException(MyHorizontalSlider.__init__, 'on_input', type(on_input))

		super().configure(x=x, y=y, z=z_index, width=width, height=height,
						  border=border, highlight_border=highlight_border, active_border=active_border,
						  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						  callback=callback,
						  on_focus=on_focus, off_focus=off_focus,
						  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						  on_tick=on_tick, on_close=on_close)
		
		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		_min = self.__range__[0] if _min is ... or _min is None else float(_min)
		_max = self.__range__[1] if _max is ... or _max is None else float(_max)
		step = self.__range__[2] if step is ... or step is None else float(step)

		self.__fill_char__: Terminal.Struct.AnsiStr = self.__fill_char__ if fill_char is ... or fill_char is None else Terminal.Struct.AnsiStr(fill_char)[0]
		self.__range__: tuple[float, float, float] = (_min, _max, step)

	@property
	def min(self) -> float:
		"""
		:return: The minimum slider value
		"""
		
		return self.__range__[0]

	@property
	def max(self) -> float:
		"""
		:return: The maximum slider value
		"""
		
		return self.__range__[1]

	@property
	def step(self) -> float:
		"""
		:return: The slider step per scroll
		"""
		
		return self.__range__[2]

	@property
	def fill(self) -> Terminal.Struct.AnsiStr:
		"""
		:return: The slider's fill character
		"""
		
		return self.__fill_char__

	@property
	def value(self) -> float:
		"""
		:return: The slider's current value
		"""
		
		return self.__value__

	@value.setter
	def value(self, value: float) -> None:
		"""
		Sets the slider's current value
		:raises InvalidArgumentException: If 'value' is not a number
		:raises ValueError: If 'value' is outside the range of this slider
		"""
		
		Misc.raise_ifn(isinstance(value, (int, float)), Exceptions.InvalidArgumentException(MyHorizontalSlider.value.setter, 'value', type(value), (int, float)))
		Misc.raise_ifn(self.__range__[0] <= (value := float(value)) <= self.__range__[1], ValueError('Value out of range'))
		self.__value__ = float(value)

	@property
	def percentage(self) -> float:
		"""
		:return: The slider's current percentage
		"""
		
		_min, _max, _ = self.__range__
		return (self.__value__ - _min) / (_max - _min)

	@percentage.setter
	def percentage(self, percent: float) -> None:
		"""
		Sets the slider's current percentage
		:raises InvalidArgumentException: If 'value' is not a number
		:raises ValueError: If 'value' is outside the range of this slider
		"""

		Misc.raise_ifn(isinstance(percent, (int, float)), Exceptions.InvalidArgumentException(MyHorizontalSlider.percentage.setter, 'percent', type(percent), (int, float)))
		Misc.raise_ifn(0 <= (percent := float(percent)) <= 1, ValueError('Percentage out of range'))
		_min, _max, _ = self.__range__
		self.__value__ = (_max - _min) * percent + _min

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyHorizontalSlider.MySerializedHorizontalSlider


class MyVerticalSlider(MyActivatableWidget):
	"""
	Widget class representing a vertical scrollbar
	"""

	class MySerializedVerticalSlider(MyHorizontalSlider.MySerializedHorizontalSlider):
		pass
	
	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, width: int, height: int, *, z_index: int = 0, step: float = 1, fill_char: str | Terminal.Struct.AnsiStr = '=', _max: float = 10, _min: float = 0, on_input: typing.Optional[typing.Callable[[MyVerticalSlider], None]] = ...,
				 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
		"""
		Widget class representing a vertical scrollbar
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param z_index: The widget's z-index, higher is drawn last
		:param step: The amount to increment by per scroll
		:param fill_char: The character to use to show value
		:param _max: The maximum value of this slider
		:param _min: The minimum value of this slider
		:param on_input: The callback to call once the mouse enters this widget taking this widget as an argument
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises ValueError: If 'width' is < 1 or 'height' <= 2
		"""
	
		if on_input is not None and on_input is not ... and not callable(on_input):
			raise Exceptions.InvalidArgumentException(MyVerticalSlider.__init__, 'on_input', type(on_input))

		super().__init__(parent, x, y, z_index, width, height,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus,
						 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)
		self.__fill_char__: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr(fill_char)[0]
		self.__range__: tuple[float, float, float] = (float(_min), float(_max), float(step))
		self.__value__: float = 0
		self.__callback__: typing.Callable[[MyVerticalSlider], None] = on_input

		if self.width < 1 or self.height <= 2:
			raise ValueError('Dimensions too small (width >= 1; height > 2)')

	def __draw1(self, mode: int):
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		mouse_info: Terminal.Struct.MouseInfo = self.__terminal__.mouse

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
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  step: float = 1, fill_char: str | Terminal.Struct.AnsiStr = '|', _max: float = 10, _min: float = 0, on_input: typing.Optional[typing.Callable[[MyHorizontalSlider], None]] = ...,
				  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param z_index: The widget's z-index, higher is drawn last
		:param step: The amount to increment by per scroll
		:param fill_char: The character to use to show value
		:param _max: The maximum value of this slider
		:param _min: The minimum value of this slider
		:param on_input: The callback to call once the mouse enters this widget taking this widget as an argument
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises ValueError: If 'width' is < 1 or 'height' <= 2
		"""

		if on_input is not None and on_input is not ... and not callable(on_input):
			raise Exceptions.InvalidArgumentException(MyVerticalSlider.__init__, 'on_input', type(on_input))

		super().configure(x=x, y=y, z=z_index, width=width, height=height,
						  border=border, highlight_border=highlight_border, active_border=active_border,
						  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						  callback=callback,
						  on_focus=on_focus, off_focus=off_focus,
						  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						  on_tick=on_tick, on_close=on_close)
		
		if self.width < 1 or self.height <= 2:
			raise ValueError('Dimensions too small (width >= 1; height > 2)')

		_min = self.__range__[0] if _min is ... or _min is None else float(_min)
		_max = self.__range__[1] if _max is ... or _max is None else float(_max)
		step = self.__range__[2] if step is ... or step is None else float(step)

		self.__fill_char__: Terminal.Struct.AnsiStr = self.__fill_char__ if fill_char is ... or fill_char is None else Terminal.Struct.AnsiStr(fill_char)[0]
		self.__range__: tuple[float, float, float] = (_min, _max, step)

	@property
	def min(self) -> float:
		"""
		:return: The minimum slider value
		"""
		
		return self.__range__[0]

	@property
	def max(self) -> float:
		"""
		:return: The maximum slider value
		"""
		
		return self.__range__[1]

	@property
	def step(self) -> float:
		"""
		:return: The slider step per scroll
		"""
		
		return self.__range__[2]

	@property
	def fill(self) -> Terminal.Struct.AnsiStr:
		"""
		:return: The slider's fill character
		"""
		
		return self.__fill_char__

	@property
	def value(self) -> float:
		"""
		:return: The slider's current value
		"""
		
		return self.__value__

	@value.setter
	def value(self, value: float) -> None:
		"""
		Sets the slider's current value
		:raises InvalidArgumentException: If 'value' is not a number
		:raises ValueError: If 'value' is outside the range of this slider
		"""
		
		Misc.raise_ifn(isinstance(value, (int, float)), Exceptions.InvalidArgumentException(MyVerticalSlider.value.setter, 'value', type(value), (int, float)))
		Misc.raise_ifn(self.__range__[0] <= (value := float(value)) <= self.__range__[1], ValueError('Value out of range'))
		self.__value__ = float(value)

	@property
	def percentage(self) -> float:
		"""
		:return: The slider's current percentage
		"""
		
		_min, _max, _ = self.__range__
		return (self.__value__ - _min) / (_max - _min)

	@percentage.setter
	def percentage(self, percent: float) -> None:
		"""
		Sets the slider's current percentage
		:raises InvalidArgumentException: If 'value' is not a number
		:raises ValueError: If 'value' is outside the range of this slider
		"""

		Misc.raise_ifn(isinstance(percent, (int, float)), Exceptions.InvalidArgumentException(MyVerticalSlider.percentage.setter, 'percent', type(percent), (int, float)))
		Misc.raise_ifn(0 <= (percent := float(percent)) <= 1, ValueError('Percentage out of range'))
		_min, _max, _ = self.__range__
		self.__value__ = (_max - _min) * percent + _min

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyVerticalSlider.MySerializedVerticalSlider


class MyHorizontalProgressBar(MyHorizontalSlider):
	"""
	Widget class representing a horizontal progress bar
	"""

	class MySerializedHorizontalProgressBar(MyHorizontalSlider.MySerializedHorizontalSlider):
		pass

	def draw(self) -> None:
		super(MyHorizontalSlider, self).draw()
		mouse_info: Terminal.Struct.MouseInfo = self.__terminal__.mouse
		is_inside: bool = self.is_mouse_inside
		mode: int = 2 if is_inside and mouse_info.left_pressed else 1 if is_inside else 0
		self.__draw__(mode)

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyHorizontalProgressBar.MySerializedHorizontalProgressBar


class MyVerticalProgressBar(MyVerticalSlider):
	"""
	Widget class representing a vertical progress bar
	"""

	class MySerializedVerticalProgressBar(MyVerticalSlider.MySerializedVerticalSlider):
		pass

	def draw(self) -> None:
		super(MyVerticalSlider, self).draw()
		mouse_info: Terminal.Struct.MouseInfo = self.__terminal__.mouse
		is_inside: bool = self.is_mouse_inside
		mode: int = 2 if is_inside and mouse_info.left_pressed else 1 if is_inside else 0
		self.__draw__(mode)

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyVerticalProgressBar.MySerializedVerticalProgressBar


class MyText(MyActivatableWidget):
	"""
	Widget class representing a text box
	"""

	class MySerializedText(MyActivatableWidget.MySerializedActivatableWidget):
		def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
					  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  text: typing.Optional[str | Terminal.Struct.AnsiStr] = ..., justify: typing.Optional[int] = ..., word_wrap: typing.Optional[int] = ...,
					  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					  ) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this widget
			Any value not supplied will not be updated
			:param x: The widget's x position
			:param y: The widget's y position
			:param width: The widget's width in characters
			:param height: The widget's height in characters
			:param text: Display text
			:param z_index: The widget's z-index, higher is drawn last
			:param justify: Text justification (one of the cardinal direction enums)
			:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If 'width' is not an integer
			:raises InvalidArgumentException: If 'height' is not an integer
			:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises InvalidArgumentException: If any supplied border is not a border instance
			:raises ValueError: If 'width' < 1 or 'height' < 1
			"""

			return self.send('configure()', x=x, y=y, z=z_index, width=width, height=height,
							  text=text, justify=justify, word_wrap=word_wrap,
							  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
							  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
							  callback=callback,
							  on_focus=on_focus, off_focus=off_focus,
							  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							  on_tick=on_tick, on_close=on_close)

		@property
		def text(self) -> Concurrent.ThreadedPromise[Terminal.Struct.AnsiStr]:
			"""
			:return: A promise with this text's text
			"""

			return self.send('text')

		@property
		def justify(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with this text's text justification
			"""

			return self.send('justify')
	
	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, width: int, height: int, text: str | Terminal.Struct.AnsiStr, *, z_index: int = 0, justify: int = Terminal.Enums.NORTH_WEST, word_wrap: int = Terminal.Enums.WORDWRAP_NONE,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
		"""
		Widget class representing a text box
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param text: Display text
		:param z_index: The widget's z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises ValueError: If 'width' < 1 or 'height' < 1
		"""

		if not isinstance(text, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyText.__init__, 'text', type(text), (str, Terminal.Struct.AnsiStr, Iterable.String))
		if not isinstance(width, int):
			raise Exceptions.InvalidArgumentException(MyText.__init__, 'width', type(width), (int,))
		if not isinstance(height, int):
			raise Exceptions.InvalidArgumentException(MyText.__init__, 'height', type(height), (int,))

		text: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr(text)
		raw_text: str = text.raw

		self.__true_size__: tuple[int, int] = (width, height)

		if width <= 0 and len(raw_text):
			width = max(len(line) for line in raw_text.split('\n'))

		if height <= 0 and len(raw_text):
			height = raw_text.count('\n') + 1

		if width < 1 or height < 1:
			raise ValueError('Dimensions too small (width >= 1; height >= 1)')

		super().__init__(parent, x, y, z_index, width, height,
						 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus,
						 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)
		self.__text__: Terminal.Struct.AnsiStr = text
		self.__justify__: int = int(justify)
		self.__word_wrap__: int = int(word_wrap)

	def __draw1(self, mode: int):
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []

		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		if not null_bg_color or not null_fg_color:
			self.__terminal__.putstr(f'{ansi}m{" " * self.width}', self.x, self.y)

		if (self.__justify__ & Terminal.Enums.EAST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + i, self.width)

		elif (self.__justify__ & Terminal.Enums.WEST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + i, self.width)

		elif self.__justify__ == Terminal.Enums.CENTER or self.__justify__ == Terminal.Enums.NORTH or self.__justify__ == Terminal.Enums.SOUTH:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width)

	def __draw2(self, mode: int):
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		if not null_bg_color or not null_fg_color:
			self.__terminal__.putstr(f'{ansi}m{" " * self.width}', self.x, self.y)
			self.__terminal__.putstr(f'{ansi}m{" " * self.width}', self.x, self.y + 1)

		if self.__justify__ == Terminal.Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + i, self.width)

		elif self.__justify__ == Terminal.Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + i, self.width)

		elif self.__justify__ == Terminal.Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Terminal.Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Terminal.Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + i, self.width)

		elif self.__justify__ == Terminal.Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Terminal.Enums.WEST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + delta + i, self.width)

		elif self.__justify__ == Terminal.Enums.EAST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + delta + i, self.width)

		elif self.__justify__ == Terminal.Enums.CENTER:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width)

	def __draw3(self, mode: int):
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		self.__wordwrap__(self.__text__, lines, self.__word_wrap__)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		if not null_bg_color or not null_fg_color:
			for i in range(self.height):
				self.__terminal__.putstr(f'{ansi}m{" " * self.width}', self.x, self.y + i)

		if self.__justify__ == Terminal.Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + i, self.width)

		elif self.__justify__ == Terminal.Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + i, self.width)

		elif self.__justify__ == Terminal.Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Terminal.Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Terminal.Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + i, self.width)

		elif self.__justify__ == Terminal.Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - (len(lines) - i), self.width)

		elif self.__justify__ == Terminal.Enums.WEST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x, self.y + delta + i, self.width)

		elif self.__justify__ == Terminal.Enums.EAST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - min(len(lines[i]), self.width), self.y + delta + i, self.width)

		elif self.__justify__ == Terminal.Enums.CENTER:
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
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  text: typing.Optional[str | Terminal.Struct.AnsiStr] = ..., justify: typing.Optional[int] = ..., word_wrap: typing.Optional[int] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param text: Display text
		:param z_index: The widget's z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises ValueError: If 'width' < 1 or 'height' < 1
		"""

		text: Terminal.Struct.AnsiStr = self.__text__ if text is None or text is ... else Terminal.Struct.AnsiStr(text)
		raw_text: str = text.raw
		width = self.__true_size__[0] if width is ... or width is None else width
		height = self.__true_size__[1] if height is ... or height is None else height

		if not isinstance(width, int):
			raise Exceptions.InvalidArgumentException(MyText.__init__, 'width', type(width), (int,))
		if not isinstance(height, int):
			raise Exceptions.InvalidArgumentException(MyText.__init__, 'height', type(height), (int,))

		if (width := int(width)) <= 0 and len(raw_text):
			width = max(len(line) for line in raw_text.split('\n'))

		if (height := int(height)) <= 0 and len(raw_text):
			height = raw_text.count('\n') + 1

		super().configure(x=x, y=y, z=z_index, width=width, height=height,
						  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						  callback=callback,
						  on_focus=on_focus, off_focus=off_focus,
						  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						  on_tick=on_tick, on_close=on_close)

		if self.width < 1 or self.height < 1:
			raise ValueError('Dimensions too small (width >= 1; height >= 1)')

		self.__text__: Terminal.Struct.AnsiStr = self.__text__ if text is ... or text is None else Terminal.Struct.AnsiStr(text)
		self.__justify__: int = self.__justify__ if justify is ... or justify is None else int(justify)
		self.__word_wrap__: int = self.__word_wrap__ if word_wrap is ... or word_wrap is None else int(word_wrap)

	@property
	def text(self) -> Terminal.Struct.AnsiStr:
		"""
		:return: This text's text
		"""

		return Terminal.Struct.AnsiStr(self.__text__)

	@property
	def justify(self) -> int:
		"""
		:return: This text's text justification
		"""

		return self.__justify__

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyText.MySerializedText


class MyDropdown(MyActivatableWidget):
	"""
	Widget class representing a dropdown menu
	"""

	class MySerializedDropdown(MyActivatableWidget.MySerializedActivatableWidget):
		def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
					  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  choices: typing.Optional[tuple[str | Terminal.Struct.AnsiStr, ...]] = ..., display_count: typing.Optional[int | None] = ..., justify: int = Terminal.Enums.CENTER, allow_scroll_rollover: bool = False, word_wrap: int = Terminal.Enums.WORDWRAP_WORD, on_select: typing.Optional[typing.Callable[[MyWidget], bool | None]] = ...,
					  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					  ) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this widget
			Any value not supplied will not be updated
			:param x: The widget's x position
			:param y: The widget's y position
			:param width: The widget's width in characters
			:param height: The widget's height in characters
			:param choices: Display text
			:param z_index: The widget's z-index, higher is drawn last
			:param justify: Text justification (one of the cardinal direction enums)
			:param display_count: The number of choices to display at once
			:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
			:param allow_scroll_rollover: Whether scrolling can cycle (too far down will cycle back to first option and vise versa)
			:param on_select: The callback to call once a choice is selected taking this widget and whether the choice was scrolled to (False) or clicked (True) as arguments and returning a boolean indicating whether to keep the selection
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:raises InvalidArgumentException: If 'dropdown' is not a 'MyDropdown' instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If 'width' is not an integer
			:raises InvalidArgumentException: If 'height' is not an integer
			:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises InvalidArgumentException: If any supplied border is not a border instance
			:raises InvalidArgumentException: If any supplied choice is not a string, AnsiStr instance, or String instance
			:raises ValueError: If 'width' <= 2 or 'height' < 1
			:raises ValueError: If the number of choices is zero
			"""

			return self.send('configure()', x=x, y=y, z=z_index, width=width, height=height,
							  choices=choices, display_count=display_count, justify=justify, word_wrap=word_wrap, allow_scroll_rollover=allow_scroll_rollover, on_select=on_select,
							  border=border, highlight_border=highlight_border, active_border=active_border,
							  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
							  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
							  callback=callback,
							  on_focus=on_focus, off_focus=off_focus,
							  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							  on_tick=on_tick, on_close=on_close)

		def option_configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
							 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
							 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
							 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
							 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
							 text: str | Terminal.Struct.AnsiStr = None, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_WORD,
							 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
							 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
							 ) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this dropdown's option widgets
			Any value not supplied will not be updated
			:param x: The widget's x position
			:param y: The widget's y position
			:param width: The widget's width in characters
			:param height: The widget's height in characters
			:param text: Display text
			:param z_index: The widget's z-index, higher is drawn last
			:param justify: Text justification (one of the cardinal direction enums)
			:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:raises InvalidArgumentException: If 'dropdown' is not a 'MyDropdown' instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If 'width' is not an integer
			:raises InvalidArgumentException: If 'height' is not an integer
			:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises InvalidArgumentException: If any supplied border is not a border instance
			"""

			return self.send('option_configure()', x=x, y=y, z_index=z_index, width=width, height=height,
					 callback=callback,
					 on_focus=on_focus, off_focus=off_focus,
					 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release,
					 on_tick=on_tick, on_close=on_close,
					 text=text, justify=justify, word_wrap=word_wrap,
					 border=border, highlight_border=highlight_border, active_border=active_border,
					 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
					 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg)

		@property
		def justify(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with this dropdown's text justification
			"""

			return self.send('justify')

		@property
		def selected_index(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with this dropdown's selected option by index
			"""

			return self.send('selected_index')

		@selected_index.setter
		def selected_index(self, index: int) -> None:
			"""
			Sets this dropdown's selected option by index
			:param index: The option index
			:raises InvalidArgumentException: If 'index' is not an integer
			:raises IndexError: If 'index' is out of range
			"""

			self.send('justify', index)

		@property
		def selected(self) -> Concurrent.ThreadedPromise[Terminal.Struct.AnsiStr]:
			"""
			:return: A promise with this dropdown's selected option's text
			"""

			return self.send('selected')

		@selected.setter
		def selected(self, value: Terminal.Struct.AnsiStr | str | int) -> None:
			"""
			Sets this dropdown's selected option by option text or index
			:param value: The option text or index
			:raises InvalidArgumentException: If 'value' is not an integer, string, AnsiStr instance, or String instance
			:raises IndexError: If 'index' is out of range
			"""

			self.send('options_displayed', value)

		@property
		def options_displayed(self) -> Concurrent.ThreadedPromise[bool]:
			"""
			:return: A promise with whether the options list is currently displayed
			"""

			return self.send('options_displayed')

	class __Option__(MyButton):
		"""
		Widget class representing a dropdown menu option
		"""

		def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, dropdown: MyDropdown, x: int, y: int, width: int, height: int, text: str | Terminal.Struct.AnsiStr, *, z_index: int = 0, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_NONE,
					 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
					 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
					 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
			"""
			Widget class representing a dropdown menu option
			- Constructor -
			:param parent: The parent terminal or sub-terminal this widget is bound to
			:param dropdown: The parent dropdown this widget is bound to
			:param x: The widget's x position
			:param y: The widget's y position
			:param width: The widget's width in characters
			:param height: The widget's height in characters
			:param text: Display text
			:param z_index: The widget's z-index, higher is drawn last
			:param justify: Text justification (one of the cardinal direction enums)
			:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:raises InvalidArgumentException: If 'dropdown' is not a 'MyDropdown' instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If 'width' is not an integer
			:raises InvalidArgumentException: If 'height' is not an integer
			:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises InvalidArgumentException: If any supplied border is not a border instance
			"""

			Misc.raise_ifn(isinstance(dropdown, MyDropdown), Exceptions.InvalidArgumentException(MyDropdown.__Option__.__init__, 'dropdown', type(dropdown), (MyDropdown,)))
			super().__init__(parent, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
							 border=border, highlight_border=highlight_border, active_border=active_border,
							 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
							 callback=callback,
							 on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							 on_tick=on_tick, on_close=on_close)
			self.__dropdown__: MyDropdown = dropdown
			self.hide()

	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, width: int, height: int, choices: tuple[str | Terminal.Struct.AnsiStr, ...], *, z_index: int = 0, justify: int = Terminal.Enums.CENTER,
				 display_count: int | None = None, word_wrap: int = Terminal.Enums.WORDWRAP_WORD, allow_scroll_rollover: bool = False, on_select: typing.Optional[typing.Callable[[MyWidget, bool], bool | None]] = ...,
				 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
		"""
		Widget class representing a dropdown menu
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param choices: Display text
		:param z_index: The widget's z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param display_count: The number of choices to display at once
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param allow_scroll_rollover: Whether scrolling can cycle (too far down will cycle back to first option and vise versa)
		:param on_select: The callback to call once a choice is selected taking this widget and whether the choice was scrolled to (False) or clicked (True) as arguments and returning a boolean indicating whether to keep the selection
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'dropdown' is not a 'MyDropdown' instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises InvalidArgumentException: If any supplied choice is not a string, AnsiStr instance, or String instance
		:raises ValueError: If 'width' <= 2 or 'height' < 1
		:raises ValueError: If the number of choices is zero
		"""

		choices = tuple(choices) if hasattr(choices, '__iter__') else choices
		Misc.raise_ifn(all(isinstance(choice, (str, Terminal.Struct.AnsiStr, Iterable.String)) for choice in choices), Exceptions.InvalidArgumentException(MyDropdown.__init__, 'choices', type(choices)))

		super().__init__(parent, x, y, z_index, width, height,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')
		elif len(choices) == 0:
			raise ValueError('Dropbox is empty')

		self.__choices__: tuple[Terminal.Struct.AnsiStr, ...] = tuple(Terminal.Struct.AnsiStr(text) for text in choices)
		self.__options__: tuple[MyDropdown.__Option__, ...] = tuple(parent.add_widget(MyDropdown.__Option__, self, self.x, self.y + (i + 1) * self.height, self.width, self.height, choice, z_index=z_index + 1, justify=justify, word_wrap=word_wrap, border=border, highlight_border=highlight_border, active_border=active_border, color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg, color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg, on_mouse_click=lambda _1, mouse, index=i: self.__select_choice__(index, mouse)) for i, choice in enumerate(self.__choices__))
		self.__option_callback__: typing.Optional[typing.Callable[[int, Terminal.Struct.MouseInfo], None]] = None
		self.__choice_override__: Terminal.Struct.AnsiStr | None = None
		self.__selected__: int = 0
		self.__ghost_selected__: int = 0
		self.__word_wrap__: int = int(word_wrap)
		self.__scroll_rollover__: bool = bool(allow_scroll_rollover)
		self.__display_count__: int | None = None if display_count is None else max(0, int(display_count))
		self.__justify__: int = int(justify)
		self.__state__: bool = False
		self.__displayed__: bool = False
		self.__on_select__: typing.Callable[[MyWidget, bool], bool | None] = on_select
		self.__selection_changed__: bool = False

	def __draw1(self, mode: int):
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.selected, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)

		if (self.__justify__ & Terminal.Enums.EAST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 1 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif (self.__justify__ & Terminal.Enums.WEST) != 0:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.CENTER or self.__justify__ == Terminal.Enums.NORTH or self.__justify__ == Terminal.Enums.SOUTH:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw2(self, mode: int):
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.selected, lines, self.__word_wrap__, self.width - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y)
		self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + 1)

		if self.__justify__ == Terminal.Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.WEST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.EAST:
			delta: int = (self.height - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.CENTER:
			delta: int = (self.height - len(ansi_lines)) // 2
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + delta + i, self.width - 2)

	def __draw3(self, mode: int):
		border: Terminal.Struct.BorderInfo = self.__border__[mode]
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		ansi: str = f'\033[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}{"" if mode == 0 or (null_bg_color and null_fg_color) else ";7"}'
		self.__wordwrap__(self.selected, lines, self.__word_wrap__, self.width - 2, self.height - 2)
		ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		for i in range(1, self.height - 1):
			self.__terminal__.putstr(f'{ansi}m{" " * (self.width - 2)}', self.x + 1, self.y + i)

		if self.__justify__ == Terminal.Enums.NORTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_EAST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH_WEST:
			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.NORTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + 1 + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.SOUTH:
			middle: int = self.width // 2

			for i, ansi_line in enumerate(ansi_lines):
				ansi_line = ansi_line[:self.width - 2]
				self.__terminal__.putstr(ansi_line, self.x + middle - len(lines[i]) // 2, self.y + self.height - 1 - (len(lines) - i), self.width - 2)

		elif self.__justify__ == Terminal.Enums.WEST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + 1, self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.EAST:
			delta: int = (self.height - 2 - len(ansi_lines)) // 2

			for i, ansi_line in enumerate(ansi_lines):
				self.__terminal__.putstr(ansi_line, self.x + self.width - 2 - min(len(lines[i]), self.width - 2), self.y + 1 + delta + i, self.width - 2)

		elif self.__justify__ == Terminal.Enums.CENTER:
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

	def __select_choice__(self, index: int, mouse: Terminal.Struct.MouseInfo) -> None:
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

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  choices: typing.Optional[tuple[str | Terminal.Struct.AnsiStr, ...]] = ..., display_count: typing.Optional[int | None] = ..., justify: int = Terminal.Enums.CENTER, allow_scroll_rollover: bool = False, word_wrap: int = Terminal.Enums.WORDWRAP_WORD, on_select: typing.Optional[typing.Callable[[MyWidget], bool | None]] = ...,
				  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param choices: Display text
		:param z_index: The widget's z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param display_count: The number of choices to display at once
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param allow_scroll_rollover: Whether scrolling can cycle (too far down will cycle back to first option and vise versa)
		:param on_select: The callback to call once a choice is selected taking this widget and whether the choice was scrolled to (False) or clicked (True) as arguments and returning a boolean indicating whether to keep the selection
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'dropdown' is not a 'MyDropdown' instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises InvalidArgumentException: If any supplied choice is not a string, AnsiStr instance, or String instance
		:raises ValueError: If 'width' <= 2 or 'height' < 1
		:raises ValueError: If the number of choices is zero
		"""

		super().configure(x=x, y=y, z=z_index, width=width, height=height,
						  border=border, highlight_border=highlight_border, active_border=active_border,
						  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						  callback=callback,
						  on_focus=on_focus, off_focus=off_focus,
						  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						  on_tick=on_tick, on_close=on_close)

		choices = tuple(choices) if hasattr(choices, '__iter__') else choices
		Misc.raise_ifn(all(isinstance(choice, (str, Terminal.Struct.AnsiStr, Iterable.String)) for choice in choices), Exceptions.InvalidArgumentException(MyDropdown.configure, 'choices', type(choices)))
		self.__choices__: tuple[Terminal.Struct.AnsiStr, ...] = self.__choices__ if choices is None or choices is ... else tuple(Terminal.Struct.AnsiStr(text) for text in choices)

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')
		elif len(self.__choices__) == 0:
			raise ValueError('Dropbox is empty')

		self.__display_count__: int = self.__display_count__ if display_count is ... else None if display_count is None else max(0, int(display_count))
		self.__justify__: int = int(justify)
		self.__word_wrap__: int = self.__word_wrap__ if word_wrap is ... or word_wrap is None else int(word_wrap)
		self.__scroll_rollover__ = self.__scroll_rollover__ if allow_scroll_rollover is None or allow_scroll_rollover is ... else bool(allow_scroll_rollover)
		self.__on_select__ = None if on_select is None else self.__on_select__ if on_select is ... else on_select

		if choices is not None and choices is not ...:
			for option in self.__options__:
				self.__terminal__.del_widget(option.id)

			self.__options__: tuple[MyDropdown.__Option__, ...] = tuple(self.__terminal__.add_widget(MyDropdown.__Option__, self, self.x, self.y + (i + 1) * self.height, self.width, self.height, choice, z_index=z_index + 1, justify=justify, word_wrap=word_wrap, border=border, highlight_border=highlight_border, active_border=active_border, color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg, color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg, on_mouse_click=lambda _1, mouse, index=i: self.__select_choice__(index, mouse)) for i, choice in enumerate(self.__choices__))

	def option_configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
						 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
						 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
						 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
						 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
						 text: str | Terminal.Struct.AnsiStr = None, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_WORD,
						 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
						 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
						 ) -> None:
		"""
		Modifies this dropdown's option widgets
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param text: Display text
		:param z_index: The widget's z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'dropdown' is not a 'MyDropdown' instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		"""

		self.__option_callback__ = self.__option_callback__ if on_mouse_click is ... else on_mouse_click

		for option in self.__options__:
			option.configure(x=x, y=y, z_index=z_index, width=width, height=height,
							 callback=callback,
							 on_focus=on_focus, off_focus=off_focus,
							 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release,
							 on_tick=on_tick, on_close=on_close,
							 text=text, justify=justify, word_wrap=word_wrap,
							 border=border, highlight_border=highlight_border, active_border=active_border,
							 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
							 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg)

	def hide(self) -> None:
		super().hide()

		for option in self.__options__:
			option.hide()

	def close(self) -> None:
		for option in self.__options__:
			self.parent.del_widget(option.id)
		super().close()

	@property
	def justify(self) -> int:
		"""
		:return: This dropdown's text justification
		"""

		return self.__justify__

	@property
	def selected_index(self) -> int:
		"""
		:return: This dropdown's selected option by index
		"""

		return self.__selected__

	@selected_index.setter
	def selected_index(self, index: int) -> None:
		"""
		Sets this dropdown's selected option by index
		:param index: The option index
		:raises InvalidArgumentException: If 'index' is not an integer
		:raises IndexError: If 'index' is out of range
		"""

		if not isinstance(index, (int,)):
			raise Exceptions.InvalidArgumentException(MyDropdown.selected_index.setter, 'index', type(index), (int,))

		index = int(index)

		if index < 0 or index >= len(self.__choices__):
			raise IndexError(f'Index out of range for selected choices - 0 <= {index} < {len(self.__choices__)}')
		else:
			self.__selected__ = index
			self.__choice_override__ = None
			self.__selection_changed__ = True

	@property
	def selected(self) -> Terminal.Struct.AnsiStr:
		"""
		:return: This dropdown's selected option's text
		"""

		return self.__choices__[self.__selected__] if self.__choice_override__ is None else self.__choice_override__

	@selected.setter
	def selected(self, value: Terminal.Struct.AnsiStr | str | int) -> None:
		"""
		Sets this dropdown's selected option by option text or index
		:param value: The option text or index
		:raises InvalidArgumentException: If 'value' is not an integer, string, AnsiStr instance, or String instance
		:raises IndexError: If 'index' is out of range
		"""

		if not isinstance(value, (str, Terminal.Struct.AnsiStr, Iterable.String, int)):
			raise Exceptions.InvalidArgumentException(MyDropdown.selected.setter, 'value', type(value), (str, Terminal.Struct.AnsiStr, Iterable.String, int))
		elif isinstance(value, int):
			self.selected_index = int(value)
		else:
			raw: str = value if isinstance(value, str) else value.raw

			for i, choice in enumerate(self.__choices__):
				if choice.raw == raw:
					self.__choice_override__ = None
					self.__selected__ = i
					return

			self.__choice_override__ = Terminal.Struct.AnsiStr(value)
			self.__selection_changed__ = True

	@property
	def options_displayed(self) -> bool:
		"""
		:return: Whether the options list is currently displayed
		"""

		return self.__displayed__

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyDropdown.MySerializedDropdown


class MyEntry(MyActivatableWidget):
	"""
	Widget class representing a text entry
	"""

	class MySerializedEntry(MyActivatableWidget.MySerializedActivatableWidget):
		def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
					  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  word_wrap: int = Terminal.Enums.WORDWRAP_WORD, justify: typing.Optional[int] = ..., replace_chars: typing.Optional[str | Terminal.Struct.AnsiStr] = ..., placeholder: typing.Optional[str | Terminal.Struct.AnsiStr] = ..., cursor_blink_speed: typing.Optional[int] = ..., on_text: typing.Optional[typing.Callable[[MyEntry, bool], bool | Terminal.Struct.AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[MyEntry, Terminal.Struct.AnsiStr, int], bool | str | Terminal.Struct.AnsiStr | None]] = ...,
					  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					  ) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this widget
			Any value not supplied will not be updated
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param z_index: Z-index, higher is drawn last
			:param justify: Text justification (one of the cardinal direction enums)
			:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
			:param replace_chars: The character to replace entered characters with (visual only; for things like passwords)
			:param placeholder: The placeholder text to show when widget is empty
			:param cursor_blink_speed:
			:param on_text: The callback to call once the 'enter' is pressed taking this widget and whether text should be kept and returning either a boolean indicating whether to keep the modified text or a string to replace the accepted text
			:param on_input: The callback to call when a user enters any character taking this widget, the character entered, and the characters position in the string or -1 if at the end
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z_index' is not an integer
			:raises InvalidArgumentException: If 'width' is not an integer
			:raises InvalidArgumentException: If 'height' is not an integer
			:raises InvalidArgumentException: If 'replace_chars' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If 'placeholder' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises InvalidArgumentException: If any supplied border is not a border instance
			:raises ValueError: If 'width' <= 2 or 'height' < 1
			"""

			return self.send('configure()', x=x, y=y, z=z_index, width=width, height=height,
							  replace_chars=replace_chars, placeholder=placeholder, on_input=on_input, justify=justify, cursor_blink_speed=cursor_blink_speed, word_wrap=word_wrap, on_text=on_text,
							  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
							  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
							  callback=callback,
							  on_focus=on_focus, off_focus=off_focus,
							  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							  on_tick=on_tick, on_close=on_close)

		@property
		def justify(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with this entry's text justification
			"""

			return self.send('justify')

		@property
		def text(self) -> Concurrent.ThreadedPromise[Terminal.Struct.AnsiStr]:
			"""
			:return: A promise with this entry's text
			"""

			return self.send('text')

		@text.setter
		def text(self, text: str | Terminal.Struct.AnsiStr | Iterable.String) -> None:
			"""
			Sets this entry's text
			:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
			"""

			self.send('text', text)

		@property
		def cursor(self) -> Concurrent.ThreadedPromise[int]:
			"""
			Gets the position of this entry's cursor
			This position is where any text edits will appear
			:return: A promise with this entry's cursor position
			"""

			return self.send('cursor')

		@cursor.setter
		def cursor(self, cursor: int) -> None:
			"""
			Sets the position of this entry's cursor
			This position is where any text edits will appear
			:raises InvalidArgumentException: If 'cursor' is not an integer
			"""

			self.send('cursor', cursor)

	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, width: int, height: int, *, z_index: int = 0, word_wrap: int = Terminal.Enums.WORDWRAP_WORD, justify: int = Terminal.Enums.NORTH_WEST, replace_chars: str | Terminal.Struct.AnsiStr | Iterable.String = '', placeholder: typing.Optional[str | Terminal.Struct.AnsiStr | Iterable.String] = ..., cursor_blink_speed: int = 0, on_text: typing.Optional[typing.Callable[[MyEntry, bool], bool | Terminal.Struct.AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[MyEntry, Terminal.Struct.AnsiStr, int], bool | str | Terminal.Struct.AnsiStr | None]] = ...,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
		"""
		Widget class representing a text entry
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param replace_chars: The character to replace entered characters with (visual only; for things like passwords)
		:param placeholder: The placeholder text to show when widget is empty
		:param cursor_blink_speed:
		:param on_text: The callback to call once the 'enter' is pressed taking this widget and whether text should be kept and returning either a boolean indicating whether to keep the modified text or a string to replace the accepted text
		:param on_input: The callback to call when a user enters any character taking this widget, the character entered, and the characters position in the string or -1 if at the end
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z_index' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'replace_chars' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'placeholder' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises ValueError: If 'width' <= 2 or 'height' < 1
		"""

		if replace_chars is not ... and replace_chars is not None and not isinstance(replace_chars, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyEntry.__init__, 'replace_char', type(replace_chars), (str, Terminal.Struct.AnsiStr, Iterable.String))
		if placeholder is not ... and placeholder is not None and not isinstance(placeholder, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyEntry.__init__, 'placeholder', type(placeholder), (str, Terminal.Struct.AnsiStr, Iterable.String))
		if on_input is not None and on_input is not ... and not callable(on_input):
			raise Exceptions.InvalidArgumentException(MyEntry.__init__, 'on_input', type(on_input))

		replace_chars = '' if replace_chars is None or replace_chars is ... else Terminal.Struct.AnsiStr(replace_chars)
		placeholder = '' if placeholder is None or placeholder is ... else Terminal.Struct.AnsiStr(placeholder)

		super().__init__(parent, x, y, z_index, width, height,
						 color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus,
						 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		self.__justify__: int = int(justify)
		self.__text_index__: int = 0
		self.__placeholder__: typing.Optional[Terminal.Struct.AnsiStr] = None if len(placeholder) == 0 else placeholder
		self.__text__: list[tuple[str, Terminal.Struct.AnsiStr.AnsiFormat]] = []
		self.__old_text__: list[tuple[str, Terminal.Struct.AnsiStr.AnsiFormat]] = []
		self.__blink__: int = max(0, int(cursor_blink_speed))
		self.__start_blink__: int = 0
		self.__word_wrap__: int = int(word_wrap)
		self.__replace_chars__: Terminal.Struct.AnsiStr = replace_chars
		self.__text_callback__: typing.Callable[[MyEntry, bool], bool | str | None] = on_text
		self.__input_callback___: typing.Callable[[MyEntry, str | Terminal.Struct.AnsiStr, int], bool | str | Terminal.Struct.AnsiStr | None] = on_input

	def __draw(self, mode: int) -> None:
		bg_color: Terminal.Struct.Color = self.__bg_color__[mode]
		fg_color: Terminal.Struct.Color = self.__fg_color__[mode]
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
		lines: list[Terminal.Struct.AnsiStr] = []
		cursor: tuple[int, int] | None = None
		text_index: int = self.__text_index__
		self.__wordwrap__(self.__placeholder__ if self.__placeholder__ is not None and len(self.__text__) == 0 and not self.focused else self.text, lines, self.__word_wrap__)

		if len(self.__replace_chars__):
			ansi_lines.extend(f'{ansi}m{(self.__replace_chars__ * (math.ceil(len(line) / len(self.__replace_chars__))))[:len(line)]}' for line in lines)
		else:
			ansi_lines.extend(f'{ansi}m{line}' for line in lines)

		if self.__justify__ == Terminal.Enums.NORTH_EAST:
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
		elif self.__justify__ == Terminal.Enums.NORTH_WEST:
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
		elif self.__justify__ == Terminal.Enums.SOUTH_EAST:
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
		elif self.__justify__ == Terminal.Enums.SOUTH_WEST:
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
		elif self.__justify__ == Terminal.Enums.NORTH:
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
		elif self.__justify__ == Terminal.Enums.SOUTH:
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
		elif self.__justify__ == Terminal.Enums.WEST:
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
		elif self.__justify__ == Terminal.Enums.EAST:
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
		elif self.__justify__ == Terminal.Enums.CENTER:
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
			char: str | Terminal.Struct.AnsiStr = self.__replace_chars__[self.__text_index__ % len(self.__replace_chars__)] if self.__text_index__ < len(self.__text__) and len(self.__replace_chars__) else Terminal.Struct.AnsiStr.from_pairs((self.__text__[self.__text_index__],)) if self.__text_index__ < len(self.__text__) else ' '
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
		mouse_info: Terminal.Struct.MouseInfo = self.__terminal__.mouse
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
				char: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr(chr(c))
				endpoint: bool = self.__text_index__ == len(self.__text__)
				value: bool | Terminal.Struct.AnsiStr | None = True

				if callable(self.__input_callback___):
					value = self.__input_callback___(self, char, -1 if endpoint else self.__text_index__)
				elif callable(self.__general_callback__):
					value = self.__general_callback__(self, 'input', char, -1 if endpoint else self.__text_index__)
					value = True if value is None else value

				if isinstance(value, (str, Terminal.Struct.AnsiStr)):
					value = Terminal.Struct.AnsiStr(value)

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

			elif os.name == 'nt' and (c == curses.KEY_HOME or c == curses.CTL_HOME):
				self.__text_index__ = 0
			elif os.name != 'nt' and c == curses.KEY_HOME:
				self.__text_index__ = 0

			elif os.name == 'nt' and (c == curses.CTL_END or c == curses.KEY_END):
				self.__text_index__ = len(self.__text__)
			elif os.name != 'nt' and c == curses.KEY_END:
				self.__text_index__ = len(self.__text__)

			elif (os.name == 'nt' and (c == curses.SHF_PADENTER or c == curses.CTL_ENTER)) or (os.name != 'nt' and c == curses.KEY_ENTER):
				char: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr('\n')
				endpoint: bool = self.__text_index__ == len(self.__text__)
				value: bool |  Terminal.Struct.AnsiStr | None = True

				if callable(self.__input_callback___):
					value = self.__input_callback___(self, char, -1 if endpoint else self.__text_index__)
				elif callable(self.__general_callback__):
					value = self.__general_callback__(self, 'input', char, -1 if endpoint else self.__text_index__)
					value = True if value is None else value

				if isinstance(value, (str, Terminal.Struct.AnsiStr)):
					value = Terminal.Struct.AnsiStr(value)

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
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  word_wrap: int = Terminal.Enums.WORDWRAP_WORD, justify: typing.Optional[int] = ..., replace_chars: typing.Optional[str | Terminal.Struct.AnsiStr] = ..., placeholder: typing.Optional[str | Terminal.Struct.AnsiStr] = ..., cursor_blink_speed: typing.Optional[int] = ..., on_text: typing.Optional[typing.Callable[[MyEntry, bool], bool | Terminal.Struct.AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[MyEntry, Terminal.Struct.AnsiStr, int], bool | str | Terminal.Struct.AnsiStr | None]] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param replace_chars: The character to replace entered characters with (visual only; for things like passwords)
		:param placeholder: The placeholder text to show when widget is empty
		:param cursor_blink_speed:
		:param on_text: The callback to call once the 'enter' is pressed taking this widget and whether text should be kept and returning either a boolean indicating whether to keep the modified text or a string to replace the accepted text
		:param on_input: The callback to call when a user enters any character taking this widget, the character entered, and the characters position in the string or -1 if at the end
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z_index' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'replace_chars' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'placeholder' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises ValueError: If 'width' <= 2 or 'height' < 1
		"""

		super().configure(x=x, y=y, z=z_index, width=width, height=height,
						  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						  color_fg=color_fg, highlight_color_fg=highlight_color_fg, active_color_fg=active_color_fg,
						  callback=callback,
						  on_focus=on_focus, off_focus=off_focus,
						  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						  on_tick=on_tick, on_close=on_close)

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')
		if replace_chars is not ... and replace_chars is not None and not isinstance(replace_chars, (str, Terminal.Struct.AnsiStr)):
			raise Exceptions.InvalidArgumentException(MyEntry.configure, 'replace_char', type(replace_chars), (type(None), type(...), (str, Terminal.Struct.AnsiStr)))
		if placeholder is not ... and placeholder is not None and not isinstance(placeholder, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyEntry.configure, 'placeholder', type(placeholder), (str, Terminal.Struct.AnsiStr, Iterable.String))
		if on_input is not None and on_input is not ... and not callable(on_input):
			raise Exceptions.InvalidArgumentException(MyEntry.configure, 'on_input', type(on_input))

		replace_chars = self.__replace_chars__ if replace_chars is None or replace_chars is ... else Terminal.Struct.AnsiStr(replace_chars)
		placeholder = self.__placeholder__ if placeholder is None or placeholder is ... else Terminal.Struct.AnsiStr(placeholder)

		self.__justify__ = self.__justify__ if justify is ... or justify is None else int(justify)
		self.__replace_chars__ = replace_chars
		self.__placeholder__ = None if placeholder is None or len(placeholder) == 0 else Terminal.Struct.AnsiStr(placeholder)
		self.__blink__ = self.__blink__ if cursor_blink_speed is ... or cursor_blink_speed is None else max(0, int(cursor_blink_speed))
		self.__word_wrap__ = self.__word_wrap__ if word_wrap is ... or word_wrap is None else int(word_wrap)
		self.__text_callback__ = self.__text_callback__ if on_text is ... else on_text
		self.__input_callback___ = self.__input_callback___ if on_input is ... else on_input

	@property
	def justify(self) -> int:
		"""
		:return: This entry's text justification
		"""

		return self.__justify__

	@property
	def text(self) -> Terminal.Struct.AnsiStr:
		"""
		:return: This entry's text
		"""

		return Terminal.Struct.AnsiStr.from_pairs(self.__text__)

	@text.setter
	def text(self, text: str | Terminal.Struct.AnsiStr | Iterable.String) -> None:
		"""
		Sets this entry's text
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		"""

		if not isinstance(text, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MyEntry.text.setter, 'text', type(text), (str, Terminal.Struct.AnsiStr, Iterable.String))

		self.__text__.clear()
		self.__old_text__.clear()
		self.__text__.extend(Terminal.Struct.AnsiStr(text).pairs())
		self.__old_text__.extend(Terminal.Struct.AnsiStr(text).pairs())

	@property
	def cursor(self) -> int:
		"""
		Gets the position of this entry's cursor
		This position is where any text edits will appear
		:return: This entry's cursor position
		"""

		return self.__text_index__

	@cursor.setter
	def cursor(self, cursor: int) -> None:
		"""
		Sets the position of this entry's cursor
		This position is where any text edits will appear
		:raises InvalidArgumentException: If 'cursor' is not an integer
		"""

		if not isinstance(cursor, int):
			raise Exceptions.InvalidArgumentException(MyEntry.cursor.setter, 'cursor', type(cursor), (int,))
		elif (cursor := int(cursor)) >= 0:
			self.__text_index__ = min(int(cursor), len(self.__text__) + 1)
		else:
			self.__text_index__ = max(0, len(self.__text__) + cursor + 1)

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyEntry.MySerializedEntry


class MyImage(MyActivatableWidget):
	"""
	Widget class representing an image
	"""

	class MySerializedImage(MyActivatableWidget.MySerializedActivatableWidget):
		def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
					  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  image: typing.Optional[str | Terminal.Struct.AnsiStr | numpy.ndarray | PIL.Image.Image] = ..., div: typing.Optional[int] = ..., use_subpad: typing.Optional[bool] = ...,
					  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ...,
					  ) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this widget
			Any value not supplied will not be updated
			:param x: The widget's x position
			:param y: The widget's y position
			:param width: The widget's width in characters
			:param height: The widget's height in characters
			:param z_index: The widget's z-index, higher is drawn last
			:param image: The image filepath, numpy image array, or PIL image to display
			:param div: The color division ratio (bit depth) of the image. Set to a higher value for terminals with lower available color spaces
			:param use_subpad: Whether to use a curses sub-pad instead of drawing to the main display (may improve performance for larger images)
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param highlight_color_bg: The background color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If 'width' is not an integer
			:raises InvalidArgumentException: If 'height' is not an integer
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises ValueError: If 'width' < 3 or 'height' < 3
			"""

			return self.send('configure()', x=x, y=y, z=z_index, width=width, height=height,
							  image=image, div=div, use_subpad=use_subpad,
							  border=border, highlight_border=highlight_border, active_border=active_border,
							  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
							  callback=callback,
							  on_focus=on_focus, off_focus=off_focus,
							  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							  on_tick=on_tick, on_close=on_close)

		@property
		def div(self) -> Concurrent.ThreadedPromise[tuple[int, typing.Optional[int]]]:
			"""
			:return: A promise with this image's color division ratio
			"""

			return self.send('div')

		@property
		def image(self) -> Concurrent.ThreadedPromise[numpy.ndarray]:
			"""
			:return: A promise with the numpy image array
			"""

			return self.send('image')

		@property
		def grayscale(self) -> Concurrent.ThreadedPromise[numpy.ndarray]:
			"""
			:return: A promise with the numpy grayscale image array
			"""

			return self.send('grayscale')

		@property
		def raw_image(self) -> Concurrent.ThreadedPromise[typing.Optional[str | Terminal.Struct.AnsiStr | numpy.ndarray | PIL.Image.Image]]:
			"""
			:return: A promise with the original supplied image or filepath or None if not supplied
			"""

			return self.send('raw_image')

	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, width: int, height: int, image: str | Terminal.Struct.AnsiStr | numpy.ndarray | PIL.Image.Image | None, *, div: typing.Optional[int] = ..., use_subpad: bool = True, z_index: int = 0,
				 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
		"""
		Widget class representing an image
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param z_index: The widget's z-index, higher is drawn last
		:param image: The image filepath, numpy image array, or PIL image to display
		:param div: The color division ratio (bit depth) of the image. Set to a higher value for terminals with lower available color spaces
		:param use_subpad: Whether to use a curses sub-pad instead of drawing to the main display (may improve performance for larger images)
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param highlight_color_bg: The background color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises ValueError: If 'width' < 3 or 'height' < 3
		"""

		super().__init__(parent, x, y, z_index, width, height,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus,
						 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)

		if self.width < 3 or self.height < 3:
			raise ValueError('Dimensions too small (width >= 3; height >= 3)')

		self.__do_subpad__: bool = bool(use_subpad)
		self.__window__: _curses.window | None = None
		self.__pixel_div__: tuple[int, typing.Optional[int]] = (-1, div)
		self.__update_draw_image__(image, div, width - 2, height - 2)
		self.__border__: tuple[Terminal.Struct.BorderInfo | None, Terminal.Struct.BorderInfo | None, Terminal.Struct.BorderInfo | None] = (border, highlight_border, active_border)
		self.__bg_color__: tuple[Terminal.Struct.Color, Terminal.Struct.Color, Terminal.Struct.Color] = (color_bg, highlight_color_bg, active_color_bg)

	def __update_draw_image__(self, image: str | Terminal.Struct.AnsiStr | numpy.ndarray | PIL.Image.Image, div: typing.Optional[int], width: int, height: int) -> None:
		if image is not None:
			try:
				pilimage: PIL.Image.Image

				if isinstance(image, str):
					pilimage = PIL.Image.open(image).convert('RGB')
				elif isinstance(image, Terminal.Struct.AnsiStr):
					pilimage = PIL.Image.open(image.raw).convert('RGB')
				elif isinstance(image, numpy.ndarray):
					pilimage = PIL.Image.fromarray(image).convert('RGB')
				elif isinstance(image, PIL.Image.Image):
					pilimage = image.convert('RGB')
				else:
					raise Exceptions.InvalidArgumentException(MyImage.__init__, 'image', type(image), (str, Terminal.Struct.AnsiStr, numpy.ndarray, PIL.Image.Image))

				self.__img_actual__: str | Terminal.Struct.AnsiStr | numpy.ndarray | PIL.Image.Image = image
				image: numpy.ndarray = numpy.array(pilimage).astype(numpy.uint8)
				image = cv2.resize(image, dsize=(width, height), interpolation=cv2.INTER_CUBIC)
				true_div: int = -1

				if div is None or div is ...:
					divs: tuple[int, ...] = (4, 8, 16, 32, 64, 128)
					topmost: Terminal.Terminal.Terminal = self.topmost_parent()
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

				self.__image__ = Terminal.Struct.AnsiStr(''.join(image_str))
				self.__raw_image__ = (image, grayscale)
				self.__pixel_div__ = (true_div, div)
			except (IOError, OSError):
				self.__image__: Terminal.Struct.AnsiStr = Terminal.Struct.AnsiStr('')
				self.__raw_image__ = None
		else:
			self.__image__ = Terminal.Struct.AnsiStr('')
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
		root: Terminal.Terminal.Terminal = self.topmost_parent()
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
		border: Terminal.Struct.BorderInfo | None = self.__border__[mode]
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
			self.__update_draw_image__(self.__img_actual__, self.__pixel_div__[1], width - 2, height - 2)

	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ...,
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  image: typing.Optional[str | Terminal.Struct.AnsiStr | numpy.ndarray | PIL.Image.Image] = ..., div: typing.Optional[int] = ..., use_subpad: typing.Optional[bool] = ...,
				  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: The widget's x position
		:param y: The widget's y position
		:param width: The widget's width in characters
		:param height: The widget's height in characters
		:param z_index: The widget's z-index, higher is drawn last
		:param image: The image filepath, numpy image array, or PIL image to display
		:param div: The color division ratio (bit depth) of the image. Set to a higher value for terminals with lower available color spaces
		:param use_subpad: Whether to use a curses sub-pad instead of drawing to the main display (may improve performance for larger images)
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param highlight_color_bg: The background color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Terminal.Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises ValueError: If 'width' < 3 or 'height' < 3
		"""

		super().configure(x=x, y=y, z=z_index, width=width, height=height,
						  border=border, highlight_border=highlight_border, active_border=active_border,
						  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						  callback=callback,
						  on_focus=on_focus, off_focus=off_focus,
						  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						  on_tick=on_tick, on_close=on_close)

		if self.width <= 2 or self.height < 1:
			raise ValueError('Dimensions too small (width > 2; height >= 1)')

		if image is not ... or div != self.__pixel_div__[1]:
			image = self.__img_actual__ if image is None or image is ... else image
			w, h = self.size
			self.__update_draw_image__(image, self.__pixel_div__ if div is ... else None if div is None else int(div), w - 2, h - 2)

		self.__do_subpad__: bool = self.__do_subpad__ if use_subpad is ... or use_subpad is None else bool(use_subpad)

	@property
	def div(self) -> tuple[int, typing.Optional[int]]:
		"""
		:return: This image's color division ratio
		"""

		return self.__pixel_div__

	@property
	def image(self) -> numpy.ndarray:
		"""
		:return: The numpy image array
		"""

		return self.__raw_image__[0]

	@property
	def grayscale(self) -> numpy.ndarray:
		"""
		:return:  The numpy grayscale image array
		"""

		return self.__raw_image__[1]

	@property
	def raw_image(self) -> typing.Optional[str | Terminal.Struct.AnsiStr | numpy.ndarray | PIL.Image.Image]:
		"""
		:return: The original supplied image or filepath or None if not supplied
		"""

		return self.__img_actual__ if hasattr(self, '__img_actual__') else None

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MyImage.MySerializedImage


class MySubTerminal(MyActivatableWidget):
	"""
	Widget class representing a nested sub-terminal
	"""

	class MySerializedSubTerminal(MyActivatableWidget.MySerializedActivatableWidget):
		def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ..., name: str | Terminal.Struct.AnsiStr | Iterable.String = ..., transparent: bool = ...,
					  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
					  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
					  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
					  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					  ) -> Concurrent.ThreadedPromise[None]:
			"""
			Modifies this widget
			Any value not supplied will not be updated
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param name: Display title
			:param z_index: Z-index, higher is drawn last
			:param transparent: Whether to display the contents this sub-terminal will overlap
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
			:return: A promise
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises InvalidArgumentException: If 'z' is not an integer
			:raises InvalidArgumentException: If 'width' is not an integer
			:raises InvalidArgumentException: If 'height' is not an integer
			:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If any supplied callback is not callable
			:raises InvalidArgumentException: If any supplied border is not a border instance
			:raises InvalidArgumentException: If 'width' < 3 or 'height' < 3
			"""

			return self.send('configure()', x=x, y=y, z=z_index, width=width, height=height,
							  name=name, transparent=transparent,
							  border=border, highlight_border=highlight_border, active_border=active_border,
							  callback=callback,
							  on_focus=on_focus, off_focus=off_focus,
							  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
							  on_tick=on_tick, on_close=on_close)

		def putstr(self, msg: str | Terminal.Struct.AnsiStr | Iterable.String, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., n: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[None]:
			"""
			Prints a string to the sub-terminal
			:param msg: A string, String or AnsiStr instance
			:param x: The x coordinate or current x if not supplied
			:param y: The y coordinate or current y if not supplied
			:param n: ?
			:return: A promise
			:raises InvalidArgumentException: If 'msg' is not a string, String instance, or AnsiStr instance
			:raises InvalidArgumentException: If 'x', 'y', or 'n' is not an integer
			"""

			return self.send('putstr()', msg, x, y, n)

		def del_widget(self, _id: int) -> Concurrent.ThreadedPromise[None]:
			"""
			Deletes a widget by ID
			:param _id: The widget's ID
			:return: A promise
			:raises InvalidArgumentException: If '_id' is not an integer
			"""

			return self.send('del_widget()', _id)

		def del_sub_terminal(self, _id: int) -> Concurrent.ThreadedPromise[None]:
			"""
			Deletes a sub-terminal by ID
			:param _id: The sub-terminal's ID
			:return: A promise
			:raises InvalidArgumentException: If '_id' is not an integer
			"""

			return self.send('del_sub_terminal()', _id)

		def cancel(self, _id: int) -> Concurrent.ThreadedPromise[None]:
			"""
			Cancels a scheduled callback by ID
			:param _id: The callback's ID
			:return: A promise
			:raises InvalidArgumentException: If '_id' is not an integer
			"""

			return self.send('cancel()', _id)

		def cursor_visibility(self, visibility: int) -> Concurrent.ThreadedPromise[None]:
			"""
			Sets the cursor visibility
			 ... 0 - Hidden
			 ... 1 - Visible
			 ... 2 - Very visible
			:param visibility: The cursor visibility
			:return: A promise
			:raises InvalidArgumentException: if 'visibility' is not an integer
			:raises ValueError: If 'visibility' is not 0, 1, or 2
			"""

			return self.send('cursor_visibility()', visibility)

		def cursor_flash(self, flash_rate: int) -> Concurrent.ThreadedPromise[None]:
			"""
			Sets the cursor flash
			Cursor will complete one half flash cycle every 'flash_rate' ticks
			The actual rate of cursor flashing will depend on terminal tick rate
			For a one-second interval, this value should equal the terminal tick rate
			:param flash_rate: Flash rate in ticks
			:return: A promise
			:raises InvalidArgumentException: if 'flash_rate' is not an integer
			:raises ValueError: If 'flash_rate' is not positive
			"""

			return self.send('cursor_flash()', flash_rate)

		def set_focus(self, widget: MyWidget | int | None) -> Concurrent.ThreadedPromise[None]:
			"""
			Sets focus on a specific widget or clears focus if None
			:param widget: The widget to focus or None to clear focus
			:return: A promise
			:raises InvalidArgumentException: If 'widget' is not a Widget instance
			:raises ValueError: If the widget's handling terminal is not this sub-terminal
			"""

			return self.send('set_focus()', None if widget is None else widget.id if isinstance(widget, MyWidget) else int(widget))

		def ungetch(self, key: int) -> Concurrent.ThreadedPromise[None]:
			"""
			Appends a key to this sub-terminal's event queue
			:param key: The key code to append
			:return: A promise
			:raises InvalidArgumentException: If 'key' is not an integer
			"""

			return self.send('ungetch()', key)

		def ungetgch(self, key: int) -> Concurrent.ThreadedPromise[None]:
			"""
			Appends a key to this terminal's global event queue
			:param key: The key code to append
			:return: A promise
			:raises InvalidArgumentException: If 'key' is not an integer
			"""

			return self.send('ungetgch()', key)

		def erase_refresh(self, flag: bool) -> Concurrent.ThreadedPromise[None]:
			"""
			:param flag: Whether this sub-terminal will fully erase the sub-terminal before the next draw
			:return: A promise
			"""

			return self.send('erase_refresh()', flag)

		def getch(self) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
			"""
			Reads the next key code from this sub-terminal's event queue
			:return: A promise with the next key code or None if no event is waiting
			"""

			return self.send('getch()')

		def peekch(self) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
			"""
			Peeks the next key code from this sub-terminal's event queue
			:return: A promise with the next key code or None if no event is waiting
			"""

			return self.send('peekch()')

		def getgch(self) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
			"""
			Reads the next key code from this terminal's global event queue
			:return: A promise with the next key code or None if no event is waiting
			"""

			return self.send('getgch()')

		def peekgch(self) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
			"""
			Peeks the next key code from this terminal's global event queue
			:return: A promise with the next key code or None if no event is waiting
			"""

			return self.send('peekgch()')

		def scroll_speed(self, scroll: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
			"""
			Gets or sets the sub-terminal's scrolling speed in lines per scroll button
			If the mouse scrolls once, this sub-terminal will scroll 'scroll' lines
			:param scroll: The number of lines to scroll per scroll button press
			:return: A promise with the scroll speed if 'scroll' is unset otherwise None
			:raises InvalidArgumentException: If 'scroll' is not an integer
			"""

			return self.send('scroll_speed()', scroll)

		def after(self, ticks: int, callback: typing.Callable, *args, __threaded: bool = True, **kwargs) -> Concurrent.ThreadedPromise[int]:
			"""
			Schedules a function to be executed after a certain number of ticks
			:param ticks: The number of terminal ticks to execute after
			:param callback: The callable callback
			:param args: The positional arguments to pass
			:param __threaded: Whether to use a threading.Thread
			:param kwargs: The keyword arguments to pass
			:return: A promise with the scheduled callback ID
			"""

			return self.send('after()', ticks, callback, *args, __threaded=__threaded, **kwargs)

		def cursor(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[typing.Optional[tuple[int, int]]]:
			"""
			Gets or sets the sub-terminal's current cursor position
			:param x: The new cursor x position
			:param y: The new cursor y position
			:return: A promise with the current cursor position if 'x' and 'y' are unset otherwise None
			"""

			return self.send('cursor()', x, y)

		def scroll(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[typing.Optional[tuple[int, int]]]:
			"""
			Gets or sets the sub-terminal's current scroll offset
			:param x: The new scroll x offset
			:param y: The new scroll y offset
			:return: A promise with the current scroll offset if 'x' and 'y' are unset otherwise None
			"""

			return self.send('scroll()', x, y)

		def first_empty_row(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with the first empty row
			"""

			return self.send('first_empty_row()')

		def last_empty_row(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with the last empty row
			"""

			return self.send('last_empty_row()')

		def first_empty_column(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with the first empty column
			"""

			return self.send('first_empty_column()')

		def last_empty_column(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with the last empty column
			"""

			return self.send('last_empty_column()')

		def tab_size(self, size: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
			"""
			Gets or sets this sub-terminal's tab size
			Tab will equal the space character times this value
			:param size: The tab size in characters
			:return: A promise with the current tab size if 'size' is unset otherwise None
			:raises InvalidArgumentException: If 'size' is not an integer
			:raises ValueError: If 'size' is less than 0
			"""

			return self.send('tab_size()', size)

		def chat(self, x: int, y: int) -> Concurrent.ThreadedPromise[tuple[int, int]]:
			"""
			Gets the character and its format attribute at the specified position
			:param x: The x position
			:param y: The y position
			:return: A promise with the character and attribute
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			"""

			return self.send('chat()', x, y)

		def to_fixed(self, x: int, y: int) -> Concurrent.ThreadedPromise[tuple[int, int]]:
			"""
			Converts the specified scroll independent coordinate into true sub-terminal coordinates
			An input of (0, 0) will always give the top-left corner regardless of scroll offset
			:param x: The scroll independent x coordinate
			:param y: The scroll independent y coordinate
			:return: A promise with the true adjusted coordinates
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			"""

			return self.send('to_fixed()', x, y)

		def from_fixed(self, x: int, y: int) -> Concurrent.ThreadedPromise[tuple[int, int]]:
			"""
			Converts the specified true sub-terminal coordinate into scroll independent coordinates
			:param x: The true x coordinate
			:param y: The true y coordinate
			:return: A promise with the scroll independent coordinates
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			"""

			return self.send('from_fixed()', x, y)

		def getline(self, replace_char: typing.Optional[str | Terminal.Struct.AnsiStr | Iterable.String] = ..., prompt: typing.Optional[str | Terminal.Struct.AnsiStr | Iterable.String] = '', x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[str]:
			"""
			Pauses terminal execution and reads a line from the user
			For standard input without pausing, add an 'Entry' widget
			:param replace_char: The character to replace entered characters with (usefull for passwords or hidden entries)
			:param prompt: The prompt to display
			:param x: The x position to display at
			:param y: The y position to display at
			:return: A promise with the entered string
			:raises InvalidArgumentException: If 'replace_char' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If 'prompt' is not a string, AnsiStr instance, or String instance
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			:raises ValueError: If 'replace_char' is not a single character
			"""

			return self.send('getline()', replace_char, prompt, x, y)

		def get_topmost_child_at(self, x: int, y: int) -> Concurrent.ThreadedPromise[typing.Optional[MyWidget.MySerializedWidget]]:
			"""
			Gets the topmost widget at the specified coordinates
			:param x: The x coordinate to check
			:param y: The y coordinate to check
			:return: A promise with the topmost widget or None if no widget exists
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			"""

			return self.send('get_topmost_child_at()', x, y)

		def get_focus(self) -> Concurrent.ThreadedPromise[typing.Optional[MyWidget.MySerializedWidget]]:
			"""
			:return: A promise with the widget with focus or None if no widget has focus
			"""

			return self.send('get_focus()')

		def active_subterminal(self) -> Concurrent.ThreadedPromise[typing.Optional[MySubTerminal.MySerializedSubTerminal]]:
			"""
			:return: A promise with the sub-terminal with focus or None if no sub-terminal is active
			"""

			return self.send('active_subterminal()')

		def get_widget(self, _id: int) -> Concurrent.ThreadedPromise[MyWidget.MySerializedWidget]:
			"""
			Gets the widget with the specified ID
			:param _id: The widget ID
			:return: A promise with the widget
			:raises InvalidArgumentException: If '_id' is not an integer
			:raises KeyError: If no widget with the specified ID exists
			"""

			return self.send('get_widget()', _id)

		def get_sub_terminal(self, _id: int) -> Concurrent.ThreadedPromise[MySubTerminal.MySerializedSubTerminal]:
			"""
			Gets the sub-terminal with the specified ID
			:param _id: The sub-terminal ID
			:return: A promise with the sub-terminal
			:raises InvalidArgumentException: If '_id' is not an integer
			:raises KeyError: If no sub-terminal with the specified ID exists
			"""

			return self.send('get_sub_terminal()', _id)

		def get_children_at(self, x: int, y: int) -> Concurrent.ThreadedPromise[tuple[MyWidget.MySerializedWidget, ...]]:
			"""
			Gets all widgets or sub-terminals at the specified coordinates
			:param x: The x coordinate to check
			:param y: The y coordinate to check
			:return: A promise with all widgets or sub-terminals overlapping the specified coordinates
			:raises InvalidArgumentException: If 'x' is not an integer
			:raises InvalidArgumentException: If 'y' is not an integer
			"""

			return self.send('get_children_at()', x, y)

		def widgets(self) -> Concurrent.ThreadedPromise[tuple[MyWidget.MySerializedWidget, ...]]:
			"""
			:return: A promise with all widgets in this sub-terminal
			"""

			return self.send('widgets()')

		def subterminals(self) -> Concurrent.ThreadedPromise[tuple[MySubTerminal.MySerializedSubTerminal, ...]]:
			"""
			:return: A promise with all sub-terminals in this sub-terminal
			"""

			return self.send('subterminals()')

		def children(self) -> Concurrent.ThreadedPromise[dict[int, MyWidget.MySerializedWidget]]:
			"""
			:return: A promise with all widgets and sub-terminals in this sub-terminal
			"""

			return self.send('children()')

		### Widget methods
		def add_button(self, x: int, y: int, width: int, height: int, text: str | Terminal.Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_NONE,
					   border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					   color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					   callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MyButton.MySerializedButton]:
			"""
			Adds a new button widget to this terminal
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param text: Display text
			:param z_index: Z-index, higher is drawn last
			:param justify: Text justification (one of the cardinal direction enums)
			:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the button widget
			"""

			return self.send('add_button()', x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
										border=border, highlight_border=highlight_border, active_border=active_border,
										color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
										callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_toggle_button(self, x: int, y: int, width: int, height: int, text: str | Terminal.Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_NONE,
							  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
							  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
							  callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MyToggleButton.MySerializedToggleButton]:
			"""
			Adds a new toggle button widget to this terminal
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param text: Display text
			:param z_index: Z-index, higher is drawn last
			:param justify: Text justification (one of the cardinal direction enums)
			:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the button widget
			"""

			return self.send('add_toggle_button()', x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
													border=border, highlight_border=highlight_border, active_border=active_border,
													color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
													callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str | Terminal.Struct.AnsiStr | Iterable.String = '', active_text: str | Terminal.Struct.AnsiStr | Iterable.String = 'X',
						 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
						 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
						 callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_checked: typing.Optional[typing.Callable[[[MyWidget], bool], None]] = ...) -> Concurrent.ThreadedPromise[MyCheckbox.MySerializedCheckbox]:
			"""
			Adds a new checkbox button widget to this terminal
			:param x: X position
			:param y: Y position
			:param text: Text to display when checkbox is unchecked
			:param active_text: Text to display when checkbox is checked
			:param z_index: Z-index, higher is drawn last
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:param on_checked: The callback to call when the checkbox's checked state changes this widget and the widget's current state as arguments
			:return: A promise with the checkbox button widget
			"""

			return self.send('add_checkbox()', x, y, z_index=z_index, text=text, active_text=active_text,
											border=border, highlight_border=highlight_border, active_border=active_border,
											color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
											callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close, on_checked=on_checked)

		def add_inline_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str | Terminal.Struct.AnsiStr | Iterable.String = '', active_text: str | Terminal.Struct.AnsiStr | Iterable.String = 'X',
								border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
								color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
								callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_checked: typing.Optional[typing.Callable[[[MyWidget], bool], None]] = ...) -> Concurrent.ThreadedPromise[MyInlineCheckbox.MySerializedInlineCheckbox]:
			"""
			Adds a new inline checkbox button widget to this terminal
			:param x: X position
			:param y: Y position
			:param text: Text to display when checkbox is unchecked
			:param active_text: Text to display when checkbox is checked
			:param z_index: Z-index, higher is drawn last
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:param on_checked: The callback to call when the checkbox's checked state changes this widget and the widget's current state as arguments
			:return: A promise with the checkbox button widget
			"""

			return self.send('add_inline_checkbox()', x, y, z_index=z_index, text=text, active_text=active_text,
														border=border, highlight_border=highlight_border, active_border=active_border,
														color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
														callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close, on_checked=on_checked)

		def add_radial_spinner(self, x: int, y: int, *, z_index: int = 0, phases: typing.Iterable[str | Terminal.Struct.AnsiStr | Iterable.String] = ('--', '\\', '|', '/'), bg_phase_colors: typing.Optional[Terminal.Enums.Color_T] | typing.Iterable[typing.Optional[Terminal.Enums.Color_T]] = ..., fg_phase_colors: typing.Optional[Terminal.Enums.Color_T] | typing.Iterable[typing.Optional[Terminal.Enums.Color_T]] = Terminal.Struct.Color(0xFFFFFF),
							   callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MyRadialSpinner.MySerializedRadialSpinner]:
			"""
			Adds a new radial spinner widget to this terminal
			:param x: X position
			:param y: Y position
			:param z_index: Z-index, higher is drawn last
			:param phases: The individual frames to display
			:param bg_phase_colors: The background colors to cycle through when ticking
			:param fg_phase_colors: The foreground colors to cycle through when ticking
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the radial spinner widget
			"""

			return self.send('add_radial_spinner()', x, y, z_index=z_index, phases=phases, bg_phase_colors=bg_phase_colors, fg_phase_colors=fg_phase_colors,
													  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_horizontal_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, step: float = 1, fill_char: str | Terminal.Struct.AnsiStr | Iterable.String = '|', _max: float = 10, _min: float = 0, on_input: typing.Callable[[MyHorizontalSlider], None] = ...,
								  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
								  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
								  callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MyHorizontalSlider.MySerializedHorizontalSlider]:
			"""
			Adds a new horizontal slider widget to this terminal
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param z_index: Z-index, higher is drawn last
			:param step: The amount to increment by per scroll
			:param fill_char: The character to use to show value
			:param _max: The maximum value of this slider
			:param _min: The minimum value of this slider
			:param on_input: The callback to call once the mouse enters this widget taking this widget as an argument
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the horizontal slider widget
			"""

			return self.send('add_horizontal_slider()', x, y, width, height, z_index=z_index, step=step, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
															border=border, highlight_border=highlight_border, active_border=active_border,
															color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
															callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_vertical_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Terminal.Struct.AnsiStr | Iterable.String = '=', _max: float = 10, _min: float = 0, on_input: typing.Callable[[MyVerticalSlider], None] = ...,
								border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
								color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
								callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MyVerticalSlider.MySerializedVerticalSlider]:
			"""
			Adds a new vertical slider widget to this terminal
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param z_index: Z-index, higher is drawn last
			:param fill_char: The character to use to show value
			:param _max: The maximum value of this slider
			:param _min: The minimum value of this slider
			:param on_input: The callback to call once the mouse enters this widget taking this widget as an argument
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the vertical slider widget
			"""

			return self.send('add_vertical_slider()', x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
														border=border, highlight_border=highlight_border, active_border=active_border,
														color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
														callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_horizontal_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Terminal.Struct.AnsiStr | Iterable.String = '|', _max: float = 10, _min: float = 0,
										border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
										color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
										callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MyHorizontalProgressBar.MySerializedHorizontalProgressBar]:
			"""
			Adds a new horizontal progress bar widget to this terminal
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param z_index: Z-index, higher is drawn last
			:param fill_char: The character to use to show value
			:param _max: The maximum value of this slider
			:param _min: The minimum value of this slider
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the horizontal progress bar widget
			"""

			return self.send('add_horizontal_progress_bar()', x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
																	  border=border, highlight_border=highlight_border, active_border=active_border,
																	  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																	  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_vertical_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Terminal.Struct.AnsiStr | Iterable.String = '=', _max: float = 10, _min: float = 0,
									  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
									  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
									  callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MyVerticalProgressBar.MySerializedVerticalProgressBar]:
			"""
			Adds a new vertical progress bar widget to this terminal
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param z_index: Z-index, higher is drawn last
			:param fill_char: The character to use to show value
			:param _max: The maximum value of this slider
			:param _min: The minimum value of this slider
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the vertical progress bar widget
			"""

			return self.send('add_vertical_progress_bar()', x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
																  border=border, highlight_border=highlight_border, active_border=active_border,
																  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_text(self, x: int, y: int, width: int, height: int, text: str | Terminal.Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Terminal.Enums.NORTH_WEST, word_wrap: int = Terminal.Enums.WORDWRAP_NONE,
					 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MyText.MySerializedText]:
			"""
			Adds a new text widget to this terminal
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param text: Display text
			:param z_index: Z-index, higher is drawn last
			:param justify: Text justification (one of the cardinal direction enums)
			:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the text widget
			"""

			return self.send('add_text()', x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
									color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
									callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_dropdown(self, x: int, y: int, width: int, height: int, choices: tuple[str | Terminal.Struct.AnsiStr | Iterable.String, ...], *, display_count: int | None = None, allow_scroll_rollover: bool = False, z_index: int = 0, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_WORD, on_select: typing.Optional[typing.Callable[[[MyWidget]], bool | None]] = ...,
						 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
						 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
						 callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MyDropdown.MySerializedDropdown]:
			"""
			Adds a new dropdown widget to this terminal
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param choices: The choices to display
			:param display_count: The number of choices to display at a time
			:param allow_scroll_rollover: Whether scrolling can cycle (too far down will cycle back to first option and vise versa)
			:param z_index: Z-index, higher is drawn last
			:param justify: Text justification (one of the cardinal direction enums)
			:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
			:param on_select: The callback to call once a choice is selected taking this widget and whether the choice was scrolled to (False) or clicked (True) as arguments and returning a boolean indicating whether to keep the selection
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the dropdown widget
			"""

			return self.send('add_dropdown()', x, y, width, height, choices, display_count=display_count, allow_scroll_rollover=allow_scroll_rollover, z_index=z_index, justify=justify, word_wrap=word_wrap, on_select=on_select,
											border=border, highlight_border=highlight_border, active_border=active_border,
											color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
											callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_entry(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, word_wrap: int = Terminal.Enums.WORDWRAP_WORD, justify: int = Terminal.Enums.NORTH_WEST, replace_chars: str | Terminal.Struct.AnsiStr | Iterable.String = '', placeholder: typing.Optional[str | Terminal.Struct.AnsiStr | Iterable.String] = ..., cursor_blink_speed: int = 0, on_text: typing.Optional[typing.Callable[[MyEntry, bool], bool | str | Terminal.Struct.AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[MyEntry, str | Terminal.Struct.AnsiStr, int], bool | str | Terminal.Struct.AnsiStr | None]] = ...,
					  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					  callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MyEntry.MySerializedEntry]:
			"""
			Adds a new entry widget to this terminal
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param z_index: Z-index, higher is drawn last
			:param justify: Text justification (one of the cardinal direction enums)
			:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
			:param replace_chars: The character to replace entered characters with (visual only; for things like passwords)
			:param placeholder: The placeholder text to show when widget is empty
			:param cursor_blink_speed:
			:param on_text: The callback to call once the 'enter' is pressed taking this widget and whether text should be kept and returning either a boolean indicating whether to keep the modified text or a string to replace the accepted text
			:param on_input: The callback to call when a user enters any character taking this widget, the character entered, and the characters position in the string or -1 if at the end
			:param color_bg: The background color
			:param color_fg: The foreground (text) color
			:param highlight_color_bg: The background color when mouse is hovering
			:param highlight_color_fg: The foreground color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param active_color_fg: The foreground color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the entry widget
			"""

			return self.send('add_entry()', x, y, width, height, z_index=z_index, word_wrap=word_wrap, justify=justify, replace_chars=replace_chars, placeholder=placeholder, cursor_blink_speed=cursor_blink_speed, on_text=on_text, on_input=on_input,
									  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
									  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_image(self, x: int, y: int, width: int, height: int, image: str | Terminal.Struct.AnsiStr | Iterable.String | numpy.ndarray | PIL.Image.Image, *, z_index: int = 0, use_subpad: bool = True, div: typing.Optional[int] = ...,
					  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ...,
					  callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MyImage.MySerializedImage]:
			"""
			Adds a new image widget to this terminal
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param image: The image filepath, numpy image array, or PIL image to display
			:param z_index: Z-index, higher is drawn last
			:param use_subpad: Whether to use a curses sub-pad instead of drawing to the main display (may improve performance for larger images)
			:param div: The color division ratio (bit depth) of the image. Set to a higher value for terminals with lower available color spaces
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param color_bg: The background color
			:param highlight_color_bg: The background color when mouse is hovering
			:param active_color_bg: The background color when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the image widget
			"""

			return self.send('add_image()', x, y, width, height, image, z_index=z_index, div=div, use_subpad=use_subpad,
									  border=border, highlight_border=highlight_border, active_border=active_border,
									  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
									  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_sub_terminal(self, x: int, y: int, width: int, height: int, *, title: typing.Optional[str | Terminal.Struct.AnsiStr | Iterable.String] = ..., z_index: int = 0, transparent: bool = False,
							 border: Terminal.Struct.BorderInfo = ..., highlight_border: Terminal.Struct.BorderInfo = ..., active_border: Terminal.Struct.BorderInfo = ...,
							 callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[MySubTerminal.MySerializedSubTerminal]:
			"""
			Adds a new sub-terminal to this terminal
			:param x: X position
			:param y: Y position
			:param width: Width in characters
			:param height: Height in characters
			:param title: Display title
			:param z_index: Z-index, higher is drawn last
			:param transparent: Whether to display the contents this sub-terminal will overlap
			:param border: The border to display
			:param highlight_border: The border to display when mouse is hovering
			:param active_border: The border to display when button is pressed
			:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
			:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
			:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
			:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
			:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
			:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
			:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
			:return: A promise with the sub-terminal
			"""

			return self.send('add_sub_terminal()', x, y, width, height, title, z_index=z_index, transparent=transparent,
													border=border, highlight_border=highlight_border, active_border=active_border,
													callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		def add_widget[T: MyWidget](self, cls: type[T], *args, z_index: int = 0, **kwargs) -> Concurrent.ThreadedPromise[MyWidget.MySerializedWidget]:
			"""
			Adds a new widget to this terminal
			This is for use with custom widget classes extending from the Widget class
			:param cls: The widget class to instantiate
			:param args: The positional arguments to pass into the constructor
			:param z_index: Z-index, higher is drawn last
			:param kwargs: The keyword arguments to pass into the constructor
			:return: A promise with the new widget
			"""

			assert issubclass(cls, MyWidget)
			return self.send('add_widget()', cls, *args, z_index=z_index, **kwargs)

		### Properties
		@property
		def screen(self) -> Concurrent.ThreadedPromise[_curses.window]:
			"""
			:return: A promise with the underlying curses window
			"""

			return self.send('screen')

		@property
		def enabled(self) -> Concurrent.ThreadedPromise[bool]:
			"""
			:return: A promise with whether the terminal is active
			"""

			return self.send('enabled')

		@property
		def exit_code(self) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
			"""
			:return: A promise with this terminal's exit code or None if still active
			"""

			return self.send('exit_code')

		@property
		def current_tick(self) -> Concurrent.ThreadedPromise[int]:
			"""
			:return: A promise with this terminal's current tick
			"""

			return self.send('current_tick')

		@property
		def mouse(self) -> Concurrent.ThreadedPromise[Terminal.Struct.MouseInfo]:
			"""
			:return: A promise with the mouse info holding the last mouse event this sub-terminal received
			"""

			return self.send('mouse')

		@property
		def transparent(self) -> Concurrent.ThreadedPromise[bool]:
			"""
			:return: A promise with whether to display the contents this sub-terminal will overlap
			"""

			return self.send('transparent')

		@transparent.setter
		def transparent(self, transparent: bool) -> None:
			"""
			Sets whether to display the contents this sub-terminal will overlap
			:param transparent: Transparency
			"""

			self.send('transparent', bool(transparent))

		@property
		def title(self) -> Concurrent.ThreadedPromise[str]:
			"""
			:return: A promise with this sub-terminal's title
			"""

			return self.send('title')

		@title.setter
		def title(self, title: str | Terminal.Struct.AnsiStr | Iterable.String) -> None:
			"""
			Sets this sub-terminal's title
			:param title: The new title
			:raises InvalidArgumentException: If 'title' is not a string, AnsiStr instance, or String instance
			"""

			Misc.raise_ifn(isinstance(title, (str, Terminal.Struct.AnsiStr, Iterable.String)), Exceptions.InvalidArgumentException(MySubTerminal.title.setter, 'title', type(title), (str, Terminal.Struct.AnsiStr, Iterable.String)))
			value: str = str(title) if isinstance(title, (str, Iterable.String)) else title.raw if isinstance(title, Terminal.Struct.AnsiStr) else ''
			self.send('title', value)

		@property
		def selected_subterminal(self) -> Concurrent.ThreadedPromise[typing.Optional[MySubTerminal]]:
			"""
			:return: A promise with the current focused sub-terminal or None if no sub-terminal is active
			"""

			return self.send('selected_subterminal')

		@property
		def default_bg(self) -> Concurrent.ThreadedPromise[Terminal.Struct.Color]:
			"""
			:return: A promise with he default terminal background color
			"""

			return self.send('default_bg')

		@property
		def default_fg(self) -> Concurrent.ThreadedPromise[Terminal.Struct.Color]:
			"""
			:return: A promise with he default terminal foreground color
			"""

			return self.send('default_fg')

	### Magic methods
	def __init__(self, parent: Terminal.Terminal.Terminal | MySubTerminal, x: int, y: int, width: int, height: int, name: str | Terminal.Struct.AnsiStr | Iterable.String = '', *, z_index: int = 0, transparent: bool = False,
				 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				 callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...):
		"""
		Widget class representing a nested sub-terminal
		- Constructor -
		:param parent: The parent terminal or sub-terminal this widget is bound to
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param name: Display title
		:param z_index: Z-index, higher is drawn last
		:param transparent: Whether to display the contents this sub-terminal will overlap
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'name' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'transparent' is not a boolean
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises ValueError: If 'width' < 3 or 'height' < 3
		"""

		super().__init__(parent, x, y, z_index, width, height,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 callback=callback,
						 on_focus=on_focus, off_focus=off_focus,
						 on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						 on_tick=on_tick, on_close=on_close)

		Misc.raise_ifn(self.width >= 3, ValueError('Width must be greater than 2'))
		Misc.raise_ifn(self.height >= 3, ValueError('Height must be greater than 2'))
		Misc.raise_ifn(isinstance(name, (str, Terminal.Struct.AnsiStr, Iterable.String)), Exceptions.InvalidArgumentException(MySubTerminal.__init__, 'name', type(name), (str, Terminal.Struct.AnsiStr, Iterable.String)))
		Misc.raise_ifn(isinstance(transparent, bool), Exceptions.InvalidArgumentException(MySubTerminal.__init__, 'transparent', type(transparent), (bool,)))

		self.__widgets__: dict[int, dict[int, MyWidget]] = {}
		self.__pages__: dict[int, dict[int, MySubTerminal]] = {}
		self.__previous_inputs__: list[str] = []
		self.__title__ = str(name) if isinstance(name, (str, Iterable.String)) else name.raw if isinstance(name, Terminal.Struct.AnsiStr) else ''
		self.__transparent__: bool = bool(transparent)

		self.__scroll__: list[int] = [0, 0]
		self.__cursor__: tuple[int, int, int, int] = (0, 0, 0, 0)
		self.__last_mouse_info__: Terminal.Struct.MouseInfo = Terminal.Struct.MouseInfo(-1, 0, 0, 0, 0)
		self.__event_queue__: Iterable.SpinQueue[int] = Iterable.SpinQueue(10)
		self.__auto_scroll__: int = 10
		self.__tab_size__: int = 4
		self.__active_page__: MySubTerminal | None = None
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
		"""
		INTERNAL METHOD
		Moves this terminal's cursor
		:param x: The new x position or current
		:param y: The new y position or current
		:return: The current position if both x and y are unset otherwise whether the terminal was moved
		:raises InvalidArgumentException: If x or y are not integers
		"""

		if (x is None or x is ...) and (y is None or y is ...):
			y, x = self.__stdscr__.getyx()
			return x, y
		elif x is not None and x is not ... and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(MySubTerminal.__move__, 'x', type(x), ('int',))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(MySubTerminal.__move__, 'y', type(y), ('int',))
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
		topmost: MyWidget | None = self.get_topmost_child_at(local_x, local_y)
		self.set_focus(topmost)

		if isinstance(topmost, MySubTerminal):
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

	def draw_border(self, border: Terminal.Struct.BorderInfo | None) -> None:
		if border is None:
			return
		elif not isinstance(border, Terminal.Struct.BorderInfo):
			raise Exceptions.InvalidArgumentException(MyWidget.draw_border, 'border', type(border), (Terminal.Struct.BorderInfo,))

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
		root: Terminal.Terminal.Terminal = self.topmost_parent()
		_id, x, y, z, bstate = root.mouse
		scroll_x, scroll_y = self.__scroll__
		gx, gy = self.global_pos()
		self.__last_mouse_info__ = Terminal.Struct.MouseInfo(_id, x - gx + scroll_x, y - gy + scroll_y, z, bstate)
		cx: int = self.__last_mouse_info__.pos_x
		cy: int = self.__last_mouse_info__.pos_y
		topmost: MyWidget | None = self.get_topmost_child_at(cx, cy)

		if self.__last_mouse_info__.scroll_up_pressed and self.__auto_scroll__ > 0 and topmost is None and self.is_mouse_inside:
			self.__scroll__[not self.__last_mouse_info__.alt_pressed] -= self.__auto_scroll__

		if self.__last_mouse_info__.scroll_down_pressed and self.__auto_scroll__ > 0 and topmost is None and self.is_mouse_inside:
			self.__scroll__[not self.__last_mouse_info__.alt_pressed] += self.__auto_scroll__

		if self.__last_mouse_info__.left_pressed or self.__last_mouse_info__.middle_pressed or self.__last_mouse_info__.right_pressed:
			if isinstance(topmost, MySubTerminal):
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
	def configure(self, *, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., z_index: typing.Optional[int] = ..., width: typing.Optional[int] = ..., height: typing.Optional[int] = ..., name: str | Terminal.Struct.AnsiStr | Iterable.String = ..., transparent: bool = ...,
				  callback: typing.Optional[typing.Callable[[MyWidget, str, ...], None]] = ...,
				  on_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  on_mouse_enter: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[MyWidget, Terminal.Struct.MouseInfo], None]] = ...,
				  on_tick: typing.Optional[typing.Callable[[MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[MyWidget], None]] = ...,
				  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				  ) -> None:
		"""
		Modifies this widget
		Any value not supplied will not be updated
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param name: Display title
		:param z_index: Z-index, higher is drawn last
		:param transparent: Whether to display the contents this sub-terminal will overlap
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:raises InvalidArgumentException: If 'parent' is not a Terminal or SubTerminal instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises InvalidArgumentException: If 'z' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'text' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If any supplied callback is not callable
		:raises InvalidArgumentException: If any supplied border is not a border instance
		:raises InvalidArgumentException: If 'width' < 3 or 'height' < 3
		"""

		super().configure(x=x, y=y, z=z_index, width=width, height=height,
						  border=border, highlight_border=highlight_border, active_border=active_border,
						  callback=callback,
						  on_focus=on_focus, off_focus=off_focus,
						  on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click,
						  on_tick=on_tick, on_close=on_close)

		Misc.raise_ifn(self.width >= 3, ValueError('Width must be greater than 2'))
		Misc.raise_ifn(self.height >= 3, ValueError('Height must be greater than 2'))
		Misc.raise_ifn(name is ... or name is None or isinstance(name, (str, Terminal.Struct.AnsiStr, Iterable.String)), Exceptions.InvalidArgumentException(MySubTerminal.configure, 'name', type(name), (str, Terminal.Struct.AnsiStr, Iterable.String)))
		Misc.raise_ifn(transparent is ... or transparent is None or isinstance(transparent, bool), Exceptions.InvalidArgumentException(MySubTerminal.configure, 'transparent', type(transparent), (bool,)))
		self.__title__ = self.__title__ if name is ... or name is None else str(name) if isinstance(name, (str, Iterable.String)) else name.raw if isinstance(name, Terminal.Struct.AnsiStr) else ''
		self.__transparent__ = self.__transparent__ if transparent is ... or transparent is None else bool(transparent)

	def putstr(self, msg: str | Terminal.Struct.AnsiStr | Iterable.String, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., n: typing.Optional[int] = ...) -> None:
		"""
		Prints a string to the sub-terminal
		:param msg: A string, String or AnsiStr instance
		:param x: The x coordinate or current x if not supplied
		:param y: The y coordinate or current y if not supplied
		:param n: ?
		:raises InvalidArgumentException: If 'msg' is not a string, String instance, or AnsiStr instance
		:raises InvalidArgumentException: If 'x', 'y', or 'n' is not an integer
		"""

		if not isinstance(msg, (str, Terminal.Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(MySubTerminal.putstr, 'msg', type(msg), (str, Terminal.Struct.AnsiStr))
		elif x is not ... and x is not None and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(MySubTerminal.putstr, 'x', type(x), (int,))
		elif y is not ... and y is not None and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(MySubTerminal.putstr, 'y', type(y), (int,))
		elif n is not ... and n is not None and not isinstance(n, int):
			raise Exceptions.InvalidArgumentException(MySubTerminal.putstr, 'n', type(n), (int,))

		n = None if n is None or n is ... else int(n)

		if n is not None and n <= 0:
			return

		msg = msg if isinstance(msg, Terminal.Struct.AnsiStr) else Terminal.Struct.AnsiStr(msg)
		root: Terminal.Terminal.Terminal = self.topmost_parent()
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
		"""
		Deletes a widget by ID
		:param _id: The widget's ID
		:raises InvalidArgumentException: If '_id' is not an integer
		"""

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(MySubTerminal.del_widget, '_id', type(_id), (int,)))
		_id = int(_id)

		for alloc in self.__widgets__.values():
			if _id in alloc:
				del alloc[_id]
				break

	def del_sub_terminal(self, _id: int) -> None:
		"""
		Deletes a sub-terminal by ID
		:param _id: The sub-terminal's ID
		:raises InvalidArgumentException: If '_id' is not an integer
		"""

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(MySubTerminal.del_sub_terminal, '_id', type(_id), (int,)))
		_id = int(_id)

		for alloc in self.__pages__.values():
			if _id in alloc:
				del alloc[_id]
				break

	def cancel(self, _id: int) -> None:
		"""
		Cancels a scheduled callback by ID
		:param _id: The callback's ID
		:raises InvalidArgumentException: If '_id' is not an integer
		"""

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(MySubTerminal.cancel, '_id', type(_id), (int,)))
		_id = int(_id)
		self.__terminal__.cancel(_id)

	def cursor_visibility(self, visibility: int) -> None:
		"""
		Sets the cursor visibility
		 ... 0 - Hidden
		 ... 1 - Visible
		 ... 2 - Very visible
		:param visibility: The cursor visibility
		:raises InvalidArgumentException: if 'visibility' is not an integer
		:raises ValueError: If 'visibility' is not 0, 1, or 2
		"""

		Misc.raise_ifn(isinstance(visibility, int), Exceptions.InvalidArgumentException(MySubTerminal.cursor_visibility, 'visibility', type(visibility), (int,)))
		Misc.raise_ifn(0 <= (visibility := int(visibility)) <= 2, ValueError('Cursor visibility must be either 0, 1, or 2'))
		cx, cy, _, rt = self.__cursor__
		self.__cursor__ = (cx, cy, visibility, rt)

	def cursor_flash(self, flash_rate: int) -> None:
		"""
		Sets the cursor flash
		Cursor will complete one half flash cycle every 'flash_rate' ticks
		The actual rate of cursor flashing will depend on terminal tick rate
		For a one-second interval, this value should equal the terminal tick rate
		:param flash_rate: Flash rate in ticks
		:raises InvalidArgumentException: if 'flash_rate' is not an integer
		:raises ValueError: If 'flash_rate' is not positive
		"""

		Misc.raise_ifn(isinstance(flash_rate, int), Exceptions.InvalidArgumentException(MySubTerminal.cursor_flash, 'flash_rate', type(flash_rate), (int,)))
		Misc.raise_ifn(flash_rate := int(flash_rate) >= 0, ValueError('Cursor flash_rate must be >= 0'))
		cx, cy, vs, _ = self.__cursor__
		self.__cursor__ = (cx, cy, vs, flash_rate)

	def set_focus(self, widget: MyWidget | int | None) -> None:
		"""
		Sets focus on a specific widget or clears focus if None
		:param widget: The widget or widget ID to focus or None to clear focus
		:raises InvalidArgumentException: If 'widget' is not a Widget instance or integer
		:raises ValueError: If the widget's handling terminal is not this sub-terminal
		"""

		if widget is not None and not isinstance(widget, (MyWidget, int)):
			raise Exceptions.InvalidArgumentException(MySubTerminal.set_focus, 'widget', type(widget), (MyWidget,))
		elif widget is None or isinstance(widget, int) or widget.parent is self:
			child: MyWidget
			old_page: MySubTerminal = self.__active_page__
			widget = self.get_widget(int(widget)) if isinstance(widget, int) else widget

			if widget is not None:
				subterminals: tuple[MySubTerminal, ...] = self.subterminals()

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
		"""
		Appends a key to this sub-terminal's event queue
		:param key: The key code to append
		:raises InvalidArgumentException: If 'key' is not an integer
		"""

		Misc.raise_ifn(isinstance(key, int), Exceptions.InvalidArgumentException(MySubTerminal.ungetch, 'key', type(key), (int,)))
		self.__event_queue__.append(int(key))

	def ungetgch(self, key: int) -> None:
		"""
		Appends a key to this terminal's global event queue
		:param key: The key code to append
		:raises InvalidArgumentException: If 'key' is not an integer
		"""

		Misc.raise_ifn(isinstance(key, int), Exceptions.InvalidArgumentException(MySubTerminal.ungetgch, 'key', type(key), (int,)))
		self.topmost_parent().ungetgch(key)

	def erase_refresh(self, flag: bool) -> None:
		"""
		:param flag: Whether this sub-terminal will fully erase the sub-terminal before the next draw
		"""

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

	def getch(self) -> typing.Optional[int]:
		"""
		Reads the next key code from this sub-terminal's event queue
		:return: The next key code or None if no event is waiting
		"""

		return self.__event_queue__.pop() if len(self.__event_queue__) else None

	def peekch(self) -> typing.Optional[int]:
		"""
		Peeks the next key code from this sub-terminal's event queue
		:return: The next key code or None if no event is waiting
		"""

		return self.__event_queue__[-1] if len(self.__event_queue__) else None

	def getgch(self) -> typing.Optional[int]:
		"""
		Reads the next key code from this terminal's global event queue
		:return: The next key code or None if no event is waiting
		"""

		return self.topmost_parent().getgch()

	def peekgch(self) -> typing.Optional[int]:
		"""
		Peeks the next key code from this terminal's global event queue
		:return: The next key code or None if no event is waiting
		"""

		return self.topmost_parent().peekgch()

	def scroll_speed(self, scroll: typing.Optional[int] = ...) -> typing.Optional[int]:
		"""
		Gets or sets the sub-terminal's scrolling speed in lines per scroll button
		If the mouse scrolls once, this sub-terminal will scroll 'scroll' lines
		:param scroll: The number of lines to scroll per scroll button press
		:return: The scroll speed if 'scroll' is unset otherwise None
		:raises InvalidArgumentException: If 'scroll' is not an integer
		"""

		if scroll is None or scroll is ...:
			return self.__auto_scroll__
		elif not isinstance(scroll, int):
			raise Exceptions.InvalidArgumentException(MySubTerminal.scroll_speed, 'scroll', type(scroll), (int,))
		else:
			self.__auto_scroll__ = int(scroll)

	def after(self, ticks: int, callback: typing.Callable, *args, __threaded: bool = True, **kwargs) -> int:
		"""
		Schedules a function to be executed after a certain number of ticks
		:param ticks: The number of terminal ticks to execute after
		:param callback: The callable callback
		:param args: The positional arguments to pass
		:param __threaded: Whether to use a threading.Thread
		:param kwargs: The keyword arguments to pass
		:return: The scheduled callback ID
		"""

		return self.__terminal__.after(ticks, callback, *args, __threaded=__threaded, **kwargs)

	def cursor(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> typing.Optional[tuple[int, int]]:
		"""
		Gets or sets the sub-terminal's current cursor position
		:param x: The new cursor x position
		:param y: The new cursor y position
		:return: The current cursor position if 'x' and 'y' are unset otherwise None
		"""

		if (x is None or x is ...) and (y is None or y is ...):
			return self.__cursor__[0], self.__cursor__[1]
		elif x is not None and x is not ... and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(MySubTerminal.cursor, 'x', type(x), (int,))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(MySubTerminal.cursor, 'y', type(y), (int,))
		else:
			cy, cx = self.__stdscr__.getyx()
			_, _, visibility, rate = self.__cursor__
			self.__cursor__ = (cx if x is None or x is ... else int(x), cy if y is None or y is ... else int(y), visibility, rate)

	def scroll(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> typing.Optional[tuple[int, int]]:
		"""
		Gets or sets the sub-terminal's current scroll offset
		:param x: The new scroll x offset
		:param y: The new scroll y offset
		:return: The current scroll offset if 'x' and 'y' are unset otherwise None
		"""

		if (x is None or x is ...) and (y is None or y is ...):
			x, y = self.__scroll__
			return x, y
		elif x is not None and x is not ... and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(MySubTerminal.scroll, 'x', type(x), (int,))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(MySubTerminal.scroll, 'y', type(y), (int,))
		else:
			self.__scroll__[0] = self.__scroll__[0] if x is None or x is ... else int(x)
			self.__scroll__[1] = self.__scroll__[1] if y is None or y is ... else int(y)

	def first_empty_row(self) -> int:
		"""
		:return: The first empty row
		"""

		my, mx = self.__stdscr__.getmaxyx()
		bg = self.__stdscr__.getbkgd()

		for y in range(0, my):
			line: bytes = self.__stdscr__.instr(y, 0, mx)

			if len(tuple(x for x in line if x != bg)) == 0:
				return y

		return -1

	def last_empty_row(self) -> int:
		"""
		:return: The last empty row
		"""

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
		"""
		:return: The first empty column
		"""

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
		"""
		:return: The last empty column
		"""

		my, mx = self.__stdscr__.getmaxyx()
		bg = self.__stdscr__.getbkgd()
		last_x: int = mx

		for x in range(mx - 1, -1, -1):
			for y in range(my):
				if self.__stdscr__.instr(y, x, 1)[0] != bg:
					return last_x

			last_x = x

		return -1

	def tab_size(self, size: typing.Optional[int] = ...) -> typing.Optional[int]:
		"""
		Gets or sets this sub-terminal's tab size
		Tab will equal the space character times this value
		:param size: The tab size in characters
		:return: The current tab size if 'size' is unset otherwise None
		:raises InvalidArgumentException: If 'size' is not an integer
		:raises ValueError: If 'size' is less than 0
		"""

		if size is None or size is ...:
			return self.__tab_size__
		elif not isinstance(size, int):
			raise Exceptions.InvalidArgumentException(MySubTerminal.tab_size, 'size', type(size), (int,))
		elif size < 0:
			raise ValueError('Tab size cannot be less than zero')
		else:
			self.__tab_size__ = int(size)

	def chat(self, x: int, y: int) -> tuple[int, int]:
		"""
		Gets the character and its format attribute at the specified position
		:param x: The x position
		:param y: The y position
		:return: The character and attribute
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		Misc.raise_ifn(isinstance(x, int), Exceptions.InvalidArgumentException(MySubTerminal.chat, 'x', type(x), (int,)))
		Misc.raise_ifn(isinstance(y, int), Exceptions.InvalidArgumentException(MySubTerminal.chat, 'y', type(y), (int,)))
		full: int = self.__stdscr__.inch(x, y)
		char: int = full & 0xFF
		attr: int = (full >> 8) & 0xFF
		return char, attr

	def to_fixed(self, x: int, y: int) -> tuple[int, int]:
		"""
		Converts the specified scroll independent coordinate into true sub-terminal coordinates
		An input of (0, 0) will always give the top-left corner regardless of scroll offset
		:param x: The scroll independent x coordinate
		:param y: The scroll independent y coordinate
		:return: The true adjusted coordinates
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		Misc.raise_ifn(isinstance(x, int), Exceptions.InvalidArgumentException(MySubTerminal.to_fixed, 'x', type(x), (int,)))
		Misc.raise_ifn(isinstance(y, int), Exceptions.InvalidArgumentException(MySubTerminal.to_fixed, 'y', type(y), (int,)))
		sx, sy = self.__scroll__
		return x + sx, y + sy

	def from_fixed(self, x: int, y: int) -> tuple[int, int]:
		"""
		Converts the specified true sub-terminal coordinate into scroll independent coordinates
		:param x: The true x coordinate
		:param y: The true y coordinate
		:return: The scroll independent coordinates
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		Misc.raise_ifn(isinstance(x, int), Exceptions.InvalidArgumentException(MySubTerminal.from_fixed, 'x', type(x), (int,)))
		Misc.raise_ifn(isinstance(y, int), Exceptions.InvalidArgumentException(MySubTerminal.from_fixed, 'y', type(y), (int,)))
		sx, sy = self.__scroll__
		return x - sx, y - sy

	def getline(self, replace_char: typing.Optional[str | Terminal.Struct.AnsiStr | Iterable.String] = ..., prompt: typing.Optional[str | Terminal.Struct.AnsiStr | Iterable.String] = '', x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> str:
		"""
		Pauses terminal execution and reads a line from the user
		For standard input without pausing, add an 'Entry' widget
		:param replace_char: The character to replace entered characters with (usefull for passwords or hidden entries)
		:param prompt: The prompt to display
		:param x: The x position to display at
		:param y: The y position to display at
		:return: The entered string
		:raises InvalidArgumentException: If 'replace_char' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'prompt' is not a string, AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises ValueError: If 'replace_char' is not a single character
		"""

		Misc.raise_ifn(replace_char is None or replace_char is ... or (isinstance(replace_char, (str, Terminal.Struct.AnsiStr, Iterable.String))), Exceptions.InvalidArgumentException(MySubTerminal.getline, 'replace_char', type(replace_char), (str, Iterable.String, Terminal.Struct.AnsiStr)))
		Misc.raise_ifn(replace_char is None or replace_char is ... or len(replace_char := str(replace_char)) == 1, ValueError('Replacement character must be a string of length 1'))
		Misc.raise_ifn(x is None or x is ... or isinstance(x, int), Exceptions.InvalidArgumentException(MySubTerminal.from_fixed, 'x', type(x), (int,)))
		Misc.raise_ifn(x is None or x is ... or isinstance(y, int), Exceptions.InvalidArgumentException(MySubTerminal.from_fixed, 'y', type(y), (int,)))
		Misc.raise_ifn(prompt is None or prompt is ... or (isinstance(prompt, (str, Iterable.String, Terminal.Struct.AnsiStr))), Exceptions.InvalidArgumentException(MySubTerminal.getline, 'prompt', type(prompt), (str, Iterable.String, Terminal.Struct.AnsiStr)))

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

	def get_topmost_child_at(self, x: int, y: int) -> typing.Optional[MyWidget]:
		"""
		Gets the topmost widget at the specified coordinates
		:param x: The x coordinate to check
		:param y: The y coordinate to check
		:return: The topmost widget or None if no widget exists
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		Misc.raise_ifn(isinstance(x, int), Exceptions.InvalidArgumentException(MySubTerminal.get_topmost_child_at, 'x', type(x), (int,)))
		Misc.raise_ifn(isinstance(y, int), Exceptions.InvalidArgumentException(MySubTerminal.get_topmost_child_at, 'y', type(y), (int,)))

		for z_index in sorted(self.__pages__.keys(), reverse=True):
			for _id, widget in self.__pages__[z_index].items():
				if not widget.hidden and widget.has_coord(x, y):
					return widget

		for z_index in sorted(self.__widgets__.keys(), reverse=True):
			for _id, widget in self.__widgets__[z_index].items():
				if not widget.hidden and widget.has_coord(x, y):
					return widget

		return None

	def get_focus(self) -> typing.Optional[MyWidget]:
		"""
		:return: The widget with focus or None if no widget has focus
		"""

		child: MyWidget

		for child in (*self.widgets(), *self.subterminals()):
			if child.focused:
				return child

		return None

	def active_subterminal(self) -> typing.Optional[MySubTerminal]:
		"""
		:return: The sub-terminal with focus or None if no sub-terminal is active
		"""

		page: MySubTerminal | None = self.__active_page__

		if page is None or page.hidden:
			return None

		while page.selected_subterminal is not None and not page.selected_subterminal.hidden:
			page = page.selected_subterminal

		return page

	def get_widget(self, _id: int) -> MyWidget:
		"""
		Gets the widget with the specified ID
		:param _id: The widget ID
		:return: The widget
		:raises InvalidArgumentException: If '_id' is not an integer
		:raises KeyError: If no widget with the specified ID exists
		"""

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(MySubTerminal.get_widget, '_id', type(_id), (int,)))

		for z_index, widgets in self.__widgets__.items():
			if _id in widgets:
				return widgets[_id]

		raise KeyError(f'No such widget - {_id}')

	def get_sub_terminal(self, _id: int) -> MySubTerminal:
		"""
		Gets the sub-terminal with the specified ID
		:param _id: The sub-terminal ID
		:return: The sub-terminal
		:raises InvalidArgumentException: If '_id' is not an integer
		:raises KeyError: If no sub-terminal with the specified ID exists
		"""

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(MySubTerminal.get_sub_terminal, '_id', type(_id), (int,)))

		for z_index, sub_terminals in self.__pages__.items():
			if _id in sub_terminals:
				return sub_terminals[_id]

		raise KeyError(f'No such widget - {_id}')

	def get_children_at(self, x: int, y: int) -> tuple[MyWidget, ...]:
		"""
		Gets all widgets or sub-terminals at the specified coordinates
		:param x: The x coordinate to check
		:param y: The y coordinate to check
		:return: All widgets or sub-terminals overlapping the specified coordinates
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		Misc.raise_ifn(isinstance(x, int), Exceptions.InvalidArgumentException(MySubTerminal.get_children_at, 'x', type(x), (int,)))
		Misc.raise_ifn(isinstance(y, int), Exceptions.InvalidArgumentException(MySubTerminal.get_children_at, 'y', type(y), (int,)))
		children: list[MyWidget] = []

		for z_index in sorted(self.__pages__.keys(), reverse=True):
			for _id, widget in self.__pages__[z_index].items():
				if widget.has_coord(x, y):
					children.append(widget)

		for z_index in sorted(self.__widgets__.keys(), reverse=True):
			for _id, widget in self.__widgets__[z_index].items():
				if widget.has_coord(x, y):
					children.append(widget)

		return tuple(children)

	def widgets(self) -> tuple[MyWidget, ...]:
		"""
		:return: All widgets in this sub-terminal
		"""

		ids: list[MyWidget] = []

		for alloc in self.__widgets__.values():
			ids.extend(alloc.values())

		return tuple(ids)

	def subterminals(self) -> tuple[MySubTerminal, ...]:
		"""
		:return: All sub-terminals in this sub-terminal
		"""

		ids: list[MySubTerminal] = []

		for alloc in self.__pages__.values():
			ids.extend(alloc.values())

		return tuple(ids)

	def children(self) -> dict[int, MyWidget]:
		"""
		:return: All widgets and sub-terminals in this sub-terminal
		"""

		children: dict[int, MyWidget] = {}

		for alloc in self.__pages__.values():
			children.update(alloc)

		for alloc in self.__widgets__.values():
			children.update(alloc)

		return children

	### Widget methods
	def add_button(self, x: int, y: int, width: int, height: int, text: str | Terminal.Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_NONE,
				   border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				   color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MyButton:
		"""
		Adds a new button widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param text: Display text
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The button widget
		"""

		widget: MyButton = MyButton(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
													border=border, highlight_border=highlight_border, active_border=active_border,
													color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
													callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_toggle_button(self, x: int, y: int, width: int, height: int, text: str | Terminal.Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_NONE,
						  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
						  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
						  callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MyToggleButton:
		"""
		Adds a new toggle button widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param text: Display text
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The button widget
		"""

		widget: MyToggleButton = MyToggleButton(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
																border=border, highlight_border=highlight_border, active_border=active_border,
																color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str | Terminal.Struct.AnsiStr | Iterable.String = '', active_text: str | Terminal.Struct.AnsiStr | Iterable.String = 'X',
					 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_checked: typing.Optional[typing.Callable[[[MyWidget], bool], None]] = ...) -> MyCheckbox:
		"""
		Adds a new checkbox button widget to this terminal
		:param x: X position
		:param y: Y position
		:param text: Text to display when checkbox is unchecked
		:param active_text: Text to display when checkbox is checked
		:param z_index: Z-index, higher is drawn last
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:param on_checked: The callback to call when the checkbox's checked state changes this widget and the widget's current state as arguments
		:return: The checkbox button widget
		"""

		widget: MyCheckbox = MyCheckbox(self, x, y, z_index=z_index, text=text, active_text=active_text,
														border=border, highlight_border=highlight_border, active_border=active_border,
														color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
														callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close, on_checked=on_checked)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_inline_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str | Terminal.Struct.AnsiStr | Iterable.String = '', active_text: str | Terminal.Struct.AnsiStr | Iterable.String = 'X',
							border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
							color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
							callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_checked: typing.Optional[typing.Callable[[[MyWidget], bool], None]] = ...) -> MyInlineCheckbox:
		"""
		Adds a new inline checkbox button widget to this terminal
		:param x: X position
		:param y: Y position
		:param text: Text to display when checkbox is unchecked
		:param active_text: Text to display when checkbox is checked
		:param z_index: Z-index, higher is drawn last
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:param on_checked: The callback to call when the checkbox's checked state changes this widget and the widget's current state as arguments
		:return: The checkbox button widget
		"""
		
		widget: MyInlineCheckbox = MyInlineCheckbox(self, x, y, z_index=z_index, text=text, active_text=active_text,
																	border=border, highlight_border=highlight_border, active_border=active_border,
																	color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																	callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close, on_checked=on_checked)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_radial_spinner(self, x: int, y: int, *, z_index: int = 0, phases: typing.Iterable[str | Terminal.Struct.AnsiStr | Iterable.String] = ('--', '\\', '|', '/'), bg_phase_colors: typing.Optional[Terminal.Enums.Color_T] | typing.Iterable[typing.Optional[Terminal.Enums.Color_T]] = ..., fg_phase_colors: typing.Optional[Terminal.Enums.Color_T] | typing.Iterable[typing.Optional[Terminal.Enums.Color_T]] = Terminal.Struct.Color(0xFFFFFF),
						   callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MyRadialSpinner:
		"""
		Adds a new radial spinner widget to this terminal
		:param x: X position
		:param y: Y position
		:param z_index: Z-index, higher is drawn last
		:param phases: The individual frames to display
		:param bg_phase_colors: The background colors to cycle through when ticking
		:param fg_phase_colors: The foreground colors to cycle through when ticking
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The radial spinner widget
		"""

		widget: MyRadialSpinner = MyRadialSpinner(self, x, y, z_index=z_index, phases=phases, bg_phase_colors=bg_phase_colors, fg_phase_colors=fg_phase_colors,
																  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_horizontal_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, step: float = 1, fill_char: str | Terminal.Struct.AnsiStr | Iterable.String = '|', _max: float = 10, _min: float = 0, on_input: typing.Callable[[MyHorizontalSlider], None] = ...,
							  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
							  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
							  callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MyHorizontalSlider:
		"""
		Adds a new horizontal slider widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param z_index: Z-index, higher is drawn last
		:param step: The amount to increment by per scroll
		:param fill_char: The character to use to show value
		:param _max: The maximum value of this slider
		:param _min: The minimum value of this slider
		:param on_input: The callback to call once the mouse enters this widget taking this widget as an argument
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The horizontal slider widget
		"""

		widget: MyHorizontalSlider = MyHorizontalSlider(self, x, y, width, height, z_index=z_index, step=step, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
																		border=border, highlight_border=highlight_border, active_border=active_border,
																		color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																		callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_vertical_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Terminal.Struct.AnsiStr | Iterable.String = '=', _max: float = 10, _min: float = 0, on_input: typing.Callable[[MyVerticalSlider], None] = ...,
							border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
							color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
							callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MyVerticalSlider:
		"""
		Adds a new vertical slider widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param z_index: Z-index, higher is drawn last
		:param fill_char: The character to use to show value
		:param _max: The maximum value of this slider
		:param _min: The minimum value of this slider
		:param on_input: The callback to call once the mouse enters this widget taking this widget as an argument
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The vertical slider widget
		"""

		widget: MyVerticalSlider = MyVerticalSlider(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
																	border=border, highlight_border=highlight_border, active_border=active_border,
																	color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																	callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_horizontal_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Terminal.Struct.AnsiStr | Iterable.String = '|', _max: float = 10, _min: float = 0,
									border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
									color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
									callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MyHorizontalProgressBar:
		"""
		Adds a new horizontal progress bar widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param z_index: Z-index, higher is drawn last
		:param fill_char: The character to use to show value
		:param _max: The maximum value of this slider
		:param _min: The minimum value of this slider
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The horizontal progress bar widget
		"""

		widget: MyHorizontalProgressBar = MyHorizontalProgressBar(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
																				  border=border, highlight_border=highlight_border, active_border=active_border,
																				  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																				  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_vertical_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Terminal.Struct.AnsiStr | Iterable.String = '=', _max: float = 10, _min: float = 0,
								  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
								  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
								  callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MyVerticalProgressBar:
		"""
		Adds a new vertical progress bar widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param z_index: Z-index, higher is drawn last
		:param fill_char: The character to use to show value
		:param _max: The maximum value of this slider
		:param _min: The minimum value of this slider
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The vertical progress bar widget
		"""

		widget: MyVerticalProgressBar = MyVerticalProgressBar(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
																			  border=border, highlight_border=highlight_border, active_border=active_border,
																			  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																			  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_text(self, x: int, y: int, width: int, height: int, text: str | Terminal.Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Terminal.Enums.NORTH_WEST, word_wrap: int = Terminal.Enums.WORDWRAP_NONE,
				 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MyText:
		"""
		Adds a new text widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param text: Display text
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The text widget
		"""

		widget: MyText = MyText(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
												color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_dropdown(self, x: int, y: int, width: int, height: int, choices: tuple[str | Terminal.Struct.AnsiStr | Iterable.String, ...], *, display_count: int | None = None, allow_scroll_rollover: bool = False, z_index: int = 0, justify: int = Terminal.Enums.CENTER, word_wrap: int = Terminal.Enums.WORDWRAP_WORD, on_select: typing.Optional[typing.Callable[[[MyWidget]], bool | None]] = ...,
					 border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
					 color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MyDropdown:
		"""
		Adds a new dropdown widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param choices: The choices to display
		:param display_count: The number of choices to display at a time
		:param allow_scroll_rollover: Whether scrolling can cycle (too far down will cycle back to first option and vise versa)
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param on_select: The callback to call once a choice is selected taking this widget and whether the choice was scrolled to (False) or clicked (True) as arguments and returning a boolean indicating whether to keep the selection
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The dropdown widget
		"""

		widget: MyDropdown = MyDropdown(self, x, y, width, height, choices, display_count=display_count, allow_scroll_rollover=allow_scroll_rollover, z_index=z_index, justify=justify, word_wrap=word_wrap, on_select=on_select,
														border=border, highlight_border=highlight_border, active_border=active_border,
														color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
														callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_entry(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, word_wrap: int = Terminal.Enums.WORDWRAP_WORD, justify: int = Terminal.Enums.NORTH_WEST, replace_chars: str | Terminal.Struct.AnsiStr | Iterable.String = '', placeholder: typing.Optional[str | Terminal.Struct.AnsiStr | Iterable.String] = ..., cursor_blink_speed: int = 0, on_text: typing.Optional[typing.Callable[[MyEntry, bool], bool | str | Terminal.Struct.AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[MyEntry, str | Terminal.Struct.AnsiStr, int], bool | str | Terminal.Struct.AnsiStr | None]] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_fg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MyEntry:
		"""
		Adds a new entry widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the WORDWRAP_ enums)
		:param replace_chars: The character to replace entered characters with (visual only; for things like passwords)
		:param placeholder: The placeholder text to show when widget is empty
		:param cursor_blink_speed:
		:param on_text: The callback to call once the 'enter' is pressed taking this widget and whether text should be kept and returning either a boolean indicating whether to keep the modified text or a string to replace the accepted text
		:param on_input: The callback to call when a user enters any character taking this widget, the character entered, and the characters position in the string or -1 if at the end
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The entry widget
		"""

		widget: MyEntry = MyEntry(self, x, y, width, height, z_index=z_index, word_wrap=word_wrap, justify=justify, replace_chars=replace_chars, placeholder=placeholder, cursor_blink_speed=cursor_blink_speed, on_text=on_text, on_input=on_input,
								  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
								  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_image(self, x: int, y: int, width: int, height: int, image: str | Terminal.Struct.AnsiStr | Iterable.String | numpy.ndarray | PIL.Image.Image, *, z_index: int = 0, use_subpad: bool = True, div: typing.Optional[int] = ...,
				  border: typing.Optional[Terminal.Struct.BorderInfo] = ..., highlight_border: typing.Optional[Terminal.Struct.BorderInfo] = ..., active_border: typing.Optional[Terminal.Struct.BorderInfo] = ...,
				  color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Terminal.Enums.Color_T] = ..., active_color_bg: typing.Optional[Terminal.Enums.Color_T] = ...,
				  callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MyImage:
		"""
		Adds a new image widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param image: The image filepath, numpy image array, or PIL image to display
		:param z_index: Z-index, higher is drawn last
		:param use_subpad: Whether to use a curses sub-pad instead of drawing to the main display (may improve performance for larger images)
		:param div: The color division ratio (bit depth) of the image. Set to a higher value for terminals with lower available color spaces
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param color_bg: The background color
		:param highlight_color_bg: The background color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The image widget
		"""

		widget: MyImage = MyImage(self, x, y, width, height, image, z_index=z_index, div=div, use_subpad=use_subpad,
								  border=border, highlight_border=highlight_border, active_border=active_border,
								  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
								  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_sub_terminal(self, x: int, y: int, width: int, height: int, *, title: typing.Optional[str | Terminal.Struct.AnsiStr | Iterable.String] = ..., z_index: int = 0, transparent: bool = False,
						 border: Terminal.Struct.BorderInfo = ..., highlight_border: Terminal.Struct.BorderInfo = ..., active_border: Terminal.Struct.BorderInfo = ...,
						 callback: typing.Optional[typing.Callable[[[MyWidget], str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[MyWidget]], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[MyWidget], Terminal.Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[[MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[MyWidget]], None]] = ...) -> MySubTerminal:
		"""
		Adds a new sub-terminal to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param title: Display title
		:param z_index: Z-index, higher is drawn last
		:param transparent: Whether to display the contents this sub-terminal will overlap
		:param border: The border to display
		:param highlight_border: The border to display when mouse is hovering
		:param active_border: The border to display when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The sub-terminal
		"""

		terminal: MySubTerminal = MySubTerminal(self, x, y, width, height, title, z_index=z_index, transparent=transparent,
												border=border, highlight_border=highlight_border, active_border=active_border,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(terminal)

		if z_index in self.__pages__:
			self.__pages__[z_index][_id] = terminal
		else:
			self.__pages__[z_index] = {_id: terminal}

		return terminal

	def add_widget[T: MyWidget](self, cls: type[T], *args, z_index: int = 0, **kwargs) -> T:
		"""
		Adds a new widget to this terminal
		This is for use with custom widget classes extending from the Widget class
		:param cls: The widget class to instantiate
		:param args: The positional arguments to pass into the constructor
		:param z_index: Z-index, higher is drawn last
		:param kwargs: The keyword arguments to pass into the constructor
		:return: The new widget
		"""

		assert issubclass(cls, MyWidget)
		widget: MyWidget = cls(self, *args, **kwargs)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	### Properties
	@property
	def screen(self) -> _curses.window:
		"""
		:return: The underlying curses window
		"""

		return self.__stdscr__

	@property
	def enabled(self) -> bool:
		"""
		:return: Whether the terminal is active
		"""

		return self.__terminal__.enabled

	@property
	def exit_code(self) -> typing.Optional[int]:
		"""
		:return: This terminal's exit code or None if still active
		"""

		return self.__terminal__.exit_code

	@property
	def current_tick(self) -> int:
		"""
		:return: This terminal's current tick
		"""

		return self.__terminal__.current_tick

	@property
	def mouse(self) -> Terminal.Struct.MouseInfo:
		"""
		:return: The mouse info holding the last mouse event this sub-terminal received
		"""

		return self.__last_mouse_info__

	@property
	def transparent(self) -> bool:
		"""
		:return: Whether to display the contents this sub-terminal will overlap
		"""

		return self.__transparent__

	@transparent.setter
	def transparent(self, transparent: bool) -> None:
		"""
		Sets whether to display the contents this sub-terminal will overlap
		:param transparent: Transparency
		"""

		self.__transparent__ = bool(transparent)

	@property
	def title(self) -> str:
		"""
		:return: This sub-terminal's title
		"""

		return self.__title__

	@title.setter
	def title(self, title: str | Terminal.Struct.AnsiStr | Iterable.String) -> None:
		"""
		Sets this sub-terminal's title
		:param title: The new title
		:raises InvalidArgumentException: If 'title' is not a string, AnsiStr instance, or String instance
		"""

		Misc.raise_ifn(isinstance(title, (str, Terminal.Struct.AnsiStr, Iterable.String)), Exceptions.InvalidArgumentException(MySubTerminal.title.setter, 'title', type(title), (str, Terminal.Struct.AnsiStr, Iterable.String)))
		self.__title__ = str(title) if isinstance(title, (str, Iterable.String)) else title.raw if isinstance(title, Terminal.Struct.AnsiStr) else ''

	@property
	def selected_subterminal(self) -> typing.Optional[MySubTerminal]:
		"""
		:return: The current focused sub-terminal or None if no sub-terminal is active
		"""

		return self.__active_page__

	@property
	def default_bg(self) -> Terminal.Struct.Color:
		"""
		:return: The default terminal background color
		"""

		return Terminal.Struct.Color.fromcursesrgb(*curses.color_content(0))

	@property
	def default_fg(self) -> Terminal.Struct.Color:
		"""
		:return: The default terminal foreground color
		"""

		return Terminal.Struct.Color.fromcursesrgb(*curses.color_content(7))

	@property
	def __serializer__(self) -> type[MyWidget.MySerializedWidget]:
		return MySubTerminal.MySerializedSubTerminal
