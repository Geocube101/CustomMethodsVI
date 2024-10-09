import tkinter as tk
import math

import CustomMethodsVI.Stream as Stream


def animate_sin():
	def __blink(duration_ms: int, a: float, b: float, c: float):
		state_changes: list[int] = []
		last_state_change: int = 0
		last_state: bool = ...

		def __inner(current_tick: int):
			nonlocal last_state_change
			nonlocal last_state

			ratio: float = current_tick / duration_ms
			value: float = math.sin(a * (ratio + b) ** c)
			state: bool = value >= 0

			if state != last_state:
				last_state = state
				state_changes.append(current_tick)
				last_state_change = current_tick
				canvas.itemconfig(dot, fill='#ff0000' if state else '#222222')

			if ratio < 1:
				root.after(1, __inner, current_tick + 1)
			else:
				text: list[str] = []
				b16 = ' ' * 16
				b18 = ' ' * 18
				n: int = 5

				for i in range(len(state_changes)):
					t0 = round(state_changes[i] / 1000, n)
					t1 = round(t0 + 0.25, n)
					t2 = round(t0 + 0.251, n)
					t3 = round(state_changes[i + 1] / 1000 - 0.001, n) if i + 1 < len(state_changes) else round(duration_ms / 1000, n)
					text.append(f'''{b16}<Key>
{b18}<Time>{t0}</Time>
{b18}<ValueFloat>1000</ValueFloat>
{b18}<Value2D />
{b16}</Key>
{b16}<Key>
{b18}<Time>{t1}</Time>
{b18}<ValueFloat>1000</ValueFloat>
{b18}<Value2D />
{b16}</Key>
{b16}<Key>
{b18}<Time>{t2}</Time>
{b18}<ValueFloat>0</ValueFloat>
{b18}<Value2D />
{b16}</Key>
{b16}<Key>
{b18}<Time>{t3}</Time>
{b18}<ValueFloat>0</ValueFloat>
{b18}<Value2D />
{b16}</Key>''')

				with Stream.FileStream('output.txt', 'w') as f:
					f.write('\n'.join(text))

				print(state_changes)

		__inner(0)

	root = tk.Tk()
	root.title('Test')
	root.geometry('400x400')
	canvas = tk.Canvas(root, bg='#222222')
	canvas.place(x=0, y=0, relwidth=1, relheight=1)
	dot: int = canvas.create_oval((100, 100), (300, 300), fill='#222222', outline='#eeeeee')
	root.after(1, __blink, 20000, 2, 0.96, 6)
	root.mainloop()


if __name__ == '__main__':
	animate_sin()