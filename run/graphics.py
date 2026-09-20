import cv2
import dearpygui.dearpygui as dpg
import tkinter as tk
import math

from CustomMethodsVI.Graphics.Colors import Transparent

from CustomMethodsVI.Graphics.Bounds import *
from CustomMethodsVI.Graphics.Camera import *
from CustomMethodsVI.Graphics.Colors import *
from CustomMethodsVI.Graphics.Math import *
from CustomMethodsVI.Graphics.Material import *
from CustomMethodsVI.Graphics.Poly import *
from CustomMethodsVI.Graphics.Util import *
from CustomMethodsVI.Graphics.Renderer import *
from CustomMethodsVI.Graphics.VectorOps import *

WIDTH: int = 1024
HEIGHT: int = 1024
DISTANCE: float = 10


def image():
		# Setup graphics
	camera: Camera = VectorizedCamera(
		Camera.create_lookat_view(Vector3(-DISTANCE, 2, 0), Vector3.zero(), Vector3.up()),
		Camera.create_fov_perspective_projection(70, WIDTH / HEIGHT),
		cull_faces=True
	)

	renderer: ImageRenderer3DCPU = ImageRenderer3DCPU((1024, 1024))
	renderer.add_cameras(camera)
	bounds = BoundingCapsule3D(Vector3.zero(), 1, 1, 4)
	material = UVMap.simple(Red, Blue)

	renderer.add_meshes(
	#	bounds.meshify(material, count=16)
		cyl := Mesh3D.create_cylinder(Vector3.zero(), uv_mat=UVMap.simple(Transparent, Blue)).scale(2, 0.1, 2),
		cube := Mesh3D.create_cube(Vector3.zero(), material)
	)

	cyl.rotate(Quaternion3D.from_euler_angles(math.radians(0), 0, 0))
	#cyl.enabled = False
	renderer.active_camera = camera
	renderer.sun_normal = Vector3(0, 0, -1)
	renderer.render()
	cv2.imshow('Render', renderer.image)
	cv2.waitKey(0)


def dearpygui():
	def animate() -> None:
		nonlocal rotation

		rotation += 1
		theta: float = math.radians(rotation)
		sin_ticker: float = math.sin(2 * math.pi * (rotation % 180 / 180))
		camera.view = Camera.create_lookat_view(Vector3(math.cos(theta) * -DISTANCE, 5 * sin_ticker, math.sin(theta) * -DISTANCE), Vector3.zero(), Vector3.up())
		renderer.render()
		return
		for i, face in enumerate(renderer.meshes[0].get_polygons()):
			p1, p2 = camera.points_world_to_screen(WIDTH, HEIGHT, face.center, face.center + face.normal)

			if p1 is ... or p2 is ...:
				continue

			if (existing := normals.get(i)) is not None:
				dpg.configure_item(existing, p1=p1.components[:2], p2=p2.components[:2])
			else:
				lid: int = dpg.draw_line(p1.components[:2], p2.components[:2], color=Lime.rgba, parent=drawlist)
				normals[i] = lid

		if renderer.is_sun_enabled:
			p1, p2 = camera.points_world_to_screen(WIDTH, HEIGHT, Vector3.zero(), renderer.sun_normal)

			if p1 is not ... and p2 is not ...:
				if dpg.does_item_exist('sun-normal'):
					dpg.configure_item('sun-normal', p1=p1.components[:2], p2=p2.components[:2])
				else:
					dpg.draw_line(p1.components[:2], p2.components[:2], color=Gold.rgba, parent=drawlist, tag='sun-normal', thickness=5)

	# Setup TK
	dpg.create_context()
	dpg.create_viewport(title='Graphics', width=WIDTH, height=HEIGHT)
	dpg.setup_dearpygui()

	with dpg.window() as window:
		drawlist: int = dpg.add_drawlist(WIDTH, HEIGHT)

	dpg.show_viewport()
	dpg.set_primary_window(window, True)

	# Setup graphics
	camera: Camera = VectorizedCamera(
		Camera.create_lookat_view(Vector3(-DISTANCE, 0, 0), Vector3.zero(), Vector3.up()),
		Camera.create_fov_perspective_projection(70, WIDTH / HEIGHT),
		cull_faces=True
	)

	renderer: DearPyGuiRenderer3DCPU = DearPyGuiRenderer3DCPU(drawlist)
	renderer.add_cameras(camera)
	bounds = BoundingCapsule3D(Vector3.zero(), 1, 1, 4)
	material = UVMap.simple(Red, Blue)

	renderer.add_meshes(
	#	bounds.meshify(material, count=16)
		Mesh3D.create_sphere(Vector3.zero(), uv_mat=material)
		#Mesh3D.create_cube(Vector3.zero(), material)
	)

	#renderer.add_polygons(Mesh2D.create_square(Vector2.zero()).to_polygon(uv_mat=material))
	renderer.add_polygons(Mesh2D.create_circle(Vector2.zero()).to_polygon(uv_mat=material))

	renderer.active_camera = camera
	renderer.sun_normal = Vector3(0, 0, -1)
	normals: dict[int, int] = {}
	rotation: float = 0
	# renderer.render()
	
	while dpg.is_dearpygui_running():
		animate()
		dpg.render_dearpygui_frame()

	dpg.destroy_context()


def tkinter():
	def animate() -> None:
		nonlocal rotation

		rotation += 1
		theta: float = math.radians(rotation)
		sin_ticker: float = math.sin(2 * math.pi * (rotation % 180 / 180))
		camera.view = Camera.create_lookat_view(Vector3(math.cos(theta) * -10, 5 * sin_ticker, math.sin(theta) * -10), Vector3.zero(), Vector3.up())
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
	bounds = BoundingBox3D(Vector3.zero(), Vector3.one())
	material = UVMap.simple(Red, Blue)

	renderer.add_meshes(
		bounds.meshify(material)
	)

	renderer.active_camera = camera
	renderer.sun_normal = Vector3(0, 0, -1)
	root.after(16, animate)
	root.mainloop()


if __name__ == '__main__':
	image()
