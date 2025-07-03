from CustomMethodsVI.Math.Tensor import Tensor


if __name__ == '__main__':
	tensor: Tensor = Tensor.shaped((x + 1 for x in range(9)), 3, 3)
	print(tensor, tensor.inverted(), sep='\n')
