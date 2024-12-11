from __future__ import annotations

import math


class CacheArchitecture:
	"""
	CacheArchitecture - Class for deducing cache architecture data
	"""

	class CacheMapper:
		def __init__(self, cache: CacheArchitecture, address: int):
			self.__cache__: CacheArchitecture = cache
			self.__address_mask__: int = (2 << self.__cache__.word_size) - 1
			self.__base_address__: int = int(address) & self.__address_mask__

		def is_same_set(self, address: int) -> bool:
			return self.__cache__.set_address_of(self.__base_address__) == self.__cache__.set_address_of(address & self.__address_mask__)

		def is_same_block(self, address: int) -> bool:
			return self.__cache__.block_offset_of(self.__base_address__) == self.__cache__.block_offset_of(address & self.__address_mask__)

		def is_same_location(self, address: int) -> bool:
			return self.is_same_set(address) & self.is_same_block(address)

	def __init__(self, capacity: int, block_size: int, associativity: int, word_size_bits: int):
		"""
		CacheArchitecture - Class for deducing cache architecture data
		- Constructor -
		:param capacity: (int) The capacity in bytes
		:param block_size: (int) The block size in bytes
		:param associativity: (int) The degree of associativity
		:param word_size_bits: (int) The word size in bits
		"""

		word_size_bytes: int = word_size_bits // 8

		self.__capacity__: int = int(capacity)
		self.__block_size__: int = int(block_size)
		self.__word_size_bits__: int = int(word_size_bits)
		self.__block_count__: int = self.__capacity__ // self.__block_size__
		self.__associativity__: int = int(self.__block_count__ if associativity <= 0 else associativity)
		self.__set_count__: int = self.__block_count__ // self.__associativity__
		self.__word_offset_size_bits__: int = int(math.log2(word_size_bits // 8))
		self.__block_offset_size_bits__: int = int(math.log2(self.__block_size__ / word_size_bytes))
		self.__tag_size_bits__: int = int(self.__word_size_bits__ - self.__word_offset_size_bits__ - self.__block_offset_size_bits__ - math.log2(self.__set_count__))
		self.__set_index_size_bits: int = int(math.log2(self.__set_count__))

	def set_address_of(self, true_address: int) -> int:
		cutoff: int = self.__block_offset_size_bits__ + self.__word_offset_size_bits__
		mask: int = (1 << self.__set_index_size_bits) - 1
		return (true_address >> cutoff) & mask

	def block_offset_of(self, true_address: int) -> int:
		mask: int = (1 << self.__block_offset_size_bits__) - 1
		return (true_address >> self.__word_offset_size_bits__) & mask

	def byte_offset_of(self, true_address: int) -> int:
		mask: int = (1 << self.__word_offset_size_bits__) - 1
		return true_address & mask

	def tag_value_of(self, true_address: int) -> int:
		cutoff: int = self.__word_size_bits__ - self.__tag_size_bits__
		mask: int = (1 << self.__tag_size_bits__) - 1
		return (true_address >> cutoff) & mask

	def mapper_for(self, true_address: int) -> CacheArchitecture.CacheMapper:
		return CacheArchitecture.CacheMapper(self, true_address)

	@property
	def capacity(self) -> int:
		return self.__capacity__

	@property
	def block_size(self) -> int:
		return self.__block_size__

	@property
	def degree_associativity(self) -> int:
		return self.__associativity__

	@property
	def block_count(self) -> int:
		return self.__block_count__

	@property
	def set_count(self) -> int:
		return self.__set_count__

	@property
	def set_index_size(self) -> int:
		"""
		:return: (int) The set index size of this cache in bits
		"""
		return self.__set_index_size_bits

	@property
	def block_offset_size(self) -> int:
		"""
		:return: (int) The block offset size of this cache in bits
		"""

		return self.__block_offset_size_bits__

	@property
	def tag_size(self) -> int:
		"""
		:return: (int) The tag size of this cache in bits
		"""

		return self.__tag_size_bits__

	@property
	def word_size(self) -> int:
		"""
		:return: (int) The size of a word in bits
		"""

		return self.__word_size_bits__

	@property
	def word_offset_size(self) -> int:
		"""
		:return: (int) The size of the word index offset in bits
		"""

		return self.__word_offset_size_bits__
