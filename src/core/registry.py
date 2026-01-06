"""Registry for item type modules."""

from typing import Dict, Optional, Type

from .base import ItemTypeModule, ItemTypeInfo


class ItemTypeRegistry:
    """Central registry for all item type modules.

    This singleton class manages registration and lookup of item type modules.
    Use the @ItemTypeRegistry.register decorator to register modules.

    Example:
        @ItemTypeRegistry.register
        class AwakeningModule(ItemTypeModule):
            ...
    """

    _modules: Dict[str, Type[ItemTypeModule]] = {}

    @classmethod
    def register(cls, module_class: Type[ItemTypeModule]) -> Type[ItemTypeModule]:
        """Decorator to register an item type module.

        Args:
            module_class: The module class to register

        Returns:
            The same module class (for decorator chaining)
        """
        info = module_class.get_info()
        cls._modules[info.id] = module_class
        return module_class

    @classmethod
    def get(cls, item_type_id: str) -> Optional[Type[ItemTypeModule]]:
        """Get a module by its ID.

        Args:
            item_type_id: The unique identifier of the item type

        Returns:
            The module class, or None if not found
        """
        return cls._modules.get(item_type_id)

    @classmethod
    def get_all(cls) -> Dict[str, Type[ItemTypeModule]]:
        """Get all registered modules.

        Returns:
            Dictionary mapping item type IDs to module classes
        """
        return dict(cls._modules)

    @classmethod
    def get_implemented(cls) -> Dict[str, Type[ItemTypeModule]]:
        """Get only implemented (ready to use) modules.

        Returns:
            Dictionary of implemented modules
        """
        return {
            k: v for k, v in cls._modules.items()
            if v.get_info().implemented
        }

    @classmethod
    def get_all_info(cls) -> list[ItemTypeInfo]:
        """Get info for all modules, sorted with implemented first.

        Returns:
            List of ItemTypeInfo, sorted by implementation status then name
        """
        return sorted(
            [m.get_info() for m in cls._modules.values()],
            key=lambda x: (not x.implemented, x.name)
        )

    @classmethod
    def is_implemented(cls, item_type_id: str) -> bool:
        """Check if an item type is implemented.

        Args:
            item_type_id: The unique identifier of the item type

        Returns:
            True if the module exists and is implemented
        """
        module = cls.get(item_type_id)
        return module is not None and module.get_info().implemented
