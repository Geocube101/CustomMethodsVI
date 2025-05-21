from CustomMethodsVI.FileSystem import *
from CustomMethodsVI.Grammar import Grammar

if __name__ == '__main__':
	# print(LoggingDirectory(r'C:\Users\geoga\AppData\Roaming\SpaceEngineers').logfiles())
	g = Grammar({'S', 'X', 'Y', 'Z', 'M', 'N'}, {'a', 'b'}, 'S', {
		'S': {('X', 'Y')},
		'X': {'a'},
		'Y': {'Z', 'b'},
		'Z': {'M'},
		'M': {'N'},
		'N': {'a'}
	})
	print(('a', 'a', 'b') in g)
