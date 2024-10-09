import CustomMethodsVI.Math.Matrix as Matrix


if __name__ == '__main__':
	ma = Matrix.Matrix.shaped(range(0, 9), 3, 3)
	mb = Matrix.Matrix.shaped(range(0, 6), 3, 2)
	mc = ma @ mb
	print(ma, mb, mc, mc.dimensions, mc.dimension, sep='\n')
