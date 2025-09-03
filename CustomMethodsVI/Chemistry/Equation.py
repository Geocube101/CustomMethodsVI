from __future__ import annotations

import enum
import typing

from .. import Chemistry
from .. import Exceptions
from .. import Misc


class EquationCompound:
	"""
	Class representing a compound with a phase
	"""

	class Phase(enum.StrEnum):
		UNKNOWN: str = 'u'
		SOLID: str = 's'
		LIQUID: str = 'l'
		GAS: str = 'g'
		AQUEOUS: str = 'aq'

	def __init__(self, source: Chemistry.Atom.Atom | Chemistry.Atom.Atoms | Chemistry.Compound.Compound, phase: str | Phase, coefficient: int = 1):
		"""
		Class representing a compound with a phase
		- Constructor -
		:param source: The compound
		:param phase: The phase
		:param coefficient: The number of compound
		:raises InvalidArgumentException: If 'source' is not an Atom instance, Atoms instance, or Compound instance
		:raises InvalidArgumentException: If 'phase' is not a string or Phase enum
		:raises InvalidArgumentException: If 'coefficient' if not an integer
		:raises ValueError: If 'coefficient' is not greater than 0
		"""

		Misc.raise_ifn(isinstance(source, (Chemistry.Atom.Atom, Chemistry.Atom.Atoms, Chemistry.Compound.Compound)), Exceptions.InvalidArgumentException(EquationCompound.__init__, 'source', type(source), (Chemistry.Atom.Atom, Chemistry.Atom.Atoms, Chemistry.Compound.Compound)))
		Misc.raise_ifn(isinstance(phase, (EquationCompound.Phase, str)), Exceptions.InvalidArgumentException(EquationCompound.__init__, 'phase', type(phase), (str, EquationCompound.Phase)))
		Misc.raise_ifn(isinstance(coefficient, int), Exceptions.InvalidArgumentException(EquationCompound.__init__, 'coefficient', type(coefficient), (int,)))
		Misc.raise_ifn((coefficient := int(coefficient)) > 0, ValueError('Coefficient must be greater than 0'))
		self.__compound__: Chemistry.Compound.Compound = source if isinstance(source, Chemistry.Compound.Compound) else Chemistry.Compound.Compound(source)
		self.__phase__: EquationCompound.Phase = EquationCompound.Phase(phase.lower()) if isinstance(phase, str) else phase
		self.__coefficient__: int = int(coefficient)

	def __repr__(self) -> str:
		msg: str = repr(self.__compound__) + (f'({self.__phase__})' if self.__phase__ != EquationCompound.Phase.UNKNOWN else '')
		return msg if self.__coefficient__ == 1 else f'{self.__coefficient__}({msg})'

	def __str__(self) -> str:
		msg: str = str(self.__compound__) + (f'({self.__phase__})' if self.__phase__ != EquationCompound.Phase.UNKNOWN else '')
		return msg if self.__coefficient__ == 1 else f'{self.__coefficient__}({msg})'

	@property
	def coefficient(self) -> int:
		"""
		:return: This compound's coefficient
		"""

		return self.__coefficient__

	@property
	def compound(self) -> Chemistry.Compound.Compound:
		"""
		:return: This compound's underlying compound
		"""

		return self.__compound__

	@property
	def phase(self) -> Phase:
		"""
		:return: This compound's phase
		"""

		return self.__phase__


