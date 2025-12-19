from __future__ import annotations

import builtins
import copy
import cmath
import math
import sys
import types
import typing

from .. import Exceptions
from .. import Misc
from . import Vector


class Equation:
	def __init__(self, left: Expression, right: Expression):
		Misc.raise_ifn(isinstance(left, Expression), Exceptions.InvalidArgumentException(Equation.__init__, 'left', type(left), (Expression,)))
		Misc.raise_ifn(isinstance(right, Expression), Exceptions.InvalidArgumentException(Equation.__init__, 'right', type(right), (Expression,)))
		self.__equation__: tuple[Expression, Expression] = (left, right)

	def solve(self, **kwargs) -> bool:
		return False

	def simplify(self) -> Equation:
		return type(self)(self.left.simplify(), self.right.simplify())

	@property
	def left(self) -> Expression:
		return self.__equation__[0]

	@property
	def right(self) -> Expression:
		return self.__equation__[1]


class EqualityEquation(Equation):
	def __str__(self) -> str:
		return f'{self.left} = {self.right}'

	def solve(self, **kwargs) -> bool:
		left: complex = self.left.solve(**kwargs)
		right: complex = self.right.solve(**kwargs)
		return left == right


class InequalityEquation(Equation):
	def __str__(self) -> str:
		return f'{self.left} != {self.right}'

	def solve(self, **kwargs) -> bool:
		left: complex = self.left.solve(**kwargs)
		right: complex = self.right.solve(**kwargs)
		return left != right


class ComparisonEquation(Equation):
	def __str__(self) -> str:
		return f'{self.left} <=> {self.right}'

	def solve(self, **kwargs) -> int:
		left: complex = self.left.solve(**kwargs)
		right: complex = self.right.solve(**kwargs)

		if left == right:
			return 0
		elif left.imag == 0 and right.imag == 0:
			return 0 if left.real == right.real else -1 if left.real < right.real else 1

		lmag: float = Vector.Vector(left.real, left.imag).length_squared()
		rmag: float = Vector.Vector(right.real, right.imag).length_squared()
		return 0 if lmag == rmag else -1 if lmag < rmag else 1


