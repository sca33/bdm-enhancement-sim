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


@dataclass(slots=True)
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


@dataclass(slots=True)
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


@dataclass(slots=True)
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


@dataclass(slots=True)
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


# Pre-compute rate caches at module level (computed once on import)
_RATE_CACHE: dict[int, float] = {
    level: AWAKENING_ENHANCEMENT_RATES.get(level, 0.01)
    for level in range(1, 11)
}
_ANVIL_CACHE: dict[int, int] = {
    level: ANVIL_THRESHOLDS_AWAKENING.get(level, 999)
    for level in range(1, 11)
}

# Pre-compute valks-adjusted rates at module level
_RATE_CACHE_VALKS_10: dict[int, float] = {
    level: min(1.0, rate * VALKS_MULTIPLIER_10)
    for level, rate in _RATE_CACHE.items()
}
_RATE_CACHE_VALKS_50: dict[int, float] = {
    level: min(1.0, rate * VALKS_MULTIPLIER_50)
    for level, rate in _RATE_CACHE.items()
}
_RATE_CACHE_VALKS_100: dict[int, float] = {
    level: min(1.0, rate * VALKS_MULTIPLIER_100)
    for level, rate in _RATE_CACHE.items()
}

# Pre-extract recipe values (avoid dict lookups in hot path)
_EXQUISITE_RESTORATION_SCROLLS = EXQUISITE_BLACK_CRYSTAL_RECIPE["restoration_scrolls"]
_EXQUISITE_VALKS_100 = EXQUISITE_BLACK_CRYSTAL_RECIPE["valks_100"]
_EXQUISITE_PRISTINE_CRYSTAL = EXQUISITE_BLACK_CRYSTAL_RECIPE["pristine_black_crystal"]


