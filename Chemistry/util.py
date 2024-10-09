def convert_int_to_subscript_str(number: int) -> str:
	charmap = ('₀', '₁', '₂', '₃', '₄', '₅', '₆', '₇', '₈', '₉')
	output = '₋' if number < 0 else ''
	buffer = []
	number = abs(number)

	while number > 0:
		buffer.append(charmap[number % 10])
		number //= 10

	return output + ''.join(reversed(buffer))
