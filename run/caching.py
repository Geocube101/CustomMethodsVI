import sys

from CustomMethodsVI.CacheArch import CacheArchitecture


if __name__ == '__main__':
	try:
		cache_capacity: int = int(input('Cache Capacity (positive bytes): '))
		block_size: int = int(input('Block Size (positive bytes): '))
		associativity: int = int(input('Degree Associativity (positive): '))
		word_size: int = int(input('Word Size (positive bits multiple_of_8): '))

		assert cache_capacity > 0, 'Negative or zero cache capacity'
		assert block_size > 0, 'Negative or zero block size'
		assert associativity > 0, 'Negative or zero degree of associativity'
		assert word_size > 0, 'Negative or zero word size'

		assert word_size % 8 == 0, 'Word size not a multiple of 8'
	except ValueError:
		input('One or more input values was not an integer-10 value')
		sys.exit(2)
	except AssertionError as err:
		input(f'One or more input values was not a valid value\n ... {str(err)}')
		sys.exit(2)

	cache: CacheArchitecture = CacheArchitecture(cache_capacity, block_size, associativity, word_size)

	print(f'Cache Variables:')
	print(' ... B:', cache.block_count)
	print(' ... N:', cache.degree_associativity)
	print(' ... S:', cache.set_count)
	print(' ... Set ID Size:', cache.set_index_size)
	print(' ... Block Offset Size:', cache.block_offset_size)
	print(' ... Tag Size:', cache.tag_size)
	print(' ... Word Offset Size:', cache.word_offset_size)
	print(' ... Cache Type:', 'Direct-Mapped' if cache.set_count == cache.block_count and cache.degree_associativity == 1 else 'Fully Mapped' if cache.set_count == 1 and cache.degree_associativity == cache.block_count else 'N-Way')

	print('\n\n[ Cache Mapper ]\n')

	input_str: str = ''

	while True:
		try:
			input_str = input('Enter Address to Compare Against: ').lower()

			if len(input_str) == 0:
				break

			target: int = int(input_str[2:], 16) if input_str.startswith('0x') else int(input_str[2:], 8) if input_str.startswith('0o') else int(input_str[2:], 2) if input_str.startswith('0b') else int(input_str)
			input_str = input('Enter Address to Test: ').lower()

			if len(input_str) == 0:
				break

			address: int = int(input_str[2:], 16) if input_str.startswith('0x') else int(input_str[2:], 8) if input_str.startswith('0o') else int(input_str[2:], 2) if input_str.startswith('0b') else int(input_str)

			mapper: CacheArchitecture.CacheMapper = cache.mapper_for(target)
			print(f'\nMapper For "{address}" (mapping {target}):')
			print(' ... Does Map Set:', mapper.is_same_set(address))
			print(' ... Does Map Block:', mapper.is_same_block(address))
			print(' ... Does Map Location:', mapper.is_same_location(address))

			print(f'\nBit Info For "{address}"')
			print(' ... Set Address:', cache.set_address_of(address), bin(cache.set_address_of(address)), hex(cache.set_address_of(address)))
			print(' ... Block Offset:', cache.block_offset_of(address), bin(cache.block_offset_of(address)), hex(cache.block_offset_of(address)))
			print(' ... Byte Offset:', cache.byte_offset_of(address), bin(cache.byte_offset_of(address)), hex(cache.byte_offset_of(address)))
			print(' ... Tag Value:', cache.tag_value_of(address), bin(cache.tag_value_of(address)), hex(cache.tag_value_of(address)))
		except ValueError:
			print(f'Invalid address: {input_str}')
