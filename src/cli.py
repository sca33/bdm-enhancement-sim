"""Command-line interface for the BDM enhancement simulator."""
import argparse
import json
import sys
from typing import Optional

from .simulator import (
    AwakeningSimulator,
    EnhancementStrategy,
    RestorationStrategy,
    ValksStrategy,
    GearState,
)
from .config import AWAKENING_ENHANCEMENT_RATES, ANVIL_THRESHOLDS_AWAKENING


# Predefined strategy presets
STRATEGY_PRESETS = {
    "conservative": EnhancementStrategy(
        restoration=RestorationStrategy.ALWAYS,
        valks=ValksStrategy.NEVER,
    ),
    "no_restoration": EnhancementStrategy(
        restoration=RestorationStrategy.NEVER,
        valks=ValksStrategy.NEVER,
    ),
    "restoration_above_3": EnhancementStrategy(
        restoration=RestorationStrategy.ABOVE_THRESHOLD,
        restoration_threshold=3,
        valks=ValksStrategy.NEVER,
    ),
    "restoration_above_5": EnhancementStrategy(
        restoration=RestorationStrategy.ABOVE_THRESHOLD,
        restoration_threshold=5,
        valks=ValksStrategy.NEVER,
    ),
    "valks_high_tier": EnhancementStrategy(
        restoration=RestorationStrategy.ALWAYS,
        valks=ValksStrategy.LARGE_HIGH_TIER,
        valks_large_threshold=6,
    ),
    "full_optimal": EnhancementStrategy(
        restoration=RestorationStrategy.ALWAYS,
        valks=ValksStrategy.OPTIMAL,
    ),
}


def format_number(n: float) -> str:
    """Format large numbers with K/M suffixes."""
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:.1f}"


def print_results(stats: dict) -> None:
    """Pretty print simulation results."""
    print("\n" + "=" * 60)
    print(f"  BDM Awakening Enhancement Simulation Results")
    print("=" * 60)

    print(f"\nTarget: 0 → +{stats['target_level']} ({to_roman(stats['target_level'])})")
    print(f"Simulations: {stats['num_simulations']:,}")
    print(f"Strategy: restoration={stats['strategy']['restoration']}, "
          f"valks={stats['strategy']['valks']}")

    print("\n" + "-" * 60)
    print("  ATTEMPTS REQUIRED")
    print("-" * 60)
    print(f"  Average:    {stats['attempts']['average']:.1f}")
    print(f"  Median:     {stats['attempts']['p50']:.0f}")
    print(f"  P90:        {stats['attempts']['p90']:.0f}")
    print(f"  P99:        {stats['attempts']['p99']:.0f}")
    print(f"  Worst:      {stats['attempts']['worst']:.0f}")

    print("\n" + "-" * 60)
    print("  SILVER COST")
    print("-" * 60)
    print(f"  Average:    {format_number(stats['silver_cost']['average'])}")
    print(f"  Median:     {format_number(stats['silver_cost']['p50'])}")
    print(f"  P90:        {format_number(stats['silver_cost']['p90'])}")
    print(f"  P99:        {format_number(stats['silver_cost']['p99'])}")
    print(f"  Worst:      {format_number(stats['silver_cost']['worst'])}")

    print("\n" + "-" * 60)
    print("  MATERIALS")
    print("-" * 60)
    print(f"  Pristine Black Crystals:")
    print(f"    Average:  {stats['pristine_black_crystals']['average']:.1f}")
    print(f"    P50:      {stats['pristine_black_crystals']['p50']:.0f}")
    print(f"    P90:      {stats['pristine_black_crystals']['p90']:.0f}")
    print(f"    Worst:    {stats['pristine_black_crystals']['worst']:.0f}")
    print(f"  Restoration Scrolls:")
    print(f"    Average:  {stats['restoration_scrolls']['average']:.1f}")
    print(f"    P50:      {stats['restoration_scrolls']['p50']:.0f}")
    print(f"    P90:      {stats['restoration_scrolls']['p90']:.0f}")
    print(f"    Worst:    {stats['restoration_scrolls']['worst']:.0f}")

    print("\n" + "-" * 60)
    print("  FAILURES & PITY")
    print("-" * 60)
    print(f"  Level Drops:")
    print(f"    Average:  {stats['level_drops']['average']:.1f}")
    print(f"    P90:      {stats['level_drops']['p90']:.0f}")
    print(f"    Worst:    {stats['level_drops']['worst']:.0f}")
    print(f"  Anvil (Pity) Triggers:")
    print(f"    Average:  {stats['anvil_triggers']['average']:.1f}")
    print(f"    P90:      {stats['anvil_triggers']['p90']:.0f}")

    print("\n" + "=" * 60)


