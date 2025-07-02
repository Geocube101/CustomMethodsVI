import math

from ..Decorators import Overload


@Overload
def factorial(x: int) -> int:
	"""
	Calculates the factorial for a given integer
	:param x: (int) The factorial value
	:return: (int) x!
	"""

	return math.prod(x for x in range(1, x + 1))


@Overload
def combination(n: int, r: int) -> int:
	"""
	Calculates the combination of (n r)
	:param n:
	:param r:
	:return:
	"""

	return factorial(n) // (factorial(r) * factorial(n - r))


@Overload
def sdivide(a: float, b: float) -> float:
	"""
	Performs a safe divide of two numbers
	If A and B is 0, returns NaN
	If B is 0, returns inf
	If A and B is inf, returns NaN
	If B is inf, returns 0
	:param a: (float) A
	:param b: (float) B
	:return: (float) The divided value
	"""

	inf: float = float('inf')
	return float('nan') if a == 0 and b == 0 or a == inf and b == inf else 0 if b == inf else inf if b == 0 else (a / b)