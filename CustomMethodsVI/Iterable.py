from __future__ import annotations

import time
import typing
import collections.abc
import sys
import threading
import warnings

from . import Exceptions
from . import Misc
from .Decorators import Overload
from . import Stream


class Iterable[T](collections.abc.Sequence, collections.abc.Sized, typing.Iterable):
	"""
	Base iterable class for CM-VI iterables
	"""

	def __init__(self, collection: typing.Sized[T] | typing.Iterable[T]):
		"""
		Base iterable class for CM-VI iterables
		- Constructor -
		:param collection: The iterable to build from
		"""

		self.__buffer__: list = list(collection)

	def __contains__(self, item: T) -> bool:
		"""
		:param item: The item to search for
		:return: If the item exists within this collection
		"""

		return item in self.__buffer__

	def __eq__(self, other: Iterable[T]) -> bool:
		"""
		Checks if this instance matches another Iterable instance
		:param other: The callback instance to compare
		:return: True if both are an Iterable and their contents are equal
		"""

		return self.__buffer__ == other.__buffer__ if isinstance(other, Iterable) else False

	def __ne__(self, other: Iterable[T]) -> bool:
		"""
		Checks if this instance doesn't match another Iterable instance
		:param other: The callback instance to compare
		:return: False if both are an Iterable and their contents are equal
		"""

		return not self == other

	def __gt__(self, other: Iterable[T]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: The callback instance
		:return: If this length is greater
		"""

		return len(self) > len(other) if isinstance(other, Iterable) else NotImplemented

	def __lt__(self, other: Iterable[T]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: The callback instance
		:return: If this length is lesser
		"""

		return len(self) < len(other) if isinstance(other, Iterable) else NotImplemented

	def __ge__(self, other: Iterable[T]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: The callback instance
		:return: If this length is greater or equal
		"""

		return len(self) >= len(other) if isinstance(other, Iterable) else NotImplemented

	def __le__(self, other: Iterable[T]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: The callback instance
		:return: If this length is lesser or equal
		"""

		return len(self) <= len(other) if isinstance(other, Iterable) else NotImplemented

	def __bool__(self) -> bool:
		"""
		Converts this instance to a bool based on it's size
		:return: True if this list is not empty
		"""

		return bool(len(self))

	def __len__(self) -> int:
		"""
		:return: The length of this iterable
		"""
		return len(self.__buffer__)

	def __repr__(self) -> str:
		"""
		:return: The string representation of this list
		"""

		return repr(self.__buffer__)

	def __str__(self) -> str:
		"""
		:return: The string representation of this list
		"""

		return str(self.__buffer__)

	def __iter__(self) -> typing.Iterator[T]:
		"""
		:return: The iterator for this iterable
		"""

		return iter(self.__buffer__)

	def __delitem__(self, key: int | tuple[int, ...] | slice) -> None:
		"""
		Deletes one or more items in this collection
		:param key: The index or indices to modify
		:raises TypeError: If indices are not integers, slices, or a collection of indices
		"""

		if type(key) is tuple:
			for item in key:
				del self[item]

		elif type(key) is slice:
			start: int = 0 if key.start is None else int(key.start)
			stop: int = len(self) if key.stop is None else int(key.stop)
			step: int = 1 if key.step is None else int(key.step)

			for i in range(start, stop, step):
				self.__buffer__[i] = None

		elif type(key) is int:
			self.__buffer__[key] = None

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(key).__name__}')

		self.__buffer__.remove(None)

	def __setitem__(self, key: int | tuple[int, ...] | slice, value: T) -> None:
		"""
		Sets one or more items in this collection
		:param key: The index or indices to modify
		:param value: The value to set
		:raises TypeError: If indices are not integers, slices, or a collection of indices
		"""

		if type(key) is int:
			self.__buffer__[key] = value

		elif type(key) is tuple:
			for k in key:
				self.__buffer__[k] = value

		elif type(key) is slice:
			start: int = 0 if key.start is None else int(key.start)
			stop: int = len(self) if key.stop is None else int(key.stop)
			step: int = 1 if key.step is None else int(key.step)

			for i in range(start, stop, step):
				self.__buffer__[i] = value

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(key).__name__}')

	def __getitem__(self, item: int | slice | tuple[int, ...]) -> T | Iterable[T]:
		"""
		Gets one or more items in this collection
		:param item: The index or indices to get
		:return: If a single element, only that item, otherwise an Iterable of items
		:raises TypeError: If indices are not integers, slices, or a collection of indices
		"""

		if type(item) is int:
			return self.__buffer__[item]

		elif type(item) is tuple:
			items: list = []

			for key in item:
				result = self[key]

				if isinstance(key, (tuple, slice)):
					items.extend(result)
				else:
					items.append(result)

			return Iterable(items)

		elif type(item) is slice:
			start: int = 0 if item.start is None else int(item.start)
			stop: int = len(self) if item.stop is None else int(item.stop)
			step: int = 1 if item.step is None else int(item.step)
			items: list = []

			for i in range(start, stop, step):
				items.append(self.__buffer__[i])

			return Iterable(items)

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(item).__name__}')

	def __reversed__(self) -> reversed[T]:
		"""
		:return: A reverse iterator
		"""

		return reversed(self.__buffer__)

	def clear(self) -> None:
		"""
		Clears the collection
		"""

		self.__buffer__.clear()

	def reverse(self) -> None:
		"""
		Reverses the array in-place
		"""

		self.__buffer__.reverse()

	def count(self, item: T) -> int:
		"""
		:param item: The item to search for
		:return: The number of times an item occurs in this list
		"""

		return self.__buffer__.count(item)

	def index(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Gets the index of an item in the list
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The index of the element in this list
		:raises ValueError: If the specified value is not in this list
		"""

		return self.__buffer__.index(item, start, stop)

	def find(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Gets the index of an item in the list
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The index of the element in this list or -1 if no such element
		"""

		start: int = 0 if start is ... or start is None else int(start)
		stop: int = -1 if stop is ... or stop is None else int(stop)
		start = start if start >= 0 else len(self) + start
		stop = stop if stop >= 0 else len(self) + stop

		while start < stop:
			if self.__buffer__[start] == item:
				return start
			start += 1

		return -1

	def copy(self) -> Iterable[T]:
		"""
		:return: A copy of this collection
		"""

		return Iterable(self.__buffer__.copy())


class LinqIterable[T](Iterable, Stream.LinqStream):
	"""
	An iterable with properties of 'Iterable' and 'LinqStream'
	Supports all LINQ queries that 'LinqStream' supports
	"""

	def __init__(self, collection: typing.Sized | typing.Iterable[T]):
		"""
		An iterable with properties of 'Iterable' and 'LinqStream'
		Supports all LINQ queries that 'LinqStream' supports
		- Constructor -
		:param collection: The initial collection
		"""

		Stream.LinqStream.__init__(self, self)
		Iterable.__init__(self, collection)

	def copy(self) -> LinqIterable[T]:
		return LinqIterable(self)


class SortableIterable[T](LinqIterable):
	"""
	Class representing an iterable containing sorting functions
	"""

	def __init__(self, collection: typing.Sized | typing.Iterable[T]):
		"""
		Class representing an iterable containing sorting functions
		- Constructor -
		:param collection: The initial collection
		"""

		LinqIterable.__init__(self, collection)

	def sort(self, *, key: typing.Optional[typing.Callable] = ..., reverse: typing.Optional[bool] = False) -> None:
		"""
		Sorts the collection in-place
		:param key: (CALLABLE?) An optional callable specifying how to sort the collection
		:param reverse: (bool>) An optional bool specifying whether to sort in reversed order
		:return: (None)
		"""

		self.__buffer__.sort(key=key, reverse=reverse)

	def copy(self) -> SortableIterable[T]:
		return SortableIterable(self)


class SortedList[T](SortableIterable):
	"""
	A list using binary search to maintain a sorted list of elements
	"""

	def __init__(self, *args: T | typing.Iterable[T]):
		"""
		A list using binary search to search and maintain a sorted list of elements
		- Constructor -
		:param args: Either a variadic list of elements to use, or an iterable whose elements to use
		:raises AssertionError: If the single supplied argument is not iterable
		:raises TypeError: If the iterable's contents are not comparable
		"""

		if len(args) == 0:
			super().__init__([])
		elif len(args) == 1 and isinstance(args[0], SortedList):
			super().__init__(args[0].__buffer__.copy())
		elif len(args) == 1 and isinstance(args[0], ReverseSortedList):
			super().__init__(reversed(args[0].__buffer__))
		elif len(args) == 1:
			assert hasattr(args[0], '__iter__'), 'Set argument must be an iterable'

			try:
				super().__init__(sorted(args[0]))
			except TypeError as e:
				raise TypeError(f'One or more objects are incomparable') from e

		else:
			try:
				super().__init__(sorted(args))
			except TypeError as e:
				raise TypeError(f'One or more objects are incomparable') from e

	def __contains__(self, item: T) -> bool:
		"""
		Uses binary search to check if an item exists within this collection
		:param item: The item to search for
		:return: Whether the item exists
		"""

		return self.bin_search(item) != -1

	def __add__(self, other: typing.Iterable[T]) -> SortedList[T]:
		"""
		Adds the elements of the second iterable to this collection
		:param other: The iterable to add
		:return: A new sorted collection containing the appended elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		return self.extended(other) if hasattr(other, '__iter__') else NotImplemented

	def __iadd__(self, other: typing.Iterable[T]) -> SortedList[T]:
		"""
		Adds the elements of the second iterable to this collection in place
		:param other: The collection to add
		:return: This instance
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		if hasattr(other, '__iter__'):
			self.extend(other)
			return self
		else:
			return NotImplemented

	def __radd__(self, other: typing.Iterable[T]) -> SortedList[T]:
		"""
		Adds the elements of the second iterable to this collection
		:param other: The collection to add
		:return: A new sorted collection containing the appended elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		return self.extended(other) if hasattr(other, '__iter__') else NotImplemented

	def __mul__(self, times: int) -> SortedList[T]:
		"""
		Duplicates the elements in this collection
		:param times: The number of times to duplicate
		:return: A new sorted collection containing the duplicated elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		if isinstance(times, int):
			result: list = []
			__times: list[int] = list(range(int(times)))

			for i in range(len(self)):
				result.extend(self.__buffer__[i] for _ in __times)

			copy: SortedList = SortedList()
			copy.__buffer__ = result
			return copy
		else:
			return NotImplemented

	def __imul__(self, times: int) -> SortedList[T]:
		"""
		Duplicates the elements in this collection in place
		:param times: The number of times to duplicate
		:return: This instance
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		if isinstance(times, int):
			result: list = []
			__times: list[int] = list(range(int(times)))

			for i in range(len(self)):
				result.extend(self.__buffer__[i] for _ in __times)

			self.__buffer__ = result
			return self
		else:
			return NotImplemented

	def __rmul__(self, times: int) -> SortedList[T]:
		"""
		Duplicates the elements in this collection
		:param times: The number of times to duplicate
		:return: A new sorted collection containing the duplicated elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		if isinstance(times, int):
			result: list = []
			__times: list[int] = list(range(int(times)))

			for i in range(len(self)):
				result.extend(self.__buffer__[i] for _ in __times)

			copy: SortedList = SortedList()
			copy.__buffer__ = result
			return copy
		else:
			return NotImplemented

	def __setitem__(self, key: int | slice | tuple[int | slice, ...], value: T) -> None:
		"""
		SHOULD NOT BE USED - Alias for SortedList::append
		Adds an item into the collection using binary search
		This will throw a warning
		:param key: NOT USED, this value will be ignored
		:param value: The item to insert
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		warnings.warn('\\\\\\\nDirect insertion in binary-sorted collection\nUse \'SortedList::append\' instead \\\\\\', UserWarning, stacklevel=2)
		self.append(value)

	def append(self, item: T) -> None:
		"""
		Appends an item to this collection
		:param item: The item to append
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		length: int = len(self)

		if length == 0:
			self.__buffer__.append(item)
			return

		start: int = 0
		end: int = length

		try:
			if item >= self.__buffer__[-1]:
				self.__buffer__.append(item)
				return
			elif item <= self.__buffer__[0]:
				self.__buffer__.insert(0, item)
				return

			while True:
				mid: int = round((start + end) / 2)

				if mid >= length or mid < 0:
					raise ValueError(f'Unexpected error during binary-reduction - MIDPOINT={mid}')
				elif item == self.__buffer__[mid]:
					self.__buffer__.insert(mid, item)
					return
				elif item > self.__buffer__[mid]:
					start = mid
				elif item < self.__buffer__[mid]:
					end = mid
				else:
					raise ValueError(f'Unexpected error during binary-reduction - MIDPOINT={mid}')

		except TypeError:
			raise TypeError(f'Incomparable object of type \'{type(item)}\' is not storable')

	def extend(self, iterable: typing.Iterable[T]) -> None:
		"""
		Appends a collection of items to this collection in-place
		:param iterable: The collection to append
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		for e in iterable:
			self.append(e)

	def remove(self, item: T) -> None:
		"""
		Removes the first occurrence item from the collection
		:param item: The item to remove
		"""

		if item in self:
			self.__buffer__.remove(item)

	def remove_all(self, item: T) -> None:
		"""
		Removes all occurrences item from the collection
		:param item: The item to remove
		"""

		while item in self:
			self.__buffer__.remove(item)

	def resort(self, *iterables: typing.Iterable[T]) -> None:
		"""
		Resorts the entire collection, appending the supplied values from '*iterables' if provided
		:param iterables: The extra collections to append before resort
		:raises TypeError: If the item cannot be compared or one of the arguments is not an iterable
		"""

		for i in iterables:
			if not hasattr(i, '__iter__'):
				raise TypeError('Arguments in resort must be iterables')
			else:
				self.__buffer__.extend(i)

		self.__buffer__.sort()

	def set_resort(self, *iterables: typing.Iterable[T]) -> None:
		"""
		Resorts the entire collection using a set, appending the supplied values from '*iterables' if provided and removing duplicates
		:param iterables: The extra collections to append before resort
		:raises TypeError: If the item cannot be compared or one of the arguments is not an iterable
		"""

		buffer = set(self.__buffer__)

		for i in iterables:
			if not hasattr(i, '__iter__'):
				raise TypeError('Arguments in resort must be iterables')
			else:
				buffer.update(i)

		self.__buffer__ = list(sorted(buffer))

	def bin_search(self, item: T, lower: typing.Optional[int] = ..., upper: typing.Optional[int] = ...) -> int:
		"""
		Performs an O(log(n)) binary search for the specified item
		:param item: The item to search for
		:param lower: The index's lower bound to search in
		:param upper: The index's upper bound to search in
		:return: The position if found or -1
		"""

		if len(self) == 0 or item > self.__buffer__[-1] or item < self.__buffer__[0]:
			return -1

		__lower = 0
		__upper = len(self)
		mid = __upper // 2

		while True:
			if self[mid] == item:
				return mid
			elif mid == 0 or mid == len(self) - 1 or (lower is not ... and lower is not None and mid < lower) or (upper is not ... and upper is not None and mid > upper):
				return -1
			elif item > self[mid]:
				__lower = mid
				mid = (__lower + __upper) // 2
			elif item < self[mid]:
				__upper = mid
				mid = (__lower + __upper) // 2

	def lin_search(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Performs an O(n) linear search for the specified item
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The position if found or -1
		"""

		__lower = 0 if start is ... or start is None else int(start)
		__upper = len(self) if stop is ... or stop is None else int(stop)

		for i in range(__lower, __upper):
			if self[i] == item:
				return i

		return -1

	def rlin_search(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Performs an O(n) reversed linear search for the specified item
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The position if found or -1
		"""

		__lower = 0 if start is ... or start is None else int(start)
		__upper = len(self) if stop is ... or stop is None else int(stop)

		for i in range(__upper - 1, __lower - 1, -1):
			if self[i] == item:
				return i

		return -1

	def index(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...):
		"""
		Gets the index of an item in the collection using binary search
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The index of the element in this list
		:raises ValueError: If the specified value is not in this list
		"""

		position: int = self.bin_search(item, start, stop)

		if position == -1:
			raise ValueError(f'{item} is not in list')

		return position

	def count(self, item: T) -> int:
		"""
		:param item: The item to search for
		:return: The number of times an item occurs in this collection using binary search
		"""

		start = self.bin_search(item)

		if start == -1:
			return 0

		forward = start + 1
		backward = start - 1

		while backward >= 0 and self.__buffer__[backward] == item:
			backward -= 1

		while forward < len(self) and self.__buffer__[forward] == item:
			forward += 1

		return (forward - 1) - (backward + 1) + 1

	def get_bounds(self, item: T) -> tuple[int, int]:
		"""
		Gets the start and end index for an item in this collection
		:param item: The item to search for
		:return: The range of indices an item covers
		:raises ValueError: If the specified item is not in this list
		"""

		start = self.bin_search(item)

		if start == -1:
			raise ValueError(f'Item \'{item}\' is not in sorted list')

		forward = start + 1
		backward = start - 1

		while backward >= 0 and self.__buffer__[backward] == item:
			backward -= 1

		while forward < len(self) and self.__buffer__[forward] == item:
			forward += 1

		return backward + 1, forward - 1

	def extended(self, iterable: typing.Iterable[T]) -> SortedList[T]:
		"""
		Appends a collection of items to a copy of this collection
		:param iterable: The collection to append
		:return: The new, updated list
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		copied: SortedList[T] = SortedList(self)
		copied.extend(iterable)
		return copied

	def removed_duplicates(self) -> SortedList[T]:
		"""
		:return: A copy  of this collection with all duplicates removed
		"""

		return SortedList(set(self.__buffer__))

	def reversed(self) -> ReverseSortedList[T]:
		"""
		:return: A reversed sorted collection
		"""

		return ReverseSortedList(self)

	def pop(self, index: typing.Optional[int] = ...) -> T:
		"""
		Deletes and returns a single item from this collection
		:param index: The index to remove or the last element if not supplied
		:return: The element at that position
		"""

		return self.__buffer__.pop(-1 if index is ... or index is None else int(index))

	def copy(self) -> SortedList[T]:
		return SortedList(self)


class ReverseSortedList[T](SortableIterable):
	"""
	A list using binary search to maintain a reverse sorted list of elements
	"""

	def __init__(self, *args: T | typing.Iterable[T]):
		"""
		A list using binary search to search and maintain a reverse sorted list of elements
		- Constructor -
		:param args: Either a variadic list of elements to use, or an iterable whose elements to use
		:raises AssertionError: If the single supplied argument is not iterable
		:raises TypeError: If the iterable's contents are not comparable
		"""

		super().__init__([])

		if len(args) == 0:
			self.__buffer__ = []
		elif len(args) == 1 and isinstance(args[0], ReverseSortedList):
			self.__buffer__ = args[0].__buffer__.copy()
		elif len(args) == 1 and isinstance(args[0], SortedList):
			super().__init__(reversed(args[0].__buffer__))
		elif len(args) == 1:
			assert hasattr(args[0], '__iter__'), 'Set argument must be an iterable'

			try:
				self.__buffer__ = list(sorted(args[0], reverse=True))
			except TypeError as e:
				raise TypeError(f'One or more objects are incomparable') from e

		else:
			try:
				self.__buffer__ = list(sorted(args, reverse=True))
			except TypeError as e:
				raise TypeError(f'One or more objects are incomparable') from e

	def __contains__(self, item: T) -> bool:
		"""
		Uses binary search to check if an item exists within this collection
		:param item: The item to search for
		:return: Whether the item exists
		"""

		return self.bin_search(item) != -1

	def __add__(self, other: typing.Iterable[T]) -> ReverseSortedList[T]:
		"""
		Adds the elements of the second iterable to this collection
		:param other: The iterable to add
		:return: A new reverse sorted collection containing the appended elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		return self.extended(other) if hasattr(other, '__iter__') else NotImplemented

	def __iadd__(self, other: typing.Iterable[T]) -> ReverseSortedList[T]:
		"""
		Adds the elements of the second iterable to this collection in place
		:param other: The collection to add
		:return: This instance
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		if hasattr(other, '__iter__'):
			self.extend(other)
			return self
		else:
			return NotImplemented

	def __radd__(self, other: typing.Iterable[T]) -> ReverseSortedList[T]:
		"""
		Adds the elements of the second iterable to this collection
		:param other: The collection to add
		:return: A new reverse sorted collection containing the appended elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		return self.extended(other) if hasattr(other, '__iter__') else NotImplemented

	def __mul__(self, times: int) -> ReverseSortedList[T]:
		"""
		Duplicates the elements in this collection
		:param times: The number of times to duplicate
		:return: A new reverse sorted collection containing the duplicated elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		if isinstance(times, int):
			result: list = []
			__times: list[int] = list(range(int(times)))

			for i in range(len(self)):
				result.extend(self.__buffer__[i] for _ in __times)

			copy: ReverseSortedList = ReverseSortedList()
			copy.__buffer__ = result
			return copy
		else:
			return NotImplemented

	def __imul__(self, times: int) -> ReverseSortedList[T]:
		"""
		Duplicates the elements in this collection in place
		:param times: The number of times to duplicate
		:return: This instance
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		if isinstance(times, int):
			result: list = []
			__times: list[int] = list(range(int(times)))

			for i in range(len(self)):
				result.extend(self.__buffer__[i] for _ in __times)

			self.__buffer__ = result
			return self
		else:
			return NotImplemented

	def __rmul__(self, times: int) -> ReverseSortedList[T]:
		"""
		Duplicates the elements in this collection
		:param times: The number of times to duplicate
		:return: A new reverse sorted collection containing the duplicated elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		if isinstance(times, int):
			result: list = []
			__times: list[int] = list(range(int(times)))

			for i in range(len(self)):
				result.extend(self.__buffer__[i] for _ in __times)

			copy: ReverseSortedList = ReverseSortedList()
			copy.__buffer__ = result
			return copy
		else:
			return NotImplemented

	def __setitem__(self, key: int | slice | tuple[int | slice, ...], value: T) -> None:
		"""
		SHOULD NOT BE USED - Alias for ReverseSortedList::append
		Adds an item into the collection using binary search
		This will throw a warning
		:param key: NOT USED, this value will be ignored
		:param value: The item to insert
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		warnings.warn('\\\\\\\nDirect insertion in binary-sorted collection\nUse \'ReverseSortedList::append\' instead \\\\\\', UserWarning, stacklevel=2)
		self.append(value)

	def append(self, item: T) -> None:
		"""
		Appends an item to this collection
		:param item: The item to append
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		length: int = len(self)

		if length == 0:
			self.__buffer__.append(item)
			return

		start: int = 0
		end: int = length

		try:
			if item >= self.__buffer__[0]:
				self.__buffer__.insert(0, item)
				return
			elif item <= self.__buffer__[-1]:
				self.__buffer__.append(item)
				return

			while True:
				mid: int = round((start + end) / 2)

				if mid >= length or mid < 0:
					raise ValueError(f'Unexpected error during binary-reduction - MIDPOINT={mid}')
				elif item == self.__buffer__[mid]:
					self.__buffer__.insert(mid, item)
					return
				elif item < self.__buffer__[mid]:
					start = mid
				elif item > self.__buffer__[mid]:
					end = mid
				else:
					raise ValueError(f'Unexpected error during binary-reduction - MIDPOINT={mid}')

		except TypeError:
			raise TypeError(f'Incomparable object of type \'{type(item)}\' is not storable')

	def extend(self, iterable: typing.Iterable[T]) -> None:
		"""
		Appends a collection of items to this collection in-place
		:param iterable: The collection to append
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		for e in iterable:
			self.append(e)

	def remove(self, item: T) -> None:
		"""
		Removes the first occurrence item from the collection
		:param item: The item to remove
		"""

		if item in self:
			self.__buffer__.remove(item)

	def remove_all(self, item: T) -> None:
		"""
		Removes all occurrences item from the collection
		:param item: The item to remove
		"""

		while item in self:
			self.__buffer__.remove(item)

	def resort(self, *iterables: typing.Iterable[T]) -> None:
		"""
		Resorts the entire collection, appending the supplied values from '*iterables' if provided
		:param iterables: The extra collections to append before resort
		:raises TypeError: If the item cannot be compared or one of the arguments is not an iterable
		"""

		for i in iterables:
			if not hasattr(i, '__iter__'):
				raise TypeError('Arguments in resort must be iterables')
			else:
				self.__buffer__.extend(i)

		self.__buffer__.sort(reverse=True)

	def set_resort(self, *iterables: typing.Iterable[T]) -> None:
		"""
		Resorts the entire collection, appending the supplied values from '*iterables' if provided and removing duplicates
		:param iterables: The extra collections to append before resort
		:raises TypeError: If the item cannot be compared or one of the arguments is not an iterable
		"""

		buffer = set(self.__buffer__)

		for i in iterables:
			if not hasattr(i, '__iter__'):
				raise TypeError('Arguments in resort must be iterables')
			else:
				buffer.update(i)

		self.__buffer__ = list(sorted(buffer, reverse=True))

	def bin_search(self, item: T, lower: typing.Optional[int] = ..., upper: typing.Optional[int] = ...) -> int:
		"""
		Performs an O(log(n)) binary search for the specified item
		:param item: The item to search for
		:param lower: The index's lower bound to search in
		:param upper: The index's upper bound to search in
		:return: The position if found or -1
		"""

		if len(self) == 0 or item < self.__buffer__[-1] or item > self.__buffer__[0]:
			return -1

		__lower = 0
		__upper = len(self)
		mid = __upper // 2

		while True:
			if self[mid] == item:
				return mid
			elif mid == 0 or mid == len(self) - 1 or (lower is not ... and lower is not None and mid < lower) or (upper is not ... and upper is not None and mid > upper):
				return -1
			elif item < self[mid]:
				__lower = mid
				mid = (__lower + __upper) // 2
			elif item > self[mid]:
				__upper = mid
				mid = (__lower + __upper) // 2

	def lin_search(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Performs an O(n) linear search for the specified item
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The position if found or -1
		"""

		__lower = 0 if start is ... or start is None else int(start)
		__upper = len(self) if stop is ... or stop is None else int(stop)

		for i in range(__lower, __upper):
			if self[i] == item:
				return i

		return -1

	def rlin_search(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Performs an O(n) reversed linear search for the specified item
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The position if found or -1
		"""

		__lower = 0 if start is ... or start is None else int(start)
		__upper = len(self) if stop is ... or stop is None else int(stop)

		for i in range(__upper - 1, __lower - 1, -1):
			if self[i] == item:
				return i

		return -1

	def index(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...):
		"""
		Gets the index of an item in the collection using binary search
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The index of the element in this list
		:raises ValueError: If the specified value is not in this list
		"""

		position: int = self.bin_search(item, start, stop)

		if position == -1:
			raise ValueError(f'{item} is not in list')

		return position

	def count(self, item: T) -> int:
		"""
		:param item: The item to search for
		:return: The number of times an item occurs in this collection using binary search
		"""

		start = self.bin_search(item)

		if start == -1:
			return 0

		forward = start + 1
		backward = start - 1

		while backward >= 0 and self.__buffer__[backward] == item:
			backward -= 1

		while forward < len(self) and self.__buffer__[forward] == item:
			forward += 1

		return (forward - 1) - (backward + 1) + 1

	def get_bounds(self, item: T) -> tuple[int, int]:
		"""
		Gets the start and end index for an item in this collection
		:param item: The item to search for
		:return: The range of indices an item covers
		:raises ValueError: If the specified item is not in this list
		"""

		start = self.bin_search(item)

		if start == -1:
			raise ValueError(f'Item \'{item}\' is not in sorted list')

		forward = start + 1
		backward = start - 1

		while backward >= 0 and self.__buffer__[backward] == item:
			backward -= 1

		while forward < len(self) and self.__buffer__[forward] == item:
			forward += 1

		return backward + 1, forward - 1

	def extended(self, iterable: typing.Iterable[T]) -> ReverseSortedList[T]:
		"""
		Appends a collection of items to a copy of this collection
		:param iterable: The collection to append
		:return: The new, updated list
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		copied: ReverseSortedList[T] = ReverseSortedList(self)
		copied.extend(iterable)
		return copied

	def removed_duplicates(self) -> ReverseSortedList[T]:
		"""
		:return: A copy  of this list with all duplicates removed
		"""

		return ReverseSortedList(set(self.__buffer__))

	def reversed(self) -> SortedList[T]:
		"""
		:return: A normally sorted collection
		"""

		return SortedList(self)

	def pop(self, index: typing.Optional[int] = ...) -> T:
		"""
		Deletes and returns a single item from this collection
		:param index: The index to remove or the last element if not supplied
		:return: The element at that position
		"""

		return self.__buffer__.pop(-1 if index is ... or index is None else int(index))

	def copy(self) -> ReverseSortedList[T]:
		return ReverseSortedList(self)


class String(Iterable[int]):
	"""
	A class providing extended string functionality
	"""

	@Overload
	def __init__(self, string: str | bytes | bytearray | typing.Iterable[int | str] = ''):
		"""
		A class providing extended string functionality
		- Constructor -
		Depending on the specified value, iteration will yield a str, bytes-like, or int
		:param string: The string to use; either a string, bytes object, bytearray, or iterable of characters or integers
		:raises TypeError: If 'string' is not a string, bytes, bytearray, or an iterable characters or integers
		"""

		if isinstance(string, str):
			super().__init__([ord(c) for c in string])
			self.__cls__ = str
		elif isinstance(string, (bytes, bytearray)):
			super().__init__(string)
			self.__cls__ = bytes
		elif hasattr(string, '__iter__') and (string := tuple(string)) is not None and all(isinstance(x, int) or (isinstance(x, str) and len(x) == 1) for x in string):
			super().__init__(int(x) for x in string)
			self.__cls__ = int
		else:
			raise TypeError('String is not a string, bytes object, bytearray, or iterable of characters or integers')

		self.__buffer__: list[int]

	def __contains__(self, item: str | String | bytes | bytearray | int) -> bool:
		"""
		:param item: The substring or character code to check
		:return: Whether a substring or character is within this string
		:raises TypeError: If 'item' is not a string, bytes object, bytearray, or integer
		"""

		char: tuple[int, ...] = (item,) if isinstance(item, int) else tuple(ord(c) for c in item) if isinstance(item, str) else tuple(item) if isinstance(item, (bytes, bytearray)) else None
		this_length: int = len(self)
		length: int = len(char)

		if char is None:
			raise TypeError(f'\'item\' must be one of: str, bytes, bytearray, int - got \'{type(item)}\'')

		for i in range(this_length - length + 1):
			if tuple(self.__buffer__[i:i + length]) == char:
				return True

		return False

	def __int__(self, base: int = 10) -> int:
		"""
		:param base: The base to convert to
		:return: The integer value of this string
		"""
		return int(str(self), base)

	def __float__(self) -> float:
		"""
		:return: The floating-point value of this string
		"""
		return float(str(self))

	def __bytes__(self) -> bytes:
		"""
		:return: This string as a bytes-like instance
		"""

		return bytes(self.__buffer__)

	def __iter__(self) -> typing.Generator[str]:
		for x in self.__buffer__:
			yield chr(x) if self.__cls__ is str else x.to_bytes(1, sys.byteorder, signed=False) if self.__cls__ is bytes else x

	def __str__(self) -> str:
		return ''.join(chr(x) for x in self.__buffer__)

	def __repr__(self) -> str:
		quotes: str = '"""' if '\'' in self and '"' in self else '\'' if '"' in self else '"'
		return f'{quotes}{str(self)}{quotes}'

	def __add__(self, other: str | bytes | bytearray | String) -> String:
		"""
		Adds a string, bytes-like or String instance to this String
		:param other: The string to add
		:return: The concatenated string
		"""

		cls = type(self)

		if isinstance(other, (str, bytes, bytearray)):
			copy: String = cls()
			copy.__buffer__ = self.__buffer__ + ([ord(c) for c in other] if isinstance(other, str) else list(other))
			return copy
		elif isinstance(other, cls):
			copy: String = cls()
			copy.__buffer__ = self.__buffer__ + other.__buffer__
			return copy
		else:
			return NotImplemented

	def __iadd__(self, other: str | bytes | bytearray | String) -> String:
		"""
		Adds a string, bytes-like or String instance to this String in-place
		:param other: The string to add
		:return: This instance
		"""

		cls = type(self)

		if isinstance(other, (str, bytes, bytearray)):
			self.__buffer__ += ([ord(c) for c in other] if isinstance(other, str) else list(other))
			return self
		elif isinstance(other, cls):
			self.__buffer__ += other.__buffer__
			return self
		else:
			return NotImplemented

	def __radd__(self, other: str | bytes | bytearray | String) -> str | bytes | bytearray | String:
		"""
		Adds this String to another string, bytes-like, or String instance
		:param other: The buffer to add this String to
		:return: A new, updated buffer whose type matches the specified argument
		"""

		cls = type(self)

		if isinstance(other, str):
			return other + str(self)
		elif isinstance(other, (bytes, bytearray)):
			return other + bytes(self)
		elif isinstance(other, cls):
			copy: String = cls()
			copy.__buffer__ = other.__buffer__ + self.__buffer__
			return copy
		else:
			return NotImplemented

	def __mul__(self, n: int) -> String:
		"""
		Multiplies the string 'n' times
		:param n: The number of times to multiply
		:return: The multiplied String instance
		"""

		if not isinstance(n, int):
			return NotImplemented

		copy: String = type(self)()
		copy.__buffer__ = self.__buffer__ * n
		return copy

	def __imul__(self, n: int) -> String:
		"""
		Multiplies the string 'n' times in-place
		:param n: The number of times to multiply
		:return: This instance
		"""

		if not isinstance(n, int):
			return NotImplemented

		self.__buffer__ *= n
		return self

	def __rmul__(self, n: int) -> String:
		"""
		Multiplies the string 'n' times
		:param n: The number of times to multiply
		:return: The multiplied String instance
		"""

		if not isinstance(n, int):
			return NotImplemented

		copy: String = type(self)()
		copy.__buffer__ = self.__buffer__ * n
		return copy

	def __getitem__(self, item: int) -> str | bytes | bytearray | int | String:
		"""
		Gets one or more characters in this string
		:param item: The index or indices to get
		:return: If a single element, only that item, otherwise a substring
		"""

		if isinstance(item, int):
			x: int = self.__buffer__[item]
			return chr(x) if self.__cls__ is str else x.to_bytes(1, sys.byteorder, signed=False) if self.__cls__ is bytes else x
		else:
			return super().__getitem__(item)

	def __setitem__(self, key: int, value: str | bytes | bytearray | int | String):
		"""
		Sets one or more characters in this string
		:param key: The index or indices to modify
		:param value: The value to set
		"""

		raise NotImplementedError()

	def can_be_int(self) -> bool:
		"""
		:return: Whether this value can be converted to a base-10 integer
		"""

		return all(chr(c).isdigit() for c in self.__buffer__)

	def can_be_float(self) -> bool:
		"""
		:return: Whether this value can be converted to a base-10 decimal
		"""

		try:
			float(str(self))
			return True
		except ValueError:
			return False

	def starts_with(self, prefix: str | bytes | bytearray | String) -> bool:
		"""
		:param prefix: The prefix to check
		:return: Whether this string starts with 'prefix'
		:raises InvalidArgumentException: If 'prefix' is not a string, bytes object, bytearray, or String instance
		"""

		Misc.raise_ifn(isinstance(prefix, (str, bytes, bytearray, String)), Exceptions.InvalidArgumentException(String.starts_with, 'prefix', type(prefix), (str, bytes, bytearray, String)))

		if len(prefix) > len(self):
			return False

		for i, char in enumerate(self):
			prefix_char: str = prefix[i] if isinstance(prefix, (str, String)) else chr(prefix[i])

			if prefix_char != char:
				return False

		return True

	def ends_with(self, postfix: str | String) -> bool:
		"""
		:param postfix: The postfix to check
		:return: Whether this string ends with 'postfix'
		:raises InvalidArgumentException: If 'postfix' is not a string, bytes object, bytearray, or String instance
		"""

		Misc.raise_ifn(isinstance(postfix, (str, bytes, bytearray, String)), Exceptions.InvalidArgumentException(String.ends_with, 'postfix', type(postfix), (str, bytes, bytearray, String)))

		if len(postfix) > len(self):
			return False

		for i in range(len(self) - 1, len(self) - len(postfix), -1):
			postfix_char: str = postfix[i] if isinstance(postfix, (str, String)) else chr(postfix[i])

			if postfix_char != self[i]:
				return False

		return True

	def left_pad(self, length: int, pad_char: str | bytes | bytearray | int | String = ' ') -> String:
		"""
		Left pads this string with the specified character until equal to the specified length
		:param length: The length to match
		:param pad_char: The character to pad with (defaults to space)
		:return: The padded String
		:raises ValueError: If the pad character's length is greater than 1
		:raises TypeError: If 'pad_char' is not a string, bytes object, bytearray, String instance, or integer
		"""

		if not isinstance(pad_char, (str, bytes, bytearray, int, String)):
			raise Exceptions.InvalidArgumentException(String.left_pad, 'pad_char', type(pad_char), (str, bytes, bytearray, int, String))
		elif isinstance(pad_char, (str, bytes, bytearray, String)) and len(pad_char) > 1:
			raise ValueError(f'Character must be of length 1 - got length {len(pad_char)}')
		elif isinstance(pad_char, (str, bytes, bytearray, String)) and len(pad_char) == 0:
			return self.copy()

		char: int = pad_char if isinstance(pad_char, int) else ord(pad_char) if isinstance(pad_char, str) else pad_char[0]
		copy: String = self.copy()

		while len(self) < length:
			copy.__buffer__.append(char)

		return copy

	def right_pad(self, length: int, pad_char: str | bytes | bytearray | int = ' ') -> String:
		"""
		Right pads this string with the specified character until equal to the specified length
		:param length: The length to match
		:param pad_char: The character to pad with (defaults to space)
		:return: The padded String
		:raises ValueError: If the pad character's length is greater than 1
		:raises TypeError: If 'pad_char' is not a string, bytes object, bytearray, String instance, or integer
		"""

		if not isinstance(pad_char, (str, bytes, bytearray, int, String)):
			raise Exceptions.InvalidArgumentException(String.left_pad, 'pad_char', type(pad_char), (str, bytes, bytearray, int, String))
		elif isinstance(pad_char, (str, bytes, bytearray, String)) and len(pad_char) > 1:
			raise ValueError(f'Character must be of length 1 - got length {len(pad_char)}')
		elif isinstance(pad_char, (str, bytes, bytearray, String)) and len(pad_char) == 0:
			return self.copy()

		char: int = pad_char if isinstance(pad_char, int) else ord(pad_char) if isinstance(pad_char, str) else pad_char[0]
		copy: String = self.copy()

		while len(self) < length:
			copy.__buffer__.insert(0, char)

		return copy

	def to_upper(self) -> String:
		"""
		:return: The uppercase string
		"""

		return String(ord(chr(c).upper()) for c in self.__buffer__)

	def to_lower(self) -> String:
		"""
		:return: The lowercase string
		"""

		return String(ord(chr(c).lower()) for c in self.__buffer__)

	def capitalized(self) -> String:
		"""
		:return: The capitalized string
		"""

		if len(self) == 0:
			return self.copy()

		copy: String = self.copy()
		copy.__buffer__[0] = ord(chr(copy.__buffer__[0]).upper())
		return copy

	def substring(self, start: int, length: typing.Optional[int] = ...) -> String:
		"""
		:param start: The start index
		:param length: The substring length
		:return: A substring 'length' characters long starting from 'start'
		"""

		return self[start:start + length]

	def copy(self) -> String:
		"""
		:return: A copy of this String instance
		"""

		return String(self.__buffer__.copy())


class FixedArray[T](SortableIterable):
	"""
	Class representing an array of a fixed size
	"""

	def __init__(self, iterable_or_size: typing.Iterable[T] | int):
		"""
		Class representing an array of a fixed size
		- Constructor -
		:param iterable_or_size: The iterable or number of elements this list contains
		:raises TypeError: If 'iterable_or_size' is not a positive integer or iterable
		"""

		if isinstance(iterable_or_size, int) and (iterable_or_size := int(iterable_or_size)) > 0:
			super().__init__([None] * iterable_or_size)
			self.__size__: int = iterable_or_size
		elif hasattr(iterable_or_size, '__iter__'):
			super().__init__(iterable_or_size)
			self.__size__: int = len(self.__buffer__)
		else:
			raise TypeError('Iterable or size must be an iterable or positive integer')

	def __len__(self) -> int:
		"""
		:return: The size of this array
		"""

		return self.__size__

	def __delitem__(self, key: int | tuple[int, ...] | slice) -> None:
		"""
		Deletes one or more items in this list
		Deleted items are assigned 'None'
		:param key: The index or indices to modify
		"""

		self[key] = None

	def clear(self) -> None:
		"""
		Clears the list, setting all elements to 'None'
		"""

		for i in range(len(self)):
			self.__buffer__[i] = None

	def copy(self) -> FixedArray[T]:
		return FixedArray(self)


class SpinQueue[T](SortableIterable):
	"""
	Class representing a queue-like array of a maximum size
	"""

	def __init__(self, iterable_or_size: typing.Iterable[T] | int):
		"""
		Class representing an array of a fixed size
		- Constructor -
		:param iterable_or_size: The iterable or number of elements this list contains
		:raises TypeError: If 'iterable_or_size' is not a positive integer or iterable
		"""

		if isinstance(iterable_or_size, int) and (iterable_or_size := int(iterable_or_size)) > 0:
			super().__init__([None] * iterable_or_size)
			self.__max_size__: int = iterable_or_size
			self.__count__: int = 0
			self.__offset__: int = 0
		elif hasattr(iterable_or_size, '__iter__'):
			super().__init__(iterable_or_size)
			self.__max_size__: int = len(self.__buffer__)
			self.__count__: int = 0
			self.__offset__: int = 0
		else:
			raise TypeError('Iterable or size must be an iterable or positive integer')

	def __iter__(self):
		for i in range(self.__count__):
			yield self[i]

	def __len__(self) -> int:
		return self.__count__

	def __str__(self) -> str:
		return str(list(self))

	def __repr__(self) -> str:
		return str(self)

	def __getitem__(self, index: int) -> T:
		"""
		Gets one item from this collection
		:param index: The index to get
		:return: The element at the specified index
		:raises TypeError: If indices are not integers
		"""

		if not isinstance(index, int):
			raise TypeError(f'SpinQueue indices must be of type int, got \'{type(index)}\'')
		elif index >= self.__count__:
			raise IndexError(f'Specified index \'{index}\' is out of bounds for SpinQueue of count \'{self.__count__}\'')

		return self.__buffer__[(self.__offset__ + ((self.__count__ + index) if index < 0 else index)) % self.__max_size__]

	def __setitem__(self, index: int, value: T) -> None:
		"""
		Sets one item into this collection
		:param index: The index to set
		:raises TypeError: If indices are not integers
		"""

		if not isinstance(index, int):
			raise TypeError(f'SpinQueue indices must be of type int, got \'{type(index)}\'')
		elif index >= self.__count__:
			raise IndexError(f'Specified index \'{index}\' is out of bounds for SpinQueue of count \'{self.__count__}\'')

		self.__buffer__[(self.__offset__ + index) % self.__max_size__] = value

	def __delitem__(self, index: int) -> None:
		"""
		Deletes one item into this collection
		Item is set to 'None'
		:param index: The index to set
		:raises TypeError: If indices are not integers
		"""

		self[index] = None

	def append(self, item: T) -> tuple[bool, T]:
		"""
		Pushes an item onto the queue and returns the first item if max size is exceeded
		:param item: The item to append
		:return: A tuple indicating whether an item was popped and the item
		"""

		overwrite: bool = self.__count__ == self.__max_size__
		position: int = (self.__offset__ + self.__count__) % self.__max_size__
		old_elem: T = self.__buffer__[position] if overwrite else None
		self.__buffer__[position] = item
		# print(overwrite, item)
		self.__count__ += not overwrite
		self.__offset__ += overwrite
		return overwrite, old_elem

	def clear(self) -> None:
		"""
		Clears the collection
		All elements are set to 'None'
		"""

		self.__count__ = 0
		self.__offset__ = 0

		for i in range(self.__max_size__):
			self.__buffer__[i] = None

	def pop(self) -> T:
		"""
		Pops an item from the queue
		:return: The popped item
		:raises IterableEmptyException: If the collection is empty
		"""

		if self.__count__ == 0:
			raise Exceptions.IterableEmptyException('Pop from empty queue')

		self.__count__ -= 1
		position: int = (self.__offset__ + self.__count__) % self.__max_size__
		elem: T = self.__buffer__[position]
		self.__buffer__[position] = None
		return elem

	@property
	def size(self) -> int:
		"""
		:return: The maximum size of this queue
		"""

		return self.__max_size__


class ThreadedGenerator[T]:
	"""
	Special generator using threading.Thread threads
	"""

	def __init__(self, generator: typing.Generator | typing.Iterable[T]):
		"""
		Special generator using threading.Thread threads
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


def frange(start: float, stop: float = None, step: float = 1, precision: int = None) -> typing.Generator[float, None, None]:
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

	if precision is None:
		precision: int = 0
		pstep: float = _step

		while pstep != int(pstep):
			precision += 1
			pstep *= 10

	while a < _stop:
		yield a
		a = round(a + _step, precision)

def minmax(arg: typing.Iterable, *args) -> tuple[typing.Any, typing.Any]:
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