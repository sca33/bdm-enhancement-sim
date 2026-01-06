"""Relic enhancement module (placeholder).

This module is not yet implemented. It will provide simulation
for relic enhancement mechanics when completed.
"""

from src.core.base import ItemTypeInfo, ItemTypeModule
from src.core.registry import ItemTypeRegistry


@ItemTypeRegistry.register
class RelicModule(ItemTypeModule):
    """Placeholder module for relic enhancement."""

    @classmethod
    def get_info(cls) -> ItemTypeInfo:
        return ItemTypeInfo(
            id="relic",
            name="Relics",
            description="Enhance relics with unique mechanics",
            implemented=False,
            min_level=0,
            max_level=5,
            has_restoration=False,
            has_failsafe_paths=False,
        )

    @classmethod
    def get_engine_class(cls) -> type:
        raise NotImplementedError("Relic module not yet implemented")

    @classmethod
    def get_config_screen_class(cls) -> type:
        raise NotImplementedError("Relic module not yet implemented")

    @classmethod
    def get_simulation_screen_class(cls) -> type:
        raise NotImplementedError("Relic module not yet implemented")
