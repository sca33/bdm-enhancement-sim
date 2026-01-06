"""Enhancement configuration and probability tables.

Data sourced from:
- Official BDM Korea patch notes (Dec 30, 2025)
- Community research and player estimates
- https://forum.blackdesertm.com/Board/Detail?boardNo=7&contentNo=641570

Some values are estimates and should be verified in-game.
"""

# Awakening enhancement success rates (I-X)
# Format: {target_level: base_success_rate}
# Source: User-provided actual in-game rates
AWAKENING_ENHANCEMENT_RATES: dict[int, float] = {
    1: 0.70,    # I - 70%
    2: 0.60,    # II - 60%
    3: 0.40,    # III - 40%
    4: 0.20,    # IV - 20%
    5: 0.10,    # V - 10%
    6: 0.07,    # VI - 7%
    7: 0.05,    # VII - 5%
    8: 0.03,    # VIII - 3%
    9: 0.01,    # IX - 1%
    10: 0.005,  # X - 0.5%
}

# Ancient Anvil (고대의 모루) maximum energy thresholds
# When energy reaches this value, next enhancement is guaranteed success
# Source: Official Dec 30, 2025 patch notes
# Format: {target_level: max_failures_before_guaranteed}
ANVIL_THRESHOLDS_AWAKENING: dict[int, int] = {
    1: 0,     # I - no pity
    2: 0,     # II - no pity
    3: 2,     # III - guaranteed after 2 failures
    4: 3,     # IV - guaranteed after 3 failures
    5: 5,     # V - guaranteed after 5 failures
    6: 8,     # VI - guaranteed after 8 failures
    7: 10,    # VII - guaranteed after 10 failures
    8: 17,    # VIII - guaranteed after 17 failures
    9: 50,    # IX - guaranteed after 50 failures
    10: 100,  # X - guaranteed after 100 failures
}

# Accessory Breakthrough thresholds (for reference)
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

# Material costs per awakening enhancement attempt
# Format: {target_level: pristine_black_crystals_needed}
# Source: User-provided (1 crystal per attempt regardless of level)
AWAKENING_MATERIAL_COSTS: dict[int, int] = {
    1: 1,
    2: 1,
    3: 1,
    4: 1,
    5: 1,
    6: 1,
    7: 1,
    8: 1,
    9: 1,
    10: 1,
}

# Restoration scroll costs per awakening level
# Format: {current_level: scrolls_needed_to_attempt_restoration}
# Source: User-provided (200 scrolls per recovery attempt regardless of level)
RESTORATION_SCROLL_COSTS: dict[int, int] = {
    1: 200,
    2: 200,
    3: 200,
    4: 200,
    5: 200,
    6: 200,
    7: 200,
    8: 200,
    9: 200,
    10: 200,
}

# Restoration scroll success rate (50% chance to prevent downgrade)
RESTORATION_SUCCESS_RATE: float = 0.50

# Hepta/Okta sub-enhancement success rate
# Used for VII→VIII (Hepta) and VIII→IX (Okta) failsafe paths
HEPTA_OKTA_SUCCESS_RATE: float = 0.06  # 6% per sub-enhancement attempt

# Advice of Valks bonuses (RELATIVE/MULTIPLICATIVE - not additive!)
# Example: 0.5% base rate with +100% Valks = 0.5% × 2.0 = 1%
VALKS_MULTIPLIER_10: float = 1.10    # +10% = ×1.1 (발크스의 조언)
VALKS_MULTIPLIER_50: float = 1.50    # +50% = ×1.5 (강력한 발크스의 조언)
VALKS_MULTIPLIER_100: float = 2.00   # +100% = ×2.0 (초월 발크스의 조언)

# Arkram's Prophecy bonus (아크람의 예언)
# Adds flat percentage based on item type
ARKRAM_PROPHECY_BONUS: float = 0.10  # +10%

# W's Blessing (W의 가호) - prevents downgrade on failure
# Still accumulates anvil energy on failure
W_BLESSING_ENABLED: bool = True

# Ogier's Blessing (오기에르의 가호) - variants
# Still accumulates anvil energy on failure
OGIER_BLESSING_VARIANTS: dict[str, float] = {
    "basic": 0.0,      # No bonus, just prevents downgrade
    "blooming": 0.05,  # 피어나는 오기에르의 가호 - +5% success
    "saving": 0.10,    # 구원하는 오기에어의 가호 - +10% success
}
