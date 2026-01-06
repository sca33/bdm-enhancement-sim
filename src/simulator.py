"""Core enhancement simulation logic with Monte Carlo support."""
import random
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .config import (
    AWAKENING_ENHANCEMENT_RATES,
    ANVIL_THRESHOLDS_AWAKENING,
    AWAKENING_MATERIAL_COSTS,
    RESTORATION_SCROLL_COSTS,
    RESTORATION_SUCCESS_RATE,
    VALKS_MULTIPLIER_10,
    VALKS_MULTIPLIER_50,
    VALKS_MULTIPLIER_100,
)
from .market_config import get_effective_price


class RestorationStrategy(Enum):
    """When to use restoration scrolls."""
    NEVER = "never"                    # Never use restoration
    ALWAYS = "always"                  # Always use restoration on failure
    ABOVE_THRESHOLD = "above_threshold"  # Only use above certain level
    COST_EFFICIENT = "cost_efficient"  # Use when expected value is positive


class ValksStrategy(Enum):
    """When to use Advice of Valks."""
    NEVER = "never"
    SMALL_ONLY = "small_only"      # Only +10%
    LARGE_ONLY = "large_only"      # Only +50%
    LARGE_HIGH_TIER = "large_high" # +50% only on high tiers (VI+)
    OPTIMAL = "optimal"            # Algorithm decides based on EV


@dataclass
class EnhancementStrategy:
    """Configuration for auto-enhancement behavior."""
    restoration: RestorationStrategy = RestorationStrategy.ALWAYS
    restoration_threshold: int = 3  # Only use restoration above this level
    valks: ValksStrategy = ValksStrategy.NEVER
    valks_large_threshold: int = 6  # Use large valks starting at this level
    use_protection: bool = False    # Use W/Ogier blessing


@dataclass
class AttemptResult:
    """Result of a single enhancement attempt."""
    success: bool
    starting_level: int
    ending_level: int
    anvil_triggered: bool = False
    restoration_attempted: bool = False
    restoration_success: bool = False
    valks_used: Optional[str] = None  # "small", "large", or None
    materials_cost: dict = field(default_factory=dict)


@dataclass
class SimulationResult:
    """Result of a full simulation run (0 -> target)."""
    target_level: int
    total_attempts: int
    successes: int
    failures: int
    anvil_triggers: int
    restoration_attempts: int
    restoration_successes: int
    level_drops: int
    materials_used: dict = field(default_factory=dict)
    silver_cost: int = 0
    attempt_history: list = field(default_factory=list)


@dataclass
class GearState:
    """Tracks current state of gear being enhanced."""
    awakening_level: int = 0
    anvil_energy: dict = field(default_factory=dict)

    def get_energy(self, target_level: int) -> int:
        """Get accumulated anvil energy for a target level."""
        return self.anvil_energy.get(target_level, 0)

    def add_energy(self, target_level: int) -> None:
        """Add 1 energy for a target level."""
        self.anvil_energy[target_level] = self.get_energy(target_level) + 1

    def reset_energy(self, target_level: int) -> None:
        """Reset energy for a target level (on success)."""
        self.anvil_energy[target_level] = 0

    def copy(self) -> "GearState":
        """Create a copy of the gear state."""
        return GearState(
            awakening_level=self.awakening_level,
            anvil_energy=dict(self.anvil_energy),
        )


