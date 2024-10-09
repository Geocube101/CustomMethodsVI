from __future__ import annotations

import curses
import _curses
import curses.ascii
import ctypes
import ctypes.wintypes
import datetime
import sys
import typing
import types
import time
import math
import pyautogui
import traceback
import numpy
import PIL.Image
import locale
import os
import threading
import queue
import subprocess
import base64
import pickle
import psutil
import signal
import pywintypes

import win32con
import win32gui
import win32console

import CustomMethodsVI.Terminal.Widgets as Widgets
import CustomMethodsVI.Exceptions as Exceptions
import CustomMethodsVI.Concurrent as Concurrent
import CustomMethodsVI.FileSystem as FileSystem
import CustomMethodsVI.Connection as Connection

from CustomMethodsVI.Terminal.Enums import *
from CustomMethodsVI.Terminal.Struct import Color, BorderInfo, MouseInfo, FontInfoEx, Font, WidgetStruct, AnsiStr, SerializableCallable
from CustomMethodsVI.Iterable import SpinList


class Terminal:
	class ScheduledCallback:
		def __init__(self, ticks: int, threaded: bool, callback: typing.Callable, args: tuple, kwargs: dict):
			assert ticks >= 0, 'Ticks remaining must be greater than or equal to zero'
			assert callable(callback), 'Callback must be callable'

			self.ticks: int = ticks
			self.threaded: bool = threaded
			self.callback: typing.Callable = callback
			self.args: tuple = args
			self.kwargs: dict = kwargs

	### Magic methods
	def __init__(self, width: typing.Optional[int] = ..., height: typing.Optional[int] = ..., font: typing.Optional[Font] = ...):
		os.system('chcp 65001')
		kernel32 = ctypes.WinDLL('Kernel32.dll')
		stdout = kernel32.GetStdHandle(-11)

		if not stdout:
			raise RuntimeError('Failed to get STDOUT handle')

		old_font: FontInfoEx = FontInfoEx()
		old_font.cbSize = ctypes.sizeof(FontInfoEx)
		res = kernel32.GetCurrentConsoleFontEx(stdout, False, ctypes.byref(old_font))

		if not res:
			raise RuntimeError('Failed to get font info')

		if font is not None and font is not ...:
			self.font(font)

		self.__old_font__: tuple[str, int, int, int, int] = (old_font.FaceName, old_font.dwFontSize.X, old_font.dwFontSize.Y, old_font.nFont, old_font.FontWeight)
		self.__widgets__: dict[int, dict[int, typing.Type[Widgets.WIDGET_T | Widgets.Widget]]] = {}
		self.__pages__: dict[int, dict[int, Widgets.SubTerminal]] = {}
		self.__windows__: dict[int, WindowTerminal] = {}
		self.__scheduled_callables__: dict[int, Terminal.ScheduledCallback] = {}
		self.__workers__: list[tuple[threading.Thread, threading.Event]] = []
		self.__worker_queue__: queue.Queue = queue.Queue()
		self.__previous_inputs__: list[str] = []
		self.__touched_cols_rows__: list[int] = [0, 0, 0, 0]

		self.__mouse_pos__: tuple[int, int] = (-1, -1)
		self.__screen_mouse_pos__: tuple[int, int] = (0, 0)
		self.__cursor__: tuple[int, int, int, int] = (0, 0, 0, 0)
		self.__enabled__: int | None = -1
		self.__full_end__: int | None = None
		self.__exit_reason__: None | BaseException = None
		self.__fullscreen__: bool = False
		self.__iconified__: bool = False
		self.__erase_refresh__: bool = True
		self.__root__ = curses.initscr()
		self.__scroll__: list[int, int] = [0, 0]
		self.__last_mouse_info__: MouseInfo = MouseInfo(-1, 0, 0, 0, 0)
		self.__event_queue__: SpinList[int] = SpinList(10)
		self.__global_event_queue__: SpinList[int] = SpinList(10)
		self.__colors__: dict[int, int] = {}
		self.__color_usage__: dict[int, int] = {}
		self.__color_times__: dict[int, float] = {}
		self.__color_pairs__: dict[tuple[int, int], int] = {}
		self.__color_pair_usage__: dict[int, int] = {}
		self.__color_pair_times__: dict[int, float] = {}
		self.__max_workers__: int = 10
		self.__update_times__: SpinList[tuple[float, float]] = SpinList(50)
		self.__tick__: int = 0
		self.__auto_scroll__: int = 10
		self.__tab_size__: int = 4
		self.__active_page__: Widgets.SubTerminal | None = None
		self.__update_type__: int = WINUPDATE_ALL
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

		for i in range(self.__highest_default_color__):
			try:
				r, g, b = curses.color_content(i)
				color: Color = Color.fromcursesrgb(r, g, b)

				if color not in self.__colors__:
					self.__colors__[color.color] = i
			except _curses.error:
				self.__highest_default_color__ = i
				break

		for i in range(curses.COLOR_PAIRS):
			fg, bg = curses.pair_content(i)
			r, g, b = curses.color_content(fg)
			color: Color = Color.fromcursesrgb(r, g, b)

			if color.color not in self.__colors__:
				self.__colors__[color.color] = fg

			r, g, b = curses.color_content(bg)
			color: Color = Color.fromcursesrgb(r, g, b)

			if color.color not in self.__colors__:
				self.__colors__[color.color] = bg

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
	def __worker__(self, complete: threading.Event):
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

	def __mainloop__(self, tick_rate: float, factor: float, rollover: int, before_draw: typing.Callable, after_draw: typing.Callable) -> None:
		this_win = win32console.GetConsoleWindow()
		foreground = win32gui.GetForegroundWindow()
		t1: int = time.perf_counter_ns()
		do_update: bool = True
		self.update_execute_pending_callbacks()
		self.update_key_events()

		if this_win == foreground:
			self.__iconified__ = False

		if (self.__update_type__ & WINUPDATE_FOCUS) != 0:
			do_update = do_update and this_win == foreground
		if (self.__update_type__ & WINUPDATE_MOUSEIN) != 0:
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
		closed_windows: tuple[int] = tuple(_id for _id, window in self.__windows__.items() if window.closed)

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
		for z_index, widgets in self.__widgets__.items():
			for wid, widget in tuple(widgets.items()):
				if wid in widgets:
					widget.close()

		for _id, window in self.__windows__.items():
			if not window.closed:
				try:
					window.end(self.__enabled__)
				except pywintypes.error:
					pass

		curses.endwin()
		kernel32 = ctypes.WinDLL("Kernel32.dll")
		stdout = kernel32.GetStdHandle(-11)

		if not stdout:
			return -2

		font: FontInfoEx = FontInfoEx()
		font.cbSize = ctypes.sizeof(FontInfoEx)
		font.FaceName = self.__old_font__[0]
		font.dwFontSize.X = self.__old_font__[1]
		font.dwFontSize.Y = self.__old_font__[2]
		font.nFont = self.__old_font__[3]
		font.FontWeight = self.__old_font__[4]
		res = kernel32.SetCurrentConsoleFontEx(stdout, False, ctypes.byref(font))
		self.__enabled__ = 0 if self.__enabled__ is None else self.__enabled__
		self.__full_end__ = self.__enabled__ if res else -2
		return self.__full_end__

	def update_key_events(self) -> None:
		ch: int = self.__root__.getch()
		active: Widgets.SubTerminal = ...

		if ch == curses.KEY_MOUSE:
			lx, ly, lz = self.__last_mouse_info__.position
			_id, _, _, _, bstate = curses.getmouse()
			self.__last_mouse_info__ = MouseInfo(_id, lx, ly, lz, bstate)
			topmost: Widgets.WIDGET_T = self.get_topmost_child_at(lx, ly)

			if topmost is not None:
				topmost.focus()

			if self.__last_mouse_info__.left_pressed or self.__last_mouse_info__.middle_pressed or self.__last_mouse_info__.right_pressed:
				if isinstance(topmost, Widgets.SubTerminal):
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
			self.__last_mouse_info__ = MouseInfo(self.__last_mouse_info__.mouse_id, self.__mouse_pos__[0], self.__mouse_pos__[1], 0, old_bstate)
			return

		if old_bstate != self.__last_mouse_info__.bstate:
			_id, x, y, z, _ = self.__last_mouse_info__
			self.__last_mouse_info__ = MouseInfo(_id, x, y, z, old_bstate)

	def update_execute_pending_callbacks(self) -> None:
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
		self.__enabled__ = exit_code

	def putstr(self, msg: str | AnsiStr, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., n: typing.Optional[int] = ...) -> None:
		if not isinstance(msg, (str, AnsiStr)):
			raise Exceptions.InvalidArgumentException(Terminal.putstr, 'msg', type(msg), (str, AnsiStr))
		elif x is not ... and x is not None and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(Terminal.putstr, 'x', type(x), (int,))
		elif y is not ... and y is not None and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(Terminal.putstr, 'y', type(y), (int,))
		elif n is not ... and n is not None and not isinstance(n, int):
			raise Exceptions.InvalidArgumentException(Terminal.putstr, 'n', type(n), (int,))

		n = None if n is None or n is ... else int(n)

		if n is not None and n <= 0:
			return

		msg = msg if isinstance(msg, AnsiStr) else AnsiStr(msg)
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
		for alloc in self.__widgets__.values():
			if _id in alloc:
				del alloc[_id]
				break

	def del_sub_terminal(self, _id: int) -> None:
		for alloc in self.__pages__.values():
			if _id in alloc:
				del alloc[_id]
				break

	def del_window(self, _id: int, exit_code: int = 0) -> None:
		if _id in self.__windows__:
			self.__windows__[_id].end(exit_code)
			del self.__windows__[_id]

	def cancel(self, _id: int) -> None:
		if _id in self.__scheduled_callables__:
			del self.__scheduled_callables__[_id]

	def cursor_visibility(self, visibility: int) -> None:
		cx, cy, _, rt = self.__cursor__
		self.__cursor__ = (cx, cy, visibility, rt)

	def cursor_flash(self, flash_rate: int) -> None:
		cx, cy, vs, _ = self.__cursor__
		self.__cursor__ = (cx, cy, vs, flash_rate)

	def minimize(self) -> None:
		self.__iconified__ = True
		hwnd: int = win32console.GetConsoleWindow()
		win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

	def restore(self) -> None:
		hwnd: int = win32console.GetConsoleWindow()
		win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
		self.__iconified__ = False

	def set_focus(self, widget: Widgets.Widget | None) -> None:
		if widget is not None and not isinstance(widget, Widgets.Widget):
			raise Exceptions.InvalidArgumentException(Terminal.set_focus, 'widget', type(widget), (Widgets.Widget,))
		elif widget is None or widget.parent is self:
			child: Widgets.Widget
			old_page: Widgets.SubTerminal = self.__active_page__

			if widget is not None:
				subterminals: tuple[Widgets.SubTerminal, ...] = self.subterminals()

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
		self.__erase_refresh__ = bool(flag)

	def ungetch(self, key: int) -> None:
		self.__event_queue__.append(int(key))

	def ungetgch(self, key: int) -> None:
		self.__global_event_queue__.append(int(key))

	def reset_colors(self) -> None:
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

	def fullscreen(self, flag: typing.Optional[bool] = ...) -> bool | None:
		if flag is None or flag is ...:
			return self.__fullscreen__
		else:
			self.__fullscreen__ = flag
			hwnd: int = win32console.GetConsoleWindow()

			if flag:
				win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
			else:
				win32gui.ShowWindow(hwnd, win32con.SW_SHOWDEFAULT)

	def getch(self) -> int | None:
		return self.__event_queue__.pop(0) if len(self.__event_queue__) else None

	def peekch(self) -> int | None:
		return self.__event_queue__[-1] if len(self.__event_queue__) else None

	def getgch(self) -> int | None:
		return self.__global_event_queue__.pop(0) if len(self.__global_event_queue__) else None

	def peekgch(self) -> int | None:
		return self.__global_event_queue__[-1] if len(self.__global_event_queue__) else None

	def update_type(self, update_type: typing.Optional[int] = ...) -> int | None:
		if update_type is None or update_type is ...:
			return self.__update_type__
		else:
			self.__update_type__ = int(update_type)

	def scroll_speed(self, scroll: typing.Optional[int] = ...) -> int | None:
		if scroll is None or scroll is ...:
			return self.__auto_scroll__
		else:
			self.__auto_scroll__ = int(scroll)

	def first_empty_row(self) -> int:
		return self.__touched_cols_rows__[2]

	def last_empty_row(self) -> int:
		return self.__touched_cols_rows__[3]

	def first_empty_column(self) -> int:
		return self.__touched_cols_rows__[0]

	def last_empty_column(self) -> int:
		return self.__touched_cols_rows__[1]

	def get_color(self, color: Color | int) -> int:
		if isinstance(color, int):
			return int(color)
		elif not isinstance(color, Color):
			raise Exceptions.InvalidArgumentException(Terminal.get_color, 'color', type(color), (Color, types.NoneType))
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

	def get_color_pair(self, fg: Color | int, bg: Color | int) -> int:
		fg: int = self.get_color(fg)
		bg: int = self.get_color(bg)
		colors: tuple[int, int] = (fg, bg)

		if colors in self.__color_pairs__:
			color_pair: int = self.__color_pairs__[colors]
			self.__color_pair_usage__[color_pair] = self.__color_pair_usage__[color_pair] + 1 if color_pair in self.__color_pair_usage__ else 1
			return color_pair
		else:
			color_pair: int = curses.COLOR_PAIRS - 1 - len(self.__color_pairs__)

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
		__threaded = kwargs['__threaded'] if '__threaded' in kwargs else __threaded
		del kwargs['__threaded']
		struct: Terminal.ScheduledCallback = Terminal.ScheduledCallback(ticks, __threaded, callback, args, kwargs)
		_id: int = id(struct)
		self.__scheduled_callables__[_id] = struct
		return _id

	def mainloop(self, tps: int, before_draw: typing.Optional[typing.Callable] = ..., after_draw: typing.Optional[typing.Callable] = ...) -> int:
		if self.__enabled__ is None:
			raise RuntimeError('Already enabled')

		assert isinstance(tps, int) and tps > 0, 'Invalid TPS'
		tick_rate: float = 1 / int(tps)
		factor: float = 1 if tps <= 500 else 0.85 if tps <= 1000 else 0
		rollover: int = 0xFFFFFFFFFFFFFFFF
		rollover = rollover - (rollover % tps)
		self.__enabled__ = None
		self.__exit_reason__ = None
		self.__full_end__ = None

		kernel32 = ctypes.WinDLL('Kernel32.dll')
		stdout = kernel32.GetStdHandle(-11)
		font: FontInfoEx = FontInfoEx()
		font.cbSize = ctypes.sizeof(FontInfoEx)
		font.FaceName = 'Unifont'
		font.dwFontSize.X = 8
		font.dwFontSize.Y = 16
		res = kernel32.SetCurrentConsoleFontEx(stdout, False, ctypes.byref(font))
		locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

		if not res:
			raise RuntimeError('Failed to set font info')

		if os.name == 'nt':
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
		while self.__full_end__ is None:
			time.sleep(1e-6)

		return self.__full_end__

	def tab_size(self, size: typing.Optional[int] = ...) -> int | None:
		if size is None or size is ...:
			return self.__tab_size__
		elif not isinstance(size, int):
			raise Exceptions.InvalidArgumentException(Terminal.tab_size, 'size', type(size), (int,))
		elif size < 0:
			raise ValueError('Tab size cannot be less than zero')
		else:
			self.__tab_size__ = int(size)

	def cursor(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> tuple[int, int] | None:
		if (x is None or x is ...) and (y is None or y is ...):
			return self.__cursor__[:2]
		elif x is not None and x is not ... and not isinstance(x, int):
			raise Exceptions.InvalidArgumentException(Terminal.cursor, 'x', type(x), (int,))
		elif y is not None and y is not ... and not isinstance(y, int):
			raise Exceptions.InvalidArgumentException(Terminal.cursor, 'y', type(y), (int,))
		else:
			sx, sy = self.__scroll__
			cy, cx = self.__root__.getyx()
			_, _, visibility, rate = self.__cursor__
			self.__cursor__ = ((cx if x is None or x is ... else int(x)) + sx, (cy if y is None or y is ... else int(y)) + sy, visibility, rate)

	def scroll(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> tuple[int, int] | None:
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

	def size(self, cols: typing.Optional[int] = ..., rows: typing.Optional[int] = ...) -> tuple[int, int] | None:
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
		sx, sy = self.__scroll__
		full: int = self.__root__.inch(x - sx, y - sy)
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

	def font(self, font: typing.Optional[Font] = ...) -> Font | None:
		kernel32 = ctypes.WinDLL('Kernel32.dll')
		stdout = kernel32.GetStdHandle(-11)

		if font is None or font is ...:
			current_font: FontInfoEx = FontInfoEx()
			current_font.cbSize = ctypes.sizeof(FontInfoEx)
			res = kernel32.GetCurrentConsoleFontEx(stdout, False, ctypes.byref(current_font))

			if not res:
				raise RuntimeError('Failed to get font info')

			return Font(current_font.FaceName, (current_font.dwFontSize.X, current_font.dwFontSize.Y), current_font.FontWeight)
		else:
			new_font: FontInfoEx = FontInfoEx()
			new_font.cbSize = ctypes.sizeof(FontInfoEx)
			new_font.FaceName = font.fontname
			new_font.dwFontSize.X = font.fontsize[0]
			new_font.dwFontSize.Y = font.fontsize[1]
			new_font.FontFamily = 54
			new_font.FontWeight = font.fontweight

			res = kernel32.SetCurrentConsoleFontEx(stdout, False, ctypes.byref(new_font))

			if not res:
				raise RuntimeError('Failed to set font info')

	def get_topmost_child_at(self, x: int, y: int) -> Widgets.Widget | None:
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

	def get_focus(self) -> Widgets.Widget | None:
		child: Widgets.Widget

		for child in (*self.widgets(), *self.subterminals()):
			if child.focused:
				return child

		return None

	def active_subterminal(self) -> Widgets.SubTerminal | None:
		page: Widgets.SubTerminal | None = self.__active_page__

		if page is None or page.hidden:
			return None

		while page.selected_subterminal is not None and not page.selected_subterminal.hidden:
			page = page.selected_subterminal

		return page

	def get_widget(self, _id: int) -> typing.Type[Widgets.WIDGET_T]:
		for z_index, widgets in self.__widgets__.items():
			if _id in widgets:
				return widgets[_id]

		raise KeyError(f'No such widget - {_id}')

	def get_sub_terminal(self, _id: int) -> Widgets.SubTerminal:
		for z_index, sub_terminals in self.__pages__.items():
			if _id in sub_terminals:
				return sub_terminals[_id]

		raise KeyError(f'No such terminal - {_id}')

	def get_window(self, _id: int) -> WindowTerminal:
		if _id in self.__windows__:
			return self.__windows__[_id]
		else:
			raise KeyError(f'No such window - {_id}')

	def get_children_at(self, x: int, y: int) -> tuple[Widgets.Widget, ...]:
		children: list[Widgets.Widget] = []

		for z_index in sorted(self.__pages__.keys(), reverse=True):
			for _id, widget in self.__pages__[z_index].items():
				if widget.has_coord(x, y):
					children.append(widget)

		for z_index in sorted(self.__widgets__.keys(), reverse=True):
			for _id, widget in self.__widgets__[z_index].items():
				if widget.has_coord(x, y):
					children.append(widget)

		return tuple(children)

	def widgets(self) -> tuple[Widgets.Widget]:
		ids: list[Widgets.Widget] = []

		for alloc in self.__widgets__.values():
			ids.extend(alloc.values())

		return tuple(ids)

	def subterminals(self) -> tuple[Widgets.SubTerminal]:
		ids: list[Widgets.SubTerminal] = []

		for alloc in self.__pages__.values():
			ids.extend(alloc.values())

		return tuple(ids)

	def windows(self) -> tuple[WindowTerminal]:
		return tuple(self.__windows__.values())

	def children(self) -> dict[int, Widgets.Widget | WindowTerminal]:
		children: dict[int, Widgets.Widget | WindowTerminal] = self.__windows__.copy()

		for alloc in self.__pages__.values():
			children.update(alloc)

		for alloc in self.__widgets__.values():
			children.update(alloc)

		return children

	### Widget methods
	def add_button(self, x: int, y: int, width: int, height: int, text: str, *, z_index: int = 0, justify: int = CENTER, word_wrap: int = WORDWRAP_NONE,
				   border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				   color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.Button:
		widget: Widgets.Button = Widgets.Button(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
												border=border, highlight_border=highlight_border, active_border=active_border,
												color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_toggle_button(self, x: int, y: int, width: int, height: int, text: str, *, z_index: int = 0, justify: int = CENTER, word_wrap: int = WORDWRAP_NONE,
						  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
						  color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
						  callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.ToggleButton:
		widget: Widgets.ToggleButton = Widgets.ToggleButton(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
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
					 color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.Checkbox:
		widget: Widgets.Checkbox = Widgets.Checkbox(self, x, y, z_index=z_index, text=text, active_text=active_text,
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
							color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
							callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.InlineCheckbox:
		widget: Widgets.InlineCheckbox = Widgets.InlineCheckbox(self, x, y, z_index=z_index, text=text, active_text=active_text,
																border=border, highlight_border=highlight_border, active_border=active_border,
																color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_radial_spinner(self, x: int, y: int, *, z_index: int = 0, phases: typing.Iterable[str] = ('--', '\\', '|', '/'), bg_phase_colors: typing.Optional[Color_T] | typing.Iterable[typing.Optional[Color_T]] = ..., fg_phase_colors: typing.Optional[Color_T] | typing.Iterable[typing.Optional[Color_T]] = Color(0xFFFFFF),
						   callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.RadialSpinner:
		widget: Widgets.RadialSpinner = Widgets.RadialSpinner(self, x, y, z_index=z_index, phases=phases, bg_phase_colors=bg_phase_colors, fg_phase_colors=fg_phase_colors,
															  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_horizontal_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str = '|', _max: float = 10, _min: float = 0, on_input: typing.Callable[[Widgets.HorizontalSlider], None] = ...,
							  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							  color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
							  callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.HorizontalSlider:
		widget: Widgets.HorizontalSlider = Widgets.HorizontalSlider(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
																	border=border, highlight_border=highlight_border, active_border=active_border,
																	color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																	callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_vertical_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str = '=', _max: float = 10, _min: float = 0, on_input: typing.Callable[[Widgets.VerticalSlider], None] = ...,
							border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
							callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.VerticalSlider:
		widget: Widgets.VerticalSlider = Widgets.VerticalSlider(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
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
							color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
							callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.HorizontalProgressBar:
		widget: Widgets.HorizontalProgressBar = Widgets.HorizontalProgressBar(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
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
							color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
							callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.VerticalProgressBar:
		widget: Widgets.VerticalProgressBar = Widgets.VerticalProgressBar(self, x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
																border=border, highlight_border=highlight_border, active_border=active_border,
																color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_text(self, x: int, y: int, width: int, height: int, text: str, *, z_index: int = 0, justify: int = NORTH_WEST, word_wrap: int = WORDWRAP_NONE,
				 color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.Text:
		widget: Widgets.Text = Widgets.Text(self, x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
											color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
											callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_dropdown(self, x: int, y: int, width: int, height: int, choices: tuple[str | AnsiStr, ...], *, display_count: int | None = None, allow_scroll_rollover: bool = False, z_index: int = 0, justify: int = CENTER, word_wrap: int = WORDWRAP_WORD, on_select: typing.Optional[typing.Callable[[Widgets.WIDGET_T], bool | None]] = ...,
				   border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				   color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.Dropdown:
		widget: Widgets.Dropdown = Widgets.Dropdown(self, x, y, width, height, choices, display_count=display_count, allow_scroll_rollover=allow_scroll_rollover, z_index=z_index, justify=justify, word_wrap=word_wrap, on_select=on_select,
												border=border, highlight_border=highlight_border, active_border=active_border,
												color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_entry(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, word_wrap: int = WORDWRAP_WORD, justify: int = NORTH_WEST, replace_chars: str = '', placeholder: typing.Optional[str | AnsiStr] = ..., cursor_blink_speed: int = 0, on_text: typing.Optional[typing.Callable[[Widgets.Entry, bool], bool | str | AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[Widgets.Entry, str | AnsiStr, int], bool | str | AnsiStr | None]] = ...,
				  color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
				  callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.Entry:
		widget: Widgets.Entry = Widgets.Entry(self, x, y, width, height, z_index=z_index, word_wrap=word_wrap, justify=justify, replace_chars=replace_chars, placeholder=placeholder, cursor_blink_speed=cursor_blink_speed, on_text=on_text, on_input=on_input,
											  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
											  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	def add_image(self, x: int, y: int, width: int, height: int, image: str | AnsiStr | numpy.ndarray | PIL.Image.Image, *, z_index: int = 0, use_subpad: bool = True, div: typing.Optional[int] = ...,
				   border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				   color_bg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.Image:
		widget: Widgets.Image = Widgets.Image(self, x, y, width, height, image, z_index=z_index, div=div, use_subpad=use_subpad,
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
						 callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Widgets.SubTerminal:
		terminal: Widgets.SubTerminal = Widgets.SubTerminal(self, x, y, width, height, title, z_index=z_index, transparent=transparent,
															border=border, highlight_border=highlight_border, active_border=active_border,
															callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		_id: int = id(terminal)

		if z_index in self.__pages__:
			self.__pages__[z_index][_id] = terminal
		else:
			self.__pages__[z_index] = {_id: terminal}

		return terminal

	def add_window(self, tps: int, width: typing.Optional[int] = ..., height: typing.Optional[int] = ..., before_draw: typing.Optional[typing.Callable] = ..., after_draw: typing.Optional[typing.Callable] = ..., font: typing.Optional[Font] = ...) -> WindowTerminal:
		window: WindowTerminal = WindowTerminal(tps, width, height, before_draw, after_draw, font)
		_id: int = id(window)
		self.__windows__[_id] = window

		if self.__enabled__ is None:
			window.begin()

		return window

	def add_widget(self, cls: typing.Type[Widgets.WIDGET_T], *args, z_index: int = 0, **kwargs) -> Widgets.WIDGET_T:
		assert issubclass(cls, Widgets.Widget)
		widget: Widgets.WIDGET_T = cls(self, *args, **kwargs)
		_id: int = id(widget)

		if z_index in self.__widgets__:
			self.__widgets__[z_index][_id] = widget
		else:
			self.__widgets__[z_index] = {_id: widget}

		return widget

	### Properties
	@property
	def screen(self) -> _curses.window:
		return self.__root__

	@property
	def enabled(self) -> bool:
		return self.__enabled__ is None

	@property
	def minimized(self) -> bool:
		return self.__iconified__

	@property
	def exit_code(self) -> int | None:
		return self.__enabled__

	@property
	def exit_reason(self) -> None | BaseException:
		return self.__exit_reason__

	@property
	def current_tick(self) -> int:
		return self.__tick__

	@property
	def mouse(self) -> MouseInfo:
		return self.__last_mouse_info__

	@property
	def selected_subterminal(self) -> Widgets.SubTerminal | None:
		return self.__active_page__

	@property
	def default_bg(self) -> Color:
		return Color.fromcursesrgb(*curses.color_content(0))

	@property
	def default_fg(self) -> Color:
		return Color.fromcursesrgb(*curses.color_content(7))

	@property
	def focused(self) -> bool:
		this_win = win32console.GetConsoleWindow()
		foreground = win32gui.GetForegroundWindow()
		return this_win == foreground

class WindowTerminal:
	class SubprocessTerminal(Terminal):
		def __init__(self, conn: Connection.WinNamedPipe, widget_conn: Connection.WinNamedPipe, width: typing.Optional[int] = ..., height: typing.Optional[int] = ..., font: typing.Optional[Font] = ...):
			super().__init__(width, height, font)
			self.__conn__: Connection.WinNamedPipe = conn
			self.__widget_pipe__: Connection.WinNamedPipe = widget_conn
			self.__serialized_widgets__: dict[int, Widgets.SerializedWidget] = {}

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
				widget: Widgets.Widget = None if wid not in self.__serialized_widgets__ else self.__serialized_widgets__[wid].__widget__
				_widget: Widgets.Widget = self.get_widget(wid)

				if widget is None and _widget is None:
					self.__widget_pipe__.send((wid, _id, False, IndexError(f'No such widget - {wid}')))
				elif widget is not None and _widget is None:
					self.__widget_pipe__.send((wid, _id, False, IndexError(f'No such widget - {wid}')))
					del self.__serialized_widgets__[wid]
				else:
					if widget is None:
						widget = _widget
						self.__serialized_widgets__[wid] = Widgets.SerializedWidget(self.__widget_pipe__, widget)

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
	def __init__(self, tps: int, width: typing.Optional[int] = ..., height: typing.Optional[int] = ..., before_draw: typing.Optional[typing.Callable] = ..., after_draw: typing.Optional[typing.Callable] = ..., font: typing.Optional[Font] = ...):
		package: FileSystem.Directory = FileSystem.File(__file__).parentdir()
		callables: dict[str, tuple[str, str, str]] = {}
		res: int

		if callable(before_draw):
			module: types.ModuleType = sys.modules[before_draw.__module__]

			if not hasattr(module, '__file__'):
				raise AttributeError('The specified module has no file and cannot be loaded')

			callables['before_draw'] = (module.__file__, module.__name__, before_draw.__name__)

		if callable(after_draw):
			module: types.ModuleType = sys.modules[after_draw.__module__]

			if not hasattr(module, '__file__'):
				raise AttributeError('The specified module has no file and cannot be loaded')

			callables['after_draw'] = (module.__file__, module.__name__, after_draw.__name__)

		conn: Connection.WinNamedPipe = Connection.WinNamedPipe()
		widget_conn: Connection.WinNamedPipe = Connection.WinNamedPipe()
		self.__conn__: Connection.WinNamedPipe = conn
		self.__widget_pipe__: Connection.WinNamedPipe = widget_conn
		self.__process__: subprocess.Popen = subprocess.Popen(f'"{sys.executable}" "{package.file("_subterm.py").filepath()}" "{base64.b64encode(pickle.dumps((os.getpid(), conn, widget_conn, tps, width, height, font, callables))).decode()}"', creationflags=subprocess.CREATE_NEW_CONSOLE, close_fds=False)
		self.__psutil_process__: psutil.Process = psutil.Process(self.__process__.pid)
		self.__enabled__: bool = False
		self.__next_id__: int = -1
		self.__closed_ids__: list[int] = []
		self.__events__: dict[int, Concurrent.ThreadedPromise] = {}
		self.__widget_callbacks__: dict[int, typing.Callable] = {}
		self.__serialized_widgets__: dict[int, Widgets.SerializedWidget] = {}
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
		if callable(callback):
			self.__widget_callbacks__[widget_id] = callback

	def __bind_widget__(self, promise: Concurrent.ThreadedPromise, return_promise: Concurrent.ThreadedPromise) -> None:
		if promise.has_erred():
			return_promise.throw(promise.response(False))
			return

		serialized_widget: Widgets.SerializedWidget = promise.response()
		serialized_widget.__conn__ = self.__widget_pipe__
		self.__serialized_widgets__[serialized_widget.__wid__] = serialized_widget
		return_promise.resolve(serialized_widget)

	def send(self, method_name: str, *args, **kwargs) -> Concurrent.ThreadedPromise | Concurrent.Promise:
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
			args = tuple(SerializableCallable(arg) if callable(arg) else arg for arg in args)
			kwargs = {kw:(SerializableCallable(arg) if callable(arg) else arg) for kw, arg in kwargs.items()}

			if self.__enabled__:
				self.__conn__.send((method_name, _id, args, kwargs))
			else:
				self.__pending_actions__.append((method_name, _id, args, kwargs))

			return promise
		except IOError as e:
			pseudo: Concurrent.Promise = Concurrent.Promise()
			pseudo.throw(e)
			return pseudo

	def update_key_events(self) -> Concurrent.ThreadedPromise:
		return self.send('update_key_events()')

	def update_execute_pending_callbacks(self) -> Concurrent.ThreadedPromise:
		return self.send('update_execute_pending_callbacks()')

	### Standard methods
	def begin(self) -> None:
		if self.__enabled__:
			raise ValueError('Window already enabled')

		self.__conn__.write(b'\x01')

		for pending in self.__pending_actions__:
			self.__conn__.send(pending)

		self.__pending_actions__.clear()
		self.__enabled__ = True
		self.__thread__.start()

	def close(self) -> None:
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

	def end(self, exit_code: int = 0) -> Concurrent.ThreadedPromise:
		return self.send('end()', exit_code)

	def putstr(self, msg: str, x: typing.Optional[int] = ..., y: typing.Optional[int] = ..., n: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise:
		return self.send('putstr()', msg, x, y, n)

	def del_widget(self, _id: int) -> Concurrent.ThreadedPromise:
		return self.send('del_widget()', _id)

	def del_sub_terminal(self, _id: int) -> Concurrent.ThreadedPromise:
		return self.send('del_sub_terminal()', _id)

	def cancel(self, _id: int) -> Concurrent.ThreadedPromise:
		return self.send('cancel()', _id)

	def cursor_visibility(self, visibility: int) -> Concurrent.ThreadedPromise:
		return self.send('cursor_visibility()', visibility)

	def cursor_flash(self, flash_rate: int) -> Concurrent.ThreadedPromise:
		return self.send('cursor_flash()', flash_rate)

	def minimize(self) -> Concurrent.ThreadedPromise:
		return self.send('minimize()')

	def restore(self) -> Concurrent.ThreadedPromise:
		return self.send('restore()')

	def redraw(self) -> Concurrent.ThreadedPromise:
		return self.send('redraw()')

	def set_focus(self, widget: Widgets.Widget | None) -> Concurrent.ThreadedPromise:
		return self.send('set_focus()', WidgetStruct(widget.id))

	def erase_refresh(self, flag: bool) -> Concurrent.ThreadedPromise:
		return self.send('erase_refresh()', flag)

	def ungetch(self, key: int) -> Concurrent.ThreadedPromise:
		return self.send('ungetch()', key)

	def ungetgch(self, key: int) -> Concurrent.ThreadedPromise:
		return self.send('ungetgch()', key)

	def fullscreen(self, flag: typing.Optional[bool] = ...) -> Concurrent.ThreadedPromise:
		return self.send('fullscreen()', flag)

	def getch(self) -> Concurrent.ThreadedPromise:
		return self.send('getch()')

	def peekch(self) -> Concurrent.ThreadedPromise:
		return self.send('peekch()')

	def getgch(self) -> Concurrent.ThreadedPromise:
		return self.send('getgch()')

	def peekgch(self) -> Concurrent.ThreadedPromise:
		return self.send('peekgch()')

	def update_type(self, update_type: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise:
		return self.send('update_type()', update_type)

	def scroll_speed(self, scroll: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise:
		return self.send('scroll_speed()', scroll)

	def first_empty_row(self) -> Concurrent.ThreadedPromise:
		return self.send('first_empty_row()')

	def last_empty_row(self) -> Concurrent.ThreadedPromise:
		return self.send('last_empty_row()')

	def first_empty_column(self) -> Concurrent.ThreadedPromise:
		return self.send('first_empty_column()')

	def last_empty_column(self) -> Concurrent.ThreadedPromise:
		return self.send('last_empty_column()')

	def after(self, ticks: int, callback: typing.Callable, *args, __threaded: bool = True, **kwargs) -> Concurrent.ThreadedPromise:
		__threaded = kwargs['__threaded'] if '__threaded' in kwargs else __threaded
		del kwargs['__threaded']
		return self.send('after()', ticks, callback, *args, __threaded=__threaded, **kwargs)

	def tab_size(self, size: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise:
		return self.send('tab_size()', size)

	def cursor(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise:
		return self.send('cursor()', x, y)

	def scroll(self, x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise:
		return self.send('scroll()', x, y)

	def size(self, cols: typing.Optional[int] = ..., rows: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise:
		return self.send('size()', cols, rows)

	def full_size(self, cols: typing.Optional[int] = ..., rows: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise:
		return self.send('full_size()', cols, rows)

	def chat(self, x: int, y: int) -> Concurrent.ThreadedPromise:
		return self.send('chat()', x, y)

	def to_fixed(self, x: int, y: int) -> Concurrent.ThreadedPromise:
		return self.send('to_fixed()', x, y)

	def from_fixed(self, x: int, y: int) -> Concurrent.ThreadedPromise:
		return self.send('from_fixed()', x, y)

	def getline(self, replace_char: typing.Optional[str] = ..., prompt: typing.Optional[str] = '', x: typing.Optional[int] = ..., y: typing.Optional[int] = ...) -> Concurrent.ThreadedPromise:
		return self.send('getline()', replace_char, prompt, x, y)

	def font(self, font: typing.Optional[Font] = ...) -> Concurrent.ThreadedPromise:
		return self.send('font()', font)

	def get_topmost_child_at(self, x: int, y: int) -> Concurrent.ThreadedPromise:
		return self.send('get_topmost_child_at()', x, y)

	def get_focus(self) -> Concurrent.ThreadedPromise:
		return self.send('get_focus()')

	def active_subterminal(self) -> Concurrent.ThreadedPromise:
		return self.send('active_subterminal()')

	def get_widget(self, _id: int) -> Concurrent.ThreadedPromise:
		return self.send('get_widget()', _id)

	def get_sub_terminal(self, _id: int) -> Concurrent.ThreadedPromise:
		return self.send('get_sub_terminal()', _id)

	def get_children_at(self, x: int, y: int) -> Concurrent.ThreadedPromise:
		return self.send('get_children_at()', x, y)

	def widgets(self) -> Concurrent.ThreadedPromise:
		return self.send('widgets()')

	def subterminals(self) -> Concurrent.ThreadedPromise:
		return self.send('subterminals()')

	def windows(self) -> Concurrent.ThreadedPromise:
		return self.send('windows()')

	def children(self) -> Concurrent.ThreadedPromise:
		return self.send('children()')

	### Widget methods
	def add_button(self, x: int, y: int, width: int, height: int, text: str, *, z_index: int = 0, justify: int = CENTER, word_wrap: int = WORDWRAP_NONE,
				   border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				   color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_button()', x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
												border=border, highlight_border=highlight_border, active_border=active_border,
												color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_toggle_button(self, x: int, y: int, width: int, height: int, text: str, *, z_index: int = 0, justify: int = CENTER, word_wrap: int = WORDWRAP_NONE,
						  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
						  color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
						  callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_toggle_button()', x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
												border=border, highlight_border=highlight_border, active_border=active_border,
												color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str = '', active_text: str = 'X',
					 border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
					 color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
					 callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_checkbox()', x, y, z_index=z_index, text=text, active_text=active_text,
													border=border, highlight_border=highlight_border, active_border=active_border,
													color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
													callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_inline_checkbox(self, x: int, y: int, *, z_index: int = 0, text: str = '', active_text: str = 'X',
							border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
							callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_inline_checkbox()', x, y, z_index=z_index, text=text, active_text=active_text,
																border=border, highlight_border=highlight_border, active_border=active_border,
																color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_radial_spinner(self, x: int, y: int, *, z_index: int = 0, phases: typing.Iterable[str] = ('--', '\\', '|', '/'), bg_phase_colors: typing.Optional[Color_T] | typing.Iterable[typing.Optional[Color_T]] = ..., fg_phase_colors: typing.Optional[Color_T] | typing.Iterable[typing.Optional[Color_T]] = Color(0xFFFFFF),
						   callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_radial_spinner()', x, y, z_index=z_index, phases=phases, bg_phase_colors=bg_phase_colors, fg_phase_colors=fg_phase_colors,
															  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_horizontal_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str = '|', _max: float = 10, _min: float = 0, on_input: typing.Callable[[Widgets.HorizontalSlider], None] = ...,
							  border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							  color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
							  callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_horizontal_slider()', x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
																	border=border, highlight_border=highlight_border, active_border=active_border,
																	color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																	callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_vertical_slider(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str = '=', _max: float = 10, _min: float = 0, on_input: typing.Callable[[Widgets.VerticalSlider], None] = ...,
							border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
							callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_vertical_slider()', x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min, on_input=on_input,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_horizontal_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str = '|', _max: float = 10, _min: float = 0,
							border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
							callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_horizontal_progress_bar()', x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
																border=border, highlight_border=highlight_border, active_border=active_border,
																color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
																callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_vertical_progress_bar(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, fill_char: str = '=', _max: float = 10, _min: float = 0,
							border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
							color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
							callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_vertical_progress_bar()', x, y, width, height, z_index=z_index, fill_char=fill_char, _max=_max, _min=_min,
						 border=border, highlight_border=highlight_border, active_border=active_border,
						 color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
						 callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_text(self, x: int, y: int, width: int, height: int, text: str, *, z_index: int = 0, justify: int = NORTH_WEST, word_wrap: int = WORDWRAP_NONE,
				 color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
				 callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_text()', x, y, width, height, text, z_index=z_index, justify=justify, word_wrap=word_wrap,
											color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
											callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_dropdown(self, x: int, y: int, width: int, height: int, choices: tuple[str | AnsiStr, ...], *, display_count: int | None = None, allow_scroll_rollover: bool = False, z_index: int = 0, justify: int = CENTER, word_wrap: int = WORDWRAP_WORD, on_select: typing.Optional[typing.Callable[[Widgets.WIDGET_T], bool | None]] = ...,
				   border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				   color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		return self.send('add_dropdown()', x, y, width, height, choices, display_count=display_count, allow_scroll_rollover=allow_scroll_rollover, z_index=z_index, justify=justify, word_wrap=word_wrap, on_select=on_select,
												border=border, highlight_border=highlight_border, active_border=active_border,
												color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

	def add_entry(self, x: int, y: int, width: int, height: int, *, z_index: int = 0, word_wrap: int = WORDWRAP_WORD, justify: int = NORTH_WEST, replace_chars: str = '', placeholder: typing.Optional[str | AnsiStr] = ..., cursor_blink_speed: int = 0, on_text: typing.Optional[typing.Callable[[Widgets.Entry, bool], bool | str | AnsiStr | None]] = ..., on_input: typing.Optional[typing.Callable[[Widgets.Entry, AnsiStr, int], bool | str | AnsiStr | None]] = ...,
				  color_bg: typing.Optional[Color_T] = ..., color_fg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., highlight_color_fg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ..., active_color_fg: typing.Optional[Color_T] = ...,
				  callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_entry()', x, y, width, height, z_index=z_index, word_wrap=word_wrap, justify=justify, replace_chars=replace_chars, placeholder=placeholder, cursor_blink_speed=cursor_blink_speed, on_text=on_text, on_input=on_input,
											  color_bg=color_bg, color_fg=color_fg, highlight_color_bg=highlight_color_bg, highlight_color_fg=highlight_color_fg, active_color_bg=active_color_bg, active_color_fg=active_color_fg,
											  callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_image(self, x: int, y: int, width: int, height: int, image: str | AnsiStr | numpy.ndarray | PIL.Image.Image, *, z_index: int = 0, div: typing.Optional[int] = ..., use_subpad: bool = True,
				   border: typing.Optional[BorderInfo] = ..., highlight_border: typing.Optional[BorderInfo] = ..., active_border: typing.Optional[BorderInfo] = ...,
				   color_bg: typing.Optional[Color_T] = ..., highlight_color_bg: typing.Optional[Color_T] = ..., active_color_bg: typing.Optional[Color_T] = ...,
				   callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_image()', x, y, width, height, image, z_index=z_index, div=div, use_subpad=use_subpad,
												border=border, highlight_border=highlight_border, active_border=active_border,
												color_bg=color_bg, highlight_color_bg=highlight_color_bg, active_color_bg=active_color_bg,
												callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)

		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_sub_terminal(self, x: int, y: int, width: int, height: int, *, title: typing.Optional[str] = ..., z_index: int = 0, transparent: bool = False,
						 border: BorderInfo = ..., highlight_border: BorderInfo = ..., active_border: BorderInfo = ...,
						 callback: typing.Optional[typing.Callable[[Widgets.WIDGET_T, str, ...], None]] = ..., on_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., off_focus: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ..., on_mouse_enter: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_leave: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_press: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_release: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_mouse_click: typing.Optional[typing.Callable[[Widgets.WIDGET_T, MouseInfo], None]] = ..., on_tick: typing.Optional[typing.Callable[[Widgets.WIDGET_T, int], None]] = ..., on_close: typing.Optional[typing.Callable[[Widgets.WIDGET_T], None]] = ...) -> Concurrent.ThreadedPromise:
		promise: Concurrent.ThreadedPromise = self.send('add_sub_terminal()', x, y, width, height, title, z_index=z_index, transparent=transparent,
															border=border, highlight_border=highlight_border, active_border=active_border,
															callback=callback, on_focus=on_focus, off_focus=off_focus, on_mouse_enter=on_mouse_enter, on_mouse_leave=on_mouse_leave, on_mouse_press=on_mouse_press, on_mouse_release=on_mouse_release, on_mouse_click=on_mouse_click, on_tick=on_tick, on_close=on_close)
		rp: Concurrent.ThreadedPromise = Concurrent.ThreadedPromise()
		promise.then(lambda p: self.__bind_widget__(p, rp))
		return rp

	def add_widget(self, cls: Widgets.WIDGET_T, *args, z_index: int = 0, **kwargs) -> Concurrent.ThreadedPromise:
		return self.send('add_widget()', cls, *args, z_index=z_index, **kwargs)

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