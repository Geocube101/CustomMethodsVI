from __future__ import annotations

import numpy

from . import Plotter


class Plot3D[PointType](Plotter.Plottable):
	def __draw__(self, image: numpy.ndarray, size: int) -> None:
		pass
