from __future__ import annotations

import copy
import math
import typing

class Expression:
	def __init__(self, coefficient: float | complex, exponent: float):
		self.__coefficient__: complex = complex(coefficient)
		self.__exponent__: float = float(exponent)

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return self.__wrapper_str__('')

	def __neg__(self) -> Expression:
		clone: Expression = copy.deepcopy(self)
		clone.__coefficient__ = -clone.__coefficient__
		return clone

	def __add__(self, other: Expression | float | int | complex) -> Expression | AddedTerm:
		if type(other) is type(self) is Expression and self.__exponent__ == other.__exponent__:
			return Expression(self.__coefficient__ + other.__coefficient__, self.__exponent__)
		elif isinstance(other, Expression):
			return AddedTerm(1, 1, self, other)
		elif isinstance(other, (float, int, complex)):
			return AddedTerm(1, 1, self, Expression(other, 1))
		else:
			return NotImplemented

	def __sub__(self, other: Expression | float | int | complex) -> Expression | AddedTerm:
		if type(other) is type(self) is Expression and self.__exponent__ == other.__exponent__:
			return Expression(self.__coefficient__ - other.__coefficient__, self.__exponent__)
		elif isinstance(other, Expression):
			return AddedTerm(1, 1, self, -other)
		elif isinstance(other, (float, int, complex)):
			return AddedTerm(1, 1, self, Expression(-other, 1))
		else:
			return NotImplemented

	def __radd__(self, other: Expression | float | int | complex) -> Expression | AddedTerm:
		if type(other) is type(self) is Expression and self.__exponent__ == other.__exponent__:
			return Expression(other.__coefficient__ + self.__coefficient__, self.__exponent__)
		elif isinstance(other, Expression):
			return AddedTerm(1, 1, other, self)
		elif isinstance(other, (float, int, complex)):
			return AddedTerm(1, 1, Expression(other, 1), self)
		else:
			return NotImplemented

	def __rsub__(self, other: Expression | float | int | complex) -> Expression | AddedTerm:
		if type(other) is type(self) is Expression and self.__exponent__ == other.__exponent__:
			return Expression(other.__coefficient__ - self.__coefficient__, self.__exponent__)
		elif isinstance(other, Expression):
			return AddedTerm(1, 1, other, -self)
		elif isinstance(other, (float, int, complex)):
			return AddedTerm(1, 1, Expression(other, 1), -self)
		else:
			return NotImplemented

	def __real_str__(self) -> str:
		return '' if self.__coefficient__.real == 1 else '-' if self.__coefficient__.real == -1 else f'{int(self.__coefficient__.real) if self.__coefficient__.real == int(self.__coefficient__.real) else self.__coefficient__.real}'

	def __exponent_str__(self) -> str:
		return '' if self.__exponent__ == 1 else f'^{int(self.__exponent__) if self.__exponent__ == int(self.__exponent__) else self.__exponent__}'

	def __imaginary_str__(self) -> str:
		return f'{int(self.__coefficient__.imag) if self.__coefficient__.imag == int(self.__coefficient__.imag) else self.__coefficient__.imag}'

	def __wrapper_str__(self, middle: typing.Any) -> str:
		imag: str = self.__imaginary_str__()
		real: str = self.__real_str__()
		exp: str = self.__exponent_str__()
		mid: str = str(middle)

		if len(mid) == 0:
			return f'{real}{exp}' if self.__coefficient__.imag == 0 else f'({real}+{imag}i){exp}'
		else:
			return f'({real}{mid}){exp}' if self.__coefficient__.imag == 0 else f'(({real}+{imag}i){mid}){exp}'

	def solve(self, **kwargs) -> complex:
		return self.__coefficient__ ** self.__exponent__

	def simplify(self) -> Expression:
		return copy.deepcopy(self)

	@property
	def negative(self) -> bool:
		return self.__coefficient__.real < 0

	@property
	def coefficient(self) -> complex:
		return self.__coefficient__

	@property
	def exponent(self) -> float:
		return self.__exponent__

class InverseTerm(Expression):
	def __init__(self, coefficient: float | complex, exponent: float, expression: Expression):
		super().__init__(coefficient, exponent)
		self.__expression__: Expression = expression

	def __str__(self) -> str:
		imag: str = self.__imaginary_str__()
		real: str = self.__real_str__()
		exp: str = self.__exponent_str__()
		return f'({real}/{self.__expression__}){exp}' if self.__coefficient__.imag == 0 else f'(({real}+{imag}i)/({self.__expression__})){exp}'

	def solve(self, **kwargs) -> complex:
		result: complex = self.__expression__.solve(**kwargs)
		return float('inf') if result == 0 else (self.__coefficient__ / result) ** self.__exponent__

	def simplify(self) -> InverseTerm:
		return InverseTerm(self.__coefficient__, self.__exponent__, self.__expression__.simplify())

