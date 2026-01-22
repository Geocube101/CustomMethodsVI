from __future__ import annotations

import multiprocessing
import multiprocessing.queues
import threading
import typing

from . import Misc

HCB: typing.TypeVarTuple = typing.TypeVarTuple('HCB')


class EventHandler[*HCB]:
	"""
	Class for holding a list of callbacks to trigger
	"""

	@staticmethod
	def __thread_callback_wrapper__(callback: typing.Callable, threads: list[list[threading.Thread | typing.Callable | typing.Optional[Exception]]], index: int, args: tuple, kwargs: dict[str, typing.Any]) -> None:
		"""
		INTERNAL METHOD
		:param callback: The callback to execute
		:param threads: The thread data
		:param index: The thread index
		:param args: The callback positional arguments
		:param kwargs: The callback keyword arguments
		"""

		try:
			callback(*args, **kwargs)
		except Exception as err:
			threads[index][2] = err

	@staticmethod
	def __process_callback_wrapper__(callback: typing.Callable, index: int, queue: multiprocessing.Queue, args: tuple, kwargs: dict[str, typing.Any]) -> None:
		"""
		INTERNAL METHOD
		:param callback: The callback to execute
		:param index: The process index
		:param queue: The communications queue
		:param args: The callback positional arguments
		:param kwargs: The callback keyword arguments
		"""

		try:
			callback(*args, **kwargs)
			queue.put((index, None))
		except Exception as err:
			queue.put((index, err))

	def __init__(self, *callbacks: typing.Callable[[*HCB], ...]):
		"""
		Class for holding a list of callbacks to trigger
		- Constructor -
		:raises ValueError: If one or more callbacks is not callable
		"""

		Misc.raise_ifn(all(callable(x) for x in callbacks), ValueError('One or more callbacks is not callable'))
		self.__callbacks__: list[typing.Callable[[*HCB], ...]] = list(callbacks)

	def __iadd__(self, callback: typing.Callable[[*HCB], ...]) -> EventHandler[*HCB]:
		"""
		Registers a new callback to this event handler
		:param callback: The callback to bind
		:return: This event handler instance
		"""

		if not callable(callback):
			return NotImplemented

		self.__callbacks__.append(callback)
		return self

	def __isub__(self, callback: typing.Callable[[*HCB], ...]) -> EventHandler[*HCB]:
		"""
		Unregisters a callback to this event handler
		:param callback: The callback to bind
		:return: This event handler instance
		"""

		if not callable(callback):
			return NotImplemented

		if callback in self.__callbacks__:
			self.__callbacks__.remove(callback)

		return self

	def __contains__(self, callback: typing.Callable[[*HCB], ...]) -> bool:
		"""
		:param callback: The callback to check
		:return: Whether the specified callback is registered in this event handler
		"""

		return callback in self.__callbacks__

	def clear(self) -> None:
		"""
		Clears all registered callbacks from this handler
		"""

		self.__callbacks__.clear()

	def invoke(self, *args, ignore_exceptions__: bool = False, raise_after__: bool = False, **kwargs) -> None:
		"""
		Invokes this event
		All registered functions are called with the specified arguments
		:param args: The positional arguments to supply to each callback
		:param ignore_exceptions__: Whether to ignore any raised exception
		:param raise_after__: Whether to raise any exception after executing all callbacks
		:param kwargs: The keyword arguments to supply to each callback
		"""

		exception: typing.Optional[tuple[typing.Callable[[*HCB], ...], Exception]] = None

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
		"""
		Invokes this event
		All registered functions are called with the specified arguments
		All callbacks are called on their own threading.Thread
		:param args: The positional arguments to supply to each callback
		:param ignore_exceptions__: Whether to ignore any raised exception
		:param kwargs: The keyword arguments to supply to each callback
		"""

		threads: list[list[threading.Thread | typing.Callable[[*HCB], ...] | typing.Optional[Exception]]] = []

		for i, cb in enumerate(self.__callbacks__):
			thread: threading.Thread = threading.Thread(target=EventHandler.__thread_callback_wrapper__, args=(cb, threads, i, args, kwargs))
			threads.append([thread, cb, None])

		for thr in threads:
			thr[0].start()

		for thr in threads:
			thr[0].join()

		if not ignore_exceptions__:
			for (thread, cb, err) in threads:
				if err is not None:
					raise RuntimeError(f'An exception occurred during the following callback:\n\t...\n{cb}') from err

	def invoke_processed(self, *args, ignore_exceptions__: bool = False, **kwargs) -> None:
		"""
		Invokes this event
		All registered functions are called with the specified arguments
		All callbacks are called on their own multiprocessing.Process
		:param args: The positional arguments to supply to each callback
		:param ignore_exceptions__: Whether to ignore any raised exception
		:param kwargs: The keyword arguments to supply to each callback
		"""

		threads: list[list[multiprocessing.Process | typing.Callable[[*HCB], ...]]] = []
		queue: multiprocessing.Queue = multiprocessing.Queue()

		for i, cb in enumerate(self.__callbacks__):
			thread: multiprocessing.Process = multiprocessing.Process(target=EventHandler.__process_callback_wrapper__, args=(cb, i, queue, args, kwargs))
			threads.append([thread, cb])

		for thr in threads:
			thr[0].start()

		for thr in threads:
			thr[0].join()

		if not ignore_exceptions__:
			exceptions: list[tuple[int, Exception]] = []

			while not queue.empty():
				result: tuple[int, typing.Optional[Exception]] = queue.get()
				exceptions.append(result)

			exceptions.sort(key=lambda pair: pair[0])

			for i, err in exceptions:
				if err is not None:
					raise RuntimeError(f'An exception occurred during the following callback:\n\t...\n{threads[i][1]}') from err


