import traceback
import sys
import subprocess
import os


def main():
	try:
		os.system('')

		print('Downloading packages...')
		failed: int = 0

		with open('packages.kvp', 'r') as f:
			kvp: tuple[tuple[str, ...], ...] = tuple(tuple(x.strip() for x in line.split('=', 1)) for line in f.readlines())

			for package, true_names in kvp:
				name: str = true_names if len(true_names) > 0 else package
				print(f' ... Downloading module [ {name} ] - ', end='')
				sys.stdout.flush()

				try:
					exec(f'import {package.replace("-", "_")}')
					print('\033[38;2;75;100;255mAlready Installed\033[0m')
				except ImportError:
					result = subprocess.run(['py', '-m', 'pip', 'install', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

					if result.returncode == 0:
						print('\033[38;2;0;255;0mSuccess\033[0m')
					else:
						failed += 1
						print('\033[38;2;255;0;0mFailed\033[0m')

		print('Download complete.')

		if failed:
			print('Some packages failed to download, see \'install/packages.kvp\' for a list of all packages this project uses')

	except (SystemExit, KeyboardInterrupt):
		print('USER_OVERRIDE')
	except Exception as e:
		sys.stderr.write(''.join(traceback.format_exception(e)))
	finally:
		input('ENTER. ')


if __name__ == '__main__':
	main()
