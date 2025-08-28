from __future__ import annotations

import typing

from .Math import Based


class AutomatonException(RuntimeError):
	pass


class InvalidLanguageSymbolException(AutomatonException):
	pass


class InvalidStateException(AutomatonException):
	pass


class AutomatonDeadlockedException(AutomatonException):
	pass


class MultipleStatesException(AutomatonException):
	pass


class FiniteAutomaton:
	"""
	Class representing a finite automata
	"""

	def __init__(self, states: typing.Iterable[str], language: typing.Iterable[typing.Any], start_state: str, accept_states: typing.Iterable[str], transformer: dict[str, dict[typing.Any, str | set[str]]], *, deterministic: bool = True):
		"""
		Class representing a finite automata
		- Constructor -
		:param states: The possible states this machine can be in
		:param language: The possible symbols this machine accepts as input
		:param start_state: The starting state this machine can be in (must be part of possible states)
		:param accept_states: The states this machine will accept as final states (must be part of possible states)
		:param transformer: The transformer function or mapping indicating the inputs to move from one state to the next
		:param deterministic: Whether this machine is deterministic (one state per symbol)
		:raises AssertionError: If one or more argument types do not match
		"""

		assert hasattr(states, '__iter__'), 'States must be an iterable'
		assert hasattr(language, '__iter__'), 'Language must be an iterable'
		assert hasattr(accept_states, '__iter__'), 'Accepted states must be an iterable'

		self.__states__ = set(str(x) for x in states)
		self.__language__: set[typing.Any] = set(language)
		self.__start_state__: str = str(start_state)
		self.__state__: typing.Optional[set[str]] = {self.__start_state__}
		self.__accepted_states__: set[str] = set(accept_states)
		self.__transformer_callable__: bool = False
		self.__deterministic__: bool = bool(deterministic)
		self.__transformer__: typing.Callable[[str, typing.Any], str | set[str]] | dict[str, dict[typing.Any, str | set[str]]] = transformer

		assert self.__start_state__ in self.__states__, 'Start state does not exist'
		assert len(self.__accepted_states__.difference(self.__states__)) == 0, 'One or more accepted states does not exist'

	def reset(self) -> None:
		"""
		Resets this machine to its starting state
		"""

		self.__state__ = {self.__start_state__}

	def move(self, symbol: typing.Any) -> None:
		"""
		Moves this machine once to any applicable states given the input symbol
		:param symbol: The input symbol
		"""

		if symbol not in self.__language__:
			raise InvalidLanguageSymbolException(f'Specified symbol "{symbol}" is not part of this automaton\'s language')
		elif self.__state__ is None:
			return

		result_states: set[str] = set()

		for state in self.__state__:
			possible_states: set[str]

			if state not in self.__transformer__:
				continue
			else:
				possibilities: dict[typing.Any, str | set[str]] = self.__transformer__[state]

				if symbol in possibilities:
					new_state: str | set[str] = possibilities[symbol]

					if isinstance(new_state, str):
						result_states.add(new_state)
					else:
						result_states.update(set(new_state))

		if len(result_states) == 0 and self.__deterministic__:
			raise AutomatonDeadlockedException('Deterministic automata is deadlocked')
		elif len(result_states) == 0:
			self.__state__ = None
		elif self.__deterministic__ and len(result_states) > 1:
			raise MultipleStatesException('Transition function returned multiple possible states for deterministic automaton')
		elif any((invalid := x) not in self.__states__ for x in result_states):
			raise InvalidStateException(f'Specified result state(s) "{invalid}" is not a state of this automaton')
		else:
			self.__state__ = result_states

	def check_accepted(self, input_: typing.Iterable[typing.Any]) -> bool:
		"""
		Checks whether the given sequence of inputs is accepted by this machine
		:param input_: The input sequence
		:return: Whether one ending state is final
		"""

		for symbol in input_:
			self.move(symbol)

		return self.accepted

	def generate_strings(self, max_length: int) -> set[str]:
		"""
		Generates string up to max length that are accepted by this machine
		:param max_length: The maximum length to generate string to
		:return: A set of accepted strings
		"""

		strings: set[str] = set()
		converter: Based.BaseN = Based.BaseN(len(self.__language__))
		language: tuple[str, ...] = tuple(sorted(self.__language__))

		for i in range(1, max_length + 1):
			for j in range(converter.base ** i):
				number: Based.BaseNumber = converter.convert(j)
				digits: list[int] = list(number.digits)

				while len(digits) < i:
					digits.insert(0, 0)

				strings.add(''.join(language[x] for x in digits))

		return strings

	def incoming_edges(self, state: str) -> set[tuple[str, typing.Any]]:
		"""
		:param state: The state to check
		:return: A set of tuples containing the sending state and symbol that lead into this state
		"""

		incoming: set[tuple[str, typing.Any]] = set()

		if state == self.__start_state__:
			incoming.add(...)

		for tstate, target in self.__transformer__.items():
			for symbol, next_states in target.items():
				if state == next_states or state in next_states:
					incoming.add((tstate, symbol))

		return incoming

	def clone(self) -> FiniteAutomaton:
		"""
		:return: A copy of this machine
		"""

		copy: FiniteAutomaton = FiniteAutomaton(self.__states__, self.__language__, self.__start_state__, self.__accepted_states__, self.__transformer__, deterministic=self.__deterministic__)
		copy.__state__ = self.__state__
		return copy

	def to_deterministic(self) -> FiniteAutomaton:
		raise NotImplementedError()

	def to_regular_expression(self) -> str:
		incoming_edges: dict[str, set[tuple[str, typing.Any]]] = {state: self.incoming_edges(state) for state in self.__states__}
		print(incoming_edges)

	@property
	def accepted(self) -> bool:
		"""
		:return: Whether this machine is in an accepted state
		"""

		return False if self.__state__ is None else len(self.__state__.intersection(self.__accepted_states__)) > 0

	@property
	def state(self) -> typing.Optional[str | set[str]]:
		"""
		:return: The current state(s) or None if machine is at phi
		"""

		return None if self.__state__ is None else next(iter(self.__state__)) if self.__deterministic__ else set(self.__states__)

	@property
	def accepted_states(self) -> set[str]:
		"""
		:return: The set of accepted states
		"""

		return set(self.__accepted_states__)

	@property
	def active_paths(self) -> int:
		"""
		:return: The number of active paths
		"""

		return 0 if self.__state__ is None else len(self.__state__)


StateMachine = FiniteAutomaton
