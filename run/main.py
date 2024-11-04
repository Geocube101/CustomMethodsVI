import sys

from Table import Table2D
from Stream import LinqStream

if __name__ == '__main__':
	# table: Table2D = Table2D()
	# table.add_rows(5, None)
	# table.add_columns(5, None)
	# table[:, 'A':'C'] = table
	# print(table)

	linq = LinqStream((1, 2, 3, 4, 5))
	print(linq.select(lambda i: i * 2).sort(reverse=True).count())
