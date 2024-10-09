from __future__ import annotations

import typing

from CustomMethodsVI.Decorators import Overload


class SolvableTerm:
	@Overload
	def __init__(self, coefficient: int | float, exponent: int | float):
		assert isinstance(coefficient, (int, float))
		assert isinstance(exponent, (int, float))

		self.coefficient = coefficient
		self.exponent = exponent

	def __neg__(self) -> SolvableTerm:
		copy: SolvableTerm = self
		copy.coefficient = -copy.coefficient
		return copy

	def __repr__(self) -> str:
		return str(self)

	def is_negative(self) -> bool:
		return self.coefficient < 0

	def solve(self, **variables: int | float) -> int | float:
		raise NotImplementedError


class Number(SolvableTerm):
	@Overload
	def __init__(self, value: int | float | Number):
		super().__init__(1, 1)
		assert isinstance(value, (float, int, Number))
		self.value: int | float = value.value if type(value) is type(self) else value

	def __str__(self):
		return str(self.solve())

	@Overload
	def solve(self, **variables: int | float) -> int | float:
		return self.coefficient * self.value


class LetterTerm(SolvableTerm):
	@Overload
	def __init__(self, letter: str, coefficient: int | float = 1, exponent: int | float = 1):
		super().__init__(coefficient, exponent)

		assert type(letter) is str and len(letter) == 1, f'{type(self).__name__} \'letter\' must be a single character, got string of len {len(letter)}'
		assert letter.isprintable(), f'{type(self).__name__} \'letter\' must be printable'
		self.letter = letter[0]

	def __str__(self) -> str:
		superscript: str = '⁰¹²³⁴⁵⁶⁷⁸⁹˙'
		standard: str = '0123456789.'
		return f'{"" if self.coefficient == 1 else self.coefficient}{self.letter}{"" if self.exponent == 1 else "".join(superscript[standard.index(i)] for i in str(self.exponent))}'

	@Overload
	def __add__(self, other: LetterTerm) -> LetterTerm | AddedTerm:
		if other.letter == self.letter and self.exponent == other.exponent:
			return LetterTerm(self.letter, self.coefficient + other.coefficient, self.exponent)
		else:
			return AddedTerm((self, other), 1, 1)

	@Overload
	def __add__(self, other: 'int | float | CustomMethodsVI.Math.Algebra.Number') -> 'LetterTerm | AddedTerm':
		return AddedTerm((self, Number(other)), 1, 1)

	@Overload
	def __sub__(self, other: LetterTerm) -> LetterTerm | AddedTerm:
		if other.letter == self.letter and self.exponent == other.exponent:
			return LetterTerm(self.letter, self.coefficient - other.coefficient, self.exponent)
		else:
			return AddedTerm((self, -other), 1, 1)

	@Overload
	def __sub__(self, other: int | float | Number) -> LetterTerm | AddedTerm:
		return AddedTerm((self, -Number(other)), 1, 1)

	@Overload
	def solve(self, **variables: int | float) -> int | float:
		if self.letter not in variables:
			raise NameError(f'Variable for \'{self.letter}\' not supplied')
		elif not isinstance(variables[self.letter], (float, int)):
			raise TypeError(f'Value supplied for \'{self.letter}\' is not a float or int')
		else:
			return self.coefficient * variables[self.letter] ** self.exponent


class MultiTerm(SolvableTerm):
	@Overload
	def __init__(self, terms: typing.Iterable[SolvableTerm], coefficient: int | float = 1, exponent: int | float = 1):
		super().__init__(coefficient, exponent)
		self.terms: list[SolvableTerm] = list(terms)
		assert all(isinstance(x, SolvableTerm) or isinstance(x, SolvableTerm) for x in self.terms)

	@Overload
	def solve(self, **variables: int | float) -> int | float:
		raise NotImplementedError


class AddedTerm(MultiTerm):
	@Overload
	def __init__(self, terms: typing.Iterable[SolvableTerm], coefficient: int | float = 1, exponent: int | float = 1):
		super().__init__(terms, coefficient, exponent)

	def __str__(self) -> str:
		return f'{f"{self.coefficient}" if self.coefficient != 1 else ""}{"(" if self.coefficient != 1 or self.exponent != 1 else ""}{"".join(str(t) if t.is_negative() else f"+{t}" for t in self.terms).lstrip("+")}{")" if self.coefficient != 1 or self.exponent != 1 else ""}{f"{self.exponent}" if self.exponent != 1 else ""}'

	@Overload
	def solve(self, **variables: int | float) -> int | float:
		return self.coefficient * sum(x.solve(**variables) for x in self.terms) ** self.exponent
