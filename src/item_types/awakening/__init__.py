"""Awakening enhancement module for armor/weapons.

This module provides the complete implementation for awakening enhancement,
including configuration, simulation engine, and TUI screens.
"""

from src.core.base import ItemTypeInfo, ItemTypeModule
from src.core.registry import ItemTypeRegistry

from .config import (
    AWAKENING_ENHANCEMENT_RATES,
    ANVIL_THRESHOLDS_AWAKENING,
    AWAKENING_MATERIAL_COSTS,
    RESTORATION_SCROLL_COSTS,
    RESTORATION_SUCCESS_RATE,
    HEPTA_OKTA_SUCCESS_RATE,
    VALKS_MULTIPLIER_10,
    VALKS_MULTIPLIER_50,
    VALKS_MULTIPLIER_100,
    ROMAN_NUMERALS,
)
from .engine import (
    AwakeningEngine,
    EnhancementEngine,  # Alias for compatibility
    MarketPrices,
    SimulationConfig,
    SimulationResult,
    StepResult,
)


@ItemTypeRegistry.register
class AwakeningModule(ItemTypeModule):
    """Awakening enhancement module for armor and weapons.

    This is the primary enhancement system in BDM, allowing players
    to enhance their gear from +0 to +X with increasing difficulty.
    """

    @classmethod
    def get_info(cls) -> ItemTypeInfo:
        return ItemTypeInfo(
            id="awakening",
            name="Awakening (Armor/Weapons)",
            description="Enhance armor and weapons from +0 to +X",
            implemented=True,
            min_level=0,
            max_level=10,
            has_restoration=True,
            has_failsafe_paths=True,  # Hepta/Okta paths
        )

    @classmethod
    def get_engine_class(cls) -> type:
        return AwakeningEngine

    @classmethod
    def get_config_screen_class(cls) -> type:
        # Import here to avoid circular imports
        from src.tui import ConfigScreen
        return ConfigScreen

    @classmethod
    def get_simulation_screen_class(cls) -> type:
        # Import here to avoid circular imports
        from src.tui import SimulationScreen
        return SimulationScreen

    @classmethod
    def get_strategy_screens(cls) -> list[type]:
        # Import here to avoid circular imports
        from src.tui import HeptaOktaStrategyScreen, RestorationStrategyScreen
        return [HeptaOktaStrategyScreen, RestorationStrategyScreen]


__all__ = [
    # Module
    "AwakeningModule",
    # Config
    "AWAKENING_ENHANCEMENT_RATES",
    "ANVIL_THRESHOLDS_AWAKENING",
    "AWAKENING_MATERIAL_COSTS",
    "RESTORATION_SCROLL_COSTS",
    "RESTORATION_SUCCESS_RATE",
    "HEPTA_OKTA_SUCCESS_RATE",
    "VALKS_MULTIPLIER_10",
    "VALKS_MULTIPLIER_50",
    "VALKS_MULTIPLIER_100",
    "ROMAN_NUMERALS",
    # Engine
    "AwakeningEngine",
    "EnhancementEngine",
    "MarketPrices",
    "SimulationConfig",
    "SimulationResult",
    "StepResult",
]
