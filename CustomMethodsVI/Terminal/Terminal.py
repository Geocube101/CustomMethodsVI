from __future__ import annotations

import base64
import curses
import _curses
import curses.ascii
import datetime
import locale
import math
import numpy
import os
import pickle
import PIL.Image
import psutil
import pyautogui
import queue
import signal
import subprocess
import sys
import threading
import time
import traceback
import types
import typing

if os.name == 'nt':
	import ctypes
	import ctypes.wintypes

	import pywintypes

	import win32con
	import win32gui
	import win32console

from .. import Concurrent
from .. import Connection
from . import Enums
from .. import Exceptions
from .. import Iterable
from .. import Misc
from . import Struct
from . import Widgets


class Terminal:
	"""
	Class holding all functionality for a curses terminal
	Widgets may be added to this terminal
	"""

	class ScheduledCallback:
		"""
		Class representing a schedulable callback
		"""

		def __init__(self, ticks: int, threaded: bool, callback: typing.Callable, args: tuple[typing.Any, ...], kwargs: dict[str, typing.Any]):
			"""
			Class representing a schedulable callback
			- Constructor -
			:param ticks: The number of terminal ticks to wait
			:param threaded: Whether to run this callback in a separate threading.Thread
			:param callback: The callback to call
			:param args: The callback positional arguments
			:param kwargs: The callback keyword arguments
			"""

			assert isinstance(ticks, int) and (ticks := int(ticks)) >= 0, 'Ticks remaining must be greater than or equal to zero'
			assert callable(callback), 'Callback must be callable'

			self.ticks: int = int(ticks)
			self.threaded: bool = bool(threaded)
			self.callback: typing.Callable = callback
			self.args: tuple[typing.Any, ...] = args
			self.kwargs: dict[str, typing.Any] = kwargs

	### Magic methods
	def __init__(self, width: typing.Optional[int] = ..., height: typing.Optional[int] = ..., font: typing.Optional[Struct.Font] = ...):
		"""
		Class holding all functionality for a curses terminal
		Widgets may be added to this terminal
		- Constructor -
		:param width: The terminal's width in characters
		:param height: The terminal's height in characters
		:param font: The terminal's font
		"""

		if os.name == 'nt':
			os.system('chcp 65001')
			kernel32 = ctypes.WinDLL('Kernel32.dll')
			stdout = kernel32.GetStdHandle(-11)

			if not stdout:
				raise RuntimeError('Failed to get STDOUT handle')

			old_font: Struct.FontInfoEx = Struct.FontInfoEx()
			old_font.cbSize = ctypes.sizeof(Struct.FontInfoEx)
			res = kernel32.GetCurrentConsoleFontEx(stdout, False, ctypes.byref(old_font))

			if not res:
				raise RuntimeError('Failed to get font info')

			if font is not None and font is not ...:
				self.font(font)

			self.__old_font__: tuple[str, int, int, int, int] = (old_font.FaceName, old_font.dwFontSize.X, old_font.dwFontSize.Y, old_font.nFont, old_font.FontWeight)
		else:
			self.__old_font__: tuple[str, int, int, int, int] = ('Consolas', 4, 8, 0, 400)

		self.__widgets__: dict[int, dict[int, Widgets.MyWidget]] = {}
		self.__pages__: dict[int, dict[int, Widgets.MySubTerminal]] = {}
		self.__windows__: dict[int, WindowTerminal] = {}
		self.__scheduled_callables__: dict[int, Terminal.ScheduledCallback] = {}
		self.__workers__: list[tuple[threading.Thread, threading.Event]] = []
		self.__worker_queue__: queue.Queue = queue.Queue()
		self.__previous_inputs__: list[str] = []
		self.__touched_cols_rows__: list[int] = [0, 0, 0, 0]

		self.__mouse_pos__: tuple[int, int] = (-1, -1)
		self.__screen_mouse_pos__: tuple[int, int] = (0, 0)
		self.__cursor__: tuple[int, int, int, int] = (0, 0, 0, 0)
		self.__enabled__: typing.Optional[int] = -1
		self.__full_end__: typing.Optional[int] = None
		self.__exit_reason__: typing.Optional[BaseException] = None
		self.__fullscreen__: bool = False
		self.__iconified__: bool = False
		self.__erase_refresh__: bool = True
		self.__root__ = curses.initscr()
		self.__scroll__: list[int] = [0, 0]
		self.__last_mouse_info__: Struct.MouseInfo = Struct.MouseInfo(-1, 0, 0, 0, 0)
		self.__event_queue__: Iterable.SpinQueue[int] = Iterable.SpinQueue(10)
		self.__global_event_queue__: Iterable.SpinQueue[int] = Iterable.SpinQueue(10)
		self.__colors__: dict[int, int] = {}
		self.__color_usage__: dict[int, int] = {}
		self.__color_times__: dict[int, float] = {}
		self.__color_pairs__: dict[tuple[int, int], int] = {}
		self.__color_pair_usage__: dict[int, int] = {}
		self.__color_pair_times__: dict[int, float] = {}
		self.__max_workers__: int = 10
		self.__update_times__: Iterable.SpinQueue[tuple[float, float]] = Iterable.SpinQueue(50)
		self.__tick__: int = 0
		self.__auto_scroll__: int = 10
		self.__tab_size__: int = 4
		self.__active_page__: typing.Optional[Widgets.MySubTerminal] = None
		self.__update_type__: int = Enums.WINUPDATE_ALL
		self.__on_exit__: typing.Callable = lambda *_: self.__finalize__()

		curses.cbreak()
		curses.noecho()
		curses.start_color()
		curses.use_default_colors()
		curses.curs_set(0)
		curses.mousemask(curses.REPORT_MOUSE_POSITION | curses.ALL_MOUSE_EVENTS)
		curses.mouseinterval(0)

		h, w = self.__root__.getmaxyx()
		w = int(width) if isinstance(width, int) else w
		h = int(height) if isinstance(height, int) else h
		curses.resize_term(h, w)

		self.__highest_default_color__: int = min(256, curses.COLORS)
		self.__highest_color_pair__: int = curses.COLOR_PAIRS

		for i in range(self.__highest_default_color__):
			try:
				r, g, b = curses.color_content(i)
				color: Struct.Color = Struct.Color.fromcursesrgb(r, g, b)

				if color not in self.__colors__:
					self.__colors__[color.color] = i
			except _curses.error:
				self.__highest_default_color__ = i
				break

		for i in range(curses.COLOR_PAIRS):
			fg, bg = curses.pair_content(i)

			if fg < 0 or bg < 0:
				continue

			try:
				r, g, b = curses.color_content(fg)
				color: Struct.Color = Struct.Color.fromcursesrgb(r, g, b)

				if color.color not in self.__colors__:
					self.__colors__[color.color] = fg

				r, g, b = curses.color_content(bg)
				color: Struct.Color = Struct.Color.fromcursesrgb(r, g, b)

				if color.color not in self.__colors__:
					self.__colors__[color.color] = bg
			except _curses.error:
				self.__highest_color_pair__ = i

		self.__root__.keypad(True)
		self.__root__.idlok(True)
		self.__root__.idcok(True)
		self.__root__.nodelay(True)
		self.__root__.immedok(False)
		self.__root__.leaveok(False)
		self.__root__.scrollok(False)

	def __del__(self):
		if self.__enabled__:
			self.end(-1)

	### Internal methods
	def __worker__(self, complete: threading.Event) -> None:
		"""
		INTERNAL METHOD
		:param complete: An event marking whether this worker is working
		"""

		try:
			while True:
				struct: Terminal.ScheduledCallback = self.__worker_queue__.get(False)
				complete.clear()
				struct.callback(*struct.args, **struct.kwargs)
		except queue.Empty:
			pass
		finally:
			complete.set()

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
			y, x = self.__root__.getyx()
			sx, sy = self.__scroll__
			return x + sx, y + sy
		elif x is not None and x is not ... and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(Terminal.__move__, 'x', type(x), ('int',))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(Terminal.__move__, 'y', type(y), ('int',))
		else:
			cy, cx = self.__root__.getyx()
			my, mx = self.__root__.getmaxyx()
			sx, sy = self.__scroll__
			new_x: int = (cx if x is None or x is ... else int(x)) - sx
			new_y: int = (cy if y is None or y is ... else int(y)) - sy

			if 0 <= new_y < my and 0 <= new_x < mx:
				self.__root__.move(new_y, new_x)
				return True
			else:
				return False

	def __mainloop__(self, tick_rate: float, factor: float, rollover: int, before_draw: typing.Callable[[Terminal], int], after_draw: typing.Callable[[Terminal], int]) -> None:
		"""
		INTERNAL METHOD
		Mainloop for this terminal
		:param tick_rate: The rate at which this terminal ticks in seconds
		:param factor: A multiplier for sleep used to counteract slower runtimes
		:param rollover: Value at which the internal tick counter will reset
		:param before_draw: Callback to call every tick before terminal is drawn
		:param after_draw: Callback to call every tick after terminal is drawn
		"""

		this_win = win32console.GetConsoleWindow() if os.name == 'nt' else None
		foreground = win32gui.GetForegroundWindow() if os.name == 'nt' else None
		t1: int = time.perf_counter_ns()
		do_update: bool = True
		self.update_execute_pending_callbacks()
		self.update_key_events()

		if this_win == foreground:
			self.__iconified__ = False

		if (self.__update_type__ & Enums.WINUPDATE_FOCUS) != 0:
			do_update = do_update and this_win == foreground
		if (self.__update_type__ & Enums.WINUPDATE_MOUSEIN) != 0:
			cx, cy = self.__screen_mouse_pos__
			sx, sy = self.__scroll__
			my, mx = self.__root__.getmaxyx()
			do_update = do_update and 0 <= cx - sx < mx and 0 <= cy - sy < my

		if not do_update:
			time.sleep(tick_rate)
			return

		if self.__erase_refresh__:
			self.__root__.erase()

		result_1: int = before_draw(self) if callable(before_draw) else None

		for z_index in sorted(self.__widgets__.keys()):
			closed: list[int] = []

			for widget in tuple(self.__widgets__[z_index].values()):
				if widget.closed:
					closed.append(widget.id)

			for close in closed:
				del self.__widgets__[z_index][close]

		for z_index in sorted(self.__pages__.keys()):
			closed: list[int] = []

			for page in tuple(self.__pages__[z_index].values()):
				if page.closed:
					closed.append(page.id)

			for close in closed:
				del self.__pages__[z_index][close]

		for z_index in sorted(self.__widgets__.keys()):
			for widget in tuple(self.__widgets__[z_index].values()):
				if not widget.hidden:
					widget.draw()

		result_2: int = after_draw(self) if callable(after_draw) else None

		for z_index in sorted(self.__pages__.keys()):
			for sub_terminal in tuple(self.__pages__[z_index].values()):
				if not sub_terminal.hidden:
					sub_terminal.update()

		# Update cursor
		cursor_x, cursor_y, visibility, flash_rate = self.__cursor__
		self.__root__.move(cursor_y, cursor_x)
		curses.curs_set(0 if visibility == 0 else visibility if flash_rate <= 0 else (visibility if self.__tick__ % (flash_rate * 2) > flash_rate else 0))

		# Close closed windows
		closed_windows: tuple[int, ...] = tuple(_id for _id, window in self.__windows__.items() if window.closed)

		for closed_window in closed_windows:
			if self.__windows__[closed_window].remote_exit_reason is not None:
				raise IOError(f'An error occurred in an external terminal window - {closed_window}') from self.__windows__[closed_window].remote_exit_reason

			self.__windows__[closed_window].close()
			del self.__windows__[closed_window]

		# Close closed workers
		closed: typing.Generator[tuple[threading.Thread, threading.Event]] = (x for x in self.__workers__ if not x[0].is_alive())

		for close in closed:
			self.__workers__.remove(close)

		# Refresh screen
		for i in range(len(self.__touched_cols_rows__)):
			self.__touched_cols_rows__[i] = 0

		self.__root__.refresh()

		# Handle exit
		if (isinstance(result_1, bool) and not bool(result_1)) or (isinstance(result_2, bool) and not bool(result_2)):
			self.__enabled__ = 0
		elif isinstance(result_1, int):
			self.__enabled__ = int(result_1)
		elif isinstance(result_2, int):
			self.__enabled__ = int(result_2)

		t2: int = time.perf_counter_ns()
		delta: float = (t2 - t1) * 1e-9
		remaining: float = tick_rate - delta
		self.__update_times__.append((delta, remaining))
		self.__tick__ = 0 if self.__tick__ >= rollover else self.__tick__ + 1

		if remaining > 0:
			time.sleep(remaining * factor)

	def __finalize__(self) -> int:
		"""
		INTERNAL METHOD
		Cleans-up terminal resources
		:return: The terminal stop code
		"""

		for z_index, widgets in self.__widgets__.items():
			for wid, widget in tuple(widgets.items()):
				if wid in widgets:
					widget.close()

		for _id, window in self.__windows__.items():
			if not window.closed and os.name == 'nt':
				try:
					window.end(self.__enabled__)
				except pywintypes.error:
					pass
			elif not window.closed:
				try:
					window.end(self.__enabled__)
				except Exception:
					pass

		curses.endwin()

		if os.name == 'nt':
			kernel32 = ctypes.WinDLL("Kernel32.dll")
			stdout = kernel32.GetStdHandle(-11)

			if not stdout:
				return -2

			font: Struct.FontInfoEx = Struct.FontInfoEx()
			font.cbSize = ctypes.sizeof(Struct.FontInfoEx)
			font.FaceName = self.__old_font__[0]
			font.dwFontSize.X = self.__old_font__[1]
			font.dwFontSize.Y = self.__old_font__[2]
			font.nFont = self.__old_font__[3]
			font.FontWeight = self.__old_font__[4]
			res = kernel32.SetCurrentConsoleFontEx(stdout, False, ctypes.byref(font))
		else:
			res = True

		self.__enabled__ = 0 if self.__enabled__ is None else self.__enabled__
		self.__full_end__ = self.__enabled__ if res else -2
		return self.__full_end__

	def __current_linux_window__(self) -> int:
		"""
		:return: The current window ID if on linux or macOS
		:raises OSError: If 'xprop' or 'wmctrl' is not installed
		"""

		if os.name == 'nt':
			raise ValueError('Unsupported OS')

		try:
			result: subprocess.CompletedProcess[str] = subprocess.run(['wmctrl', '-p', '-l'], capture_output=True, text=True, check=True, shell=True)

			for line in result.stdout.splitlines():
				try:
					wid, tid, pid, *_ = tuple(s.strip() for s in line.split(' '))
					win_id: int = int(wid, 16)
					prc_id: int = int(pid, 10)

					if prc_id == os.getpid():
						return win_id
				except (IndexError, ValueError):
					continue

			return self.__active_linux_window__()
		except FileNotFoundError:
			raise OSError('\'xprop\' and \'wmctrl\' may not be installed')

	def __active_linux_window__(self) -> int:
		"""
		:return: The active window ID if on linux or macOS
		:raises OSError: If 'xprop' or 'wmctrl' is not installed
		"""

		if os.name == 'nt':
			raise ValueError('Unsupported OS')

		try:
			result = subprocess.run(['xprop', '-root', '_NET_ACTIVE_WINDOW'], capture_output=True, text=True, check=True, shell=True)
			return int(result.stdout.split(' ')[-1], 16)
		except FileNotFoundError:
			raise OSError('\'xprop\' and \'wmctrl\' may not be installed')

	def update_key_events(self) -> None:
		"""
		INTERNAL METHOD
		Updates key press and mouse move events internally
		"""

		ch: int = self.__root__.getch()
		active: Widgets.MySubTerminal = ...

		if ch == curses.KEY_MOUSE:
			lx, ly, lz = self.__last_mouse_info__.position
			_id, _, _, _, bstate = curses.getmouse()
			self.__last_mouse_info__ = Struct.MouseInfo(_id, lx, ly, lz, bstate)
			topmost: Widgets.MyWidget = self.get_topmost_child_at(lx, ly)

			if topmost is not None:
				topmost.focus()

			if self.__last_mouse_info__.left_pressed or self.__last_mouse_info__.middle_pressed or self.__last_mouse_info__.right_pressed:
				if isinstance(topmost, Widgets.MySubTerminal):
					mx, my = self.__mouse_pos__
					self.__active_page__ = topmost
					self.__active_page__.__on_focus__(mx - self.__active_page__.x, my - self.__active_page__.y)
					self.__active_page__.focus()
				elif self.__active_page__ is not None:
					self.__active_page__.unfocus()
					self.__active_page__ = None

			if self.__last_mouse_info__.scroll_up_pressed and topmost is None:
				self.__scroll__[1] -= self.__auto_scroll__
			elif self.__last_mouse_info__.scroll_down_pressed and topmost is None:
				self.__scroll__[1] += self.__auto_scroll__

			return

		elif ch == curses.KEY_RESIZE:
			curses.curs_set(0)
		elif ch != -1:
			if (active := self.active_subterminal()) is None:
				self.__event_queue__.append(ch)
			else:
				active.__event_queue__.append(ch)

			self.__global_event_queue__.append(ch)

		old_bstate: int = self.__last_mouse_info__.bstate
		old_bstate &= ~(curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED | curses.BUTTON1_TRIPLE_CLICKED)
		old_bstate &= ~(curses.BUTTON2_CLICKED | curses.BUTTON2_DOUBLE_CLICKED | curses.BUTTON2_TRIPLE_CLICKED)
		old_bstate &= ~(curses.BUTTON3_CLICKED | curses.BUTTON3_DOUBLE_CLICKED | curses.BUTTON3_TRIPLE_CLICKED)
		old_bstate &= ~(curses.BUTTON4_CLICKED | curses.BUTTON4_DOUBLE_CLICKED | curses.BUTTON4_TRIPLE_CLICKED)
		old_bstate &= ~(curses.BUTTON5_CLICKED | curses.BUTTON5_DOUBLE_CLICKED | curses.BUTTON5_TRIPLE_CLICKED)

		if old_bstate & curses.BUTTON4_PRESSED != 0:
			old_bstate &= ~curses.BUTTON4_PRESSED
		if old_bstate & curses.BUTTON5_PRESSED != 0:
			old_bstate &= ~curses.BUTTON5_PRESSED

		if old_bstate & curses.BUTTON1_RELEASED != 0:
			old_bstate &= ~curses.BUTTON1_RELEASED
		if old_bstate & curses.BUTTON2_RELEASED != 0:
			old_bstate &= ~curses.BUTTON2_RELEASED
		if old_bstate & curses.BUTTON3_RELEASED != 0:
			old_bstate &= ~curses.BUTTON3_RELEASED

		if os.name != 'nt':
			return

		hwnd: int = win32console.GetConsoleWindow()
		wl, wt, wr, wb = win32gui.GetWindowRect(hwnd)
		cl, ct, cr, cb = win32gui.GetClientRect(hwnd)
		window_offset: int = math.floor(((wr - wl) - cr) / 2)
		title_offset: int = ((wb - wt) - cb) - window_offset
		wl, wt, wr, wb = (wl + window_offset, wt + title_offset, wr - window_offset, wb - window_offset)
		w: int = cr - cl
		h: int = cb - ct
		lh, lw = self.__root__.getmaxyx()

		if lw == 0 or lh == 0 or w == 0 or h == 0:
			return

		pw: float = w / lw
		ph: float = h / lh
		x, y = pyautogui.position()
		sx, sy = self.__scroll__
		tx: int = math.floor((x - wl) / pw) + sx
		ty: int = math.floor((y - wt) / ph) + sy
		self.__screen_mouse_pos__ = (tx, ty)

		if wl <= x <= wr and wt <= y <= wb and self.__screen_mouse_pos__ != self.__mouse_pos__:
			self.__mouse_pos__ = self.__screen_mouse_pos__
			self.__last_mouse_info__ = Struct.MouseInfo(self.__last_mouse_info__.mouse_id, self.__mouse_pos__[0], self.__mouse_pos__[1], 0, old_bstate)
			return

		if old_bstate != self.__last_mouse_info__.bstate:
			_id, x, y, z, _ = self.__last_mouse_info__
			self.__last_mouse_info__ = Struct.MouseInfo(_id, x, y, z, old_bstate)

	def update_execute_pending_callbacks(self) -> None:
		"""
		INTERNAL METHOD
		Updates and executes pending and scheduled callbacks
		"""

		execute: dict[int, Terminal.ScheduledCallback] = {}

		for _id, struct in self.__scheduled_callables__.items():
			if struct.ticks <= 0:
				execute[_id] = struct
			else:
				struct.ticks -= 1

		for _id, callback in execute.items():
			del self.__scheduled_callables__[_id]
			closed: typing.Generator[tuple[threading.Thread, threading.Event]] = (x for x in self.__workers__ if not x[0].is_alive())

			for close in closed:
				self.__workers__.remove(close)

			if callback.threaded:
				self.__worker_queue__.put(callback)

				if len(self.__workers__) == 0 or (all(w_complete.is_set() for w_thread, w_complete in self.__workers__) and len(self.__workers__) < self.__max_workers__):
					w_complete: threading.Event = threading.Event()
					worker: threading.Thread = threading.Thread(target=self.__worker__, args=(w_complete,))
					self.__workers__.append((worker, w_complete))
					worker.start()
			else:
				callback.callback(*callback.args, **callback.kwargs)

	### Standard methods
	def end(self, exit_code: int = 0) -> None:
		"""
		Ends the terminal
		:param exit_code: The exit code to use
		:raises InvalidArgumentException: If 'exit_code' is not an integer
		"""

		Misc.raise_ifn(isinstance(exit_code, int), Exceptions.InvalidArgumentException(Terminal.end, 'exit_code', type(exit_code), (int,)))
		self.__enabled__ = int(exit_code)

	def putstr(self, msg: str | Struct.AnsiStr | Iterable.String, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., n: typing.Optional[int] = ...) -> None:
		"""
		Prints a string to the terminal
		:param msg: A string, String or Struct.AnsiStr instance
		:param x: The x coordinate or current x if not supplied
		:param y: The y coordinate or current y if not supplied
		:param n: ?
		:raises InvalidArgumentException: If 'msg' is not a string, String instance, or Struct.AnsiStr instance
		:raises InvalidArgumentException: If 'x', 'y', or 'n' is not an integer
		"""

		if not isinstance(msg, (str, Struct.AnsiStr, Iterable.String)):
			raise Exceptions.InvalidArgumentException(Terminal.putstr, 'msg', type(msg), (str, Struct.AnsiStr, Iterable.String))
		elif x is not ... and x is not None and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(Terminal.putstr, 'x', type(x), (int,))
		elif y is not ... and y is not None and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(Terminal.putstr, 'y', type(y), (int,))
		elif n is not ... and n is not None and not isinstance(n, int):
			raise Exceptions.InvalidArgumentException(Terminal.putstr, 'n', type(n), (int,))

		n = None if n is None or n is ... else int(n)

		if n is not None and n <= 0:
			return

		msg = msg if isinstance(msg, Struct.AnsiStr) else Struct.AnsiStr(str(msg))
		my, mx = self.__root__.getmaxyx()
		cx, cy = self.__move__()
		sx, sy = self.__scroll__
		ix: int = cx if x is ... or x is None else (int(x) - sx)
		iy: int = cy if y is ... or y is None else (int(y) - sy)
		true_count: int = 0
		char_count: int = 0
		line_count: int = 0
		self.__touched_cols_rows__[0] = min(ix, self.__touched_cols_rows__[0])
		self.__touched_cols_rows__[2] = min(iy, self.__touched_cols_rows__[2])

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

			fg: int = 7 if ansi.foreground_color is None else self.get_color(ansi.foreground_color)
			bg: int = 0 if ansi.background_color is None else self.get_color(ansi.background_color)
			color_pair: int = self.get_color_pair(fg, bg)
			attributes |= curses.color_pair(color_pair)
			char_x: int = ix + char_count
			char_y: int = iy + line_count

			self.__touched_cols_rows__[1] = min(char_x, self.__touched_cols_rows__[1])
			self.__touched_cols_rows__[3] = min(char_y, self.__touched_cols_rows__[3])

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
					self.__root__.delch(char_y, char_x - 1)
			elif segment == '\t':
				if 0 <= char_x < mx and 0 <= char_y < my:
					self.__root__.addstr(char_y, char_x, ' ' * self.__tab_size__, attributes)

				true_count += 1
				char_count += self.__tab_size__
			elif 0 <= (x := ix + char_count) < mx and 0 <= (y := iy + line_count) < my and len(segment):
				try:
					max_width: int = mx - x
					self.__root__.addstr(y, x, segment[:max_width], attributes)
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

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(Terminal.del_widget, '_id', type(_id), (int,)))
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

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(Terminal.del_sub_terminal, '_id', type(_id), (int,)))
		_id = int(_id)

		for alloc in self.__pages__.values():
			if _id in alloc:
				del alloc[_id]
				break

	def del_window(self, _id: int, exit_code: int = 0) -> None:
		"""
		Deletes a window by ID
		:param _id: The window's ID
		:param exit_code: The exit code to exit the window as
		:raises InvalidArgumentException: If '_id' is not an integer
		:raises InvalidArgumentException: If 'exit_code' is not an integer
		"""

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(Terminal.del_widget, '_id', type(_id), (int,)))
		_id = int(_id)

		if _id in self.__windows__:
			self.__windows__[_id].end(exit_code)
			del self.__windows__[_id]

	def cancel(self, _id: int) -> None:
		"""
		Cancels a scheduled callback by ID
		:param _id: The callback's ID
		:raises InvalidArgumentException: If '_id' is not an integer
		"""

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(Terminal.cancel, '_id', type(_id), (int,)))
		_id = int(_id)

		if _id in self.__scheduled_callables__:
			del self.__scheduled_callables__[_id]

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

		Misc.raise_ifn(isinstance(visibility, int), Exceptions.InvalidArgumentException(Terminal.cursor_visibility, 'visibility', type(visibility), (int,)))
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

		Misc.raise_ifn(isinstance(flash_rate, int), Exceptions.InvalidArgumentException(Terminal.cursor_flash, 'flash_rate', type(flash_rate), (int,)))
		Misc.raise_ifn(flash_rate := int(flash_rate) >= 0, ValueError('Cursor flash_rate must be >= 0'))
		cx, cy, vs, _ = self.__cursor__
		self.__cursor__ = (cx, cy, vs, flash_rate)

	def minimize(self) -> None:
		"""
		Minimizes the window
		"""

		self.__iconified__ = True

		if os.name == 'nt':
			hwnd: int = win32console.GetConsoleWindow()
			win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
		else:
			wid: int = self.__current_linux_window__()
			subprocess.run(['wmctrl', '-i', '-r', hex(wid), '-b', 'add,hidden'], capture_output=True, text=True, check=True, shell=True)

	def restore(self) -> None:
		"""
		Restores the window
		"""

		if os.name == 'nt':
			hwnd: int = win32console.GetConsoleWindow()
			win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
		else:
			wid: int = self.__current_linux_window__()
			subprocess.run(['wmctrl', '-i', '-r', hex(wid), '-b', 'remove,hidden'], capture_output=True, text=True, check=True, shell=True)

		self.__iconified__ = False

	def set_focus(self, widget: Widgets.MyWidget | int | None) -> None:
		"""
		Sets focus on a specific widget or clears focus if None
		:param widget: The widget or widget ID to focus or None to clear focus
		:raises InvalidArgumentException: If 'widget' is not a Widget instance or integer
		:raises ValueError: If the widget's handling terminal is not this terminal
		"""

		if widget is not None and not isinstance(widget, (Widgets.MyWidget, int)):
			raise Exceptions.InvalidArgumentException(Terminal.set_focus, 'widget', type(widget), (Widgets.MyWidget,))
		elif widget is None or isinstance(widget, int) or widget.parent is self:
			child: Widgets.MyWidget
			old_page: Widgets.MySubTerminal = self.__active_page__
			widget = self.get_widget(int(widget)) if isinstance(widget, int) else widget

			if widget is not None:
				subterminals: tuple[Widgets.MySubTerminal, ...] = self.subterminals()

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
		elif (topmost_b := widget.topmost_parent()) is not self:
			raise ValueError(f'The specified widget is not a child of this terminal - {hex(id(topmost_b))} != {hex(id(self))} (self)')
		else:
			widget.parent.set_focus(widget)

	def erase_refresh(self, flag: bool) -> None:
		"""
		:param flag: Whether this terminal will fully erase the terminal before the next draw
		"""

		self.__erase_refresh__ = bool(flag)

	def ungetch(self, key: int) -> None:
		"""
		Appends a key to this terminal's event queue
		:param key: The key code to append
		:raises InvalidArgumentException: If 'key' is not an integer
		"""

		Misc.raise_ifn(isinstance(key, int), Exceptions.InvalidArgumentException(Terminal.ungetch, 'key', type(key), (int,)))
		self.__event_queue__.append(int(key))

	def ungetgch(self, key: int) -> None:
		"""
		Appends a key to this terminal's global event queue
		:param key: The key code to append
		:raises InvalidArgumentException: If 'key' is not an integer
		"""

		Misc.raise_ifn(isinstance(key, int), Exceptions.InvalidArgumentException(Terminal.ungetgch, 'key', type(key), (int,)))
		self.__global_event_queue__.append(int(key))

	def reset_colors(self) -> None:
		"""
		Resets this terminal's color cache
		Useful if the program uses more terminal colors than curses may display
		"""

		self.__colors__.clear()
		self.__color_usage__.clear()
		self.__color_times__.clear()

		self.__color_pairs__.clear()
		self.__color_pair_usage__.clear()
		self.__color_pair_times__.clear()

		for alloc in self.__widgets__.values():
			for widget in alloc.values():
				if not widget.hidden:
					widget.redraw()

		for alloc in self.__pages__.values():
			for subterm in alloc.values():
				if not subterm.hidden:
					subterm.redraw()

		for window in self.__windows__.values():
			if not window.closed:
				window.redraw()

	def fullscreen(self, flag: typing.Optional[bool] = ...) -> typing.Optional[bool]:
		"""
		Sets or gets the fullscreen status of this terminal's window
		:param flag: Whether to be fullscreen or unset to get current fullscreen
		:return: Fullscreen status if 'flag' is unset, otherwise None
		"""

		if flag is None or flag is ...:
			return self.__fullscreen__
		elif os.name == 'nt':
			hwnd: int = win32console.GetConsoleWindow()
			self.__fullscreen__ = bool(flag)

			if self.__fullscreen__:
				win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
			else:
				win32gui.ShowWindow(hwnd, win32con.SW_SHOWDEFAULT)
		else:
			wid: int = self.__current_linux_window__()
			self.__fullscreen__ = bool(flag)
			subprocess.run(['wmctrl', '-i', '-r', hex(wid), '-b', f'{"add" if self.__fullscreen__ else "remove"},fullscreen'], capture_output=True, text=True, check=True, shell=True)

	def getch(self) -> typing.Optional[int]:
		"""
		Reads the next key code from this terminal's event queue
		:return: The next key code or None if no event is waiting
		"""

		return self.__event_queue__.pop() if len(self.__event_queue__) else None

	def peekch(self) -> typing.Optional[int]:
		"""
		Peeks the next key code from this terminal's event queue
		:return: The next key code or None if no event is waiting
		"""

		return self.__event_queue__[-1] if len(self.__event_queue__) else None

	def getgch(self) -> typing.Optional[int]:
		"""
		Reads the next key code from this terminal's global event queue
		:return: The next key code or None if no event is waiting
		"""

		return self.__global_event_queue__.pop() if len(self.__global_event_queue__) else None

	def peekgch(self) -> typing.Optional[int]:
		"""
		Peeks the next key code from this terminal's global event queue
		:return: The next key code or None if no event is waiting
		"""

		return self.__global_event_queue__[-1] if len(self.__global_event_queue__) else None

	def update_type(self, update_type: typing.Optional[int] = ...) -> typing.Optional[int]:
		"""
		Gets or sets this terminal's update type
		:param update_type: The update type (see Enums.WINUPDATE for a list of possible types)
		:return: The current update type if 'update_type' is unset otherwise None
		:raises InvalidArgumentException: If 'update_type' is not an integer
		:raises ValueError: If 'update_type' is not a valid update type
		"""

		if update_type is None or update_type is ...:
			return self.__update_type__
		else:
			Misc.raise_ifn(isinstance(update_type, int), Exceptions.InvalidArgumentException(Terminal.update_type, 'update_type', type(update_type), (int,)))
			Misc.raise_ifn(0 <= (update_type := int(update_type)) <= 2, ValueError(f'Invalid update type: \'{update_type}\''))
			self.__update_type__ = int(update_type)

	def scroll_speed(self, scroll: typing.Optional[int] = ...) -> typing.Optional[int]:
		"""
		Gets or sets the terminal's scrolling speed in lines per scroll button
		If the mouse scrolls once, this terminal will scroll 'scroll' lines
		:param scroll: The number of lines to scroll per scroll button press
		:return: The scroll speed if 'scroll' is unset otherwise None
		:raises InvalidArgumentException: If 'scroll' is not an integer
		"""

		if scroll is None or scroll is ...:
			return self.__auto_scroll__
		elif not isinstance(scroll, int):
			raise Exceptions.InvalidArgumentException(Terminal.scroll_speed, 'scroll', type(scroll), (int,))
		else:
			self.__auto_scroll__ = int(scroll)

	def first_empty_row(self) -> int:
		"""
		:return: The first empty row
		"""

		return self.__touched_cols_rows__[2]

	def last_empty_row(self) -> int:
		"""
		:return: The last empty row
		"""

		return self.__touched_cols_rows__[3]

	def first_empty_column(self) -> int:
		"""
		:return: The first empty column
		"""

		return self.__touched_cols_rows__[0]

	def last_empty_column(self) -> int:
		"""
		:return: The last empty column
		"""

		return self.__touched_cols_rows__[1]

	def get_color(self, color: Struct.Color | int) -> int:
		"""
		Gets the curses color ID given a color or curses color ID
		Color will be cached in this terminal if not already cached
		If the color cache is full, the oldest, least used, color will be replaced
		:param color: The color or color ID
		:return: The curses color ID
		:raises InvalidArgumentException: If 'color' is not an integer or Struct.Color instance
		"""

		if isinstance(color, int):
			return int(color)
		elif not isinstance(color, Struct.Color):
			raise Exceptions.InvalidArgumentException(Terminal.get_color, 'color', type(color), (Struct.Color, types.NoneType))
		elif color.color in self.__colors__:
			color_index: int = self.__colors__[color.color]
			self.__color_usage__[color_index] = self.__color_usage__[color_index] + 1 if color_index in self.__color_usage__ else 1
			return color_index
		else:
			next_color_index: int = max((self.__highest_default_color__, *self.__colors__.values())) + 1

			if next_color_index >= curses.COLORS:
				lowest_used: int = min(self.__color_usage__.values())
				oldest: tuple[int, ...] = tuple(pair[0] for pair in sorted(self.__color_times__.items(), key=lambda a: a[1]))
				next_color_index = next(color_index for color_index in oldest if self.__color_usage__[color_index] <= lowest_used)
				self.__color_usage__[next_color_index] = 0
				old_color: int = next(color for color, index in self.__colors__.items() if index == next_color_index)
				del self.__colors__[old_color]

			self.__colors__[color.color] = next_color_index
			self.__color_usage__[next_color_index] = self.__color_usage__[next_color_index] + 1 if next_color_index in self.__color_usage__ else 1
			self.__color_times__[next_color_index] = datetime.datetime.now(datetime.timezone.utc).timestamp()
			r, g, b = color.curses_rgb
			curses.init_color(next_color_index, r, g, b)
			return next_color_index

	def get_color_pair(self, fg: Struct.Color | int, bg: Struct.Color | int) -> int:
		"""
		Gets the curses color pair ID given a foreground color and background color
		Color pair will be cached in this terminal if not already cached
		If the color pair cache is full, the oldest, least used color pair will be replaced
		:param fg: The foreground color or color ID
		:param bg: The background color or color ID
		:return: The curses color pair ID
		:raises InvalidArgumentException: If 'fg' is not an integer or Struct.Color instance
		:raises InvalidArgumentException: If 'bg' is not an integer or Struct.Color instance
		"""

		fg: int = self.get_color(fg)
		bg: int = self.get_color(bg)
		colors: tuple[int, int] = (fg, bg)

		if colors in self.__color_pairs__:
			color_pair: int = self.__color_pairs__[colors]
			self.__color_pair_usage__[color_pair] = self.__color_pair_usage__[color_pair] + 1 if color_pair in self.__color_pair_usage__ else 1
			return color_pair
		else:
			color_pair: int = self.__highest_color_pair__ - 1 - len(self.__color_pairs__)

			if color_pair < 1:
				lowest_used: int = min(self.__color_pair_usage__.values())
				oldest: tuple[int, ...] = tuple(pair[0] for pair in sorted(self.__color_pair_times__.items(), key=lambda a: a[1]))
				color_pair = next(color_index for color_index in oldest if self.__color_pair_usage__[color_index] <= lowest_used)
				self.__color_pair_usage__[color_pair] = 0
				old_pair: tuple[int, int] = next(pair for pair, index in self.__color_pairs__.items() if index == color_pair)
				del self.__color_pairs__[old_pair]

			curses.init_pair(color_pair, fg, bg)
			self.__color_pairs__[colors] = color_pair
			self.__color_pair_usage__[color_pair] = 1
			self.__color_pair_times__[color_pair] = datetime.datetime.now(datetime.timezone.utc).timestamp()
			return color_pair

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

		__threaded = kwargs['__threaded'] if '__threaded' in kwargs else __threaded
		del kwargs['__threaded']
		struct: Terminal.ScheduledCallback = Terminal.ScheduledCallback(ticks, __threaded, callback, args, kwargs)
		_id: int = id(struct)
		self.__scheduled_callables__[_id] = struct
		return _id

	def mainloop(self, tps: int, before_draw: typing.Optional[typing.Callable[[Terminal], int]] = ..., after_draw: typing.Optional[typing.Callable[[Terminal], int]] = ...) -> int:
		"""
		Starts this terminal's main-loop
		For callbacks, any non-zero exit code will terminate the session
		:param tps: The ticks per second. Terminal will attempt refresh this many times per second
		:param before_draw: An optional callback to call before the terminal draws. Accepts the terminal as the first parameter and returns an exit code
		:param after_draw: An optional callback to call after the terminal draws. Accepts the terminal as the first parameter and returns an exit code
		:return: The exit code that caused this terminal to close
		:raise InvalidArgumentException: If 'tps' is not an integer
		:raise ValueError: If 'tps' is <= 0
		"""

		if self.__enabled__ is None:
			raise RuntimeError('Already enabled')

		Misc.raise_ifn(isinstance(tps, int), Exceptions.InvalidArgumentException(Terminal.mainloop, 'tps', type(tps), (int,)))
		Misc.raise_ifn((tps := int(tps)) > 0, ValueError('TPS cannot be zero or negative'))
		tick_rate: float = 1 / int(tps)
		factor: float = 1 if tps <= 500 else 0.85 if tps <= 1000 else 0
		rollover: int = 0xFFFFFFFFFFFFFFFF
		rollover = rollover - (rollover % tps)
		self.__enabled__ = None
		self.__exit_reason__ = None
		self.__full_end__ = None

		if os.name == 'nt':
			kernel32 = ctypes.WinDLL('Kernel32.dll')
			stdout = kernel32.GetStdHandle(-11)
			font: Struct.FontInfoEx = Struct.FontInfoEx()
			font.cbSize = ctypes.sizeof(Struct.FontInfoEx)
			font.FaceName = 'Unifont'
			font.dwFontSize.X = 8
			font.dwFontSize.Y = 16
			res = kernel32.SetCurrentConsoleFontEx(stdout, False, ctypes.byref(font))
			locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

			if not res:
				raise RuntimeError('Failed to set font info')

			import win32api
			win32api.SetConsoleCtrlHandler(self.__on_exit__, True)
		else:
			import signal
			signal.signal(signal.SIGHUP, self.__on_exit__)

		for window in self.__windows__.values():
			window.begin()

		try:
			curses.flushinp()

			while self.__enabled__ is None:
				self.__mainloop__(tick_rate, factor, rollover, before_draw, after_draw)

		except (SystemExit, KeyboardInterrupt) as e:
			self.__enabled__ = -1
			self.__exit_reason__ = e
		except Exception as e:
			sys.stderr.write(''.join(traceback.format_exception(e)))
			sys.stderr.flush()
			self.__enabled__ = 1
			self.__exit_reason__ = e
		finally:
			return self.__finalize__()

	def wait(self) -> int:
		"""
		Blocks this thread until the terminal closes
		:return: The exit code that caused terminal to close
		"""

		while self.__full_end__ is None:
			time.sleep(1e-6)

		return self.__full_end__

	def tab_size(self, size: typing.Optional[int] = ...) -> typing.Optional[int]:
		"""
		Gets or sets this terminal's tab size
		Tab will equal the space character times this value
		:param size: The tab size in characters
		:return: The current tab size if 'size' is unset otherwise None
		:raises InvalidArgumentException: If 'size' is not an integer
		:raises ValueError: If 'size' is less than 0
		"""

		if size is None or size is ...:
			return self.__tab_size__
		elif not isinstance(size, int):
			raise Exceptions.InvalidArgumentException(Terminal.tab_size, 'size', type(size), (int,))
		elif size < 0:
			raise ValueError('Tab size cannot be less than zero')
		else:
			self.__tab_size__ = int(size)

	def cursor(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> typing.Optional[tuple[int, int]]:
		"""
		Gets or sets the terminal's current cursor position
		:param x: The new cursor x position
		:param y: The new cursor y position
		:return: The current cursor position if 'x' and 'y' are unset otherwise None
		"""

		if (x is None or x is ...) and (y is None or y is ...):
			return self.__cursor__[0], self.__cursor__[1]
		elif x is not None and x is not ... and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(Terminal.cursor, 'x', type(x), (int,))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(Terminal.cursor, 'y', type(y), (int,))
		else:
			sx, sy = self.__scroll__
			cy, cx = self.__root__.getyx()
			_, _, visibility, rate = self.__cursor__
			self.__cursor__ = ((cx if x is None or x is ... else int(x)) + sx, (cy if y is None or y is ... else int(y)) + sy, visibility, rate)

	def scroll(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> typing.Optional[tuple[int, int]]:
		"""
		Gets or sets the terminal's current scroll offset
		:param x: The new scroll x offset
		:param y: The new scroll y offset
		:return: The current scroll offset if 'x' and 'y' are unset otherwise None
		"""

		if (x is None or x is ...) and (y is None or y is ...):
			x, y = self.__scroll__
			return x, y
		elif x is not None and x is not ... and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(Terminal.cursor, 'x', type(x), (int,))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(Terminal.cursor, 'y', type(y), (int,))
		else:
			self.__scroll__[0] = self.__scroll__[0] if x is None or x is ... else int(x)
			self.__scroll__[1] = self.__scroll__[1] if y is None or y is ... else int(y)

	def size(self, cols: typing.Optional[int] = ..., rows: typing.Optional[int] = ...) -> typing.Optional[tuple[int, int]]:
		"""
		Gets or sets the terminal's current size in characters
		:param cols: The new terminal width
		:param rows: The new terminal height
		:return: The current width and height if 'cols' and 'rows' are unset otherwise None
		"""

		if (cols is None or cols is ...) and (rows is None or rows is ...):
			my, mx = self.__root__.getmaxyx()
			return mx, my
		elif cols is not None and cols is not ... and not isinstance(cols, int):
			raise Exceptions.InvalidArgumentException(Terminal.size, 'cols', type(cols), (int,))
		elif rows is not None and rows is not ... and not isinstance(rows, int):
			raise Exceptions.InvalidArgumentException(Terminal.size, 'rows', type(rows), (int,))
		else:
			my, mx = self.__root__.getmaxyx()
			curses.resize_term(my if rows is None or rows is ... else int(rows), mx if cols is None or cols is ... else int(cols))

	def chat(self, x: int, y: int) -> tuple[int, int]:
		"""
		Gets the character and its format attribute at the specified position
		:param x: The x position
		:param y: The y position
		:return: The character and attribute
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		Misc.raise_ifn(isinstance(x, int), Exceptions.InvalidArgumentException(Terminal.chat, 'x', type(x), (int,)))
		Misc.raise_ifn(isinstance(y, int), Exceptions.InvalidArgumentException(Terminal.chat, 'y', type(y), (int,)))
		sx, sy = self.__scroll__
		full: int = self.__root__.inch(x - sx, y - sy)
		char: int = full & 0xFF
		attr: int = (full >> 8) & 0xFF
		return char, attr

	def to_fixed(self, x: int, y: int) -> tuple[int, int]:
		"""
		Converts the specified scroll independent coordinate into true terminal coordinates
		An input of (0, 0) will always give the top-left corner regardless of scroll offset
		:param x: The scroll independent x coordinate
		:param y: The scroll independent y coordinate
		:return: The true adjusted coordinates
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		Misc.raise_ifn(isinstance(x, int), Exceptions.InvalidArgumentException(Terminal.to_fixed, 'x', type(x), (int,)))
		Misc.raise_ifn(isinstance(y, int), Exceptions.InvalidArgumentException(Terminal.to_fixed, 'y', type(y), (int,)))
		sx, sy = self.__scroll__
		return x + sx, y + sy

	def from_fixed(self, x: int, y: int) -> tuple[int, int]:
		"""
		Converts the specified true terminal coordinate into scroll independent coordinates
		:param x: The true x coordinate
		:param y: The true y coordinate
		:return: The scroll independent coordinates
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		Misc.raise_ifn(isinstance(x, int), Exceptions.InvalidArgumentException(Terminal.from_fixed, 'x', type(x), (int,)))
		Misc.raise_ifn(isinstance(y, int), Exceptions.InvalidArgumentException(Terminal.from_fixed, 'y', type(y), (int,)))
		sx, sy = self.__scroll__
		return x - sx, y - sy

	def getline(self, replace_char: typing.Optional[str | Struct.AnsiStr | Iterable.String] = ..., prompt: typing.Optional[str | Struct.AnsiStr | Iterable.String] = '', x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> str:
		"""
		Pauses terminal execution and reads a line from the user
		For standard input without pausing, add an 'Entry' widget
		:param replace_char: The character to replace entered characters with (usefull for passwords or hidden entries)
		:param prompt: The prompt to display
		:param x: The x position to display at
		:param y: The y position to display at
		:return: The entered string
		:raises InvalidArgumentException: If 'replace_char' is not a string, Struct.AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'prompt' is not a string, Struct.AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises ValueError: If 'replace_char' is not a single character
		"""

		Misc.raise_ifn(replace_char is None or replace_char is ... or (isinstance(replace_char, (str, Struct.AnsiStr, Iterable.String))), Exceptions.InvalidArgumentException(Terminal.getline, 'replace_char', type(replace_char), (str, Iterable.String, Struct.AnsiStr)))
		Misc.raise_ifn(replace_char is None or replace_char is ... or len(replace_char := str(replace_char)) == 1, ValueError('Replacement character must be a string of length 1'))
		Misc.raise_ifn(x is None or x is ... or isinstance(x, int), Exceptions.InvalidArgumentException(Terminal.from_fixed, 'x', type(x), (int,)))
		Misc.raise_ifn(x is None or x is ... or isinstance(y, int), Exceptions.InvalidArgumentException(Terminal.from_fixed, 'y', type(y), (int,)))
		Misc.raise_ifn(prompt is None or prompt is ... or (isinstance(prompt, (str, Iterable.String, Struct.AnsiStr))), Exceptions.InvalidArgumentException(Terminal.getline, 'prompt', type(prompt), (str, Iterable.String, Struct.AnsiStr)))

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
		self.__root__.move(cy, cx)

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
			my, mx = self.__root__.getmaxyx()
			self.__stdscr__.refresh(self.__scroll__[1], self.__scroll__[0], 0, 0, my - 1, mx - 1)

		result: str = ''.join(chars)

		if len(result):
			self.__previous_inputs__.append(result)

		return result

	def font(self, font: typing.Optional[Struct.Font] = ...) -> typing.Optional[Struct.Font]:
		"""
		WINDOWS ONLY
		Gets or sets the terminal's current font
		:param font: The Struct.Font instance to set
		:return: The current Struct.Font instance if 'font' is unset otherwise None
		:raises InvalidArgumentException: If 'font' is not a Struct.Font instance
		:raises RuntimeError: If system failed to get or set font
		"""

		if os.name != 'nt':
			return

		kernel32 = ctypes.WinDLL('Kernel32.dll')
		stdout = kernel32.GetStdHandle(-11)

		if font is None or font is ...:
			current_font: Struct.FontInfoEx = Struct.FontInfoEx()
			current_font.cbSize = ctypes.sizeof(Struct.FontInfoEx)
			res = kernel32.GetCurrentConsoleFontEx(stdout, False, ctypes.byref(current_font))

			if not res:
				raise RuntimeError('Failed to get font info')

			return Struct.Font(current_font.FaceName, (current_font.dwFontSize.X, current_font.dwFontSize.Y), current_font.FontWeight)
		elif not isinstance(font, Struct.Font):
			raise Exceptions.InvalidArgumentException(Terminal.font, 'font', type(font), (Struct.Font,))
		else:
			new_font: Struct.FontInfoEx = Struct.FontInfoEx()
			new_font.cbSize = ctypes.sizeof(Struct.FontInfoEx)
			new_font.FaceName = font.fontname
			new_font.dwFontSize.X = font.fontsize[0]
			new_font.dwFontSize.Y = font.fontsize[1]
			new_font.FontFamily = 54
			new_font.FontWeight = font.fontweight

			res = kernel32.SetCurrentConsoleFontEx(stdout, False, ctypes.byref(new_font))

			if not res:
				raise RuntimeError('Failed to set font info')

	def get_topmost_child_at(self, x: int, y: int) -> typing.Optional[Widgets.MyWidget]:
		"""
		Gets the topmost widget at the specified coordinates
		:param x: The x coordinate to check
		:param y: The y coordinate to check
		:return: The topmost widget or None if no widget exists
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		Misc.raise_ifn(isinstance(x, int), Exceptions.InvalidArgumentException(Terminal.get_topmost_child_at, 'x', type(x), (int,)))
		Misc.raise_ifn(isinstance(y, int), Exceptions.InvalidArgumentException(Terminal.get_topmost_child_at, 'y', type(y), (int,)))
		x -= self.__scroll__[0]
		y -= self.__scroll__[1]

		for z_index in sorted(self.__pages__.keys(), reverse=True):
			for _id, widget in self.__pages__[z_index].items():
				if not widget.hidden and widget.has_coord(x, y):
					return widget

		for z_index in sorted(self.__widgets__.keys(), reverse=True):
			for _id, widget in self.__widgets__[z_index].items():
				if not widget.hidden and widget.has_coord(x, y):
					return widget

		return None

	def get_focus(self) -> typing.Optional[Widgets.MyWidget]:
		"""
		:return: The widget with focus or None if no widget has focus
		"""

		child: Widgets.MyWidget

		for child in (*self.widgets(), *self.subterminals()):
			if child.focused:
				return child

		return None

	def active_subterminal(self) -> typing.Optional[Widgets.MySubTerminal]:
		"""
		:return: The sub-terminal with focus or None if no sub-terminal is active
		"""

		page: Widgets.MySubTerminal | None = self.__active_page__

		if page is None or page.hidden:
			return None

		while page.selected_subterminal is not None and not page.selected_subterminal.hidden:
			page = page.selected_subterminal

		return page

	def get_widget(self, _id: int) -> Widgets.MyWidget:
		"""
		Gets the widget with the specified ID
		:param _id: The widget ID
		:return: The widget
		:raises InvalidArgumentException: If '_id' is not an integer
		:raises KeyError: If no widget with the specified ID exists
		"""

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(Terminal.get_widget, '_id', type(_id), (int,)))

		for z_index, widgets in self.__widgets__.items():
			if _id in widgets:
				return widgets[_id]

		raise KeyError(f'No such widget - {_id}')

	def get_sub_terminal(self, _id: int) -> Widgets.MySubTerminal:
		"""
		Gets the sub-terminal with the specified ID
		:param _id: The sub-terminal ID
		:return: The sub-terminal
		:raises InvalidArgumentException: If '_id' is not an integer
		:raises KeyError: If no sub-terminal with the specified ID exists
		"""

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(Terminal.get_sub_terminal, '_id', type(_id), (int,)))

		for z_index, sub_terminals in self.__pages__.items():
			if _id in sub_terminals:
				return sub_terminals[_id]

		raise KeyError(f'No such terminal - {_id}')

	def get_window(self, _id: int) -> WindowTerminal:
		"""
		Gets the window with the specified ID
		:param _id: The window ID
		:return: The window
		:raises InvalidArgumentException: If '_id' is not an integer
		:raises KeyError: If no window with the specified ID exists
		"""

		Misc.raise_ifn(isinstance(_id, int), Exceptions.InvalidArgumentException(Terminal.get_window, '_id', type(_id), (int,)))

		if _id in self.__windows__:
			return self.__windows__[_id]
		else:
			raise KeyError(f'No such window - {_id}')

	def get_children_at(self, x: int, y: int) -> tuple[Widgets.MyWidget, ...]:
		"""
		Gets all widgets or sub-terminals at the specified coordinates
		:param x: The x coordinate to check
		:param y: The y coordinate to check
		:return: All widgets or sub-terminals overlapping the specified coordinates
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		Misc.raise_ifn(isinstance(x, int), Exceptions.InvalidArgumentException(Terminal.get_children_at, 'x', type(x), (int,)))
		Misc.raise_ifn(isinstance(y, int), Exceptions.InvalidArgumentException(Terminal.get_children_at, 'y', type(y), (int,)))
		children: list[Widgets.MyWidget] = []

		for z_index in sorted(self.__pages__.keys(), reverse=True):
			for _id, widget in self.__pages__[z_index].items():
				if widget.has_coord(x, y):
					children.append(widget)

		for z_index in sorted(self.__widgets__.keys(), reverse=True):
			for _id, widget in self.__widgets__[z_index].items():
				if widget.has_coord(x, y):
					children.append(widget)

		return tuple(children)

	def widgets(self) -> tuple[Widgets.MyWidget, ...]:
		"""
		:return: All widgets in this terminal
		"""

		ids: list[Widgets.MyWidget] = []

		for alloc in self.__widgets__.values():
			ids.extend(alloc.values())

		return tuple(ids)

	def subterminals(self) -> tuple[Widgets.MySubTerminal, ...]:
		"""
		:return: All sub-terminals in this terminal
		"""

		ids: list[Widgets.MySubTerminal] = []

		for alloc in self.__pages__.values():
			ids.extend(alloc.values())

		return tuple(ids)

	def windows(self) -> tuple[WindowTerminal, ...]:
		"""
		:return: All windows in this terminal
		"""

		return tuple(self.__windows__.values())

	def children(self) -> dict[int, Widgets.MyWidget | WindowTerminal]:
		"""
		:return: All widgets, sub-terminals, and windows in this terminal
		"""

		children: dict[int, Widgets.MyWidget | WindowTerminal] = self.__windows__.copy()

		for alloc in self.__pages__.values():
			children.update(alloc)

		for alloc in self.__widgets__.values():
			children.update(alloc)

		return children

	### Widget methods
	def add_button(self, x: int, y: int, width: int, height: int, text: str | Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_NONE,
				   border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
				   color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MyButton:
		"""
		Adds a new button widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param text: Display text
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the Enums.WORDWRAP_ enums)
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The button widget
		"""

		widget: Widgets.MyButton = Widgets.MyButton(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
													border=border, highlight_border=highlight_border, active_border=active_border,
													color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
													callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_toggle_button(self, x: int, y: int, width: int, height: int, text: str | Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_NONE,
						  border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
						  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
						  callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MyToggleButton:
		"""
		Adds a new toggle button widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param text: Display text
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the Enums.WORDWRAP_ enums)
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The button widget
		"""

		widget: Widgets.MyToggleButton = Widgets.MyToggleButton(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
																border=border, highlight_border=highlight_border, active_border=active_border,
																color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str | Struct.AnsiStr | Iterable.String = '', active_text: str | Struct.AnsiStr | Iterable.String = 'X',
					 border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
					 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_checked: typing.Optional[typing.Callable[[Widgets.MyWidget, bool], None]] = ...) -> Widgets.MyCheckbox:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:param on_checked: The callback to call when the checkbox's checked state changes this widget and the widget's current state as arguments
		:return: The checkbox button widget
		"""

		widget: Widgets.MyCheckbox = Widgets.MyCheckbox(self, x, y, z_index=z_index, text=text, active_text=active_text,
														border=border, highlight_border=highlight_border, active_border=active_border,
														color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
														callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close, on_checked=on_checked)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_inline_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str | Struct.AnsiStr | Iterable.String = '', active_text: str | Struct.AnsiStr | Iterable.String = 'X',
							border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
							color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
							callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_checked: typing.Optional[typing.Callable[[Widgets.MyWidget, bool], None]] = ...) -> Widgets.MyInlineCheckbox:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:param on_checked: The callback to call when the checkbox's checked state changes this widget and the widget's current state as arguments
		:return: The checkbox button widget
		"""

		widget: Widgets.MyInlineCheckbox = Widgets.MyInlineCheckbox(self, x, y, z_index=z_index, text=text, active_text=active_text,
																	border=border, highlight_border=highlight_border, active_border=active_border,
																	color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																	callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close, on_checked=on_checked)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_radial_spinner(self, x: int, y: int, *, z_index: int = 0, phases: typing.Iterable[str | Struct.AnsiStr | Iterable.String] = ('--', '\\', '|', '/'), bg_phase_colors: typing.Optional[Enums.Color_T] | typing.Iterable[typing.Optional[Enums.Color_T]] = ..., fg_phase_colors: typing.Optional[Enums.Color_T] | typing.Iterable[typing.Optional[Enums.Color_T]] = Struct.Color(0xFFFFFF),
						   callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MyRadialSpinner:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The radial spinner widget
		"""

		widget: Widgets.MyRadialSpinner = Widgets.MyRadialSpinner(self, x, y, z_index=z_index, phases=phases, bg_phase_colors=bg_phase_colors, fg_phase_colors=fg_phase_colors,
																  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_horizontal_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, step: float = 1, fill_char: str | Struct.AnsiStr | Iterable.String = '|', _max: float = 10, _min: float = 0, on_input: typing.Callable[[Widgets.MyHorizontalSlider], None] = ...,
							  border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
							  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
							  callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MyHorizontalSlider:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The horizontal slider widget
		"""

		widget: Widgets.MyHorizontalSlider = Widgets.MyHorizontalSlider(self, x, y, width, height, z_index=z_index, step=step, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
																		border=border, highlight_border=highlight_border, active_border=active_border,
																		color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																		callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_vertical_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Struct.AnsiStr | Iterable.String = '=', _max: float = 10, _min: float = 0, on_input: typing.Callable[[Widgets.MyVerticalSlider], None] = ...,
							border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
							color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
							callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MyVerticalSlider:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The vertical slider widget
		"""

		widget: Widgets.MyVerticalSlider = Widgets.MyVerticalSlider(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
																	border=border, highlight_border=highlight_border, active_border=active_border,
																	color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																	callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_horizontal_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Struct.AnsiStr | Iterable.String = '|', _max: float = 10, _min: float = 0,
									border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
									color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
									callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MyHorizontalProgressBar:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The horizontal progress bar widget
		"""

		widget: Widgets.MyHorizontalProgressBar = Widgets.MyHorizontalProgressBar(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
																				  border=border, highlight_border=highlight_border, active_border=active_border,
																				  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																				  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_vertical_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Struct.AnsiStr | Iterable.String = '=', _max: float = 10, _min: float = 0,
								  border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
								  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
								  callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MyVerticalProgressBar:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The vertical progress bar widget
		"""

		widget: Widgets.MyVerticalProgressBar = Widgets.MyVerticalProgressBar(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
																			  border=border, highlight_border=highlight_border, active_border=active_border,
																			  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																			  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_text(self, x: int, y: int, width: int, height: int, text: str | Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Enums.NORTH_WEST, word_wrap: int = Enums.WORDWRAP_NONE,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MyText:
		"""
		Adds a new text widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param text: Display text
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the Enums.WORDWRAP_ enums)
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The text widget
		"""

		widget: Widgets.MyText = Widgets.MyText(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
												color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_dropdown(self, x: int, y: int, width: int, height: int, choices: tuple[str | Struct.AnsiStr | Iterable.String, ...], *, display_count: int | None = None, allow_scroll_rollover: bool = False, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_WORD, on_select: typing.Optional[typing.Callable[[Widgets.MyWidget], bool | None]] = ...,
					 border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
					 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MyDropdown:
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
		:param word_wrap: The word wrapping type (one of the Enums.WORDWRAP_ enums)
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The dropdown widget
		"""

		widget: Widgets.MyDropdown = Widgets.MyDropdown(self, x, y, width, height, choices, display_count=display_count, allow_scroll_rollover=allow_scroll_rollover, z_index=z_index, justify=justify, word_wrap=word_wrap, on_select=on_select,
														border=border, highlight_border=highlight_border, active_border=active_border,
														color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
														callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_entry(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, word_wrap: int = Enums.WORDWRAP_WORD, justify: int = Enums.NORTH_WEST, replace_chars: str | Struct.AnsiStr | Iterable.String = '', placeholder: typing.Optional[str | Struct.AnsiStr | Iterable.String] = ..., cursor_blink_speed: int = 0, on_text: typing.Optional[typing.Callable[[Widgets.MyEntry, bool], bool | str | Struct.AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[Widgets.MyEntry, str | Struct.AnsiStr, int], bool | str | Struct.AnsiStr | None]] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MyEntry:
		"""
		Adds a new entry widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the Enums.WORDWRAP_ enums)
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The entry widget
		"""

		widget: Widgets.MyEntry = Widgets.MyEntry(self, x, y, width, height, z_index=z_index, word_wrap=word_wrap, justify=justify, replace_chars=replace_chars, placeholder=placeholder, cursor_blink_speed=cursor_blink_speed, on_text=on_text, on_input=on_input,
												  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_image(self, x: int, y: int, width: int, height: int, image: str | Struct.AnsiStr | Iterable.String | numpy.ndarray | PIL.Image.Image, *, z_index: int = 0, use_subpad: bool = True, div: typing.Optional[int] = ...,
				  border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ...,
				  callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MyImage:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The image widget
		"""

		widget: Widgets.MyImage = Widgets.MyImage(self, x, y, width, height, image, z_index=z_index, div=div, use_subpad=use_subpad,
												  border=border, highlight_border=highlight_border, active_border=active_border,
												  color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
												  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_sub_terminal(self, x: int, y: int, width: int, height: int, *, title: typing.Optional[str | Struct.AnsiStr | Iterable.String] = ..., z_index: int = 0, transparent: bool = False,
						 border: Struct.BorderInfo = ..., highlight_border: Struct.BorderInfo = ..., active_border: Struct.BorderInfo = ...,
						 callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Widgets.MySubTerminal:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: The sub-terminal
		"""

		terminal: Widgets.MySubTerminal = Widgets.MySubTerminal(self, x, y, width, height, title, z_index=z_index, transparent=transparent,
																border=border, highlight_border=highlight_border, active_border=active_border,
																callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(terminal)

		if z_index in self.__pages__:
			self.__pages__[z_index][_id] = terminal
		else:
			self.__pages__[z_index] = {_id: terminal}

		return terminal

	def add_window(self, tps: int, width: typing.Optional[int] = ..., height: typing.Optional[int] = ..., before_draw: typing.Optional[typing.Callable] = ..., after_draw: typing.Optional[typing.Callable] = ..., font: typing.Optional[Struct.Font] = ...) -> WindowTerminal:
		"""
		Adds a new sub-window to this terminal
		Windows are separate consoles and processes
		:param tps: The window's tick rate (same as supplied to this terminal's mainloop method)
		:param width: The width of the window in characters
		:param height: The height of the window in characters
		:param before_draw: A callback to call every tick of the window before draw
		:param after_draw: A callback to call every tick of the window after draw
		:param font: The font the window should use
		:return: The new sub-window
		"""

		window: WindowTerminal = WindowTerminal(tps, width, height, before_draw, after_draw, font)
		_id: int = id(window)
		self.__windows__[_id] = window

		if self.__enabled__ is None:
			window.begin()

		return window

	def add_widget[T: Widgets.MyWidget](self, cls: type[T], *args, z_index: int = 0, **kwargs) -> T:
		"""
		Adds a new widget to this terminal
		This is for use with custom widget classes extending from the Widget class
		:param cls: The widget class to instantiate
		:param args: The positional arguments to pass into the constructor
		:param z_index: Z-index, higher is drawn last
		:param kwargs: The keyword arguments to pass into the constructor
		:return: The new widget
		"""

		assert issubclass(cls, Widgets.MyWidget)
		widget: Widgets.MyWidget = cls(self, *args, **kwargs)
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

		return self.__root__

	@property
	def enabled(self) -> bool:
		"""
		:return: Whether the terminal is active
		"""

		return self.__enabled__ is None

	@property
	def minimized(self) -> bool:
		"""
		:return: Whether the terminal window is minimized
		"""

		return self.__iconified__

	@property
	def exit_code(self) -> typing.Optional[int]:
		"""
		:return: This terminal's exit code or None if still active
		"""

		return self.__enabled__

	@property
	def exit_reason(self) -> typing.Optional[BaseException]:
		"""
		:return: The error that caused this terminal to exit or None if not an error or still active
		"""

		return self.__exit_reason__

	@property
	def current_tick(self) -> int:
		"""
		:return: This terminal's current tick
		"""

		return self.__tick__

	@property
	def mouse(self) -> Struct.MouseInfo:
		"""
		:return: The mouse info holding the last mouse event this terminal received
		"""

		return self.__last_mouse_info__

	@property
	def selected_subterminal(self) -> typing.Optional[Widgets.MySubTerminal]:
		"""
		:return: The current focused sub-terminal or None if no sub-terminal is active
		"""

		return self.__active_page__

	@property
	def default_bg(self) -> Struct.Color:
		"""
		:return: The default terminal background color
		"""

		return Struct.Color.fromcursesrgb(*curses.color_content(0))

	@property
	def default_fg(self) -> Struct.Color:
		"""
		:return: The default terminal foreground color
		"""

		return Struct.Color.fromcursesrgb(*curses.color_content(7))

	@property
	def focused(self) -> bool:
		"""
		:return: Whether this window has focus
		:raises NotImplementedError: If on linux or macOS
		"""

		if os.name == 'nt':
			this_win = win32console.GetConsoleWindow()
			foreground = win32gui.GetForegroundWindow()
			return this_win == foreground
		else:
			return self.__current_linux_window__() == self.__active_linux_window__()

class WindowTerminal:
	class SubprocessTerminal(Terminal):
		def __init__(self, conn: Connection.NamedPipe, widget_conn: Connection.NamedPipe, width: typing.Optional[int] = ..., height: typing.Optional[int] = ..., font: typing.Optional[Struct.Font] = ...):
			super().__init__(width, height, font)
			self.__conn__: Connection.NamedPipe = conn
			self.__widget_pipe__: Connection.NamedPipe = widget_conn
			self.__serialized_widgets__: dict[int, Widgets.MyWidget.MySerializedWidget] = {}

		def __mainloop__(self, tick_rate: float, factor: float, rollover: int, before_draw: typing.Callable, after_draw: typing.Callable) -> None:
			if self.__conn__.closed or self.__widget_pipe__.closed:
				self.end(13)

			while self.__conn__.poll():
				attr_name, _id, args, kwargs = self.__conn__.recv()
				is_method: bool = attr_name.endswith('()')

				try:
					attr = getattr(self, attr_name[:-2] if is_method else attr_name)
					has_callback = is_method and 'callback' in kwargs and callable(attr) and kwargs['callback'] is True

					if has_callback:
						kwargs['callback'] = lambda widget: self.__conn__.send((id(widget), True, id(widget)))

					result = attr(*args, **kwargs) if is_method else attr
					self.__conn__.send((_id, True, result))
				except (SystemExit, KeyboardInterrupt) as err:
					self.__conn__.send((_id, False, err))
					self.__enabled__ = -1
				except Exception as err:
					self.__conn__.send((_id, False, err))

			while self.__widget_pipe__.poll():
				wid, attr_name, _id, args, kwargs = self.__widget_pipe__.recv()
				is_method: bool = attr_name.endswith('()')
				widget: Widgets.MyWidget = None if wid not in self.__serialized_widgets__ else self.__serialized_widgets__[wid].__widget__
				_widget: Widgets.MyWidget = self.get_widget(wid)

				if widget is None and _widget is None:
					self.__widget_pipe__.send((wid, _id, False, IndexError(f'No such widget - {wid}')))
				elif widget is not None and _widget is None:
					self.__widget_pipe__.send((wid, _id, False, IndexError(f'No such widget - {wid}')))
					del self.__serialized_widgets__[wid]
				else:
					if widget is None:
						widget = _widget
						self.__serialized_widgets__[wid] = Widgets.MyWidget.MySerializedWidget(self.__widget_pipe__, widget)

					try:
						attr = getattr(widget, attr_name[:-2] if is_method else attr_name)
						result = attr(*args, **kwargs) if is_method else attr
						self.__widget_pipe__.send((wid, _id, True, result))
					except (SystemExit, KeyboardInterrupt) as err:
						self.__widget_pipe__.send((wid, _id, False, err))
						self.__enabled__ = -1
					except Exception as err:
						self.__widget_pipe__.send((wid, _id, False, err))
			super().__mainloop__(tick_rate, factor, rollover, before_draw, after_draw)

	### Magic methods
	def __init__(self, tps: int, width: typing.Optional[int] = ..., height: typing.Optional[int] = ..., before_draw: typing.Optional[typing.Callable] = ..., after_draw: typing.Optional[typing.Callable] = ..., font: typing.Optional[Struct.Font] = ...):
		"""
		Creates a new sub-window
		:param tps: The window's tick rate (same as supplied to this terminal's mainloop method)
		:param width: The width of the window in characters
		:param height: The height of the window in characters
		:param before_draw: A callback to call every tick of the window before draw
		:param after_draw: A callback to call every tick of the window after draw
		:param font: The font the window should use
		:raises AttributeError: If 'before_draw' or 'after_draw' are not module level callables
		:raises InvalidArgumentException: If 'tps' is not an integer
		:raises InvalidArgumentException: If 'width' is not an integer
		:raises InvalidArgumentException: If 'height' is not an integer
		:raises InvalidArgumentException: If 'before_draw' or 'after_draw' are not callable
		:raises InvalidArgumentException: If 'font' is not a Struct.Font instance
		:raise ValueError: If 'tps' is <= 0
		:raises IOError: If the window failed to open inter-process communications pipe
		"""

		callables: dict[str, tuple[str, str, str]] = {}
		res: int

		if callable(before_draw):
			module: types.ModuleType = sys.modules[before_draw.__module__]

			if not hasattr(module, '__file__'):
				raise AttributeError('The specified module has no file and cannot be loaded')

			callables['before_draw'] = (module.__file__, module.__name__, before_draw.__name__)
		elif before_draw is not None and before_draw is not ...:
			raise Exceptions.InvalidArgumentException(WindowTerminal.__init__, 'before_draw', type(before_draw))

		if callable(after_draw):
			module: types.ModuleType = sys.modules[after_draw.__module__]

			if not hasattr(module, '__file__'):
				raise AttributeError('The specified module has no file and cannot be loaded')

			callables['after_draw'] = (module.__file__, module.__name__, after_draw.__name__)
		elif after_draw is not None and after_draw is not ...:
			raise Exceptions.InvalidArgumentException(WindowTerminal.__init__, 'after_draw', type(after_draw))

		Misc.raise_ifn(isinstance(tps, int), Exceptions.InvalidArgumentException(WindowTerminal.__init__, 'tps', type(tps), (int,)))
		Misc.raise_ifn(width is None or width is ... or isinstance(width, int), Exceptions.InvalidArgumentException(WindowTerminal.__init__, 'width', type(width), (int,)))
		Misc.raise_ifn(height is None or height is ... or isinstance(height, int), Exceptions.InvalidArgumentException(WindowTerminal.__init__, 'height', type(height), (int,)))
		Misc.raise_ifn(font is None or font is ... or isinstance(font, Struct.Font), Exceptions.InvalidArgumentException(WindowTerminal.__init__, 'font', type(font), (Struct.Font,)))
		Misc.raise_ifn((tps := int(tps)) > 0, ValueError('TPS cannot be zero or negative'))

		conn: Connection.NamedPipe = Connection.NamedPipe()
		widget_conn: Connection.NamedPipe = Connection.NamedPipe()
		self.__conn__: Connection.NamedPipe = conn
		self.__widget_pipe__: Connection.NamedPipe = widget_conn
		self.__process__: subprocess.Popen = subprocess.Popen(f'"{sys.executable}" -m "CustomMethodsVI.Terminal._subterm" "{base64.b64encode(pickle.dumps((os.getpid(), conn, widget_conn, tps, width, height, font, callables))).decode()}"', creationflags=subprocess.CREATE_NEW_CONSOLE, close_fds=False)
		self.__psutil_process__: psutil.Process = psutil.Process(self.__process__.pid)
		self.__enabled__: bool = False
		self.__next_id__: int = -1
		self.__closed_ids__: list[int] = []
		self.__events__: dict[int, Concurrent.ThreadedPromise] = {}
		self.__widget_callbacks__: dict[int, typing.Callable] = {}
		self.__serialized_widgets__: dict[int, Widgets.MyWidget.MySerializedWidget] = {}
		self.__remote_exit_reason__: None | BaseException = None
		self.__thread__ = None
		self.__pending_actions__: list[tuple] = []

		while (res := self.__conn__.poll()) == 0 and self.__psutil_process__.is_running():
			time.sleep(1e-3)

		if res:
			start_byte: int = self.__conn__.read(1)[0]

			if start_byte != 0:
				os.kill(self.__process__.pid, signal.SIGINT)
				self.__conn__.close()
			else:
				self.__thread__: threading.Thread = threading.Thread(target=self.__promise_handler__)
		else:
			raise IOError(f'Failed to open IPC - EXIT={self.__process__.poll()}')

	def __del__(self):
		if not self.closed:
			self.close()

	### Internal methods
	def __promise_handler__(self) -> None:
		"""
		INTERNAL METHOD
		Handles results of IPC promise
		"""

		try:
			while self.__enabled__ and not self.__conn__.closed and self.__psutil_process__.is_running():
				if self.__conn__.poll():
					_id, success, data = self.__conn__.recv()

					if _id == 0:
						self.__remote_exit_reason__ = data
						self.__enabled__ = False
						self.__conn__.close()
						self.__widget_pipe__.close()
						break

					elif _id in self.__events__:
						promise = self.__events__[_id]

						if success:
							promise.resolve(data)
						else:
							promise.throw(data)

						del self.__events__[_id]
						self.__closed_ids__.append(_id)

					elif _id in self.__widget_callbacks__:
						self.__widget_callbacks__[_id](data)

				if self.__widget_pipe__.poll():
					wid, _id, success, data = self.__widget_pipe__.recv()

					if wid in self.__serialized_widgets__:
						self.__serialized_widgets__[wid].__fulfill__(_id, success, data)

				time.sleep(1e-6)

		except (SystemExit, KeyboardInterrupt):
			pass
		finally:
			print('CLOSED')
			for _id, promise in self.__events__.items():
				promise.throw(ConnectionAbortedError('Process closed'))

	def __bind_widget_callback__(self, widget_id: int, callback: typing.Callable) -> None:
		"""
		INTERNAL METHOD
		Binds a widget callback
		:param widget_id: The source widget ID
		:param callback: The callback
		"""

		if callable(callback):
			self.__widget_callbacks__[widget_id] = callback

	def __bind_widget__(self, promise: Concurrent.ThreadedPromise[Widgets.MyWidget.MySerializedWidget], return_promise: Concurrent.ThreadedPromise[Widgets.MyWidget.MySerializedWidget]) -> None:
		"""
		Binds a widget's IPC promise with a return promise sent to caller
		:param promise: The widget's promise
		:param return_promise: The promise to fulfill
		"""

		if promise.has_erred():
			return_promise.throw(promise.response(False))
			return

		serialized_widget: Widgets.MyWidget.MySerializedWidget = promise.response()
		serialized_widget.__conn__ = self.__widget_pipe__
		self.__serialized_widgets__[serialized_widget.__wid__] = serialized_widget
		return_promise.resolve(serialized_widget)

	def send[T](self, method_name: str, *args, **kwargs) -> Concurrent.ThreadedPromise[T] | Concurrent.Promise[T]:
		"""
		Sends an event to the remote window terminal
		:param method_name: The method or attribute name to retrieve or call
		:param args: The positional arguments to call with
		:param kwargs: The keyword arguments to call with
		:return: A promise
		"""

		if self.closed:
			raise IOError('Window is closed')
		elif not isinstance(method_name, str):
			raise Exceptions.InvalidArgumentException(WindowTerminal.send, 'method_name', type(method_name), (str,))

		try:
			_id: int

			if len(self.__closed_ids__):
				_id = self.__closed_ids__.pop()
			else:
				_id: int = self.__next_id__
				self.__next_id__ -= 1

			promise: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
			self.__events__[_id] = promise
			args = tuple(Struct.SerializableCallable(arg) if callable(arg) else arg for arg in args)
			kwargs = {kw:(Struct.SerializableCallable(arg) if callable(arg) else arg) for kw, arg in kwargs.items()}

			if self.__enabled__:
				self.__conn__.send((method_name, _id, args, kwargs))
			else:
				self.__pending_actions__.append((method_name, _id, args, kwargs))

			return promise
		except IOError as e:
			pseudo: Concurrent.Promise = Concurrent.Promise()
			pseudo.throw(e)
			return pseudo

	def update_key_events(self) -> Concurrent.ThreadedPromise[None]:
		"""
		Sends a request to update key events to the terminal
		:return: A promise
		"""

		return self.send('update_key_events()')

	def update_execute_pending_callbacks(self) -> Concurrent.ThreadedPromise[None]:
		"""
		Sends a request to update scheduled callbacks
		:return: A promise
		"""

		return self.send('update_execute_pending_callbacks()')

	### Standard methods
	def begin(self) -> None:
		"""
		Starts the remote window terminal
		"""

		if self.__enabled__:
			raise ValueError('Window already enabled')

		self.__conn__.write(b'\x01')

		for pending in self.__pending_actions__:
			self.__conn__.send(pending)

		self.__pending_actions__.clear()
		self.__enabled__ = True
		self.__thread__.start()

	def close(self) -> None:
		"""
		Closes the remote window terminal and IPC pipe
		"""

		if not self.closed:
			self.__enabled__ = False

			if self.__thread__ is not None:
				self.__thread__.join()
				self.__thread__ = None
				self.send('__del__()').wait()
				self.__process__.wait()

			if not self.__conn__.closed:
				self.__conn__.close()

			if not self.__widget_pipe__.closed:
				self.__widget_pipe__.close()

	def end(self, exit_code: int = 0) -> Concurrent.ThreadedPromise[int]:
		"""
		Ends the remote window terminal
		:param exit_code: The exit code to return
		:return: A promise with the specified exit code
		"""

		return self.send('end()', exit_code)

	def putstr(self, msg: str | Struct.AnsiStr | Iterable.String, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., n: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[None]:
		"""
		Prints a string to the remote terminal
		:param msg: A string, String or Struct.AnsiStr instance
		:param x: The x coordinate or current x if not supplied
		:param y: The y coordinate or current y if not supplied
		:param n: ?
		:return: A promise
		:raises InvalidArgumentException: If 'msg' is not a string, String instance, or Struct.AnsiStr instance
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
		"""

		return self.send('cursor_flash()', flash_rate)

	def minimize(self) -> Concurrent.ThreadedPromise[None]:
		"""
		Minimizes the window
		:return: A promise
		"""

		return self.send('minimize()')

	def restore(self) -> Concurrent.ThreadedPromise[None]:
		"""
		Restores the window
		:return: A promise
		"""

		return self.send('restore()')

	def set_focus(self, widget: Widgets.MyWidget | int | None) -> Concurrent.ThreadedPromise[None]:
		"""
		Sets focus on a specific widget or clears focus if None
		:param widget: The widget to focus or None to clear focus
		:raises InvalidArgumentException: If 'widget' is not a Widget instance
		:raises ValueError: If the widget's handling terminal is not this terminal
		"""

		return self.send('set_focus()', widget.id if isinstance(widget, Widgets.MyWidget) else widget)

	def erase_refresh(self, flag: bool) -> Concurrent.ThreadedPromise[None]:
		"""
		:param flag: Whether this terminal will fully erase the terminal before the next draw
		:return: A promise
		"""

		return self.send('erase_refresh()', flag)

	def ungetch(self, key: int) -> Concurrent.ThreadedPromise[None]:
		"""
		Appends a key to this terminal's event queue
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

	def fullscreen(self, flag: typing.Optional[bool] = ...) -> Concurrent.ThreadedPromise[typing.Optional[bool]]:
		"""
		Sets or gets the fullscreen status of this terminal's window
		:param flag: Whether to be fullscreen or unset to get current fullscreen
		:return: A promise with fullscreen status if 'flag' is unset, otherwise None
		"""

		return self.send('fullscreen()', flag)

	def getch(self) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
		"""
		Reads the next key code from this terminal's event queue
		:return: A promise with the next key code or None if no event is waiting
		"""

		return self.send('getch()')

	def peekch(self) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
		"""
		Peeks the next key code from this terminal's event queue
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

	def update_type(self, update_type: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
		"""
		Gets or sets this terminal's update type
		:param update_type: The update type (see Enums.WINUPDATE for a list of possible types)
		:return: A promise with the current update type if 'update_type' is unset otherwise None
		:raises InvalidArgumentException: If 'update_type' is not an integer
		:raises ValueError: If 'update_type' is not a valid update type
		"""

		return self.send('update_type()', update_type)

	def scroll_speed(self, scroll: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
		"""
		Gets or sets the terminal's scrolling speed in lines per scroll button
		If the mouse scrolls once, this terminal will scroll 'scroll' lines
		:param scroll: The number of lines to scroll per scroll button press
		:return: A promise with the scroll speed if 'scroll' is unset otherwise None
		:raises InvalidArgumentException: If 'scroll' is not an integer
		"""

		return self.send('scroll_speed()', scroll)

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

		__threaded = kwargs['__threaded'] if '__threaded' in kwargs else __threaded
		del kwargs['__threaded']
		return self.send('after()', ticks, callback, *args, __threaded=__threaded, **kwargs)

	def tab_size(self, size: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[typing.Optional[int]]:
		"""
		Gets or sets this terminal's tab size
		Tab will equal the space character times this value
		:param size: The tab size in characters
		:return: A promise with the current tab size if 'size' is unset otherwise None
		:raises InvalidArgumentException: If 'size' is not an integer
		:raises ValueError: If 'size' is less than 0
		"""

		return self.send('tab_size()', size)

	def cursor(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[typing.Optional[tuple[int, int]]]:
		"""
		Gets or sets the terminal's current cursor position
		:param x: The new cursor x position
		:param y: The new cursor y position
		:return: A promise with the current cursor position if 'x' and 'y' are unset otherwise None
		"""

		return self.send('cursor()', x, y)

	def scroll(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[typing.Optional[tuple[int, int]]]:
		"""
		Gets or sets the terminal's current scroll offset
		:param x: The new scroll x offset
		:param y: The new scroll y offset
		:return: A promise with the current scroll offset if 'x' and 'y' are unset otherwise None
		"""

		return self.send('scroll()', x, y)

	def size(self, cols: typing.Optional[int] = ..., rows: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[typing.Optional[tuple[int, int]]]:
		"""
		Gets or sets the terminal's current size in characters
		:param cols: The new terminal width
		:param rows: The new terminal height
		:return: A promise with the current width and height if 'cols' and 'rows' are unset otherwise None
		"""

		return self.send('size()', cols, rows)

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
		Converts the specified scroll independent coordinate into true terminal coordinates
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
		Converts the specified true terminal coordinate into scroll independent coordinates
		:param x: The true x coordinate
		:param y: The true y coordinate
		:return: A promise with the scroll independent coordinates
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		return self.send('from_fixed()', x, y)

	def getline(self, replace_char: typing.Optional[str | Struct.AnsiStr | Iterable.String] = ..., prompt: typing.Optional[str | Struct.AnsiStr | Iterable.String] = '', x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise[str]:
		"""
		Pauses terminal execution and reads a line from the user
		For standard input without pausing, add an 'Entry' widget
		:param replace_char: The character to replace entered characters with (usefull for passwords or hidden entries)
		:param prompt: The prompt to display
		:param x: The x position to display at
		:param y: The y position to display at
		:return: A promise with the entered string
		:raises InvalidArgumentException: If 'replace_char' is not a string, Struct.AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'prompt' is not a string, Struct.AnsiStr instance, or String instance
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		:raises ValueError: If 'replace_char' is not a single character
		"""

		return self.send('getline()', replace_char, prompt, x, y)

	def font(self, font: typing.Optional[Struct.Font] = ...) -> Concurrent.ThreadedPromise[typing.Optional[Struct.Font]]:
		"""
		WINDOWS ONLY
		Gets or sets the terminal's current font
		:param font: The Struct.Font instance to set
		:return: A promise with the current Struct.Font instance if 'font' is unset otherwise None
		:raises InvalidArgumentException: If 'font' is not a Struct.Font instance
		:raises RuntimeError: If system failed to get or set font
		"""

		return self.send('font()', font)

	def get_topmost_child_at(self, x: int, y: int) -> Concurrent.ThreadedPromise[typing.Optional[Widgets.MyWidget]]:
		"""
		Gets the topmost widget at the specified coordinates
		:param x: The x coordinate to check
		:param y: The y coordinate to check
		:return: A promise with the topmost widget or None if no widget exists
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		return self.send('get_topmost_child_at()', x, y)

	def get_focus(self) -> Concurrent.ThreadedPromise[typing.Optional[Widgets.MyWidget]]:
		"""
		:return: A promise with the widget with focus or None if no widget has focus
		"""

		return self.send('get_focus()')

	def active_subterminal(self) -> Concurrent.ThreadedPromise[typing.Optional[Widgets.MySubTerminal]]:
		"""
		:return: A promise with the sub-terminal with focus or None if no sub-terminal is active
		"""

		return self.send('active_subterminal()')

	def get_widget(self, _id: int) -> Concurrent.ThreadedPromise[typing.Type[Widgets.MyWidget]]:
		"""
		Gets the widget with the specified ID
		:param _id: The widget ID
		:return: A promise with the widget
		:raises InvalidArgumentException: If '_id' is not an integer
		:raises KeyError: If no widget with the specified ID exists
		"""

		return self.send('get_widget()', _id)

	def get_sub_terminal(self, _id: int) -> Concurrent.ThreadedPromise[Widgets.MySubTerminal]:
		"""
		Gets the sub-terminal with the specified ID
		:param _id: The sub-terminal ID
		:return: A promise with the sub-terminal
		:raises InvalidArgumentException: If '_id' is not an integer
		:raises KeyError: If no sub-terminal with the specified ID exists
		"""

		return self.send('get_sub_terminal()', _id)

	def get_children_at(self, x: int, y: int) -> Concurrent.ThreadedPromise[tuple[Widgets.MyWidget, ...]]:
		"""
		Gets all widgets or sub-terminals at the specified coordinates
		:param x: The x coordinate to check
		:param y: The y coordinate to check
		:return: A promise with all widgets or sub-terminals overlapping the specified coordinates
		:raises InvalidArgumentException: If 'x' is not an integer
		:raises InvalidArgumentException: If 'y' is not an integer
		"""

		return self.send('get_children_at()', x, y)

	def widgets(self) -> Concurrent.ThreadedPromise[tuple[Widgets.MyWidget, ...]]:
		"""
		:return: A promise with all widgets in this terminal
		"""

		return self.send('widgets()')

	def subterminals(self) -> Concurrent.ThreadedPromise[tuple[Widgets.MySubTerminal, ...]]:
		"""
		:return: A promise with all sub-terminals in this terminal
		"""

		return self.send('subterminals()')

	def children(self) -> Concurrent.ThreadedPromise[dict[int, Widgets.MyWidget | WindowTerminal]]:
		"""
		:return: A promise with all widgets, sub-terminals, and windows in this terminal
		"""

		return self.send('children()')

	### Widget methods
	def add_button(self, x: int, y: int, width: int, height: int, text: str, *, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_NONE,
				   border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
				   color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[Widgets.MyWidget, str, ...], None]] = ...,
				   on_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...,
				   on_mouse_enter: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.MyWidget, Struct.MouseInfo], None]] = ...,
				   on_tick: typing.Optional[typing.Callable[[Widgets.MyWidget, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.MyWidget], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyButton.MySerializedButton]:
		"""
		Adds a new button widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param text: Display text
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the Enums.WORDWRAP_ enums)
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the button widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyButton.MySerializedButton] = self.send('add_button()', x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
												border=border, highlight_border=highlight_border, active_border=active_border,
												color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MyButton.MySerializedButton] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_toggle_button(self, x: int, y: int, width: int, height: int, text: str | Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_NONE,
						  border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
						  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
						  callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
						  on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
						  on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
						  on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyToggleButton.MySerializedToggleButton]:
		"""
		Adds a new toggle button widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param text: Display text
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the Enums.WORDWRAP_ enums)
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the button widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyToggleButton.MySerializedToggleButton] = self.send('add_toggle_button()', x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MyToggleButton.MySerializedToggleButton] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str | Struct.AnsiStr | Iterable.String = '', active_text: str | Struct.AnsiStr | Iterable.String = 'X',
					 border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
					 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
					 on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
					 on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
					 on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., on_checked: typing.Optional[typing.Callable[[[Widgets.MyWidget], bool], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyCheckbox.MySerializedCheckbox]:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:param on_checked: The callback to call when the checkbox's checked state changes this widget and the widget's current state as arguments
		:return: A promise with the checkbox button widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyCheckbox.MySerializedCheckbox] = self.send('add_checkbox()', x, y, z_index=z_index, text=text, active_text=active_text,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close, on_checked=on_checked)
		rp: Concurrent.ThreadedPromise[Widgets.MyCheckbox.MySerializedCheckbox] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_inline_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str | Struct.AnsiStr | Iterable.String = '', active_text: str | Struct.AnsiStr | Iterable.String = 'X',
							border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
							color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
							callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
							on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
							on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
							on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., on_checked: typing.Optional[typing.Callable[[[Widgets.MyWidget], bool], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyInlineCheckbox.MySerializedInlineCheckbox]:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:param on_checked: The callback to call when the checkbox's checked state changes this widget and the widget's current state as arguments
		:return: A promise with the checkbox button widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyInlineCheckbox.MySerializedInlineCheckbox] = self.send('add_inline_checkbox()', x, y, z_index=z_index, text=text, active_text=active_text,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close, on_checked=on_checked)
		rp: Concurrent.ThreadedPromise[Widgets.MyInlineCheckbox.MySerializedInlineCheckbox] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_radial_spinner(self, x: int, y: int, *, z_index: int = 0, phases: typing.Iterable[str | Struct.AnsiStr | Iterable.String] = ('--', '\\', '|', '/'), bg_phase_colors: typing.Optional[Enums.Color_T] | typing.Iterable[typing.Optional[Enums.Color_T]] = ..., fg_phase_colors: typing.Optional[Enums.Color_T] | typing.Iterable[typing.Optional[Enums.Color_T]] = Struct.Color(0xFFFFFF),
						   callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
						   on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
						   on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
						   on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyRadialSpinner.MySerializedRadialSpinner]:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the radial spinner widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyRadialSpinner.MySerializedRadialSpinner] = self.send('add_radial_spinner()', x, y, z_index=z_index, phases=phases, bg_phase_colors=bg_phase_colors, fg_phase_colors=fg_phase_colors,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MyRadialSpinner.MySerializedRadialSpinner] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_horizontal_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, step: float = 1, fill_char: str | Struct.AnsiStr | Iterable.String = '|', _max: float = 10, _min: float = 0, on_input: typing.Callable[[Widgets.MyHorizontalSlider], None] = ...,
							  border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
							  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
							  callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
							  on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
							  on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
							  on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyHorizontalSlider.MySerializedHorizontalSlider]:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the horizontal slider widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyHorizontalSlider.MySerializedHorizontalSlider] = self.send('add_horizontal_slider()', x, y, width, height, z_index=z_index, step=step, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MyHorizontalSlider.MySerializedHorizontalSlider] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_vertical_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Struct.AnsiStr | Iterable.String = '=', _max: float = 10, _min: float = 0, on_input: typing.Callable[[Widgets.MyVerticalSlider], None] = ...,
							border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
							color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
							callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
							on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
							on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
							on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyVerticalSlider.MySerializedVerticalSlider]:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the vertical slider widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyVerticalSlider.MySerializedVerticalSlider] = self.send('add_vertical_slider()', x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MyVerticalSlider.MySerializedVerticalSlider] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_horizontal_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Struct.AnsiStr | Iterable.String = '|', _max: float = 10, _min: float = 0,
									border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
									color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
									callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
									on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
									on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
									on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyHorizontalProgressBar.MySerializedHorizontalProgressBar]:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the horizontal progress bar widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyHorizontalProgressBar.MySerializedHorizontalProgressBar] = self.send('add_horizontal_progress_bar()', x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MyHorizontalProgressBar.MySerializedHorizontalProgressBar] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_vertical_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str | Struct.AnsiStr | Iterable.String = '=', _max: float = 10, _min: float = 0,
								  border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
								  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
								  callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
								  on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
								  on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
								  on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyVerticalProgressBar.MySerializedVerticalProgressBar]:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the vertical progress bar widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyVerticalProgressBar.MySerializedVerticalProgressBar] = self.send('add_vertical_progress_bar()', x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MyVerticalProgressBar.MySerializedVerticalProgressBar] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_text(self, x: int, y: int, width: int, height: int, text: str | Struct.AnsiStr | Iterable.String, *, z_index: int = 0, justify: int = Enums.NORTH_WEST, word_wrap: int = Enums.WORDWRAP_NONE,
				 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
				 on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
				 on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
				 on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyText.MySerializedText]:
		"""
		Adds a new text widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param text: Display text
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the Enums.WORDWRAP_ enums)
		:param color_bg: The background color
		:param color_fg: The foreground (text) color
		:param highlight_color_bg: The background color when mouse is hovering
		:param highlight_color_fg: The foreground color when mouse is hovering
		:param active_color_bg: The background color when button is pressed
		:param active_color_fg: The foreground color when button is pressed
		:param callback: The general callback to call taking the widget, event, and event info. General callback will be called for every event listed below
		:param on_focus: The callback to call once this widget gains focus taking this widget as an argument
		:param off_focus: The callback to call once this widget loses focus taking this widget as an argument
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the text widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyText.MySerializedText] = self.send('add_text()', x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MyText.MySerializedText] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_dropdown(self, x: int, y: int, width: int, height: int, choices: tuple[str | Struct.AnsiStr | Iterable.String, ...], *, display_count: int | None = None, allow_scroll_rollover: bool = False, z_index: int = 0, justify: int = Enums.CENTER, word_wrap: int = Enums.WORDWRAP_WORD, on_select: typing.Optional[typing.Callable[[[Widgets.MyWidget]], bool | None]] = ...,
					 border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
					 color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
					 on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
					 on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
					 on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyDropdown.MySerializedDropdown]:
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
		:param word_wrap: The word wrapping type (one of the Enums.WORDWRAP_ enums)
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the dropdown widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyDropdown.MySerializedDropdown] = self.send('add_dropdown()', x, y, width, height, choices, display_count=display_count, allow_scroll_rollover=allow_scroll_rollover, z_index=z_index, justify=justify, word_wrap=word_wrap, on_select=on_select,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MyDropdown.MySerializedDropdown] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_entry(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, word_wrap: int = Enums.WORDWRAP_WORD, justify: int = Enums.NORTH_WEST, replace_chars: str | Struct.AnsiStr | Iterable.String = '', placeholder: typing.Optional[str | Struct.AnsiStr | Iterable.String] = ..., cursor_blink_speed: int = 0, on_text: typing.Optional[typing.Callable[[Widgets.MyEntry, bool], bool | str | Struct.AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[Widgets.MyEntry, str | Struct.AnsiStr, int], bool | str | Struct.AnsiStr | None]] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., color_fg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_fg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_fg: typing.Optional[Enums.Color_T] = ...,
				  callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
				  on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
				  on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
				  on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyEntry.MySerializedEntry]:
		"""
		Adds a new entry widget to this terminal
		:param x: X position
		:param y: Y position
		:param width: Width in characters
		:param height: Height in characters
		:param z_index: Z-index, higher is drawn last
		:param justify: Text justification (one of the cardinal direction enums)
		:param word_wrap: The word wrapping type (one of the Enums.WORDWRAP_ enums)
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the entry widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyEntry.MySerializedEntry] = self.send('add_entry()', x, y, width, height, z_index=z_index, word_wrap=word_wrap, justify=justify, replace_chars=replace_chars, placeholder=placeholder, cursor_blink_speed=cursor_blink_speed, on_text=on_text, on_input=on_input,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MyEntry.MySerializedEntry] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_image(self, x: int, y: int, width: int, height: int, image: str | Struct.AnsiStr | Iterable.String | numpy.ndarray | PIL.Image.Image, *, z_index: int = 0, use_subpad: bool = True, div: typing.Optional[int] = ...,
				  border: typing.Optional[Struct.BorderInfo] = ..., highlight_border: typing.Optional[Struct.BorderInfo] = ..., active_border: typing.Optional[Struct.BorderInfo] = ...,
				  color_bg: typing.Optional[Enums.Color_T] = ..., highlight_color_bg: typing.Optional[Enums.Color_T] = ..., active_color_bg: typing.Optional[Enums.Color_T] = ...,
				  callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
				  on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
				  on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
				  on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MyImage.MySerializedImage]:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the image widget
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MyImage.MySerializedImage] = self.send('add_image()', x, y, width, height, image, z_index=z_index, div=div, use_subpad=use_subpad,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MyImage.MySerializedImage] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_sub_terminal(self, x: int, y: int, width: int, height: int, *, title: typing.Optional[str | Struct.AnsiStr | Iterable.String] = ..., z_index: int = 0, transparent: bool = False,
						 border: Struct.BorderInfo = ..., highlight_border: Struct.BorderInfo = ..., active_border: Struct.BorderInfo = ...,
						 callback: typing.Optional[typing.Callable[[[Widgets.MyWidget], str, ...], None]] = ...,
						 on_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ..., off_focus: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...,
						 on_mouse_enter: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[[Widgets.MyWidget], Struct.MouseInfo], None]] = ...,
						 on_tick: typing.Optional[typing.Callable[[[Widgets.MyWidget], int], None]] = ..., on_close: typing.Optional[typing.Callable[[[Widgets.MyWidget]], None]] = ...) -> Concurrent.ThreadedPromise[Widgets.MySubTerminal.MySerializedSubTerminal]:
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
		:param on_mouse_enter: The callback to call once the mouse enters this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_leave: The callback to call once the mouse leaves this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_press: The callback to call once the mouse presses this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_release: The callback to call once the mouse releases this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_mouse_click: The callback to call once the mouse clicks this widget taking this widget and the Struct.MouseInfo instance as arguments
		:param on_tick: The callback to call once every tick taking this widget and the widget's current tick as arguments
		:param on_close: The callback to call once the widget is destroyed taking this widget as an argument
		:return: A promise with the sub-terminal
		"""

		promise: Concurrent.ThreadedPromise[Widgets.MySubTerminal.MySerializedSubTerminal] = self.send('add_sub_terminal()', x, y, width, height, title, z_index=z_index, transparent=transparent,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise[Widgets.MySubTerminal.MySerializedSubTerminal] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_widget[T: Widgets.MyWidget](self, cls: type[T], *args, z_index: int = 0, **kwargs) -> Concurrent.ThreadedPromise[Widgets.MyWidget.MySerializedWidget]:
		"""
		Adds a new widget to this terminal
		This is for use with custom widget classes extending from the Widget class
		:param cls: The widget class to instantiate
		:param args: The positional arguments to pass into the constructor
		:param z_index: Z-index, higher is drawn last
		:param kwargs: The keyword arguments to pass into the constructor
		:return: A promise with the new widget
		"""

		assert issubclass(cls, Widgets.MyWidget)
		promise: Concurrent.ThreadedPromise[Widgets.MyWidget.MySerializedWidget] = self.send('add_widget()', cls, *args, z_index=z_index, **kwargs)
		rp: Concurrent.ThreadedPromise[Widgets.MyWidget.MySerializedWidget] = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	### Properties
	@property
	def enabled(self) -> Concurrent.ThreadedPromise:
		return self.send('enabled')

	@property
	def minimized(self) -> Concurrent.ThreadedPromise:
		return self.send('minimized')

	@property
	def exit_code(self) -> Concurrent.ThreadedPromise:
		return self.send('exit_code')

	@property
	def exit_reason(self) -> Concurrent.ThreadedPromise:
		return self.send('exit_reason')

	@property
	def current_tick(self) -> Concurrent.ThreadedPromise:
		return self.send('current_tick')

	@property
	def mouse(self) -> Concurrent.ThreadedPromise:
		return self.send('mouse')

	@property
	def selected_subterminal(self) -> Concurrent.ThreadedPromise:
		return self.send('selected_subterminal')

	@property
	def default_bg(self) -> Concurrent.ThreadedPromise:
		return self.send('default_bg')

	@property
	def default_fg(self) -> Concurrent.ThreadedPromise:
		return self.send('default_fg')

	@property
	def focused(self) -> Concurrent.ThreadedPromise:
		return self.send('focused')

	@property
	def closed(self) -> bool:
		return not self.__enabled__ and (self.__conn__.closed or self.__thread__ is None or not self.__psutil_process__.is_running())

	@property
	def remote_exit_reason(self) -> None | BaseException:
		return self.__remote_exit_reason__