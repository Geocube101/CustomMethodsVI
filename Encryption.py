import struct

import CustomMethodsVI.Math.Matrix
import CustomMethodsVI.Decorators


class MatrixEncryption:
	__OPERATION_TRANSPOSE: int = 0
	__OPERATION_ADD: int = 1
	__OPERATION_SUB: int = 2
	__OPERATION_MUL: int = 3
	__OPERATION_MATRIX_MUL: int = 4
	__OPERATION_DIV = 5
	__OPERATION_POW: int = 6
	__OPERATION_INVERT: int = 7
	__HIGHEST_OPERATION: int = 8

	@CustomMethodsVI.Decorators.Overload
	def __init__(self, matrix: CustomMethodsVI.Math.Matrix.Matrix):
		assert isinstance(matrix, CustomMethodsVI.Math.Matrix.Matrix), 'Supplied value is not a matrix'
		self.__matrix__: CustomMethodsVI.Math.Matrix.Matrix = matrix
		self.__operations__: CustomMethodsVI.Math.Matrix.Matrix = matrix % MatrixEncryption.__HIGHEST_OPERATION
		self.__extra_data__: CustomMethodsVI.Math.Matrix.Matrix = matrix // MatrixEncryption.__HIGHEST_OPERATION * MatrixEncryption.__HIGHEST_OPERATION

	def encrypt(self, data: bytes | bytearray) -> bytes:
		padding: int = len(self.__operations__) - len(data)
		operand: tuple[int, ...] = (*data, *[0 for _ in range(max(0, padding))])

		if len(operand) > len(self.__operations__):
			raise ValueError(f'Supplied {"x".join(str(x) for x in self.__matrix__.dimensions)} is insufficient for {len(data)} bytes')

		operations: CustomMethodsVI.Math.Matrix.Matrix = self.__operations__
		matrix: CustomMethodsVI.Math.Matrix.Matrix = CustomMethodsVI.Math.Matrix.Matrix.shaped(operand, *self.__matrix__.dimensions)

		for i, operation in enumerate(self.__operations__.flattened()):
			if operation == MatrixEncryption.__OPERATION_TRANSPOSE:
				matrix = matrix.transpose()
				operations = operations.transpose()
			elif operation == MatrixEncryption.__OPERATION_ADD:
				matrix += operations
			elif operation == MatrixEncryption.__OPERATION_SUB:
				matrix -= operations
			elif MatrixEncryption.__OPERATION_MUL:
				# matrix *= operations
				pass
			elif MatrixEncryption.__OPERATION_MATRIX_MUL:
				# matrix @= operations
				pass
			elif MatrixEncryption.__OPERATION_DIV:
				# matrix /= operations
				pass
			elif MatrixEncryption.__OPERATION_POW:
				matrix **= operations
			elif MatrixEncryption.__OPERATION_INVERT:
				matrix = -matrix

		return padding.to_bytes(8, 'little') + b''.join(struct.pack('<d', x) for x in matrix.flattened())

	def decrypt(self, data: bytes | bytearray) -> bytes:
		data: bytes = bytes(data)
		padding = int.from_bytes(data[:8], 'little')
		operations: CustomMethodsVI.Math.Matrix.Matrix = self.__operations__
		matrix: CustomMethodsVI.Math.Matrix.Matrix = CustomMethodsVI.Math.Matrix.Matrix.shaped((struct.unpack('<d', data[i * 8 + 8:i * 8 + 16])[0] for i in range(len(operations))), *operations.dimensions)

		for operation in self.__operations__.flattened():
			if operation == MatrixEncryption.__OPERATION_TRANSPOSE:
				operations = operations.transpose()

		for operation in self.__operations__.flattened():
			if operation == MatrixEncryption.__OPERATION_TRANSPOSE:
				matrix = matrix.transpose()
				operations = operations.transpose()
			elif operation == MatrixEncryption.__OPERATION_ADD:
				matrix -= operations
			elif operation == MatrixEncryption.__OPERATION_SUB:
				matrix += operations
			elif MatrixEncryption.__OPERATION_MUL:
				# matrix /= operations
				pass
			elif MatrixEncryption.__OPERATION_MATRIX_MUL:
				# matrix @= operations
				pass
			elif MatrixEncryption.__OPERATION_DIV:
				# matrix *= operations
				pass
			elif MatrixEncryption.__OPERATION_POW:
				matrix **= 1 / operations
			elif MatrixEncryption.__OPERATION_INVERT:
				matrix = -matrix

		data: bytes = bytes(int(x) for x in matrix.flattened()[:-padding])
		return data