class Expression:
	def __init__(self, coefficient: complex, exponent: float):
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

	def __add__(self, other: Expression | complex) -> Expression | AddedTerm:
		if type(other) is type(self) is Expression and self.exponent == other.exponent:
			return Expression(self.__coefficient__ + other.__coefficient__, self.exponent)
		elif isinstance(other, Expression):
			return AddedTerm(1, 1, self, other)
		elif isinstance(other, (float, int, complex)):
			return AddedTerm(1, 1, self, Expression(other, 1))
		else:
			return NotImplemented

	def __sub__(self, other: Expression | complex) -> Expression | AddedTerm:
		if type(other) is type(self) is Expression and self.exponent == other.exponent:
			return Expression(self.__coefficient__ - other.__coefficient__, self.exponent)
		elif isinstance(other, Expression):
			return AddedTerm(1, 1, self, -other)
		elif isinstance(other, (float, int, complex)):
			return AddedTerm(1, 1, self, Expression(-other, 1))
		else:
			return NotImplemented

	def __radd__(self, other: Expression | complex) -> Expression | AddedTerm:
		if type(other) is type(self) is Expression and self.exponent == other.exponent:
			return Expression(other.__coefficient__ + self.__coefficient__, self.exponent)
		elif isinstance(other, Expression):
			return AddedTerm(1, 1, other, self)
		elif isinstance(other, (float, int, complex)):
			return AddedTerm(1, 1, Expression(other, 1), self)
		else:
			return NotImplemented

	def __rsub__(self, other: Expression | complex) -> Expression | AddedTerm:
		if type(other) is type(self) is Expression and self.exponent == other.exponent:
			return Expression(other.__coefficient__ - self.__coefficient__, self.exponent)
		elif isinstance(other, Expression):
			return AddedTerm(1, 1, other, -self)
		elif isinstance(other, (float, int, complex)):
			return AddedTerm(1, 1, Expression(other, 1), -self)
		else:
			return NotImplemented

	def __mul__(self, other: Expression | complex) -> Expression | MultipliedTerm:
		if type(other) is type(self) is Expression:
			return Expression(self.__coefficient__ * other.__coefficient__, self.exponent + other.exponent)
		elif isinstance(other, Expression):
			return MultipliedTerm(1, 1, self, other)
		elif isinstance(other, (float, int, complex)):
			return MultipliedTerm(1, 1, self, Expression(other, 1))
		else:
			return NotImplemented

	def __rmul__(self, other: Expression | complex) -> Expression | DividedTerm:
		if type(other) is type(self) is Expression:
			return Expression(other.__coefficient__ * self.__coefficient__, other.exponent * self.exponent)
		elif isinstance(other, Expression):
			return MultipliedTerm(1, 1, other, self)
		elif isinstance(other, (float, int, complex)):
			return MultipliedTerm(1, 1, Expression(other, 1), self)
		else:
			return NotImplemented

	def __truediv__(self, other: Expression | complex) -> Expression | DividedTerm:
		if type(other) is type(self) is Expression and self.exponent == other.exponent:
			return Expression(self.__coefficient__ / other.__coefficient__, self.exponent)
		elif type(other) is type(self) is Expression and self.coefficient == other.coefficient:
			return Expression(self.__coefficient__, self.exponent - other.exponent)
		elif isinstance(other, Expression):
			return DividedTerm(1, 1, self, other)
		elif isinstance(other, (float, int, complex)):
			return DividedTerm(1, 1, self, Expression(other, 1))
		else:
			return NotImplemented

	def __rtruediv__(self, other: Expression | complex) -> Expression | AddedTerm:
		if type(other) is type(self) is Expression and self.exponent == other.exponent:
			return Expression(other.__coefficient__ / self.__coefficient__, other.exponent)
		elif type(other) is type(self) is Expression and self.coefficient == other.coefficient:
			return Expression(other.__coefficient__, other.exponent - self.exponent)
		elif isinstance(other, Expression):
			return DividedTerm(1, 1, other, self)
		elif isinstance(other, (float, int, complex)):
			return DividedTerm(1, 1, Expression(other, 1), self)
		else:
			return NotImplemented

	def __pow__(self, other: Expression | float, modulo=None) -> Expression | PoweredTerm:
		assert modulo is None, 'Modulo not yet supported'

		if isinstance(other, Expression):
			return PoweredTerm(1, self, other)
		elif isinstance(other, (float, int)):
			clone: Expression = copy.deepcopy(self)
			clone.__exponent__ *= other
			return clone
		else:
			return NotImplemented

	def __rpow__(self, other: Expression | float | complex) -> Expression | PoweredTerm:
		if isinstance(other, Expression):
			return PoweredTerm(1, other, self)
		elif isinstance(other, (float, int)):
			return PoweredTerm(1, Expression(other, 1), self)
		else:
			return NotImplemented

	def __real_str__(self) -> str:
		return '' if self.__coefficient__ == 1 else '-' if self.__coefficient__ == -1 else f'{int(self.__coefficient__.real) if self.__coefficient__.real.is_integer() else self.__coefficient__.real}' if self.__coefficient__.imag == 0 else f'({int(self.__coefficient__.real) if self.__coefficient__.real.is_integer() else self.__coefficient__.real}+{int(self.__coefficient__.imag) if self.__coefficient__.imag.is_integer() else self.__coefficient__.imag}i)'

	def __exponent_str__(self) -> str:
		return '' if self.__exponent__ == 1 else f'^{int(self.__exponent__) if self.__exponent__ == int(self.__exponent__) else self.__exponent__}'

	def __imaginary_str__(self) -> str:
		return '' if self.__coefficient__.imag == 0 else f'{int(self.__coefficient__.imag) if self.__coefficient__.imag == int(self.__coefficient__.imag) else self.__coefficient__.imag}'

	def __coefficient_str__(self) -> str:
		real: str = self.__real_str__()
		imag: str = self.__imaginary_str__()
		return '' if len(real) == 0 and len(imag) == 0 else real if len(imag) == 0 else f'({real}+{imag}i)'

	def __wrapper_str__(self, middle: typing.Any) -> str:
		coef: str = self.__coefficient_str__()
		powr: str = self.__exponent_str__()
		midl: str = str(middle)

		if len(coef) == 0 and len(powr) == 0 and len(midl) == 0 and self.__coefficient__.imag == 0:
			return str(int(self.__coefficient__.real)) if self.__coefficient__.real.is_integer() else str(self.__coefficient__.real)
		elif len(coef) == 0 and len(powr) == 0 and len(midl) == 0 and self.__coefficient__.imag == 0:
			return str(self.__coefficient__)
		elif len(coef) == 0 and len(powr) == 0:
			return midl
		elif len(coef) == 0 and len(midl) == 0:
			return '1'
		elif len(powr) == 0 and len(midl) == 0:
			return coef
		elif len(coef) == 0:
			return f'({midl}){powr}'
		elif len(powr) == 0:
			return f'{coef}({midl})'
		elif len(midl) == 0:
			return f'{coef}{powr}'
		else:
			return f'{coef}({midl}){powr}'

	def solve(self, **kwargs) -> complex:
		return complex('inf') if self.is_infinite else self.__coefficient__ ** self.__exponent__

	def simplify(self) -> Expression:
		return copy.deepcopy(self)

	@property
	def is_negative(self) -> bool:
		return self.__coefficient__.real < 0

	@property
	def is_number(self) -> bool:
		return type(self) is Expression

	@property
	def is_infinite(self) -> bool:
		return cmath.isinf(self.__coefficient__) or cmath.isinf(self.__exponent__)

	@property
	def coefficient(self) -> complex:
		return self.__coefficient__

	@property
	def exponent(self) -> float:
		return self.__exponent__


