import curses
import sys

import CustomMethodsVI.Terminal.Enums as Enums
import CustomMethodsVI.Terminal.Struct as Struct
import CustomMethodsVI.Terminal.Terminal as Terminal
import CustomMethodsVI.Terminal.Widgets as Widgets


def mainloop(term: Terminal.Terminal) -> int:
	x, y = term.to_fixed(0, 0)
	# x, y = 0, 0
	c = term.getgch()
	term.putstr(f'MOUSE1={term.mouse.position}, TICK={term.current_tick}\nCURSOR={term.cursor()}\nUSED_COLORS={len(term.__colors__)}\nACTIVE_PAGE={term.active_subterminal()}\nSCROLL={term.__scroll__}, KEY={c}', x, y)

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

	#term.end(5)


if __name__ == '__main__':
	term = Terminal.Terminal()
	w, h = term.size()
	term.scroll_speed(10)
	term.font(Struct.Font('Courier New', (4, 8), 400))

	img: Widgets.Image = term.add_image(10, 5, 100, 50, r"C:\Users\geoga\Pictures\nuclear.png")
	term.update_type(Enums.WINUPDATE_MOUSEIN)

	sys.exit(term.mainloop(100, after_draw=mainloop))
