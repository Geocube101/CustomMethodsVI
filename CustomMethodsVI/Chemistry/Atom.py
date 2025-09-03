from __future__ import annotations

import typing

from .. import Chemistry
from .. import Exceptions
from .. import Misc


class Atom:
	"""
	Class representing a single atomic element
	"""

	def __init__(self, info: dict[str, int | float | str]):
		"""
		Class representing a single atomic element
		- Constructor -
		:param info: The atomic element info
		"""

		Misc.raise_ifn(all(isinstance(key, str) and isinstance(value, (int, float, str)) for key, value in info.items()), TypeError('Invalid atomic-info type'))
		self.__atom_info__: dict[str, int | float | str] = dict(info)

	def __eq__(self, other: Atom) -> bool:
		return isinstance(other, Atom) and self.proton_count == other.proton_count

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return self['Symbol']

	def __mul__(self, n: int) -> Atoms:
		"""
		Multiplies this atom 'n' times
		:param n: The number of times to multiply
		:return: The grouping of atoms
		"""

		return Atoms(self, int(n)) if isinstance(n, int) else NotImplemented

	def __rmul__(self, n: int) -> Atoms:
		"""
		Multiplies this atom 'n' times
		:param n: The number of times to multiply
		:return: The grouping of atoms
		"""

		return self * n

	def __add__(self, other: Atom | Atoms | Chemistry.Compound.Compound) -> Atoms | Chemistry.Compound.Compound:
		"""
		Adds either another atom, atom group, or compound to this atom
		:param other: The other atom, atom group, or compound
		:return: The resulting atom group or compound
		"""

		if isinstance(other, Atom) and self == other:
			return Atoms(self, 2)
		elif isinstance(other, Atoms) and other.atom == self:
			return Atoms(self, other.count + 1)
		elif isinstance(other, (Atom, Atoms, Chemistry.Compound.Compound)):
			return Chemistry.Compound.Compound(self, other)
		else:
			return NotImplemented

	def __radd__(self, other: Atom | Atoms | Chemistry.Compound.Compound) -> Atoms | Chemistry.Compound.Compound:
		"""
		Adds this atom to either another atom, atom group, or compound
		:param other: The other atom, atom group, or compound
		:return: The resulting atom group or compound
		"""

		if isinstance(other, Atom) and self == other:
			return Atoms(self, 2)
		elif isinstance(other, Atoms) and other.atom == self:
			return Atoms(self, other.count + 1)
		elif isinstance(other, (Atom, Atoms, Chemistry.Compound.Compound)):
			return Chemistry.Compound.Compound(other, self)
		else:
			return NotImplemented

	def __rtruediv__(self, coefficient: int) -> Chemistry.Equation.EquationCompound:
		"""
		Appends a coefficient to this compound
		:param coefficient: The coefficient
		:return: The new compound
		"""

		return Chemistry.Equation.EquationCompound(self, Chemistry.Equation.EquationCompound.Phase.UNKNOWN, coefficient) if isinstance(coefficient, int) else NotImplemented

	def __rfloordiv__(self, coefficient: int) -> Chemistry.Equation.EquationCompound:
		"""
		Appends a coefficient to this compound
		:param coefficient: The coefficient
		:return: The new compound
		"""

		return coefficient / self

	def __rmod__(self, coefficient: int) -> Chemistry.Equation.EquationCompound:
		"""
		Appends a coefficient to this compound
		:param coefficient: The coefficient
		:return: The new compound
		"""

		return coefficient / self

	def __rxor__(self, coefficient: int) -> Chemistry.Equation.EquationCompound:
		"""
		Appends a coefficient to this compound
		:param coefficient: The coefficient
		:return: The new compound
		"""

		return coefficient / self

	def __hash__(self) -> int:
		return self.proton_count

	def __getitem__(self, item: str) -> int | float | str:
		return getattr(self, str(item))

	def __getattr__(self, item: str) -> int | float | str:
		if (item := str(item)) not in self.__atom_info__:
			raise AttributeError(f'\'{type(self).__name__}\' object has no attribute \'{item}\'')

		return self.__atom_info__[str(item)]

	def __iter__(self) -> typing.Iterator[tuple[str, int | float | str]]:
		"""
		:return: An iterator iterating this element's name attribute pairs
		"""

		return iter(self.__atom_info__.items())

	@property
	def proton_count(self) -> int:
		"""
		:return: This element's atomic number
		"""

		return self['Atomic_Number']

	@property
	def neutron_count(self) -> int:
		"""
		:return: This element's neutron count
		"""

		return int(self.mass) - self.proton_count

	@property
	def valence_count(self) -> int:
		"""
		:return: The number of valence electrons for this element when neutral
		"""

		valence: int | str = self['Group']
		return valence % 10 if isinstance(valence, int) else 0

	@property
	def mass(self) -> float:
		"""
		:return: This element's atomic weight
		"""

		return self['Atomic_Weight']

	@property
	def electronegativity(self) -> float:
		"""
		:return: This element's electronegativity
		"""

		return self['Electronegativity']

	@property
	def name(self) -> str:
		"""
		:return: This element's name
		"""

		return self.__atom_info__['Name']

	@property
	def symbol(self) -> str:
		"""
		:return: This element's name
		"""

		return self.__atom_info__['Symbol']


