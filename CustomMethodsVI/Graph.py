from __future__ import annotations

import typing


from . import Exceptions
from . import Misc


class UnweightedGraph:
	class Node:
		def __init__(self, graph: UnweightedGraph, name: str, connections: typing.Optional[typing.Iterable[UnweightedGraph.Node]] = None):
			Misc.raise_ifn(isinstance(graph, UnweightedGraph), Exceptions.InvalidArgumentException(UnweightedGraph.Node.__init__, 'graph', type(graph), (UnweightedGraph,)))
			Misc.raise_ifn(isinstance(name, str), Exceptions.InvalidArgumentException(UnweightedGraph.Node.__init__, 'name', type(name), (str,)))
			Misc.raise_ifn(connections is None or connections is ... or hasattr(connections, '__iter__'), TypeError('Node connections list is not iterable'))
			self.__graph__: UnweightedGraph = graph
			self.__node__: str = str(name)
			self.__connections__: set[UnweightedGraph.Node] = set() if connections is None or connections is ... else set(connections)
			Misc.raise_ifn(all(isinstance(conn, UnweightedGraph.Node) for conn in self.__connections__), TypeError('One or more node connections is not a Node instance'))

		def __eq__(self, other: UnweightedGraph.Node) -> bool:
			return isinstance(other, UnweightedGraph.Node) and self.__graph__ == other.__graph__ and self.__node__ == other.__node__

		def __lt__(self, other: UnweightedGraph.Node) -> bool:
			return self.name < other.name if isinstance(other, UnweightedGraph.Node) else NotImplemented

		def __gt__(self, other: UnweightedGraph.Node) -> bool:
			return self.name < other.name if isinstance(other, UnweightedGraph.Node) else NotImplemented

		def __hash__(self) -> int:
			parent: int = hash(self.__graph__)
			child: int = hash(self.__node__)
			return (parent << child.bit_length()) | child

		def __repr__(self) -> str:
			return f'<UnweightedGraph.Node[{self.__node__}] instance @ {hex(id(self)).upper()}>'

		def remove_connection(self, node: UnweightedGraph.Node) -> None:
			self.__connections__.remove(node)

		def add_connection(self, node: UnweightedGraph.Node) -> None:
			Misc.raise_ifn(isinstance(node, UnweightedGraph.Node), Exceptions.InvalidArgumentException(UnweightedGraph.Node.add_connection, 'node', type(node), (UnweightedGraph.Node,)))
			Misc.raise_ifn(node.__graph__ == self.__graph__, ValueError('Node graph not shared'))
			self.__connections__.add(node)
			node.__connections__.add(self)

		def has_bfs_connection(self, node: UnweightedGraph.Node) -> bool:
			Misc.raise_ifn(isinstance(node, UnweightedGraph.Node), Exceptions.InvalidArgumentException(UnweightedGraph.Node.add_connection, 'node', type(node), (UnweightedGraph.Node,)))

			if node == self:
				return True
			elif node.__graph__ != self.__graph__:
				return False

			queue: list[UnweightedGraph.Node] = [self]
			visited: list[UnweightedGraph.Node] = []

			while len(queue) > 0:
				current: UnweightedGraph.Node = queue.pop(0)
				visited.append(current)

				if current == node:
					return True

				queue.extend(friend for friend in current.friends if friend not in visited)

			return False

		def has_dfs_connection(self, node: UnweightedGraph.Node) -> bool:
			Misc.raise_ifn(isinstance(node, UnweightedGraph.Node), Exceptions.InvalidArgumentException(UnweightedGraph.Node.add_connection, 'node', type(node), (UnweightedGraph.Node,)))

			if node == self:
				return True
			elif node.__graph__ != self.__graph__:
				return False

			queue: list[UnweightedGraph.Node] = [self]
			visited: list[UnweightedGraph.Node] = []

			while len(queue) > 0:
				current: UnweightedGraph.Node = queue.pop()
				visited.append(current)

				if current == node:
					return True

				queue.extend(friend for friend in current.friends if friend not in visited)

			return False

		@property
		def name(self) -> str:
			return self.__node__

		@property
		def graph(self) -> UnweightedGraph:
			return self.__graph__

		@property
		def friends(self) -> set[UnweightedGraph.Node]:
			return self.__connections__.copy()

	def __init__(self, nodes: typing.Optional[typing.Mapping[str, typing.Iterable[str]]] = ...):
		self.__graph__: set[UnweightedGraph.Node] = set()

		if isinstance(nodes, typing.Mapping):
			for name, connections in nodes.items():
				Misc.raise_ifn(hasattr(connections, '__iter__'), TypeError('Node connections list is not iterable'))
				Misc.raise_ifn(isinstance(name, str), TypeError('Node name is not a string'))
				friends: tuple[str, ...] = tuple(connections)
				Misc.raise_ifn(all(isinstance(conn, str) for conn in friends), TypeError('Connection is not a string'))
				node: UnweightedGraph.Node = UnweightedGraph.Node(self, name)
				self.__graph__.add(node)

				for conn in friends:
					friend: UnweightedGraph.Node = UnweightedGraph.Node(self, conn)
					self.__graph__.add(friend)
					node.add_connection(friend)
		elif nodes is not ... and nodes is not None:
			raise TypeError('Expected mapping of node names to node connections')

	def __eq__(self, other: UnweightedGraph) -> bool:
		return other is self

	def __contains__(self, node: str | UnweightedGraph.Node) -> bool:
		return node in self.__graph__ if isinstance(node, UnweightedGraph.Node) else any((node := str(node)) == x.name for x in self.__graph__) if isinstance(node, str) else False

	def __hash__(self) -> int:
		return id(self)

	def __iter__(self) -> typing.Iterator[UnweightedGraph.Node]:
		return iter(self.__graph__)

	def __getitem__(self, node: str | UnweightedGraph.Node) -> typing.Optional[UnweightedGraph.Node]:
		if isinstance(node, UnweightedGraph.Node):
			return node if node.graph == self else None
		elif isinstance(node, str):
			matched: tuple[UnweightedGraph.Node, ...] = tuple(x for x in self.__graph__ if x.name == str(node))
			return None if len(matched) == 0 else matched[0]
		else:
			raise TypeError('Graph indices must be a Node instance or a string')

	def print(self) -> None:
		print(self)

		for node in sorted(self):
			print(f'  | {node.name} --- {", ".join(child.name for child in sorted(node.friends))}')

	def has_bfs_connection(self, src: UnweightedGraph.Node | str, dst: UnweightedGraph.Node | str) -> bool:
		return self[src].has_bfs_connection(self[dst])

	def has_dfs_connection(self, src: UnweightedGraph.Node | str, dst: UnweightedGraph.Node | str) -> bool:
		return self[src].has_dfs_connection(self[dst])

	def add_node(self, name: str, *connections: str | UnweightedGraph.Node) -> UnweightedGraph.Node:
		Misc.raise_ifn(isinstance(name, str) and len(name := str(name)) > 0, TypeError('Graph node name must be a non-empty string'))
		Misc.raise_if(name in self, KeyError(f'A node with this name already exists: \'{name}\''))
		neighbors: list[UnweightedGraph.Node] = []

		for node in connections:
			target: UnweightedGraph.Node = self[node] if isinstance(node, str) else node

			if target is None:
				raise KeyError(f'No such node: \'{node}\'')
			elif not isinstance(target, UnweightedGraph.Node) or target.graph != self:
				raise TypeError(f'Node connections must be either a node or node name in this graph, got \'{type(node)}\'')

			neighbors.append(target)

		node: UnweightedGraph.Node = UnweightedGraph.Node(self, name, neighbors)
		self.__graph__.add(node)

		for friend in neighbors:
			friend.add_connection(node)

		return node

	@property
	def nodes(self) -> set[UnweightedGraph.Node]:
		return self.__graph__.copy()


