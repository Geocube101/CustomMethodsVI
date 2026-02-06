import math
import time
import typing

from . import Exceptions


def raise_if(expression: bool, exception: BaseException = AssertionError('Assertion Failed')) -> None:
	"""
	Raises an exception if the expression evaluates to True
	:param expression: The expression to evaluate
	:param exception: The exception to raise
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
	"""

	if not isinstance(exception, BaseException):
		raise Exceptions.InvalidArgumentException(raise_if, 'exception', type(exception))
	elif not expression:
		raise exception


def sleep(seconds: float) -> None:
	"""
	Pauses the current thread for the specified number of seconds
	:param seconds: The second to wait
	"""

	t1: float = time.perf_counter_ns()
	remaining: float = seconds * 1e9

	while remaining > 1e4:
		time.sleep(remaining * 0.5 * 1e-9)
		t2: float = time.perf_counter_ns()
		remaining -= t2 - t1
		t1 = t2


def busy_sleep(seconds: float) -> None:
	"""
	Pauses the current thread for the specified number of seconds
	This function busy-waits and will not yield thread execution
	:param seconds:
	:return:
	"""

	t1: float = time.perf_counter_ns()

	while time.perf_counter_ns() - t1 < seconds * 1e9:
		pass


def get_ratio(value: float, _min: float = 0, _max: float = 1) -> float:
	"""
	:param value: The value
	:param _min: The lower bound
	:param _max: The upper bound
	:return: The ratio of value in relation to lower and upper bounds
	"""

	return (value - _min) / (_max - _min)


def get_value(ratio: float, _min: float = 0, _max: float = 1) -> float:
	"""
	:param ratio: The ratio
	:param _min: The lower bound
	:param _max: The upper bound
	:return: The value of ratio in relation to lower and upper bounds
	"""
	return (_max - _min) * ratio + _min


def convert_metric(value: float | int, unit: str, places: int = ...) -> str:
	"""
	Converts the value into its metric string
	:param value: The value
	:param unit: The base unit
	:param places: The number of places to round
	:return: The metric prefixed value
	:raises InvalidArgumentException: If 'value' is not a float or integer
	:raises InvalidArgumentException: If 'unit' is not a string
	:raises InvalidArgumentException: If 'places' is not an integer
	"""

	raise_ifn(isinstance(value, (float, int)), Exceptions.InvalidArgumentException(convert_metric, 'value', type(value), (float, int)))
	raise_ifn(isinstance(unit, str), Exceptions.InvalidArgumentException(convert_metric, 'unit', type(unit), (str,)))
	raise_ifn(isinstance(places, int) and (places := int(places)) >= 0, Exceptions.InvalidArgumentException(convert_metric, 'places', type(places), (int,)))

	prefixes_up: tuple[str, ...] = ('', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y', 'R', 'Q')
	prefixes_down: tuple[str, ...] = ('', 'm', 'μ', 'n', 'p', 'f', 'a', 'z', 'y', 'r', 'q')
	l10: int = 0 if value == 0 else math.floor(math.log10(abs(value))) // 3
	prefix: str = prefixes_up[min(len(prefixes_up) - 1, l10)] if l10 > 0 else prefixes_down[min(len(prefixes_down) - 1, -l10)]
	value = value / pow(10, l10 * 3)
	return f'{round(value, places)} {prefix}{unit}'


def convert_scientific(value: float | int, places: int, e: str = " E ") -> str:
	"""
	Converts the value into its metric string
	:param value: The value
	:param places: The number of places to round
	:param e: The separator used for scientific notation
	:return: The metric prefixed value
	:raises InvalidArgumentException: If 'value' is not a float or integer
	:raises InvalidArgumentException: If 'places' is not an integer
	:raises InvalidArgumentException: If 'e' is not a string
	"""

	raise_ifn(isinstance(value, (float, int)), Exceptions.InvalidArgumentException(convert_scientific, 'value', type(value), (float, int)))
	raise_ifn(isinstance(places, int) and (places := int(places)) >= 0, Exceptions.InvalidArgumentException(convert_scientific, 'places', type(places), (int,)))
	raise_ifn(isinstance(e, str), Exceptions.InvalidArgumentException(convert_scientific, 'e', type(e), (str,)))

	l10: int = 0 if value == 0 else math.floor(math.log10(abs(value)))
	value = value / pow(10, l10)
	return f'{round(value, places)}{e}{l10}'


def convert_ddhhmmss(value: float | int) -> str:
	"""
	Converts this value into its temporal string
	Resulting time follows the format DD:HH:MM:SS:mm
	:param value: The value to convert
	:return: The formatted time string
	:raises InvalidArgumentException: If 'value' is not a float or integer
	"""

	raise_ifn(isinstance(value, (float, int)), Exceptions.InvalidArgumentException(convert_scientific, 'value', type(value), (float, int)))
	upper: int = abs(int(value))
	sign: str = '-' if value < 0 else '+'
	milliseconds: int = round(abs(value - upper) * 1000)
	seconds: int = round(upper % 60)
	minutes: int = round(upper % 3600 // 60)
	hours: int = round(upper % 86400 // 3600)
	days: int = round(upper // 86400)
	return f'{sign}{days:02}:{hours:02}:{minutes:02}:{seconds:02}:{milliseconds:04}'


def minmax(a: typing.Any, b: typing.Any) -> tuple[typing.Any, typing.Any]:
	"""
	:param a: The first value
	:param b: The second value
	:return: A tuple of the smallest and largest value
	"""

	return (a, b) if a <= b else (b, a)


def clamp(value: float, lower: float, upper: float) -> float:
	"""
	Clamps a value between 'lower' and 'upper'
	:param value: The value to clamp
	:param lower: The lower limit
	:param upper: The upper limit
	:return: The clamped value
	"""

	return min(upper, max(lower, value))
