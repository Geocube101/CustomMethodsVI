import sys

from CustomMethodsVI.Assembly.Arm32 import Assembler
from CustomMethodsVI.Math.Based import BaseN


if __name__ == '__main__':
	print('ENCODE\n')
	with open('../assemblyin.txt') as fin:
		with open('../assembly.out', 'wb') as fout:
			lines: list[str] = [y for x in fin.readlines() if len(y := x.strip()) > 0]
			encoded: tuple[int, ...] = Assembler.encode(lines)
			binary: BaseN = BaseN(2)
			payload: bytes = b''

			for i, line in enumerate(lines):
				instr: int = encoded[i]
				payload += instr.to_bytes(4, sys.byteorder)
				print(f'"{line}" ->\n ... {hex(instr)[2:].upper().rjust(8, '0')} {str(instr).rjust(10, "0")}, {str(binary.convert(instr)).rjust(32, "0")}, {instr.bit_length()}\n')
				# print(f'"{line}" {hex(instr)[2:].upper()}\n')

			fout.write(payload)

	print('\nDECODE\n')
	with open('../assembly.out', 'rb') as fin:
		data: bytes = fin.read()
		instructions: tuple[int, ...] = tuple(int.from_bytes(data[i:i + 4], sys.byteorder) for i in range(0, len(data), 4))
		decoded: tuple[str, ...] = Assembler.decode(instructions)

		for i, instr in enumerate(instructions):
			line: str = decoded[i]
			print(f'"{instr}" ->\n ... {line}\n')

	print('\nBREAKDOWN\n')
	Assembler.print_breakdown(0x12490AFF)