def to_roman(n: int) -> str:
    """Convert integer to Roman numeral."""
    numerals = [
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")
    ]
    result = ""
    for value, numeral in numerals:
        while n >= value:
            result += numeral
            n -= value
    return result


def print_enhancement_table() -> None:
    """Print the enhancement rate and anvil threshold table."""
    print("\n" + "=" * 60)
    print("  Enhancement Rates & Anvil Thresholds")
    print("=" * 60)
    print(f"{'Level':<8} {'Rate':<12} {'Anvil Pity':<12}")
    print("-" * 60)

    for level in range(1, 11):
        rate = AWAKENING_ENHANCEMENT_RATES.get(level, 0)
        anvil = ANVIL_THRESHOLDS_AWAKENING.get(level, "N/A")
        anvil_str = str(anvil) if anvil > 0 else "N/A (100%)"
        print(f"{to_roman(level):<8} {rate*100:.1f}%{'':<7} {anvil_str:<12}")

    print("=" * 60)
    print("Note: Anvil Pity = guaranteed success after N failures")
    print()


def compare_strategies(
    target: int,
    num_simulations: int,
    seed: Optional[int] = None,
) -> None:
    """Compare different enhancement strategies."""
    simulator = AwakeningSimulator(seed=seed)

    print("\n" + "=" * 70)
    print(f"  Strategy Comparison: 0 → +{target} ({to_roman(target)})")
    print(f"  Simulations per strategy: {num_simulations:,}")
    print("=" * 70)

    results = {}
    for name, strategy in STRATEGY_PRESETS.items():
        print(f"  Running '{name}'...", end="", flush=True)
        stats = simulator.run_monte_carlo(
            target_level=target,
            strategy=strategy,
            num_simulations=num_simulations,
        )
        results[name] = stats
        print(" done")

    print("\n" + "-" * 70)
    print(f"{'Strategy':<22} {'Avg Cost':<12} {'P50 Cost':<12} {'P90 Cost':<12}")
    print("-" * 70)

    sorted_results = sorted(
        results.items(),
        key=lambda x: x[1]["silver_cost"]["average"]
    )

    for name, stats in sorted_results:
        avg = format_number(stats["silver_cost"]["average"])
        p50 = format_number(stats["silver_cost"]["p50"])
        p90 = format_number(stats["silver_cost"]["p90"])
        print(f"{name:<22} {avg:<12} {p50:<12} {p90:<12}")

    print("-" * 70)
    best = sorted_results[0][0]
    print(f"\nBest strategy by average cost: {best}")
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Black Desert Mobile Enhancement Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --target 5                    # Simulate to +V with default strategy
  %(prog)s --target 7 --strategy valks_high_tier
  %(prog)s --compare --target 5          # Compare all strategies
  %(prog)s --show-rates                  # Show enhancement rate table

Strategy presets:
  conservative        Always use restoration, no valks
  no_restoration      Never use restoration scrolls
  restoration_above_3 Use restoration only at +III and above
  restoration_above_5 Use restoration only at +V and above
  valks_high_tier     Use +50% valks at +VI and above
  full_optimal        Use restoration + optimal valks
        """,
    )

    parser.add_argument(
        "--target", "-t",
        type=int,
        default=5,
        help="Target awakening level (1-10, default: 5)",
    )
    parser.add_argument(
        "--simulations", "-n",
        type=int,
        default=10_000,
        help="Number of simulations (default: 10000)",
    )
    parser.add_argument(
        "--strategy", "-s",
        choices=list(STRATEGY_PRESETS.keys()),
        default="conservative",
        help="Enhancement strategy preset",
    )
    parser.add_argument(
        "--compare", "-c",
        action="store_true",
        help="Compare all strategy presets",
    )
    parser.add_argument(
        "--show-rates",
        action="store_true",
        help="Show enhancement rate and anvil threshold table",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--start-level",
        type=int,
        default=0,
        help="Starting awakening level (default: 0)",
    )

    args = parser.parse_args()

    if args.show_rates:
        print_enhancement_table()
        return

    if args.target < 1 or args.target > 10:
        print("Error: Target must be between 1 and 10", file=sys.stderr)
        sys.exit(1)

    if args.compare:
        compare_strategies(args.target, args.simulations, args.seed)
        return

    # Run single strategy simulation
    simulator = AwakeningSimulator(seed=args.seed)
    strategy = STRATEGY_PRESETS[args.strategy]

    starting_state = None
    if args.start_level > 0:
        starting_state = GearState(awakening_level=args.start_level)

    print(f"Running {args.simulations:,} simulations...")
    stats = simulator.run_monte_carlo(
        target_level=args.target,
        strategy=strategy,
        num_simulations=args.simulations,
        starting_state=starting_state,
    )

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print_results(stats)


if __name__ == "__main__":
    main()
