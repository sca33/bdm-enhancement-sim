"""Rune enhancement module (placeholder).

This module is not yet implemented. It will provide simulation
for rune enhancement mechanics when completed.
"""

from src.core.base import ItemTypeInfo, ItemTypeModule
from src.core.registry import ItemTypeRegistry


@ItemTypeRegistry.register
class RuneModule(ItemTypeModule):
    """Placeholder module for rune enhancement."""

    @classmethod
    def get_info(cls) -> ItemTypeInfo:
        return ItemTypeInfo(
            id="rune",
            name="Runes",
            description="Enhance runes for stat bonuses",
            implemented=False,
            min_level=0,
            max_level=5,
            has_restoration=False,
            has_failsafe_paths=False,
        )

    @classmethod
    def get_engine_class(cls) -> type:
        raise NotImplementedError("Rune module not yet implemented")

    @classmethod
    def get_config_screen_class(cls) -> type:
        raise NotImplementedError("Rune module not yet implemented")

    @classmethod
    def get_simulation_screen_class(cls) -> type:
        raise NotImplementedError("Rune module not yet implemented")
