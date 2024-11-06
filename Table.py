from __future__ import annotations

import typing
import collections


class Table2D(typing.Sized):
	@staticmethod
	def __column_index_to_flat_index__(col: str) -> int:
		col = str(col).upper()
		values: tuple[str, ...] = tuple('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
		index = 0

		for c in col:
			if c not in values:
				raise ValueError(f'Unexpected column letter \'{c}\'')

			index = index * 10 + values.index(c)

		return index

	@classmethod
	def shaped(cls, iterable: typing.Iterable, shape: tuple[int, int]) -> Table2D:
		w, h = shape
		size: int = w * h
		flattened: list = list(iterable)
		flattened.extend(None for _ in range(len(flattened), size))
		nested: list[list] = []

		for y in range(h):
			nested.append([flattened[i + (w * y)] for i in range(w)])

		instance = cls()
		instance.__cells__ = nested
		return instance

	@classmethod
	def fromarray(cls, nested: typing.Iterable) -> Table2D:
		pass

	def __init__(self):
		self.__cells__: list[list[typing.Any]] = []
		self.__allowed_types__: list[type] = []

	def __setitem__(self, key: tuple[int, int | str] | slice, value) -> None:
		w, h = self.dimensions()

		if len(self.__allowed_types__) and value is not None and value is not ... and not isinstance(value, tuple(self.__allowed_types__)):
			raise TypeError(f'The specified value is not an allowed type.\nExpected one of: ({", ".join(str(t) for t in self.__allowed_types__)})')

		if isinstance(key, tuple):
			assert len(key) == 2, 'Expected 2D coordinate pair'
			p1, p2 = key

			if isinstance(p1, int) and isinstance(p2, int):
				self.__cells__[p1][p2] = value
			elif isinstance(p1, int) and isinstance(p2, slice):
				start: int = Table2D.__column_index_to_flat_index__(p2.start) if isinstance(p2.start, str) else int(p2.start) if isinstance(p2.start, int) else 0
				stop: int = Table2D.__column_index_to_flat_index__(p2.stop) if isinstance(p2.stop, str) else int(p2.stop) if isinstance(p2.stop, int) else w
				step: int = int(p2.step) if isinstance(p2.step, int) else 1

				for i in range(start, stop, step):
					self.__cells__[p1][i] = value
			elif isinstance(p1, slice) and isinstance(p2, (int, str)):
				start: int = Table2D.__column_index_to_flat_index__(p1.start) if isinstance(p1.start, str) else int(p1.start) if isinstance(p1.start, int) else 0
				stop: int = Table2D.__column_index_to_flat_index__(p1.stop) if isinstance(p1.stop, str) else int(p1.stop) if isinstance(p1.stop, int) else h
				step: int = int(p1.step) if isinstance(p1.step, int) else 1
				p2: int = Table2D.__column_index_to_flat_index__(p2) if isinstance(p2, str) else p2

				for i in range(start, stop, step):
					self.__cells__[i][p2] = value
			elif isinstance(p1, slice) and isinstance(p2, slice):
				start1: int = Table2D.__column_index_to_flat_index__(p1.start) if isinstance(p1.start, str) else int(p1.start) if isinstance(p1.start, int) else 0
				stop1: int = Table2D.__column_index_to_flat_index__(p1.stop) if isinstance(p1.stop, str) else int(p1.stop) if isinstance(p1.stop, int) else h
				step1: int = int(p1.step) if isinstance(p1.step, int) else 1

				start2: int = Table2D.__column_index_to_flat_index__(p2.start) if isinstance(p2.start, str) else int(p2.start) if isinstance(p2.start, int) else 0
				stop2: int = Table2D.__column_index_to_flat_index__(p2.stop) if isinstance(p2.stop, str) else int(p2.stop) if isinstance(p2.stop, int) else w
				step2: int = int(p2.step) if isinstance(p2.step, int) else 1

				for i in range(start1, stop1, step1):
					for j in range(start2, stop2, step2):
						self.__cells__[i][j] = value
			elif isinstance(p1, int) and isinstance(p2, str):
				self.__cells__[p1][Table2D.__column_index_to_flat_index__(p2)] = value
			else:
				raise TypeError(f'Table2D tuple index must be a tuple[slice | int, slice | int | str]; got \'({type(p1)}, {type(p2)})\'')
		elif isinstance(key, slice):
			start: int = int(key.start) if isinstance(key.start, int) else 0
			stop: int = int(key.stop) if isinstance(key.stop, int) else len(self)
			step: int = int(key.step) if isinstance(key.step, int) else 1

			for i in range(start, stop, step):
				row, col = divmod(i, w)
				self.__cells__[row][col] = value
		elif isinstance(key, int):
			row, col = divmod(key, w)
			self.__cells__[row][col] = value
		else:
			raise TypeError(f'Table2D index must be a tuple[slice | int, slice | int | str], int, or slice; got \'{type(key)}\'')

	def __len__(self) -> int:
		return len(self.__cells__[0]) * len(self.__cells__)

	def __getitem__(self, key: int | slice | tuple[int | slice, int | slice | str]) -> typing.Any | Table2D:
		w, h = self.dimensions()

		if isinstance(key, tuple):
			assert len(key) == 2, 'Expected 2D coordinate pair'
			p1, p2 = key

			if isinstance(p1, int) and isinstance(p2, int):
				return self.__cells__[p1][p2]
			elif isinstance(p1, int) and isinstance(p2, slice):
				start: int = Table2D.__column_index_to_flat_index__(p2.start) if isinstance(p2.start, str) else int(p2.start) if isinstance(p2.start, int) else 0
				stop: int = Table2D.__column_index_to_flat_index__(p2.stop) if isinstance(p2.stop, str) else int(p2.stop) if isinstance(p2.stop, int) else w
				step: int = int(p2.step) if isinstance(p2.step, int) else 1
				return Table2D.shaped((self.__cells__[p1][i] for i in range(start, stop, step)), (w, h))
			elif isinstance(p1, slice) and isinstance(p2, (int, str)):
				start: int = Table2D.__column_index_to_flat_index__(p1.start) if isinstance(p1.start, str) else int(p1.start) if isinstance(p1.start, int) else 0
				stop: int = Table2D.__column_index_to_flat_index__(p1.stop) if isinstance(p1.stop, str) else int(p1.stop) if isinstance(p1.stop, int) else h
				step: int = int(p1.step) if isinstance(p1.step, int) else 1
				p2: int = Table2D.__column_index_to_flat_index__(p2) if isinstance(p2, str) else p2
				return Table2D.shaped((self.__cells__[i][p2] for i in range(start, stop, step)), (w, h))
			elif isinstance(p1, slice) and isinstance(p2, slice):
				start1: int = Table2D.__column_index_to_flat_index__(p1.start) if isinstance(p1.start, str) else int(p1.start) if isinstance(p1.start, int) else 0
				stop1: int = Table2D.__column_index_to_flat_index__(p1.stop) if isinstance(p1.stop, str) else int(p1.stop) if isinstance(p1.stop, int) else h
				step1: int = int(p1.step) if isinstance(p1.step, int) else 1

				start2: int = Table2D.__column_index_to_flat_index__(p2.start) if isinstance(p2.start, str) else int(p2.start) if isinstance(p2.start, int) else 0
				stop2: int = Table2D.__column_index_to_flat_index__(p2.stop) if isinstance(p2.stop, str) else int(p2.stop) if isinstance(p2.stop, int) else w
				step2: int = int(p2.step) if isinstance(p2.step, int) else 1

				return Table2D.shaped(([self.__cells__[i][j] for j in range(start2, stop2, step2)] for i in range(start1, stop1, step1)), (w, h))
			elif isinstance(p1, int) and isinstance(p2, str):
				return self.__cells__[p1][Table2D.__column_index_to_flat_index__(p2)]
			else:
				raise TypeError(f'Table2D tuple index must be a tuple[slice | int, slice | int | str]; got \'({type(p1)}, {type(p2)})\'')
		elif isinstance(key, slice):
			start: int = int(key.start) if isinstance(key.start, int) else 0
			stop: int = int(key.stop) if isinstance(key.stop, int) else len(self)
			step: int = int(key.step) if isinstance(key.step, int) else 1
			values: list = []

			for i in range(start, stop, step):
				row, col = divmod(i, w)
				values.append(self.__cells__[row][col])

			return Table2D.shaped(values, (w, h))
		elif isinstance(key, int):
			row, col = divmod(key, w)
			return self.__cells__[row][col]
		else:
			raise TypeError(f'Table2D index must be a tuple[slice | int, slice | int | str], int, or slice; got \'{type(key)}\'')

	def __str__(self) -> str:
		w, h = self.dimensions()

		if w == 0 or h == 0:
			return '[//]'

		row_heights: collections.OrderedDict[int, int] = collections.OrderedDict()
		col_widths: collections.OrderedDict[int, int] = collections.OrderedDict()
		str_cells: list[list[list[str]]] = []

		for y, row in enumerate(self.__cells__):
			str_row: list[list[str]] = []
			row_height: int = 0

			for x, cell in enumerate(row):
				str_cell: str = repr(cell)
				lines: list[str] = str_cell.split('\n')
				str_row.append(lines)
				width: int = max(len(line) for line in lines)
				row_height = max(row_height, len(lines))
				col_widths[x] = max(col_widths[x], width) if x in col_widths else width

			str_cells.append(str_row)
			row_heights[y] = row_height

		table_str: str = ''

		for y, row in enumerate(str_cells):
			height: int = row_heights[y]
			row_str: list[list[str]] = [[] for _ in range(height)]
			footer: str = f'└{"┴".join(("─" * (width + 2)) for width in col_widths.values())}┘\n' if y + 1 >= h else f'├{"┼".join(("─" * (width + 2)) for width in col_widths.values())}┤\n'
			header: str = '' if y > 0 else f'┌{"┬".join(("─" * (width + 2)) for width in col_widths.values())}┐\n'

			for x, cell in enumerate(row):
				width: int = col_widths[x]
				cell.extend((' ' * width) for _ in range(len(cell), height))

				for i in range(height):
					line: str = cell[i].rjust(width, ' ') if i < len(cell) else (' ' * width)
					row_str[i].append(f'│ {line} ')

			line: str = '\n'.join(''.join(line) + '│' for line in row_str)
			table_str += header + line + '\n' + footer

		return table_str

	def __repr__(self) -> str:
		w, h = self.dimensions()
		return f'<Table2D[{w}x{h}] object @ {hex(id(self))}>'

	def add_rows(self, n: int, fill_value: typing.Any = None) -> None:
		if len(self.__allowed_types__) and not isinstance(fill_value, tuple(self.__allowed_types__)):
			raise TypeError(f'The specified fill value is not an allowed type.\nExpected one of: ({", ".join(str(t) for t in self.__allowed_types__)})')

		w, _ = self.dimensions()
		self.__cells__.extend([fill_value for j in range(w)] for i in range(n))

	def add_columns(self, n: int, fill_value: typing.Any = None) -> None:
		if len(self.__allowed_types__) and not isinstance(fill_value, tuple(self.__allowed_types__)):
			raise TypeError(f'The specified fill value is not an allowed type.\nExpected one of: ({", ".join(str(t) for t in self.__allowed_types__)})')

		for row in self.__cells__:
			row.extend(fill_value for _ in range(n))

	def truncate(self) -> None:
		index: int = len(self.__cells__) - 1

		while index >= 0 and all(cell is None or cell is ... for cell in self.__cells__[index]):
			del self.__cells__[index]
			index -= 1

		if index < 0:
			return

		index: int = max(row.index(None) if None in row else row.index(...) if ... in row else -1 for row in self.__cells__)

		for row in self.__cells__:
			del row[index:]

	def dimensions(self, width: typing.Optional[int] = ..., height: typing.Optional[int] = ...) -> None | tuple[int, int]:
		if (width is ... or width is None) and (height is ... or height is None):
			h: int = len(self.__cells__)
			return 0 if h == 0 else len(self.__cells__[0]), h
		else:
			w, h = self.dimensions()
			width = w if width is None or width is ... else int(width)
			height = h if height is None or height is ... else int(height)

			if width < 0 or height < 0:
				raise ValueError('Negative dimension value')
			elif width == 0 or height == 0:
				self.__cells__.clear()
			else:
				del self.__cells__[:height]

				for col in self.__cells__:
					del col[:width]

	def get_column(self, index_or_letter: str | int) -> tuple[typing.Any, ...]:
		width: int = self.dimensions()[0]
		index: int

		if isinstance(index_or_letter, str):
			index = Table2D.__column_index_to_flat_index__(index_or_letter)
		elif isinstance(index_or_letter, int):
			index = int(index_or_letter)
			index = width + index if index < 0 else index
		else:
			raise TypeError('Specified index or letter is invalid')

		if index >= width:
			raise IndexError(f'Column index \'{index}\' is out of range')

		return tuple(row[index] for row in self.__cells__)

	def get_row(self, index: int) -> tuple[typing.Any, ...]:
		if not isinstance(index, int):
			raise TypeError('Specified index or letter is invalid')
		elif (index := int(index)) >= self.dimensions()[1]:
			raise IndexError(f'Row index \'{index}\' is out of range')

		return tuple(self.__cells__[index])

	def copy(self) -> Table2D:
		instance = Table2D()
		instance.__cells__ = [[cell for cell in row] for row in self.__cells__]
		return instance

	def truncated(self) -> Table2D:
		clone: Table2D = self.copy()
		clone.truncate()
		return clone

	def allow_types(self, type_: type | None, *types) -> Table2D:
		if type_ is None and len(types):
			raise ValueError('Types specified whilst clearing allowed types')
		elif type_ is None:
			self.__allowed_types__.clear()
		else:
			self.__allowed_types__.extend((type_, *types))

		return self
