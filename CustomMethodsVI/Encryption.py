import math
import struct

from . import Exceptions
from . import Decorators
from . import Misc
from .Math import Tensor

class TensorEncryption:
	"""
	Class using N-rank tensors to encrypt data
	"""

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
		"""
		Class using N-rank tensors to encrypt data
		- Constructor -
		:param tensor: The tensor to encrypt with
		:raises InvalidArgumentException: If 'tensor' is not a Tensor instance
		"""

		Misc.raise_ifn(isinstance(tensor, Tensor.Tensor), Exceptions.InvalidArgumentException(TensorEncryption.__init__, 'tensor', type(tensor), (Tensor.Tensor,)))
		data: list[float] = []

		for cell in tensor.flattened():
			if cell is None:
				raise ValueError('Empty cell in tensor')

			a, b = divmod(cell, TensorEncryption.__HIGHEST_OPERATION)
			data.append((b + 1) if a % 2 == 0 else -(b + 1))

		self.__tensor__: Tensor.Tensor = Tensor.Tensor.shaped(data, *tensor.dimensions)

	def encrypt(self, data: bytes | bytearray) -> bytes:
		"""
		Encrypts binary data
		:param data: The data to encrypt
		:return: The encrypted binary data
		:raises InvalidArgumentException: If 'data' is not a bytes object or bytearray
		:raises ValueError: If the supplied tensor cannot be used to encrypt the specified data
		"""

		Misc.raise_ifn(isinstance(data, (bytes, bytearray)), Exceptions.InvalidArgumentException(TensorEncryption.encrypt, 'data', type(data), (bytes, bytearray)))
		padding: int = len(self.__tensor__) - len(data)
		operand: tuple[int, ...] = (*data, *[0 for _ in range(max(0, padding))])

		if len(operand) > len(self.__tensor__):
			raise ValueError(f'Supplied {"x".join(str(x) for x in self.__tensor__.dimensions)} is insufficient for {len(data)} bytes')

		operations: Tensor.Tensor = self.__tensor__
		matrix: Tensor.Tensor = Tensor.Tensor.shaped(operand, *self.__tensor__.dimensions)

		for operation in self.__tensor__.flattened():
			if operation == TensorEncryption.__OPERATION_TRANSPOSE:
				matrix = matrix.transposed()
				operations = operations.transposed()
			elif operation == TensorEncryption.__OPERATION_ADD:
				matrix += operations
			elif operation == TensorEncryption.__OPERATION_SUB:
				matrix -= operations
			elif TensorEncryption.__OPERATION_MUL:
				matrix *= operations
			elif TensorEncryption.__OPERATION_MATRIX_MUL:
				#matrix @= operations
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
		"""
		Decrypts binary data
		:param data: The data to decrypt
		:return: The decrypted binary data
		:raises InvalidArgumentException: If 'data' is not a bytes object or bytearray
		"""

		Misc.raise_ifn(isinstance(data, (bytes, bytearray)), Exceptions.InvalidArgumentException(TensorEncryption.encrypt, 'data', type(data), (bytes, bytearray)))
		data: bytes = bytes(data)
		padding = int.from_bytes(data[:8], 'little')
		operations: Tensor.Tensor = self.__tensor__
		matrix: Tensor.Tensor = Tensor.Tensor.shaped((struct.unpack('<d', data[i * 8 + 8:i * 8 + 16])[0] for i in range(len(operations))), *operations.dimensions)

		for operation in reversed(self.__tensor__.flattened()):
			if operation == TensorEncryption.__OPERATION_TRANSPOSE:
				matrix = matrix.transposed()
				operations = operations.transposed()
			elif operation == TensorEncryption.__OPERATION_ADD:
				matrix -= operations
			elif operation == TensorEncryption.__OPERATION_SUB:
				matrix += operations
			elif TensorEncryption.__OPERATION_MUL:
				matrix /= operations
			elif TensorEncryption.__OPERATION_MATRIX_MUL:
				# matrix @= operations
				pass
			elif TensorEncryption.__OPERATION_DIV:
				matrix *= operations
			elif TensorEncryption.__OPERATION_POW:
				matrix **= 1 / operations
			elif TensorEncryption.__OPERATION_INVERT:
				matrix = -matrix

		data: bytes = bytes(int(x) % 256 for x in matrix.flattened()[:-padding] if not math.isinf(x))
		return data

