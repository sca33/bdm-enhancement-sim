"""Enhancement configuration - facade for backward compatibility.

This module re-exports from src.item_types.awakening.config.
New code should import directly from the item type module.
"""

from src.item_types.awakening.config import (
    AWAKENING_ENHANCEMENT_RATES,
    ANVIL_THRESHOLDS_AWAKENING,
    AWAKENING_MATERIAL_COSTS,
    RESTORATION_SCROLL_COSTS,
    RESTORATION_SUCCESS_RATE,
    HEPTA_OKTA_SUCCESS_RATE,
    VALKS_MULTIPLIER_10,
    VALKS_MULTIPLIER_50,
    VALKS_MULTIPLIER_100,
    ARKRAM_PROPHECY_BONUS,
    W_BLESSING_ENABLED,
    OGIER_BLESSING_VARIANTS,
)

# Accessory thresholds kept here as they're not part of awakening module yet
ANVIL_THRESHOLDS_ACCESSORY: dict[int, int] = {
    1: 0,
    2: 0,
    3: 2,
    4: 3,
    5: 4,
    6: 12,
    7: 25,
    8: 100,
    9: 334,
}

__all__ = [
    "AWAKENING_ENHANCEMENT_RATES",
    "ANVIL_THRESHOLDS_AWAKENING",
    "ANVIL_THRESHOLDS_ACCESSORY",
    "AWAKENING_MATERIAL_COSTS",
    "RESTORATION_SCROLL_COSTS",
    "RESTORATION_SUCCESS_RATE",
    "HEPTA_OKTA_SUCCESS_RATE",
    "VALKS_MULTIPLIER_10",
    "VALKS_MULTIPLIER_50",
    "VALKS_MULTIPLIER_100",
    "ARKRAM_PROPHECY_BONUS",
    "W_BLESSING_ENABLED",
    "OGIER_BLESSING_VARIANTS",
]
