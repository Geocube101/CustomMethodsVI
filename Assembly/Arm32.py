import typing

from collections import OrderedDict

from CustomMethodsVI.Math.Based import BaseN, BaseNumber


class Assembler:
	"""
	[Assembler] - Class for encoding and decoding assembly from Arm32 instruction set
	"""

	__DATA_PROCESSING__: tuple[str, ...] = (
		'AND',
		'EOR',
		'SUB',
		'RSB',
		'ADD',
		'ADC',
		'SBC',
		'RSC',
		'TST',
		'TEQ',
		'CMP',
		'CMN',
		'ORR',
		'MOV',
		'BIC',
		'MVN'
	)

	__MEMORY__: tuple[str, ...] = (
		'STR',
		'STRB',
		'LDR',
		'LDRB'
	)

	__BRANCH__: tuple[str, ...] = (
		'B',
		'BL'
	)

	__SHIFT_TYPES__: tuple[str, ...] = (
		'LSL',
		'LSR',
		'ASR',
		'ROR'
	)

	__CONDITIONS__: tuple[int, ...] = (
		'EQ',
		'NE',
		'CS',
		'CC',
		'MI',
		'PL',
		'VS',
		'VC',
		'HI',
		'LS',
		'GE',
		'LT',
		'GT',
		'LE',
		'AL'
	)

	@staticmethod
	def encode(assembly: typing.Iterable[str]) -> tuple[int, ...]:
		"""
		Encodes a set of assembly instructions to machine code
		:param assembly: (Iterable[str]) An iterable of assembly code lines to encode
		:return: (tuple[int]) The encoded 32-bit machine instructions
		"""

		def parse_value(val: str) -> int:
			if val.startswith('#0O'):
				return int(val[3:], 8)
			elif val.startswith('#0X'):
				return int(val[3:], 16)
			else:
				try:
					return int(val[1:], 10)
				except ValueError:
					raise ValueError(f'Invalid immediate \'{val}\'') from None

		def parse_register(val: str) -> int:
			if val == 'SP':
				return 13
			elif val == 'LR':
				return 14
			elif val == 'PC':
				return 15
			elif val == 'RA':
				return 0
			elif not (val := val[1:] if val.startswith('R') else val).isdigit():
				raise ValueError(f'Invalid register \'{val}\'')

			return int(val[1:]) if val.startswith('R') else int(val)

		output: list[int] = []
		labels: dict[str, int] = {}
		index: int = 0
		commands: tuple[str, ...] = (*Assembler.__DATA_PROCESSING__, *Assembler.__MEMORY__, *Assembler.__BRANCH__)
		assembly: list[str, ...] = list(assembly)

		for i, line in enumerate(assembly):
			if len(line.strip()) == 0:
				continue

			cmd: str
			args: str
			split_line: list[str] = line.split(maxsplit=1)
			command_indices: tuple[int, ...] = tuple(i for i, x in enumerate(split_line) if any(x.startswith(cmd) for cmd in commands))

			if len(command_indices) == 0:
				raise ValueError(f'Invalid command \'{split_line[0]}\'')
			elif command_indices[0] == 1:
				label, rest = split_line
				assembly[i] = rest
				labels[label] = i * 4

		while index < len(assembly):
			line: str = assembly[index]

			if len(line.strip()) == 0:
				index += 1
				continue

			cmd: str
			args: str
			cmd, args, *_ = line.split(maxsplit=1)
			cmd = cmd.upper()

			_args: list[str] = []
			_arg: str = ''
			controls: list[str] = ['\x00']

			for c in args:
				if c == ',' and len(controls) == 1:
					_args.append(_arg)
					_arg = ''
				elif c == '[':
					controls.append(c)
					_args.append(_arg)
					_arg = c
				elif c == ']':
					assert controls[-1] == '[', 'Unbalanced brackets'
					controls.pop()
					_arg += c
				elif c == ';':
					break
				else:
					_arg += c

			_args.append(_arg)
			args: tuple[str, ...] = tuple(y for y in (x.strip().upper() for x in _args) if len(y))
			encoded: int = 0

			if len(_found := tuple(x for x in Assembler.__DATA_PROCESSING__ if cmd.startswith(x))) > 0 and (full_cmd := sorted(_found, key=lambda c: len(c), reverse=True)[0]):
				_extra: str = cmd[len(full_cmd):]
				has_s: bool = _extra == 'S'
				cond_str: str = 'AL' if len(_extra) == 0 or has_s else _extra if not has_s else None
				assert cond_str in Assembler.__CONDITIONS__, f'Invalid condition \'{_extra}\''
				cond: int = Assembler.__CONDITIONS__.index(cond_str)
				cmd: int = Assembler.__DATA_PROCESSING__.index(full_cmd)
				rd, rn, *args = args
				Rn: int = parse_value(rn) if full_cmd == 'MOV' and rn.startswith('#') else parse_register(rn)
				Rd: int = parse_register(rd)
				src12: int = 0
				is_immediate: bool

				if len(args) == 1 and args[0].startswith('#'):
					value: int = parse_value(args[0])
					basen: BaseNumber = BaseN(2).convert(value)
					assert basen.precision() <= 8, 'Immediate operand is not 8-bit precision'
					binary: str = str(basen).rjust(8, '0')
					is_immediate = True
					shamt: int = len(binary) - binary.rindex('1') - 1
					shamt = shamt if shamt % 2 == 0 else shamt - 1
					rot: int = ((32 - shamt) // 2) % 16
					src12 = src12 << 4 | (rot & 0xF)
					src12 = src12 << 8 | (value >> shamt & 0xFF)

				elif len(args) == 1:
					Rm: int = parse_register(args[0])
					src12 <<= 8
					src12 = src12 << 4 | (Rm & 0xF)
					is_immediate = False

				elif len(args) == 2:
					Rm: int = parse_register(args[0])
					sh_str: str
					shamt_str: str
					sh_str, shamt_str, *_rem = args[1].split()
					assert len(_rem) == 0, 'Invalid shifter arguments'
					assert sh_str in Assembler.__SHIFT_TYPES__, f'Invalid shift mode \'{sh_str}\''
					sh: int = Assembler.__SHIFT_TYPES__.index(sh_str)
					is_immediate = False

					if shamt_str.startswith('#'):
						shamt5: int = parse_value(shamt_str)
						src12 = src12 << 5 | (shamt5 & 0b11111)
						src12 = src12 << 2 | (sh & 0b11)
						src12 <<= 1
						src12 = src12 << 4 | (Rm & 0xF)
					else:
						Rs: int = parse_register(shamt_str)
						src12 = src12 << 4 | (Rs & 0xF)
						src12 <<= 1
						src12 = src12 << 2 | (sh & 0b11)
						src12 = src12 << 1 | 1
						src12 = src12 << 4 | (Rm & 0xF)

				elif len(args) == 0 and full_cmd == 'MOV':
					is_immediate = rn.startswith('#')

					if not is_immediate:
						basen: BaseNumber = BaseN(2).convert(Rn)
						assert basen.precision() <= 8, 'Immediate operand is not 8-bit precision'
						binary: str = str(basen).rjust(8, '0')
						is_immediate = True
						shamt: int = len(binary) - binary.rindex('1') - 1
						shamt = shamt if shamt % 2 == 0 else shamt - 1
						rot: int = ((32 - shamt) // 2) % 16
						src12 = src12 << 4 | (rot & 0xF)
						src12 = src12 << 8 | (Rn >> shamt & 0xFF)
						Rn = 0

				else:
					raise ValueError('Invalid number of arguments')

				encoded |= cond & 0xF
				encoded <<= 2
				encoded = encoded << 1 | (is_immediate & 0b1)
				encoded = encoded << 4 | (cmd & 0xF)
				encoded = encoded << 1 | (has_s & 0x1)
				encoded = encoded << 4 | (Rn & 0xF)
				encoded = encoded << 4 | (Rd & 0xF)
				encoded = encoded << 12 | (src12 & 0xFFF)

			elif len(_found := tuple(x for x in Assembler.__MEMORY__ if cmd.startswith(x))) > 0 and (full_cmd := sorted(_found, key=lambda c: len(c), reverse=True)[0]):
				assert 2 <= len(args) <= 4, 'Invalid number of arguments'
				_extra: str = cmd[len(full_cmd):]
				has_s: bool = _extra == 'S'
				cond_str: str = 'AL' if len(_extra) == 0 or has_s else _extra if not has_s else None
				cond: int = Assembler.__CONDITIONS__.index(cond_str)
				byte: bool = full_cmd[-1] == 'B'
				Rd: int = parse_register(args[0])
				base_offset: str = args[1]
				do_prefix: bool = False

				if base_offset.endswith('!'):
					base_offset = base_offset[:-1]
					do_prefix = True

				assert len(base_offset) > 2 and base_offset[0] == '[' and base_offset[-1] == ']', 'Malformed base offset'
				base_ptr_args: tuple[str, ...] = tuple(x.strip() for x in base_offset[1:-1].split(','))
				is_immediate: bool
				register_shifted: bool = False
				offset: int
				sh: int = 0
				Rn: int = parse_register(base_ptr_args[0])
				method: int = 0b11 if do_prefix else 0b00 if len(args) > 3 else 0b10
				shamt5: int = 0
				Rm: int = 0
				Rs: int = 0

				if len(base_ptr_args) == 1:
					is_immediate = True
					offset = 0
				elif len(base_ptr_args) == 2:
					is_immediate = base_ptr_args[1].startswith('#')
					offset = parse_value(base_ptr_args[1]) if is_immediate else parse_register(base_ptr_args[1])
					Rm = offset
				elif len(base_ptr_args) == 3:
					is_immediate = False
					offset = parse_register(base_ptr_args[1])
					sh_str, shamt_str = base_ptr_args[2].split(maxsplit=1)
					assert sh_str in Assembler.__SHIFT_TYPES__, f'Invalid shift mode \'{sh_str}\''
					sh = Assembler.__SHIFT_TYPES__.index(sh_str)
					Rm = offset
					shamt5 = parse_value(shamt_str)
				else:
					raise ValueError('Malformed command')

				if len(args) >= 3 and do_prefix:
					raise SyntaxError('Combined prefix-postfix')
				elif len(args) == 3 and args[2].startswith('#'):
					is_immediate = True
					offset = parse_value(args[2])
				elif len(args) == 3:
					is_immediate = False
					offset = parse_register(args[2])
					Rm = offset
				elif len(args) == 4:
					is_immediate = False
					offset = parse_register(args[2])
					Rm = offset
					sh_str, shamt_str = args[3].split(maxsplit=1)
					assert sh_str in Assembler.__SHIFT_TYPES__, f'Invalid shift mode \'{sh_str}\''
					sh = Assembler.__SHIFT_TYPES__.index(sh_str)

					if shamt_str.startswith('#'):
						shamt5 = parse_value(shamt_str)
					else:
						register_shifted = True
						Rs = parse_register(shamt_str)

				encoded |= cond & 0xF
				encoded = encoded << 2 | 0x1
				encoded = encoded << 1 | ((not is_immediate) & 0x1)
				encoded = encoded << 1 | (method >> 1 & 0b1)
				encoded = encoded << 1 | ((not (is_immediate and offset >= 0)) & 0x1)
				encoded = encoded << 1 | (byte & 0x1)
				encoded = encoded << 1 | (method & 0x1)
				encoded = encoded << 1 | ((full_cmd[0] == 'L') & 0x1)
				encoded = encoded << 4 | (Rn & 0xF)
				encoded = encoded << 4 | (Rd & 0xF)

				if is_immediate:
					encoded = encoded << 12 | (abs(offset) & 0xFFF)
				elif register_shifted:
					encoded = encoded << 4 | (Rs & 0xF)
					encoded <<= 1
					encoded = encoded << 2 | (sh & 0b11)
					encoded = encoded << 1 | 1
					encoded = encoded << 4 | (Rm & 0xF)
				else:
					encoded = encoded << 5 | (shamt5 & 0b11111)
					encoded = encoded << 2 | (sh & 0b11)
					encoded = encoded << 1
					encoded = encoded << 4 | (Rm & 0xF)

			elif len(_found := tuple(x for x in Assembler.__BRANCH__ if cmd.startswith(x))) > 0:
				assert len(args) == 1, 'Invalid number of arguments'
				assert args[0] in labels, f'No such label \'{args[0]}\''
				full_cmd = 'BL' if cmd == 'BL' else _found[len(cmd) > 3]
				_extra: str = cmd[len(full_cmd):]
				has_s: bool = _extra == 'S'
				cond_str: str = 'AL' if len(_extra) == 0 or has_s else _extra if not has_s else None
				assert cond_str in Assembler.__CONDITIONS__, f'Invalid condition \'{cond_str}\''
				cond: int = Assembler.__CONDITIONS__.index(cond_str)
				linked: bool = full_cmd == 'BL'
				pc: int = index * 4 + 8
				target: int = labels[args[0]]
				offset: int = (target - pc) // 4

				encoded |= cond & 0xF
				encoded = encoded << 2 | 0x2
				encoded = encoded << 1 | 0x1
				encoded = encoded << 1 | (linked & 0b1)
				encoded = encoded << 24 | (offset & 0xFFFFFF)

			else:
				raise ValueError(f'Invalid command \'{cmd}\'')

			output.append(encoded)
			index += 1

		return tuple(output)

	@staticmethod
	def decode(assembly: typing.Iterable[int]) -> tuple[str, ...]:
		"""
		Decodes a set of assembly instructions from machine code
		:param assembly: (tuple[int]) An iterable of 32-bit machine code values to decode
		:return: (Iterable[str]) The decoded assembly instructions
		"""

		decoded: list[str] = []
		labels: dict[int, str] = {}
		label_counter: int = 0

		for i, instr in enumerate(assembly):
			instruction: list[str] = []
			cond: int = instr >> 28 & 0xF
			op: int = instr >> 26 & 0b11

			if op == 0:
				i: bool = bool(instr >> 25 & 0b1)
				cmd: int = instr >> 21 & 0xF
				s: bool = bool(instr >> 20 & 0x1)
				rn: int = instr >> 16 & 0xF
				rd: int = instr >> 12 & 0xF
				src2: int = instr & 0xFFF
				cmd_str: str = Assembler.__DATA_PROCESSING__[cmd]
				instruction.append(cmd_str + ('S' if s else '' if (cond_str := Assembler.__CONDITIONS__[cond]) == 'AL' else cond_str))
				instruction.append(f'R{rd},')
				instruction.append(f'R{rn},')

				if i and cmd_str != 'MOV':
					rot: int = src2 >> 8 & 0xF
					imm8: int = (src2 & 0xFF) << ((32 - (rot << 1)) % 32)
					instruction.append(f'#{hex(imm8)}')
				elif not i and src2 >> 4 & 0x1:
					rs: int = src2 >> 8 & 0xF
					sh: int = src2 >> 5 & 0b11
					rm: int = src2 & 0xF
					instruction.append(f'R{rm},')
					instruction.append(Assembler.__SHIFT_TYPES__[sh])
					instruction.append(f'R{rs}')
				elif not i:
					shamt5: int = src2 >> 7 & 0b11111
					sh: int = src2 >> 5 & 0b11
					rm: int = src2 & 0xF
					instruction.append(f'R{rm},')

					if shamt5 != 0 and sh != 0:
						instruction.append(Assembler.__SHIFT_TYPES__[sh])
						instruction.append(hex(shamt5))

			elif op == 1:
				not_i: bool = bool(instr >> 25 & 0b1)
				p: bool = bool(instr >> 24 & 0b1)
				u: bool = bool(instr >> 23 & 0b1)
				b: bool = bool(instr >> 22 & 0b1)
				w: bool = bool(instr >> 21 & 0b1)
				l: bool = bool(instr >> 20 & 0b1)
				rn: int = instr >> 16 & 0xF
				rd: int = instr >> 12 & 0xF
				src2: int = instr & 0xFFF
				method: int = (p << 1) | w
				register_shifted: bool = bool(src2 >> 4 & 0b1)
				instruction.append(('LDR' if l else 'STR') + ('B' if b else '') + ('' if (cond_str := Assembler.__CONDITIONS__[cond]) == 'AL' else cond_str))
				instruction.append(f'R{rd},')

				if not_i and register_shifted:
					rs: int = src2 >> 8 & 0xFF
					sh: int = src2 >> 5 & 0b11
					rm: int = src2 & 0xF
					offset: str = f'[R{rn}'
					offset += '' if method == 0b00 else f', R{rm}'

					if method != 0b00:
						offset += f', {Assembler.__SHIFT_TYPES__[sh]} R{rs}'

					instruction.append(offset + ']')

					if method == 0b11:
						instruction[-1] += '!'
					elif method == 0b00:
						instruction[-1] += ','
						instruction.append(f'R{rm},')
						instruction.append(f'{Assembler.__SHIFT_TYPES__[sh]} R{rs}')
				elif not_i:
					shamt5: int = src2 >> 7 & 0b11111
					sh: int = src2 >> 5 & 0b11
					rm: int = src2 & 0xF
					offset: str = f'[R{rn}'
					offset += '' if method == 0b00 else f', R{rm}'

					if method != 0b00 and (sh != 0 or shamt5 != 0):
						offset += f', {Assembler.__SHIFT_TYPES__[sh]} #{hex(shamt5)}'

					instruction.append(offset + ']')

					if method == 0b11:
						instruction[-1] += '!'
					elif method == 0b00:
						instruction[-1] += ','
						instruction.append(f'R{rm}')

						if sh != 0 or shamt5 != 0:
							instruction[-1] += ','
							instruction.append(f'{Assembler.__SHIFT_TYPES__[sh]} #{hex(shamt5)}')
				else:
					src2_str: str = f'-{hex(src2)}' if u else hex(src2)
					instruction.append(f'[R{rn}{"" if method == 0b00 or src2 == 0 else f", #{src2_str}"}]' + ('!' if method == 0b11 else f' #{src2_str}' if method == 0b00 else ''))

			elif op == 2:
				l: bool = bool(instr >> 24 & 0b1)
				imm24: int = instr & 0xFFFFFF
				imm24 = -(0xFFFFFF - imm24 + 1) if imm24 >> 23 & 0b1 else imm24
				target: int = (i * 4 + 8) + (imm24 * 4)
				label_str: str

				if target in labels:
					label_str = labels[target]
				else:
					label_str = f'LABEL_{label_counter}'
					label_counter += 1
					labels[target] = label_str

				instruction.append('B' + ('L' if l else '') + ('' if (cond_str := Assembler.__CONDITIONS__[cond]) == 'AL' else cond_str))
				instruction.append(label_str)
			else:
				raise ValueError('Invalid instruction operand')

			decoded.append(' '.join(instruction).rstrip(','))

		for pos, label_str in labels.items():
			index: int = pos // 4
			decoded[index] = f'{label_str}\t' + decoded[index]

		return tuple(decoded)

	@staticmethod
	def breakdown(instruction: int) -> OrderedDict[str, int]:
		"""
		Creates a breakdown of the single 32-bit Arm32 instruction
		The resulting ordered dictionary contains a mapping of tuples
		Each tuple contains a str (the column name) and the field size in bits
		If the size is negative, the number should be represented as a negative number
		:param instruction: (int) The 32-bit Arm32 instruction
		:return: (OrderedDict[str, int]) The breakdown
		"""

		breakdown: OrderedDict[str, tuple[int, int]] = OrderedDict()
		instruction = instruction & 0xFFFFFFFF
		cond: int = instruction >> 28 & 0xF
		op: int = instruction >> 26 & 0b11
		breakdown['cond'] = (4, cond)
		breakdown['op'] = (2, op)

		if op == 0:
			i: bool = bool(instruction >> 25 & 0b1)
			cmd: int = instruction >> 21 & 0xF
			s: bool = bool(instruction >> 20 & 0x1)
			rn: int = instruction >> 16 & 0xF
			rd: int = instruction >> 12 & 0xF
			src2: int = instruction & 0xFFF
			breakdown['i'] = (1, i)
			breakdown['cmd'] = (4, cmd)
			breakdown['s'] = (1, s)
			breakdown['Rn'] = (4, rn)
			breakdown['Rd'] = (4, rd)

			if i:
				rot: int = src2 >> 8 & 0xF
				imm8: int = (src2 & 0xFF)
				breakdown['rot'] = (4, rot)
				breakdown['imm8'] = (8, imm8)
			elif not i and src2 >> 4 & 0x1:
				rs: int = src2 >> 8 & 0xF
				sh: int = src2 >> 5 & 0b11
				rm: int = src2 & 0xF
				breakdown['Rs'] = (4, rs)
				breakdown['0'] = (1, 0)
				breakdown['sh'] = (2, sh)
				breakdown['1'] = (1, 1)
				breakdown['Rm'] = (4, rm)
			elif not i:
				shamt5: int = src2 >> 7 & 0b11111
				sh: int = src2 >> 5 & 0b11
				rm: int = src2 & 0xF
				breakdown['shamt5'] = (5, shamt5)
				breakdown['sh'] = (2, sh)
				breakdown['0'] = (1, 0)
				breakdown['Rm'] = (4, rm)

		elif op == 1:
			not_i: bool = bool(instruction >> 25 & 0b1)
			p: bool = bool(instruction >> 24 & 0b1)
			u: bool = bool(instruction >> 23 & 0b1)
			b: bool = bool(instruction >> 22 & 0b1)
			w: bool = bool(instruction >> 21 & 0b1)
			l: bool = bool(instruction >> 20 & 0b1)
			rn: int = instruction >> 16 & 0xF
			rd: int = instruction >> 12 & 0xF
			src2: int = instruction & 0xFFF
			method: int = (p << 1) | w
			register_shifted: bool = bool(src2 >> 4 & 0b1)
			breakdown['/I'] = (1, not_i)
			breakdown['P'] = (1, p)
			breakdown['U'] = (1, u)
			breakdown['B'] = (1, b)
			breakdown['W'] = (1, w)
			breakdown['L'] = (1, l)
			breakdown['Rn'] = (4, rn)
			breakdown['Rd'] = (4, rd)

			if not_i and register_shifted:
				rs: int = src2 >> 8 & 0xFF
				sh: int = src2 >> 5 & 0b11
				rm: int = src2 & 0xF
				breakdown['Rs'] = (4, rs)
				breakdown['0'] = (1, 0)
				breakdown['sh'] = (2, sh)
				breakdown['1'] = (1, 1)
				breakdown['Rm'] = (4, rm)
			elif not_i:
				shamt5: int = src2 >> 7 & 0b11111
				sh: int = src2 >> 5 & 0b11
				rm: int = src2 & 0xF
				breakdown['shamt5'] = (5, shamt5)
				breakdown['sh'] = (2, sh)
				breakdown['0'] = (1, 0)
				breakdown['Rm'] = (4, rm)
			else:
				breakdown['imm12'] = (-12, src2)

		elif op == 2:
			l: bool = bool(instruction >> 24 & 0b1)
			imm24: int = instruction & 0xFFFFFF
			breakdown['1'] = (1, 1)
			breakdown['l'] = (1, l)
			breakdown['imm24'] = (24, imm24)

		else:
			raise ValueError(f'Unexpected op-flag \'{op}\'')


		return breakdown

	@staticmethod
	def print_breakdown(instruction: int) -> None:
		"""
		Prints a breakdown of the single 32-bit Arm32 instruction
		:param instruction: (int) The 32-bit Arm32 instruction
		:return: (None)
		"""

		msg: str = f'"{instruction}"\n\n'
		breakdown: OrderedDict[str, int] = Assembler.breakdown(instruction)
		lines: list[str] = [' FORMAT │ ', '────────┼─', '    BIN │ ', '    OCT │ ', '    DEC │ ', '    HEX │ ']

		for i, (field, (size, value)) in enumerate(breakdown.items()):
			signed: bool = size < 0
			size = abs(size)
			mask: int = (1 << size) - 1
			value &= mask
			bin_: str = f'-{bin(abs(value))[2:].zfill(size)}' if signed and value < 0 else bin(value)[2:].zfill(size)
			oct_: str = f'-{oct(abs(value))[2:]}' if signed and value < 0 else oct(value)[2:]
			dec_: str = f'-{abs(value)[2:]}' if signed and value < 0 else str(value)
			hex_: str = (f'-{hex(abs(value))[2:]}' if signed and value < 0 else hex(value)[2:]).upper()
			longest: int = max(len(bin_), len(oct_), len(dec_), len(hex_), len(field))
			end: str = ' │ ' if i + 1 < len(breakdown) else ''
			lines[0] += f'{field.rjust(longest, " ")}{end}'
			lines[1] += '─' * (longest + 1) + ('┼─' if i + 1 < len(breakdown) else '')
			lines[2] += f'{bin_.rjust(longest)}{end}'
			lines[3] += f'{oct_.rjust(longest)}{end}'
			lines[4] += f'{dec_.rjust(longest)}{end}'
			lines[5] += f'{hex_.rjust(longest)}{end}'

		print(msg + '\n'.join(lines))
