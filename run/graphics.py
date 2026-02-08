import dearpygui.dearpygui as dpg
import math

from CustomMethodsVI.Graphics.Camera import *
from CustomMethodsVI.Graphics.Colors import *
from CustomMethodsVI.Graphics.Math import *
from CustomMethodsVI.Graphics.Material import *
from CustomMethodsVI.Graphics.Poly import *
from CustomMethodsVI.Graphics.Util import *
from CustomMethodsVI.Graphics.Renderer import *


def main():
	def animate() -> None:
		nonlocal rotation

		rotation += 10
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
		PolyShape3D.create_cube(Vector3(0, 0, 0), Vector3.one(), UVMap.simple(Red, Blue)).rotate(0, math.radians(30), 0)
	)

	renderer.active_camera = camera

	while dpg.is_dearpygui_running():
		animate()
		dpg.render_dearpygui_frame()

	dpg.destroy_context()


if __name__ == '__main__':
	main()
