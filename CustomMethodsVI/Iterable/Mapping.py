from __future__ import annotations

import collections
import threading
import typing

from . import Iterable
from .. import Exceptions
from .. import Misc
from .. import Synchronization


class Mapping[K: typing.Hashable, V](Iterable.Iterable[dict[K, V], tuple[K, V]], collections.abc.Mapping):
	"""
	Base iterable class for CM-VI mappings
	"""

	def __init__(self, collection: collections.abc.Mapping[K, V] = ...):
		"""
		Base iterable class for CM-VI mappings\n
		- Constructor -
		:param collection: The mapping to build from
		"""

		super().__init__({} if collection is None or collection is ... else dict(collection))

	def __contains__(self, item: K) -> bool:
		"""
		:param item: The key to search for
		:return: If the key exists within this collection
		"""

		return item in self.__buffer__

	def __repr__(self) -> str:
		"""
		:return: The string representation of this mapping
		"""

		return repr(self.__buffer__)

	def __str__(self) -> str:
		"""
		:return: The string representation of this mapping
		"""

		return str(self.__buffer__)

	def __iter__(self) -> collections.abc.Iterator[tuple[K, V]]:
		"""
		:return: The iterator for this iterable
		"""

		return iter(self.__buffer__.items())

	def __getitem__(self, key: K) -> V:
		"""
		Gets a key's associated value from this mapping
		:param key: The key to get
		:return: The associated element
		:raises KeyError: If the specified key does not exist
		"""

		return self.__buffer__[key]

	def __or__(self, other: collections.abc.Mapping[K, V]) -> Mapping[K, V]:
		"""
		Merges this mapping and another mapping
		:param other: The other mapping
		:return: The merged mapping
		"""

		return type(self)(self.__buffer__ | dict(other))

	def copy[I: Mapping](self: I) -> I:
		"""
		:return: A copy of this mapping
		"""

		return type(self)(self.__buffer__.copy())

	def get_or_default(self, key: K, default: typing.Optional[V] = None) -> typing.Optional[V]:
		"""
		Gets the item at the specified key or 'default' if key does not exist
		:param key: The key to retrieve
		:param default: The default item to return if key does not exist
		:return: The item at 'key' or 'default' if does not exist
		"""

		return self.__buffer__.get(key, default)

	def keys(self) -> collections.abc.KeysView[K]:
		"""
		:return: A view of all keys in this mapping
		"""

		return self.__buffer__.keys()

	def values(self) -> collections.abc.ValuesView[V]:
		"""
		:return: A view of all values in this mapping
		"""

		return self.__buffer__.values()


class MutableMapping[K, V](Mapping[K, V], collections.abc.MutableMapping):
	"""
	Mapping allowing modifications
	"""

	def __delitem__(self, key: K) -> None:
		"""
		Deletes a key from this mapping
		:param key: The key or keys to delete
		:raises KeyError: If the specified key does not exist
		"""

		del self.__buffer__[key]

	def __setitem__(self, key: K | tuple[K, ...], value: V) -> None:
		"""
		Sets a key in this mapping
		:param key: The key or keys to modify
		:param value: The value to set
		"""

		self.__buffer__[key] = value

	def __ior__(self, other: typing.Mapping[K, V]) -> MutableMapping[K, V]:
		"""
		Merges this mapping and another mapping
		:param other: The other mapping
		:return: This mapping
		"""

		self.update(other)
		return self

	def clear(self) -> None:
		"""
		Clears the mapping
		"""

		self.__buffer__.clear()

	def get_or_insert(self, key: K, default: typing.Optional[V] = None) -> V:
		"""
		Gets the item at the specified key or inserts and returns 'default' if key does not exist
		:param key: The key to retrieve
		:param default: The default item to insert and return if key does not exist
		:return: The item at 'key'
		"""

		return self.__buffer__.setdefault(key, default)

	def pop(self, key: K, default: typing.Optional[V] = ...) -> V:
		"""
		Removes and returns the element at the specified key
		:param key: The key to remove and return
		:param default: The default value to return or raise KeyError if not supplied
		:return: The removed element
		"""

		return self.__buffer__.pop(key) if default is ... else self.__buffer__.pop(key, default)

	def pop_last(self) -> tuple[K, V]:
		"""
		Removes and returns the last key-value pair added to this mapping
		:return: The removed pair
		"""

		return self.__buffer__.popitem()

	def update(self, mapping: collections.abc.Mapping[K, V], /, **kwargs) -> Mapping[K, V]:
		"""
		Adds the key-value pairs from the specified mapping to this one in-place\n
		Duplicate keys are overwritten
		:param mapping: The mapping to add
		:return: This mapping
		"""

		self.__buffer__.update(mapping, **kwargs)
		return self