class FunctionTerm(Expression):
	def __init__(self, coefficient: float | complex, exponent: float, expression: Expression, function: typing.Callable[[complex], complex]):
		super().__init__(coefficient, exponent)
		self.__expression__: Expression = expression
		self.__function__: typing.Callable[[complex], complex] = function

	def __str__(self) -> str:
		imag: str = self.__imaginary_str__()
		real: str = self.__real_str__()
		exp: str = self.__exponent_str__()
		return self.__wrapper_str__(self.__function__.__name__)
		return f'({real}{self.__function__.__name__}({self.__expression__})){exp}' if self.__coefficient__.imag == 0 else f'(({real}+{imag}i)*{self.__function__.__name__}({self.__expression__})){exp}'

	def solve(self, **kwargs) -> complex:
		return (self.__coefficient__ * self.__function__(self.__expression__.solve(**kwargs))) ** self.__exponent__

	def simplify(self) -> FunctionTerm:
		return FunctionTerm(self.__coefficient__, self.__exponent__, self.__expression__.simplify(), self.__function__)

class SingleTerm(Expression):
	def __init__(self, coefficient: float | complex, exponent: float, letter: str):
		letter = str(letter)
		assert len(letter) == 1, 'Letter must be a single character'
		super().__init__(coefficient, exponent)
		self.__letter__: str = letter

	def __str__(self):
		return self.__wrapper_str__(self.__letter__)

	def solve(self, **kwargs: float | complex) -> complex:
		if self.__letter__ not in kwargs:
			raise NameError(f'Variable \'{self.__letter__}\' not present in input arguments')

		return (self.__coefficient__ * kwargs[self.__letter__]) ** self.__exponent__

	@property
	def letter(self) -> str:
		return self.__letter__

class CompoundTerm(Expression):
	def __init__(self, coefficient: float | complex, exponent: float, *expressions: Expression):
		assert all(isinstance(expr, Expression) for expr in expressions), 'Found non expression object'
		super().__init__(coefficient, exponent)
		self.__expressions__: tuple[Expression, ...] = tuple(expressions)

	def __str__(self):
		return object.__repr__(self)

	@property
	def expressions(self) -> tuple[Expression, ...]:
		return self.__expressions__

class AddedTerm(CompoundTerm):
	def __init__(self, coefficient: float | complex, exponent: float, *expressions: Expression):
		super().__init__(coefficient, exponent, *expressions)

	def __str__(self):
		exprs: str = ''.join(f'{f"-" if x.negative else f"+"}{f"({x})" if isinstance(x, CompoundTerm) else str(x)}' for x in self.__expressions__).lstrip('+')
		return self.__wrapper_str__(exprs)

	def solve(self, **kwargs) -> complex:
		return self.__coefficient__ * sum(x.solve(**kwargs) for x in self.__expressions__) ** self.__exponent__

	def simplify(self) -> Expression:
		expressions: list[Expression] = []
		mapping: dict[(str, int), SingleTerm] = {}

		for expression in self.__expressions__:
			expression = expression.simplify()

			if isinstance(expression, SingleTerm) and (key := (expression.letter, expression.exponent)) in mapping:
				mapping[key].__coefficient__ += expression.__coefficient__
			elif isinstance(expression, SingleTerm):
				mapping[key] = expression
				expressions.append(expression)
			else:
				expressions.append(expression)

		if len(expressions) == 1:
			expression = expressions[0]
			expression.__coefficient__ = self.__coefficient__ * expression.coefficient ** self.__exponent__
			expression.__exponent__ *= self.__exponent__
			return expression
		else:
			return AddedTerm(self.__coefficient__, self.__exponent__, *expressions)

class MultipliedTerm(CompoundTerm):
	def __init__(self, coefficient: float | complex, exponent: float, *expressions: Expression):
		super().__init__(coefficient, exponent, *expressions)

	def __str__(self):
		imag: str = f'{int(self.__coefficient__.imag) if self.__coefficient__.imag == int(self.__coefficient__.imag) else self.__coefficient__.imag}'
		real: str = '' if self.__coefficient__.real == 1 else f'{int(self.__coefficient__.real) if self.__coefficient__.real == int(self.__coefficient__.real) else self.__coefficient__.real}'
		exp: str = '' if self.__exponent__ == 1 else f'^{int(self.__exponent__) if self.__exponent__ == int(self.__exponent__) else self.__exponent__}'
		exprs: str = '*'.join(f'{f"-" if x.negative else ""}{f"({x})" if isinstance(x, CompoundTerm) else str(x)}' for x in self.__expressions__).lstrip('+')
		return f'{real}({exprs}){exp}' if self.__coefficient__.imag == 0 else f'({real}+{imag}i)({exprs}){exp}'

	def solve(self, **kwargs) -> complex:
		return self.__coefficient__ * math.prod(x.solve(**kwargs) for x in self.__expressions__) ** self.__exponent__

	def simplify(self) -> Expression:
		expressions: list[Expression] = []
		mapping: dict[str, SingleTerm] = {}

		for expression in self.__expressions__:
			expression = expression.simplify()

			if isinstance(expression, SingleTerm) and expression.letter in mapping:
				old_expression: SingleTerm = mapping[expression.letter]
				old_expression.__coefficient__ *= expression.__coefficient__
				old_expression.__exponent__ += expression.__exponent__
			elif isinstance(expression, SingleTerm):
				mapping[expression.letter] = expression
				expressions.append(expression)
			else:
				expressions.append(expression)

		expressions.extend(mapping.values())

		if len(expressions) == 1:
			expression = expressions[0]
			expression.__coefficient__ = self.__coefficient__ * expression.coefficient ** self.__exponent__
			expression.__exponent__ *= self.__exponent__
			return expression
		else:
			return AddedTerm(self.__coefficient__, self.__exponent__, *expressions)
