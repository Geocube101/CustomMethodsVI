from __future__ import annotations

import typing
import multiprocessing

import CustomMethodsVI.Math.Based as Based


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
	def __init__(self, states: typing.Iterable[str], language: typing.Iterable[typing.Any], start_state: str, accept_states: typing.Iterable[str], transformer: dict[str, dict[typing.Any, str | set[str]]], *, deterministic: bool = True):
		self.__states__ = set(str(x) for x in states)
		self.__language__: set[typing.Any] = set(language)
		self.__start_state__: str = str(start_state)
		self.__state__: set[str] = {self.__start_state__}
		self.__accepted_states__: set[str] = set(accept_states)
		self.__transformer_callable__: bool = False
		self.__deterministic__: bool = bool(deterministic)
		self.__transformer__: typing.Callable[[str, typing.Any], str | set[str]] | dict[str, dict[typing.Any, str | set[str]]] = transformer

	def reset(self) -> None:
		self.__state__ = {self.__start_state__}

	def move(self, symbol: typing.Any) -> None:
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
		for symbol in input_:
			self.move(symbol)

		return self.accepted

	def generate_strings(self, max_length: int) -> set[str]:
		strings: set[str] = set()
		converter: Based.BaseN = Based.BaseN(len(self.__language__))
		language: tuple[str, ...] = tuple(sorted(self.__language__))

		for i in range(1, max_length + 1):
			for j in range(converter.base ** i):
				number: Based.BaseNumber = converter.convert(j)
				digits: list[int] = list(number.digits())

				while len(digits) < i:
					digits.insert(0, 0)

				strings.add(''.join(language[x] for x in digits))

		return strings

	def incoming_edges(self, state: str) -> set[tuple[str, typing.Any]]:
		incoming: set[tuple[str, typing.Any]] = set()

		if state == self.__start_state__:
			incoming.add(...)

		for tstate, target in self.__transformer__.items():
			for symbol, next_states in target.items():
				if state == next_states or state in next_states:
					incoming.add((tstate, symbol))

		return incoming

	def clone(self) -> FiniteAutomaton:
		copy: FiniteAutomaton = FiniteAutomaton(self.__states__, self.__language__, self.__start_state__, self.__accepted_states__, self.__transformer__, deterministic=self.__deterministic__)
		copy.__state__ = self.__state__
		return copy

	def to_deterministic(self) -> FiniteAutomaton:
		pass

	def to_regular_expression(self) -> str:
		incoming_edges: dict[str, set[tuple[str, typing.Any]]] = {state: self.incoming_edges(state) for state in self.__states__}
		print(incoming_edges)

	@property
	def accepted(self) -> bool:
		return False if self.__state__ is None and not self.__deterministic__ else len(self.__state__.intersection(self.__accepted_states__)) > 0

	@property
	def state(self) -> str | set[str]:
		return None if self.__state__ is None and not self.__deterministic__ else next(iter(self.__state__)) if self.__deterministic__ else set(self.__states__)

	@property
	def accepted_states(self) -> set[str]:
		return set(self.__accepted_states__)

	@property
	def active_paths(self) -> int:
		return 0 if self.__state__ is None and not self.__deterministic__ else len(self.__state__)


StateMachine = FiniteAutomaton