class AwakeningSimulator:
    """Simulates BDM awakening enhancement mechanics."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize simulator with optional random seed."""
        self.rng = random.Random(seed)

    def _get_success_rate(
        self,
        target_level: int,
        valks: Optional[str] = None,
    ) -> float:
        """Calculate success rate including any bonuses.

        Valks bonuses are MULTIPLICATIVE (relative), not additive.
        Example: 0.5% base with +100% Valks = 0.5% × 2.0 = 1%
        """
        base_rate = AWAKENING_ENHANCEMENT_RATES.get(target_level, 0.01)

        if valks == "small" or valks == "10":
            base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_10)
        elif valks == "large" or valks == "50":
            base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_50)
        elif valks == "100":
            base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_100)

        return base_rate

    def _should_use_restoration(
        self,
        current_level: int,
        strategy: EnhancementStrategy,
    ) -> bool:
        """Determine if restoration should be used based on strategy."""
        if strategy.restoration == RestorationStrategy.NEVER:
            return False
        if strategy.restoration == RestorationStrategy.ALWAYS:
            return True
        if strategy.restoration == RestorationStrategy.ABOVE_THRESHOLD:
            return current_level >= strategy.restoration_threshold
        # COST_EFFICIENT - simplified heuristic
        return current_level >= 4

    def _get_valks_type(
        self,
        target_level: int,
        strategy: EnhancementStrategy,
    ) -> Optional[str]:
        """Determine which Valks to use based on strategy."""
        if strategy.valks == ValksStrategy.NEVER:
            return None
        if strategy.valks == ValksStrategy.SMALL_ONLY:
            return "small"
        if strategy.valks == ValksStrategy.LARGE_ONLY:
            return "large"
        if strategy.valks == ValksStrategy.LARGE_HIGH_TIER:
            return "large" if target_level >= strategy.valks_large_threshold else None
        # OPTIMAL - use large on high tiers, small on medium
        if target_level >= 7:
            return "large"
        elif target_level >= 4:
            return "small"
        return None

    def attempt_enhancement(
        self,
        gear: GearState,
        strategy: EnhancementStrategy,
    ) -> AttemptResult:
        """Perform a single enhancement attempt."""
        target_level = gear.awakening_level + 1

        if target_level > 10:
            raise ValueError("Already at max awakening level (X)")

        # Determine what to use
        valks_type = self._get_valks_type(target_level, strategy)
        success_rate = self._get_success_rate(target_level, valks_type)

        # Check anvil pity
        current_energy = gear.get_energy(target_level)
        max_energy = ANVIL_THRESHOLDS_AWAKENING.get(target_level, 999)
        anvil_triggered = current_energy >= max_energy

        # Calculate material costs
        materials = {
            "pristine_black_crystal": AWAKENING_MATERIAL_COSTS.get(target_level, 1),
        }
        if valks_type == "small":
            materials["valks_advice_10"] = 1
        elif valks_type == "large":
            materials["valks_advice_50"] = 1

        starting_level = gear.awakening_level

        if anvil_triggered:
            # Guaranteed success
            gear.awakening_level = target_level
            gear.reset_energy(target_level)
            return AttemptResult(
                success=True,
                starting_level=starting_level,
                ending_level=target_level,
                anvil_triggered=True,
                valks_used=valks_type,
                materials_cost=materials,
            )

        # Roll for success
        roll = self.rng.random()
        success = roll < success_rate

        if success:
            gear.awakening_level = target_level
            gear.reset_energy(target_level)
            return AttemptResult(
                success=True,
                starting_level=starting_level,
                ending_level=target_level,
                valks_used=valks_type,
                materials_cost=materials,
            )

        # Failed - accumulate energy
        gear.add_energy(target_level)

        # Handle downgrade
        restoration_attempted = False
        restoration_success = False
        ending_level = gear.awakening_level

        if gear.awakening_level > 0:
            use_restoration = self._should_use_restoration(
                gear.awakening_level, strategy
            )

            if use_restoration:
                restoration_attempted = True
                materials["restoration_scroll"] = RESTORATION_SCROLL_COSTS.get(
                    gear.awakening_level, 1
                )
                restoration_success = self.rng.random() < RESTORATION_SUCCESS_RATE

                if not restoration_success:
                    gear.awakening_level -= 1
                    ending_level = gear.awakening_level
            else:
                gear.awakening_level -= 1
                ending_level = gear.awakening_level

        return AttemptResult(
            success=False,
            starting_level=starting_level,
            ending_level=ending_level,
            restoration_attempted=restoration_attempted,
            restoration_success=restoration_success,
            valks_used=valks_type,
            materials_cost=materials,
        )

    def simulate_to_target(
        self,
        target_level: int,
        strategy: EnhancementStrategy,
        starting_state: Optional[GearState] = None,
        max_attempts: int = 100_000,
    ) -> SimulationResult:
        """Run simulation until target level is reached."""
        gear = starting_state.copy() if starting_state else GearState()

        result = SimulationResult(
            target_level=target_level,
            total_attempts=0,
            successes=0,
            failures=0,
            anvil_triggers=0,
            restoration_attempts=0,
            restoration_successes=0,
            level_drops=0,
        )

        while gear.awakening_level < target_level and result.total_attempts < max_attempts:
            attempt = self.attempt_enhancement(gear, strategy)
            result.total_attempts += 1
            result.attempt_history.append(attempt)

            if attempt.success:
                result.successes += 1
            else:
                result.failures += 1

            if attempt.anvil_triggered:
                result.anvil_triggers += 1

            if attempt.restoration_attempted:
                result.restoration_attempts += 1
                if attempt.restoration_success:
                    result.restoration_successes += 1
                else:
                    result.level_drops += 1
            elif not attempt.success and attempt.starting_level > 0:
                result.level_drops += 1

            # Accumulate materials
            for mat, amount in attempt.materials_cost.items():
                result.materials_used[mat] = (
                    result.materials_used.get(mat, 0) + amount
                )

        # Calculate silver cost
        for mat, amount in result.materials_used.items():
            result.silver_cost += get_effective_price(mat) * amount

        return result

    def run_monte_carlo(
        self,
        target_level: int,
        strategy: EnhancementStrategy,
        num_simulations: int = 10_000,
        starting_state: Optional[GearState] = None,
    ) -> dict:
        """Run multiple simulations and return statistics."""
        results = []

        for _ in range(num_simulations):
            result = self.simulate_to_target(
                target_level=target_level,
                strategy=strategy,
                starting_state=starting_state,
            )
            results.append(result)

        # Calculate statistics
        attempts = sorted(r.total_attempts for r in results)
        silver_costs = sorted(r.silver_cost for r in results)
        crystals = sorted(
            r.materials_used.get("pristine_black_crystal", 0) for r in results
        )
        scrolls = sorted(
            r.materials_used.get("restoration_scroll", 0) for r in results
        )
        level_drops = sorted(r.level_drops for r in results)
        anvil_triggers = sorted(r.anvil_triggers for r in results)

        def percentile(data: list, p: float) -> float:
            idx = int(len(data) * p)
            return data[min(idx, len(data) - 1)]

        def average(data: list) -> float:
            return sum(data) / len(data) if data else 0

        return {
            "num_simulations": num_simulations,
            "target_level": target_level,
            "strategy": {
                "restoration": strategy.restoration.value,
                "valks": strategy.valks.value,
            },
            "attempts": {
                "average": average(attempts),
                "p50": percentile(attempts, 0.50),
                "p90": percentile(attempts, 0.90),
                "p99": percentile(attempts, 0.99),
                "worst": attempts[-1],
            },
            "silver_cost": {
                "average": average(silver_costs),
                "p50": percentile(silver_costs, 0.50),
                "p90": percentile(silver_costs, 0.90),
                "p99": percentile(silver_costs, 0.99),
                "worst": silver_costs[-1],
            },
            "pristine_black_crystals": {
                "average": average(crystals),
                "p50": percentile(crystals, 0.50),
                "p90": percentile(crystals, 0.90),
                "worst": crystals[-1],
            },
            "restoration_scrolls": {
                "average": average(scrolls),
                "p50": percentile(scrolls, 0.50),
                "p90": percentile(scrolls, 0.90),
                "worst": scrolls[-1],
            },
            "level_drops": {
                "average": average(level_drops),
                "p50": percentile(level_drops, 0.50),
                "p90": percentile(level_drops, 0.90),
                "worst": level_drops[-1],
            },
            "anvil_triggers": {
                "average": average(anvil_triggers),
                "p50": percentile(anvil_triggers, 0.50),
                "p90": percentile(anvil_triggers, 0.90),
            },
        }
