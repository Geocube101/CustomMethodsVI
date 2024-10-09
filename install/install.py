import time
import traceback
import ctypes
import sys
import subprocess
import os

from CustomMethodsVI.Parser.KVP import KVP


def is_admin():
	try:
		return ctypes.windll.shell32.IsUserAnAdmin()
	except:
		return False


if __name__ == '__main__':
	if is_admin():
		try:
			os.system('')

			with open('packages.kvp', 'r') as f:
				kvp = KVP.decode(f.read())

				for package, true_names in kvp:
					name: str = true_names[0] if len(true_names) > 0 else package
					print(f'Downloading module [ {name} ] - ', end='')
					result = subprocess.run(['python', '-m', 'pip', 'install', name], stdout=subprocess.DEVNULL)

					if result.returncode == 0:
						print('\033[38;2;0;255;0mSuccess\033[0m')
					else:
						print('\033[38;2;255;0;0mFailed\033[0m')

		except Exception as e:
			sys.stderr.write(''.join(traceback.format_exception(e)))
		finally:
			input('ENTER. ')
	else:
		args = ' '.join(f'"{x}"' if any(s.isspace() for s in x) else x for x in sys.argv)
		ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, args, None, 1)
