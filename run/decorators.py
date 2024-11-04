import typing

from CustomMethodsVI.Decorators import Overload, DefaultOverload
from CustomMethodsVI.Math.Vector import Vector


@Overload(strict=False)
def func(b: float, a: float) -> float:
	print(a, type(a))
	print(b, type(b))
	return a + b


if __name__ == '__main__':
	# print(func(1, 2))
	a = Vector(x for x in range(3))
	print(a)