class AwakeningEngine:
    """Simulation engine for awakening (armor/weapons) enhancement.

    This engine handles:
    - Normal enhancement with anvil pity
    - Hepta/Okta sub-enhancement paths
    - Restoration scrolls
    - Valks bonuses
    - Resource tracking
    """

    __slots__ = (
        'config', 'rng', 'level', 'anvil_energy', 'crystals', 'scrolls',
        'silver', 'exquisite_crystals', 'valks_10_used', 'valks_50_used',
        'valks_100_used', 'attempts', 'hepta_progress', 'okta_progress',
        'hepta_pity', 'okta_pity',
        # Cached config values
        '_target_level', '_restoration_from', '_use_hepta', '_use_okta',
        '_valks_10_from', '_valks_50_from', '_valks_100_from',
        '_crystal_price', '_valks_10_price', '_valks_50_price', '_valks_100_price',
        '_restoration_attempt_cost', '_exquisite_cost',
    )

    def __init__(self, config: SimulationConfig, seed: Optional[int] = None):
        self.config = config
        self.rng = random.Random(seed)

        # Cache config values to avoid nested attribute lookups in hot paths
        self._target_level = config.target_level
        self._restoration_from = config.restoration_from
        self._use_hepta = config.use_hepta
        self._use_okta = config.use_okta
        self._valks_10_from = config.valks_10_from
        self._valks_50_from = config.valks_50_from
        self._valks_100_from = config.valks_100_from

        # Cache price values
        prices = config.prices
        self._crystal_price = prices.crystal_price
        self._valks_10_price = prices.valks_10_price
        self._valks_50_price = prices.valks_50_price
        self._valks_100_price = prices.valks_100_price
        self._restoration_attempt_cost = prices.restoration_attempt_cost

        # Pre-compute exquisite crystal cost (constant per config)
        self._exquisite_cost = (
            (_EXQUISITE_RESTORATION_SCROLLS * prices.restoration_bundle_price) // RESTORATION_MARKET_BUNDLE_SIZE +
            _EXQUISITE_VALKS_100 * prices.valks_100_price +
            _EXQUISITE_PRISTINE_CRYSTAL * prices.crystal_price
        )

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
        return self.level >= self._target_level

    def get_energy(self, level: int) -> int:
        """Get anvil energy for a specific level."""
        return self.anvil_energy.get(level, 0)

    def _add_energy(self, level: int) -> None:
        """Add 1 energy for a level."""
        self.anvil_energy[level] = self.anvil_energy.get(level, 0) + 1

    def _reset_energy(self, level: int) -> None:
        """Reset energy for a level."""
        self.anvil_energy[level] = 0

    def _get_valks_for_level(self, target_level: int) -> Optional[str]:
        """Determine which Valks to use for a target level."""
        if self._valks_100_from > 0 and target_level >= self._valks_100_from:
            return "100"
        if self._valks_50_from > 0 and target_level >= self._valks_50_from:
            return "50"
        if self._valks_10_from > 0 and target_level >= self._valks_10_from:
            return "10"
        return None

    def _should_use_restoration(self) -> bool:
        """Check if restoration should be used at current level."""
        return self._restoration_from > 0 and self.level >= self._restoration_from

    def _should_use_hepta(self) -> bool:
        """Check if Hepta path should be used."""
        return ((self._use_hepta or self.hepta_progress > 0) and
                self.level == 7 and
                self.hepta_progress < HEPTA_SUB_ENHANCEMENTS)

    def _should_use_okta(self) -> bool:
        """Check if Okta path should be used."""
        return ((self._use_okta or self.okta_progress > 0) and
                self.level == 8 and
                self.okta_progress < OKTA_SUB_ENHANCEMENTS)

    def _get_exquisite_crystal_cost(self) -> int:
        """Calculate cost of one Exquisite Black Crystal."""
        return self._exquisite_cost

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
        path_name = "Okta" if is_okta else "Hepta"

        # Get current state
        current_progress = self.okta_progress if is_okta else self.hepta_progress
        current_pity = self.okta_pity if is_okta else self.hepta_pity
        max_progress = OKTA_SUB_ENHANCEMENTS if is_okta else HEPTA_SUB_ENHANCEMENTS

        # Cost tracking (use cached values)
        self.exquisite_crystals += HEPTA_OKTA_CRYSTALS_PER_ATTEMPT
        self.silver += self._exquisite_cost * HEPTA_OKTA_CRYSTALS_PER_ATTEMPT
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
        # Local variable caching for hot path
        level = self.level
        target_level = level + 1
        starting_level = level
        rng_random = self.rng.random  # Cache method lookup
        anvil_energy = self.anvil_energy

        # Determine valks and get rate from pre-computed cache
        valks_100_from = self._valks_100_from
        valks_50_from = self._valks_50_from
        valks_10_from = self._valks_10_from

        if valks_100_from > 0 and target_level >= valks_100_from:
            valks_type = "100"
            base_rate = _RATE_CACHE_VALKS_100.get(target_level, 0.01)
        elif valks_50_from > 0 and target_level >= valks_50_from:
            valks_type = "50"
            base_rate = _RATE_CACHE_VALKS_50.get(target_level, 0.01)
        elif valks_10_from > 0 and target_level >= valks_10_from:
            valks_type = "10"
            base_rate = _RATE_CACHE_VALKS_10.get(target_level, 0.01)
        else:
            valks_type = None
            base_rate = _RATE_CACHE.get(target_level, 0.01)

        # Check anvil pity using cached lookup
        current_energy = anvil_energy.get(target_level, 0)
        max_energy = _ANVIL_CACHE.get(target_level, 999)
        anvil_triggered = current_energy >= max_energy and max_energy > 0

        # Resource tracking (use cached prices)
        self.attempts += 1
        self.crystals += 1
        self.silver += self._crystal_price

        if valks_type == "10":
            self.valks_10_used += 1
            self.silver += self._valks_10_price
        elif valks_type == "50":
            self.valks_50_used += 1
            self.silver += self._valks_50_price
        elif valks_type == "100":
            self.valks_100_used += 1
            self.silver += self._valks_100_price

        if anvil_triggered or rng_random() < base_rate:
            # Success
            self.level = target_level
            anvil_energy[target_level] = 0
            return StepResult(
                success=True,
                anvil_triggered=anvil_triggered,
                starting_level=starting_level,
                ending_level=target_level,
                valks_used=valks_type,
            )

        # Failure
        anvil_energy[target_level] = current_energy + 1
        restoration_attempted = False
        restoration_success = False
        ending_level = level

        restoration_from = self._restoration_from
        if level > 0 and restoration_from > 0 and level >= restoration_from:
            restoration_attempted = True
            self.scrolls += RESTORATION_PER_ATTEMPT
            self.silver += self._restoration_attempt_cost

            if rng_random() < RESTORATION_SUCCESS_RATE:
                restoration_success = True
            else:
                level -= 1
                self.level = level
                ending_level = level
        elif level > 0:
            level -= 1
            self.level = level
            ending_level = level

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

    def run_fast(self) -> tuple[int, int, int, int]:
        """Run simulation and return minimal results as tuple.

        Returns (crystals, scrolls, silver, exquisite_crystals).
        This is faster than run_full_simulation() as it avoids dataclass creation.
        """
        # Local variable caching for maximum performance
        level = self.level
        target_level = self._target_level
        anvil_energy = self.anvil_energy
        rng_random = self.rng.random

        # Cached config values
        restoration_from = self._restoration_from
        use_hepta = self._use_hepta
        use_okta = self._use_okta
        valks_100_from = self._valks_100_from
        valks_50_from = self._valks_50_from
        valks_10_from = self._valks_10_from
        crystal_price = self._crystal_price
        valks_10_price = self._valks_10_price
        valks_50_price = self._valks_50_price
        valks_100_price = self._valks_100_price
        restoration_cost = self._restoration_attempt_cost
        exquisite_cost = self._exquisite_cost

        # Resource counters
        crystals = 0
        scrolls = 0
        silver = 0
        exquisite_crystals = 0

        # Hepta/Okta state
        hepta_progress = self.hepta_progress
        okta_progress = self.okta_progress
        hepta_pity = 0
        okta_pity = 0

        while level < target_level:
            # Check Hepta path
            if ((use_hepta or hepta_progress > 0) and
                level == 7 and hepta_progress < HEPTA_SUB_ENHANCEMENTS):
                # Hepta step
                exquisite_crystals += HEPTA_OKTA_CRYSTALS_PER_ATTEMPT
                silver += exquisite_cost * HEPTA_OKTA_CRYSTALS_PER_ATTEMPT

                if hepta_pity >= HEPTA_OKTA_ANVIL_PITY or rng_random() < HEPTA_OKTA_SUCCESS_RATE:
                    hepta_progress += 1
                    hepta_pity = 0
                    if hepta_progress >= HEPTA_SUB_ENHANCEMENTS:
                        level = 8
                        anvil_energy[8] = 0
                        hepta_progress = 0
                else:
                    hepta_pity += 1
                continue

            # Check Okta path
            if ((use_okta or okta_progress > 0) and
                level == 8 and okta_progress < OKTA_SUB_ENHANCEMENTS):
                # Okta step
                exquisite_crystals += HEPTA_OKTA_CRYSTALS_PER_ATTEMPT
                silver += exquisite_cost * HEPTA_OKTA_CRYSTALS_PER_ATTEMPT

                if okta_pity >= HEPTA_OKTA_ANVIL_PITY or rng_random() < HEPTA_OKTA_SUCCESS_RATE:
                    okta_progress += 1
                    okta_pity = 0
                    if okta_progress >= OKTA_SUB_ENHANCEMENTS:
                        level = 9
                        anvil_energy[9] = 0
                        okta_progress = 0
                else:
                    okta_pity += 1
                continue

            # Normal enhancement
            next_level = level + 1

            # Get rate based on valks
            if valks_100_from > 0 and next_level >= valks_100_from:
                base_rate = _RATE_CACHE_VALKS_100.get(next_level, 0.01)
                silver += valks_100_price
            elif valks_50_from > 0 and next_level >= valks_50_from:
                base_rate = _RATE_CACHE_VALKS_50.get(next_level, 0.01)
                silver += valks_50_price
            elif valks_10_from > 0 and next_level >= valks_10_from:
                base_rate = _RATE_CACHE_VALKS_10.get(next_level, 0.01)
                silver += valks_10_price
            else:
                base_rate = _RATE_CACHE.get(next_level, 0.01)

            # Resource cost
            crystals += 1
            silver += crystal_price

            # Check anvil pity
            current_energy = anvil_energy.get(next_level, 0)
            max_energy = _ANVIL_CACHE.get(next_level, 999)
            anvil_triggered = current_energy >= max_energy and max_energy > 0

            if anvil_triggered or rng_random() < base_rate:
                # Success
                level = next_level
                anvil_energy[next_level] = 0
            else:
                # Failure
                anvil_energy[next_level] = current_energy + 1
                if level > 0 and restoration_from > 0 and level >= restoration_from:
                    scrolls += RESTORATION_PER_ATTEMPT
                    silver += restoration_cost
                    if rng_random() >= RESTORATION_SUCCESS_RATE:
                        level -= 1
                elif level > 0:
                    level -= 1

        return (crystals, scrolls, silver, exquisite_crystals)


# Alias for backward compatibility
EnhancementEngine = AwakeningEngine
