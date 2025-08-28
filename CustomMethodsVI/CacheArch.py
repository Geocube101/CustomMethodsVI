from __future__ import annotations

import math


class CacheArchitecture:
	"""
	Class for deducing cache architecture data
	"""

	class CacheMapper:
		"""
		Class for operations on a single cache address
		"""

		def __init__(self, cache: CacheArchitecture, address: int):
			"""
			Class for operations on a single cache address
			- Constructor -
			:param cache: The cache architecture
			:param address: The cache address
			:raises AssertionError: If 'cache' is not an instance of 'CacheArchitecture'
			"""

			assert isinstance(cache, CacheArchitecture), 'Not a cache architecture'

			self.__cache__: CacheArchitecture = cache
			self.__address_mask__: int = (2 << self.__cache__.word_size) - 1
			self.__base_address__: int = int(address) & self.__address_mask__

		def is_same_set(self, address: int) -> bool:
			"""
			:param address: The full cache address
			:return: Whether these addresses have the same set address
			"""

			return self.__cache__.set_address_of(self.__base_address__) == self.__cache__.set_address_of(address & self.__address_mask__)

		def is_same_block(self, address: int) -> bool:
			"""
			:param address: The full cache address
			:return: Whether these addresses have the same block
			"""
			return self.__cache__.block_offset_of(self.__base_address__) == self.__cache__.block_offset_of(address & self.__address_mask__)

		def is_same_location(self, address: int) -> bool:
			"""
			:param address: The full cache address
			:return: Whether these addresses have the same location (same set and same block)
			"""
			return self.is_same_set(address) & self.is_same_block(address)

		@property
		def set_address(self) -> int:
			"""
			:return: The set address of this address
			"""

			return self.__cache__.set_address_of(self.__base_address__)

		@property
		def block_offset(self) -> int:
			"""
			:return: The block offset of this address
			"""
			return self.__cache__.block_offset_of(self.__base_address__)

		@property
		def byte_offset(self) -> int:
			"""
			:return: The byte offset of this address
			"""
			return self.__cache__.byte_offset_of(self.__base_address__)

		@property
		def tag(self) -> int:
			"""
			:return: The tag of this address
			"""
			return self.__cache__.tag_value_of(self.__base_address__)

	def __init__(self, capacity: int, block_size: int, associativity: int, word_size_bits: int):
		"""
		Class for deducing cache architecture data
		- Constructor -
		:param capacity: The capacity in bytes
		:param block_size: The block size in bytes
		:param associativity: The degree of associativity
		:param word_size_bits: The word size in bits
		:raises AssertionError: If any value is not an integer
		"""

		assert isinstance(capacity, int) and (capacity := int(capacity)) >= 0, 'Invalid capacity'
		assert isinstance(block_size, int) and (block_size := int(block_size)) >= 0, 'Invalid block size'
		assert isinstance(associativity, int), 'Invalid associativity'
		assert isinstance(word_size_bits, int) and (word_size_bits := int(word_size_bits)) >= 0, 'Invalid word_size_bits'

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
		"""
		:param true_address: The full cache address
		:return: The set address
		"""

		cutoff: int = self.__block_offset_size_bits__ + self.__word_offset_size_bits__
		mask: int = (1 << self.__set_index_size_bits) - 1
		return (true_address >> cutoff) & mask

	def block_offset_of(self, true_address: int) -> int:
		"""
		:param true_address: The full cache address
		:return: The block offset
		"""

		mask: int = (1 << self.__block_offset_size_bits__) - 1
		return (true_address >> self.__word_offset_size_bits__) & mask

	def byte_offset_of(self, true_address: int) -> int:
		"""
		:param true_address: The full cache address
		:return: The byte offset
		"""
		mask: int = (1 << self.__word_offset_size_bits__) - 1
		return true_address & mask

	def tag_value_of(self, true_address: int) -> int:
		"""
		:param true_address: The full cache address
		:return: The tag value
		"""
		cutoff: int = self.__word_size_bits__ - self.__tag_size_bits__
		mask: int = (1 << self.__tag_size_bits__) - 1
		return (true_address >> cutoff) & mask

	def mapper_for(self, true_address: int) -> CacheArchitecture.CacheMapper:
		"""
		:param true_address: The full cache address
		:return: A mapper allowing operations on said address
		"""

		return CacheArchitecture.CacheMapper(self, true_address)

	@property
	def capacity(self) -> int:
		"""
		:return: This cache's capacity in bytes
		"""

		return self.__capacity__

	@property
	def block_size(self) -> int:
		"""
		:return: This cache's block size in bytes
		"""

		return self.__block_size__

	@property
	def degree_associativity(self) -> int:
		"""
		:return: The degree of associativity
		"""

		return self.__associativity__

	@property
	def block_count(self) -> int:
		"""
		:return: The number of blocks this cache has
		"""

		return self.__block_count__

	@property
	def set_count(self) -> int:
		"""
		:return: The number of sets this cache has
		"""

		return self.__set_count__

	@property
	def set_index_size(self) -> int:
		"""
		:return: The set index size of this cache in bits
		"""

		return self.__set_index_size_bits

	@property
	def block_offset_size(self) -> int:
		"""
		:return: The block offset size of this cache in bits
		"""

		return self.__block_offset_size_bits__

	@property
	def tag_size(self) -> int:
		"""
		:return: The tag size of this cache in bits
		"""

		return self.__tag_size_bits__

	@property
	def word_size(self) -> int:
		"""
		:return: The size of a word in bits
		"""

		return self.__word_size_bits__

	@property
	def word_offset_size(self) -> int:
		"""
		:return: The size of the word index offset in bits
		"""

		return self.__word_offset_size_bits__
