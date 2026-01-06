"""Market prices and silver conversion rates.

Configure these values based on your server's auction house prices.
All prices are in silver.
"""

# Base material silver values
# UPDATE THESE based on your server's current market prices!
# Default: 200 restoration scrolls = 1 trillion silver
MARKET_PRICES: dict[str, int] = {
    # Black Stones (used to craft Pristine Black Crystals)
    "black_stone_weapon": 0,
    "black_stone_armor": 0,

    # Black Crystals (used to craft Pristine Black Crystals)
    "black_crystal": 0,

    # Pristine Black Crystals (main awakening material)
    # Cost not yet calculated - set to 0 by default
    "pristine_black_crystal": 0,

    # Restoration Scrolls (price per single scroll)
    # 200 scrolls = 1 trillion silver → 1 scroll = 5 billion silver
    "restoration_scroll": 5_000_000_000,  # 5B per scroll

    # Advice of Valks - not sold on market yet, set to 0
    "valks_advice_10": 0,    # +10% - not on market
    "valks_advice_50": 0,    # +50% - not on market
    "valks_advice_100": 0,   # +100% - not on market

    # Arkram's Prophecy
    "arkram_prophecy": 0,

    # Protection items
    "w_blessing": 0,
    "ogier_blessing_basic": 0,
    "ogier_blessing_blooming": 0,
    "ogier_blessing_saving": 0,

    # Breakthrough Restoration Ticket (돌파 복구권)
    "breakthrough_restoration": 0,
}

# Restoration market bundle (what you buy on market)
RESTORATION_MARKET_BUNDLE_SIZE: int = 200_000      # 200K scrolls per market bundle
RESTORATION_MARKET_BUNDLE_COST: int = 1_000_000_000_000  # 1 trillion silver

# Restoration per attempt
RESTORATION_PER_ATTEMPT: int = 200  # 200 scrolls per recovery attempt
# Cost per attempt = (200 / 200,000) * 1T = 1 billion silver

# Crafting recipes
# Format: {output_item: {input_item: quantity, ...}}
CRAFTING_RECIPES: dict[str, dict[str, int]] = {
    "pristine_black_crystal": {
        "black_stone_weapon": 10,
        "black_stone_armor": 10,
        "black_crystal": 5,
    },
}

# Hepta/Okta failsafe enhancement system
# Alternative paths for VII→VIII (Hepta) and VIII→IX (Okta)
HEPTA_SUB_ENHANCEMENTS: int = 5   # VII→VIII via 5 sub-enhancements
OKTA_SUB_ENHANCEMENTS: int = 10   # VIII→IX via 10 sub-enhancements
HEPTA_OKTA_ANVIL_PITY: int = 17   # 17 failures = guaranteed success per sub-enhancement
HEPTA_OKTA_CRYSTALS_PER_ATTEMPT: int = 15  # Exquisite Black Crystals per attempt

# Exquisite Black Crystal crafting recipe
# Used for Hepta/Okta enhancement paths
EXQUISITE_BLACK_CRYSTAL_RECIPE: dict[str, int] = {
    "restoration_scrolls": 1050,
    "valks_100": 2,
    "pristine_black_crystal": 30,
}


def calculate_crafting_cost(item: str) -> int:
    """Calculate the cost to craft an item from base materials."""
    if item not in CRAFTING_RECIPES:
        return MARKET_PRICES.get(item, 0)

    recipe = CRAFTING_RECIPES[item]
    total = 0
    for material, quantity in recipe.items():
        total += MARKET_PRICES.get(material, 0) * quantity
    return total


def get_effective_price(item: str, prefer_craft: bool = True) -> int:
    """Get the effective price, choosing cheaper between market and crafting."""
    market_price = MARKET_PRICES.get(item, 0)
    craft_cost = calculate_crafting_cost(item)

    if prefer_craft and craft_cost > 0:
        return min(market_price, craft_cost) if market_price > 0 else craft_cost
    return market_price
