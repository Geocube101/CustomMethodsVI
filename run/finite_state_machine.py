import sys

import Automata


if __name__ == '__main__':
	fa: Automata.FiniteAutomaton = Automata.FiniteAutomaton({'A', 'B', 'C'}, '01', 'A', {'C'}, {
		'A': {'0': {'A'}, '1': {'A', 'B'}},
		'B': {'1': 'C'}
	}, deterministic=False)

	print(fa.to_regular_expression())
	sys.exit(0)

	strings: set[str] = fa.generate_strings(4)

	for string in strings:
		print(f'{string} -> {fa.check_accepted(string)}')
		fa.reset()