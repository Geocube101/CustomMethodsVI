import math

from ..Decorators import Overload


@Overload
def factorial(x: int) -> int:
	"""
	Calculates the factorial for a given integer
	:param x: The input integer value
	:return: x!
	"""

	return math.prod(y for y in range(1, int(x) + 1))


@Overload
def combination(n: int, r: int) -> int:
	"""
	Calculates the combination of (n r)
	:param n:
	:param r:
	:return:
	"""

	n = int(n)
	r = int(r)
	return factorial(n) // (factorial(r) * factorial(n - r))


@Overload
def safe_divide(a: float, b: float) -> float:
	"""
	Performs a safe divide of two numbers
	If A and B is 0, returns NaN
	If B is 0, returns inf
	If A and B is inf, returns NaN
	If B is inf, returns 0
	:param a: First operand
	:param b: Second operand
	:return: The quotient
	"""

	a = float(a)
	b = float(b)
	inf: float = float('inf')
	return float('nan') if a == 0 and b == 0 or a == inf and b == inf else 0 if b == inf else inf if b == 0 else (a / b)


@Overload
def safe_floor_divide(a: float, b: float) -> float:
	"""
	Performs a safe floor-divide of two numbers
	If A and B is 0, returns NaN
	If B is 0, returns inf
	If A and B is inf, returns NaN
	If B is inf, returns 0
	:param a: First operand
	:param b: Second operand
	:return: The quotient
	"""

	a = float(a)
	b = float(b)
	inf: float = float('inf')
	return float('nan') if a == 0 and b == 0 or a == inf and b == inf else 0 if b == inf else inf if b == 0 else (a // b)


@Overload
def safe_divmod(a: float, b: float) -> tuple[float, float]:
	"""
	Performs a safe div-mod of two numbers
	If A and B is 0, returns NaN and NaN
	If B is 0, returns inf and 0
	If A and B is inf, returns NaN and NaN
	If B is inf, returns 0 and NaN
	:param a: First operand
	:param b: Second operand
	:return: The quotient and remainder
	"""

	a = float(a)
	b = float(b)
	inf: float = float('inf')
	nan: float = float('nan')
	return (nan, nan) if a == 0 and b == 0 or a == inf and b == inf else (0, nan) if b == inf else (inf, 0) if b == 0 else divmod(a, b)