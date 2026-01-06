"""Base abstractions for item type modules."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ItemTypeInfo:
    """Metadata about an item type for display and configuration.

    Attributes:
        id: Unique identifier (e.g., "awakening", "totem")
        name: Display name (e.g., "Awakening (Armor/Weapons)")
        description: Brief description for the selection screen
        implemented: Whether this module is ready to use
        min_level: Minimum enhancement level
        max_level: Maximum enhancement level
        has_restoration: Whether restoration mechanic exists
        has_failsafe_paths: Whether Hepta/Okta style paths exist
    """
    id: str
    name: str
    description: str
    implemented: bool = False
    min_level: int = 0
    max_level: int = 10
    has_restoration: bool = True
    has_failsafe_paths: bool = False


class ItemTypeModule(ABC):
    """Abstract base class for item type modules (plugin pattern).

    Each item type (awakening, totem, rune, etc.) should implement
    this class to register with the system.
    """

    @classmethod
    @abstractmethod
    def get_info(cls) -> ItemTypeInfo:
        """Return metadata about this item type."""
        pass

    @classmethod
    @abstractmethod
    def get_engine_class(cls) -> type:
        """Return the simulation engine class for this item type."""
        pass

    @classmethod
    @abstractmethod
    def get_config_screen_class(cls) -> type:
        """Return the TUI config screen class."""
        pass

    @classmethod
    @abstractmethod
    def get_simulation_screen_class(cls) -> type:
        """Return the TUI simulation screen class."""
        pass

    @classmethod
    def get_strategy_screens(cls) -> list[type]:
        """Return additional strategy analysis screens (optional).

        Override this method to provide strategy analysis screens
        specific to this item type.
        """
        return []
