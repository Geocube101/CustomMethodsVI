from __future__ import annotations

import multiprocessing
import multiprocessing.queues
import threading
import typing


class EventHandler:
	@staticmethod
	def __thread_callback_wrapper__(callback: typing.Callable, threads: list[list[threading.Thread | typing.Callable | typing.Optional[Exception]]], index: int, args: tuple, kwargs: dict[str, typing.Any]) -> None:
		try:
			callback(*args, **kwargs)
		except Exception as err:
			threads[index][2] = err

	@staticmethod
	def __process_callback_wrapper__(callback: typing.Callable, index: int, queue: multiprocessing.Queue, args: tuple, kwargs: dict[str, typing.Any]) -> None:
		try:
			callback(*args, **kwargs)
			queue.put((index, None))
		except Exception as err:
			queue.put((index, err))

	def __init__(self):
		self.__callbacks__: list[typing.Callable] = []

	def __iadd__(self, callback: typing.Callable) -> EventHandler:
		if not callable(callback):
			return NotImplemented

		self.__callbacks__.append(callback)
		return self

	def __isub__(self, callback: typing.Callable) -> EventHandler:
		if not callable(callback):
			return NotImplemented

		if callback in self.__callbacks__:
			self.__callbacks__.remove(callback)

		return self

	def __contains__(self, callback: typing.Callable) -> bool:
		return callback in self.__callbacks__

	def invoke(self, *args, ignore_exceptions__: bool = False, raise_after__: bool = False, **kwargs) -> None:
		exception: typing.Optional[tuple[typing.Callable, Exception]] = None

		for cb in self.__callbacks__:
			try:
				cb(*args, **kwargs)
			except Exception as err:
				if not ignore_exceptions__ and raise_after__:
					exception = (cb, err)
				elif not ignore_exceptions__:
					raise RuntimeError(f'An exception occurred during the following callback:\n\t...\n{cb}') from err

		if exception is not None:
			cb, err = exception
			raise RuntimeError(f'An exception occurred during the following callback:\n\t...\n{cb}') from err

	def invoke_threaded(self, *args, ignore_exceptions__: bool = False, **kwargs) -> None:
		threads: list[list[threading.Thread | typing.Callable | typing.Optional[Exception]]] = []

		for i, cb in enumerate(self.__callbacks__):
			thread: threading.Thread = threading.Thread(target=EventHandler.__thread_callback_wrapper__, args=(cb, threads, i, args, kwargs))
			threads.append([thread, cb, None])

		for thread in threads:
			thread[0].start()

		for thread in threads:
			thread[0].join()

		if not ignore_exceptions__:
			for (thread, cb, err) in threads:
				if err is not None:
					raise RuntimeError(f'An exception occurred during the following callback:\n\t...\n{cb}') from err

	def invoke_processed(self, *args, ignore_exceptions__: bool = False, **kwargs) -> None:
		threads: list[list[multiprocessing.Process | typing.Callable]] = []
		queue: multiprocessing.Queue = multiprocessing.Queue()

		for i, cb in enumerate(self.__callbacks__):
			thread: multiprocessing.Process = multiprocessing.Process(target=EventHandler.__process_callback_wrapper__, args=(cb, i, queue, args, kwargs))
			threads.append([thread, cb])

		for thread in threads:
			thread[0].start()

		for thread in threads:
			thread[0].join()

		if not ignore_exceptions__:
			exceptions: list[tuple[int, Exception]] = []

			while not queue.empty():
				result: tuple[int, typing.Optional[Exception]] = queue.get()
				exceptions.append(result)

			exceptions.sort(key=lambda pair: pair[0])

			for i, err in exceptions:
				if err is not None:
					raise RuntimeError(f'An exception occurred during the following callback:\n\t...\n{threads[i][1]}') from err


class MultiEventHandler:
	def __init__(self, *event_ids: str):
		self.__handlers__: dict[str, EventHandler] = {eid: EventHandler() for eid in event_ids}

	def __getitem__(self, eid: str) -> EventHandler:
		if eid not in self.__handlers__:
			raise KeyError('Specified event id does not exist')
		else:
			return self.__handlers__[eid]

	def on(self, eid: str, callback: typing.Optional[typing.Callable] = ...) -> typing.Optional[typing.Callable]:
		if callback is None or callback is ...:
			def binder(func: typing.Callable) -> None:
				if not callable(func):
					raise ValueError('Specified callback is not callable')
				elif eid in self.__handlers__:
					self.__handlers__[eid] += func
				else:
					handler_: EventHandler = EventHandler()
					handler_ += func
					self.__handlers__[eid] = handler_

			return binder
		elif not callable(callback):
			raise ValueError('Specified callback is not callable')
		elif eid in self.__handlers__:
			self.__handlers__[eid] += callback
		else:
			handler: EventHandler = EventHandler()
			handler += callback
			self.__handlers__[eid] = handler

	def off(self, eid: str, callback: typing.Optional[typing.Callable] = ...) -> None:
		if eid not in self.__handlers__:
			raise KeyError('Specified event id does not exist')
		elif callback is None or callback is ...:
			del self.__handlers__[eid]
		elif not callable(callback):
			raise ValueError('Specified callback is not callable')
		else:
			self.__handlers__[eid] -= callback

	def invoke(self, eid: str, *args, ignore_exceptions__: bool = False, raise_after__: bool = False, **kwargs):
		if eid not in self.__handlers__:
			raise KeyError('Specified event id does not exist')
		else:
			self.__handlers__[eid].invoke(*args, ignore_exceptions__=ignore_exceptions__, raise_after__=raise_after__, **kwargs)

	def invoke_threaded(self, eid: str, *args, ignore_exceptions__: bool = False, **kwargs):
		if eid not in self.__handlers__:
			raise KeyError('Specified event id does not exist')
		else:
			self.__handlers__[eid].invoke_threaded(*args, ignore_exceptions__=ignore_exceptions__, **kwargs)

	def invoke_processed(self, eid: str, *args, ignore_exceptions__: bool = False, **kwargs):
		if eid not in self.__handlers__:
			raise KeyError('Specified event id does not exist')
		else:
			self.__handlers__[eid].invoke_processed(*args, ignore_exceptions__=ignore_exceptions__, **kwargs)
