from __future__ import annotations

import atexit
import bs4
import json
import os
import requests
import typing

from ..Chemistry import Atom
from .. import FileSystem


class __PTABLE__:
	"""
	Singleton class holding all atomic elements
	"""

	__SINGLETON: __PTABLE__ = ...
	__TABLE_FILE: str = 'periodic_table.json'
	__MAX_ATOMIC_NUMBER = 118

	def __new__(cls, *args, **kwargs) -> __PTABLE__:
		if __PTABLE__.__SINGLETON is ...:
			__PTABLE__.__SINGLETON = super().__new__(cls)

		return __PTABLE__.__SINGLETON

	def __init__(self):
		"""
		Singleton class holding all atomic elements
		- Constructor -
		"""

		home_dir: FileSystem.Directory = FileSystem.Directory(os.path.dirname(__file__))
		table_json: FileSystem.File = home_dir.file(__PTABLE__.__TABLE_FILE)
		self.__elements__: dict[str, Atom.Atom] = {}

		if table_json.exists():
			with table_json.open('r') as f:
				elements: dict[str, dict[str, int | float | str]] = json.JSONDecoder().decode(f.read())

				if len(elements) < __PTABLE__.__MAX_ATOMIC_NUMBER:
					self.update()
				else:
					for k, v in elements.items():
						self.__elements__[k] = Atom.Atom(v)
		else:
			self.update()

		atexit.register(self.store)

	def __getitem__(self, item: str | int) -> Atom.Atom:
		"""
		Gets an atomic element by either atomic name or atomic number
		:param item: The atomic name or number
		:return: The associated atomic element
		:raises KeyError: If no such element exists
		"""

		if type(item) is str:
			if item in self.__elements__:
				return self.__elements__[item]
			else:
				raise KeyError(f'No element with name: {item}')
		elif type(item) is int:
			for atom in self.__elements__.values():
				if atom.proton_count == item:
					return atom

			raise KeyError(f'No element with atomic number: {item}')

	def __getattr__(self, item: str | int):
		"""
		Gets an atomic element by either atomic name or atomic number
		:param item: The atomic name or number
		:return: The associated atomic element
		:raises KeyError: If no such element exists
		"""

		return self[item]

	def __iter__(self) -> typing.Iterator[tuple[str, Atom.Atom]]:
		"""
		:return: An iterator over all name element pairs
		"""

		for name, atom in self.__elements__.items():
			yield name, atom

	def store(self) -> None:
		"""
		Writes the contents of this periodic table back to its source file
		"""

		home_dir: FileSystem.Directory = FileSystem.Directory(os.path.dirname(__file__))
		table_json: FileSystem.File = home_dir.file(__PTABLE__.__TABLE_FILE)
		elements: dict[str, dict[str, int | float | str]] = {}

		for name, atom in self.__elements__.items():
			elements[name] = dict(atom)

		with table_json.open('w') as f:
			f.write(json.JSONEncoder().encode(elements))

	def update(self, *, print_updates: bool = False) -> None:
		"""
		Updates the internal listing of atomic elements from the internet
		Will also update 'Elements.py'
		:param print_updates: Whether to print updates to console
		:raises IOError: If downloading failed
		"""

		headers: dict[str, str] = {'User-Agent': 'Mozilla/5.0'}
		home_dir: FileSystem.Directory = FileSystem.Directory(os.path.dirname(__file__))
		elements_py: FileSystem.File = home_dir.file('Elements.py')
		lines: list[str] = ['from . import PeriodicTable', '']

		for atomic_number in range(1, __PTABLE__.__MAX_ATOMIC_NUMBER + 1):
			response: requests.Response = requests.get(f'https://periodictable.com/Elements/{atomic_number:03}/data.html', headers=headers)

			if not response.ok:
				raise IOError('Failed to download elements')

			parser: bs4.BeautifulSoup = bs4.BeautifulSoup(response.text, 'html.parser')
			rows: typing.Generator[bs4.Tag, typing.Any] = (tr for tr in parser.find_all('tr') if len(tr.find_all('td')) == 2)
			element_info: dict[str, int | float | str] = {}

			for row in rows:
				attribute: str
				value: str
				attribute, value = (td.text for td in row.find_all('td'))
				value = value.split(' ')[0].replace('×10', 'e').replace('[note]', '').rstrip('%')

				try:
					value_int: int = int(value)
					element_info[attribute] = value_int

					if attribute.startswith('%_'):
						element_info[f'percent_{attribute[2:]}'] = value_int
				except ValueError:
					try:
						value_float: float = float(value)
						element_info[attribute] = value_float

						if attribute.startswith('%_'):
							element_info[f'percent_{attribute[2:]}'] = value_float
					except ValueError:
						element_info[attribute] = value

						if attribute.startswith('%_'):
							element_info[f'percent_{attribute[2:]}'] = value

			atom: Atom.Atom = Atom.Atom(element_info)
			self.__elements__[atom.symbol] = atom
			lines.append(f'{atom.symbol} = PeriodicTable.PTable[{atom.proton_count}]')

			if print_updates:
				print(f'Updated element {atomic_number:03}: \"{atom.name}\" ({round(atomic_number / 118 * 100):02}%)')

		with elements_py.open('w') as f:
			f.write('\n'.join(lines))

	def unpack_into(self, mapping: dict[str, Atom.Atom]) -> None:
		"""
		Updates the specified dictionary with all elements from the periodic table
		:param mapping: The mapping to insert into
		"""

		for name, atom in self.__elements__.items():
			mapping[atom['Symbol']] = atom


PTable: __PTABLE__ = __PTABLE__()
"""
The periodic table singleton
"""