class InverseTerm(Expression):
	def __init__(self, coefficient: complex, exponent: float, expression: Expression | complex):
		super().__init__(coefficient, exponent)
		self.__expression__: Expression = expression if isinstance(expression, Expression) else Expression(complex(expression), 1)

	def __str__(self) -> str:
		powr: str = self.__exponent_str__()
		coef: str = self.__coefficient_str__()
		expr: str = str(self.__expression__)
		return f'1/{expr}' if len(expr) == 1 and len(coef) == 0 and len(powr) == 0 else f'1/({expr})' if len(coef) == 0 and len(powr) == 0 else f'(1/{coef})({expr})' if len(powr) == 0 else f'({expr})^({powr})' if len(coef) == 0 else f'(1/{coef})({expr})^({powr})'

	def solve(self, **kwargs) -> complex:
		result: complex = self.__expression__.solve(**kwargs)
		return float('inf') if result == 0 else (self.__coefficient__ / result) ** self.__exponent__

	def simplify(self) -> InverseTerm:
		return InverseTerm(self.__coefficient__, self.__exponent__, self.__expression__.simplify())


class PoweredTerm(Expression):
	def __init__(self, coefficient: complex, base: Expression | complex, exponent: Expression | complex):
		super().__init__(coefficient, 1)
		self.__base__: Expression = base if isinstance(base, Expression) else Expression(complex(base), 1)
		self.__power__: Expression = exponent if isinstance(exponent, Expression) else Expression(complex(exponent), 1)

	def __str__(self):
		exp: str = str(self.__power__)
		base: str = self.__wrapper_str__(str(self.__base__))
		return base if len(exp) == 0 else f'({base})^({exp})'

	def solve(self, **kwargs) -> complex:
		base: complex = self.__base__.solve(**kwargs)
		exp: complex = self.__power__.solve(**kwargs)

		try:
			return self.__coefficient__ * base ** exp
		except OverflowError:
			return complex('inf')

	def simplify(self) -> PoweredTerm | Expression:
		bse: Expression = self.__base__.simplify()
		exp: Expression = self.__power__.simplify()

		if type(exp) is Expression and (value := exp.solve()).imag == 0:
			bse.__exponent__ *= value.real
			return bse
		else:
			return PoweredTerm(self.__coefficient__, bse, exp)

	@property
	def exponent(self) -> Expression:
		return self.__power__


class FunctionTerm(Expression):
	def __init__(self, coefficient: complex, exponent: float, expression: Expression | complex, function: typing.Callable[[complex], complex], inverse: typing.Optional[typing.Callable[[complex], complex]] = ...):
		super().__init__(coefficient, exponent)
		self.__expression__: Expression = expression if isinstance(expression, Expression) else Expression(complex(expression), 1)
		self.__function__: typing.Callable[[complex], complex] = function
		self.__inverse__: typing.Optional[typing.Callable[[complex], complex]] = inverse

	def __str__(self) -> str:
		imag: str = self.__imaginary_str__()
		real: str = self.__real_str__()
		exp: str = self.__exponent_str__()

		if len(exp) == 0:
			return f'{real}{self.__function__.__name__}({self.__expression__})' if self.__coefficient__.imag == 0 else f'({real}+{imag}i)*{self.__function__.__name__}({self.__expression__})'
		else:
			return f'({real}{self.__function__.__name__}({self.__expression__})){exp}' if self.__coefficient__.imag == 0 else f'(({real}+{imag}i)*{self.__function__.__name__}({self.__expression__})){exp}'

	def solve(self, **kwargs) -> complex:
		return (self.__coefficient__ * self.__function__(self.__expression__.solve(**kwargs))) ** self.__exponent__

	def simplify(self) -> FunctionTerm | Expression:
		inner: Expression = self.__expression__.simplify()
		return inner.__expression__ if isinstance(inner, FunctionTerm) and inner.__function__ == self.__inverse__ else FunctionTerm(self.__coefficient__, self.__exponent__, inner, self.__function__, self.__inverse__)


