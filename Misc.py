import time
import math
import typing

import CustomMethodsVI.Exceptions as Exceptions
import CustomMethodsVI.Decorators as Decorators


def raise_if(expression: bool, exception: BaseException = AssertionError('Assertion Failed')) -> None:
	"""
	Raises an exception if the expression evaluates to True
	:param expression: The expression to evaluate
	:param exception: The exception to raise
	:return: (None)
	"""

	if not isinstance(exception, BaseException):
		raise Exceptions.InvalidArgumentException(raise_if, 'exception', type(exception))
	elif expression:
		raise exception


def raise_ifn(expression: bool, exception: BaseException = AssertionError('Assertion Failed')) -> None:
	"""
	Raises an exception if the expression evaluates to False
	:param expression: The expression to evaluate
	:param exception: The exception to raise
	:return: (None)
	"""

	if not isinstance(exception, BaseException):
		raise Exceptions.InvalidArgumentException(raise_if, 'exception', type(exception))
	elif not expression:
		raise exception


def sleep(seconds: float) -> None:
	t1: float = time.perf_counter_ns()
	remaining: float = seconds * 1e9

	while remaining > 1e4:
		time.sleep(remaining * 0.5 * 1e-9)
		t2: float = time.perf_counter_ns()
		remaining -= t2 - t1
		t1 = t2


def busy_sleep(seconds: float) -> None:
	t1: float = time.perf_counter_ns()

	while time.perf_counter_ns() - t1 < seconds * 1e9:
		pass


def get_ratio(value: float, _min: float = 0, _max: float = 1) -> float:
	return (value - _min) / (_max - _min)


def get_value(ratio: float, _min: float = 0, _max: float = 1) -> float:
	return (_max - _min) * ratio + _min


def convert_metric(value: float | int, unit: str, places: int = ...) -> str:
	assert isinstance(value, (float, int)), '\'value\' is not a number'
	assert isinstance(unit, str), '\'unit\' is not a str'
	assert isinstance(places, int), '\'places\' is not an int'

	prefixes_up: tuple[str, ...] = ('', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y', 'R', 'Q')
	prefixes_down: tuple[str, ...] = ('', 'm', 'μ', 'n', 'p', 'f', 'a', 'z', 'y', 'r', 'q')
	count: int = 0

	if value > 0:
		while value >= 1e3 and count < len(prefixes_up) - 1:
			count += 1
			value /= 1e3

		return f'{round(value, places)} {prefixes_up[count]}{unit}'
	elif value < 0:
		while value <= 1e3 and count < len(prefixes_down) - 1:
			count += 1
			value *= 1e3

		return f'{round(value, places)} {prefixes_down[count]}{unit}'
	else:
		return f'{value} {unit}'


def convert_scientific(value: float | int, places: int, e: str = " E "):
	l10: int = math.floor(math.log10(abs(value)))
	sign: str = '-' if value < 0 else ''
	value = value / pow(10, l10)
	return f'{sign}{round(value, places)}{e}{l10}'


@Decorators.Overload
def minmax(a: typing.Any, b: typing.Any) -> tuple[typing.Any, typing.Any]:
	return (a, b) if a <= b else (b, a)

@Decorators.DefaultOverload
def minmax(collection: typing.Iterable[typing.Any]) -> tuple[typing.Any, typing.Any]:
	iterator: typing.Iterator[typing.Any] = iter(collection)
	lowest = highest = next(iterator)

	try:
		while True:
			current = next(iterator)
			lowest = min(lowest, current)
			highest = max(highest, current)
	except StopIteration:
		pass

	return lowest, highest