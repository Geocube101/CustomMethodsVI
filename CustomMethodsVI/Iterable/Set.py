from __future__ import annotations

import collections

from . import Iterable
from .. import Exceptions
from .. import Misc
from .. import Synchronization


class Set[T](Iterable.Iterable[set[T], T], collections.abc.Set[T]):
	"""
	Base iterable class for CM-VI sets
	"""

	def __init__(self, collection: collections.abc.Iterable[T] = ...):
		"""
		Base iterable class for CM-VI sets\n
		- Constructor -
		:param collection: The sequence to build from
		"""

		super().__init__(set() if collection is None or collection is ... else set(collection))

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

	def __add__(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Unifies this set with another iterable
		:param other: The other iterable
		:return: The unified set
		"""

		return type(self)([*self, *other]) if isinstance(other, collections.abc.Iterable) else NotImplemented

	def __sub__(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Differentiates this set
		:param other: The other iterable
		:return: The set difference of this set and 'other'
		"""

		return self.difference(other)

	def __or__(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Unifies this set with another iterable
		:param other: The other iterable
		:return: The unified set
		"""

		return self + other

	def __and__(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Intersects this set
		:param other: The other iterable
		:return: The intersection of this set and 'other'
		"""

		return self.intersection(other) if isinstance(other, collections.abc.Iterable) else NotImplemented

	def __radd__(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Unifies this set with another iterable
		:param other: The other iterable
		:return: The unified set
		"""

		return type(self)([*other, *self]) if isinstance(other, collections.abc.Iterable) else NotImplemented

	def __rsub__(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Differentiates this set
		:param other: The other iterable
		:return: The set difference of this set and 'other'
		"""

		return self.difference(other)

	def __ror__(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Unifies this set with another iterable
		:param other: The other iterable
		:return: The unified set
		"""

		return other + self

	def __rand__(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Intersects this set
		:param other: The other iterable
		:return: The intersection of this set and 'other'
		"""

		return self.intersection(other) if isinstance(other, collections.abc.Iterable) else NotImplemented

	def copy[I: Set](self: I) -> I:
		"""
		:return: A copy of this set
		"""

		return type(self)(self.__buffer__.copy())

	def difference(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Performs the set difference between this set and another iterable
		:param other: The other iterable
		:return: The set difference
		"""

		return type(self)(self.__buffer__.difference(other))

	def union(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Performs the set union between this set and another iterable
		:param other: The other iterable
		:return: The set union
		"""

		return type(self)({*self, *other})

	def intersection(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Performs the set intersection between this set and another iterable
		:param other: The other iterable
		:return: The set intersection
		"""

		return type(self)(self.__buffer__.intersection(other))


class MutableSet[T](Set[T], collections.abc.MutableSet[T]):
	"""
	Set class allowing modifications
	"""

	def __iadd__(self, other: collections.abc.Iterable[T]) -> MutableSet[T]:
		"""
		Unifies this set with another iterable in-place
		:param other: The other iterable
		:return: This set
		"""

		if not isinstance(other, collections.abc.Iterable):
			return NotImplemented

		self.__buffer__.update(other)
		return self

	def __isub__(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Differentiates this set in-place
		:param other: The other iterable
		:return: This set
		"""

		for item in other:
			self.discard(item)

		return self

	def __ior__(self, other: collections.abc.Iterable[T]) -> MutableSet[T]:
		"""
		Unifies this set with another iterable in-place
		:param other: The other iterable
		:return: This set
		"""

		return self.__iadd__(other)

	def __iand__(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Intersects this set in-place
		:param other: The other iterable
		:return: This set
		"""

		self.__buffer__.intersection_update(other)
		return self

	def remove(self, value: T) -> bool:
		"""
		Discards an element from this set
		:param value: The element to discard
		:return: Whether the element was in this set
		"""

		try:
			self.__buffer__.remove(value)
			return True
		except KeyError:
			return False

	def discard(self, value: T) -> Set[T]:
		"""
		Discards an element from this set
		:param value: The element to discard
		:return: This set
		"""

		self.__buffer__.discard(value)
		return self

	def add(self, value: T) -> Set[T]:
		"""
		Adds an element to this set
		:param value: The element to add
		:return: This set
		"""

		self.__buffer__.add(value)
		return self

	def clear(self) -> Set[T]:
		"""
		Clears the set
		:return: This set
		"""

		self.__buffer__.clear()
		return self

	def replace(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Replaces all contents in this set with the new collection
		:param other: The iterable to update from
		:return: This set
		"""

		self.__buffer__.clear()
		self.__buffer__.update(other)
		return self

	def differ(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Performs the set difference between this set and another iterable in-place
		:param other: The other iterable
		:return: This set
		"""

		self.__buffer__.difference_update(other)
		return self

	def unionify(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Performs the set union between this set and another iterable in-place
		:param other: The other iterable
		:return: This set
		"""

		self.__buffer__.update(other)
		return self

	def intersect(self, other: collections.abc.Iterable[T]) -> Set[T]:
		"""
		Performs the set intersection between this set and another iterable in-place
		:param other: The other iterable
		:return: The set intersection
		:return: This set
		"""

		self.__buffer__.intersection_update(other)
		return self


class LockedSet[T](MutableSet[T], Synchronization.Synchronization.LockUser):
	"""
	Thread safe set using locks
	"""

	def __init__(self, hashset: collections.abc.Iterable[T] = ..., *, lock: Synchronization.Synchronization.LockType_T = ...):
		"""
		Thread safe set using locks\n
		- Constructor -
		:param hashset: The initial set
		:param lock: The lock to use for operations
		"""

		MutableSet.__init__(self, hashset)
		Synchronization.Synchronization.LockUser.__init__(self, Synchronization.Threading.SpinLock() if lock is ... or lock is None else lock)

	def __repr__(self) -> str:
		with self.read_lock():
			return repr(self.__buffer__)

	def __str__(self) -> str:
		with self.read_lock():
			return str(self.__buffer__)

	def __add__(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.read_lock():
			return type(self)([*self, *other]) if isinstance(other, collections.abc.Iterable) else NotImplemented

	def __iadd__(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		if not isinstance(other, collections.abc.Iterable):
			return NotImplemented

		with self.write_lock():
			self.__buffer__.update(other)
			return self

	def __radd__(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.read_lock():
			return type(self)([*other, *self]) if isinstance(other, collections.abc.Iterable) else NotImplemented

	def __isub__(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.write_lock():
			for item in other:
				self.discard(item)

			return self

	def __and__(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.read_lock():
			return self.intersection(other) if isinstance(other, collections.abc.Iterable) else NotImplemented

	def __rand__(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.read_lock():
			return self.intersection(other) if isinstance(other, collections.abc.Iterable) else NotImplemented

	def __iter__(self) -> collections.abc.Iterator[T]:
		with self.read_lock():
			copy: tuple[T, ...] = tuple(self.__buffer__)
			return iter(copy)

	def remove(self, value: T) -> bool:
		with self.write_lock():
			try:
				self.__buffer__.remove(value)
				return True
			except KeyError:
				return False

	def discard(self, value: T) -> LockedSet[T]:
		with self.write_lock():
			self.__buffer__.discard(value)
			return self

	def add(self, value: T) -> LockedSet[T]:
		with self.write_lock():
			self.__buffer__.add(value)
			return self

	def clear(self) -> LockedSet[T]:
		with self.write_lock():
			self.__buffer__.clear()
			return self

	def copy[I: LockedSet](self: I) -> I:
		with self.read_lock():
			return type(self)(self.__buffer__.copy())

	def difference(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.read_lock():
			return type(self)(self.__buffer__.difference(other))

	def union(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.read_lock():
			return type(self)({*self, *other})

	def intersection(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.read_lock():
			return type(self)(self.__buffer__.intersection(other))

	def replace(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.write_lock():
			self.__buffer__.clear()
			self.__buffer__.update(other)
			return self

	def differ(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.write_lock():
			self.__buffer__.difference_update(other)
			return self

	def unionify(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.write_lock():
			self.__buffer__.update(other)
			return self

	def intersect(self, other: collections.abc.Iterable[T]) -> LockedSet[T]:
		with self.write_lock():
			self.__buffer__.intersection_update(other)
			return self


class SetView[T](Iterable.IterableView[Set, T]):
	def __init__(self, iterable: Set[T]):
		"""
		Class allowing a view into a collection\n
		- Constructor -
		:param iterable: The iterable to view
		"""

		Misc.raise_ifn(isinstance(iterable, Set), Exceptions.InvalidArgumentException(SetView.__init__, 'iterable', type(iterable), (Set,)))
		super().__init__(iterable)


__all__: list[str] = ['Set', 'MutableSet', 'LockedSet', 'SetView']
