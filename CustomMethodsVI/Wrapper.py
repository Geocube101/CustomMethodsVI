from __future__ import annotations

import collections.abc
import math
import typing

from . import Exceptions
from . import Misc


class ValueWrapper[T]:
	@classmethod
	def set_value[A, B](cls, wrapper: ValueWrapper[A], new_value: B) -> None:
		Misc.raise_ifn(isinstance(wrapper, cls), Exceptions.InvalidArgumentException(ValueWrapper.get_value, 'wrapper', type(wrapper), (cls,)))
		wrapper.__value = new_value

	@classmethod
	def get_value[V](cls, wrapper: ValueWrapper[V]) -> V:
		Misc.raise_ifn(isinstance(wrapper, cls), Exceptions.InvalidArgumentException(ValueWrapper.get_value, 'wrapper', type(wrapper), (cls,)))
		return wrapper.__value

	@classmethod
	def get_type[V](cls, wrapper: ValueWrapper[V]) -> type[V]:
		Misc.raise_ifn(isinstance(wrapper, cls), Exceptions.InvalidArgumentException(ValueWrapper.get_type, 'wrapper', type(wrapper), (cls,)))
		return type(wrapper.__value)

	def __init__(self, value: T):
		self.__value: T = value.__value if isinstance(value, ValueWrapper) else value

	def __repr__(self) -> str:
		return repr(self.__value)

	def __eq__(self, other: typing.Any) -> typing.Any:
		return self.__value == other

	def __ne__(self, other: typing.Any) -> typing.Any:
		return self.__value != other

	def __hash__(self) -> int:
		return hash(self.__value)

	def __lt__(self, other: typing.Any) -> typing.Any:
		return self.__value < other

	def __le__(self, other: typing.Any) -> typing.Any:
		return self.__value <= other

	def __gt__(self, other: typing.Any) -> typing.Any:
		return self.__value > other

	def __ge__(self, other: typing.Any) -> typing.Any:
		return self.__value >= other

	def __str__(self) -> str:
		return str(self.__value)

	def __float__(self) -> float:
		return float(self.__value)

	def __int__(self) -> int:
		return int(self.__value)

	def __bytes__(self) -> bytes:
		return bytes(self.__value)

	def __complex__(self) -> complex:
		return complex(self.__value)

	def __format__(self, format_string: str) -> str:
		return format(self.__value, format_string)

	def __enter__(self) -> typing.Any:
		return self.__value.__enter__()

	def __exit__(self, exc_type, exc_val, exc_tb) -> typing.Any:
		return self.__value.__exit__(exc_type, exc_val, exc_tb)

	def __len__(self) -> int:
		return len(self.__value)

	def __iter__(self) -> collections.abc.Iterator:
		return iter(self.__value)

	def __getitem__(self, item: typing.Any) -> typing.Any:
		return self.__value[item]

	def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
		self.__value[key] = value

	def __delitem__(self, key: typing.Any) -> None:
		del self.__value[key]

	def __contains__(self, item: typing.Any) -> bool:
		return item in self.__value

	def __reversed__(self) -> collections.abc.Iterator:
		return reversed(self.__value)

	def __next__(self) -> typing.Any:
		return next(self.__value)

	def __missing__(self, key: typing.Any) -> typing.Any:
		return self.__value.__missing__(key)

	def __length_hint__(self) -> int:
		return self.__value.__length_hint__()

	def __call__(self, *args, **kwargs) -> typing.Any:
		return self.__value(*args, **kwargs)

	def __add__(self, other: typing.Any) -> typing.Any:
		return self.__value + other

	def __radd__(self, other: typing.Any) -> typing.Any:
		return other + self.__value

	def __iadd__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value += other
		return self

	def __sub__(self, other: typing.Any) -> typing.Any:
		return self.__value - other

	def __rsub__(self, other: typing.Any) -> typing.Any:
		return other - self.__value

	def __isub__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value -= other
		return self

	def __mul__(self, other: typing.Any) -> typing.Any:
		return self.__value * other

	def __rmul__(self, other: typing.Any) -> typing.Any:
		return other * self.__value

	def __imul__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value *= other
		return self

	def __truediv__(self, other: typing.Any) -> typing.Any:
		return self.__value / other

	def __rtruediv__(self, other: typing.Any) -> typing.Any:
		return other / self.__value

	def __itruediv__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value /= other
		return self

	def __mod__(self, other: typing.Any) -> typing.Any:
		return self.__value % other

	def __rmod__(self, other: typing.Any) -> typing.Any:
		return other % self.__value

	def __imod__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value %= other
		return self

	def __floordiv__(self, other: typing.Any) -> typing.Any:
		return self.__value // other

	def __rfloordiv__(self, other: typing.Any) -> typing.Any:
		return other // self.__value

	def __ifloordiv__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value //= other
		return self

	def __pow__(self, other: typing.Any) -> typing.Any:
		return self.__value ** other

	def __rpow__(self, other: typing.Any) -> typing.Any:
		return other ** self.__value

	def __ipow__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value **= other
		return self

	def __matmul__(self, other: typing.Any) -> typing.Any:
		return self.__value @ other

	def __rmatmul__(self, other: typing.Any) -> typing.Any:
		return other @ self.__value

	def __imatmul__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value @= other
		return self

	def __and__(self, other: typing.Any) -> typing.Any:
		return self.__value & other

	def __rand__(self, other: typing.Any) -> typing.Any:
		return other & self.__value

	def __iand__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value &= other
		return self

	def __or__(self, other: typing.Any) -> typing.Any:
		return self.__value | other

	def __ror__(self, other: typing.Any) -> typing.Any:
		return other | self.__value

	def __ior__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value |= other
		return self

	def __xor__(self, other: typing.Any) -> typing.Any:
		return self.__value ^ other

	def __rxor__(self, other: typing.Any) -> typing.Any:
		return other ^ self.__value

	def __ixor__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value ^= other
		return self

	def __rshift__(self, other: typing.Any) -> typing.Any:
		return self.__value >> other

	def __rrshift__(self, other: typing.Any) -> typing.Any:
		return other >> self.__value

	def __irshift__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value >>= other
		return self

	def __lshift__(self, other: typing.Any) -> typing.Any:
		return self.__value << other

	def __rlshift__(self, other: typing.Any) -> typing.Any:
		return other << self.__value

	def __ilshift__(self, other: typing.Any) -> ValueWrapper[T]:
		self.__value <<= other
		return self

	def __neg__(self) -> typing.Any:
		return -self.__value

	def __pos__(self) -> typing.Any:
		return +self.__value

	def __invert__(self) -> typing.Any:
		return ~self.__value

	def __divmod__(self, other: typing.Any) -> typing.Any:
		return divmod(self.__value, other)

	def __rdivmod__(self, other: typing.Any) -> typing.Any:
		return divmod(other, self.__value)

	def __abs__(self) -> typing.Any:
		return abs(self.__value)

	def __index__(self) -> int:
		return self.__value.__index__()

	def __round__(self, n: typing.Optional[int] = None) -> typing.Any:
		return round(self.__value, n)

	def __trunc__(self) -> typing.Any:
		return math.trunc(self.__value)

	def __floor__(self) -> typing.Any:
		return math.floor(self.__value)

	def __ceil__(self) -> typing.Any:
		return math.ceil(self.__value)

	def __getattr__(self, item: str) -> typing.Any:
		return getattr(self.__value, item)

	def __setattr__(self, key: str, value: typing.Any) -> None:
		if key == '_ValueWrapper__value':
			super().__setattr__(key, value)
			return

		setattr(self.__value, key, value)

	def __delattr__(self, item: str) -> typing.Any:
		return delattr(self.__value, item)

	def __dir__(self) -> list[str]:
		return dir(self.__value)


