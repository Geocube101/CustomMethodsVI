import pickle
import psutil
import sys
import traceback
import base64
import typing
import types
import importlib.util
import uuid
import os
import curses

import CustomMethodsVI.Connection as Connection
import CustomMethodsVI.Terminal.Terminal as Terminal
import CustomMethodsVI.Terminal.Struct as Struct


if __name__ == '__main__':
	res: int = -1

	try:
		parent_pid: int
		conn: Connection.NamedPipe
		widget_conn: Connection.NamedPipe
		tps: int
		width: int
		height: int
		font: Struct.Font
		callables: dict[str, tuple[str, str, str]]
		parent_pid, conn, widget_conn, tps, width, height, font, callables = tuple(pickle.loads(base64.b64decode(sys.argv[1].encode())))
		conn.write(b'\x00')
		process: psutil = psutil.Process(parent_pid)
		start_byte: int = -1

		while process.is_running():
			if conn.poll() >= 1:
				start_byte: int = conn.read(1)[0]
				break

		if not process.is_running():
			print('ERROR_PARENT_CLOSED')
			sys.exit(254)
		elif start_byte != 1:
			print('ERROR_START_BYTE_INVALID')
			sys.exit(255)

		functions: dict[str, typing.Callable] = {}
		temp_module: str = f'{str(uuid.uuid4()).replace("-", "_")}_MODULE'

		for key, (module_path, mode_name, fname) in callables.items():
			spec = importlib.util.spec_from_file_location(temp_module, module_path)
			module: types.ModuleType = importlib.util.module_from_spec(spec)
			sys.modules[temp_module] = module
			spec.loader.exec_module(module)
			function: typing.Callable = getattr(module, fname)

			if callable(function):
				functions[key] = function

		if temp_module in sys.modules:
			del sys.modules[temp_module]

		terminal: Terminal.WindowTerminal.SubprocessTerminal = Terminal.WindowTerminal.SubprocessTerminal(conn, widget_conn, width, height, font)

		def on_exit(*_) -> None:
			global res

			terminal.end(-1)
			res = terminal.wait()

			if not conn.closed:
				conn.send((0, True, terminal.exit_reason))
				conn.flush()
				conn.close()

			if not widget_conn.closed:
				widget_conn.close()

		if os.name == 'nt':
			import win32api
			win32api.SetConsoleCtrlHandler(on_exit, True)
		else:
			import signal
			signal.signal(signal.SIGHUP, on_exit)

		res = terminal.mainloop(tps, before_draw=functions['before_draw'] if 'before_draw' in functions else ..., after_draw=functions['after_draw'] if 'after_draw' in functions else ...)

		if not conn.closed:
			conn.send((0, True, terminal.exit_reason))
			conn.flush()
			conn.close()

		if not widget_conn.closed:
			widget_conn.close()

		if res != 0:
			input('...')

	except (KeyboardInterrupt, Exception) as e:
		curses.endwin()
		print(''.join(traceback.format_exception(e)))
		input('...')
	finally:
		sys.exit(res)
