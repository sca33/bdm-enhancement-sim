"""Accessory enhancement module (placeholder).

This module is not yet implemented. It will provide simulation
for accessory breakthrough mechanics when completed.
"""

from src.core.base import ItemTypeInfo, ItemTypeModule
from src.core.registry import ItemTypeRegistry


@ItemTypeRegistry.register
class AccessoryModule(ItemTypeModule):
    """Placeholder module for accessory breakthrough."""

    @classmethod
    def get_info(cls) -> ItemTypeInfo:
        return ItemTypeInfo(
            id="accessory",
            name="Accessories",
            description="Breakthrough accessories with different rates",
            implemented=False,
            min_level=0,
            max_level=9,
            has_restoration=True,
            has_failsafe_paths=False,
        )

    @classmethod
    def get_engine_class(cls) -> type:
        raise NotImplementedError("Accessory module not yet implemented")

    @classmethod
    def get_config_screen_class(cls) -> type:
        raise NotImplementedError("Accessory module not yet implemented")

    @classmethod
    def get_simulation_screen_class(cls) -> type:
        raise NotImplementedError("Accessory module not yet implemented")
