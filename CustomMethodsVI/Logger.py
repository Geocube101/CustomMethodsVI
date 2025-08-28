from __future__ import annotations

import datetime
import io
import typing

from . import Exceptions


class Logger:
	"""
	Class representing a log file writer
	"""

	def __init__(self, stream: io.IOBase, timezone: datetime.timezone = datetime.timezone.utc):
		"""
		Class representing a log file writer
		- Constructor -
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

		self.__stream__: io.IOBase = stream
		self.__timezone__: datetime.timezone = timezone
		self.__state__: bool = True
		self.__stream__.write('==========[ Log Opened ]==========\n\n')

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

	def debug(self, msg: typing.Any) -> Logger:
		"""
		Writes a message to the log on DEBUG level
		:param msg: The message to write
		:return: This log writer instance
		:raises IOError: If log is closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(f'{datetime.datetime.now(datetime.timezone.utc).strftime("%m/%d/%Y %H:%M:%S.%f")} [ {self.__timezone__} ] [ DEBUG ]: {str(msg).strip()}\n')
		return self

	def info(self, msg: typing.Any) -> Logger:
		"""
		Writes a message to the log on INFO level
		:param msg: The message to write
		:return: This log writer instance
		:raises IOError: If log is closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(f'{datetime.datetime.now(datetime.timezone.utc).strftime("%m/%d/%Y %H:%M:%S.%f")} [ {self.__timezone__} ] [ INFO ]: {str(msg).strip()}\n')
		return self

	def warn(self, msg: typing.Any) -> Logger:
		"""
		Writes a message to the log on WARN level
		:param msg: The message to write
		:return: This log writer instance
		:raises IOError: If log is closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(f'{datetime.datetime.now(datetime.timezone.utc).strftime("%m/%d/%Y %H:%M:%S.%f")} [ {self.__timezone__} ] [ WARN ]: {str(msg).strip()}\n')
		return self

	def error(self, msg: typing.Any) -> Logger:
		"""
		Writes a message to the log on ERROR level
		:param msg: The message to write
		:return: This log writer instance
		:raises IOError: If log is closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(f'{datetime.datetime.now(datetime.timezone.utc).strftime("%m/%d/%Y %H:%M:%S.%f")} [ {self.__timezone__} ] [ ERROR ]: {str(msg).strip()}\n')
		return self

	def critical(self, msg: typing.Any) -> Logger:
		"""
		Writes a message to the log on CRITICAL level
		:param msg: The message to write
		:return: This log writer instance
		:raises IOError: If log is closed
		"""

		if self.__state__ is False:
			raise IOError('Log is closed')

		self.__stream__.write(f'{datetime.datetime.now(datetime.timezone.utc).strftime("%m/%d/%Y %H:%M:%S.%f")} [ {self.__timezone__} ] [ CRITICAL ]: {str(msg).strip()}\n')
		return self
