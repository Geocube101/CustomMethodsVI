import cv2
import math

import CustomMethodsVI.Math.Plotter as Plotter


def linear_scatter():
	def func(theta):
		return math.sin(theta) - 0.5

	scatter = Plotter.CartesianScatterPlot2D()
	scatter.axis_info('xy', min_=-math.pi * 2, max_=math.pi * 2, minor_spacing=math.pi / 4, major_spacing=4)
	scatter.plot_info('', point_size=1)
	scatter.graph(func)
	scatter.show(True)


def polar_scatter():
	def func(theta):
		return math.sin(theta) - 0.5

	scatter = Plotter.PolarScatterPlot2D()
	scatter.axis_info('xy', min_=-math.pi * 2, max_=math.pi * 2, minor_spacing=math.pi / 4, major_spacing=4)
	scatter.axis_info('t', minor_spacing=5, major_spacing=9)
	scatter.plot_info('', point_size=1)
	scatter.graph(func)
	scatter.show(True)


def bar():
	barp = Plotter.BarPlot2D()
	barp.add_points(x=(10, 0x0000FF), y=(20, 0x00FF00), z=(-30, 0xFF0000))
	barp.show(True)


def histogram():
	hist = Plotter.HistogramPlot2D()
	hist.add_points(1, 1, 2, 2, 2, 3, 3, 3, 3, 5)
	hist.bins = len(set(hist.get_points()))
	hist.show(True)


def density():
	dens = Plotter.DensityPlot2D()
	dens.add_points(1, 1, 2, 2, 2, 3, 3, 3, 3, 5)
	dens.bins = len(set(dens.get_points()))
	dens.show(True)


def dot():
	dotplot = Plotter.DotPlot2D()
	dotplot.add_points(1, 1, 2, 2, 2, 3, 3, 3, 3, 5)
	dotplot.bins = len(set(dotplot.get_points()))
	dotplot.plot_info(color=0xFF00FF, point_size=100)
	dotplot.show(True)


if __name__ == '__main__':
	dot()