class SingleTerm(Expression):
	def __init__(self, coefficient: complex, exponent: float, letter: str):
		assert isinstance(letter, str) and len(letter := str(letter)) == 1, 'Letter must be a single character'
		super().__init__(coefficient, exponent)
		self.__letter__: str = letter

	def __str__(self):
		return self.__wrapper_str__(self.__letter__)

	def solve(self, **kwargs: complex) -> complex:
		if self.__letter__ not in kwargs:
			raise NameError(f'Variable \'{self.__letter__}\' not present in input arguments')

		return (self.__coefficient__ * kwargs[self.__letter__]) ** self.__exponent__

	@property
	def letter(self) -> str:
		return self.__letter__


class LimitedTerm(Expression):
	class Limit:
		def __init__(self, variable: str, target: complex):
			assert isinstance(variable, str) and len(variable := str(variable)) == 1, 'Letter must be a single character'
			self.__variable__: str = variable
			self.__target__: complex = complex(target)

		def __repr__(self) -> str:
			return str(self)

		def __str__(self) -> str:
			return f'{self.__variable__}→{'∞' if self.is_infinite else self.__target__.real if self.__target__.imag == 0 else self.__target__}'

		@property
		def is_infinite(self) -> bool:
			return self.__target__ == complex('inf')

		@property
		def limit(self) -> complex:
			return self.__target__

		@property
		def variable(self) -> str:
			return self.__variable__

	def __init__(self, coefficient: complex, exponent: float, expression: Expression | complex, *limits: Limit):
		super().__init__(coefficient, exponent)
		assert len(limits) > 0, 'No limit supplied'
		assert all(isinstance(limit, LimitedTerm.Limit) for limit in limits), 'One or more limits is not valid'
		self.__expression__: Expression = expression if isinstance(expression, Expression) else Expression(complex(expression), 1)
		self.__limits__: tuple[LimitedTerm.Limit, ...] = tuple(limits)

	def __str__(self) -> str:
		expr: str = f'lim({self.__expression__}, {",".join(map(str, self.__limits__))})'
		return self.__wrapper_str__(expr)

	def solve(self, **kwargs) -> complex:
		if all(not lim.is_infinite for lim in self.__limits__):
			values: dict[str, complex] = {lim.variable: lim.limit for lim in self.__limits__}
			return self.__expression__.solve(**values)
		else:
			max_step: int = 1000
			results: list[complex] = []
			total_weight: float = 0
			current_weight: float = 1
			infinite: set[str] = {lim.variable for lim in self.__limits__}
			values: dict[str, complex] = {lim.variable: int(sys.float_info.max) if lim.limit == float('inf') else int(sys.float_info.min) if lim.limit == float('-inf') else lim.limit for lim in self.__limits__}

			for i in range(max_step):
				result: complex = self.__expression__.solve(**values)
				weight: float = current_weight
				results.append(result * weight)
				total_weight += weight
				current_weight *= 0.75

				for variable in infinite:
					values[variable] >>= 1

			average: complex = sum(results) / total_weight
			return complex(round(average.real, 24), round(average.imag, 24))

	@property
	def limits(self) -> tuple[LimitedTerm.Limit, ...]:
		return self.__limits__