class LockedMapping[K, V](MutableMapping):
	"""
	Thread safe mapping using locks
	"""

	def __init__(self, mapping: collections.abc.Mapping[K, V] = ..., *, lock: threading.Lock | Synchronization.SynchronizationPrimitive = Synchronization.SpinLock()):
		"""
		Thread safe mapping using locks\n
		- Constructor -
		:param mapping: The initial mapping
		:param lock: The lock to use for operations
		"""

		Misc.raise_ifn(isinstance(lock, (threading.Lock, Synchronization.SynchronizationPrimitive)), Exceptions.InvalidArgumentException(LockedMapping.__init__, 'lock', type(lock), (threading.Lock, Synchronization.SynchronizationPrimitive)))
		super().__init__(mapping)
		self.__lock__: threading.Lock | Synchronization.SpinLock | Synchronization.ReaderWriterLock = lock

	def __contains__(self, key: K) -> bool:
		with self.read_lock():
			return super().__contains__(key)

	def __eq__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__eq__(other)

	def __ne__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__ne__(other)

	def __gt__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__gt__(other)

	def __lt__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__lt__(other)

	def __ge__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__ge__(other)

	def __le__(self, other: Mapping[K, V]) -> bool:
		with self.read_lock():
			return super().__le__(other)

	def __bool__(self) -> bool:
		with self.read_lock():
			return super().__bool__()

	def __len__(self) -> int:
		with self.read_lock():
			return super().__len__()

	def __repr__(self) -> str:
		with self.read_lock():
			return super().__repr__()

	def __str__(self) -> str:
		with self.read_lock():
			return super().__str__()

	def __iter__(self) -> collections.abc.Iterator[tuple[K, V]]:
		keys: tuple[K, ...] = tuple(self.keys())

		for key in keys:
			yield key, self[key]

	def __delitem__(self, key: K) -> None:
		with self.write_lock():
			super().__delitem__(key)

	def __setitem__(self, key: K, value: V) -> None:
		with self.write_lock():
			super().__setitem__(key, value)

	def __getitem__(self, key: K) -> V:
		with self.read_lock():
			return super().__getitem__(key)

	def __or__(self, other: collections.abc.Mapping[K, V]) -> Mapping[K, V]:
		with self.read_lock():
			return type(self)(self.__buffer__ | dict(other))

	def clear(self) -> None:
		with self.write_lock():
			self.__buffer__.clear()

	def copy[I: LockedMapping](self: I) -> I:
		with self.read_lock():
			return type(self)(self.__buffer__.copy())

	def get_or_default(self, key: K, default: typing.Optional[V] = None) -> typing.Optional[V]:
		with self.read_lock():
			return self.__buffer__.get(key, default)

	def get_or_insert(self, key: K, default: typing.Optional[V] = None) -> V:
		with self.write_lock():
			return self.__buffer__.setdefault(key, default)

	def pop(self, key: K, default: typing.Optional[V] = ...) -> V:
		with self.write_lock():
			return self.__buffer__.pop(key) if default is ... else self.__buffer__.pop(key, default)

	def pop_last(self) -> tuple[K, V]:
		with self.write_lock():
			return self.__buffer__.popitem()

	def update(self, mapping: collections.abc.Mapping[K, V], /, **kwargs) -> Mapping[K, V]:
		with self.write_lock():
			self.__buffer__.update(mapping, **kwargs)
			return self

	def keys(self) -> collections.abc.KeysView[K]:
		with self.read_lock():
			return self.__buffer__.keys()

	def values(self) -> collections.abc.ValuesView[V]:
		with self.read_lock():
			return self.__buffer__.values()

	def acquire_read_lock(self) -> bool:
		"""
		Acquires the reader lock if an RW lock, otherwise acquires the lock\n
		Blocks until lock is acquired
		:return: Whether the lock was acquired
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__.acquire()
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.acquire_reader()

	def acquire_write_lock(self) -> bool:
		"""
		Acquires the writer lock if an RW lock, otherwise acquires the lock\n
		Blocks until lock is acquired
		:return: Whether the lock was acquired
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__.acquire()
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.acquire_writer()

	def read_lock(self) -> threading.Lock | Synchronization.SynchronizationPrimitive | Synchronization.ReaderWriterLock.Lock:
		"""
		Returns the reader lock if an RW lock, otherwise the lock
		:return: The lock object for context management
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.reader()

	def write_lock(self) -> threading.Lock | Synchronization.SynchronizationPrimitive | Synchronization.ReaderWriterLock.Lock:
		"""
		Returns the reader lock if an RW lock, otherwise the lock
		:return: The lock object for context management
		"""

		if isinstance(self.__lock__, (threading.Lock, Synchronization.SpinLock)):
			return self.__lock__
		elif isinstance(self.__lock__, Synchronization.ReaderWriterLock):
			return self.__lock__.writer()


class MultiMapping[K: typing.Hashable, V](Iterable.Iterable[dict[K, list[V]], tuple[K, tuple[V, ...]]], collections.abc.Mapping):
	"""
	Base iterable class for CM-VI multi-mappings
	"""

	def __init__(self, mapping: collections.abc.Mapping[K, V | collections.abc.Iterable[V]] = ...):
		"""
		Base iterable class for CM-VI mappings\n
		- Constructor -
		:param mapping: The mapping to build from
		"""

		super().__init__({} if mapping is None or mapping is ... else {k: list(v) if isinstance(v, tuple) else [v] for k, v in mapping.items()})

	def __contains__(self, item: K) -> bool:
		"""
		:param item: The key to search for
		:return: If the key exists within this collection
		"""

		return item in self.__buffer__

	def __repr__(self) -> str:
		"""
		:return: The string representation of this mapping
		"""

		return repr(self.__buffer__)

	def __str__(self) -> str:
		"""
		:return: The string representation of this mapping
		"""

		return str(self.__buffer__)

	def __iter__(self) -> collections.abc.Iterator[tuple[K, collections.abc.ValuesView[V]]]:
		"""
		:return: An iterator iterating the key-value pairs
		"""

		for k, v in self.__buffer__.items():
			yield k, tuple(v)

	def __getitem__(self, key: K) -> tuple[V, ...]:
		"""
		Gets a key's associated values from this mapping
		:param key: The key to get
		:return: The associated elements
		:raises KeyError: If the specified key does not exist
		"""

		return tuple(self.__buffer__[key])

	def __or__(self, other: collections.abc.Mapping[K, V]) -> Mapping[K, V]:
		"""
		Merges this mapping and another mapping
		:param other: The other mapping
		:return: The merged mapping
		"""

		result: dict[K, list[V]] = self.__buffer__

		for k, v in other.items():
			if isinstance(v, tuple) and k in result:
				result[k].extend(v)
			elif isinstance(v, tuple):
				result[k] = list(v)
			elif k in result:
				result[k].append(v)
			else:
				result[k] = [v]

		return type(self)(result)

	def copy[I: MultiMapping](self: I) -> I:
		"""
		:return: A copy of this mapping
		"""

		return type(self)(self.__buffer__.copy())

	def get_or_default(self, key: K, default: typing.Optional[tuple[V, ...]] = ()) -> typing.Optional[tuple[V, ...]]:
		"""
		Gets the items at the specified key or 'default' if key does not exist
		:param key: The key to retrieve
		:param default: The default item to return if key does not exist
		:return: The item at 'key' or 'default' if does not exist
		"""

		if key in self.__buffer__:
			return tuple(self.__buffer__[key])
		else:
			return default

	def keys(self) -> collections.abc.KeysView[K]:
		"""
		:return: A view of all keys in this mapping
		"""

		return self.__buffer__.keys()

	def values(self) -> collections.abc.ValuesView[list[V]]:
		"""
		:return: A view of all values in this mapping
		"""

		return self.__buffer__.values()


class MutableMultiMapping[K, V](MultiMapping[K, V], collections.abc.MutableMapping):
	"""
	Multi-mapping allowing modifications
	"""

	def __delitem__(self, key: K) -> None:
		"""
		Deletes a key from this mapping
		:param key: The key or keys to delete
		:raises KeyError: If the specified key does not exist
		"""

		del self.__buffer__[key]

	def __setitem__(self, key: K | tuple[K, ...], value: V) -> None:
		"""
		Sets a key in this mapping
		:param key: The key or keys to modify
		:param value: The value to set
		"""

		self.__buffer__.setdefault(key, []).append(value)

	def __ior__(self, other: typing.Mapping[K, V]) -> MutableMapping[K, V]:
		"""
		Merges this mapping and another mapping
		:param other: The other mapping
		:return: This mapping
		"""

		self.update(other)
		return self

	def clear(self) -> None:
		"""
		Clears the mapping
		"""

		self.__buffer__.clear()

	def delete(self, key: K, value: V) -> None:
		"""
		Removes the specific value from this mapping
		:param key: The key to remove
		:param value: The value to remove
		"""

		values: typing.Optional[list[V]] = self.__buffer__.get(key)
		Misc.raise_if(values is None, KeyError(str(key)))
		values.remove(value)

		if len(values) == 0:
			del self.__buffer__[key]

	def get_or_insert(self, key: K, default: typing.Optional[V] = None) -> V:
		"""
		Gets the item at the specified key or inserts and returns 'default' if key does not exist
		:param key: The key to retrieve
		:param default: The default item to insert and return if key does not exist
		:return: The item at 'key'
		"""

		return self.__buffer__.setdefault(key, default)

	def pop(self, key: K, default: typing.Optional[V] = ...) -> tuple[V, ...]:
		"""
		Removes and returns the last element added at the specified key
		:param key: The key to pop and return
		:param default: The default value to return or raise KeyError if not supplied
		:return: The removed element
		"""

		if key not in self.__buffer__ and default is not ...:
			return default

		values: list[V] = self.__buffer__[key]
		value: V = values.pop()

		if len(values) == 0:
			del self.__buffer__[key]

		return value

	def pop_last(self) -> tuple[K, tuple[V, ...]]:
		"""
		Removes and returns the last key-value pair added to this mapping
		:return: The removed pair
		"""

		key, values = self.__buffer__.popitem()
		return key, tuple(values)

	def update(self, mapping: collections.abc.Mapping[K, V], /, **kwargs) -> Mapping[K, V]:
		"""
		Adds the key-value pairs from the specified mapping to this one in-place
		:param mapping: The mapping to add
		:return: This mapping
		"""

		for k, v in mapping.items():
			if isinstance(v, tuple) and k in self.__buffer__:
				self.__buffer__[k].extend(v)
			elif isinstance(v, tuple):
				self.__buffer__[k] = list(v)
			elif k in self.__buffer__:
				self.__buffer__[k].append(v)
			else:
				self.__buffer__[k] = [v]

		return self


class MappingView[K, V](Iterable.IterableView[Mapping, tuple[K, V]]):
	def __init__(self, mapping: Mapping[K, V]):
		"""
		Class allowing a view into a collection\n
		- Constructor -
		:param mapping: The iterable to view
		"""

		Misc.raise_ifn(isinstance(mapping, Mapping), Exceptions.InvalidArgumentException(MappingView.__init__, 'iterable', type(mapping), (Mapping,)))
		super().__init__(mapping)

	def __getitem__(self, key: K) -> V:
		"""
		Gets a key's associated value from this view's mapping
		:param key: The key to get
		:return: The associated element
		:raises KeyError: If the specified key does not exist
		"""

		return self.__iterable__[key]

	def get_or_default(self, key: K, default: typing.Optional[V] = None) -> typing.Optional[V]:
		"""
		Gets the item at the specified key or 'default' if key does not exist
		:param key: The key to retrieve
		:param default: The default item to return if key does not exist
		:return: The item at 'key' or 'default' if does not exist
		"""

		return self.__iterable__.get_or_default(key, default)

	def keys(self) -> collections.abc.KeysView[K]:
		"""
		:return: A view of all keys in this mapping
		"""

		return self.__iterable__.keys()

	def values(self) -> collections.abc.ValuesView[V]:
		"""
		:return: A view of all values in this mapping
		"""

		return self.__iterable__.values()
