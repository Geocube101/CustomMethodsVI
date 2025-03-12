from __future__ import annotations

import time
import typing
import collections.abc
import sys
import threading
import warnings

from CustomMethodsVI.Decorators import Overload
from CustomMethodsVI.Stream import LinqStream


class Iterable[T](collections.abc.Sequence, collections.abc.Sized, typing.Iterable):
	"""
	[Iterable(collections.abc.Sequence, collections.abc.Sized)] Base iterable class for CMVI iterables
	"""

	def __init__(self, collection: typing.Sized[T] | typing.Iterable[T]):
		"""
		[Iterable(collections.abc.Sequence, collections.abc.Sized)] Base iterable class for CMVI iterables
		- Constructor -
		:param collection: The iterable to build from
		"""

		self.__buffer__: list = list(collection)

	def __contains__(self, item: T) -> bool:
		"""
		Checks if an item exists within this collection
		:param item: (ANY) The item to search for
		:return: (bool) Containedness
		"""

		return item in self.__buffer__

	def __eq__(self, other: Iterable[T]) -> bool:
		"""
		Checks if this instance matches another Iterable instance
		:param other: (Iterable) The callback instance to compare
		:return: (bool) True if both are an Iterable and their contents are equal
		"""

		return self.__buffer__ == other.__buffer__ if isinstance(other, type(self)) else False

	def __ne__(self, other: Iterable[T]) -> bool:
		"""
		Checks if this instance doesn't match another Iterable instance
		:param other: (Iterable) The callback instance to compare
		:return: (bool) False if both are an Iterable and their contents are equal
		"""

		return not self == other

	def __gt__(self, other: Iterable[T]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: (Iterable) The callback instance
		:return: (bool) If this length is greater
		"""

		return len(self) > len(other) if type(other) is type(self) else NotImplemented

	def __lt__(self, other: Iterable[T]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: (Iterable) The callback instance
		:return: (bool) If this length is lesser
		"""

		return len(self) < len(other) if type(other) is type(self) else NotImplemented

	def __ge__(self, other: Iterable[T]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: (Iterable) The callback instance
		:return: (bool) If this length is greater or equal
		"""

		return len(self) >= len(other) if type(other) is type(self) else NotImplemented

	def __le__(self, other: Iterable[T]) -> bool:
		"""
		Compares two Iterable instances based on their length
		:param other: (Iterable) The callback instance
		:return: (bool) If this length is lesser or equal
		"""

		return len(self) <= len(other) if type(other) is type(self) else NotImplemented

	def __bool__(self) -> bool:
		"""
		Converts this instance to a bool based on it's size
		:return: (bool) True if this list is not empty
		"""

		return bool(len(self))

	def __len__(self) -> int:
		"""
		Returns the length of this iterable
		:return: (int) Length
		"""
		return len(self.__buffer__)

	def __repr__(self) -> str:
		"""
		Gets the string representation of this list
		:return: (str) Representation string
		"""

		return repr(self.__buffer__)

	def __str__(self) -> str:
		"""
		Gets the string representation of this list
		:return: (str) Representation string
		"""

		return str(self.__buffer__)

	def __iter__(self) -> typing.Iterator[T]:
		"""
		Returns an iterator for this list
		:return: (Generator) The iterator
		"""

		return iter(self.__buffer__)

	def __delitem__(self, key: int | tuple[int, ...] | slice) -> None:
		"""
		Deletes one or more items in this collection
		:param key: (int | tuple[int] | slice) The index or indices to modify
		:return: (None)
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
			raise TypeError('TypeError: list indices must be integers or slices, not float')

		self.__buffer__.remove(None)

	def __setitem__(self, key: int | tuple[int, ...] | slice, value: T) -> None:
		"""
		Sets one or more items in this collection
		:param key: (int | tuple[int] | slice) The index or indices to modify
		:param value: (ANY) The value to set
		:return: (None)
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
			raise TypeError('TypeError: list indices must be integers or slices, not float')

	def __getitem__(self, item: int | slice | tuple[int, ...]) -> T | Iterable[T]:
		"""
		Gets one or more items in this collection
		:param item: (int | tuple[int] | slice) The index or indices to get
		:return: (ANY) If a single element, only that item, otherwise a tuple of items
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

			return type(self)(items)

		elif type(item) is slice:
			start: int = 0 if item.start is None else int(item.start)
			stop: int = len(self) if item.stop is None else int(item.stop)
			step: int = 1 if item.step is None else int(item.step)
			items: list = []

			for i in range(start, stop, step):
				items.append(self.__buffer__[i])

			return type(self)(items)

		else:
			raise TypeError('TypeError: list indices must be integers or slices, not float')

	def __reversed__(self) -> reversed:
		"""
		Reverses this list
		:return: (reversed) A reverse iterator
		"""

		return reversed(self.__buffer__)

	def clear(self) -> None:
		"""
		Clears the collection
		:return: (None)
		"""

		self.__buffer__.clear()

	def reverse(self) -> None:
		"""
		Reverses the array in-place
		:return: (None)
		"""

		self.__buffer__.reverse()

	def count(self, item: T) -> int:
		"""
		Gets the number of times an item occurs in this list
		:param item: (ANY) The item to search for
		:return: (int) The number of occurrences
		"""

		return self.__buffer__.count(item)

	def index(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Gets the index of an item in the list
		:param item: (ANY) The item to search for
		:param start: (int?) The index to begin the search
		:param stop: (int?) The index to end the search
		:return: (int) The index of the element in this list
		:raises ValueError: If the specified value is not in this list
		"""

		return self.__buffer__.index(item, start, stop)

	def find(self, item: T, start: typing.Optional[int] = ..., stop: typing.Optional[int] = ...) -> int:
		"""
		Gets the index of an item in the list
		:param item: (ANY) The item to search for
		:param start: (int?) The index to begin the search
		:param stop: (int?) The index to end the search
		:return: (int) The index of the element in this list or -1 if no such element
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
		Returns a copy of this collection
		:return: (Iterable) Copyness
		"""

		return type(self)(self.__buffer__.copy())


class LinqIterable[T](Iterable, LinqStream):
	def __init__(self, collection: typing.Sized | typing.Iterable[T]):
		LinqStream.__init__(self, self)
		Iterable.__init__(self, collection)


class SortableIterable[T](LinqIterable):
	"""
	[SortableIterable(Iterable)] - Class representing an iterable containing sorting functions
	"""

	def __init__(self, collection: typing.Sized | typing.Iterable[T]):
		LinqIterable.__init__(self, collection)

	def sort(self, *, key: typing.Optional[typing.Callable] = ..., reverse: typing.Optional[bool] = False) -> None:
		"""
		Sorts the collection in-place
		:param key: (CALLABLE?) An optional callable specifying how to sort the collection
		:param reverse: (bool>) An optional bool specifying whether to sort in reversed order
		:return: (None)
		"""

		self.__buffer__.sort(key=key, reverse=reverse)


class SortedList[T](SortableIterable):
	"""
	[SortedList(Iterable)] - A list using binary search to maintain a sorted list of elements
	"""

	def __init__(self, *args: T | typing.Iterable[T]):
		"""
		[SortedList(Iterable)] - A list using binary search to search and maintain a sorted list of elements
		- Constructor -
		:param args: (ANY) Either a variadic list of elements to use, or an iterable whose elements to use
		"""

		if len(args) == 0:
			super().__init__([])
		elif len(args) == 1 and isinstance(args[0], type(self)):
			super().__init__(args[0].__buffer__.copy())
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
		:param item: (ANY) The item to search for
		:return: (bool) Containedness
		"""

		return self.bin_search(item) != -1

	def __add__(self, other: typing.Iterable[T]) -> SortedList[T]:
		"""
		Adds the elements of the second iterable to this collection
		:param other: (ITERABLE) The iterable to add
		:return: (SortedList) A new sorted collection containing the appended elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		return self.extended(other) if hasattr(other, '__iter__') else NotImplemented

	def __iadd__(self, other: typing.Iterable[T]) -> SortedList[T]:
		"""
		Adds the elements of the second iterable to this collection in place
		:param other: (ITERABLE) The collection to add
		:return: (SortedList) This instance
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
		:param other: (ITERABLE) The collection to add
		:return: (SortedList) A new sorted collection containing the appended elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		return self.extended(other) if hasattr(other, '__iter__') else NotImplemented

	def __mul__(self, times: int) -> SortedList[T]:
		"""
		Duplicates the elements in this collection
		:param times: (int) The number of times to duplicate
		:return: (SortedList) A new sorted collection containing the duplicated elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		if type(times) is int:
			result: list = []
			__times: list[int] = list(range(times))

			for i in range(len(self)):
				result.extend(self.__buffer__[i] for _ in __times)

			copy: SortedList = type(self)()
			copy.__buffer__ = result
			return copy
		else:
			return NotImplemented

	def __imul__(self, times: int) -> SortedList[T]:
		"""
		Duplicates the elements in this collection in place
		:param times: (int) The number of times to duplicate
		:return: (SortedList) This instance
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		if type(times) is int:
			result: list = []
			__times: list[int] = list(range(times))

			for i in range(len(self)):
				result.extend(self.__buffer__[i] for _ in __times)

			self.__buffer__ = result
			return self
		else:
			return NotImplemented

	def __rmul__(self, times: int) -> SortedList[T]:
		"""
		Duplicates the elements in this collection
		:param times: (int) The number of times to duplicate
		:return: (SortedList) A new sorted collection containing the duplicated elements
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		if type(times) is int:
			result: list = []
			__times: list[int] = list(range(times))

			for i in range(len(self)):
				result.extend(self.__buffer__[i] for _ in __times)

			copy: SortedList = type(self)()
			copy.__buffer__ = result
			return copy
		else:
			return NotImplemented

	def __setitem__(self, key: int | slice | tuple[int | slice, ...], value: T) -> None:
		"""
		SHOULD NOT BE USED - Alias for SortedList::append
		Adds an item into the collection using binary search
		This will throw a warning
		:param key: (---) NOT USED, this value will be ignored
		:param value: (ANY) The item to insert
		:return: (NONE)
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		warnings.warn('\\\\\\\nDirect insertion in binary-sorted collection\nUse \'SortedList::append\' instead \\\\\\', UserWarning, stacklevel=2)
		self.append(value)

	def append(self, item: T) -> None:
		"""
		Appends an item to this collection
		:param item: (ANY) The item to append
		:return: (None)
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
		:param iterable: (ITERABLE) The collection to append
		:return: (None)
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		for e in iterable:
			self.append(e)

	def remove(self, item: T) -> None:
		"""
		Removes the first occurrence item from the collection
		:param item: (ANY) The item to remove
		:return: (None)
		"""

		if item in self:
			self.__buffer__.remove(item)

	def remove_all(self, item: T) -> None:
		"""
		Removes all occurrences item from the collection
		:param item: (ANY) The item to remove
		:return: (None)
		"""

		while item in self:
			self.__buffer__.remove(item)

	def resort(self, *iterables: typing.Iterable[T]) -> None:
		"""
		Resorts the entire collection, appending the supplied values from '*iterables' if provided
		:param iterables: (*ITERABLES) The extra collections to append before resort
		:return: (None)
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
		Resorts the entire collection, appending the supplied values from '*iterables' if provided and removing duplicates
		:param iterables: (*ITERABLES) The extra collections to append before resort
		:return: (None)
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
		:param item: (ANY) The item to search for
		:param lower: (int?) The index's lower bound to search in
		:param upper: (int?) The index's upper bound to search in
		:return: (int) The position if found or -1
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
		:param item: (ANY) The item to search for
		:param start: (int?) The index to begin the search
		:param stop: (int?) The index to end the search
		:return: (int) The position if found or -1
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
		:param item: (ANY) The item to search for
		:param start: (int?) The index to begin the search
		:param stop: (int?) The index to end the search
		:return: (int) The position if found or -1
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
		:param item: (ANY) The item to search for
		:param start: (int?) The index to begin the search
		:param stop: (int?) The index to end the search
		:return: (int) The index of the element in this list
		:raises ValueError: If the specified value is not in this list
		"""

		position: int = self.bin_search(item, start, stop)

		if position == -1:
			raise ValueError(f'{item} is not in list')

		return position

	def count(self, item: T) -> int:
		"""
		Gets the number of times an item occurs in this collection using binary search
		:param item: (ANY) The item to search for
		:return: (int) The number of occurrences
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
		:param item: (ANY) The item to search for
		:return: (tuple[int, int]) The range of indices an item covers
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
		:param iterable: (ITERABLE) The collection to append
		:return: (SortedList) The new, updated list
		:raises TypeError: If the item cannot be compared
		:raises ValueError: If an error occurred during binary search
		"""

		copied = self.copy()
		copied.extend(iterable)
		return copied

	def removed_duplicates(self) -> SortedList[T]:
		"""
		Removes all duplicates from this collection
		:return: (SortedList) A copy  of this collection with all duplicates removed
		"""

		return SortedList(set(self.__buffer__))

	def reversed(self) -> ReverseSortedList[T]:
		"""
		Reverses this collection
		:return: (ReverseSortedList) A reversed collection
		"""

		return ReverseSortedList(self.__buffer__)

	def pop(self, index: typing.Optional[int] = ...) -> T:
		"""
		Deletes and returns a single item from this collection
		:param index: (int?) The index to remove or the last element if not supplied
		:return: (ANY) The element at that position
		"""

		return self.__buffer__.pop(-1 if index is ... or index is None else int(index))


class ReverseSortedList[T](SortableIterable):
	"""
	[ReverseSortedList(SortedList)] - A list using binary search to maintain a reverse sorted list of elements
	"""

	def __init__(self, *args: T | typing.Iterable[T]):
		"""
		[ReverseSortedList(SortedList)] - A list using binary search to search and maintain a reverse sorted list of elements
		- Constructor -
		:param args: (ANY) Either a variadic list of elements to use, or an iterable whose elements to use
		"""

		super().__init__([])

		if len(args) == 0:
			self.__buffer__ = []
		elif len(args) == 1 and isinstance(args[0], type(self)):
			self.__buffer__ = args[0].__buffer__.copy()
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

	def append(self, item: T) -> None:
		"""
		Appends an item to this collection
		:param item: (ANY) The item to append
		:return: (None)
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
		:param iterables: (*ITERABLES) The extra collections to append before resort
		:return: (None)
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
		:param iterables: (*ITERABLES) The extra collections to append before resort
		:return: (None)
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
		:param item: (ANY) The item to search for
		:param lower: (int?) The index's lower bound to search in
		:param upper: (int?) The index's upper bound to search in
		:return: (int) The position if found or -1
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

	def get_bounds(self, item: T) -> tuple[int, int]:
		"""
		Gets the start and end index for an item in this collection
		:param item: (ANY) The item to search for
		:return: (tuple[int, int]) The range of indices an item covers
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

	def removed_duplicates(self) -> ReverseSortedList[T]:
		"""
		Removes all duplicates from this collection
		:return: (SortedList) A copy  of this list with all duplicates removed
		"""

		return ReverseSortedList(set(self.__buffer__))

	def reversed(self) -> SortedList[T]:
		"""
		Reverses this collection
		:return: (SortedList) A reversed list
		"""

		return SortedList(self.__buffer__)


class String(Iterable):
	"""
	[String(Iterable)] - A class providing extended string functionality
	"""

	@Overload
	def __init__(self, string: str | bytes | bytearray | typing.Iterable[int] = ''):
		"""
		[String(Iterable)] - A class providing extended string functionality
		- Constructor -
		Depending on the specified value, iteration will yield a str, bytes-like, or int
		:param string: (str | bytes | bytearray) The string to use
		:raises TypeError: If 'string' is not a str, bytes, bytearray, or an iterable of ints
		"""

		if isinstance(string, str):
			super().__init__([ord(c) for c in string])
			self.__cls__ = str
		elif isinstance(string, (bytes, bytearray)):
			super().__init__(string)
			self.__cls__ = bytes
		else:
			super().__init__(int(x) for x in string)
			self.__cls__ = int

		self.__buffer__: list[int]

	def __contains__(self, item: str | String | bytes | int) -> bool:
		"""
		Checks if a substring or character is within this string
		:param item: (str | bytes | int) The substring or character code to check
		:return: (bool) Containedness
		"""

		char: tuple[int, ...] = (item,) if isinstance(item, int) else tuple(ord(c) for c in item) if isinstance(item, str) else tuple(item) if isinstance(item, bytes) else None
		this_length: int = len(self)
		length: int = len(char)

		if char is None:
			raise TypeError(f'\'item\' must be one of: str, bytes, int - got \'{type(item)}\'')

		for i in range(this_length - length + 1):
			if tuple(self.__buffer__[i:i + length]) == char:
				return True

		return False

	def __int__(self, base: int = 10) -> int:
		"""
		Returns the integer value of this string
		:param base: (int) The base to convert to
		:return: (int) The converted integer
		"""
		return int(str(self), base)

	def __float__(self) -> float:
		"""
		Returns the floating-point value of this string
		:return: (int) The converted float
		"""
		return float(str(self))

	def __bytes__(self) -> bytes:
		"""
		Converts this string into a bytes-like instance
		:return: (bytes) The bytestring
		"""

		return bytes(self.__buffer__)

	def __iter__(self) -> typing.Generator[str]:
		for x in self.__buffer__:
			yield chr(x) if self.__cls__ is str else x.to_bytes(1, sys.byteorder, signed=False) if self.__cls__ is bytes else x

	def __str__(self) -> str:
		"""
		Gets the string representation of this list
		:return: (str) Representation string
		"""

		return ''.join(chr(x) for x in self.__buffer__)

	def __repr__(self) -> str:
		"""
		Gets the string representation of this list
		:return: (str) Representation string
		"""

		quotes: str = '"""' if '\'' in self and '"' in self else '\'' if '"' in self else '"'
		return f'{quotes}{str(self)}{quotes}'

	def __add__(self, other: str | bytes | bytearray | String) -> String:
		"""
		Adds a string, bytes-like or String instance to this String
		:param other: (str | bytes | bytearray | String) The callback string to add
		:return: (String) A new String instance
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
		:param other: (str | bytes | bytearray | String) The callback string to add
		:return: (String) This instance
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
		:param other: (str | bytes | bytearray | String) The buffer to add this String to
		:return: (str | bytes | bytearray | String) A new, updated buffer whose type matches the specified argument
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
		:param n: (int) The number of times to multiply
		:return: (String) A new String instance
		"""

		if not isinstance(n, int):
			return NotImplemented

		copy: String = type(self)()
		copy.__buffer__ = self.__buffer__ * n
		return copy

	def __imul__(self, n: int) -> String:
		"""
		Multiplies the string 'n' times in-place
		:param n: (int) The number of times to multiply
		:return: (String) This instance
		"""

		if not isinstance(n, int):
			return NotImplemented

		self.__buffer__ *= n
		return self

	def __rmul__(self, n: int) -> String:
		"""
		Multiplies the string 'n' times
		:param n: (int) The number of times to multiply
		:return: (String) A new String instance
		"""

		if not isinstance(n, int):
			return NotImplemented

		copy: String = type(self)()
		copy.__buffer__ = self.__buffer__ * n
		return copy

	def __getitem__(self, item: int) -> str | bytes | bytearray | int | String:
		"""
		Gets one or more characters in this string
		:param item: (int | tuple[int] | slice) The index or indices to get
		:return: (str | bytes | bytearray | int | String) If a single element, only that item, otherwise a substring
		"""

		if isinstance(item, int):
			x: int = self.__buffer__[item]
			return chr(x) if self.__cls__ is str else x.to_bytes(1, sys.byteorder, signed=False) if self.__cls__ is bytes else x
		else:
			return super().__getitem__(item)

	def __setitem__(self, key: int, value: str | bytes | bytearray | int | String):
		"""
		Sets one or more characters in this string
		:param key: (int | tuple[int] | slice) The index or indices to modify
		:param value: (str | bytes | bytearray | int | String) The value to set
		:return: (None)
		"""

		raise NotImplementedError()

	def can_be_int(self) -> bool:
		"""
		Checks if this value can be converted to a base-10 integer
		:return: (bool) True if all characters are base-10 digits
		"""

		return all(chr(c).isdigit() for c in self.__buffer__)

	def can_be_float(self) -> bool:
		"""
		Checks if this value can be converted to a base-10 decimal
		:return: (bool) True if this string is a float
		"""

		try:
			float(str(self))
			return True
		except ValueError:
			return False

	def starts_with(self, prefix: str | String) -> bool:
		"""
		Checks if the specified string prefixes this string
		:param prefix: (str | String) The prefix to check
		:return: (bool) True if this string starts with 'prefix'
		"""

		if len(prefix) > len(self):
			return False

		for i, char in enumerate(self):
			if prefix[i] != char:
				return False

		return True

	def ends_with(self, postfix: str | String) -> bool:
		"""
		Checks if the specified string postfixes this string
		:param postfix: (str | String) The postfix to check
		:return: (bool) True if this string ends with 'postfix'
		"""

		if len(postfix) > len(self):
			return False

		for i in range(len(self) - 1, len(self) - len(postfix), -1):
			if postfix[i] != self[i]:
				return False

		return True

	def left_pad(self, length: int, pad_char: str | bytes | bytearray | int = ' ') -> String:
		"""
		Left pads this string with the specified character until greater than or equal to the specified length
		:param length: (int) The length to match
		:param pad_char: (str | bytes | bytearray | int) The character to pad with (defaults to space)
		:return: (String) A new String instance
		:raises ValueError: If a string or bytes-like is supplied and its length is greater than 1
		"""

		if isinstance(pad_char, (str, bytes, bytearray)) and len(pad_char) > 1:
			raise ValueError(f'Character must be of length 1 - got length {len(pad_char)}')
		elif isinstance(pad_char, (str, bytes, bytearray)) and len(pad_char) == 0:
			return self.copy()

		char: int = pad_char if isinstance(pad_char, int) else ord(pad_char) if isinstance(pad_char, str) else pad_char[0]

		while len(self) < length:
			self.__buffer__.append(char)

		return self

	def right_pad(self, length: int, pad_char: str | bytes | bytearray | int = ' ') -> String:
		"""
		Right pads this string with the specified character until greater than or equal to the specified length
		:param length: (int) The length to match
		:param pad_char: (str | bytes | bytearray | int) The character to pad with (defaults to space)
		:return: (String) A new String instance
		:raises ValueError: If a string or bytes-like is supplied and its length is greater than 1
		"""

		if isinstance(pad_char, (str, bytes, bytearray)) and len(pad_char) > 1:
			raise ValueError(f'Character must be of length 1 - got length {len(pad_char)}')
		elif isinstance(pad_char, (str, bytes, bytearray)) and len(pad_char) == 0:
			return self.copy()

		char: int = pad_char if isinstance(pad_char, int) else ord(pad_char) if isinstance(pad_char, str) else pad_char[0]

		while len(self) < length:
			self.__buffer__.insert(0, char)

		return self

	def to_upper(self) -> String:
		"""
		Converts all characters to their upper-case
		:return: (String) The upper-cased string
		"""

		return type(self)(ord(chr(c).upper()) for c in self.__buffer__)

	def to_lower(self) -> String:
		"""
		Converts all characters to their lower-case
		:return: (String) The lower-cased string
		"""

		return type(self)(ord(chr(c).lower()) for c in self.__buffer__)

	def capitalized(self) -> String:
		"""
		Converts the first, left-most character to it's upper-case
		:return: (String) The capitalized string
		"""

		if len(self) == 0:
			return self.copy()

		copy: String = self.copy()
		copy.__buffer__[0] = ord(chr(copy.__buffer__[0]).upper())
		return copy

	def substring(self, start: int, length: typing.Optional[int] = ...) -> String:
		"""
		Returns a substring 'length' characters long starting from 'start'
		:param start: (int) The start index
		:param length: (int?) The substring length
		:return: (String) A new String instance
		"""

		return self[start:start + length]


class FixedArray[T](SortableIterable):
	"""
	[FixedArray(SortableIterable)] - Class representing an array of a fixed size
	"""

	def __init__(self, iterable_or_size: typing.Iterable[T] | int):
		"""
		[FixedArray(SortableIterable)] - Class representing an array of a fixed size
		- Constructor -
		:param iterable_or_size: (ITERABLE | int) The iterable or number of elements this list contains
		"""

		if type(iterable_or_size) is int:
			super().__init__([None] * self.__size__)
			self.__size__: int = iterable_or_size
		else:
			super().__init__(iterable_or_size)
			self.__size__: int = len(self.__buffer__)

	def __len__(self) -> int:
		"""
		Returns the length of this list
		:return: (int) Lengthness
		"""

		return self.__size__

	def __delitem__(self, key: int | tuple[int, ...] | slice) -> None:
		"""
		Deletes one or more items in this list
		Deleted items are assigned 'None'
		:param key: (int | tuple[int] | slice) The index or indices to modify
		:return: (None)
		"""

		self[key] = None

	def clear(self) -> None:
		"""
		Clears the list, setting all elements to 'None'
		:return: (None)
		"""

		for i in range(len(self)):
			self.__buffer__[i] = None


class SpinQueue[T](SortableIterable):
	"""
	[SpinQueue(SortableIterable)] - Class representing a queue-like array of a maximum size
	"""

	def __init__(self, iterable_or_size: typing.Iterable[T] | int):
		"""
		[SpinQueue(SortableIterable)] - Class representing a queue-like array of a maximum size
		- Constructor -
		:param iterable_or_size: (ITERABLE | int) The iterable or number of elements this list contains
		"""

		if type(iterable_or_size) is int:
			super().__init__([None] * iterable_or_size)
			self.__max_size__: int = iterable_or_size
			self.__count__: int = 0
			self.__offset__: int = 0
		else:
			super().__init__(iterable_or_size)
			self.__max_size__: int = len(self.__buffer__)
			self.__count__: int = 0
			self.__offset__: int = 0

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
		if not isinstance(index, int):
			raise TypeError(f'SpinQueue indices must be of type int, got \'{type(index)}\'')
		elif index >= self.__count__:
			raise IndexError(f'Specified index \'{index}\' is out of bounds for SpinQueue of count \'{self.__count__}\'')

		return self.__buffer__[(self.__offset__ + ((self.__count__ + index) if index < 0 else index)) % self.__max_size__]

	def __setitem__(self, index: int, value: T) -> None:
		if not isinstance(index, int):
			raise TypeError(f'SpinQueue indices must be of type int, got \'{type(index)}\'')
		elif index >= self.__count__:
			raise IndexError(f'Specified index \'{index}\' is out of bounds for SpinQueue of count \'{self.__count__}\'')

		self.__buffer__[(self.__offset__ + index) % self.__max_size__] = value

	def append(self, item: T) -> tuple[bool, T]:
		"""
		Pushes an item onto the queue and returns the first item if max size is exceeded
		:param item: (ANY) The item to append
		:return: (tuple[bool, ANY]) A tuple indicating whether an item was popped and the item
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
		self.__count__ = 0
		self.__offset__ = 0

		for i in range(self.__max_size__):
			self.__buffer__[i] = None

	def pop(self) -> T:
		"""
		Pops an item from the queue
		:return: (ANY) The popped item
		"""

		if self.__count__ == 0:
			raise IndexError('Pop from empty queue')

		self.__count__ -= 1
		position: int = (self.__offset__ + self.__count__) % self.__max_size__
		elem: T = self.__buffer__[position]
		self.__buffer__[position] = None
		return elem

	@property
	def maxlen(self) -> int:
		return self.__max_size__


class ThreadedGenerator[T]:
	"""
	[ThreadedGenerator] - Special generator using threading.Thread threads
	"""

	def __init__(self, generator: typing.Generator | typing.Iterable[T]):
		"""
		[ThreadedGenerator] - Special generator using threading.Thread threads
		- Constructor -
		:param generator: The initial generator or iterable to iterate
		"""

		self.__buffer = []
		self.__thread = threading.Thread(target=self.__mainloop)
		self.__state = False
		self.__iterator = iter(generator)
		self.__exec = None

		self.__thread.start()

	def __del__(self) -> None:
		self.close()

	def __mainloop(self) -> None:
		"""
		INTERNAL METHOD; DO NOT USE
		Starts the threaded generator
		:return: (None)
		"""

		self.__state = True
		base_count = sys.getrefcount(self)

		try:
			while self.__state and sys.getrefcount(self) >= base_count:
				self.__buffer.append(next(self.__iterator))
		except (SystemExit, KeyboardInterrupt, Exception) as e:
			self.__state = False
			self.__exec = e

	def __next__(self) -> T:
		"""
		Waits until a new value is available or until internal thread is closed
		Returns next value or raises StopIteration
		:return: (ANY) The next value
		:raises StopIteration: If iteration is complete
		"""

		try:
			while len(self.__buffer) == 0:
				if type(self.__exec) is StopIteration or not self.__thread.is_alive():
					raise StopIteration
				time.sleep(1e-7)

			return self.__buffer.pop(0)
		except (KeyboardInterrupt, SystemExit) as e:
			self.__exec = e
			self.close()
			raise e

	def __iter__(self):
		return self

	def close(self) -> None:
		"""
		Closes the iterator
		Raises an exception if an exception occured during iteration
		:return: (None)
		"""

		if not self.__state:
			return

		self.__state = False

		if self.__thread.is_alive():
			self.__thread.join()

		if self.__exec is not None:
			raise self.__exec


def frange(start: float, stop: float = None, step: float = 1, precision: int = None) -> typing.Generator[float, None, None]:
	"""
	Float compatible range generator
	:param start: (float) Start of range
	:param stop: (float) End of range
	:param step: (float) Step
	:param precision: (int) Number of digits to round, or no rounding if None
	:return: (GENERATOR[float]) A generator iterating the range
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