class CompoundTerm(Expression):
	def __init__(self, coefficient: complex, exponent: float, *expressions: Expression | complex):
		assert all(isinstance(expr, (Expression, complex)) for expr in expressions), 'Found non expression object'
		super().__init__(coefficient, exponent)
		self.__expressions__: tuple[Expression, ...] = tuple(expression if isinstance(expression, Expression) else Expression(complex(expression), 1) for expression in expressions)

	def __str__(self):
		return object.__repr__(self)

	def __wrapper_str__(self, middle: typing.Any) -> str:
		imag: str = self.__imaginary_str__()
		real: str = self.__real_str__()
		exp: str = self.__exponent_str__()
		mid: str = str(middle)

		if len(mid) == 0:
			return f'{real}{exp}' if self.__coefficient__.imag == 0 else f'({real}+{imag}i){exp}'
		elif len(real) == 0 and len(exp) == 0:
			return mid if self.__coefficient__.imag == 0 else f'({real}+{imag}i)({mid})'
		elif self.__coefficient__ == 1:
			return f'({mid}){exp}'
		elif self.__exponent__ == 1:
			return f'{real}({mid})'
		else:
			return f'({real}({mid})){exp}' if self.__coefficient__.imag == 0 else f'(({real}+{imag}i)({mid})){exp}' if self.__exponent__ != 1 else f'({real}+{imag}i)({mid})'

	@property
	def expressions(self) -> tuple[Expression, ...]:
		return self.__expressions__


class AddedTerm(CompoundTerm):
	def __init__(self, coefficient: complex, exponent: float, *expressions: Expression | complex):
		super().__init__(coefficient, exponent, *expressions)

	def __str__(self):
		exprs: str = ''.join(f'{"" if x.is_negative else "+"}{f"({x})" if isinstance(x, CompoundTerm) else str(x)}' for x in self.__expressions__).lstrip('+')
		return self.__wrapper_str__(exprs)

	def solve(self, **kwargs) -> complex:
		return self.__coefficient__ * sum(x.solve(**kwargs) for x in self.__expressions__) ** self.__exponent__

	def simplify(self) -> Expression:
		expressions: list[Expression] = []
		mapping: dict[(str, int), SingleTerm] = {}

		for expression in self.__expressions__:
			expression = expression.simplify()

			if (is_term := isinstance(expression, SingleTerm)) and (key := (expression.letter, expression.exponent)) in mapping:
				mapping[key].__coefficient__ += expression.__coefficient__
			elif is_term:
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
	def __init__(self, coefficient: complex, exponent: float, *expressions: Expression | complex):
		super().__init__(coefficient, exponent, *expressions)

	def __str__(self):
		imag: str = f'{int(self.__coefficient__.imag) if self.__coefficient__.imag == int(self.__coefficient__.imag) else self.__coefficient__.imag}'
		real: str = '' if self.__coefficient__.real == 1 else f'{int(self.__coefficient__.real) if self.__coefficient__.real == int(self.__coefficient__.real) else self.__coefficient__.real}'
		exp: str = '' if self.__exponent__ == 1 else f'^{int(self.__exponent__) if self.__exponent__ == int(self.__exponent__) else self.__exponent__}'
		exprs: str = '*'.join(f'{f"-" if x.is_negative else ""}{f"({x})" if isinstance(x, CompoundTerm) else str(x)}' for x in self.__expressions__).lstrip('+')
		return exprs if len(real) == 0 and len(exp) == 0 else f'{real}({exprs}){exp}' if self.__coefficient__.imag == 0 else f'({real}+{imag}i)({exprs}){exp}'

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
			else:
				expressions.append(expression)

		expressions.extend(mapping.values())

		if len(expressions) == 1:
			expression = expressions[0]
			expression.__coefficient__ = self.__coefficient__ * expression.coefficient ** self.__exponent__
			expression.__exponent__ *= self.__exponent__
			return expression
		elif expressions[0].is_number and isinstance(term := expressions[1], SingleTerm):
			return SingleTerm(expressions[0].solve() * term.coefficient * self.__coefficient__, term.exponent * self.__exponent__, term.letter)
		else:
			return MultipliedTerm(self.__coefficient__, self.__exponent__, *expressions)


