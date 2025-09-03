from __future__ import annotations

from .. import Chemistry
from .. import Exceptions
from .. import Misc
from .. import Stream


class Compound:
	"""
	Class representing a grouping of different elements
	"""

	def __init__(self, *atoms: Chemistry.Atom.Atom | Chemistry.Atom.Atoms | Compound, count: int = 1):
		"""
		Class representing a grouping of different elements
		- Constructor -
		:param atoms: The atoms or compounds that make up this compound
		:raises InvalidArgumentException: If any atom is not an Atom instance, Atoms instance, or Compound instance
		:raises InvalidArgumentException: If 'count' is not an integer
		:raises ValueError: If 'count' is negative
		"""

		Misc.raise_ifn(isinstance(count, int), Exceptions.InvalidArgumentException(Compound.__init__, 'count', type(count), (int,)))
		Misc.raise_ifn((count := int(count)) > 0, ValueError('Count cannot be negative'))
		self.__atoms__: list[Chemistry.Atom.Atoms | Compound] = []
		self.__count__: int = int(count)

		for atom in atoms:
			if isinstance(atom, Chemistry.Atom.Atom):
				self.__atoms__.append(Chemistry.Atom.Atoms(atom, 1))
			elif isinstance(atom, Chemistry.Atom.Atoms) and atom.count >= 1:
				self.__atoms__.append(atom)
			elif isinstance(atom, Compound):
				self.__atoms__.append(atom)
			elif not isinstance(atom, (Chemistry.Atom.Atom, Chemistry.Atom.Atoms, Compound)):
				raise Exceptions.InvalidArgumentException(Compound.__init__, 'atoms', type(atom), (Chemistry.Atom.Atom, Chemistry.Atom.Atoms, Compound))

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		msg: str = ''.join(f'({elem})' if isinstance(elem, Compound) else str(elem) for elem in self.__atoms__)
		return msg if self.__count__ == 1 else f'({msg}){Chemistry.util.convert_int_to_subscript_str(self.__count__)}'

	def __eq__(self, other: Compound):
		return isinstance(other, Compound) and self.__atoms__ == other.__atoms__ and self.__count__ == other.__count__

	def __mul__(self, n: int) -> Compound:
		"""
		Multiplies this compound 'n' times
		:param n: The number of times to multiply this grouping by
		:return: The multiplied compound
		"""

		if not isinstance(n, int):
			return NotImplemented
		elif (n := int(n)) < 0:
			raise ValueError('Multiplier cannot be negative')
		else:
			return Compound(*self.__atoms__, count=self.__count__ * int(n))

	def __rmul__(self, n: int) -> Compound:
		"""
		Multiplies this compound 'n' times
		:param n: The number of times to multiply this grouping by
		:return: The multiplied compound
		"""

		return self * n

	def __matmul__(self, n: int) -> Compound:
		"""
		Multiplies this compound's elements 'n' times
		:param n: The number of times to multiply this grouping by
		:return: The multiplied compound
		"""

		if not isinstance(n, int):
			return NotImplemented
		elif (n := int(n)) < 0:
			raise ValueError('Multiplier cannot be negative')
		else:
			return Compound(*[atoms * int(n) for atoms in self.__atoms__])

	def __rmatmul__(self, n: int) -> Compound:
		"""
		Multiplies this compound's elements 'n' times
		:param n: The number of times to multiply this grouping by
		:return: The multiplied compound
		"""

		return self @ n

	def __add__(self, other: Chemistry.Atom.Atom | Chemistry.Atom.Atoms | Compound) -> Compound:
		"""
		Adds either another atom, atom group, or compound to this compound
		:param other: The other atom, atom group, or compound
		:return: The resulting compound
		"""

		return Compound(*self.__atoms__, count=self.__count__ + other.__count__) if isinstance(other, Compound) and other.__atoms__ == self.__atoms__ else Compound(self, other) if isinstance(other, (Chemistry.Atom.Atom, Chemistry.Atom.Atoms, Compound)) else NotImplemented

	def __radd__(self, other: Chemistry.Atom.Atom | Chemistry.Atom.Atoms | Compound) -> Compound:
		"""
		Adds this compound to either another atom, atom group, or compound
		:param other: The other atom, atom group, or compound
		:return: The resulting compound
		"""

		return Compound(other, self) if isinstance(other, (Chemistry.Atom.Atom, Chemistry.Atom.Atoms, Compound)) else NotImplemented

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

	def __getitem__(self, key: int | Chemistry.Atom.Atom) -> Chemistry.Atom.Atoms:
		"""
		Gets the atom group in this compound by index if 'key' is an integer
		Gets the combined atom group in this compound by symbol if 'key' is an Atom instance
		:param key: The group index or atomic element
		:return: The atom group
		:raises IndexError: If the index is out of bounds
		:raises TypeError: If the key is not an integer or Atom instance
		"""

		if isinstance(key, int):
			return self.__atoms__[int(key)]
		elif isinstance(key, Chemistry.Atom.Atom):
			return Chemistry.Atom.Atoms(key, Stream.LinqStream(self.__atoms__).filter(lambda atoms: atoms.atom == key).transform(lambda atoms: atoms.count).sum())
		else:
			raise TypeError(f'Compound indices must be either an integer or an Atom instance, got \'{type(key).__name__}\'')

	def normalize(self) -> None:
		"""
		Normalizes this compound
		Example: H6O2 -> H3O
		"""

		if len(self.__atoms__) == 0:
			return

		sort_order: list[int] = sorted(atom.count for atom in self.__atoms__ if isinstance(atom, Chemistry.Atom.Atoms))
		smallest: int = ...

		if 1 in sort_order:
			return

		for small in sort_order:
			if all(x % small == 0 for x in sort_order):
				smallest = small
				break

		if smallest is ...:
			return

		for i, atoms in enumerate(self.__atoms__):
			if isinstance(atoms, Chemistry.Atom.Atoms):
				self.__atoms__[i] = Chemistry.Atom.Atoms(atoms.atom, atoms.count // smallest)
			else:
				self.__atoms__[i].normalize()

	def normalized(self) -> Compound:
		"""
		Normalizes this compound
		Example: H6O2 -> H3O
		:return: The normalized compound
		"""

		copy: Compound = Compound(self)
		copy.normalize()
		return copy

	@property
	def count(self) -> int:
		"""
		:return: The subscript count of this compound
		"""

		return self.__count__

	@property
	def mass(self) -> float:
		"""
		:return: The total mass of this compound
		"""

		return sum(elem.mass for elem in self.__atoms__) * self.__count__

	@property
	def valence_count(self) -> float:
		"""
		:return: The valence count of this compound
		"""

		return sum(atoms.valence_count if isinstance(atoms, Compound) else (atoms.atom.valence_count * atoms.count) for atoms in self.__atoms__ if atoms.atom.valence_count >= 0)

	@property
	def elements(self) -> tuple[Chemistry.Atom.Atoms | Compound, ...]:
		"""
		:return: The individual element terms in this compound
		"""

		return tuple(self.__atoms__)

	@property
	def atoms(self) -> set[Chemistry.Atom.Atoms]:
		"""
		:return: The atomic element groups in this compound
		"""

		atoms: set[Chemistry.Atom.Atoms] = set()

		for atom in self.__atoms__:
			if isinstance(atom, Compound):
				atoms.update(x * self.__count__ for x in atom.atoms)
			else:
				atoms.add(atom * self.__count__)

		return atoms
