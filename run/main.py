from CustomMethodsVI.Network.Functions import *


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


def is_prime(x: int) -> bool:
	if x < 2:
		return False

	sqrt: int = int(x ** 0.5)

	for i in range(2, sqrt + 1):
		if x % i == 0:
			return False

	return True


def factors(x: int) -> tuple[tuple[int, int], ...]:
	facs: list[tuple[int, int]] = []

	for i in range((x // 2) + 1):
		facs.append((i, x - i))

	return tuple(facs)


def prime_factors(x: int) -> tuple[tuple[int, int], ...]:
	return tuple((i, j) for i, j in factors(x) if is_prime(i) and is_prime(j))


def main():
	print(baudrate_noise(1e15, 48, 0))
	return

	maxint: int = 0xFFF

	for i in range(2, maxint, 2):
		primes: tuple[tuple[int, int], ...] = prime_factors(i)
		j: int = len(primes)
		print(f'{str(i).zfill(4)}: {str(j).zfill(4)}')


if __name__ == '__main__':
	main()
