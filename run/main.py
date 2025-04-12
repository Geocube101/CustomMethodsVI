import time
import math
import typing

import CustomMethodsVI.Misc
from CustomMethodsVI.Math.Plotter import *
from CustomMethodsVI.Stream import StringStream
from Stream import ByteStream

if __name__ == '__main__':
	# print(LoggingDirectory(r'C:\Users\geoga\AppData\Roaming\SpaceEngineers').logfiles())

	# plotter = Plot2D()
	# plotter.show()

	ss = StringStream()
	ss.write('Hello World')
	print(ss.read())