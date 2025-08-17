import CustomMethodsVI.Stream as Stream


def steam():
	start: int = 5792
	end: int = 5872
	text: str = 'Yggdrasil - "I am Thaumiel, the high echelon elemental representing entropy!"'
	text = text.replace(' ', '-')
	length: int = len(text)
	modulo: int = 7
	print(length, length % modulo)
	result: str = ''

	for c in text:
		lower: int = 97 if c.islower() else 65 if c.isupper() else 33
		point: int = (ord(c) - lower) % (end - start) + start
		assert point <= end, f'OOB/{c} - {point} > {end}'
		result += chr(point)

	segments: list[str] = [' '.join(result[i:i + modulo]) for i in range(0, len(result), 7)]
	result: str = '\n'.join(segments)
	print(result)


def main():
	data1: str = 'Hello how are you?'
	data2: str = 'This is a string'
	stream: Stream.OrderedStream[int] = Stream.OrderedStream()
	stream.write(2.)


if __name__ == '__main__':
	main()
