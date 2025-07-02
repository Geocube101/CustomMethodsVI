from CustomMethodsVI.Stream import ByteStream

if __name__ == '__main__':
	# print(LoggingDirectory(r'C:\Users\geoga\AppData\Roaming\SpaceEngineers').logfiles())
	s = ByteStream()
	s.write(b'\x00\x01')
	print(s.read(2))