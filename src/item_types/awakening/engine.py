"""Awakening enhancement simulation engine.

This module provides the simulation engine for awakening (armor/weapons) enhancement.
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from .config import (
    AWAKENING_ENHANCEMENT_RATES,
    ANVIL_THRESHOLDS_AWAKENING,
    RESTORATION_SUCCESS_RATE,
    HEPTA_OKTA_SUCCESS_RATE,
    VALKS_MULTIPLIER_10,
    VALKS_MULTIPLIER_50,
    VALKS_MULTIPLIER_100,
)
from src.market_config import (
    RESTORATION_PER_ATTEMPT,
    RESTORATION_MARKET_BUNDLE_SIZE,
    HEPTA_SUB_ENHANCEMENTS,
    OKTA_SUB_ENHANCEMENTS,
    HEPTA_OKTA_ANVIL_PITY,
    HEPTA_OKTA_CRYSTALS_PER_ATTEMPT,
    EXQUISITE_BLACK_CRYSTAL_RECIPE,
)


@dataclass
class MarketPrices:
    """Market prices for cost calculations."""
    crystal_price: int = 34_650_000           # Price per pristine black crystal
    restoration_bundle_price: int = 1_000_000_000_000  # Price for 200K scrolls (1T)
    valks_10_price: int = 0
    valks_50_price: int = 0
    valks_100_price: int = 0

    @property
    def restoration_attempt_cost(self) -> int:
        """Cost per restoration attempt (200 scrolls)."""
        if self.restoration_bundle_price == 0:
            return 0
        return (RESTORATION_PER_ATTEMPT * self.restoration_bundle_price) // RESTORATION_MARKET_BUNDLE_SIZE


@dataclass
class SimulationConfig:
    """Configuration for a simulation run."""
    start_level: int = 0
    target_level: int = 9
    restoration_from: int = 6
    use_hepta: bool = False
    use_okta: bool = False
    start_hepta: int = 0
    start_okta: int = 0
    valks_10_from: int = 1
    valks_50_from: int = 3
    valks_100_from: int = 5
    prices: MarketPrices = field(default_factory=MarketPrices)


@dataclass
class SimulationResult:
    """Result of a complete simulation run."""
    crystals: int
    scrolls: int
    silver: int
    exquisite_crystals: int
    attempts: int
    final_level: int
    anvil_energy: dict[int, int]
    valks_10_used: int = 0
    valks_50_used: int = 0
    valks_100_used: int = 0


@dataclass
class StepResult:
    """Result of a single enhancement step."""
    success: bool
    anvil_triggered: bool
    starting_level: int
    ending_level: int
    valks_used: Optional[str] = None
    restoration_attempted: bool = False
    restoration_success: bool = False
    # For Hepta/Okta
    is_hepta_okta: bool = False
    sub_progress: int = 0
    sub_pity: int = 0
    path_complete: bool = False
    path_name: str = ""


class AwakeningEngine:
    """Simulation engine for awakening (armor/weapons) enhancement.

    This engine handles:
    - Normal enhancement with anvil pity
    - Hepta/Okta sub-enhancement paths
    - Restoration scrolls
    - Valks bonuses
    - Resource tracking
    """

    def __init__(self, config: SimulationConfig, seed: Optional[int] = None):
        self.config = config
        self.rng = random.Random(seed)
        self.reset()

    def reset(self) -> None:
        """Reset simulation state to initial values."""
        self.level = self.config.start_level
        self.anvil_energy: dict[int, int] = {}

        # Resource tracking
        self.crystals = 0
        self.scrolls = 0
        self.silver = 0
        self.exquisite_crystals = 0
        self.valks_10_used = 0
        self.valks_50_used = 0
        self.valks_100_used = 0
        self.attempts = 0

        # Hepta/Okta state
        self.hepta_progress = self.config.start_hepta
        self.okta_progress = self.config.start_okta
        self.hepta_pity = 0
        self.okta_pity = 0

    def is_complete(self) -> bool:
        """Check if target level has been reached."""
        return self.level >= self.config.target_level

    def get_energy(self, level: int) -> int:
        """Get anvil energy for a specific level."""
        return self.anvil_energy.get(level, 0)

    def _add_energy(self, level: int) -> None:
        """Add 1 energy for a level."""
        self.anvil_energy[level] = self.get_energy(level) + 1

    def _reset_energy(self, level: int) -> None:
        """Reset energy for a level."""
        self.anvil_energy[level] = 0

    def _get_valks_for_level(self, target_level: int) -> Optional[str]:
        """Determine which Valks to use for a target level."""
        if self.config.valks_100_from > 0 and target_level >= self.config.valks_100_from:
            return "100"
        if self.config.valks_50_from > 0 and target_level >= self.config.valks_50_from:
            return "50"
        if self.config.valks_10_from > 0 and target_level >= self.config.valks_10_from:
            return "10"
        return None

    def _should_use_restoration(self) -> bool:
        """Check if restoration should be used at current level."""
        if self.config.restoration_from == 0:
            return False
        return self.level >= self.config.restoration_from

    def _should_use_hepta(self) -> bool:
        """Check if Hepta path should be used."""
        return ((self.config.use_hepta or self.hepta_progress > 0) and
                self.level == 7 and
                self.hepta_progress < HEPTA_SUB_ENHANCEMENTS)

    def _should_use_okta(self) -> bool:
        """Check if Okta path should be used."""
        return ((self.config.use_okta or self.okta_progress > 0) and
                self.level == 8 and
                self.okta_progress < OKTA_SUB_ENHANCEMENTS)

    def _get_exquisite_crystal_cost(self) -> int:
        """Calculate cost of one Exquisite Black Crystal."""
        prices = self.config.prices
        scroll_cost = (EXQUISITE_BLACK_CRYSTAL_RECIPE["restoration_scrolls"] *
                       prices.restoration_bundle_price) // RESTORATION_MARKET_BUNDLE_SIZE
        valks_cost = EXQUISITE_BLACK_CRYSTAL_RECIPE["valks_100"] * prices.valks_100_price
        crystal_cost = EXQUISITE_BLACK_CRYSTAL_RECIPE["pristine_black_crystal"] * prices.crystal_price
        return scroll_cost + valks_cost + crystal_cost

    def step(self) -> StepResult:
        """Perform a single enhancement step.

        Returns the result of the step for UI display.
        """
        if self.is_complete():
            raise RuntimeError("Simulation already complete")

        # Check Hepta/Okta paths first
        if self._should_use_hepta():
            return self._perform_hepta_okta_step(is_okta=False)
        if self._should_use_okta():
            return self._perform_hepta_okta_step(is_okta=True)

        # Normal enhancement
        return self._perform_enhancement_step()

    def _perform_hepta_okta_step(self, is_okta: bool) -> StepResult:
        """Perform a Hepta/Okta sub-enhancement step."""
        prices = self.config.prices
        path_name = "Okta" if is_okta else "Hepta"

        # Get current state
        current_progress = self.okta_progress if is_okta else self.hepta_progress
        current_pity = self.okta_pity if is_okta else self.hepta_pity
        max_progress = OKTA_SUB_ENHANCEMENTS if is_okta else HEPTA_SUB_ENHANCEMENTS

        # Cost tracking
        self.exquisite_crystals += HEPTA_OKTA_CRYSTALS_PER_ATTEMPT
        self.silver += self._get_exquisite_crystal_cost() * HEPTA_OKTA_CRYSTALS_PER_ATTEMPT
        self.attempts += 1

        # Check anvil pity
        anvil_triggered = current_pity >= HEPTA_OKTA_ANVIL_PITY

        if anvil_triggered or self.rng.random() < HEPTA_OKTA_SUCCESS_RATE:
            # Success
            if is_okta:
                self.okta_progress += 1
                self.okta_pity = 0
            else:
                self.hepta_progress += 1
                self.hepta_pity = 0

            new_progress = self.okta_progress if is_okta else self.hepta_progress

            # Check if path complete
            path_complete = new_progress >= max_progress
            if path_complete:
                target_level = 9 if is_okta else 8
                self.level = target_level
                self._reset_energy(target_level)
                if is_okta:
                    self.okta_progress = 0
                    self.okta_pity = 0
                else:
                    self.hepta_progress = 0
                    self.hepta_pity = 0

            return StepResult(
                success=True,
                anvil_triggered=anvil_triggered,
                starting_level=self.level if not path_complete else (8 if is_okta else 7),
                ending_level=self.level,
                is_hepta_okta=True,
                sub_progress=new_progress if not path_complete else 0,
                sub_pity=0,
                path_complete=path_complete,
                path_name=path_name,
            )
        else:
            # Failure - increment pity
            if is_okta:
                self.okta_pity += 1
            else:
                self.hepta_pity += 1

            return StepResult(
                success=False,
                anvil_triggered=False,
                starting_level=self.level,
                ending_level=self.level,
                is_hepta_okta=True,
                sub_progress=current_progress,
                sub_pity=self.okta_pity if is_okta else self.hepta_pity,
                path_complete=False,
                path_name=path_name,
            )

    def _perform_enhancement_step(self) -> StepResult:
        """Perform a normal enhancement step."""
        prices = self.config.prices
        target_level = self.level + 1
        starting_level = self.level

        # Determine valks
        valks_type = self._get_valks_for_level(target_level)

        # Get base rate and apply valks
        base_rate = AWAKENING_ENHANCEMENT_RATES.get(target_level, 0.01)
        if valks_type == "10":
            base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_10)
        elif valks_type == "50":
            base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_50)
        elif valks_type == "100":
            base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_100)

        # Check anvil pity
        current_energy = self.get_energy(target_level)
        max_energy = ANVIL_THRESHOLDS_AWAKENING.get(target_level, 999)
        anvil_triggered = current_energy >= max_energy and max_energy > 0

        # Resource tracking
        self.attempts += 1
        self.crystals += 1
        self.silver += prices.crystal_price

        if valks_type == "10":
            self.valks_10_used += 1
            self.silver += prices.valks_10_price
        elif valks_type == "50":
            self.valks_50_used += 1
            self.silver += prices.valks_50_price
        elif valks_type == "100":
            self.valks_100_used += 1
            self.silver += prices.valks_100_price

        if anvil_triggered or self.rng.random() < base_rate:
            # Success
            self.level = target_level
            self._reset_energy(target_level)
            return StepResult(
                success=True,
                anvil_triggered=anvil_triggered,
                starting_level=starting_level,
                ending_level=target_level,
                valks_used=valks_type,
            )

        # Failure
        self._add_energy(target_level)
        restoration_attempted = False
        restoration_success = False
        ending_level = self.level

        if self.level > 0 and self._should_use_restoration():
            restoration_attempted = True
            self.scrolls += RESTORATION_PER_ATTEMPT
            self.silver += prices.restoration_attempt_cost

            if self.rng.random() < RESTORATION_SUCCESS_RATE:
                restoration_success = True
            else:
                self.level -= 1
                ending_level = self.level
        elif self.level > 0:
            self.level -= 1
            ending_level = self.level

        return StepResult(
            success=False,
            anvil_triggered=False,
            starting_level=starting_level,
            ending_level=ending_level,
            valks_used=valks_type,
            restoration_attempted=restoration_attempted,
            restoration_success=restoration_success,
        )

    def run_full_simulation(self) -> SimulationResult:
        """Run simulation to completion and return results."""
        while not self.is_complete():
            self.step()

        return SimulationResult(
            crystals=self.crystals,
            scrolls=self.scrolls,
            silver=self.silver,
            exquisite_crystals=self.exquisite_crystals,
            attempts=self.attempts,
            final_level=self.level,
            anvil_energy=dict(self.anvil_energy),
            valks_10_used=self.valks_10_used,
            valks_50_used=self.valks_50_used,
            valks_100_used=self.valks_100_used,
        )


# Alias for backward compatibility
EnhancementEngine = AwakeningEngine
