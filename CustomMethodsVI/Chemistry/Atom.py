from __future__ import annotations

import typing

from ..Chemistry import Compound
from ..Chemistry import util


class Atom:
	def __init__(self, info: dict[str, [int | float | str]]):
		self.__atom_info: tuple[str, ...] = tuple(x.replace(' ', '_') for x in info.keys())

		for key, value in info.items():
			setattr(self, key.replace(' ', '_'), value)

	def __eq__(self, other: Atom) -> bool:
		return self.proton_count() == other.proton_count() if type(other) is type(self) else NotImplemented

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return self['Symbol']

	def __mul__(self, other: int) -> Atoms:
		if type(other) is not int:
			return NotImplemented
		else:
			return Atoms(self, other)

	def __rmul__(self, other: int) -> Atoms:
		if type(other) is not int:
			return NotImplemented
		else:
			return Atoms(self, other)

	def __add__(self, other: 'Atom | Atoms | Compound.Compound') -> 'Atoms | Compound.Compound':
		if type(other) not in (Atom, Atoms, Compound.Compound):
			return NotImplemented
		elif type(other) is Atoms:
			if other.atom() == self:
				return Atoms(self, other.count() + 1)
			else:
				return Compound.Compound(self, other)
		elif type(other) is Atom and self == other:
			return Atoms(self, 2)
		else:
			return Compound.Compound(self, other)

	def __hash__(self):
		return self.proton_count()

	def __getitem__(self, item: str) -> int | float | str:
		return getattr(self, item)

	def __iter__(self) -> typing.Generator:
		for name in self.__atom_info:
			info = getattr(self, name)
			yield name, info

	def proton_count(self) -> int:
		return self['Atomic_Number']

	def neutron_count(self) -> int:
		return int(self.mass()) - self.proton_count()

	def valence_count(self) -> int:
		valence: int | str = self['Group']
		return valence % 10 if type(valence) is int else 0

	def mass(self) -> float:
		return self['Atomic_Weight']

	def electronegativity(self) -> float:
		return self['Electronegativity']


class Atoms:
	def __init__(self, atom: Atom, count: int):
		if type(atom) is not Atom:
			raise TypeError(f'Cannot convert "{atom}" (type {type(atom).__name__}) to Atom.Atom')

		self.__atom = atom
		self.__count = count

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return str(self.__atom) if self.__count == 1 else str(self.__atom) + util.convert_int_to_subscript_str(self.__count)

	def __mul__(self, other: int) -> Atoms:
		if type(other) is not int:
			return NotImplemented
		else:
			return Atoms(self.__atom, self.__count * other)

	def __rmul__(self, other: int) -> Atoms:
		if type(other) is not int:
			return NotImplemented
		else:
			return Atoms(self.__atom, self.__count * other)

	def __add__(self, other: 'Atom | Atoms | Compound.Compound') -> 'Atoms | Compound.Compound':
		if type(other) not in (Atom, Atoms, Compound.Compound):
			return NotImplemented
		elif type(other) is Atoms:
			if other.atom() == self:
				return Atoms(self.__atom, self.__count + other.__count)
			else:
				return Compound.Compound(self, other)
		elif type(other) is Atom and other == self.__atom:
			return Atoms(self.__atom, self.__count + 1)
		else:
			return Compound.Compound(self, other)

	def mass(self) -> float:
		return self.__atom.mass() * self.__count

	def atom(self) -> Atom:
		return self.__atom

	def count(self) -> int:
		return self.__count


def sort(collection: typing.Iterable[Atom | Atoms], attribute: str, reverse: bool = False) -> tuple[Atom, ...]:
	atoms: tuple[Atom, ...] = tuple(atom if type(atom) is Atom else atom.atom() for atom in collection)
	return tuple(sorted(atoms, key=lambda atom: atom[attribute], reverse=reverse))


def sort_map(collection: typing.Iterable[Atom | Atoms], attribute: str, reverse: bool = False) -> dict[Atom, typing.Any]:
	atoms: tuple[Atom, ...] = tuple(atom if type(atom) is Atom else atom.atom() for atom in collection)
	attributes: dict[typing.Any, Atom] = {atom[attribute]: atom for atom in atoms}
	sorted_attrs: tuple[typing.Any, ...] = tuple(sorted(attributes.keys(), reverse=reverse))
	return {attributes[attr]: attr for attr in sorted_attrs}


def getattribute(collection: typing.Iterable[Atom | Atoms], attribute: str) -> tuple[typing.Any, ...]:
	atoms: tuple[Atom, ...] = tuple(atom if type(atom) is Atom else atom.atom() for atom in collection)
	return tuple(atom[attribute] for atom in atoms)
