from __future__ import annotations

import collections.abc
import re
import sys
import time
import threading
import typing
import warnings

from . import Exceptions
from . import Misc
from . import Stream
from . import Synchronization


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

		return self.__buffer__ == other.__buffer__ if isinstance(other, Sequence) else False

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
		:return: True if this list is not empty
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


class Sequence[T](Iterable[list[T], T], collections.abc.Sequence[T]):
	"""
	Base iterable class for CM-VI sequences
	"""

	def __init__(self, collection: collections.abc.Iterable[T] = ...):
		"""
		Base iterable class for CM-VI sequences\n
		- Constructor -
		:param collection: The sequence to build from
		"""

		super().__init__([] if collection is None or collection is ... else list(collection))

	def __repr__(self) -> str:
		"""
		:return: The string representation of this sequence
		"""

		return repr(self.__buffer__)

	def __str__(self) -> str:
		"""
		:return: The string representation of this sequence
		"""

		return str(self.__buffer__)

	def __getitem__(self, item: int | slice | tuple[int, ...]) -> T | Sequence[T]:
		"""
		Gets one or more items in this sequence
		:param item: The index or indices to get
		:return: If a single element, only that item, otherwise a Sequence of items
		:raises TypeError: If indices are not integers, slices, or a sequence of indices
		"""

		if isinstance(item, int):
			return self.__buffer__[item]

		elif isinstance(item, tuple):
			items: list = []

			for key in item:
				result = self[key]

				if isinstance(key, (tuple, slice)):
					items.extend(result)
				else:
					items.append(result)

			return Sequence(items)

		elif isinstance(item, slice):
			start: int = 0 if item.start is None else int(item.start)
			stop: int = len(self) if item.stop is None else int(item.stop)
			step: int = 1 if item.step is None else int(item.step)
			items: list = []

			for i in range(start, stop, step):
				items.append(self.__buffer__[i])

			return Sequence(items)

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(item).__name__}')

	def __reversed__(self) -> reversed[T]:
		"""
		:return: A reverse iterator
		"""

		return reversed(self.__buffer__)

	def count(self, item: T) -> int:
		"""
		:param item: The item to search for
		:return: The number of times an item occurs in this sequence
		"""

		return self.__buffer__.count(item)

	def index(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Gets the index of an item in the sequence
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The index of the element in this sequence
		:raises ValueError: If the specified value is not in this sequence
		"""

		return self.__buffer__.index(item, start, stop)

	def find(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Gets the index of an item in the sequence
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The index of the element in this sequence or -1 if no such element
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

	def copy[I: Sequence](self: I) -> I:
		"""
		:return: A copy of this sequence
		"""

		return type(self)(self.__buffer__.copy())

	def get_or_default(self, index: int, default: typing.Optional[T] = None) -> typing.Optional[T]:
		"""
		Gets the item at the specified index or 'default' if index out of bounds
		:param index: The index to retrieve
		:param default: The default item to return if index out of bounds
		:return: The item at 'index' or 'default' if out of bounds
		"""

		length: int = len(self)
		index = length + index if index < 0 else index
		return default if index >= length else self[index]

	def stream(self) -> Stream.LinqStream[T]:
		"""
		:return: A new LinqStream for queries on this sequence
		"""

		return Stream.LinqStream(self)


class MutableSequence[T](Sequence[T], collections.abc.MutableSequence[T]):
	"""
	Sequence class allowing modifications
	"""

	def __delitem__(self, key: int | tuple[int, ...] | slice) -> None:
		"""
		Deletes one or more items in this sequence
		:param key: The index or indices to modify
		:raises TypeError: If indices are not integers, slices, or a tuple of indices
		"""

		if isinstance(key, tuple):
			for item in key:
				del self[item]

		elif isinstance(key, slice):
			length: int = len(self.__buffer__)
			start: int = 0 if key.start is None else int(key.start)
			stop: int = len(self) if key.stop is None else int(key.stop)
			step: int = 1 if key.step is None else int(key.step)
			start = (length + start) if start < 0 else start
			stop = (length + stop) if stop < 0 else stop
			count: int = 0

			for i in range(start, stop, step):
				index: int = i - count

				if index >= length - count:
					break

				del self.__buffer__[index]
				count += 1

		elif isinstance(key, int):
			del self.__buffer__[key]

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(key).__name__}')

	def __setitem__(self, key: int | tuple[int, ...] | slice, value: T) -> None:
		"""
		Sets one or more items in this sequence
		:param key: The index or indices to modify
		:param value: The value to set
		:raises TypeError: If indices are not integers, slices, or a tuple of indices
		"""

		if isinstance(key, int):
			self.__buffer__[key] = value

		elif isinstance(key, tuple):
			for k in key:
				self[k] = value

		elif isinstance(key, slice):
			start: int = 0 if key.start is None else int(key.start)
			stop: int = len(self) if key.stop is None else int(key.stop)
			step: int = 1 if key.step is None else int(key.step)

			for i in range(start, stop, step):
				self.__buffer__[i] = value

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(key).__name__}')

	def __add__(self, other: typing.Iterable[T]) -> MutableSequence[T]:
		"""
		Appends an iterable to the end of this sequence
		:param other: The other iterable to append
		:return: The extended sequence
		"""

		return type(self)([*self, *other]) if isinstance(other, typing.Iterable) else NotImplemented

	def __iadd__(self, other: typing.Iterable[T]) -> MutableSequence[T]:
		"""
		Appends an iterable to the end of this sequence in-place
		:param other: The other iterable to append
		:return: This sequence
		"""

		if not isinstance(other, typing.Iterable):
			return NotImplemented

		self.__buffer__.extend(other)
		return self

	def __radd__(self, other: typing.Iterable[T]) -> MutableSequence[T]:
		"""
		Appends this sequence to the end of an iterable
		:param other: The other iterable to append to
		:return: The extended sequence
		"""

		return type(self)([*other, *self]) if isinstance(other, typing.Iterable) else NotImplemented

	def __mul__(self, other: int) -> MutableSequence[T]:
		"""
		Multiplies this sequence 'n' times
		:param other: The amount of times to multiply
		:return: The multiplied sequence
		"""

		return type(self)(self.__buffer__ * int(other)) if isinstance(other, int) else NotImplemented

	def __imul__(self, other: int) -> MutableSequence[T]:
		"""
		Multiplies this sequence 'n' times in-place
		:param other: The amount of times to multiply
		:return: This sequence
		"""

		self.__buffer__ *= int(other)
		return self

	def __rmul__(self, other: int) -> MutableSequence[T]:
		"""
		Multiplies this sequence 'n' times
		:param other: The amount of times to multiply
		:return: The multiplied sequence
		"""

		return type(self)(self.__buffer__ * int(other)) if isinstance(other, int) else NotImplemented

	def clear(self) -> None:
		"""
		Clears the sequence
		"""

		self.__buffer__.clear()

	def reverse(self) -> None:
		"""
		Reverses the sequence in-place
		"""

		self.__buffer__.reverse()

	def remove(self, element: T, count: int = -1) -> int:
		"""
		Removes the specified element from this sequence
		:param element: The element to remove
		:param count: The number of occurrences to remove or all if less than 0
		:return: The number of occurrences removed
		"""

		matches: int = 0

		for i in range(len(self)):
			if i < len(self) and self.__buffer__[i] == element:
				del self.__buffer__[i]
				matches += 1

			if 0 <= count <= matches:
				break

		return matches

	def pop(self, index: int = -1) -> T:
		"""
		Removes and returns the element at the specified index
		:param index: The index or last element if not specified
		:return: The removed element
		"""

		return self.__buffer__.pop(index)

	def append(self, element: T) -> MutableSequence[T]:
		"""
		Appends an item at the end of the sequence
		:param element: The element to append
		:return: This sequence
		"""

		self.__buffer__.append(element)
		return self

	def extend(self, iterable: T) -> MutableSequence[T]:
		"""
		Appends all elements from an iterable to the end of this sequence
		:param iterable: The iterable whose elements to insert
		:return: This sequence
		"""

		for element in iterable:
			self.append(element)

		return self

	def insert(self, index: int, element: T) -> MutableSequence[T]:
		"""
		Inserts an element into the sequence at the specified index
		:param index: The index to insert to
		:param element: The element to insert
		:return: This sequence
		"""

		self.__buffer__.insert(index, element)
		return self


class SortableSequence[T](MutableSequence[T]):
	"""
	Class representing an iterable containing sorting functions
	"""

	def sort(self, *, key: typing.Optional[typing.Callable] = ..., reverse: typing.Optional[bool] = False) -> SortableSequence[T]:
		"""
		Sorts the sequence in-place
		:param key: An optional callable specifying how to sort the collection
		:param reverse: An optional bool specifying whether to sort in reversed order
		:return: This sequence
		"""

		self.__buffer__.sort(key=key, reverse=reverse)
		return self


class SortedList[T](SortableSequence[T]):
	"""
	A list using binary search to maintain a sorted list of elements
	"""

	def __init__(self, *args: T | typing.Iterable[T]):
		"""
		A list using binary search to search and maintain a sorted list of elements\n
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

	def reversed(self) -> ReverseSortedList[T]:
		"""
		:return: A reversed sorted collection
		"""

		return ReverseSortedList(self)


class ReverseSortedList[T](SortableSequence[T]):
	"""
	A list using binary search to maintain a reverse sorted list of elements
	"""

	def __init__(self, *args: T | typing.Iterable[T]):
		"""
		A list using binary search to search and maintain a reverse sorted list of elements\n
		- Constructor -
		:param args: Either a variadic list of elements to use, or an iterable whose elements to use
		:raises AssertionError: If the single supplied argument is not iterable
		:raises TypeError: If the iterable's contents are not comparable
		"""

		if len(args) == 0:
			super().__init__([])
		elif len(args) == 1 and isinstance(args[0], ReverseSortedList):
			super().__init__(args[0].__buffer__.copy())
		elif len(args) == 1 and isinstance(args[0], SortedList):
			super().__init__(reversed(args[0].__buffer__))
		elif len(args) == 1:
			assert hasattr(args[0], '__iter__'), 'Set argument must be an iterable'

			try:
				super().__init__(sorted(args[0], reverse=True))
			except TypeError as e:
				raise TypeError(f'One or more objects are incomparable') from e

		else:
			try:
				super().__init__(sorted(args[0], reverse=True))
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

	def reversed(self) -> SortedList[T]:
		"""
		:return: A normally sorted collection
		"""

		return SortedList(self)


class String(MutableSequence[str], str):
	"""
	An extension adding additional string functionality
	"""

	class __Stringify__:
		def __init__(self, callback: typing.Callable):
			self.__callback__: typing.Callable = callback

		def __call__(self, *args, **kwargs) -> typing.Any:
			result: typing.Any = self.__callback__(*args, **kwargs)
			return String(result) if isinstance(result, Sequence) and all(isinstance(x, str) for x in result) else result

	def __init__(self, string: typing.Optional[typing.Any] = None):
		"""
		An extension adding additional string functionality\n
		- Constructor -
		:param string: The input value to convert to a string
		"""

		super().__init__([] if string is ... or string is None else list(str(string)))

	def __contains__(self, substr: str | String) -> bool:
		return isinstance(substr, (str, String)) and self.index(substr) >= 0

	def __eq__(self, other: str | String) -> bool:
		return isinstance(other, (str, String)) and str(other) == str(self)

	def __float__(self) -> float:
		return float(str(self))

	def __complex__(self) -> complex:
		return complex(str(self))

	def __int__(self) -> int:
		return int(str(self))

	def __str__(self) -> str:
		return ''.join(self)

	def __repr__(self) -> str:
		return repr(str(self))

	def __iadd__(self, other: str | String) -> String:
		if not isinstance(other, (str, String)):
			return NotImplemented

		super().__iadd__(other)
		return self

	def __imul__(self, other: int) -> String:
		super().__imul__(other)
		return self

	def __lshift__(self, other: str | String) -> String:
		if isinstance(other, String):
			self.append(other.pop())
		elif isinstance(other, str):
			return String(self + other)
		else:
			return NotImplemented

	def __rshift__(self, other: String) -> String:
		if not isinstance(other, String):
			return NotImplemented

		other.append(self.pop())
		return other

	def __setitem__(self, key: int | tuple[int, ...] | slice, value: str | String) -> None:
		"""
		Sets one or more items in this collection
		:param key: The index or indices to modify
		:param value: The value to set
		:raises TypeError: If indices are not integers, slices, or a collection of indices
		"""

		Misc.raise_ifn(isinstance(value, (bytes, bytearray, ByteString)) or (isinstance(value, int) and 0 <= (value := int(value)) <= 255), ValueError('String set item value must be either a string or String instance'))

		if isinstance(key, int) and len(value) == 1:
			self.__buffer__[key] = str(value)
		elif isinstance(key, int):
			key = int(key)

			for i, char in enumerate(value):
				self.__buffer__.insert(key + i, char)

		elif isinstance(key, tuple):
			for k in key:
				self[k] = value

		elif isinstance(key, slice):
			start: int = 0 if key.start is None else int(key.start)
			stop: int = len(self) if key.stop is None else int(key.stop)
			step: int = 1 if key.step is None else int(key.step)
			index: int = 0

			for i in range(start, stop, step):
				element: str = value[index % len(value)]
				self.__buffer__[i] = element
				index += 1

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(key).__name__}')

	def __getitem__(self, item: int | slice | tuple[int, ...]) -> str | Sequence[str] | String:
		"""
		Gets one or more items in this collection
		:param item: The index or indices to get
		:return: If a single element, only that character; if multiple non-continuous elements, an iterable of characters; otherwise a substring
		:raises TypeError: If indices are not integers, slices, or a collection of indices
		"""

		if isinstance(item, int):
			return self.__buffer__[item]

		elif isinstance(item, tuple):
			items: list = []

			for key in item:
				result = self[key]

				if isinstance(key, (tuple, slice)):
					items.extend(result)
				else:
					items.append(result)

			return Sequence(items)

		elif isinstance(item, slice):
			start: int = 0 if item.start is None else int(item.start)
			stop: int = len(self) if item.stop is None else int(item.stop)
			step: int = 1 if item.step is None else int(item.step)
			items: list = []

			for i in range(start, stop, step):
				items.append(self.__buffer__[i])

			return String(items)

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(item).__name__}')

	def __getattribute__(self, name: str) -> typing.Any:
		attribute: typing.Any = super().__getattribute__(name)
		is_this: bool = name in vars(type(self))
		super_str_attr: typing.Any = getattr(str, name) if hasattr(str, name) else None
		super_iterable_attr: typing.Any = getattr(MutableSequence, name) if hasattr(MutableSequence, name) else None

		if is_this or not callable(attribute):
			return attribute
		elif super_iterable_attr is not None:
			return String.__Stringify__(attribute) if callable(super_iterable_attr) else attribute
		elif super_str_attr is not None:
			return String.__Stringify__(getattr(str(self), name)) if callable(super_str_attr) else attribute
		else:
			return attribute

	def is_integer2(self) -> bool:
		"""
		Checks if the string is a binary integer
		:return: Whether all characters are 0 or 1
		"""

		return all(x == '0' or x == '1' for x in self)

	def is_integer8(self) -> bool:
		"""
		Checks if the string is an octal integer
		:return: Whether all characters are in the range 0-7
		"""

		chars: tuple[str, ...] = tuple(map(str, range(8)))
		return all(x in chars for x in self)

	def is_integer10(self) -> bool:
		"""
		Checks if the string is a decimal integer
		:return: Whether all characters are in the range 0-9
		"""

		return self.isnumeric()

	def is_integer16(self) -> bool:
		"""
		Checks if the string is a hexadecimal integer
		:return: Whether all characters are in the range 0-9 or A-F
		"""

		chars: tuple[str, ...] = tuple('abcdefABCDEF')
		return all(x.isnumeric() or x in chars for x in self)

	def is_float(self) -> bool:
		"""
		:return: Whether the string is a valid float representation
		"""

		return re.fullmatch(r'\d+(\.\d*(([eE])\d*)?)?', self) is not None

	def is_extended_float(self) -> bool:
		"""
		Allows for a single decimal in the exponent as well: "1.2e3.4"

		Use "String.to_extended_float" to convert the value to a float
		:return: Whether the string is a valid float representation
		"""

		return re.fullmatch(r'\d+(\.\d*(([e|E])\d*(\.\d*)?)?)?', self) is not None

	def is_complex(self) -> bool:
		"""
		:return: Whether the string is a valid complex number representation
		"""

		return re.fullmatch(r'\(?\d*(\.\d*)?(e|E\d*)?(\+\d*(\.\d*)?(e|E\d*)?j)?\)?', self) is not None

	def to_extended_float(self) -> float:
		"""
		Converts the string to a float using the extended float format described in "String.is_extended_float"
		:return: The converted value
		:raises ValueError: If the string is not an extended float
		"""

		Misc.raise_ifn(self.is_extended_float(), ValueError(f'could not convert string to extended float: \'{self}\''))
		sections: list[String] = self.multisplit('eE')
		left: float = float(sections[0])
		right: float = float(sections[1]) if len(sections) > 0 else 1
		return left * 10 ** right

	def copy(self) -> String:
		"""
		:return: A copy of this string
		"""

		return String(self)

	def append(self, element: str | String) -> String:
		"""
		Adds the specified substring to the end of this string
		:param element: The substring to add
		:return: This string
		"""

		if isinstance(element, str):
			self.__buffer__.extend(str(element))
		elif isinstance(element, String):
			self.__buffer__.extend(element.__buffer__)
		else:
			raise TypeError('String elements must be a string or String instance')

		return self

	def extend(self, iterable: typing.Iterable[bytes, bytearray, ByteString, int]) -> String:
		"""
		Adds all strings or bytes from the specified iterable to the end of this string
		:param iterable: The collection of substrings or bytes to add
		:return: This string
		"""

		for item in iterable:
			self.append(item)

		return self

	def insert(self, index: int, element: bytes | bytearray | ByteString | int) -> String:
		if isinstance(element, (str, String)):
			index = int(index)

			for i, char in enumerate(element):
				self.__buffer__.insert(index + i, char)
		else:
			raise TypeError('String elements must be a string or String instance')

		return self

	def multisplit(self, sep: typing.Optional[typing.Iterable[str]] = ..., maxsplit: int = -1) -> list[String]:
		"""
		Splits the string around multiple delimiters
		:param sep: The delimiters to split around
		:param maxsplit: The maximum number of splits to perform (negative or zero values are infinite)
		:return: A list of the split string
		"""

		return [String(s) for s in re.split('|'.join(re.escape(delimiter) for delimiter in sep), self, 0 if maxsplit <= 0 else maxsplit)]


