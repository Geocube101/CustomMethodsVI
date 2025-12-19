class NormalDistribution:
	def __init__(self, mean: float, standard_deviation: float):
		assert standard_deviation > 0, 'Standard Deviation cannot be less than or equal to 0'

		self.__mean__: float = float(mean)
		self.__stddev__: float = float(standard_deviation)

	def is_standard(self) -> bool:
		return self.__mean__ == 0 and self.__stddev__ == 1

	def pnorm(self, value: float) -> float:
		pass

	def qnorm(self, percent_decimal: float) -> float:
		pass

	def zscore(self, value: float) -> float:
		return (value - self.__mean__) / self.__stddev__