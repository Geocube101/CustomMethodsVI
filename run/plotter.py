import math

import CustomMethodsVI.Math.Plotter as Plotter


def linear_scatter():
	def func(theta):
		return math.sin(theta)

	scatter = Plotter.CartesianScatterPlot2D()
	scatter.axes_info('x', 'y', minor_spacing=math.pi / 4, major_spacing=4)
	scatter.graph(func)
	return scatter


def polar_scatter():
	def func(theta):
		return math.tan(theta)

	scatter = Plotter.PolarScatterPlot2D()
	scatter.axes_info('x', 'y', minor_spacing=math.pi / 4, major_spacing=4)
	scatter.axes_info('t', minor_spacing=5, major_spacing=9)
	scatter.graph(func)
	return scatter

def pie():
	piep = Plotter.PiePlot2D()
	piep.add_points(('a', 20), ('b', 50), ('c', 30))
	return piep


def bar():
	barp = Plotter.BarPlot2D()
	barp.add_points(('x', 10), ('y', 20), ('z', -30))
	return barp


def histogram():
	hist = Plotter.HistogramPlot2D()
	hist.add_points((1, 2), (2, 3), (3, 4), (5, 1))
	# hist.bins = len(set(hist.get_points()))
	return hist


def density():
	dens = Plotter.DensityPlot2D()
	dens[0].add_points((1, 2), (2, 3), (3, 4), (5, 1))
	# dens.bins = len(set(hist.get_points()))
	return dens


def dot():
	dotplot = Plotter.DotPlot2D()
	dotplot[0].add_points(('1', 2), ('2', 3), ('3', 4), ('5', 1))
	# dotplot.bins = len(set(dotplot.get_points()))
	dotplot[0].plot_info(point_color=0xFF00FFFF, point_size=10)
	return dotplot


def stacked_dot():
	dotplot = Plotter.StackedDotPlot2D()
	dotplot.add_points(('1', 2), ('2', 3), ('3', 4), ('5', 1))
	# dotplot.bins = len(set(dotplot.get_points()))
	dotplot.plot_info(point_color=0xFF00FFFF, point_size=50)
	return dotplot


def boxplot():
	box = Plotter.BoxPlot2D()
	box[0].add_points(1, 1, 2, 2, 2, 3, 3, 3, 3, 5)
	return box


def main():
	display = Plotter.GridPlotDisplay()
	display[0, 0] = linear_scatter()
	display[0, 1] = polar_scatter()
	display[0, 2] = pie()
	display[1, 0] = bar()
	display[1, 1] = histogram()
	display[1, 2] = density()
	display[2, 0] = dot()
	display[2, 1] = stacked_dot()
	display[2, 2] = boxplot()
	display.show(square_size=384)


if __name__ == '__main__':
	main()