class Reference[T]:
	def __init__(self, value: T):
		"""
		A reference wrapping a single value
		:param value: The value to reference
		"""

		self.__value__: T = value

	def set_value(self, value: T) -> None:
		"""
		Updates the internal value
		:param value: The new value
		"""

		self.__value__ = value

	def get_value(self) -> T:
		"""
		:return: The value
		"""

		return self.__value__

	@property
	def value(self) -> T:
		"""
		:return: The value
		"""

		return self.get_value()

	@value.setter
	def value(self, value: T) -> None:
		self.set_value(value)


class OptionalReference[T](Reference[T]):
	@classmethod
	def create_empty(cls) -> OptionalReference[T]:
		"""
		:return: An empty optional
		"""

		return cls(exists=False)

	@classmethod
	def create_value(cls, value: T) -> OptionalReference[T]:
		"""
		:return: An optional containing the specifed value
		"""

		return cls(value, exists=True)

	def __init__(self, value: T = ..., *, exists: bool = True):
		"""
		A reference wrapping a single optional value
		:param value: The value to reference or ... if does not exist
		:param exists: Whether the value exists
		"""

		self.__exists__: bool = bool(exists)
		super().__init__(value if self.has_value else ...)

	def set_value(self, value: T) -> None:
		super().set_value(value)
		self.__exists__ = True

	def clear_value(self) -> None:
		"""
		Clears the internal value
		"""

		self.set_value(...)
		self.__exists__ = False

	def get_value(self) -> T:
		assert self.has_value, 'Optional has no value'
		return super().get_value()

	@property
	def has_value(self) -> bool:
		"""
		:return: Whether this reference has a value
		"""

		return self.__exists__


__all__: list[str] = ['ValueWrapper', 'Reference', 'OptionalReference']