class Atoms:
	"""
	Class representing a collection of single elemental atoms
	"""

	def __init__(self, atom: Atom, count: int):
		"""
		Class representing a collection of single elemental atoms
		- Constructor -
		:param atom: The elemental atom
		:param count: The number of atoms
		:raises InvalidArgumentException: If 'atom' is not an Atom instance
		:raises InvalidArgumentException: If 'count' is not an integer
		"""

		Misc.raise_ifn(isinstance(atom, Atom), Exceptions.InvalidArgumentException(Atoms.__init__, 'atom', type(atom), (Atom,)))
		Misc.raise_ifn(isinstance(count, int), Exceptions.InvalidArgumentException(Atoms.__init__, 'count', type(count), (int,)))
		self.__atom__ = atom
		self.__count__ = int(count)

	def __eq__(self, other: Atoms) -> bool:
		return isinstance(other, Atoms) and self.__atom__ == other.__atom__ and self.__count__ == other.__count__

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return str(self.__atom__) if self.__count__ == 1 else str(self.__atom__) + Chemistry.util.convert_int_to_subscript_str(self.__count__)

	def __mul__(self, n: int) -> Atoms:
		"""
		Multiplies this grouping of atoms 'n' times
		:param n: The number of times to multiply this grouping by
		:return: The multiplied grouping
		"""

		return Atoms(self.__atom__, self.__count__ * int(n)) if isinstance(n, int) else NotImplemented

	def __rmul__(self, n: int) -> Atoms:
		"""
		Multiplies this grouping of atoms 'n' times
		:param n: The number of times to multiply this grouping by
		:return: The multiplied grouping
		"""

		return self * n

	def __add__(self, other: Atom | Atoms | Chemistry.Compound.Compound) -> Atoms | Chemistry.Compound.Compound:
		"""
		Adds either another atom, atom group, or compound to this atom group
		:param other: The other atom, atom group, or compound
		:return: The resulting atom group or compound
		"""

		if isinstance(other, Atom) and other == self.__atom__:
			return Atoms(self.__atom__, self.__count__ + 1)
		elif isinstance(other, Atoms) and other.__atom__ == self.__atom__:
			return Atoms(self.__atom__, self.__count__ + other.__count__)
		elif isinstance(other, (Atom, Atoms, Chemistry.Compound.Compound)):
			return Chemistry.Compound.Compound(self, other)
		else:
			return NotImplemented

	def __radd__(self, other: Atom | Atoms | Chemistry.Compound.Compound) -> Atoms | Chemistry.Compound.Compound:
		"""
		Adds this atom group to either another atom, atom group, or compound
		:param other: The other atom, atom group, or compound
		:return: The resulting atom group or compound
		"""

		if isinstance(other, Atom) and other == self.__atom__:
			return Atoms(self.__atom__, self.__count__ + 1)
		elif isinstance(other, Atoms) and other.__atom__ == self.__atom__:
			return Atoms(self.__atom__, self.__count__ + other.__count__)
		elif isinstance(other, (Atom, Atoms, Chemistry.Compound.Compound)):
			return Chemistry.Compound.Compound(other, self)
		else:
			return NotImplemented

	def __rtruediv__(self, coefficient: int) -> Chemistry.Equation.EquationCompound:
		"""
		Appends a coefficient to this compound
		:param coefficient: The coefficient
		:return: The new compound
		"""

		return Chemistry.Equation.EquationCompound(self, Chemistry.Equation.EquationCompound.Phase.UNKNOWN, coefficient) if isinstance(coefficient, int) else NotImplemented

	def __rfloordiv__(self, coefficient: int) -> Chemistry.Equation.EquationCompound:
		"""
		Appends a coefficient to this compound
		:param coefficient: The coefficient
		:return: The new compound
		"""

		return coefficient / self

	def __rmod__(self, coefficient: int) -> Chemistry.Equation.EquationCompound:
		"""
		Appends a coefficient to this compound
		:param coefficient: The coefficient
		:return: The new compound
		"""

		return coefficient / self

	def __rxor__(self, coefficient: int) -> Chemistry.Equation.EquationCompound:
		"""
		Appends a coefficient to this compound
		:param coefficient: The coefficient
		:return: The new compound
		"""

		return coefficient / self

	def __hash__(self) -> int:
		return self.__atom__.proton_count

	@property
	def mass(self) -> float:
		"""
		:return: The total mass of the atom group
		"""

		return self.__atom__.mass * self.__count__

	@property
	def atom(self) -> Atom:
		"""
		:return: The base atom of this group
		"""

		return self.__atom__

	@property
	def count(self) -> int:
		"""
		:return: The number of atoms in this group
		"""

		return self.__count__


def sort(collection: typing.Iterable[Atom | Atoms], attribute: str = 'proton_count', *, reverse: bool = False) -> list[Atom]:
	"""
	Sorts a collection of atoms by some attribute
	:param collection: The collection of atoms
	:param attribute: The attribute to sort py
	:param reverse: Whether to sort descending
	:return: The sorted list of atoms
	:raises TypeError: If one or more items in the collection is not an Atom instance or an Atoms instance
	"""

	atoms: tuple[Atom, ...] = tuple(atom if isinstance(atom, Atom) else atom.atom if isinstance(atom, Atoms) else None for atom in collection)
	Misc.raise_if(None in atoms, TypeError('One or more atoms is not an Atom instance or an Atoms instance'))
	return sorted(atoms, key=lambda atom: atom[attribute], reverse=reverse)
