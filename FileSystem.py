from __future__ import annotations

import os
import shutil
import datetime

from CustomMethodsVI import Stream


class File:
	"""
	[File] - Represents a single file-like object
	"""

	def __init__(self, path: str):
		"""
		[File] - Represents a single file-like object
		- Constructor -
		:param path: (str) The path of the file
		:raises IsADirectoryError: If the file at the specified path is a directory
		"""

		self.__fpath__ = str(path)
		self.__streams__ = []  # type: list[Stream.FileStream]

		if os.path.isdir(self.__fpath__):
			raise IsADirectoryError(f'The object at "{self.__fpath__}" is a directory')

	def __repr__(self) -> str:
		return f'<FILE: "{self.__fpath__}">'

	def __eq__(self, other: File) -> bool:
		return self.__fpath__ == other.__fpath__ if isinstance(other, File) else NotImplemented

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		pass

	def rename(self, new_name: str) -> None:
		"""
		Renames this file to a new name
		:param new_name: (str) The new name; should not include slashes
		:return: (None)
		"""

		os.rename(self.__fpath__, self.parentdir().file(new_name).__fpath__)

	def exists(self) -> bool:
		"""
		Existedness
		:return: (bool) Whether this file exists in path
		"""

		return os.path.isfile(self.__fpath__)

	def open(self, mode='r', encoding: str = 'utf-8') -> Stream.FileStream:
		"""
		Opens this file in the specified mode
		:param mode: The mode to open this file as
		:param encoding: If non-binary, the text encoding
		:return: (FileStream) A new filestream
		"""

		fstream = Stream.FileStream(self.__fpath__, mode, encoding)
		self.__streams__.append(fstream)
		return fstream

	def delete(self) -> bool:
		"""
		Deletes this file from disk
		:return: (bool) Whether the file existed before deletion
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

	def statsize(self) -> int:
		"""
		Gets the size of this file in bytes using os.stat
		:return: (int) The file size or -1 if non-existent
		"""

		if self.exists():
			return os.stat(self.__fpath__).st_size
		else:
			return -1

	def create(self) -> bool:
		"""
		Creates the file at path
		:return: (bool) True if file did not exist otherwise False
		"""

		if os.path.isfile(self.__fpath__):
			return False
		else:
			open(self.__fpath__, 'x').close()
			return True

	def filepath(self) -> str:
		"""
		Filepathness
		:return: (str) Returns the filepath
		"""

		return self.__fpath__

	def filename(self) -> str:
		"""
		Filenameness
		:return: (str) Returns the filename without extension
		"""

		return os.path.basename(self.__fpath__).split('.')[0]

	def extension(self) -> str:
		"""
		Extensionness
		:return: (str) Returns the last extension
		"""

		return os.path.basename(self.__fpath__).split('.')[-1]

	def full_extension(self) -> str:
		"""
		Extensionness
		:return: (str) Returns the full extension (same as File.extension if only one extension present)
		"""

		return os.path.basename(self.__fpath__).split('.', 1)[-1]

	def extensions(self) -> tuple[str, ...]:
		"""
		Extensionsness
		:return: (tuple[str, ...]) Returns all extensions as a tuple
		"""

		return tuple(os.path.basename(self.__fpath__).split('.')[1:])

	def basename(self) -> str:
		"""
		Basenameness
		:return: (str) Returns the filepath base name
		"""

		return os.path.basename(self.__fpath__)

	def parentdir(self) -> Directory:
		"""
		Returns the containing directory
		:return: (Directory) Parent directory
		"""

		return Directory(os.path.dirname(self.__fpath__))

	def times(self) -> tuple[datetime.datetime, datetime.datetime, datetime.datetime]:
		"""
		Returns the stat times of the file
		:return: (tuple[datetime.datetime]) Access Time, Modified Time, Created Time
		"""

		return (datetime.datetime.fromtimestamp(os.path.getatime(self.__fpath__), datetime.timezone.utc),
			datetime.datetime.fromtimestamp(os.path.getmtime(self.__fpath__), datetime.timezone.utc),
			datetime.datetime.fromtimestamp(os.path.getctime(self.__fpath__), datetime.timezone.utc))

	def time_accessed(self, atime: datetime.datetime | int | float = None) -> datetime.datetime | None:
		"""
		Sets the 'accessed' time of the file or if no value supplied, gets the 'accessed' time
		:param atime: (datetime.datetime or int or float) The new 'accessed' time
		:return: (datetime.datetime or None) The 'accessed' time if 'atime' is None else None
		"""

		if atime is None:
			return datetime.datetime.fromtimestamp(os.path.getatime(self.__fpath__))
		else:
			atime = atime.timestamp() if type(atime) is datetime.datetime else atime
			mtime = self.time_modified().timestamp()
			os.utime(self.__fpath__, (atime, mtime))

	def time_modified(self, mtime: datetime.datetime | int | float = None) -> datetime.datetime | None:
		"""
		Sets the 'modified' time of the file or if no value supplied, gets the 'modified' time
		:param mtime: (datetime.datetime or int or float) The new 'modified' time
		:return: (datetime.datetime or None) The 'modified' time if 'mtime' is None else None
		"""

		if mtime is None:
			return datetime.datetime.fromtimestamp(os.path.getmtime(self.__fpath__))
		else:
			atime = self.time_modified().timestamp()
			mtime = mtime.timestamp() if type(mtime) is datetime.datetime else mtime
			os.utime(self.__fpath__, (atime, mtime))

	def time_created(self) -> datetime.datetime:
		"""
		Gets the 'created' time of the file
		:return: (datetime.datetime) The 'created' time
		"""

		return datetime.datetime.fromtimestamp(os.path.getctime(self.__fpath__))


class Directory:
	"""
	[Directory] - Represents a single directory
	"""

	def __init__(self, path: str):
		"""
		[Directory] - Represents a single directory
		- Constructor -
		:param path: (str) The path of the file
		:raises OSError: If the file at the specified path is a file
		"""

		self.__dpath__ = str(path).replace('\\', '/').rstrip('/') + '/'

		if os.path.isfile(self.__dpath__):
			raise OSError(f'The object at "{self.__dpath__}" is a file')

	def __repr__(self) -> str:
		return f'<DIRECTORY: "{self.__dpath__}">'

	def __eq__(self, other: Directory) -> bool:
		return self.__dpath__ == other.__dpath__ if isinstance(other, Directory) else NotImplemented

	def rename(self, new_name: str) -> None:
		"""
		Renames this directory to a new name
		:param new_name: (str) The new name; should not include slashes
		:return: (None)
		"""

		os.rename(self.__dpath__, self.up().directory(new_name).__dpath__)

	def copyto(self, dst: str | Directory) -> False:
		"""
		Copies this directory to the specified directory
		:param dst: (str | Directory) The directory or path to copy to
		:return: (None)
		"""

		dpath: str = dst.__dpath__ if isinstance(dst, Directory) else str(dst)
		shutil.copytree(self.__dpath__, dpath)

	def contents(self) -> dict[str, tuple[File | Directory, ...]]:
		"""
		Recursively gets directory contents as a dict
		:return: (dict[str, tuple[File or Directory, ...]]) A dictionary with two keys: 'files' and 'dirs'
		"""

		try:
			data = next(os.walk(self.__dpath__, True))
			return {'files': tuple(File(data[0] + x) for x in data[2]), 'dirs': tuple(Directory(data[0] + x) for x in data[1])}
		except StopIteration:
			return {}

	def files(self) -> tuple[File, ...]:
		"""
		:return: (tuple[File, ...]) All sub-files of this directory
		"""

		try:
			data = next(os.walk(self.__dpath__, True))
			return tuple(File(data[0] + x) for x in data[2])
		except StopIteration:
			return tuple()

	def dirs(self) -> tuple[Directory, ...]:
		"""
		:return: (tuple[Directory, ...]) All sub-directories of this directory
		"""

		try:
			data = next(os.walk(self.__dpath__, True))
			return tuple(Directory(data[0] + x) for x in data[1])
		except StopIteration:
			return tuple()

	def cd(self, rel_path: str) -> Directory:
		"""
		Changes the directory
		:param rel_path: The relative path
		:return: (Directory) The new directory
		"""

		return Directory(self.__dpath__ + rel_path.replace('\\', '/').lstrip('/'))

	def up(self) -> Directory:
		"""
		Gets the parent directory
		:return: (Directory) The parent
		"""

		return Directory(self.__dpath__.rsplit('/', 2)[0])

	def exists(self) -> bool:
		"""
		Existedness
		:return: (bool) If the object at path is a directory
		"""

		return os.path.isdir(self.__dpath__)

	def create(self) -> bool:
		"""
		Creates this directory and all parents
		:return: (bool) If this directory did not already exist
		"""

		if not self.exists():
			os.makedirs(self.__dpath__, exist_ok=True)
			return True
		else:
			return False

	def createdir(self, subdir: str) -> Directory:
		"""
		Creates a new subdirectory
		:param subdir: (str) The relative path
		:return: (Directory) The new directory
		"""

		subdir = self.cd(subdir)
		subdir.create()
		return subdir

	def delete(self) -> bool:
		"""
		Deletes this directory and all contents
		:return: (bool) Whether this directory existed
		"""

		if os.path.isdir(self.__dpath__):
			shutil.rmtree(self.__dpath__)
			return True
		else:
			return False

	def deletedir(self, subdir: str) -> bool:
		"""
		Deletes the specified sub-directory and all its contents
		Same as Directory.cd(subdir).delete()
		:param subdir: (str) The sub-directory to delete
		:return: (bool) Whether the subdirectory existed
		"""

		return self.cd(subdir).delete()

	def delfile(self, path: str) -> bool:
		"""
		Deletes the specified internal file
		:param path: (str) The relative path
		:return: (bool) Whether the file existed
		"""

		fpath = self.__dpath__ + path.replace('\\', '/').lstrip('/')

		if os.path.isfile(fpath):
			os.remove(fpath)
			return True
		else:
			return False

	def file(self, path: str) -> File:
		"""
		Returns a new 'File' pointing to the specified relative path
		The file may not exist and no new file is created
		:param path: (str) The relative path
		:return: (File) A new File object
		"""

		return File(self.__dpath__ + path.replace('\\', '/').lstrip('/'))

	def directory(self, path: str) -> Directory:
		"""
		Returns a new 'Directory' pointing to the specified relative path
		The directory may not exist and no new directory is created
		:param path: (str) The relative path
		:return: (Directory) A new Directory object
		"""

		return Directory(self.__dpath__ + path.replace('\\', '/').lstrip('/'))

	def dirpath(self) -> str:
		"""
		Pathness
		:return: (str) The internal path
		"""

		return self.__dpath__

	def abspath(self) -> str:
		"""
		Pathness
		:return: (str) The internal path as an absolute path
		"""

		return os.path.abspath(self.__dpath__)

	def realpath(self) -> str:
		"""
		Pathness
		:return: (str) The internal path as a real path
		"""

		return os.path.realpath(self.__dpath__)

	def dirname(self) -> str:
		"""
		Nameness
		:return: (str) The name of this directory
		"""

		return self.__dpath__.split('/')[-2]