class Equation:
	"""
	Class representing a chemical equation
	"""

	def __init__(self, left: typing.Iterable[Chemistry.Atom.Atom | Chemistry.Atom.Atoms | Chemistry.Compound.Compound | HeatSource | EquationCompound], right: typing.Iterable[Chemistry.Atom.Atom | Chemistry.Atom.Atoms | Chemistry.Compound.Compound | HeatSource | EquationCompound], *, reversible: bool = False):
		"""
		Class representing a chemical equation
		- Constructor -
		:param left: The compounds on the left side of the equation
		:param right: The compounds on the right side of the equation
		:param reversible: Whether this equation is an equilibrium equation (reversible)
		:raises TypeError: If 'left' or 'right' contains anything that's not Heat, a PhasedCompound instance, a Compound instance, Atom instance, or Atoms instance
		"""

		self.__left__: tuple[EquationCompound | Heat, ...] = tuple(x if isinstance(x, (HeatSource, EquationCompound)) else EquationCompound(x) if isinstance(x, (Chemistry.Atom.Atom, Chemistry.Atom.Atoms)) else None for x in left)
		self.__right__: tuple[EquationCompound | Heat, ...] = tuple(x if isinstance(x, (HeatSource, EquationCompound)) else EquationCompound(x) if isinstance(x, (Chemistry.Atom.Atom, Chemistry.Atom.Atoms)) else None for x in right)
		self.__reversible__: bool = bool(reversible)

		if None in self.__left__ or None in self.__right__:
			raise TypeError('One or more inputs was not Heat, a PhasedCompound instance, an Atom instance, Atoms instance, or a Compound instance')

	def __repr__(self) -> str:
		eq: str = ' ⇋ ' if self.__reversible__ else ' ⇀ '
		return ' + '.join(repr(x) for x in self.__left__) + eq + ' + '.join(repr(x) for x in self.__right__)

	def __str__(self) -> str:
		eq: str = ' ⇋ ' if self.__reversible__ else ' ⇀ '
		return ' + '.join(str(x) for x in self.__left__) + eq + ' + '.join(str(x) for x in self.__right__)

	def reverse(self) -> None:
		"""
		Reverses the equation
		:raises RuntimeError: If the equation is not reversible
		"""

		if not self.__reversible__:
			raise RuntimeError('Equation is not reversible')

		left: tuple[EquationCompound | Heat, ...] = self.__left__
		self.__left__ = self.__right__
		self.__right__ = left

	def is_balanced(self) -> bool:
		left: dict[Chemistry.Atom.Atom, int] = {}
		right: dict[Chemistry.Atom.Atom, int] = {}

		for compound in self.__left__:
			if isinstance(compound, EquationCompound):
				for atom in compound.compound.atoms:
					if atom in left:
						left[atom.atom] += atom.count * compound.coefficient
					else:
						left[atom.atom] = atom.count * compound.coefficient

		for compound in self.__right__:
			if isinstance(compound, EquationCompound):
				for atom in compound.compound.atoms:
					if atom in left:
						right[atom.atom] += atom.count * compound.coefficient
					else:
						right[atom.atom] = atom.count * compound.coefficient

		if len(set(left.keys()).difference(right.keys())) > 0:
			return False

		for atom, count in left.items():
			if right[atom] != count:
				return False

		return True

	def reversed(self) -> Equation:
		"""
		Reverses the equation
		:return: The reversed equation
		:raises RuntimeError: If the equation is not reversible
		"""

		copy: Equation = self.copy()
		copy.reverse()
		return copy

	def copy(self) -> Equation:
		"""
		:return: A copy of this equation
		"""

		return Equation(self.__left__, self.__right__, reversible=self.__reversible__)

	@property
	def reversible(self) -> bool:
		"""
		:return: Whether this equation is reversible
		"""

		return self.__reversible__

	@property
	def left(self) -> tuple[EquationCompound | Heat, ...]:
		"""
		:return: This equation's reactants
		"""

		return self.__left__

	@property
	def right(self) -> tuple[EquationCompound | Heat, ...]:
		"""
		:return: This equation's products
		"""

		return self.__right__


class HeatSource:
	__SINGLETON: HeatSource = ...

	def __new__(cls, *args, **kwargs) -> HeatSource:
		if HeatSource.__SINGLETON is ...:
			HeatSource.__SINGLETON = super().__new__(cls)

		return HeatSource.__SINGLETON

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return 'heat'


Heat: HeatSource = HeatSource()