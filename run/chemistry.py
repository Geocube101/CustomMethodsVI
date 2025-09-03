from CustomMethodsVI.Chemistry.Elements import *
from CustomMethodsVI.Chemistry.Compound import *
from CustomMethodsVI.Chemistry.Equation import *

if __name__ == '__main__':
	water: Compound = 2*H+O
	eq: Equation = Equation((EquationCompound(water, 'l', 2), Heat), (EquationCompound(2 * water, 'g'),), reversible=True)
	print(eq, eq.is_balanced(), sep='\n')
