import typing


class Graph:
	class Node:
		def __init__(self, index: int, neighbours: 'typing.Iterable[Graph.Node]', source: 'Graph'):
			assert type(index) is int, f'Index must be an int, got: {type(index)}'
			assert type(index) is int, f'Index must be an int, got: {type(index)}'
			assert type(source) is Graph, f'Source must be a graph, got: {type(source)}'

			self.__index = int(index)
			self.__neighbours: list[Graph.Node] = list(neighbours)
			self.__source: Graph = source

		def __str__(self) -> str:
			return f'Node[{self.__index}]'

		def __add_neighbours__(self, *neighbours):
			assert all(type(n) is Graph.Node for n in neighbours), 'One or more values are not a Graph.Node'
			self.__neighbours.extend(neighbours)

			for neighbour in neighbours:
				neighbour.__neighbours.append(self)

		def get_edges(self) -> 'tuple[tuple[Graph.Node, Graph.Node], ...]':
			return tuple((self, neighbour) for neighbour in self.__neighbours)

	def __init__(self):
		self.__nodes: dict[int, Graph.Node] = {}

	def __getitem__(self, item: int) -> 'Graph.Node':
		assert item in self.__nodes, 'Node not in graph'
		return self.__nodes[item]
