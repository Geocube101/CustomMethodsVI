from __future__ import annotations

import collections.abc
import math
import sys
import time
import threading
import typing

from .. import Exceptions
from .. import Misc
from .. import Stream


class Iterable[IterType, ElemType](collections.abc.Collection[ElemType]):
	"""
	Base iterable class for CM-VI iterables
	"""

	def __init__(self, collection: IterType):
		"""
		Base iterable class for CM-VI iterables\n
		- Constructor -
		:param collection: The iterable to build from
		"""

		self.__buffer__: IterType = collection

	def __contains__(self, item: ElemType) -> bool:
		"""
		:param item: The item to search for
		:return: If the item exists within this collection
		"""

		return item in self.__buffer__

	def __eq__(self, other: Iterable[IterType, ElemType]) -> bool:
		"""
		Checks if this instance matches another Iterable instance
		:param other: The callback instance to compare
		:return: True if both are an Iterable and their contents are equal
		"""

		return self.__buffer__ == other.__buffer__ if isinstance(other, Iterable) else False

	def __ne__(self, other: Iterable[IterType, ElemType]) -> bool:
		"""
		Checks if this instance doesn't match another Iterable instance
		:param other: The callback instance to compare
		:return: True if both are an IterableIterable and their contents are equal
		"""

		return not self == other

	def __gt__(self, other: Iterable[IterType, ElemType]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: The callback instance
		:return: If this length is greater
		"""

		return len(self) > len(other) if isinstance(other, Iterable) else NotImplemented

	def __lt__(self, other: Iterable[IterType, ElemType]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: The callback instance
		:return: If this length is lesser
		"""

		return len(self) < len(other) if isinstance(other, Iterable) else NotImplemented

	def __ge__(self, other: Iterable[IterType, ElemType]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: The callback instance
		:return: If this length is greater or equal
		"""

		return len(self) >= len(other) if isinstance(other, Iterable) else NotImplemented

	def __le__(self, other: Iterable[IterType, ElemType]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: The callback instance
		:return: If this length is lesser or equal
		"""

		return len(self) <= len(other) if isinstance(other, Iterable) else NotImplemented

	def __bool__(self) -> bool:
		"""
		Converts this instance to a bool based on it's size
		:return: True if this collection is not empty
		"""

		return bool(len(self))

	def __len__(self) -> int:
		"""
		:return: The length of this iterable
		"""

		return len(self.__buffer__)

	def __iter__(self) -> typing.Iterator[ElemType]:
		"""
		:return: An iterator to iterate over this iterable
		"""

		return iter(self.__buffer__)

	def stream(self) -> Stream.LinqStream[ElemType]:
		"""
		:return: A new LinqStream for queries on this sequence
		"""

		return Stream.LinqStream(self)


class IterableView[IterType: collections.abc.Collection, ElemType](collections.abc.Collection[ElemType]):
	"""
	Class allowing a view into a collection
	"""

	def __init__(self, iterable: IterType):
		"""
		Class allowing a view into a collection\n
		- Constructor -
		:param iterable: The iterable to view
		"""

		Misc.raise_ifn(isinstance(iterable, collections.abc.Collection), Exceptions.InvalidArgumentException(IterableView.__init__, 'iterable', type(iterable), (collections.abc.Collection,)))
		self.__iterable__: IterType = iterable

	def __contains__(self, item: ElemType) -> bool:
		"""
		:param item: The item to search for
		:return: If the item exists within this view's collection
		"""

		return item in self.__iterable__

	def __eq__(self, other: collections.abc.Collection[ElemType] | IterableView[ElemType]) -> bool:
		"""
		Checks if this view's collection matches another collection
		:param other: The callback instance to compare
		:return: True if both are a collection and their contents are equal
		"""

		return self is other if isinstance(other, IterableView) else self.__iterable__ == other if isinstance(other, collections.abc.Collection) else False

	def __ne__(self, other: collections.abc.Collection[ElemType] | IterableView[ElemType]) -> bool:
		"""
		Checks if this view's collection matches another collection
		:param other: The callback instance to compare
		:return: False if both are a collection and their contents are equal
		"""

		return not self == other

	def __gt__(self, other: collections.abc.Collection[ElemType] | IterableView[ElemType]) -> bool:
		"""
		Compares two collections based on their length
		:param other: The callback instance
		:return: If this view's length is greater
		"""

		return len(self) > len(other) if isinstance(other, collections.abc.Collection) else NotImplemented

	def __lt__(self, other: collections.abc.Collection[ElemType] | IterableView[ElemType]) -> bool:
		"""
		Compares two collections based on their length
		:param other: The callback instance
		:return: If this view's length is lesser
		"""

		return len(self) < len(other) if isinstance(other, collections.abc.Collection) else NotImplemented

	def __ge__(self, other: collections.abc.Collection[ElemType] | IterableView[ElemType]) -> bool:
		"""
		Compares two collections based on their length
		:param other: The callback instance
		:return: If this view's length is greater or equal
		"""

		return len(self) >= len(other) if isinstance(other, collections.abc.Collection) else NotImplemented

	def __le__(self, other: collections.abc.Collection[ElemType] | IterableView[ElemType]) -> bool:
		"""
		Compares two collections based on their length
		:param other: The callback instance
		:return: If this view's length is lesser or equal
		"""

		return len(self) <= len(other) if isinstance(other, collections.abc.Collection) else NotImplemented

	def __bool__(self) -> bool:
		"""
		Converts this view's iterable to a bool based on it's size
		:return: True if this view's iterable is not empty
		"""

		return bool(len(self))

	def __len__(self) -> int:
		"""
		:return: The length of this view's iterable
		"""

		return len(self.__iterable__)

	def __iter__(self) -> typing.Iterator[ElemType]:
		"""
		:return: An iterator to iterate over this view's iterable
		"""

		return iter(self.__iterable__)

	def stream(self) -> Stream.LinqStream[ElemType]:
		"""
		:return: A LinqStream iterating over this view's collection
		"""

		return Stream.LinqStream(self.__iterable__)


class ThreadedGenerator[T]:
	"""
	Special generator using threading.Thread threads
	"""

	def __init__(self, generator: typing.Generator | typing.Iterable[T]):
		"""
		Special generator using threading.Thread threads\n
		- Constructor -
		:param generator: The initial generator or iterable to iterate
		"""

		self.__buffer__ = []
		self.__thread__ = threading.Thread(target=self.__mainloop)
		self.__state__ = False
		self.__iterator__ = iter(generator)
		self.__exec__ = None

		self.__thread__.start()

	def __del__(self) -> None:
		self.close()

	def __mainloop(self) -> None:
		"""
		INTERNAL METHOD
		Starts the threaded generator
		"""

		self.__state__ = True
		base_count = sys.getrefcount(self)

		try:
			while self.__state__ and sys.getrefcount(self) >= base_count:
				self.__buffer__.append(next(self.__iterator__))
		except (SystemExit, KeyboardInterrupt, Exception) as e:
			self.__state__ = False
			self.__exec__ = e

	def __next__(self) -> T:
		"""
		Waits until a new value is available or until internal thread is closed
		Returns next value or raises StopIteration
		:return: The next value
		:raises StopIteration: If iteration is complete
		"""

		try:
			while len(self.__buffer__) == 0:
				if type(self.__exec__) is StopIteration or not self.__thread__.is_alive():
					raise StopIteration
				time.sleep(1e-7)

			return self.__buffer__.pop(0)
		except (KeyboardInterrupt, SystemExit) as e:
			self.__exec__ = e
			self.close()
			raise e

	def __iter__(self):
		return self

	def close(self) -> None:
		"""
		Closes the iterator
		Raises an exception if an exception occurred during iteration
		"""

		if not self.__state__:
			return

		self.__state__ = False

		if self.__thread__.is_alive():
			self.__thread__.join()

		if self.__exec__ is not None:
			raise self.__exec__


def frange(start: float, stop: float = None, step: float = 1, precision: int = None) -> collections.abc.Generator[float]:
	"""
	Float compatible range generator
	:param start: Start of range
	:param stop: End of range
	:param step: Step
	:param precision: Number of digits to round, or no rounding if None
	:return: A generator iterating the range
	"""

	_start: float = 0 if stop is None else float(start)
	_stop: float = float(start) if stop is None else float(stop)
	_step: float = float(step)
	a: float = _start
	precision = int(precision) if precision is None or precision is ... else max(0, -math.floor(math.log10(step)))

	while a < _stop:
		yield a
		a = round(a + _step, precision)


def minmax(arg: collections.abc.Iterable, *args) -> tuple[typing.Any, typing.Any]:
	"""
	:param arg: The first iterable to scan
	:param args: The remaining iterables to scan
	:return: A tuple of the smallest and largest value in the collection
	"""

	if len(args) > 0:
		return minmax((arg, *args))

	try:
		iterator: typing.Iterator = iter(arg)
		vmin: typing.Any = next(iterator)
		vmax: typing.Any = vmin

		for rem in iterator:
			if rem > vmax:
				vmax = rem

			if rem < vmin:
				vmin = rem

		return vmin, vmax

	except StopIteration:
		raise ValueError('minmax() iterable argument is empty') from None
