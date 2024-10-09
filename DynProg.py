import typing
import numpy


def bounded_knapsack(capacity: int, weights: typing.Iterable[int], values: typing.Iterable[int]) -> numpy.ndarray:
	"""
	Handles a dynamic programming bounded knapsack
	:param capacity: (int) Knapsack total capacity
	:param weights: (ITERABLE[int]) Weights of items
	:param values: (ITERABLE[int]) Values of items
	:return: (numpy.ndarray) The total knapsack matrix
	"""

	matrix = numpy.full((capacity + 1, len(weights) + 1), 0, dtype=float)

	for x in range(1, capacity + 1):
		for j in range(1, len(weights) + 1):
			matrix[x, j] = matrix[x, j - 1]
			weight = weights[j - 1]
			value = values[j - 1]

			if weight <= x and (updated := matrix[x - weight, j - 1] + value) > matrix[x, j]:
				matrix[x, j] = updated

	return matrix


def unbounded_knapsack(capacity: int, weights: typing.Iterable[int], values: typing.Iterable[int]) -> set:
	"""
	Handles a dynamic programming unbounded knapsack
	:param capacity: (int) Knapsack target capacity
	:param weights: (ITERABLE[int]) Weights of items
	:param values: (ITERABLE[int]) Values of items
	:return: (numpy.ndarray) The total knapsack matrix
	"""

	K = [0] * (capacity + 1)
	items = [set() for _ in range(capacity + 1)]

	for x in range(1, capacity + 1):
		K[x] = 0

		for i in range(len(weights) - 1):
			wi = weights[i]
			vi = values[i]

			if wi <= x and (updated := K[x - wi] + vi) >= K[x]:
				K[x] = updated
				old = items[x - wi].copy()
				old.add(i)
				items[x] = old
	print(K)
	print(items)
	return items[capacity]