class DividedTerm(CompoundTerm):
	def __init__(self, coefficient: complex, exponent: float, *expressions: Expression | complex):
		super().__init__(coefficient, exponent, *expressions)

	def __str__(self):
		imag: str = f'{int(self.__coefficient__.imag) if self.__coefficient__.imag == int(self.__coefficient__.imag) else self.__coefficient__.imag}'
		real: str = '' if self.__coefficient__.real == 1 else f'{int(self.__coefficient__.real) if self.__coefficient__.real == int(self.__coefficient__.real) else self.__coefficient__.real}'
		exp: str = '' if self.__exponent__ == 1 else f'^{int(self.__exponent__) if self.__exponent__ == int(self.__exponent__) else self.__exponent__}'
		exprs: str = '/'.join(f'{f"-" if x.is_negative else ""}{f"({x})" if isinstance(x, CompoundTerm) else str(x)}' for x in self.__expressions__).lstrip('+')
		return exprs if len(real) == 0 and len(exp) == 0 else f'{real}({exprs}){exp}' if self.__coefficient__.imag == 0 else f'({real}+{imag}i)({exprs}){exp}'

	def solve(self, **kwargs) -> complex:
		return self.__coefficient__ * math.prod(1 / x.solve(**kwargs) for x in self.__expressions__) ** self.__exponent__

	def simplify(self) -> Expression:
		expressions: list[Expression] = []
		mapping: dict[str, SingleTerm] = {}

		for expression in self.__expressions__:
			expression = expression.simplify()

			if isinstance(expression, SingleTerm) and expression.letter in mapping:
				old_expression: SingleTerm = mapping[expression.letter]
				old_expression.__coefficient__ /= expression.__coefficient__
				old_expression.__exponent__ -= expression.__exponent__
			elif isinstance(expression, SingleTerm):
				mapping[expression.letter] = expression
			else:
				expressions.append(expression)

		expressions.extend(mapping.values())

		if len(expressions) == 1:
			expression = expressions[0]
			expression.__coefficient__ = self.__coefficient__ / expression.coefficient ** self.__exponent__
			expression.__exponent__ /= self.__exponent__
			return expression
		else:
			return DividedTerm(self.__coefficient__, self.__exponent__, *expressions)