class MultiEventHandler[*HCB]:
	"""
	Class for holding multiple lists of callbacks to trigger
	"""

	def __init__(self, *event_ids: str):
		"""
		Class for holding multiple lists of callbacks to trigger
		:param event_ids: The initial event ids to register
		:raises TypeError: If one or more event IDs is not a string
		"""

		Misc.raise_ifn(all(isinstance(x, str) for x in event_ids), TypeError('One or more event IDs is not a string'))
		self.__handlers__: dict[str, EventHandler] = {str(eid): EventHandler() for eid in event_ids}

	def __contains__(self, eid_cb: str | typing.Callable[[*HCB], ...]) -> bool:
		"""
		:param eid_cb: The event ID or callback
		:return: Whether an event ID or callback is held within this event handler
		"""

		if isinstance(eid_cb, str):
			return str(eid_cb) in self.__handlers__
		elif callable(eid_cb):
			return any(eid_cb in event for event in self.__handlers__.values())
		else:
			return False

	def __setitem__(self, eid: str, handler: EventHandler[*HCB] | typing.Iterable[typing.Callable[[*HCB], ...]] | typing.Callable[[*HCB], ...]) -> None:
		"""
		Overrides or adds a new event handler for the specified event ID
		:param eid: The event ID
		:param handler: The event handler, callback, or collection of callbacks to overwrite with
		:raises InvalidArgumentException: If 'eid' is not a string
		:raises TypeError: If 'handler' is not an EventHandler instance, collection of callbacks, or a single callback
		"""

		Misc.raise_ifn(isinstance(eid, str), TypeError('Event ID is not a string'))

		if isinstance(handler, EventHandler):
			self.__handlers__[str(eid)] = handler
		elif hasattr(handler, '__iter__'):
			self.__handlers__[str(eid)] = EventHandler(*tuple(handler))
		elif callable(handler):
			self.__handlers__[str(eid)] = EventHandler(handler)
		else:
			raise TypeError('Handler is not an EventHandler instance, collection of callbacks, or a single callback')

	def __delitem__(self, eid: str) -> None:
		"""
		Unregisters all callbacks for an event ID
		:param eid: The event ID to unregister
		"""

		if eid in self.__handlers__:
			del self.__handlers__[eid]

	def __getitem__(self, eid: str) -> EventHandler[*HCB]:
		"""
		Gets the event handler for a specific event ID
		:param eid: The event ID
		:return: The event's handler
		:raises KeyError: If the event ID does not exist
		"""

		if eid not in self.__handlers__:
			raise KeyError('Specified event id does not exist')
		else:
			return self.__handlers__[eid]

	def clear(self) -> None:
		"""
		Clears all registered callbacks from this handler
		"""

		for handler in self.__handlers__.values():
			handler.clear()

		self.__handlers__.clear()

	def on(self, eid: str, callback: typing.Optional[typing.Callable[[*HCB], ...]] = ...) -> typing.Optional[typing.Callable[[*HCB], ...]]:
		"""
		Registers a callback for the specified event ID
		:param eid: The event ID
		:param callback: The callback or None to decorate
		:return: None or binder if used as a decorator
		:raises ValueError: If specified callback is not callable
		"""

		if callback is None or callback is ...:
			def binder(func: typing.Callable[[*HCB], ...]) -> None:
				if not callable(func):
					raise ValueError('Specified callback is not callable')
				elif eid in self.__handlers__:
					self.__handlers__[eid] += func
				else:
					handler_: EventHandler[*HCB] = EventHandler()
					handler_ += func
					self.__handlers__[eid] = handler_

			return binder
		elif not callable(callback):
			raise ValueError('Specified callback is not callable')
		elif eid in self.__handlers__:
			self.__handlers__[eid] += callback
		else:
			handler: EventHandler[*HCB] = EventHandler()
			handler += callback
			self.__handlers__[eid] = handler

	def off(self, eid: str, callback: typing.Optional[typing.Callable[[*HCB], ...]] = ...) -> None:
		"""
		Unregisters a callback for the specified event ID or all callbacks for the specified event ID if callback is not supplied
		:param eid: The event ID
		:param callback: The callback or None to unregister all
		:raises ValueError: If specified callback is not callable
		:raises KeyError: If the event ID does not exist
		"""

		if eid not in self.__handlers__:
			raise KeyError('Specified event id does not exist')
		elif callback is None or callback is ...:
			del self.__handlers__[eid]
		elif not callable(callback):
			raise ValueError('Specified callback is not callable')
		else:
			self.__handlers__[eid] -= callback

	def invoke(self, eid: str, *args, ignore_exceptions__: bool = False, raise_after__: bool = False, **kwargs):
		"""
		Invokes all callbacks for the specified event ID
		All registered functions are called with the specified arguments
		:param eid: The event ID to invoke
		:param args: The positional arguments to supply to each callback
		:param ignore_exceptions__: Whether to ignore any raised exception
		:param raise_after__: Whether to raise any exception after executing all callbacks
		:param kwargs: The keyword arguments to supply to each callback
		"""

		if eid not in self.__handlers__:
			raise KeyError('Specified event id does not exist')
		else:
			self.__handlers__[eid].invoke(*args, ignore_exceptions__=ignore_exceptions__, raise_after__=raise_after__, **kwargs)

	def invoke_threaded(self, eid: str, *args, ignore_exceptions__: bool = False, **kwargs):
		"""
		Invokes all callbacks for the specified event ID
		All registered functions are called with the specified arguments
		All callbacks are called on their own threading.Thread
		:param eid: The event ID to invoke
		:param args: The positional arguments to supply to each callback
		:param ignore_exceptions__: Whether to ignore any raised exception
		:param kwargs: The keyword arguments to supply to each callback
		"""

		if eid not in self.__handlers__:
			raise KeyError('Specified event id does not exist')
		else:
			self.__handlers__[eid].invoke_threaded(*args, ignore_exceptions__=ignore_exceptions__, **kwargs)

	def invoke_processed(self, eid: str, *args, ignore_exceptions__: bool = False, **kwargs):
		"""
		Invokes all callbacks for the specified event ID
		All registered functions are called with the specified arguments
		All callbacks are called on their own multiprocessing.Process
		:param eid: The event ID to invoke
		:param args: The positional arguments to supply to each callback
		:param ignore_exceptions__: Whether to ignore any raised exception
		:param kwargs: The keyword arguments to supply to each callback
		"""

		if eid not in self.__handlers__:
			raise KeyError('Specified event id does not exist')
		else:
			self.__handlers__[eid].invoke_processed(*args, ignore_exceptions__=ignore_exceptions__, **kwargs)

	@property
	def event_ids(self) -> tuple[str, ...]:
		"""
		:return: All bound event IDs in this handler
		"""

		return tuple(self.__handlers__.keys())
