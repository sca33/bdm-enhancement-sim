"""Simulation engine - facade for backward compatibility.

This module re-exports from src.item_types.awakening.engine.
New code should import directly from the item type module.
"""

from src.item_types.awakening.engine import (
    AwakeningEngine,
    EnhancementEngine,
    MarketPrices,
    SimulationConfig,
    SimulationResult,
    StepResult,
)

__all__ = [
    "AwakeningEngine",
    "EnhancementEngine",
    "MarketPrices",
    "SimulationConfig",
    "SimulationResult",
    "StepResult",
]
