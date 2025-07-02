from __future__ import annotations

import typing

from .. import Iterable


class Set[T](Iterable.LinqIterable):
	def __init__(self, *args: T | typing.Iterable[T]):
		super().__init__([])

		if len(args) == 0:
			self.__set_collection__: Iterable.SortedList[T] = Iterable.SortedList()
		elif len(args) == 1:
			assert hasattr(args[0], '__iter__'), 'Set argument must be an iterable'
			self.__set_collection__: Iterable.SortedList[T] = Iterable.SortedList(set(args[0]))
		else:
			self.__set_collection__: Iterable.SortedList[T] = Iterable.SortedList(set(args))

	def __len__(self) -> int:
		return len(self.__set_collection__)

	def __repr__(self) -> str:
		return str(self)

	def __str__(self):
		return f'{{{", ".join(map(repr, self.__set_collection__))}}}'

	def __iter__(self) -> typing.Iterator[T]:
		return iter(self.__set_collection__)

	def __contains__(self, item: T) -> bool:
		return item in self.__set_collection__

	def add(self, item: T) -> None:
		if item not in self.__set_collection__:
			self.__set_collection__.append(item)

	def remove(self, item: T) -> None:
		self.__set_collection__.remove(item)

	def clear(self) -> None:
		self.__set_collection__.clear()

	def update(self, *iterables: typing.Iterable[T]) -> None:
		self.__set_collection__.set_resort(*iterables)

	def difference_update(self, *iterable: typing.Iterable[T]) -> None:
		assert hasattr(iterable, '__iter__'), 'Argument must be an iterable'

		for i in iterable:
			for j in i:
				if j in self:
					self.remove(j)

	def mean(self) -> T:
		return sum(self) / len(self)

	def median(self) -> T:
		index: int = len(self) // 2
		return self.__buffer__[index]

	def union(self, iterable: typing.Iterable[T]) -> Set[T]:
		assert hasattr(iterable, '__iter__'), 'Argument must be an iterable'
		return self.__set_collection__.copy().extended(iterable)

	def difference(self, iterable: typing.Iterable[T]) -> Set[T]:
		assert hasattr(iterable, '__iter__'), 'Argument must be an iterable'
		return Set(set(self.__set_collection__).difference(iterable))

	def cross_product(self, iterable: typing.Iterable[T]) -> Set[tuple[T, T]]:
		assert hasattr(iterable, '__iter__'), 'Argument must be an iterable'
		other: Set[T] = Set(iterable)
		output: list[tuple[T, T]] = []

		for a in self:
			for b in other:
				output.append((a, b))

		return Set(output)

	def domain(self) -> Set[T]:
		domain = []

		for x in self:
			if not hasattr(x, '__iter__'):
				raise TypeError('Set is one-dimensional')
			domain.append(x[0])

		return Set(domain)

	def co_domain(self) -> Set[T]:
		domain = []

		for x in self:
			if not hasattr(x, '__iter__'):
				raise TypeError('Set is one-dimensional')
			elif len(x) < 2:
				raise TypeError('Set has no co-domain')
			domain.append(x[1])

		return Set(domain)

	def copy(self) -> Set:
		return Set(self.__set_collection__.copy())


