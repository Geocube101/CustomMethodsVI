from __future__ import annotations

import math
import typing

from ... import Iterable
from ... import Math
from ... import Misc
from ...Decorators import Overload

NUMBER_T: typing.TypeAlias = float | int | complex
NUMBERSET_T: typing.TypeAlias = typing.Iterable[NUMBER_T]


@Overload
def mean(set_: NUMBERSET_T) -> NUMBER_T:
	"""
	Computes the average of all numbers in the specified iterable
	:param set_: The iterable of numbers
	:return: The average value
	:raises ValueError: If set is empty
	"""

	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	Misc.raise_if(len(set_) == 0, ValueError('Set is empty'))
	return sum(set_) / len(set_)


@Overload
def median(set_: NUMBERSET_T) -> NUMBER_T:
	"""
	Computes the median of an ordered set of numbers (50% quantile)
	Numbers will be ordered if not already
	:param set_: The iterable of numbers
	:return: The middle value
	:raises ValueError: If set is empty
	"""

	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	Misc.raise_if(len(set_) == 0, ValueError('Set is empty'))
	return quantile(set_, 0.5)


@Overload
def mode(set_: NUMBERSET_T) -> NUMBER_T:
	"""
	Computes the mode of a set of numbers
	The number with the highest occurrence will be returned
	:param set_: The iterable of numbers
	:return: The most common number
	:raises ValueError: If set is empty
	"""

	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	Misc.raise_if(len(set_) == 0, ValueError('Set is empty'))
	counts: dict[NUMBER_T, int] = {}

	for value in set_:
		if value in counts:
			counts[value] += 1
		else:
			counts[value] = 1

	highest: int = max(counts.values())
	return sorted(a for a, b in counts.items() if b == highest)[0]


@Overload
def variance(set_: NUMBERSET_T) -> NUMBER_T:
	"""
	Calculates the variance of a set of numbers
	:param set_: The iterable of numbers
	:return: The variance of the set
	:raises ValueError: If set is empty
	"""

	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	Misc.raise_if(len(set_) == 0, ValueError('Set is empty'))
	mean_: NUMBER_T = mean(set_)
	return sum((x - mean_) ** 2 for x in set_) / (len(set_) - 1)


@Overload
def standard_deviation(set_: NUMBERSET_T) -> NUMBER_T:
	"""
	Calculates the standard deviation of a set of numbers
	Equal to the square root of the variance
	:param set_: The iterable of numbers
	:return: The standard deviation
	:raises ValueError: If set is empty
	"""

	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	Misc.raise_if(len(set_) == 0, ValueError('Set is empty'))
	return variance(set_) ** 0.5


@Overload
def quantile(set_: NUMBERSET_T, percent: float) -> NUMBER_T:
	"""
	Calculates the nth quantile of a set of numbers
	:param set_: The iterable of numbers
	:param percent: The quantile percent (must be between 0 and 1 inclusive)
	:return: The nth quantile
	:raises ValueError: If set is empty
	:raises ValueError: If the percent value is outside range [0, 1]
	"""

	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	Misc.raise_if(len(set_) == 0, ValueError('Set is empty'))
	Misc.raise_ifn(isinstance(percent, (int, float)) and 0 <= (percent := float(percent)) <= 1, ValueError('Percent value is outside range [0, 1]'))
	index: float = len(set_) * percent - 0.5

	if index.is_integer():
		return set_[int(index)]
	else:
		return (set_[math.floor(index)] + set_[math.ceil(index)]) / 2

@Overload
def standard_deviation_pn(p: float, n: float) -> float:
	"""
	Calculates the standard deviation of a sample population given "p" and "n"
	:param p: The true population chance of success (must be between 0 and 1 inclusive)
	:param n: The sample size
	:return: The sample standard deviation
	:raises ValueError: If the percent value is outside range [0, 1]
	"""

	Misc.raise_ifn(0 <= p <= 1, ValueError('P must be a 0-1 clamped value'))
	return math.sqrt((p * (1 - p)) / n)


def poisson(lambda_: float, t: float, k: float) -> float:
	return ((lambda_ * t) ** k / Math.Functions.factorial(k)) * math.e ** (-lambda_ * t)
