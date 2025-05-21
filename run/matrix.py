import CustomMethodsVI.Math.Matrix as Matrix


if __name__ == '__main__':
	ma = Matrix.Matrix.shaped(range(0, 8), 2, 2, 2)
	mb = Matrix.Matrix.shaped(range(8, 16), 2, 2, 2)
	mc = ma @ mb
	print(ma, mb, mc, mc.dimensions, mc.dimension, sep='\n')
