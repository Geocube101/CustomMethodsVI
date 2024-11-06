import math
import typing

import CustomMethodsVI.Iterable as Iterable

from CustomMethodsVI.Decorators import Overload

NUMBER_T: typing.TypeAlias = float | int | complex
NUMBERSET_T: typing.TypeAlias = typing.Iterable[NUMBER_T]


@Overload
def mean(set_: NUMBERSET_T) -> NUMBER_T:
	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	assert len(set_) > 0, 'Set is empty'
	return sum(set_) / len(set_)


@Overload
def median(set_: NUMBERSET_T) -> NUMBER_T:
	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	assert len(set_) > 0, 'Set is empty'
	return quantile(set_, 0.5)


@Overload
def mode(set_: NUMBERSET_T) -> NUMBER_T:
	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	assert len(set_) > 0, 'Set is empty'
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
	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	assert len(set_) > 0, 'Set is empty'
	mean_: NUMBER_T = mean(set_)
	return sum((x - mean_) ** 2 for x in set_) / (len(set_) - 1)


@Overload
def standard_deviation(set_: NUMBERSET_T) -> NUMBER_T:
	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	assert len(set_) > 0, 'Set is empty'
	return variance(set_) ** 0.5


@Overload
def quantile(set_: NUMBERSET_T, percent: float) -> NUMBER_T:
	set_: Iterable.SortedList = set_ if isinstance(set_, Iterable.SortedList) else Iterable.SortedList(set_)
	assert len(set_) > 0, 'Set is empty'
	index: float = len(set_) * percent - 0.5

	if index.is_integer():
		return set_[int(index)]
	else:
		return (set_[math.floor(index)] + set_[math.ceil(index)]) / 2

@Overload
def standard_deviation_pn(p: float, n: float) -> float:
	assert 0 <= p <= 1, 'P must be a 0-1 clamped value'
	return math.sqrt((p * (1 - p)) / n)