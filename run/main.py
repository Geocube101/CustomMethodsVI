import sys
import time

from Table import Table2D
from Stream import LinqStream
from Decorators import *


@Concurrent
def concurrent():
	time.sleep(1)
	print(2)
	return


if __name__ == '__main__':
	# table: Table2D = Table2D()
	# table.add_rows(5, None)
	# table.add_columns(5, None)
	# table[:, 'A':'C'] = table
	# print(table)

	concurrent()
	print(1)
