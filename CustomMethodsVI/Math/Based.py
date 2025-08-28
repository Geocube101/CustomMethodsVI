from __future__ import annotations

import typing

from .. import Exceptions
from .. import Misc
from ..Decorators import Overload


class BaseNumber:
	"""
	Represents a number converted to base-N
	"""

	@Overload(strict=True)
	def __init__(self, base: int, digits: typing.Iterable[int]):
		"""
		Represents a number converted to base-N
		- Constructor -
		SHOULD NOT BE CALLED DIRECTLY; USE 'BaseN.convert'
		:param base: (int) The base of the number
		:param digits: (tuple[int]) The digits that make up this number
		"""

		self.__base__: int = int(base)
		self.__digits__: tuple[int, ...] = tuple(digits)

	@Overload(strict=True)
	def to_base(self, base: int) -> BaseNumber:
		"""
		Converts this number through base 10 to another base
		:param base: The new base to convert to (should be an integer greater than 1)
		:return: This number converted to the specified base
		"""

		return BaseNumber(self.__base__, self.__digits__) if base == self.__base__ else BaseN(base).convert(int(self))

	def precision(self) -> int:
		"""
		Calculates how many digits are needed to represent this number
		:return: The precision of this BaseNumber
		"""

		first: int = 0
		last: int = len(self.__digits__)

		while first < last:
			if self.__digits__[first] == 0:
				first += 1
			else:
				break

		while last > first:
			if self.__digits__[last - 1] == 0:
				last -= 1
			else:
				break

		return last - first

	def half_complement(self, size: typing.Optional[int] = ...) -> BaseNumber:
		"""
		Calculates the half complement of this number
		:param size: The minimum size to pad the result number to
		:return: The half complement of this number
		:raises ValueError: If the size is not an integer >= 1
		"""

		deltas: list[int] = [(self.__base__ - digit - 1) % self.__base__ for digit in self.__digits__]

		if size is not None and size is not ...:
			Misc.raise_ifn(isinstance(size, int) and (size := int(size)) > 0, ValueError('Size must be an integer >= 1'))

			while len(deltas) < size:
				deltas.insert(0, self.__base__ - 1)

			while len(deltas) > size and deltas[0] == 0:
				deltas.pop(0)

		return BaseNumber(self.__base__, deltas)

	def full_complement(self, size: typing.Optional[int] = ...) -> BaseNumber:
		"""
		Calculates the full complement of this number
		Equal to the half complement plus 1
		:param size: The minimum size to pad the result number to
		:return: The full complement of this number
		:raises ValueError: If the size is not an integer >= 1
		"""

		return self.half_complement(size) + 1

	def of_size(self, size: int) -> BaseNumber:
		"""
		Truncates or extends this number to the specified number of digits
		:param size: The specified number of digits
		:return: The new number
		:raises ValueError: If the size is not an integer >= 0
		"""

		Misc.raise_ifn(isinstance(size, int) and (size := int(size)) >= 0, ValueError('Size must be an integer >= 0'))
		digits: tuple[int, ...] = (*([0] * size), *self.__digits__)
		return BaseNumber(self.__base__, digits[-size:])

	def __repr__(self):
		return str(self)

	def __str__(self):
		return ''.join(('-' if x < 0 else '') + (str(x) if abs(x) <= 9 else chr(abs(x) - 9 + 64)) for x in self.__digits__)

	def __int__(self) -> int:
		return sum(d * self.__base__ ** i for i, d in enumerate(reversed(self.__digits__)))

	def __add__(self, other: BaseNumber | int) -> BaseNumber:
		if isinstance(other, int):
			other = BaseN(10).convert(other)
		elif not isinstance(other, BaseNumber):
			return NotImplemented

		digits_b: tuple[int, ...] = other.to_base(self.__base__).__digits__
		length: int = max(len(self.__digits__), len(digits_b))
		digits_a: tuple[int, ...] = (*([0] * max(0, length - len(self.__digits__))), *self.__digits__)
		digits_b = (*([0] * max(0, length - len(digits_b))), *digits_b)
		carry: int = 0
		digits: list[int] = []

		for i in range(length):
			digit_a: int = digits_a[i]
			digit_b: int = digits_b[i]
			result: int = digit_a + digit_b + carry

			while result >= self.__base__:
				carry += 1
				result -= self.__base__

			digits.append(result)

		digits.insert(0, carry)

		while len(digits) > 1 and digits[0] == 0:
			digits.pop(0)

		return BaseNumber(self.__base__, tuple(digits))

	@property
	def digits(self) -> tuple[int, ...]:
		"""
		:return: The digits (arranged most significant first) that make up this number
		"""

		return self.__digits__

	@property
	def digit_length(self) -> int:
		"""
		:return: The number of digits to represent this number
		"""
		return len(self.__digits__)

	@property
	def base(self) -> int:
		"""
		:return: The base of this number
		"""
		return self.__base__


class BaseN:
	"""
	Class for converting a base 10 number into another base
	"""

	@Overload
	def __init__(self, base: int):
		"""
		Class for converting a base 10 number into another base
		- Constructor -
		:param base: The base to convert to
		:raises AssertionError: If the base is less than 2
		"""

		assert base >= 2, f'Minimum base is 2, got {base}'
		self.__base__ = int(base)  # type: int

	def __repr__(self):
		return str(self)

	def __str__(self):
		return f'Base<{self.__base__}> Converter'

	#@Overload
	def convert(self, x: int | BaseNumber) -> BaseNumber:
		"""
		Converts the given number to this base
		:param x: The number to convert
		:return: The converted number
		:raises InvalidArgumentException: If 'x' is not an integer or BaseNumber
		"""

		if isinstance(x, BaseNumber):
			return x.to_base(self.__base__)
		elif isinstance(x, int):
			negative: int = -1 if x < 0 else 1

			if x == 0:
				return BaseNumber(self.__base__, (0,))
			x: int = abs(x)
			digits: list[int] = []

			while x >= self.__base__:
				digits.append(x % self.__base__)
				x //= self.__base__

			digits.append(x)
			digits[-1] *= negative
			return BaseNumber(self.__base__, tuple(reversed(digits)))
		else:
			raise Exceptions.InvalidArgumentException(self.convert, 'x', type(x), (int, BaseNumber))

	@property
	def base(self) -> int:
		"""
		:return: The current base of this number converter
		"""

		return self.__base__
