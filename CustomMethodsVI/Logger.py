from __future__ import annotations

import datetime
import io
import os
import threading
import typing

from . import Exceptions
from . import Stream


class Logger:
	class CategoryLogger(Stream.StringStream):
		def __init__(self, logger: Logger, category: str):
			"""
			Class representing a logging stream under a single category level
			:param logger: The parent logger
			:param category: The logging category
			"""

			super().__init__()
			self.__logger__: Logger = logger
			self.__category__: str = str(category)

		def print(self, *data: typing.Any, sep: str = ' ', end: str = '\n') -> Logger.CategoryLogger:
			"""
			Prints data to the logger
			:param data: The data
			:param sep: Data delimiter
			:param end: Data terminator
			:return: This stream
			"""

			self.write(self.__logger__.__get_line__(self.category, sep.join(map(str, data))) + end)
			return self

		def write(self, line: str, *, ignore_invalid=False) -> Logger.CategoryLogger:
			"""
			Writes raw data to the logger
			:param line: The line to write
			:param ignore_invalid: Not used
			:return: This stream
			"""

			if self.closed or self.__logger__.closed:
				raise IOError('Log is closed')

			self.__logger__.__stream__.write(self.__logger__.__get_line__(self.category, line))
			return self

		@property
		def category(self) -> str:
			"""
			:return: This writer's category
			"""

			return self.__category__

	def __init__(self, stream: io.IOBase, timezone: datetime.timezone | datetime.tzinfo = datetime.timezone.utc, header_format: str = '{%D} {%T} - [ {%TZ} ] [ {%C} ] -> Thread {%TID}: {%M}'):
		"""
		Class representing a log file writer\n
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
			raise Exceptions.InvalidArgumentException(Logger.__init__, 'timezone', type(timezone), (datetime.timezone, datetime.tzinfo))

		if stream.closed:
			raise IOError('Stream is closed')
		elif not stream.writable():
			raise IOError('Target stream is not writable')

		categories: tuple[str, ...] = ('DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL')
		self.__header__: str = str(header_format)
		self.__stream__: io.IOBase = stream
		self.__timezone__: datetime.timezone = timezone
		self.__state__: bool = True
		self.__categories__: dict[str, Logger.CategoryLogger] = {category: Logger.CategoryLogger(self, category) for category in categories}
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

		for category in self.__categories__.values():
			category.flush()
			category.close()

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

		self.category_debug.print(*data, sep=sep, end=end)
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

		self.category_info.print(*data, sep=sep, end=end)
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

		self.category_warn.print(*data, sep=sep, end=end)
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

		self.category_error.print(*data, sep=sep, end=end)
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

		self.category_critical.print(*data, sep=sep, end=end)
		return self

	def category(self, category: str) -> Logger.CategoryLogger:
		"""
		Creates or gets a category writer
		:param category: The category to write to
		:return: The writer
		"""

		category = str(category).upper()
		writer: typing.Optional[Logger.CategoryLogger] = self.__categories__.get(category)

		if writer is None or writer.closed:
			writer = Logger.CategoryLogger(self, category)
			self.__categories__[category] = writer
			return writer
		else:
			return writer

	@property
	def closed(self) -> bool:
		"""
		:return: Whether this logger is closed
		"""

		return not self.__state__

	@property
	def category_debug(self) -> Logger.CategoryLogger:
		"""
		:return: Category writer for debug level
		"""

		return self.__categories__['DEBUG']

	@property
	def category_info(self) -> Logger.CategoryLogger:
		"""
		:return: Category writer for info level
		"""

		return self.__categories__['INFO']

	@property
	def category_warn(self) -> Logger.CategoryLogger:
		"""
		:return: Category writer for warn level
		"""

		return self.__categories__['WARN']

	@property
	def category_error(self) -> Logger.CategoryLogger:
		"""
		:return: Category writer for error level
		"""

		return self.__categories__['ERROR']

	@property
	def category_critical(self) -> Logger.CategoryLogger:
		"""
		:return: Category writer for critical level
		"""

		return self.__categories__['CRITICAL']


__all__: list[str] = ['Logger']
