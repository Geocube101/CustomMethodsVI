import datetime
import math
import json

from CustomMethodsVI.Math.Plotter.Plotter import GridPlotDisplay, LabelSpacing, LabelAlignment
from CustomMethodsVI.Math.Plotter.Plot2D import *


def linear_scatter():
	def func(theta):
		return math.sin(theta)

	scatter = CartesianScatterPlot2D()
	scatter.axes_info('x', 'y', minor_spacing=math.pi / 4, major_spacing=4)
	scatter.graph(func)

	return scatter


def polar_scatter():
	def func(theta):
		return math.tan(theta)

	scatter = PolarScatterPlot2D()
	scatter.axes_info('x', 'y', minor_spacing=math.pi / 4, major_spacing=4)
	scatter.axes_info('t', minor_spacing=5, major_spacing=9)
	scatter.graph(func)
	return scatter


def pie():
	piep = PiePlot2D()
	piep.add_points(('a', 20), ('b', 50), ('c', 30))
	return piep


def bar():
	barp = BarPlot2D()
	barp.add_points(('x', 10), ('y', 20), ('z', -30))
	return barp


def histogram():
	hist = HistogramPlot2D()
	hist.add_points((1, 2), (2, 3), (3, 4), (5, 1))
	# hist.bins = len(set(hist.get_points()))
	return hist


def density():
	dens = DensityPlot2D()
	dens[0].add_points((1, 2), (2, 3), (3, 4), (5, 1))
	# dens.bins = len(set(hist.get_points()))
	return dens


def dot():
	dotplot = DotPlot2D()
	dotplot[0].add_points(('1', 2), ('2', 3), ('3', 4), ('5', 1))
	# dotplot.bins = len(set(dotplot.get_points()))
	dotplot[0].plot_info(point_color=0xFF00FFFF, point_size=10)
	return dotplot


def stacked_dot():
	dotplot = StackedDotPlot2D()
	dotplot.add_points(('1', 2), ('2', 3), ('3', 4), ('5', 1))
	# dotplot.bins = len(set(dotplot.get_points()))
	dotplot.plot_info(point_color=0xFF00FFFF, point_size=50)
	return dotplot


def boxplot():
	box = BoxPlot2D()
	box[0].add_points(1, 1, 2, 2, 2, 3, 3, 3, 3, 5)
	return box


def candlestick():
	def axis_label(axis: str, point: tuple[float, ...]) -> str:
		x, y = point
		return datetime.datetime.fromtimestamp(x).strftime('%m/%d/%Y (%H:%M)') if axis == 'time' else f'${y:,.2f}'

	candle = CandlestickPlot2D()
	candle.add_points(
		CandlestickPlot2D.CandleFrame(datetime.datetime.now(), 0, 550, -25, 500),
		CandlestickPlot2D.CandleFrame(datetime.datetime.now() + datetime.timedelta(days=1), 500, 860, 475, 860),
		CandlestickPlot2D.CandleFrame(datetime.datetime.now() + datetime.timedelta(days=2), 860, 860, 300, 420),
		CandlestickPlot2D.CandleFrame(datetime.datetime.now() + datetime.timedelta(days=3), 420, 2000, 300, 2420),
		CandlestickPlot2D.CandleFrame(datetime.datetime.now() + datetime.timedelta(days=4), 2420, 3000, 2210, 2800),
		CandlestickPlot2D.CandleFrame(datetime.datetime.now() + datetime.timedelta(days=5), 2800, 2950, -10, 0),
	)
	candle.axes_info('price', minor_spacing=100, major_spacing=10, label=AxisPlot2D.AxisLabel2D(labeller=axis_label, color=0xEEEEEEFF, angle=0, spacing=LabelSpacing.MAJOR))
	candle.axes_info('time', label=AxisPlot2D.AxisLabel2D(labeller=axis_label, spacing=LabelSpacing.MINOR, color=0xEEEEEEFF, angle=15))
	return candle


def main():
	candlestick().show(square_size=1024)
	return

	display = GridPlotDisplay()
	display[0, 0] = linear_scatter()
	display[0, 1] = polar_scatter()
	display[0, 2] = pie()
	display[1, 0] = bar()
	display[1, 1] = histogram()
	display[1, 2] = density()
	display[2, 0] = dot()
	display[2, 1] = stacked_dot()
	display[2, 2] = boxplot()
	display[3, 0] = candlestick()
	display.show(square_size=256)


if __name__ == '__main__':
	main()