class ByteString(MutableSequence[int], bytearray):
	"""
	An extension adding additional bytes functionality
	"""

	class __Byteify__:
		def __init__(self, callback: typing.Callable):
			self.__callback__: typing.Callable = callback

		def __call__(self, *args, **kwargs) -> typing.Any:
			result: typing.Any = self.__callback__(*args, **kwargs)
			return ByteString(result) if isinstance(result, Sequence) and all(isinstance(x, int) for x in result) else result

	def __init__(self, string: typing.Optional[typing.Any] = None, encoding: str = 'utf-8', errors: typing.Literal['strict', 'ignore', 'replace', 'xmlcharrefreplace', 'backslashreplace', 'namereplace', 'surrogateescape'] = 'strict'):
		"""
		An extension adding additional string functionality\n
		- Constructor -
		:param string: The input value to convert to a string
		"""

		super().__init__([] if string is ... or string is None else list(bytes(string, encoding, errors)) if isinstance(string, str) else list(bytes(string)))

	def __contains__(self, substr: bytes | bytearray | ByteString) -> bool:
		return isinstance(substr, (bytes, bytearray, ByteString)) and self.index(substr) >= 0

	def __eq__(self, other: bytes | bytearray | ByteString) -> bool:
		return isinstance(other, (bytes, bytearray, ByteString)) and bytes(other) == bytes(self)

	def __float__(self) -> float:
		return float(bytes(self))

	def __int__(self) -> int:
		return int(bytes(self))

	def __bytes__(self) -> bytes:
		return bytes(self.__buffer__)

	def __str__(self) -> str:
		return str(bytes(self.__buffer__))

	def __repr__(self) -> str:
		return repr(bytes(self.__buffer__))

	def __iadd__(self, other: bytes | bytearray | ByteString) -> ByteString:
		if not isinstance(other, (bytes, bytearray, ByteString)):
			return NotImplemented

		super().__iadd__(other)
		return self

	def __imul__(self, other: int) -> ByteString:
		super().__imul__(other)
		return self

	def __lshift__(self, other: bytes | bytearray | ByteString) -> ByteString:
		if isinstance(other, ByteString):
			self.append(other.pop())
		elif isinstance(other, (bytes, bytearray)):
			return ByteString(self + other)
		else:
			return NotImplemented

	def __rshift__(self, other: ByteString) -> ByteString:
		if not isinstance(other, ByteString):
			return NotImplemented

		other.append(self.pop())
		return other

	def __setitem__(self, key: int | tuple[int, ...] | slice, value: bytes | bytearray | ByteString | int) -> None:
		"""
		Sets one or more items in this collection
		:param key: The index or indices to modify
		:param value: The value to set
		:raises TypeError: If indices are not integers, slices, or a collection of indices
		"""

		Misc.raise_ifn(isinstance(value, (bytes, bytearray, ByteString)) or (isinstance(value, int) and 0 <= (value := int(value)) <= 255), ValueError('ByteString set item value must be either a bytes, bytearray, ByteString, or integer in the range 0-255'))

		if isinstance(key, int) and isinstance(value, int):
			self.__buffer__[key] = int(value)
		elif isinstance(key, int):
			key = int(key)

			for i, byte in enumerate(value):
				self.__buffer__.insert(key + i, byte)

		elif isinstance(key, tuple):
			for k in key:
				self[k] = value

		elif isinstance(key, slice):
			start: int = 0 if key.start is None else int(key.start)
			stop: int = len(self) if key.stop is None else int(key.stop)
			step: int = 1 if key.step is None else int(key.step)
			index: int = 0

			for i in range(start, stop, step):
				element: int = int(value) if isinstance(value, int) else value[index % len(value)]
				Misc.raise_ifn(0 <= element <= 255, ValueError('ByteString set item value must be either a bytes, bytearray, ByteString, or integer in the range 0-255'))
				self.__buffer__[i] = element
				index += 1

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(key).__name__}')

	def __getitem__(self, item: int | slice | tuple[int, ...]) -> int | Sequence[int] | ByteString:
		"""
		Gets one or more items in this collection
		:param item: The index or indices to get
		:return: If a single element, only that byte; if multiple non-continuous elements, an iterable of integers; otherwise a substring
		:raises TypeError: If indices are not integers, slices, or a collection of indices
		"""

		if isinstance(item, int):
			return self.__buffer__[item]

		elif isinstance(item, tuple):
			items: list = []

			for key in item:
				result = self[key]

				if isinstance(key, (tuple, slice)):
					items.extend(result)
				else:
					items.append(result)

			return Sequence(items)

		elif isinstance(item, slice):
			start: int = 0 if item.start is None else int(item.start)
			stop: int = len(self) if item.stop is None else int(item.stop)
			step: int = 1 if item.step is None else int(item.step)
			items: list = []

			for i in range(start, stop, step):
				items.append(self.__buffer__[i])

			return ByteString(items)

		else:
			raise TypeError(f'TypeError: list indices must be integers or slices, not {type(item).__name__}')

	def __getattribute__(self, name: str) -> typing.Any:
		attribute: typing.Any = super().__getattribute__(name)
		is_this: bool = name in vars(type(self))
		super_bytes_attr: typing.Any = getattr(bytearray, name) if hasattr(bytearray, name) else None
		super_iterable_attr: typing.Any = getattr(MutableSequence, name) if hasattr(MutableSequence, name) else None

		if is_this or not callable(attribute):
			return attribute
		elif super_iterable_attr is not None:
			return ByteString.__Byteify__(attribute) if callable(super_iterable_attr) else attribute
		elif super_bytes_attr is not None:
			return ByteString.__Byteify__(getattr(bytes(self), name)) if callable(super_bytes_attr) else attribute
		else:
			return attribute

	def is_integer2(self) -> bool:
		"""
		Checks if the string is a binary integer
		:return: Whether all characters are 0 or 1
		"""

		zero: int = ord('0')
		one: int = ord('1')
		return all(x == zero or x == one for x in self)

	def is_integer8(self) -> bool:
		"""
		Checks if the string is an octal integer
		:return: Whether all characters are in the range 0-7
		"""

		chars: tuple[int, ...] = tuple(ord('0') + x for x in range(8))
		return all(x in chars for x in self)

	def is_integer10(self) -> bool:
		"""
		Checks if the string is a decimal integer
		:return: Whether all characters are in the range 0-9
		"""

		chars: tuple[int, ...] = tuple(ord('0') + x for x in range(10))
		return all(x in chars for x in self)

	def is_integer16(self) -> bool:
		"""
		Checks if the string is a hexadecimal integer
		:return: Whether all characters are in the range 0-9 or A-F
		"""

		chars: tuple[int, ...] = (*[ord('0') + x for x in range(10)], *[ord(x) for x in 'abcdefABCDEF'])
		return all(x in chars for x in self)

	def is_float(self) -> bool:
		"""
		:return: Whether the string is a valid float representation
		"""

		return re.fullmatch(rb'\d+(\.\d*(([e|E])\d*)?)?', bytes(self)) is not None

	def is_extended_float(self) -> bool:
		"""
		Allows for a single decimal in the exponent as well: "1.2e3.4"

		Use "String.to_extended_float" to convert the value to a float
		:return: Whether the string is a valid float representation
		"""

		return re.fullmatch(rb'\d+(\.\d*(([e|E])\d*(\.\d*)?)?)?', bytes(self)) is not None

	def to_extended_float(self) -> float:
		"""
		Converts the string to a float using the extended float format described in "String.is_extended_float"
		:return: The converted value
		:raises ValueError: If the string is not an extended float
		"""

		Misc.raise_ifn(self.is_extended_float(), ValueError(f'could not convert string to extended float: \'{self}\''))
		sections: list[ByteString] = self.multisplit(b'eE')
		left: float = float(sections[0])
		right: float = float(sections[1]) if len(sections) > 0 else 1
		return left * 10 ** right

	def index(self, item: int | bytes | bytearray | ByteString, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Returns the index of the specified byte or substring
		:param item: The substring or byte to check for
		:param start: Index to begin check or beginning of string if not supplied
		:param stop: Index to end check or end of string if not supplied
		:return: The substring or byte index or -1 if not found
		"""

		if isinstance(item, int):
			return super().index(item, start, stop) if 0x00 <= (item := int(item)) <= 0xFF else -1

		target: bytes = bytes(item)
		start: int = 0 if start is ... or start is None else int(start)
		stop: int = (len(self) - len(target) + 1) if stop is ... or stop is None else int(stop)

		for i in range(start, stop):
			if bytes(self[i:i + len(item)]) == target:
				return i

		return -1

	def copy(self) -> ByteString:
		"""
		:return: A copy of this string
		"""

		return ByteString(self)

	def append(self, element: bytes | bytearray | ByteString | int) -> ByteString:
		"""
		Adds the specified byte or substring to the end of this string
		:param element: The substring or byte to add
		:return: This string
		"""

		if isinstance(element, (bytes, bytearray)):
			self.__buffer__.extend(bytes(element))
		elif isinstance(element, int) and 0 <= (element := int(element)) <= 255:
			self.__buffer__.append(element)
		elif isinstance(element, ByteString):
			self.__buffer__.extend(element.__buffer__)
		else:
			raise TypeError('Bytestring elements must be a bytes object, bytearray object, ByteString instance, or integer in the range 0-255')

		return self

	def extend(self, iterable: typing.Iterable[bytes, bytearray, ByteString, int]) -> ByteString:
		"""
		Adds all strings or bytes from the specified iterable to the end of this string
		:param iterable: The collection of substrings or bytes to add
		:return: This string
		"""

		for item in iterable:
			self.append(item)

		return self

	def insert(self, index: int, element: bytes | bytearray | ByteString | int) -> ByteString:
		if isinstance(element, int) and 0 <= (element := int(element)) < 255:
			self.__buffer__.insert(int(index), element)
		elif isinstance(element, (bytes, bytearray, ByteString)):
			index = int(index)

			for i, byte in enumerate(element):
				self.__buffer__.insert(index + i, byte)
		else:
			raise TypeError('Bytestring elements must be a bytes object, bytearray object, ByteString instance, or integer in the range 0-255')

		return self

	def multisplit(self, sep: typing.Optional[typing.Iterable[int | bytes | bytearray | ByteString]] = ..., maxsplit: int = -1) -> list[ByteString]:
		"""
		Splits the string around multiple delimiters
		:param sep: The delimiters to split around
		:param maxsplit: The maximum number of splits to perform (negative or zero values are infinite)
		:return: A list of the split string
		"""

		segments: list[ByteString] = []
		segment: ByteString = ByteString()
		matches: int = 0

		for i, byte in enumerate(self):
			matched: bool = False

			if maxsplit <= 0 or matches < maxsplit:
				for delimiter in sep:
					if not isinstance(delimiter, (int, bytes, bytearray, ByteString)) or (isinstance(delimiter, int) and not (0 <= (delimiter := int(delimiter)) <= 255)):
						raise TypeError('ByteString delimiter must be an integer in the range 0-255')
					elif (isinstance(delimiter, int) and delimiter == self[i]) or self[i:i + len(delimiter)] == delimiter:
						matches += 1
						segments.append(segment)
						matched = True
						segment = ByteString()
						break

			if not matched:
				segment.append(byte)

		segments.append(segment)
		return [ByteString(seg) for seg in segments]

	@property
	def bytes(self) -> typing.Iterator[bytes]:
		"""
		:return: Each byte as a bytes object instead of an integer
		"""

		for byte in self:
			yield byte.to_bytes(1, sys.byteorder)


class FixedArray[T](SortableSequence[T]):
	"""
	Class representing an array of a fixed size
	"""

	def __init__(self, iterable_or_size: typing.Iterable[T] | int):
		"""
		Class representing an array of a fixed size\n
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


class SpinQueue[T](SortableSequence[T]):
	"""
	Class representing a queue-like array of a maximum size
	"""

	def __init__(self, iterable_or_size: typing.Iterable[T] | int):
		"""
		Class representing an array of a fixed size\n
		- Constructor -
		:param iterable_or_size: The iterable or number of elements this list contains
		:raises TypeError: If 'iterable_or_size' is not a positive integer or iterable
		"""

		if isinstance(iterable_or_size, int) and (iterable_or_size := int(iterable_or_size)) > 0:
			super().__init__([None] * iterable_or_size)
			self.__max_size__: int = iterable_or_size
			self.__count__: int = 0
			self.__offset__: int = 0
		elif isinstance(iterable_or_size, typing.Iterable):
			super().__init__(iterable_or_size)
			self.__max_size__: int = len(self.__buffer__)
			self.__count__: int = self.__max_size__
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

	def pop(self, index: int = -1) -> T:
		"""
		Pops an item from the queue
		:param index: The index or last element if not specified
		:return: The popped item
		:raises IterableEmptyException: If the collection is empty
		"""

		if self.__count__ == 0:
			raise Exceptions.IterableEmptyException('Pop from empty queue')

		index = index if (index := int(index)) >= 0 else (self.__max_size__ + index)
		Misc.raise_if(index >= self.__max_size__, IndexError(f'Specified index \'{index}\' is out of bounds for SpinQueue of count \'{self.__count__}\''))
		elem: T = self.__buffer__[(self.__offset__ + index) % self.__max_size__]
		self.__count__ -= 1

		for i in range(self.__offset__ + index, self.__offset__ + self.__count__):
			self.__buffer__[i % self.__max_size__] = self.__buffer__[(i + 1) % self.__max_size__]

		self.__buffer__[(self.__offset__ + self.__count__) % self.__max_size__] = None
		return elem

	def remove(self, element: T, count: int = -1) -> int:
		"""
		Removes the specified element from this list
		:param element: The element to remove
		:param count: The number of occurrences to remove or all if less than 0
		:return: The number of occurrences removed
		"""

		matches: int = 0

		for i in range(len(self)):
			index: int = i - matches

			if index < len(self) and self.__buffer__[index] == element:
				self.pop(index)
				matches += 1

			if 0 <= count <= matches:
				break

		return matches

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


class LockedSequence[T](SortableSequence[T]):
	"""
	Thread safe sequence using locks
	"""

	class LockedIterator[Q](collections.abc.Iterator[Q]):
		def __init__(self, iterable: LockedSequence[Q]):
			assert isinstance(iterable, LockedSequence)
			self.__iterable__: LockedSequence[Q] = iterable
			self.__int_index__: int = 0

		def __iter__(self) -> collections.abc.Iterator[Q]:
			return self

		def __next__(self) -> Q:
			with self.__iterable__.read_lock():
				if self.__int_index__ >= len(self.__iterable__):
					raise StopIteration
				else:
					value: Q = self.__iterable__[self.__int_index__]
					self.__int_index__ += 1
					return value

	class ReversedLockedIterator[Q](collections.abc.Iterator[Q]):
		def __init__(self, iterable: LockedSequence[Q]):
			assert isinstance(iterable, LockedSequence)
			self.__iterable__: LockedSequence[Q] = iterable
			self.__int_index__: int = 0

		def __iter__(self) -> collections.abc.Iterator[Q]:
			return self

		def __next__(self) -> Q:
			with self.__iterable__.read_lock():
				length: int = len(self.__iterable__)

				if self.__int_index__ >= length:
					raise StopIteration
				else:
					value: Q = self.__iterable__[length - 1 - self.__int_index__]
					self.__int_index__ += 1
					return value

	def __init__(self, sequence: collections.abc.Iterable[T] = ..., *, lock: threading.Lock | Synchronization.SynchronizationPrimitive = Synchronization.SpinLock()):
		"""
		Thread safe sequence using locks\n
		- Constructor -
		:param sequence: The initial sequence
		:param lock: The lock to use for operations
		"""

		Misc.raise_ifn(isinstance(lock, (threading.Lock, Synchronization.SynchronizationPrimitive)), Exceptions.InvalidArgumentException(LockedSequence.__init__, 'lock', type(lock), (threading.Lock, Synchronization.SynchronizationPrimitive)))
		super().__init__(sequence)
		self.__lock__: threading.Lock | Synchronization.SpinLock | Synchronization.ReaderWriterLock = lock

	def __contains__(self, item: T) -> bool:
		with self.read_lock():
			return super().__contains__(item)

	def __eq__(self, other: Sequence[T]) -> bool:
		with self.read_lock():
			return super().__eq__(other)

	def __ne__(self, other: Sequence[T]) -> bool:
		with self.read_lock():
			return super().__ne__(other)

	def __gt__(self, other: Sequence[T]) -> bool:
		with self.read_lock():
			return super().__gt__(other)

	def __lt__(self, other: Sequence[T]) -> bool:
		with self.read_lock():
			return super().__lt__(other)

	def __ge__(self, other: Sequence[T]) -> bool:
		with self.read_lock():
			return super().__ge__(other)

	def __le__(self, other: Sequence[T]) -> bool:
		with self.read_lock():
			return super().__le__(other)

	def __bool__(self) -> bool:
		with self.read_lock():
			return super().__bool__()

	def __len__(self) -> int:
		with self.read_lock():
			return super().__len__()

	def __repr__(self) -> str:
		with self.read_lock():
			return super().__repr__()

	def __str__(self) -> str:
		with self.read_lock():
			return super().__str__()

	def __iter__(self) -> LockedIterator[T]:
		return LockedSequence.LockedIterator(self)

	def __delitem__(self, key: int | tuple[int, ...] | slice) -> None:
		with self.write_lock():
			super().__delitem__(key)

	def __setitem__(self, key: int | tuple[int, ...] | slice, value: T) -> None:
		with self.write_lock():
			super().__setitem__(key, value)

	def __getitem__(self, item: int | slice | tuple[int, ...]) -> T | Sequence[T]:
		with self.read_lock():
			return super().__getitem__(item)

	def __reversed__(self) -> ReversedLockedIterator[T]:
		return LockedSequence.ReversedLockedIterator(self)

	def clear(self) -> None:
		with self.write_lock():
			super().clear()

	def reverse(self) -> None:
		with self.write_lock():
			super().reverse()

	def count(self, item: T) -> int:
		with self.read_lock():
			return super().count(item)

	def index(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		with self.read_lock():
			return super().index(item, start, stop)

	def find(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		with self.read_lock():
			return super().find(item, start, stop)

	def copy[I: Sequence](self: I) -> I:
		with self.read_lock():
			return super().copy()

	def stream(self) -> Stream.LinqStream[T]:
		"""
		:return: A new LinqStream for queries on this iterable
		"""

		return Stream.LinqStream(LockedSequence.LockedIterator(self))

	def acquire_read_lock(self) -> bool:
		"""
		Acquires the reader lock if an RW lock, otherwise acquires the lock\n
		Blocks until lock is acquired
		:return: Whether the lock was acquired
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__.acquire()
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.acquire_reader()

	def acquire_write_lock(self) -> bool:
		"""
		Acquires the writer lock if an RW lock, otherwise acquires the lock\n
		Blocks until lock is acquired
		:return: Whether the lock was acquired
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__.acquire()
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.acquire_writer()

	def read_lock(self) -> threading.Lock | Synchronization.SynchronizationPrimitive | Synchronization.ReaderWriterLock.Lock:
		"""
		Returns the reader lock if an RW lock, otherwise the lock
		:return: The lock object for context management
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.reader()

	def write_lock(self) -> threading.Lock | Synchronization.SynchronizationPrimitive | Synchronization.ReaderWriterLock.Lock:
		"""
		Returns the reader lock if an RW lock, otherwise the lock
		:return: The lock object for context management
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.writer()

	def get_or_wait(self, index: int, timeout: float = None, default: T = ...) -> T:
		"""
		Gets the item at the specified index\n
		If the index does not exist, waits at most 'timeout' seconds until it does
		:param index: The index to retrieve
		:param timeout: The maximum amout of seconds to wait or None for infinite
		:param default: The default value to return if timed out
		:return: The item or 'default'
		:raises TimeoutError: If 'default' is not supplied and the operation times out
		"""

		time_point: float = time.perf_counter()

		while True:
			with self.read_lock():
				length: int = super().__len__()
				index = length + index if index < 0 else index

				if index < length:
					return super().__getitem__(index)
				elif (timed_out := (timeout is not None and timeout is not ... and time.perf_counter() - time_point >= timeout)) and default is ...:
					raise TimeoutError('LockedIterable wait timed out')
				elif timed_out:
					return default

				time.sleep(1e-6)


class Mapping[K: typing.Hashable, V](Iterable[dict[K, V], tuple[K, V]], collections.abc.Mapping):
	"""
	Base iterable class for CM-VI mappings
	"""

	def __init__(self, collection: collections.abc.Mapping[K, V] = ...):
		"""
		Base iterable class for CM-VI mappings\n
		- Constructor -
		:param collection: The mapping to build from
		"""

		super().__init__({} if collection is None or collection is ... else dict(collection))

	def __contains__(self, item: K) -> bool:
		"""
		:param item: The key to search for
		:return: If the key exists within this collection
		"""

		return item in self.__buffer__

	def __repr__(self) -> str:
		"""
		:return: The string representation of this mapping
		"""

		return repr(self.__buffer__)

	def __str__(self) -> str:
		"""
		:return: The string representation of this mapping
		"""

		return str(self.__buffer__)

	def __iter__(self) -> collections.abc.Iterator[tuple[K, V]]:
		"""
		:return: The iterator for this iterable
		"""

		return iter(self.__buffer__.items())

	def __getitem__(self, key: K) -> V:
		"""
		Gets a key's associated value from this mapping
		:param key: The key to get
		:return: The associated element
		:raises KeyError: If the specified key does not exist
		"""

		return self.__buffer__[key]

	def __or__(self, other: collections.abc.Mapping[K, V]) -> Mapping[K, V]:
		"""
		Merges this mapping and another mapping
		:param other: The other mapping
		:return: The merged mapping
		"""

		return type(self)(self.__buffer__ | dict(other))

	def copy[I: Mapping](self: I) -> I:
		"""
		:return: A copy of this mapping
		"""

		return type(self)(self.__buffer__.copy())

	def get_or_default(self, key: K, default: typing.Optional[V] = None) -> typing.Optional[V]:
		"""
		Gets the item at the specified key or 'default' if key does not exist
		:param key: The key to retrieve
		:param default: The default item to return if key does not exist
		:return: The item at 'key' or 'default' if does not exist
		"""

		return self.__buffer__.get(key, default)

	def stream(self) -> Stream.LinqStream[tuple[K, V]]:
		"""
		:return: A new LinqStream for queries on this iterable
		"""

		return Stream.LinqStream(self)

	def keys(self) -> collections.abc.KeysView[K]:
		"""
		:return: A view of all keys in this mapping
		"""

		return self.__buffer__.keys()

	def values(self) -> collections.abc.ValuesView[V]:
		"""
		:return: A view of all values in this mapping
		"""

		return self.__buffer__.values()


class MutableMapping[K, V](Mapping[K, V], collections.abc.MutableMapping):
	"""
	Mapping allowing modifications
	"""

	def __delitem__(self, key: K) -> None:
		"""
		Deletes a key from this mapping
		:param key: The key or keys to delete
		:raises KeyError: If the specified key does not exist
		"""

		del self.__buffer__[key]

	def __setitem__(self, key: K | tuple[K, ...], value: V) -> None:
		"""
		Sets a key in this mapping
		:param key: The key or keys to modify
		:param value: The value to set
		"""

		self.__buffer__[key] = value

	def __ior__(self, other: typing.Mapping[K, V]) -> MutableMapping[K, V]:
		"""
		Merges this mapping and another mapping
		:param other: The other mapping
		:return: This mapping
		"""

		self.update(other)
		return self

	def clear(self) -> None:
		"""
		Clears the mapping
		"""

		self.__buffer__.clear()

	def get_or_insert(self, key: K, default: typing.Optional[V] = None) -> V:
		"""
		Gets the item at the specified key or inserts and returns 'default' if key does not exist
		:param key: The key to retrieve
		:param default: The default item to insert and return if key does not exist
		:return: The item at 'key'
		"""

		return self.__buffer__.setdefault(key, default)

	def pop(self, key: K, default: typing.Optional[V] = ...) -> V:
		"""
		Removes and returns the element at the specified key
		:param key: The key to remove and return
		:param default: The default value to return or raise KeyError if not supplied
		:return: The removed element
		"""

		return self.__buffer__.pop(key) if default is ... else self.__buffer__.pop(key, default)

	def pop_last(self) -> tuple[K, V]:
		"""
		Removes and returns the last key-value pair added to this mapping
		:return: The removed pair
		"""

		return self.__buffer__.popitem()

	def update(self, mapping: collections.abc.Mapping[K, V], /, **kwargs) -> Mapping[K, V]:
		"""
		Adds the key-value pairs from the specified mapping to this one in-place\n
		Duplicate keys are overwritten
		:param mapping: The mapping to add
		:return: This mapping
		"""

		self.__buffer__.update(mapping, **kwargs)
		return self


class LockedMapping[K, V](MutableMapping):
	"""
	Thread safe mapping using locks
	"""

	def __init__(self, mapping: collections.abc.Mapping[K, V] = ..., *, lock: threading.Lock | Synchronization.SynchronizationPrimitive = Synchronization.SpinLock()):
		"""
		Thread safe mapping using locks\n
		- Constructor -
		:param mapping: The initial mapping
		:param lock: The lock to use for operations
		"""

		Misc.raise_ifn(isinstance(lock, (threading.Lock, Synchronization.SynchronizationPrimitive)), Exceptions.InvalidArgumentException(LockedSequence.__init__, 'lock', type(lock), (threading.Lock, Synchronization.SynchronizationPrimitive)))
		super().__init__(mapping)
		self.__lock__: threading.Lock | Synchronization.SpinLock | Synchronization.ReaderWriterLock = lock

	def __contains__(self, key: K) -> bool:
		with self.read_lock():
			return super().__contains__(key)

	def __eq__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__eq__(other)

	def __ne__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__ne__(other)

	def __gt__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__gt__(other)

	def __lt__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__lt__(other)

	def __ge__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__ge__(other)

	def __le__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__le__(other)

	def __bool__(self) -> bool:
		with self.read_lock():
			return super().__bool__()

	def __len__(self) -> int:
		with self.read_lock():
			return super().__len__()

	def __repr__(self) -> str:
		with self.read_lock():
			return super().__repr__()

	def __str__(self) -> str:
		with self.read_lock():
			return super().__str__()

	def __iter__(self) -> collections.abc.Iterator[tuple[K, V]]:
		keys: tuple[K, ...] = tuple(self.keys())

		for key in keys:
			yield key, self[key]

	def __delitem__(self, key: K) -> None:
		with self.write_lock():
			super().__delitem__(key)

	def __setitem__(self, key: K, value: V) -> None:
		with self.write_lock():
			super().__setitem__(key, value)

	def __getitem__(self, key: K) -> V:
		with self.read_lock():
			return super().__getitem__(key)

	def __or__(self, other: collections.abc.Mapping[K, V]) -> Mapping[K, V]:
		with self.read_lock():
			return type(self)(self.__buffer__ | dict(other))

	def clear(self) -> None:
		with self.write_lock():
			self.__buffer__.clear()

	def copy[I: LockedMapping](self: I) -> I:
		with self.read_lock():
			return type(self)(self.__buffer__.copy())

	def get_or_default(self, key: K, default: typing.Optional[V] = None) -> typing.Optional[V]:
		with self.read_lock():
			return self.__buffer__.get(key, default)

	def get_or_insert(self, key: K, default: typing.Optional[V] = None) -> V:
		with self.write_lock():
			return self.__buffer__.setdefault(key, default)

	def pop(self, key: K, default: typing.Optional[V] = ...) -> V:
		with self.write_lock():
			return self.__buffer__.pop(key) if default is ... else self.__buffer__.pop(key, default)

	def pop_last(self) -> tuple[K, V]:
		with self.write_lock():
			return self.__buffer__.popitem()

	def update(self, mapping: collections.abc.Mapping[K, V], /, **kwargs) -> Mapping[K, V]:
		with self.write_lock():
			self.__buffer__.update(mapping, **kwargs)
			return self

	def keys(self) -> collections.abc.KeysView[K]:
		with self.read_lock():
			return self.__buffer__.keys()

	def values(self) -> collections.abc.ValuesView[V]:
		with self.read_lock():
			return self.__buffer__.values()

	def acquire_read_lock(self) -> bool:
		"""
		Acquires the reader lock if an RW lock, otherwise acquires the lock\n
		Blocks until lock is acquired
		:return: Whether the lock was acquired
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__.acquire()
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.acquire_reader()

	def acquire_write_lock(self) -> bool:
		"""
		Acquires the writer lock if an RW lock, otherwise acquires the lock\n
		Blocks until lock is acquired
		:return: Whether the lock was acquired
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__.acquire()
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.acquire_writer()

	def read_lock(self) -> threading.Lock | Synchronization.SynchronizationPrimitive | Synchronization.ReaderWriterLock.Lock:
		"""
		Returns the reader lock if an RW lock, otherwise the lock
		:return: The lock object for context management
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.reader()

	def write_lock(self) -> threading.Lock | Synchronization.SynchronizationPrimitive | Synchronization.ReaderWriterLock.Lock:
		"""
		Returns the reader lock if an RW lock, otherwise the lock
		:return: The lock object for context management
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.writer()


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
