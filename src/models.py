"""Data models for BDM enhancement simulation.

This module is kept for potential future expansion.
Core simulation models are in simulator.py.
"""
from dataclasses import dataclass
from enum import Enum


class GearGrade(Enum):
    """Gear rarity grades in BDM."""
    MYSTICAL = "mystical"     # 신화
    ABYSSAL = "abyssal"       # 심연
    PRIMAL = "primal"         # 태고
    CHAOS = "chaos"           # 혼돈
    VOID = "void"             # 공허
    DAWN = "dawn"             # 새벽


class GearSlot(Enum):
    """Equipment slots that support awakening enhancement."""
    MAIN_WEAPON = "main_weapon"
    SUB_WEAPON = "sub_weapon"
    HELMET = "helmet"
    ARMOR = "armor"
    GLOVES = "gloves"
    SHOES = "shoes"


# Korean names for awakening levels (for display)
AWAKENING_LEVEL_NAMES = {
    1: "문 (I)",      # Moon
    2: "평 (II)",     # Plain
    3: "장 (III)",    # Long
    4: "광 (IV)",     # Light
    5: "소 (V)",      # Small
    6: "중 (VI)",     # Medium
    7: "고 (VII)",    # High
    8: "태 (VIII)",   # Grand
    9: "유 (IX)",     # Flowing
    10: "동 (X)",     # Supreme
}
