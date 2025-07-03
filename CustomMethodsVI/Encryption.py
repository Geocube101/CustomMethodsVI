import math
import struct

from .Math import Tensor
from . import Decorators

class TensorEncryption:
	__OPERATION_TRANSPOSE: int = 0
	__OPERATION_ADD: int = 1
	__OPERATION_SUB: int = 2
	__OPERATION_MUL: int = 3
	__OPERATION_MATRIX_MUL: int = 4
	__OPERATION_DIV = 5
	__OPERATION_POW: int = 6
	__OPERATION_INVERT: int = 7
	__HIGHEST_OPERATION: int = 8

	@Decorators.Overload
	def __init__(self, tensor: Tensor.Tensor):
		assert isinstance(tensor, Tensor.Tensor), 'Supplied value is not a tensor'
		self.__tensor__: Tensor.Tensor = tensor
		self.__operations__: Tensor.Tensor = tensor % TensorEncryption.__HIGHEST_OPERATION
		self.__extra_data__: Tensor.Tensor = tensor // TensorEncryption.__HIGHEST_OPERATION * TensorEncryption.__HIGHEST_OPERATION

	def encrypt(self, data: bytes | bytearray) -> bytes:
		padding: int = len(self.__operations__) - len(data)
		operand: tuple[int, ...] = (*data, *[0 for _ in range(max(0, padding))])

		if len(operand) > len(self.__operations__):
			raise ValueError(f'Supplied {"x".join(str(x) for x in self.__tensor__.dimensions)} is insufficient for {len(data)} bytes')

		operations: Tensor.Tensor = self.__operations__
		matrix: Tensor.Tensor = Tensor.Tensor.shaped(operand, *self.__tensor__.dimensions)

		for i, operation in enumerate(self.__operations__.flattened()):
			if operation == TensorEncryption.__OPERATION_TRANSPOSE:
				matrix = matrix.transposed()
				operations = operations.transposed()
			elif operation == TensorEncryption.__OPERATION_ADD:
				matrix += operations
			elif operation == TensorEncryption.__OPERATION_SUB:
				matrix -= operations
			elif TensorEncryption.__OPERATION_MUL:
				matrix *= operations
				pass
			elif TensorEncryption.__OPERATION_MATRIX_MUL:
				matrix @= operations
				pass
			elif TensorEncryption.__OPERATION_DIV:
				matrix /= operations
				pass
			elif TensorEncryption.__OPERATION_POW:
				matrix **= operations
			elif TensorEncryption.__OPERATION_INVERT:
				matrix = -matrix

		return padding.to_bytes(8, 'little') + b''.join(struct.pack('<d', x) for x in matrix.flattened())

	def decrypt(self, data: bytes | bytearray) -> bytes:
		data: bytes = bytes(data)
		padding = int.from_bytes(data[:8], 'little')
		operations: Tensor.Tensor = self.__operations__
		matrix: Tensor.Tensor = Tensor.Tensor.shaped((struct.unpack('<d', data[i * 8 + 8:i * 8 + 16])[0] for i in range(len(operations))), *operations.dimensions)

		for operation in self.__operations__.flattened():
			if operation == TensorEncryption.__OPERATION_TRANSPOSE:
				operations = operations.transposed()

		for operation in self.__operations__.flattened():
			if operation == TensorEncryption.__OPERATION_TRANSPOSE:
				matrix = matrix.transposed()
				operations = operations.transposed()
			elif operation == TensorEncryption.__OPERATION_ADD:
				matrix -= operations
			elif operation == TensorEncryption.__OPERATION_SUB:
				matrix += operations
			elif TensorEncryption.__OPERATION_MUL:
				matrix /= operations
				pass
			elif TensorEncryption.__OPERATION_MATRIX_MUL:
				matrix @= operations.inverted()
				pass
			elif TensorEncryption.__OPERATION_DIV:
				matrix *= operations
				pass
			elif TensorEncryption.__OPERATION_POW:
				matrix **= 1 / operations
			elif TensorEncryption.__OPERATION_INVERT:
				matrix = -matrix

		data: bytes = bytes(int(x) for x in matrix.flattened()[:-padding] if not math.isinf(x))
		return data

