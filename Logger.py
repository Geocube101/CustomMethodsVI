from __future__ import annotations

import io
import typing
import datetime

import CustomMethodsVI.Exceptions as Exceptions
import CustomMethodsVI.Stream as Stream


class Logger:
	def __init__(self, stream: io.IOBase, timezone: datetime.timezone = datetime.timezone.utc):
		if not isinstance(stream, io.IOBase):
			raise Exceptions.InvalidArgumentException(Logger.__init__, 'stream', type(stream), (io.IOBase,))
		elif not isinstance(timezone, datetime.timezone):
			raise Exceptions.InvalidArgumentException(Logger.__init__, 'timezone', type(timezone), (datetime.timezone,))

		if stream.closed:
			raise IOError('Stream is closed')
		elif not stream.writable():
			raise IOError('Target stream is not writable')

		self.__stream__: io.IOBase = stream
		self.__timezone__: datetime.timezone = timezone
		self.__state__: bool = True
		self.__stream__.write('==========[ Log Opened ]==========\n\n')

	def close(self) -> None:
		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write('\n==========[ Log Closed ]==========')
		self.__state__ = False
		self.__stream__.flush()
		self.__stream__.close()
		self.__stream__ = None

	def detatch(self) -> None:
		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write('\n==========[ Log Closed ]==========')
		self.__state__ = False
		self.__stream__ = None

	def debug(self, msg: typing.Any) -> Logger:
		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(f'{datetime.datetime.now(datetime.timezone.utc).strftime("%m/%d/%Y %H:%M:%S.%f")} [ {self.__timezone__} ] [ DEBUG ]: {msg}')
		return self

	def info(self, msg: typing.Any) -> Logger:
		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(f'{datetime.datetime.now(datetime.timezone.utc).strftime("%m/%d/%Y %H:%M:%S.%f")} [ {self.__timezone__} ] [ INFO ]: {msg}')
		return self

	def warn(self, msg: typing.Any) -> Logger:
		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(f'{datetime.datetime.now(datetime.timezone.utc).strftime("%m/%d/%Y %H:%M:%S.%f")} [ {self.__timezone__} ] [ WARN ]: {msg}')
		return self

	def error(self, msg: typing.Any) -> Logger:
		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(f'{datetime.datetime.now(datetime.timezone.utc).strftime("%m/%d/%Y %H:%M:%S.%f")} [ {self.__timezone__} ] [ ERROR ]: {msg}')
		return self

	def critical(self, msg: typing.Any) -> Logger:
		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(f'{datetime.datetime.now(datetime.timezone.utc).strftime("%m/%d/%Y %H:%M:%S.%f")} [ {self.__timezone__} ] [ CRITICAL ]: {msg}')
		return self
