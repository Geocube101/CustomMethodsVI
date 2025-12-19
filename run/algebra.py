import cmath
import sys

import CustomMethodsVI.Math.Algebra as Algebra


if __name__ == '__main__':
	eq = Algebra.parse('limit(sqrt(x), x->INF)')
	print(eq, type(eq), eq.solve(x=25))
