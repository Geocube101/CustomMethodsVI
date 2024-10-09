from CustomMethodsVI.Decorators import Overload, DefaultOverload


@Overload(strict=False)
def func(b: float, a: float) -> float:
	print(a, type(a))
	print(b, type(b))
	return a + b


if __name__ == '__main__':
	print(func(1, 2))
