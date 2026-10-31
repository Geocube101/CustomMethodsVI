from __future__ import annotations

import collections.abc
import threading
import typing

from . import Misc
from . import Stream
from . import Synchronization


class Component:
	__NEXT_COMPONENT_ID: int = 0

	def __init__(self):
		"""
		Base class representing a basic component
		"""

		uid: int
		Component.__NEXT_COMPONENT_ID = (uid := Component.__NEXT_COMPONENT_ID) + 1
		self.__uid__: int = (uid << 64) | threading.get_native_id()

	def __setstate__(self, state: dict[str, ...]) -> None:
		uid: int
		Component.__NEXT_COMPONENT_ID = (uid := Component.__NEXT_COMPONENT_ID) + 1
		self.__uid__: int = (uid << 64) | threading.get_native_id()

	def __getstate__(self) -> dict[str, ...]:
		return {}

	def __hash__(self) -> int:
		return self.__uid__

	def __eq__(self, other: Component) -> bool:
		return isinstance(other, Component) and other.__uid__ == self.__uid__

	@property
	def component_id(self) -> int:
		"""
		The ID of this component\n
		The ID is created using a static internal counter and thread native ID
		:return: The ID of this component
		"""

		return self.__uid__


class ComponentContainer:
	def __init__(self, *components: Component, frozen: bool = False):
		"""
		A component container containing a set of components
		:param components: The initial components in the container
		:param frozen: Whether the container is immutable
		"""

		Misc.raise_if(Stream.LinqStream(components).not_instance_of(Component).any(), TypeError('One or more components is not an instance of \'Component\''))
		self.__frozen__: bool = bool(frozen)
		self.__components__: set[Component] = set(components)

	def __contains__(self, component: Component) -> bool:
		return isinstance(component, Component) and component in self.__components__

	def __iter__(self) -> collections.abc.Iterator[Component]:
		return self.components

	def freeze(self) -> None:
		"""
		Freezes this container\n
		Any further modification will raise an error
		"""

		self.__frozen__ = True

	def frozen(self) -> ComponentContainer:
		"""
		Returns a frozen copy of this container\n
		Any modification to the copy will raise an error
		:return: This container frozen
		"""

		return ComponentContainer(*self.__components__, frozen=True)

	def get_component_by_id(self, uid: int) -> typing.Optional[Component]:
		"""
		Gets a stored component by ID
		:param uid: The component ID
		:return: The matching component or None if not in this container
		"""

		for component in self.__components__:
			if component.component_id == uid:
				return component

		return None

	def get_components_of_type[T: Component](self, component_type: type[T]) -> collections.abc.Iterator[T]:
		"""
		Gets all components of the specified type
		:param component_type: The component type
		:return: An iterator over all matching components
		"""

		if not issubclass(component_type, Component):
			return

		for component in self.__components__:
			if isinstance(component, component_type):
				yield component

	def add_components(self, *components: Component) -> ComponentContainer:
		"""
		Adds the components to this container
		:param components: The components to add
		:return: This container
		"""

		Misc.raise_if(self.is_frozen, RuntimeError('Component container is frozen'))
		Misc.raise_if(Stream.LinqStream(components).not_instance_of(Component).any(), TypeError('One or more components is not an instance of \'Component\''))
		self.__components__.update(components)
		return self

	def remove_components(self, *components: Component) -> ComponentContainer:
		"""
		Removes the components from this container
		:param components: The components to remove
		:return: This container
		"""

		Misc.raise_if(self.is_frozen, RuntimeError('Component container is frozen'))
		Stream.LinqStream(self.__components__).filter(lambda component: component not in components).apply(self.__components__)
		return self

	def clear(self) -> ComponentContainer:
		"""
		Clears this component container
		:return: This container
		"""

		Misc.raise_if(self.is_frozen, RuntimeError('Component container is frozen'))
		self.__components__.clear()
		return self

	def stream(self) -> Stream.LinqStream[Component]:
		"""
		:return: A LINQ Stream over all components in this container
		"""

		return Stream.LinqStream(self.__components__)

	@property
	def is_frozen(self) -> bool:
		"""
		:return: Whether this container is frozen
		"""

		return self.__frozen__

	@property
	def components(self) -> collections.abc.Iterator[Component]:
		"""
		:return: An iterator over all stored components
		"""

		return iter(self.__components__)


class ThreadedComponentContainer(ComponentContainer, Synchronization.Synchronization.LockUser):
	pass


__all__: list[str] = ['Component', 'ComponentContainer']
