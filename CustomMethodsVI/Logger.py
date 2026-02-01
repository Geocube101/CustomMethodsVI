from __future__ import annotations

import datetime
import io
import os
import threading
import typing

from . import Exceptions


class Logger:
	"""
	Class representing a log file writer
	"""

	def __init__(self, stream: io.IOBase, timezone: datetime.timezone = datetime.timezone.utc, header_format: str = '{%D} {%T} - [ {%TZ} ] [ {%C} ] -> Thread {%TID}: {%M}'):
		"""
		Class representing a log file writer\n
		- Constructor -\n
		[ Header Format ]\n
		* %D - Current date\n
		* %T - Current time\n
		* %TZ - Current timezone\n
		* %C - Logger category (DEBUG, INFO, WARN, ERROR, CRITICAL)\n
		* %PID - Sending process ID\n
		* %TID - Sending thread ID\n
		* %TNID - Sending thread native ID\n
		* %M - Original message
		:param stream: The stream to write results to
		:param timezone: The timezone to log with
		"""

		if not isinstance(stream, io.IOBase):
			raise Exceptions.InvalidArgumentException(Logger.__init__, 'stream', type(stream), (io.IOBase,))
		elif not isinstance(timezone, datetime.timezone):
			raise Exceptions.InvalidArgumentException(Logger.__init__, 'timezone', type(timezone), (datetime.timezone,))

		if stream.closed:
			raise IOError('Stream is closed')
		elif not stream.writable():
			raise IOError('Target stream is not writable')

		self.__header__: str = str(header_format)
		self.__stream__: io.IOBase = stream
		self.__timezone__: datetime.timezone = timezone
		self.__state__: bool = True
		self.__stream__.write('==========[ Log Opened ]==========\n\n')

	def __get_line__(self, category: str, msg: str) -> str:
		now: datetime.datetime = datetime.datetime.now(self.__timezone__)

		return self.__header__ \
			.replace('{%D}', now.strftime('%m/%d/%Y')) \
			.replace('{%T}', now.strftime('%H:%M:%S.%f')) \
			.replace('{%TZ}', str(self.__timezone__)) \
			.replace('{%C}', category) \
			.replace('{%PID}', str(os.getpid())) \
			.replace('{%TID}', str(threading.get_ident())) \
			.replace('{%TNID}', str(threading.get_native_id())) \
			.replace('{%M}', msg)

	def close(self) -> None:
		"""
		Closes the log writer
		Any further write is erroneous
		:raises IOError: If log is already closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write('\n==========[ Log Closed ]==========')
		self.__state__ = False
		self.__stream__.flush()
		self.__stream__.close()
		self.__stream__ = None

	def detach(self) -> None:
		"""
		Detaches the log writer
		The underlying stream is not closed
		Any further write is erroneous
		:raises IOError: If log is already closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write('\n==========[ Log Closed ]==========')
		self.__state__ = False
		self.__stream__ = None

	def debug(self, *data: typing.Any, sep: str = ' ', end: str = '\n') -> Logger:
		"""
		Writes a message to the log on DEBUG level
		:param data: The data to write
		:param sep: The seperator token
		:param end: The terminator token
		:return: This log writer instance
		:raises IOError: If log is closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(self.__get_line__('DEBUG', sep.join(map(str, data))) + end)
		return self

	def info(self, *data: typing.Any, sep: str = ' ', end: str = '\n') -> Logger:
		"""
		Writes a message to the log on INFO level
		:param data: The data to write
		:param sep: The seperator token
		:param end: The terminator token
		:return: This log writer instance
		:raises IOError: If log is closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(self.__get_line__('INFO', sep.join(map(str, data))) + end)
		return self

	def warn(self, *data: typing.Any, sep: str = ' ', end: str = '\n') -> Logger:
		"""
		Writes a message to the log on WARN level
		:param data: The data to write
		:param sep: The seperator token
		:param end: The terminator token
		:return: This log writer instance
		:raises IOError: If log is closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(self.__get_line__('WARN', sep.join(map(str, data))) + end)
		return self

	def error(self, *data: typing.Any, sep: str = ' ', end: str = '\n') -> Logger:
		"""
		Writes a message to the log on ERROR level
		:param data: The data to write
		:param sep: The seperator token
		:param end: The terminator token
		:return: This log writer instance
		:raises IOError: If log is closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(self.__get_line__('ERROR', sep.join(map(str, data))) + end)
		return self

	def critical(self, *data: typing.Any, sep: str = ' ', end: str = '\n') -> Logger:
		"""
		Writes a message to the log on CRITICAL level
		:param data: The data to write
		:param sep: The seperator token
		:param end: The terminator token
		:return: This log writer instance
		:raises IOError: If log is closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(self.__get_line__('CRITICAL', sep.join(map(str, data))) + end)
		return self
