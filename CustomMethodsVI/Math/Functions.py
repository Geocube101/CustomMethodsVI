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
def safe_modulo(a: float, b: float) -> float:
	"""
	Performs a safe divide of two numbers
	If A and B is 0, returns NaN
	If B is 0, returns 0
	If A and B is inf, returns NaN
	If B is inf, returns inf
	:param a: First operand
	:param b: Second operand
	:return: The remainder
	"""

	a = float(a)
	b = float(b)
	inf: float = float('inf')
	return float('nan') if a == 0 and b == 0 or a == inf and b == inf else inf if b == inf else 0 if b == 0 else (a % b)


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

@Overload
def is_prime(x: int) -> bool:
	"""
	:param x: The number to check
	:return: Whether 'x' is prime
	"""

	if x < 2:
		return False

	sqrt: int = int(x ** 0.5)

	for i in range(2, sqrt + 1):
		if x % i == 0:
			return False

	return True


@Overload
def factors(x: int) -> tuple[tuple[int, int], ...]:
	"""
	:param x: The number to check
	:return: All non-repeating factors of 'x'
	"""

	facs: list[tuple[int, int]] = []

	for i in range((x // 2) + 1):
		facs.append((i, x - i))

	return tuple(facs)


@Overload
def prime_factors(x: int) -> tuple[tuple[int, int], ...]:
	"""
	:param x: The number to check
	:return: All non-repeating prime factors of 'x'
	"""

	return tuple((i, j) for i, j in factors(x) if is_prime(i) and is_prime(j))