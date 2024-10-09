import typing
import json
import bs4
import requests
import os
import atexit

import CustomMethodsVI.Chemistry.Atom as Atom


class __PTABLE__:
	__TABLE_FILE: str = 'periodic_table.json'
	__MAX_ATOMIC_NUMBER = 118

	def __init__(self):
		if os.path.isfile(__PTABLE__.__TABLE_FILE):
			with open(__PTABLE__.__TABLE_FILE, 'r') as f:
				elements: dict[str, dict[str, int | float | str]] = json.JSONDecoder().decode(f.read())

				if len(elements) < __PTABLE__.__MAX_ATOMIC_NUMBER:
					self.__elements: dict[str, Atom.Atom] = self.update()
				else:
					self.__elements: dict[str, Atom.Atom] = {}

					for k, v in elements.items():
						self.__elements[k] = Atom.Atom(v)
		else:
			self.__elements = self.update()

		atexit.register(self.store)

	def __getitem__(self, item: str | int) -> Atom.Atom:
		if type(item) is str:
			if item in self.__elements:
				return self.__elements[item]
			else:
				raise KeyError(f'No element with name: {item}')
		elif type(item) is int:
			for name, atom in self.__elements.items():
				if atom.proton_count() == item:
					return atom

			raise KeyError(f'No element with atomic number: {item}')

	def __getattr__(self, item: str | int):
		return self[item]

	def __iter__(self) -> tuple[str, Atom.Atom]:
		for name, atom in self.__elements.items():
			yield name, atom

	def store(self) -> None:
		elements: dict[str, dict[str, int | float | str]] = {}

		for name, atom in self.__elements.items():
			elements[name] = dict(atom)

		with open(__PTABLE__.__TABLE_FILE, 'w') as f:
			f.write(json.JSONEncoder().encode(elements))

	def update(self) -> dict[str, Atom.Atom]:
		headers: dict[str, str] = {'User-Agent': 'Mozilla/5.0'}
		internal_elements: dict[str, Atom.Atom] = {}

		for atomic_number in range(1, 119):
			response: requests.Response = requests.get(f'https://periodictable.com/Elements/{atomic_number:03}/data.html', headers=headers)
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
			internal_elements[atom['Symbol']] = atom
			print(f'Updated element {atomic_number:03}: \"{atom.Name}\" ({round(atomic_number / 118 * 100):02}%)')

		return internal_elements

	def unpack_into(self, mapping: dict[str, Atom.Atom]) -> None:
		for name, atom in self.__elements.items():
			mapping[atom['Symbol']] = atom


PTable: __PTABLE__ = __PTABLE__()
