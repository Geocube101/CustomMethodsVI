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
		# renderer.sun_normal = TransformMatrix3D.create_rotation(0, 0, math.radians(0)).transform_vector(camera.view.forward)
		renderer.render()
		#return

		for i, face in enumerate(renderer.meshes[0].get_polygons()):
			p1, p2 = camera.points_world_to_screen(width, height, face.center, face.center + face.normal)

			if (existing := normals.get(i)) is not None:
				dpg.configure_item(existing, p1=p1.components[:2], p2=p2.components[:2])
			else:
				lid: int = dpg.draw_line(p1.components[:2], p2.components[:2], color=Lime.rgba, parent=drawlist)
				normals[i] = lid

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

	renderer: DearPyGuiRenderer3DCPU = DearPyGuiRenderer3DCPU(drawlist)
	renderer.add_cameras(camera)

	renderer.add_meshes(
		Mesh3D.create_octahedron(Vector3(0, 0, 0), UVMap.simple(Red, Blue)).rotate(0, math.radians(0), math.radians(0))
	)

	renderer.active_camera = camera
	renderer.sun_normal = Vector3(0, 0, -1)
	normals: dict[int, int] = {}
	
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
		renderer.sun_normal = camera.view.forward
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

	renderer: TkinterRenderer3DCPU = TkinterRenderer3DCPU(canvas)
	renderer.add_cameras(camera)

	renderer.add_meshes(
		Mesh3D.create_octahedron(Vector3(0, 0, 0), UVMap.simple(Red, Blue))
	)

	renderer.active_camera = camera
	root.after(16, animate)
	root.mainloop()


if __name__ == '__main__':
	dearpygui()
