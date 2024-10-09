import cv2

import CustomMethodsVI.Math.Plotter as Plotter


if __name__ == '__main__':
	bar = Plotter.BarPlot2D()
	bar.add_points(x=(10, 0xFF0000), y=(20, 0x00FF00), z=(30, 0x0000FF))
	bar.axis_info('y', minor_spacing=1)
	# cv2.imwrite('test.png', cv2.cvtColor(pie.as_image(True), cv2.COLOR_RGB2BGR))
	bar.show(True)
