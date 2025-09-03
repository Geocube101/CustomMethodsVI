import curses
import os
import sys

import CustomMethodsVI.Terminal.Enums as Enums
import CustomMethodsVI.Terminal.Struct as Struct
import CustomMethodsVI.Terminal.Terminal as Terminal
import CustomMethodsVI.Terminal.Widgets as Widgets


def mainloop(term: Terminal.Terminal) -> int:
	x, y = term.to_fixed(0, 0)
	# x, y = 0, 0
	c = term.getgch()
	#term.putstr(f'MOUSE1={term.mouse.position}, TICK={term.current_tick}\nCURSOR={term.cursor()}\nUSED_COLORS={len(term.__colors__)}\nACTIVE_PAGE={term.active_subterminal()}\nSCROLL={term.__scroll__}, KEY={c}', x, y)
	term.putstr('\033[38;2;255;0;0mThis is Red\033[0m', 1, 1)
	term.putstr('\033[38;2;0;255;0mThis is Green\033[0m', 1, 2)
	term.putstr('\033[38;2;0;0;255mThis is Blue\033[0m', 1, 3)

	if c == 27:
		return 1
	elif c == curses.KEY_F1:
		if term.minimized:
			term.restore()
		else:
			term.minimize()
	elif c == curses.KEY_F11:
		term.fullscreen(not term.fullscreen())
	elif c == curses.KEY_F10:
		curses.ungetch(curses.KEY_RESIZE)

	term.cursor(*term.to_fixed(0, 10))
	#term.end(5)


if __name__ == '__main__':
	term = Terminal.Terminal()
	w, h = term.size()
	term.scroll_speed(10)
	term.cursor_flash(0)
	term.cursor_visibility(2)
	term.font(Struct.Font('Courier New', (4, 8), 400))

	ansi = Struct.AnsiStr('\033[38;2;255;0;0mTHIS IS RED\033[0m')
	print(tuple(ansi.format_groups()))

	#img: Widgets.Image = term.add_image(10, 5, 100, 50, r"C:\Users\geoga\Pictures\portals2.0.png" if os.name == 'nt' else '/mnt/c/Users/geoga/Pictures/portals2.0png')
	term.add_horizontal_slider(10, 5, 100, 3, fill_char='#')
	term.update_type(Enums.WINUPDATE_MOUSEIN)

	res: int = term.mainloop(100, after_draw=mainloop)
	input('...')
	sys.exit(res)
