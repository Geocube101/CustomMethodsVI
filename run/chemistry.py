from Chemistry.Atom import *
from Chemistry.Compound import *
from Chemistry.PeriodicTable import PTable

if __name__ == '__main__':
	PTable.unpack_into(globals())
	water: Compound = 2*H + O
	print(water.calc_mass_to_moles())
