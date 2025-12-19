from __future__ import annotations

import os
import shutil
import datetime
import typing

from . import Exceptions
from . import Misc
from . import Stream


class File:
	"""
	Represents a single file-like object
	"""

	def __init__(self, path: str | File):
		"""
		Represents a single file-like object
		- Constructor -
		:param path: The path of the file
		:raises IsADirectoryError: If the file at the specified path is a directory
		:raises InvalidArgumentException: If 'path' is not a string or File instance
		"""

		Misc.raise_ifn(isinstance(path, (str, File)), Exceptions.InvalidArgumentException(File.__init__, 'path', type(path), (str, File)))
		self.__fpath__: str = ''
		self.__fpath__ = path.__fpath__ if isinstance(path, File) else str(path)
		self.__streams__: list[Stream.FileStream] = []

		if os.path.isdir(self.__fpath__):
			raise IsADirectoryError(f'The object at "{self.__fpath__}" is a directory')

	def __repr__(self) -> str:
		return f'<{type(self).__name__.upper()}: "{self.__fpath__}">'

	def __eq__(self, other: File) -> bool:
		return isinstance(other, File) and self.abspath == other.abspath

	def __hash__(self) -> int:
		return hash(self.abspath)

	def __str__(self) -> str:
		return self.__fpath__

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		pass

	def rename(self, new_name: str) -> None:
		"""
		Renames this file to a new name
		:param new_name: The new name; should not include slashes
		:raises InvalidArgumentException: If 'path' is not a string
		"""

		Misc.raise_ifn(isinstance(new_name, str), Exceptions.InvalidArgumentException(File.rename, 'new_name', type(new_name), (str,)))
		os.rename(self.__fpath__, self.parent.file(new_name).__fpath__)

	def single_write(self, data: str | bytes | bytearray, encoding: str = 'utf-8') -> None:
		"""
		Opens the file, writes data, and closes the file
		For multiple write operations, use 'File.open'
		:param data: The data to write to file
		:param encoding: The encoding to use for non-binary data
		:raises InvalidArgumentException: If 'data' is not a string, bytes object, or bytearray
		"""

		Misc.raise_ifn(isinstance(data, (str, bytes, bytearray)), Exceptions.InvalidArgumentException(File.single_write, 'data', type(data), (str, bytes, bytearray)))

		with self.open('wb' if isinstance(data, (bytes, bytearray)) else 'w', encoding) as f:
			f.write(data)

	def single_append(self, data: str | bytes | bytearray, encoding: str = 'utf-8') -> None:
		"""
		Opens the file, writes data, and closes the file
		For multiple write operations, use 'File.open'
		:param data: The data to write to file
		:param encoding: The encoding to use for non-binary data
		:raises InvalidArgumentException: If 'data' is not a string, bytes object, or bytearray
		"""

		Misc.raise_ifn(isinstance(data, (str, bytes, bytearray)), Exceptions.InvalidArgumentException(File.single_write, 'data', type(data), (str, bytes, bytearray)))

		with self.open('ab' if isinstance(data, (bytes, bytearray)) else 'a', encoding) as f:
			f.write(data)

	def exists(self) -> bool:
		"""
		:return: Whether this file exists
		"""

		return os.path.isfile(self.__fpath__)

	def open(self, mode='r', encoding: str = 'utf-8') -> Stream.FileStream:
		"""
		Opens this file in the specified mode
		:param mode: The mode to open this file as
		:param encoding: If non-binary, the text encoding
		:return: A new filestream
		"""

		fstream = Stream.FileStream(self.__fpath__, mode, encoding)
		self.__streams__.append(fstream)
		return fstream

	def delete(self) -> bool:
		"""
		Deletes this file from disk
		:return: Whether the file existed before deletion
		"""

		if os.path.isfile(self.__fpath__):
			for fstream in self.__streams__:
				if not fstream.closed:
					fstream.close()

			self.__streams__.clear()
			os.remove(self.__fpath__)
			return True
		else:
			return False

	def create(self) -> bool:
		"""
		Creates the file at path
		:return: True if file did not exist otherwise False
		"""

		if os.path.isfile(self.__fpath__):
			return False
		else:
			open(self.__fpath__, 'x').close()
			return True

	def single_read(self, as_bytes: bool = False, encoding: str = 'utf-8') -> str | bytes:
		"""
		Opens the file, reads data, and closes the file
		For multiple read operations, use 'File.open'
		:param as_bytes: Whether to read binary or text data
		:param encoding: The encoding to use for non-binary data
		"""

		with self.open('rb' if as_bytes else 'r', encoding) as f:
			return f.read()

	@property
	def statsize(self) -> int:
		"""
		Gets the size of this file in bytes using 'os.stat'
		:return: The file size or -1 if non-existent
		"""

		if self.exists():
			return os.stat(self.__fpath__).st_size
		else:
			return -1

	@property
	def abspath(self) -> str:
		"""
		:return: The absolute filepath
		"""

		return os.path.abspath(self.__fpath__)

	@property
	def filepath(self) -> str:
		"""
		:return: The filepath
		"""

		return self.__fpath__

	@property
	def filename(self) -> str:
		"""
		:return: The filename without extension
		"""

		return os.path.basename(self.__fpath__).split('.')[0]

	@property
	def extension(self) -> str:
		"""
		:return: The last extension
		"""

		return os.path.basename(self.__fpath__).split('.')[-1]

	@property
	def full_extension(self) -> str:
		"""
		:return: The full extension (same as 'File.extension' if only one extension present)
		"""

		return os.path.basename(self.__fpath__).split('.', 1)[-1]

	@property
	def extensions(self) -> tuple[str, ...]:
		"""
		:return: All extensions as a tuple
		"""

		return tuple(os.path.basename(self.__fpath__).split('.')[1:])

	@property
	def basename(self) -> str:
		"""
		:return: The filename with extension
		"""

		return os.path.basename(self.__fpath__)

	@property
	def parent(self) -> Directory:
		"""
		:return: This file's parent directory
		"""

		return Directory(os.path.dirname(self.__fpath__))

	@property
	def times(self) -> tuple[datetime.datetime, datetime.datetime, datetime.datetime]:
		"""
		:return: A tuple of stat times (Access Time, Modified Time, Created Time)
		"""

		return (datetime.datetime.fromtimestamp(os.path.getatime(self.__fpath__), datetime.timezone.utc),
			datetime.datetime.fromtimestamp(os.path.getmtime(self.__fpath__), datetime.timezone.utc),
			datetime.datetime.fromtimestamp(os.path.getctime(self.__fpath__), datetime.timezone.utc))

	@property
	def time_accessed(self) -> typing.Optional[datetime.datetime]:
		"""
		:return: The last time this file was accessed if it exists or None
		"""

		return datetime.datetime.fromtimestamp(os.path.getatime(self.__fpath__)) if self.exists() else None

	@time_accessed.setter
	def time_accessed(self, new_time: datetime.datetime | int | float) -> None:
		"""
		Sets the 'accessed' time of the file
		:param new_time: The new 'accessed' time
		:raises FileNotFoundError: If the file does not exist
		:raises InvalidArgumentException: If 'new_time' is not a datetime, integer, or float
		"""

		if self.exists():
			Misc.raise_ifn(isinstance(new_time, (datetime.datetime, int, float)), Exceptions.InvalidArgumentException(File.time_accessed.setter, 'new_time', type(new_time), (datetime.datetime, int, float)))
			atime = new_time.timestamp() if isinstance(new_time, datetime.datetime) else float(new_time)
			mtime = self.time_modified.timestamp()
			os.utime(self.__fpath__, (atime, mtime))
		else:
			raise FileNotFoundError('The specified file does not exist')

	@property
	def time_modified(self) -> typing.Optional[datetime.datetime]:
		"""
		:return: The last time this file was modified if it exists or None
		"""

		return datetime.datetime.fromtimestamp(os.path.getmtime(self.__fpath__)) if self.exists() else None

	@time_modified.setter
	def time_modified(self, new_time: typing.Optional[datetime.datetime | int | float] = None) -> None:
		"""
		Sets the 'accessed' time of the file
		:param new_time: The new 'accessed' time
		:raises FileNotFoundError: If the file does not exist
		:raises InvalidArgumentException: If 'new_time' is not a datetime, integer, or float
		"""

		if self.exists():
			Misc.raise_ifn(isinstance(new_time, (datetime.datetime, int, float)), Exceptions.InvalidArgumentException(File.time_modified.setter, 'new_time', type(new_time), (datetime.datetime, int, float)))
			atime = self.time_accessed.timestamp()
			mtime = new_time.timestamp() if isinstance(new_time, datetime.datetime) else float(new_time)
			os.utime(self.__fpath__, (atime, mtime))
		else:
			raise FileNotFoundError('The specified file does not exist')

	@property
	def time_created(self) -> datetime.datetime:
		"""
		:return: The time this file was created if it exists or None
		"""

		return datetime.datetime.fromtimestamp(os.path.getctime(self.__fpath__))


