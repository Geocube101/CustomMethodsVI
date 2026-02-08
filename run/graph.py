from CustomMethodsVI.Graph import *


def graph():
	graph1 = UnweightedGraph()

	for i in range(10):
		if i > 0:
			graph1.add_node(f'A{i}', f'A{i - 1}')
		else:
			graph1.add_node(f'A{i}')

	graph1.print()
	print(graph1.has_bfs_connection('A0', 'A9'), graph1.has_dfs_connection('A0', 'A9'))
	print(graph1.has_bfs_connection('A9', 'A0'), graph1.has_dfs_connection('A9', 'A0'))

	graph2 = UnweightedDirectionalGraph()

	for i in range(10):
		if i > 0:
			graph2.add_node(f'A{i}', f'A{i - 1}')
		else:
			graph2.add_node(f'A{i}')

	graph2.print()
	print(graph2.has_bfs_connection('A0', 'A9'), graph2.has_dfs_connection('A0', 'A9'))
	print(graph2.has_bfs_connection('A9', 'A0'), graph2.has_dfs_connection('A9', 'A0'))


if __name__ == '__main__':
	graph()