def parse(string: str) -> Expression | Equation:
	def __tokenizer__(input_str: str) -> list[str | list]:
		controls: list[str] = []
		tokens: list[str | list] = []
		token: str = ''

		for i, c in enumerate(input_str):
			lc: typing.Optional[str] = input_str[i - 1] if i > 0 else None

			if c.isspace():
				continue
			elif c == '(' and len(controls) == 0:
				controls.append(c)
				tokens.append(token)
				token = ''
			elif c == '(':
				controls.append(c)
				token += c
			elif c == ')' and len(controls) == 1 and controls[-1] == '(':
				del controls[-1]
				tokens.append(__tokenizer__(token))
				token = ''
			elif c == ')' and len(controls) > 1:
				del controls[-1]
				token += c
			elif c == ')':
				raise SyntaxError('Malformed input')
			elif len(controls) == 0 and lc is not None and lc.isalpha() != c.isalpha():
				tokens.append(token)
				token = c
			elif len(controls) == 0 and lc is not None and lc.isnumeric() != c.isnumeric():
				tokens.append(token)
				token = c
			else:
				token += c

		tokens.append(token)
		return [tok for tok in tokens if len(tok) > 0]

	def __operator__(segments: list[Expression | str]) -> Expression | LimitedTerm.Limit:
		if any(isinstance(x, str) for x in segments):
			operator_ranking: tuple[int, ...] = tuple(operators[x] for x in segments if isinstance(x, str))
			highest_operator: int = max(operator_ranking)
			indices: tuple[int, ...] = tuple(i for i, x in enumerate(segments) if isinstance(x, str) and operators[x] == highest_operator)
			actions: tuple[str, ...] = tuple(segments[i] for i in indices)
			parts: list[list[Expression | str]] = []
			part: list[Expression | str] = []

			for i, seg in enumerate(segments):
				if i in indices:
					parts.append(part)
					part = []
				else:
					part.append(seg)

			parts.append(part)
			parts = [part for part in parts if len(part) > 0]
			expression: Expression = __operator__(parts[0])
			assert actions.count('->') <= 1 and actions.count('→') <= 1, 'Limit operator is not chainable'

			for i, operator in enumerate(actions):
				second: Expression = __operator__(parts[i + 1])

				if operator == '->' or operator == '→':
					if not isinstance(expression, SingleTerm) or expression.coefficient != 1 or expression.exponent != 1:
						raise ValueError('Limit variable must be a single letter')
					elif not second.is_number:
						raise ValueError('Limit target must be a scalar constant')

					return LimitedTerm.Limit(expression.letter, second.solve())
				elif operator == '**' or operator == '^':
					expression **= second
				elif operator == '*':
					expression *= second
				elif operator == '/':
					expression /= second
				elif operator == '+':
					expression += second
				elif operator == '-':
					expression -= second

			return expression
		elif len(segments) > 1:
			raise RuntimeError('Failed to parse expression')
		else:
			return segments[0]

	def __assembler__(input_tokens: list[str | list], depth: int) -> Expression | Equation | tuple[Expression, ...]:
		last_token: typing.Optional[str | list[str | list]] = None
		segments: list[Expression | str] = []
		is_arguments_list: bool = False

		for i, token in enumerate(input_tokens):
			result: typing.Optional[Expression | str]

			if isinstance(token, list) and (function := functions.get(last_token)) is not None:
				del segments[-1]
				arguments: Expression | Equation | tuple[Expression, ...] = __assembler__(token, depth + 1)
				result = function(arguments) if isinstance(arguments, (Expression, Equation)) else function(*arguments)
			elif isinstance(token, list):
				result = __assembler__(token, depth + 1)
			elif token.isalpha() and len(token) == 1:
				result = SingleTerm(1, 1, token)
			elif token.casefold() == 'INF'.casefold():
				result = Expression(complex('inf'), 1)
			elif token.isalpha():
				result = MultipliedTerm(1, 1, *[SingleTerm(1, 1, letter) for letter in token])
			elif token.isnumeric():
				result = Expression(float(token), 1)
			elif token in operators or (token in comparison_operators and depth == 0):
				result = token
			elif token == ',':
				is_arguments_list = True
				result = token
			else:
				raise SyntaxError(f'Malformed expression - Unexpected token: \'{token}\'')

			if not is_arguments_list and len(segments) > 0 and isinstance(result, Expression) and not isinstance(segments[-1], str):
				segments.append('*')

			segments.append(result)
			last_token = token

		if is_arguments_list:
			arguments: list[list[Expression | str]] = []
			argument: list[Expression | str] = []

			for token in segments:
				if token == ',':
					arguments.append(argument)
					argument = []
				else:
					argument.append(token)

			arguments.append(argument)
			return tuple(__operator__(arg) for arg in arguments if len(arg) > 0)
		elif any(x in comparison_operators for x in segments):
			index: int = next(i for i, s in enumerate(segments) if s in comparison_operators)
			comparison: str = segments[index]
			left: Expression = __operator__(segments[:index])
			right: Expression = __operator__(segments[index + 1:])

			if comparison == '=':
				return EqualityEquation(left, right)
			elif comparison == '!=':
				return InequalityEquation(left, right)
			else:
				return ComparisonEquation(left, right)
		else:
			return __operator__(segments)

	comparison_operators: tuple[str, ...] = ('=', '<', '>', '>=', '<=', '!=')
	operators: dict[str, int] = {
		'+': 3, '-': 3,
		'*': 2, '/': 2,
		'**': 1, '^': 1,
		'->': 0, '→': 0
	}
	string = str(string)
	expression_tokens: list[str | list] = __tokenizer__(string)
	functions: dict[str, types.FunctionType] = {k: v for k, v in globals().items() if isinstance(v, types.FunctionType) and v is not parse}
	inverse_functions: dict[str, types.FunctionType] = {}
	return __assembler__(expression_tokens, 0).simplify()


def sin(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.sin)


def cos(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.cos)


def tan(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.tan)


def asin(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.asin)


def acos(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.acos)


def atan(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.atan)


def sinh(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.sinh)


def cosh(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.cosh)


def tanh(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.tanh)


def asinh(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.asinh)


def acosh(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.acosh)


def atanh(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, cmath.atanh)


def abs(expression: Expression | complex) -> FunctionTerm:
	return FunctionTerm(1, 1, expression, builtins.abs)


def pow(base: Expression | complex, exponent: Expression | complex) -> PoweredTerm:
	return PoweredTerm(1, base, exponent)


def sqrt(expression: Expression | complex) -> PoweredTerm:
	return PoweredTerm(1, expression, 0.5)


def cbrt(expression: Expression | complex) -> PoweredTerm:
	return PoweredTerm(1, expression, 0.333333333)


def root(base: Expression | complex, exponent: Expression | complex) -> PoweredTerm:
	return PoweredTerm(1, base, InverseTerm(1, 1, exponent))


def limit(expression: Expression | complex, lim: LimitedTerm.Limit, *limits: LimitedTerm.Limit) -> LimitedTerm:
	return LimitedTerm(1, 1, expression, lim, *limits)
