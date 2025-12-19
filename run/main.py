import PIL.Image

from CustomMethodsVI.Code import PixelCode
from CustomMethodsVI.Stream import BitStream
from CustomMethodsVI.Graph import *
from PIL import Image
from CustomMethodsVI.Stream import LinqStream
from CustomMethodsVI.Iterable import *


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


def code():
	# pc = PixelCode(1)
	# code = pc.encode(b'Hello World')
	# print(pc.decode(code))
	ug = UnweightedGraph({
		'A': ('B', 'C', 'D'),
		'B': ('A',)
	})
	#print(ug.nodes, ug.has_bfs_connection('A', 'B'))

	a: list[int] = [1, 2, 3, 4, 5]
	b: set[int] = LinqStream(a).filter(lambda d: d >= 3).collect(set)
	print(b)


def main():
	src: String = String('World')
	dst: String = String()
	print(src, dst)
	res = src >> dst
	print(src, dst, res is dst)


if __name__ == '__main__':
	main()
