import dearpygui.dearpygui as dpg
import tkinter as tk
import math

from CustomMethodsVI.Graphics.Camera import *
from CustomMethodsVI.Graphics.Colors import *
from CustomMethodsVI.Graphics.Math import *
from CustomMethodsVI.Graphics.Material import *
from CustomMethodsVI.Graphics.Poly import *
from CustomMethodsVI.Graphics.Util import *
from CustomMethodsVI.Graphics.Renderer import *


def dearpygui():
	def animate() -> None:
		nonlocal rotation

		rotation += 1
		theta: float = math.radians(rotation)
		camera.view = Camera.create_lookat_view(Vector3(math.cos(theta) * -10, 0, math.sin(theta) * -10), Vector3.zero(), Vector3.up())
		renderer.render()

	# Setup TK
	width: int = 1024
	height: int = 1024
	rotation: float = 0

	dpg.create_context()
	dpg.create_viewport(title='Graphics', width=width, height=height)
	dpg.setup_dearpygui()

	with dpg.window() as window:
		drawlist: int = dpg.add_drawlist(width, height)

	dpg.show_viewport()
	dpg.set_primary_window(window, True)

	# Setup graphics
	camera: Camera = Camera(
		Camera.create_lookat_view(Vector3(-10, 0, 0), Vector3.zero(), Vector3.up()),
		Camera.create_fov_perspective_projection(70, width / height)
	)

	renderer: DearPyGuiRendererCPU = DearPyGuiRendererCPU(drawlist)
	renderer.add_cameras(camera)

	renderer.add_meshes(
		PolyShape3D.create_cube(Vector3(0, 0, 0), Vector3.one(), UVMap.simple(Red, Blue)),
		PolyShape3D.create_cube(Vector3(1, 0, 0), Vector3.one(), UVMap.simple(Red, Blue)),
		#PolyShape3D.create_cube(Vector3(0, 1, 0), Vector3.one(), UVMap.simple(Red, Blue)),
		#PolyShape3D.create_cube(Vector3(0, 0, 1), Vector3.one(), UVMap.simple(Red, Blue))
	)

	renderer.active_camera = camera

	while dpg.is_dearpygui_running():
		animate()
		dpg.render_dearpygui_frame()

	dpg.destroy_context()


def tkinter():
	def animate() -> None:
		nonlocal rotation

		rotation += 1
		theta: float = math.radians(rotation)
		camera.view = Camera.create_lookat_view(Vector3(math.cos(theta) * -10, 0, math.sin(theta) * -10), Vector3.zero(), Vector3.up())
		renderer.render()
		root.after(16, animate)

	# Setup TK
	width: int = 1024
	height: int = 1024
	rotation: float = 0

	root: tk.Tk = tk.Tk()
	root.title('Graphics')
	root.configure(background='#222222')
	root.geometry(f'{width}x{height}')

	canvas = tk.Canvas(root, width=width, height=height, background='#222222')
	canvas.pack(side=tk.TOP, fill=tk.BOTH)

	# Setup graphics
	camera: Camera = Camera(
		Camera.create_lookat_view(Vector3(-10, 0, 0), Vector3.zero(), Vector3.up()),
		Camera.create_fov_perspective_projection(70, width / height)
	)

	renderer: TkinterRendererCPU = TkinterRendererCPU(canvas)
	renderer.add_cameras(camera)

	renderer.add_meshes(
		PolyShape3D.create_cube(Vector3(0, 0, 0), Vector3.one(), UVMap.simple(Red, Blue)),
		PolyShape3D.create_cube(Vector3(1, 0, 0), Vector3.one(), UVMap.simple(Red, Blue)),
		#PolyShape3D.create_cube(Vector3(0, 1, 0), Vector3.one(), UVMap.simple(Red, Blue)),
		#PolyShape3D.create_cube(Vector3(0, 0, 1), Vector3.one(), UVMap.simple(Red, Blue))
	)

	renderer.active_camera = camera
	root.after(16, animate)
	root.mainloop()


if __name__ == '__main__':
	dearpygui()
