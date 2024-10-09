from __future__ import annotations

import typing

from CustomMethodsVI import Iterable


class Set:
	def __init__(self, *args):
		if len(args) == 0:
			self.__set__ = Iterable.SortedList()
		elif len(args) == 1:
			assert hasattr(args[0], '__iter__'), 'Set argument must be an iterable'
			self.__set__ = Iterable.SortedList(set(args[0]))
		else:
			self.__set__ = Iterable.SortedList(set(args))

	def __len__(self) -> int:
		return len(self.__set__)

	def __repr__(self) -> str:
		return str(self)

	def __str__(self):
		return f'{{{", ".join(map(repr, self.__set__))}}}'

	def __iter__(self) -> typing.Iterator:
		return iter(self.__set__)

	def __contains__(self, item: typing.Any) -> bool:
		return item in self.__set__

	def add(self, item: typing.Any) -> None:
		if item not in self.__set__:
			self.__set__.append(item)

	def remove(self, item: typing.Any) -> None:
		self.__set__.remove(item)

	def clear(self) -> None:
		self.__set__.clear()

	def update(self, *iterables) -> None:
		self.__set__.set_resort(iterables)

	def difference_update(self, *iterable) -> None:
		assert hasattr(iterable, '__iter__'), 'Argument must be an iterable'
		for i in iterable:
			if i in self:
				self.remove(i)

	def union(self, iterable: typing.Iterable) -> Set:
		assert hasattr(iterable, '__iter__'), 'Argument must be an iterable'
		return self.__set__.copy().extended(iterable)

	def difference(self, iterable: typing.Iterable) -> Set:
		assert hasattr(iterable, '__iter__'), 'Argument must be an iterable'
		return Set(set(self.__set__).difference(iterable))

	def cross_product(self, iterable: typing.Iterable) -> Set:
		assert hasattr(iterable, '__iter__'), 'Argument must be an iterable'
		other = Set(iterable)
		output = []

		for a in self:
			for b in other:
				output.append((a, b))

		return Set(output)

	def filter(self, filter_: typing.Callable) -> Set:
		return Set(x for x in self if (filter_(*x) if hasattr(x, '__iter__') else filter_(x)))

	def map(self, callback: typing.Callable) -> Set:
		return Set(callback(*x) if hasattr(x, '__iter__') else callback(x) for x in self)

	def domain(self) -> Set:
		domain = []

		for x in self:
			if not hasattr(x, '__iter__'):
				raise TypeError('Set is one-dimensional')
			domain.append(x[0])

		return Set(domain)

	def co_domain(self) -> Set:
		domain = []

		for x in self:
			if not hasattr(x, '__iter__'):
				raise TypeError('Set is one-dimensional')
			elif len(x) < 2:
				raise TypeError('Set has no co-domain')
			domain.append(x[1])

		return Set(domain)

	def copy(self) -> Set:
		return Set(self.__set__.copy())