class Directory:
	"""
	Represents a single directory
	"""

	def __init__(self, path: str | Directory):
		"""
		Represents a single directory
		- Constructor -
		:param path: (str | Directory) The path of the file or another directory object
		:raises OSError: If the file at the specified path is a file
		:raises InvalidArgumentException: If 'path' is not a string or Directory instace
		"""

		Misc.raise_ifn(isinstance(path, (str, Directory)), Exceptions.InvalidArgumentException(Directory.__init__, 'path', type(path), (str, Directory)))
		self.__dpath__: str = path.__dpath__ if isinstance(path, Directory) else str(path).translate(str.maketrans({'/': os.sep, '\\': os.sep})).rstrip(os.sep) + os.sep

		if os.path.isfile(self.__dpath__):
			raise OSError(f'The object at "{self.__dpath__}" is a file')

	def __repr__(self) -> str:
		return f'<{type(self).__name__.upper()}: "{self.__dpath__}">'

	def __eq__(self, other: Directory) -> bool:
		return isinstance(other, Directory) and self.abspath == other.abspath

	def __hash__(self) -> int:
		return hash(self.abspath)

	def __str__(self) -> str:
		return self.__dpath__

	def rename(self, new_name: str) -> None:
		"""
		Renames this file to a new name
		:param new_name: The new name; should not include slashes
		:raises InvalidArgumentException: If 'path' is not a string
		"""

		Misc.raise_ifn(isinstance(new_name, str), Exceptions.InvalidArgumentException(Directory.rename, 'new_name', type(new_name), (str,)))
		new_path: str = self.up().directory(new_name).__dpath__
		os.rename(self.__dpath__, new_path)
		self.__dpath__ = new_path

	def copy_to(self, dst: str | Directory) -> None:
		"""
		Copies this directory to the specified directory
		:param dst: The directory or path to copy to
		:raises InvalidArgumentException: If 'path' is not a string or Directory
		"""

		Misc.raise_ifn(isinstance(dst, (str, Directory)), Exceptions.InvalidArgumentException(Directory.copy_to, 'dst', type(dst), (str, Directory)))
		dpath: str = dst.__dpath__ if isinstance(dst, Directory) else str(dst)
		shutil.copytree(self.__dpath__, dpath)

	def cd(self, rel_path: str) -> Directory:
		"""
		Changes the directory
		:param rel_path: The relative path
		:return: The new directory
		:raises InvalidArgumentException: If 'rel_path' is not a string
		"""

		Misc.raise_ifn(isinstance(rel_path, str), Exceptions.InvalidArgumentException(Directory.cd, 'rel_path', type(rel_path), (str,)))
		return Directory(self.__dpath__ + rel_path.translate(str.maketrans({'/': os.sep, '\\': os.sep})).lstrip(os.sep))

	def up(self) -> Directory:
		"""
		:return: This directory's parent
		"""

		return Directory(self.__dpath__.rsplit(os.sep, 2)[0])

	def exists(self) -> bool:
		"""
		:return: If this directory exists
		"""

		return os.path.isdir(self.__dpath__)

	def create(self) -> bool:
		"""
		Creates this directory and all parents
		:return: If this directory did not already exist
		"""

		if not self.exists():
			os.makedirs(self.__dpath__, exist_ok=True)
			return True
		else:
			return False

	def createdir(self, subdir: str) -> Directory:
		"""
		Creates a new subdirectory
		:param subdir: The relative path
		:return: The new directory
		"""

		subdir = self.cd(subdir)
		subdir.create()
		return subdir

	def delete(self) -> bool:
		"""
		Deletes this directory and all contents
		:return: Whether this directory existed
		"""

		if os.path.isdir(self.__dpath__):
			shutil.rmtree(self.__dpath__)
			return True
		else:
			return False

	def delete_dir(self, subdir: str) -> bool:
		"""
		Deletes the specified subdirectory and all its contents
		Same as Directory.cd(subdir).delete()
		:param subdir: The subdirectory to delete
		:return: Whether the subdirectory existed
		"""

		return self.cd(subdir).delete()

	def delete_file(self, path: str) -> bool:
		"""
		Deletes the specified internal file
		:param path: The relative path
		:return: Whether the file existed
		:raises InvalidArgumentException: If 'path' is not a string
		"""

		Misc.raise_ifn(isinstance(path, str), Exceptions.InvalidArgumentException(Directory.delete_file, 'path', type(path), (str,)))
		fpath = self.__dpath__ + path.translate(str.maketrans({'/': os.sep, '\\': os.sep})).lstrip('/')

		if os.path.isfile(fpath):
			os.remove(fpath)
			return True
		else:
			return False

	def file(self, path: str) -> File:
		"""
		Returns a new 'File' pointing to the specified relative path
		The file may not exist and no new file is created
		:param path: The relative path
		:return: A new File object
		:raises InvalidArgumentException: If 'path' is not a string
		"""

		Misc.raise_ifn(isinstance(path, str), Exceptions.InvalidArgumentException(Directory.file, 'path', type(path), (str,)))
		return File(self.__dpath__ + path.translate(str.maketrans({'/': os.sep, '\\': os.sep})).lstrip(os.sep))

	def directory(self, path: str) -> Directory:
		"""
		Returns a new 'Directory' pointing to the specified relative path
		The directory may not exist and no new directory is created
		:param path: The relative path
		:return: A new Directory object
		:raises InvalidArgumentException: If 'path' is not a string
		"""

		Misc.raise_ifn(isinstance(path, str), Exceptions.InvalidArgumentException(Directory.directory, 'path', type(path), (str,)))
		return Directory(self.__dpath__ + path.translate(str.maketrans({'/': os.sep, '\\': os.sep})).lstrip(os.sep))

	@property
	def dirpath(self) -> str:
		"""
		:return: The internal path
		"""

		return self.__dpath__

	@property
	def abspath(self) -> str:
		"""
		:return: The internal path as an absolute path
		"""

		return os.path.abspath(self.__dpath__)

	@property
	def realpath(self) -> str:
		"""
		:return: The internal path as a real path
		"""

		return os.path.realpath(self.__dpath__)

	@property
	def dirname(self) -> str:
		"""
		:return: The name of this directory
		"""

		return self.__dpath__.split(os.sep)[-2]

	@property
	def parent(self) -> Directory:
		"""
		:return: This directory's parent directory
		"""

		return Directory(self.__dpath__.rsplit(os.sep, 2)[0])

	@property
	def contents(self) -> dict[str, tuple[File | Directory, ...]]:
		"""
		Recursively gets directory contents as a dict
		:return: A dictionary with two keys: 'files' and 'dirs'
		"""

		try:
			data = next(os.walk(self.__dpath__, True))
			return {'files': tuple(File(data[0] + x) for x in data[2]), 'dirs': tuple(Directory(data[0] + x) for x in data[1])}
		except StopIteration:
			return {}

	@property
	def files(self) -> tuple[File, ...]:
		"""
		:return: All sub-files of this directory
		"""

		try:
			data = next(os.walk(self.__dpath__, True))
			return tuple(File(data[0] + x) for x in data[2])
		except StopIteration:
			return tuple()

	@property
	def dirs(self) -> tuple[Directory, ...]:
		"""
		:return: All subdirectories of this directory
		"""

		try:
			data = next(os.walk(self.__dpath__, True))
			return tuple(Directory(data[0] + x) for x in data[1])
		except StopIteration:
			return tuple()