class UnweightedDirectionalGraph:
	class Node:
		def __init__(self, graph: UnweightedDirectionalGraph, name: str, connections: typing.Optional[typing.Iterable[UnweightedDirectionalGraph.Node]] = None):
			Misc.raise_ifn(isinstance(graph, UnweightedDirectionalGraph), Exceptions.InvalidArgumentException(UnweightedDirectionalGraph.Node.__init__, 'graph', type(graph), (UnweightedDirectionalGraph,)))
			Misc.raise_ifn(isinstance(name, str), Exceptions.InvalidArgumentException(UnweightedDirectionalGraph.Node.__init__, 'name', type(name), (str,)))
			Misc.raise_ifn(connections is None or connections is ... or hasattr(connections, '__iter__'), TypeError('Node connections list is not iterable'))
			self.__graph__: UnweightedDirectionalGraph = graph
			self.__node__: str = str(name)
			self.__connections__: set[UnweightedDirectionalGraph.Node] = set() if connections is None or connections is ... else set(connections)
			Misc.raise_ifn(all(isinstance(conn, UnweightedDirectionalGraph.Node) for conn in self.__connections__), TypeError('One or more node connections is not a Node instance'))

		def __eq__(self, other: UnweightedDirectionalGraph.Node) -> bool:
			return isinstance(other, UnweightedDirectionalGraph.Node) and self.__graph__ == other.__graph__ and self.__node__ == other.__node__

		def __lt__(self, other: UnweightedDirectionalGraph.Node) -> bool:
			return self.name < other.name if isinstance(other, UnweightedDirectionalGraph.Node) else NotImplemented

		def __gt__(self, other: UnweightedDirectionalGraph.Node) -> bool:
			return self.name < other.name if isinstance(other, UnweightedDirectionalGraph.Node) else NotImplemented

		def __hash__(self) -> int:
			parent: int = hash(self.__graph__)
			child: int = hash(self.__node__)
			return (parent << child.bit_length()) | child

		def __repr__(self) -> str:
			return f'<UnweightedDirectionalGraph.Node[{self.__node__}] instance @ {hex(id(self)).upper()}>'

		def remove_connection(self, node: UnweightedDirectionalGraph.Node) -> None:
			self.__connections__.remove(node)

		def add_connection(self, node: UnweightedDirectionalGraph.Node, *, bidirectional: bool = False) -> None:
			Misc.raise_ifn(isinstance(node, UnweightedDirectionalGraph.Node), Exceptions.InvalidArgumentException(UnweightedDirectionalGraph.Node.add_connection, 'node', type(node), (UnweightedDirectionalGraph.Node,)))
			Misc.raise_ifn(node.__graph__ == self.__graph__, ValueError('Node graph not shared'))
			self.__connections__.add(node)

			if bidirectional:
				node.__connections__.add(self)

		def has_bfs_connection(self, node: UnweightedDirectionalGraph.Node) -> bool:
			Misc.raise_ifn(isinstance(node, UnweightedDirectionalGraph.Node), Exceptions.InvalidArgumentException(UnweightedDirectionalGraph.Node.add_connection, 'node', type(node), (UnweightedDirectionalGraph.Node,)))

			if node == self:
				return True
			elif node.__graph__ != self.__graph__:
				return False

			queue: list[UnweightedDirectionalGraph.Node] = [self]
			visited: list[UnweightedDirectionalGraph.Node] = []

			while len(queue) > 0:
				current: UnweightedDirectionalGraph.Node = queue.pop(0)
				visited.append(current)

				if current == node:
					return True

				queue.extend(friend for friend in current.friends if friend not in visited)

			return False

		def has_dfs_connection(self, node: UnweightedDirectionalGraph.Node) -> bool:
			Misc.raise_ifn(isinstance(node, UnweightedDirectionalGraph.Node), Exceptions.InvalidArgumentException(UnweightedDirectionalGraph.Node.add_connection, 'node', type(node), (UnweightedDirectionalGraph.Node,)))

			if node == self:
				return True
			elif node.__graph__ != self.__graph__:
				return False

			queue: list[UnweightedDirectionalGraph.Node] = [self]
			visited: list[UnweightedDirectionalGraph.Node] = []

			while len(queue) > 0:
				current: UnweightedDirectionalGraph.Node = queue.pop()
				visited.append(current)

				if current == node:
					return True

				queue.extend(friend for friend in current.friends if friend not in visited)

			return False

		@property
		def name(self) -> str:
			return self.__node__

		@property
		def graph(self) -> UnweightedDirectionalGraph:
			return self.__graph__

		@property
		def friends(self) -> set[UnweightedDirectionalGraph.Node]:
			return self.__connections__.copy()

	def __init__(self, nodes: typing.Optional[typing.Mapping[str, typing.Iterable[str]]] = ...):
		self.__graph__: set[UnweightedDirectionalGraph.Node] = set()

		if isinstance(nodes, typing.Mapping):
			for name, connections in nodes.items():
				Misc.raise_ifn(hasattr(connections, '__iter__'), TypeError('Node connections list is not iterable'))
				Misc.raise_ifn(isinstance(name, str), TypeError('Node name is not a string'))
				friends: tuple[str, ...] = tuple(connections)
				Misc.raise_ifn(all(isinstance(conn, str) for conn in friends), TypeError('Connection is not a string'))
				node: UnweightedDirectionalGraph.Node = UnweightedDirectionalGraph.Node(self, name)
				self.__graph__.add(node)

				for conn in friends:
					friend: UnweightedGraph.Node = UnweightedDirectionalGraph.Node(self, conn)
					self.__graph__.add(friend)
					node.add_connection(friend)
		elif nodes is not ... and nodes is not None:
			raise TypeError('Expected mapping of node names to node connections')

	def __eq__(self, other: UnweightedDirectionalGraph) -> bool:
		return other is self

	def __contains__(self, node: str | UnweightedDirectionalGraph.Node) -> bool:
		return node in self.__graph__ if isinstance(node, UnweightedDirectionalGraph.Node) else any((node := str(node)) == x.name for x in self.__graph__) if isinstance(node, str) else False

	def __hash__(self) -> int:
		return id(self)

	def __iter__(self) -> typing.Iterator[UnweightedDirectionalGraph.Node]:
		return iter(self.__graph__)

	def __getitem__(self, node: str | UnweightedDirectionalGraph.Node) -> typing.Optional[UnweightedDirectionalGraph.Node]:
		if isinstance(node, UnweightedDirectionalGraph.Node):
			return node if node.graph == self else None
		elif isinstance(node, str):
			matched: tuple[UnweightedDirectionalGraph.Node, ...] = tuple(x for x in self.__graph__ if x.name == str(node))
			return None if len(matched) == 0 else matched[0]
		else:
			raise TypeError('Graph indices must be a Node instance or a string')

	def print(self) -> None:
		print(self)

		for node in sorted(self):
			print(f'  | {node.name} ---> {", ".join(child.name for child in sorted(node.friends))}')

	def has_bfs_connection(self, src: UnweightedDirectionalGraph.Node | str, dst: UnweightedDirectionalGraph.Node | str) -> bool:
		return self[src].has_bfs_connection(self[dst])

	def has_dfs_connection(self, src: UnweightedDirectionalGraph.Node | str, dst: UnweightedDirectionalGraph.Node | str) -> bool:
		return self[src].has_dfs_connection(self[dst])

	def add_node(self, name: str, *connections: str | UnweightedDirectionalGraph.Node, bidirectional: bool = False) -> UnweightedDirectionalGraph.Node:
		Misc.raise_ifn(isinstance(name, str) and len(name := str(name)) > 0, TypeError('Graph node name must be a non-empty string'))
		Misc.raise_if(name in self, KeyError(f'A node with this name already exists: \'{name}\''))
		neighbors: list[UnweightedDirectionalGraph.Node] = []

		for node in connections:
			target: UnweightedDirectionalGraph.Node = self[node] if isinstance(node, str) else node

			if target is None:
				raise KeyError(f'No such node: \'{node}\'')
			elif not isinstance(target, UnweightedDirectionalGraph.Node) or target.graph != self:
				raise TypeError(f'Node connections must be either a node or node name in this graph, got \'{type(node)}\'')

			neighbors.append(target)

		node: UnweightedDirectionalGraph.Node = UnweightedDirectionalGraph.Node(self, name, neighbors)
		self.__graph__.add(node)

		if bidirectional:
			for friend in neighbors:
				friend.add_connection(node)

		return node

	@property
	def nodes(self) -> set[UnweightedDirectionalGraph.Node]:
		return self.__graph__.copy()
