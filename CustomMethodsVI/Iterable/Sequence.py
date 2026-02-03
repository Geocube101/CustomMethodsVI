from __future__ import annotations

import collections
import threading
import time
import typing
import warnings

from . import Iterable
from .. import Exceptions
from .. import Misc
from .. import Stream
from .. import Synchronization


class Sequence[T](Iterable.Iterable[list[T], T], collections.abc.Sequence[T]):
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
					value: Q = self.__iterable__.__buffer__[self.__int_index__]
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


class SequenceView[T](Iterable.IterableView[Sequence, T]):
	def __init__(self, iterable: Sequence[T]):
		"""
		Class allowing a view into a collection\n
		- Constructor -
		:param iterable: The iterable to view
		"""

		Misc.raise_ifn(isinstance(iterable, Sequence), Exceptions.InvalidArgumentException(SequenceView.__init__, 'iterable', type(iterable), (Sequence,)))
		super().__init__(iterable)

	def __getitem__(self, item: int | slice | tuple[int, ...]) -> T | Sequence[T]:
		"""
		Gets one or more items in this view's sequence
		:param item: The index or indices to get
		:return: If a single element, only that item, otherwise a Sequence of items
		:raises TypeError: If indices are not integers, slices, or a sequence of indices
		"""

		return self.__iterable__[item]

	def count(self, item: T) -> int:
		"""
		:param item: The item to search for
		:return: The number of times an item occurs in this view's sequence
		"""

		return self.__iterable__.count(item)

	def index(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Gets the index of an item in this view's sequence
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The index of the element in this view's sequence
		:raises ValueError: If the specified value is not in this view's sequence
		"""

		return self.__iterable__.index(item, start, stop)

	def find(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Gets the index of an item in this view's sequence
		:param item: The item to search for
		:param start: The index to begin the search
		:param stop: The index to end the search
		:return: The index of the element in this view's sequence or -1 if no such element
		"""

		return self.__iterable__.find(item, start, stop)

	def get_or_default(self, index: int, default: typing.Optional[T] = None) -> typing.Optional[T]:
		"""
		Gets the item at the specified index or 'default' if index out of bounds
		:param index: The index to retrieve
		:param default: The default item to return if index out of bounds
		:return: The item at 'index' or 'default' if out of bounds
		"""

		return self.__iterable__.get_or_default(index, default)
