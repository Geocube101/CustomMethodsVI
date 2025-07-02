import typing

class Grammar:
	class ProductionRule:
		def __init__(self, nonterminals: set[str], src: str, yeilds: set[str | None | tuple[str | None, ...]]):
			self.__nonterminal__: str = str(src)
			self.__yeilds__: set[tuple[str | None, ...]] = set((None if s is None else str(s),) if isinstance(s, str) else tuple(None if x is None else str(x) for x in s) for s in yeilds)
			assert self.__nonterminal__ in nonterminals, 'Production rule source is terminal'

	def __init__(self, nonterminals: set[str], terminals: set[str], start: str, productions: dict[str, set[str | None | tuple[str | None, ...]]]):
		self.__nonterminals__: set[str] = set(str(s) for s in nonterminals)
		self.__terminals__: set[str] = set(str(s) for s in terminals)
		self.__start__: str = str(start)
		self.__productions__: dict[str, Grammar.ProductionRule] = {str(s): Grammar.ProductionRule(self.__nonterminals__, s, y) for s, y in productions.items()}
		assert len(self.__nonterminals__.intersection(self.__terminals__)) == 0, 'Nonterminals intersects terminals'
		assert self.__start__ in self.__nonterminals__, 'Start is not in nonterminals'

	def __contains__(self, string: tuple[str, ...]) -> bool:
		pass

	def produce(self, path: typing.Iterable[str]) -> str:
		for p in path:
			pass
