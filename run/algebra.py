import cmath
import sys

import CustomMethodsVI.Math.Algebra as Algebra


if __name__ == '__main__':
	num1 = Algebra.SingleTerm(5, 4, 'x')
	num2 = Algebra.SingleTerm(10, 4, 'x')
	num = num1 + num2
	print(num, num.simplify(), -num, num.solve(x=1), sep='\n')