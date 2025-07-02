from .. import Decorators


class Pressure:
	@Decorators.Overload(strict=True)
	def __init__(self, value: float | int, unit: str | None):
		self.__value__: float = float(value)

		if unit is None:
			self.__unit__: tuple[str, str] | None = None
		else:
			num, den = self.__unit__.replace('/', '.').replace('_', '.').split('.')
			self.__unit__: tuple[str, str] | None = (num, den)

	def __str__(self) -> str:
		if self.__unit__ is None:
			return str(self.__value__)
		else:
			return f'{self.__value__} {self.__unit__[0]}.{self.__unit__[1]}'
