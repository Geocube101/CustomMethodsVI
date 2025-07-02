import typing

from ..Chemistry import Atom
from ..Chemistry import util


class Compound:
	def __init__(self, *atoms):
		self.__elements: list[Atom.Atoms] = []

		for atom in atoms:
			atom: Atom.Atom | Atom.Atoms | Compound

			if type(atom) is Atom.Atom:
				self.__elements.append(Atom.Atoms(atom, 1))
			elif type(atom) is Atom.Atoms:
				self.__elements.append(atom)
			elif type(atom) is Compound:
				self.__elements.extend(atom.__elements)
			else:
				raise TypeError(f'Cannot convert "{atom}" (type {type(atom).__name__}) to Compound.Compound')

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return ''.join(str(elem) for elem in self.__elements)

	def __mul__(self, other: int) -> 'Compounds':
		if type(other) is not int:
			return NotImplemented
		else:
			return Compounds(self, other)

	def __rmul__(self, other: int) -> 'Compounds':
		if type(other) is not int:
			return NotImplemented
		else:
			return Compounds(self, other)

	def __add__(self, other: 'Atom.Atom | Atom.Atoms | Compound.Compound') -> 'Compound':
		if type(other) not in (Atom.Atom, Atom.Atoms, Compound):
			return NotImplemented
		else:
			return Compound(*self.__elements, other)

	def __getitem__(self, item: 'str | int | Atom.Atom') -> 'Atom.Atoms':
		if type(item) is str:
			for atom in self.__elements:
				if atom.atom().Name == item or atom.atom().Symbol == item:
					return atom
			raise KeyError(f'No atom with name or symbol: {item}')
		elif type(item) is int:
			for atom in self.__elements:
				if atom.atom().proton_count() == item:
					return atom
			raise KeyError(f'No atom with atomic number: {item}')
		elif type(item) is Atom.Atom:
			for atom in self.__elements:
				if atom.atom() == item:
					return atom
			raise KeyError(f'No atom: {item}')
		else:
			return NotImplemented

	def __getattr__(self, item: 'str | int | Atom.Atom') -> 'Atom.Atoms':
		return self[item]

	def normalize(self) -> None:
		mapping: dict[Atom.Atom, int] = {}
		order: list[Atom.Atom] = []

		for atoms in self.__elements:
			if atoms.atom() not in mapping:
				mapping[atoms.atom()] = atoms.count()
			else:
				mapping[atoms.atom()] += atoms.count()

			if atoms.atom() not in order:
				order.append(atoms.atom())

		self.__elements.clear()

		for atom in order:
			self.__elements.append(Atom.Atoms(atom, mapping[atom]))

	def mass(self) -> float:
		return sum(elem.mass() for elem in self.__elements)

	def valence_count(self) -> float:
		return sum(atoms.atom().valence_count() * atoms.count() for atoms in self.__elements if atoms.atom().valence_count() >= 0)

	def calc_mass_to_moles(self) -> tuple[float]:
		import Equations
		return tuple(Equations.calc_gram_to_mol(elem.mass(), elem.atom()) for elem in self.__elements)

	def elements(self) -> 'tuple[Atom.Atoms, ...]':
		return tuple(self.__elements)

	def atoms(self) -> 'tuple[Atom.Atom, ...]':
		atoms_list: list[Atom.Atom] = []

		for atoms in self.__elements:
			atoms_list.extend([atoms.atom()] * atoms.count())

		return tuple(atoms_list)

	def normalized(self) -> 'Compound':
		copy: Compound = Compound(self)
		copy.normalize()
		return copy


class Compounds:
	def __init__(self, compound: Compound, count: int):
		self.__compound: Compound = compound if type(compound) is Compound else Compound(compound)
		self.__count = count

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		return str(self.__compound) if self.__count == 1 else f'{self.__count}({self.__compound})'

	def __mul__(self, other: int) -> 'Compounds':
		if type(other) is not int:
			return NotImplemented
		else:
			return Compounds(self.__compound, self.__count * other)

	def __rmul__(self, other: int) -> 'Compounds':
		if type(other) is not int:
			return NotImplemented
		else:
			return Compounds(self.__compound, self.__count * other)

	def mass(self) -> float:
		return self.__compound.mass() * self.__count

	def compound(self) -> Compound:
		return self.__compound

	def count(self) -> int:
		return self.__count
