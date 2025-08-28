import CustomMethodsVI.Encryption as Encryption


if __name__ == '__main__':
	tensor1: Encryption.Tensor.Tensor = Encryption.Tensor.Tensor.identity(3, 3, 3)
	tensor2: Encryption.Tensor.Tensor = Encryption.Tensor.Tensor.shaped(range(3**3), 3, 3, 3)
	matrix1: Encryption.TensorEncryption = Encryption.TensorEncryption(tensor1)
	matrix2: Encryption.TensorEncryption = Encryption.TensorEncryption(tensor2)
	enc: bytes = matrix2.encrypt(b'Hello World')
	print(enc)
	dec: bytes = matrix2.decrypt(enc)
	print(dec)