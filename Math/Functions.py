import math

from CustomMethodsVI.Decorators import Overload


@Overload
def factorial(x: int) -> int:
	return math.prod(x for x in range(1, x + 1))


@Overload
def combination(n: int, r: int) -> int:
	return factorial(n) // (factorial(r) * factorial(n - r))
