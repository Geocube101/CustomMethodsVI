import sys
import traceback
import typing

from tkinter.filedialog import askopenfilename

from CustomMethodsVI.Assembly.Arm32 import Assembler
from CustomMethodsVI.Math.Based import BaseN
from CustomMethodsVI.FileSystem import File


def get_input_question(prompt: str) -> bool:
	yes: tuple[str, ...] = ('y', 'yes', 't', 'true', '1')
	no: tuple[str, ...] = ('n', 'no', 'f', 'false', '0')

	try:
		while True:
			ans: str = input(prompt).lower()

			if ans in yes:
				return True
			elif ans in no:
				return False
			else:
				print('Unknown input response')
	except (SystemExit, KeyboardInterrupt):
		return False


if __name__ == '__main__':
	is_encoding: bool = get_input_question('Encoding Instruction(s)? (Y/N): ')
	from_file: bool = get_input_question('Read Instructions From File? (Y/N): ')
	outfile: typing.Optional[File] = None
	input_instructions: list[str] = []
	output_assembly: list[int] = []

	if from_file:
		filepath: str = askopenfilename(filetypes=[('Text Files', '.txt')], title='Input Assembly x32 File')

		if filepath is None:
			sys.exit(1)

		file: File = File(filepath)

		if not file.exists():
			input('The specified file does not exist')
			sys.exit(2)

		outfile = File(file.filepath() + '.out')

		with file.open('r') as fin:
			input_instructions.extend(y for x in fin.readlines() if len(y := x.strip()) > 0)
	else:
		print('[ Assembly Input ]')
		instruction: str = ''

		while len(instruction := input(' > ')) > 0:
			if is_encoding:
				input_instructions.append(instruction)
			elif instruction.startswith('0x'):
				output_assembly.append(int(instruction[2:], 16))
			elif instruction.startswith('0o'):
				output_assembly.append(int(instruction[2:], 8))
			elif instruction.startswith('0b'):
				output_assembly.append(int(instruction[2:], 2))
			else:
				output_assembly.append(int(instruction))

	try:
		if is_encoding:
			print('ENCODE\n')
			encoded: tuple[int, ...] = Assembler.encode(input_instructions)
			binary: BaseN = BaseN(2)
			payload: bytes = b''

			for i, line in enumerate(input_instructions):
				instr: int = encoded[i]
				output_assembly.append(instr)
				payload += instr.to_bytes(4, sys.byteorder)
				print(f'"{line}" ->\n ... {hex(instr)[2:].upper().rjust(8, '0')} {str(instr).rjust(10, "0")}, {str(binary.convert(instr)).rjust(32, "0")}, {instr.bit_length()}\n')

			if from_file and outfile is not None:
				with outfile.open('wb') as fout:
					fout.write(payload)

		if from_file and not is_encoding:
			with outfile.open('rb') as fin:
				data: bytes = fin.read()
				output_assembly.extend(int.from_bytes(data[i:i + 4], sys.byteorder) for i in range(0, len(data), 4))

		print('\nDECODE\n')
		decoded: tuple[str, ...] = Assembler.decode(output_assembly)

		for i, instr in enumerate(output_assembly):
			line: str = decoded[i]
			print(f'"{instr}" ->\n ... {line}\n')

		print('\nBREAKDOWN\n')
		for instr in output_assembly:
			Assembler.print_breakdown(instr)
	except (KeyboardInterrupt, SystemExit):
		pass
	except ValueError as err:
		input(f'Malformed Arm32 command:\n ... "{str(err)}"')
	except AssertionError as err:
		input(f'Standard IO Error\n ... "{str(err)}"')
	except Exception as err:
		input(f'Fatal Exception\n ... \n{"\n".join(traceback.format_exception(err))}')
