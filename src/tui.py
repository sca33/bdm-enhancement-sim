"""TUI for BDM Enhancement Simulator using Textual."""
import asyncio
from dataclasses import dataclass, field
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    RichLog,
    Rule,
)
from textual.message import Message
from rich.text import Text

from .simulator import (
    AwakeningSimulator,
    EnhancementStrategy,
    RestorationStrategy,
    ValksStrategy,
    GearState,
    AttemptResult,
)
from .config import (
    AWAKENING_ENHANCEMENT_RATES,
    ANVIL_THRESHOLDS_AWAKENING,
    VALKS_MULTIPLIER_10,
    VALKS_MULTIPLIER_50,
    VALKS_MULTIPLIER_100,
)
from .market_config import (
    MARKET_PRICES,
    RESTORATION_MARKET_BUNDLE_COST,
    RESTORATION_MARKET_BUNDLE_SIZE,
    RESTORATION_PER_ATTEMPT,
    HEPTA_SUB_ENHANCEMENTS,
    OKTA_SUB_ENHANCEMENTS,
    HEPTA_OKTA_ANVIL_PITY,
    HEPTA_OKTA_CRYSTALS_PER_ATTEMPT,
    EXQUISITE_BLACK_CRYSTAL_RECIPE,
)


ROMAN_NUMERALS = {
    0: "0", 1: "I", 2: "II", 3: "III", 4: "IV",
    5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X"
}


@dataclass
class MarketPrices:
    """Custom market prices for simulation."""
    crystal_price: int = 34_650_000           # Price per pristine black crystal (77 * 450K)
    restoration_bundle_price: int = 1_000_000_000_000  # Price for 200K scrolls (1T default)
    valks_10_price: int = 0                   # Price per +10% valks
    valks_50_price: int = 0                   # Price per +50% valks
    valks_100_price: int = 0                  # Price per +100% valks

    @property
    def restoration_attempt_cost(self) -> int:
        """Cost per restoration attempt (200 scrolls).

        200K scrolls = 1T silver (default)
        200 scrolls per attempt = 1B silver per attempt
        """
        if self.restoration_bundle_price == 0:
            return 0
        # (scrolls_per_attempt / scrolls_per_bundle) * bundle_price
        return (RESTORATION_PER_ATTEMPT * self.restoration_bundle_price) // RESTORATION_MARKET_BUNDLE_SIZE


@dataclass
class SimConfig:
    """Configuration for a simulation run."""
    target_level: int = 9
    valks_10_from: int = 1      # Use +10% Valks starting from this level (0 = never)
    valks_50_from: int = 3      # Use +50% Valks starting from this level (0 = never)
    valks_100_from: int = 5     # Use +100% Valks starting from this level (0 = never)
    restoration_from: int = 6   # Use restoration from this level (0 = never)
    speed: float = 0.0          # -1 = instant (precalc), 0 = fast (default)
    market_prices: MarketPrices = field(default_factory=MarketPrices)
    use_hepta: bool = False     # Use Hepta path for VII→VIII (5 sub-enhancements)
    use_okta: bool = False      # Use Okta path for VIII→IX (10 sub-enhancements)


class ConfigScreen(Screen):
    """Configuration screen for setting up the simulation."""

    CSS = """
    ConfigScreen {
        layout: vertical;
    }

    #config-container {
        padding: 1 2;
        height: auto;
    }

    .config-row {
        height: 3;
        margin-bottom: 1;
    }

    .config-label {
        width: 30;
        content-align: left middle;
    }

    .config-select {
        width: 20;
    }

    .config-input {
        width: 25;
    }

    .config-input-small {
        width: 18;
    }

    .price-unit {
        width: 12;
        content-align: left middle;
        color: $text-muted;
    }

    #rates-table {
        margin: 1 0;
        padding: 1;
        border: solid green;
        height: auto;
    }

    #start-button {
        margin-top: 2;
        width: 100%;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 1;
    }

    .section-title {
        text-style: bold;
        color: $primary;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "start", "Start Simulation"),
    ]

    def __init__(self):
        super().__init__()
        self.config = SimConfig()

    def compose(self) -> ComposeResult:
        yield Header()

        with ScrollableContainer(id="config-container"):
            yield Static("BDM Awakening Enhancement Simulator", id="title")
            yield Rule()

            # Target level
            yield Static("Target Settings", classes="section-title")
            with Horizontal(classes="config-row"):
                yield Label("Target Level:", classes="config-label")
                yield Select(
                    [(f"+{ROMAN_NUMERALS[i]} ({i})", i) for i in range(1, 11)],
                    value=9,
                    id="target-level",
                    classes="config-select",
                )

            yield Rule()

            # Hepta/Okta failsafe enhancement
            yield Static("Hepta/Okta Failsafe Enhancement", classes="section-title")
            yield Static("(Alternative paths using Exquisite Black Crystals)")
            with Horizontal(classes="config-row"):
                yield Checkbox("Use Hepta for VII→VIII (5 sub-enhancements, 15 crystals each)", id="use-hepta")
            with Horizontal(classes="config-row"):
                yield Checkbox("Use Okta for VIII→IX (10 sub-enhancements, 15 crystals each)", id="use-okta")

            yield Rule()

            # Enhancement rates table
            yield Static("Enhancement Rates & Anvil Pity", classes="section-title")
            yield Static(self._build_rates_table(), id="rates-table")

            yield Rule()

            # Valks settings
            yield Static("Advice of Valks Settings", classes="section-title")
            yield Static("(0 = Never use, I-X = Use starting from that level)")

            with Horizontal(classes="config-row"):
                yield Label("+10% Valks from level:", classes="config-label")
                yield Select(
                    [("Never", 0)] + [(f"+{ROMAN_NUMERALS[i]}", i) for i in range(1, 11)],
                    value=1,
                    id="valks-10",
                    classes="config-select",
                )

            with Horizontal(classes="config-row"):
                yield Label("+50% Valks from level:", classes="config-label")
                yield Select(
                    [("Never", 0)] + [(f"+{ROMAN_NUMERALS[i]}", i) for i in range(1, 11)],
                    value=3,
                    id="valks-50",
                    classes="config-select",
                )

            with Horizontal(classes="config-row"):
                yield Label("+100% Valks from level:", classes="config-label")
                yield Select(
                    [("Never", 0)] + [(f"+{ROMAN_NUMERALS[i]}", i) for i in range(1, 11)],
                    value=5,
                    id="valks-100",
                    classes="config-select",
                )

            yield Rule()

            # Restoration settings
            yield Static("Restoration Scroll Settings", classes="section-title")
            with Horizontal(classes="config-row"):
                yield Label("Use restoration from level:", classes="config-label")
                yield Select(
                    [("Never", 0)] + [(f"+{ROMAN_NUMERALS[i]}", i) for i in range(1, 11)],
                    value=6,
                    id="restoration-from",
                    classes="config-select",
                )

            yield Rule()

            # Speed settings
            yield Static("Simulation Speed", classes="section-title")
            with Horizontal(classes="config-row"):
                yield Label("Animation speed:", classes="config-label")
                yield Select(
                    [
                        ("Fast", 0.0),      # Minimal delay, animated
                        ("Instant", -1.0),  # Precalculate all at once
                    ],
                    value=0.0,
                    id="speed",
                    classes="config-select",
                )

            yield Rule()

            # Market prices settings
            yield Static("Market Prices (Silver)", classes="section-title")
            yield Static("(Set to 0 if not applicable or unknown)")

            with Horizontal(classes="config-row"):
                yield Label("Crystal price:", classes="config-label")
                yield Input(
                    value="34650000",
                    placeholder="34650000",
                    id="price-crystal",
                    classes="config-input-small",
                    type="integer",
                )
                yield Static("silver", classes="price-unit")

            with Horizontal(classes="config-row"):
                yield Label("200K Restoration Scrolls:", classes="config-label")
                yield Input(
                    value="1000000000000",
                    placeholder="1T",
                    id="price-restoration",
                    classes="config-input",
                    type="integer",
                )
                yield Static("silver", classes="price-unit")

            with Horizontal(classes="config-row"):
                yield Label("Valks +10% price:", classes="config-label")
                yield Input(
                    value="0",
                    placeholder="0",
                    id="price-valks-10",
                    classes="config-input-small",
                    type="integer",
                )
                yield Static("silver", classes="price-unit")

            with Horizontal(classes="config-row"):
                yield Label("Valks +50% price:", classes="config-label")
                yield Input(
                    value="0",
                    placeholder="0",
                    id="price-valks-50",
                    classes="config-input-small",
                    type="integer",
                )
                yield Static("silver", classes="price-unit")

            with Horizontal(classes="config-row"):
                yield Label("Valks +100% price:", classes="config-label")
                yield Input(
                    value="0",
                    placeholder="0",
                    id="price-valks-100",
                    classes="config-input-small",
                    type="integer",
                )
                yield Static("silver", classes="price-unit")

            yield Rule()

            yield Button("Start Simulation", id="start-button", variant="success")

            yield Rule()

            # Strategy analysis settings
            yield Static("Strategy Analysis", classes="section-title")
            with Horizontal(classes="config-row"):
                yield Label("Simulations per strategy:", classes="config-label")
                yield Input(
                    value="1000",
                    placeholder="1000",
                    id="num-simulations",
                    classes="config-input-small",
                    type="integer",
                )
            yield Button("Restoration Strategy (+IV to +VIII)", id="restoration-strategy-button", variant="primary")
            yield Button("Hepta/Okta Strategy (with +VI restoration)", id="hepta-okta-strategy-button", variant="primary")

        yield Footer()

    def _build_rates_table(self) -> str:
        """Build the rates table string."""
        lines = ["Level   Rate    Anvil Pity"]
        lines.append("-" * 28)
        for level in range(1, 11):
            rate = AWAKENING_ENHANCEMENT_RATES.get(level, 0) * 100
            anvil = ANVIL_THRESHOLDS_AWAKENING.get(level, 0)
            anvil_str = str(anvil) if anvil > 0 else "-"
            lines.append(f"  {ROMAN_NUMERALS[level]:<6} {rate:>5.1f}%  {anvil_str:>6}")
        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-button":
            self._start_simulation()
        elif event.button.id == "restoration-strategy-button":
            self._start_restoration_strategy_analysis()
        elif event.button.id == "hepta-okta-strategy-button":
            self._start_hepta_okta_strategy_analysis()

    def action_start(self) -> None:
        self._start_simulation()

    def _parse_price(self, input_id: str) -> int:
        """Parse price from input field, returning 0 on error."""
        try:
            input_field = self.query_one(f"#{input_id}", Input)
            value = input_field.value.strip()
            if not value:
                return 0
            return int(value)
        except (ValueError, Exception):
            return 0

    def _start_simulation(self) -> None:
        # Collect config values
        target_select = self.query_one("#target-level", Select)
        valks_10_select = self.query_one("#valks-10", Select)
        valks_50_select = self.query_one("#valks-50", Select)
        valks_100_select = self.query_one("#valks-100", Select)
        restoration_select = self.query_one("#restoration-from", Select)
        speed_select = self.query_one("#speed", Select)
        use_hepta_checkbox = self.query_one("#use-hepta", Checkbox)
        use_okta_checkbox = self.query_one("#use-okta", Checkbox)

        # Collect market prices
        market_prices = MarketPrices(
            crystal_price=self._parse_price("price-crystal"),
            restoration_bundle_price=self._parse_price("price-restoration"),
            valks_10_price=self._parse_price("price-valks-10"),
            valks_50_price=self._parse_price("price-valks-50"),
            valks_100_price=self._parse_price("price-valks-100"),
        )

        self.config = SimConfig(
            target_level=target_select.value,
            valks_10_from=valks_10_select.value,
            valks_50_from=valks_50_select.value,
            valks_100_from=valks_100_select.value,
            restoration_from=restoration_select.value,
            speed=speed_select.value,
            market_prices=market_prices,
            use_hepta=use_hepta_checkbox.value,
            use_okta=use_okta_checkbox.value,
        )

        self.app.push_screen(SimulationScreen(self.config))

    def _start_restoration_strategy_analysis(self) -> None:
        """Start restoration level strategy analysis (normal enhancement, varying restoration levels)."""
        target_select = self.query_one("#target-level", Select)
        valks_10_select = self.query_one("#valks-10", Select)
        valks_50_select = self.query_one("#valks-50", Select)
        valks_100_select = self.query_one("#valks-100", Select)

        # Get number of simulations
        num_sims = self._parse_price("num-simulations")
        if num_sims < 100:
            num_sims = 100  # Minimum 100 simulations

        # Collect market prices
        market_prices = MarketPrices(
            crystal_price=self._parse_price("price-crystal"),
            restoration_bundle_price=self._parse_price("price-restoration"),
            valks_10_price=self._parse_price("price-valks-10"),
            valks_50_price=self._parse_price("price-valks-50"),
            valks_100_price=self._parse_price("price-valks-100"),
        )

        self.config = SimConfig(
            target_level=target_select.value,
            valks_10_from=valks_10_select.value,
            valks_50_from=valks_50_select.value,
            valks_100_from=valks_100_select.value,
            restoration_from=0,  # Will be varied in strategy screen
            speed=0.0,
            market_prices=market_prices,
            use_hepta=False,  # Normal enhancement only
            use_okta=False,
        )

        self.app.push_screen(RestorationStrategyScreen(self.config, num_sims))

    def _start_hepta_okta_strategy_analysis(self) -> None:
        """Start Hepta/Okta strategy analysis (with +VI restoration fixed)."""
        target_select = self.query_one("#target-level", Select)
        valks_10_select = self.query_one("#valks-10", Select)
        valks_50_select = self.query_one("#valks-50", Select)
        valks_100_select = self.query_one("#valks-100", Select)

        # Get number of simulations
        num_sims = self._parse_price("num-simulations")
        if num_sims < 100:
            num_sims = 100  # Minimum 100 simulations

        # Collect market prices
        market_prices = MarketPrices(
            crystal_price=self._parse_price("price-crystal"),
            restoration_bundle_price=self._parse_price("price-restoration"),
            valks_10_price=self._parse_price("price-valks-10"),
            valks_50_price=self._parse_price("price-valks-50"),
            valks_100_price=self._parse_price("price-valks-100"),
        )

        self.config = SimConfig(
            target_level=target_select.value,
            valks_10_from=valks_10_select.value,
            valks_50_from=valks_50_select.value,
            valks_100_from=valks_100_select.value,
            restoration_from=6,  # Fixed at +VI
            speed=0.0,
            market_prices=market_prices,
            use_hepta=False,  # Will be varied in strategy screen
            use_okta=False,
        )

        self.app.push_screen(HeptaOktaStrategyScreen(self.config, num_sims))

    def action_quit(self) -> None:
        self.app.exit()


class SimulationScreen(Screen):
    """Simulation screen showing live enhancement log."""

    CSS = """
    SimulationScreen {
        layout: vertical;
    }

    #level-caption {
        height: 3;
        padding: 0 1;
        background: $surface;
        border-bottom: solid $primary;
    }

    .caption-field {
        width: 18;
    }

    #log-container {
        height: 1fr;
        border: solid $primary;
        margin: 0 1;
    }

    #stats-container {
        height: auto;
        padding: 1;
        background: $surface;
        border-top: solid $primary;
    }

    .stats-columns {
        height: auto;
    }

    .stats-column {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }

    .stats-column-left {
        border-right: solid $primary-darken-2;
    }

    .stat-row {
        height: 1;
    }

    .stat-label {
        width: 18;
        color: $text-muted;
    }

    .stat-value {
        width: 15;
        text-align: right;
    }

    .stat-value-highlight {
        color: $success;
        text-style: bold;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #controls {
        height: 3;
        padding: 0 1;
        background: $surface;
    }

    .success {
        color: $success;
    }

    .fail {
        color: $error;
    }

    .anvil {
        color: $warning;
    }

    .level-up {
        color: $success;
        text-style: bold;
    }

    .level-down {
        color: $error;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "restart", "Restart"),
        Binding("escape", "back", "Back to Config"),
    ]

    def __init__(self, config: SimConfig):
        super().__init__()
        self.config = config
        self.simulator = AwakeningSimulator()
        self.gear = GearState()
        self.running = False
        self.attempt_count = 0
        self.target_attempts = 0  # Attempts on current target level only
        self.max_level_reached = 0  # Track highest level achieved
        # Resource tracking
        self.total_crystals = 0
        self.total_scrolls = 0
        self.total_valks_10 = 0
        self.total_valks_50 = 0
        self.total_valks_100 = 0
        self.total_silver = 0
        # Hepta/Okta tracking
        self.total_exquisite_crystals = 0  # Exquisite Black Crystals used
        self.hepta_sub_progress = 0  # 0-5 sub-enhancements completed
        self.okta_sub_progress = 0   # 0-10 sub-enhancements completed
        self.hepta_sub_pity = 0      # Current pity for active Hepta sub-enhancement
        self.okta_sub_pity = 0       # Current pity for active Okta sub-enhancement

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="level-caption"):
            yield Static(f"Target: +{ROMAN_NUMERALS[self.config.target_level]}", id="target-display", classes="caption-field")
            yield Static("Current: 0", id="current-display", classes="caption-field")
            yield Static("Max: 0", id="max-display", classes="caption-field")
            yield Static("Attempts: 0", id="attempts-display", classes="caption-field")

        yield RichLog(id="log-container", highlight=True, markup=True)

        with Container(id="stats-container"):
            with Horizontal(classes="stats-columns"):
                # Left column: Anvil pity progress for V-X and Hepta/Okta
                with Vertical(classes="stats-column stats-column-left"):
                    yield Static("Anvil Pity (V-X)", classes="section-header")
                    for level in range(5, 11):
                        cap = ANVIL_THRESHOLDS_AWAKENING.get(level, 0)
                        with Horizontal(classes="stat-row"):
                            yield Static(f"{ROMAN_NUMERALS[level]}:", classes="stat-label")
                            yield Static(f"0/{cap}", id=f"anvil-{level}", classes="stat-value")
                    # Hepta/Okta sub-enhancement progress
                    yield Static("Hepta/Okta Progress", classes="section-header", id="hepta-okta-header")
                    with Horizontal(classes="stat-row"):
                        yield Static("Hepta (VII→VIII):", classes="stat-label")
                        yield Static("-", id="hepta-progress", classes="stat-value")
                    with Horizontal(classes="stat-row"):
                        yield Static("Okta (VIII→IX):", classes="stat-label")
                        yield Static("-", id="okta-progress", classes="stat-value")

                # Right column: Resources spent
                with Vertical(classes="stats-column"):
                    yield Static("Resources Spent", classes="section-header")
                    with Horizontal(classes="stat-row"):
                        yield Static("Crystals:", classes="stat-label")
                        yield Static("0", id="stat-crystals", classes="stat-value")
                    with Horizontal(classes="stat-row"):
                        yield Static("Exquisite:", classes="stat-label")
                        yield Static("0", id="stat-exquisite", classes="stat-value")
                    with Horizontal(classes="stat-row"):
                        yield Static("Scrolls:", classes="stat-label")
                        yield Static("0", id="stat-scrolls", classes="stat-value")
                    with Horizontal(classes="stat-row"):
                        yield Static("Valks +10%:", classes="stat-label")
                        yield Static("0", id="stat-valks-10", classes="stat-value")
                    with Horizontal(classes="stat-row"):
                        yield Static("Valks +50%:", classes="stat-label")
                        yield Static("0", id="stat-valks-50", classes="stat-value")
                    with Horizontal(classes="stat-row"):
                        yield Static("Valks +100%:", classes="stat-label")
                        yield Static("0", id="stat-valks-100", classes="stat-value")
                    with Horizontal(classes="stat-row"):
                        yield Static("Silver Total:", classes="stat-label")
                        yield Static("0", id="stat-silver", classes="stat-value stat-value-highlight")

        with Horizontal(id="controls"):
            yield Button("Back", id="back-button", variant="default")
            yield Button("Restart", id="restart-button", variant="warning")

        yield Footer()

    async def on_mount(self) -> None:
        """Start the simulation when screen is mounted."""
        self.run_simulation()

    def run_simulation(self) -> None:
        """Start the simulation as a background task."""
        self.running = True
        asyncio.create_task(self._run_simulation_async())

    async def _run_simulation_async(self) -> None:
        """Run the simulation with animated output."""
        log = self.query_one("#log-container", RichLog)

        if self.config.speed < 0:
            # Instant mode: precalculate everything, then output
            log.write("[bold]Calculating...[/bold]")
            await asyncio.sleep(0.001)  # Allow UI to update

            results = []  # List of (type, data) tuples
            while self.gear.awakening_level < self.config.target_level and self.running:
                # Check if we should use Hepta/Okta paths
                if self._should_use_hepta():
                    result = self._perform_hepta_okta_attempt(is_okta=False)
                    results.append(("hepta", result))
                    if self._check_hepta_okta_complete():
                        results.append(("level_up", {"from": 7, "to": 8, "path": "Hepta"}))
                elif self._should_use_okta():
                    result = self._perform_hepta_okta_attempt(is_okta=True)
                    results.append(("okta", result))
                    if self._check_hepta_okta_complete():
                        results.append(("level_up", {"from": 8, "to": 9, "path": "Okta"}))
                else:
                    result = self._perform_enhancement()
                    results.append(("normal", result))

            # Now output all results at once
            log.clear()
            log.write("[bold]Enhancement simulation complete![/bold]\n")
            for result_type, result in results:
                if result_type == "normal":
                    self._log_attempt(log, result)
                elif result_type in ("hepta", "okta"):
                    self._log_hepta_okta_attempt(log, result, result_type == "okta")
                elif result_type == "level_up":
                    self._log_hepta_okta_complete(log, result)

            self._update_stats()

            if self.running:
                self._log_completion(log)
        else:
            # Animated mode
            log.write("[bold]Starting enhancement simulation...[/bold]\n")

            while self.gear.awakening_level < self.config.target_level and self.running:
                # Check if we should use Hepta/Okta paths
                if self._should_use_hepta():
                    result = self._perform_hepta_okta_attempt(is_okta=False)
                    self._log_hepta_okta_attempt(log, result, is_okta=False)
                    self._update_stats()
                    if self._check_hepta_okta_complete():
                        self._log_hepta_okta_complete(log, {"from": 7, "to": 8, "path": "Hepta"})
                        self._update_stats()
                elif self._should_use_okta():
                    result = self._perform_hepta_okta_attempt(is_okta=True)
                    self._log_hepta_okta_attempt(log, result, is_okta=True)
                    self._update_stats()
                    if self._check_hepta_okta_complete():
                        self._log_hepta_okta_complete(log, {"from": 8, "to": 9, "path": "Okta"})
                        self._update_stats()
                else:
                    result = self._perform_enhancement()
                    self._log_attempt(log, result)
                    self._update_stats()

                # Use minimum 0.001s delay for "fast" mode
                delay = max(0.001, self.config.speed)
                await asyncio.sleep(delay)

            if self.running:
                self._log_completion(log)

        self.running = False

    def _get_valks_for_level(self, target_level: int) -> Optional[str]:
        """Determine which Valks to use for a given target level."""
        # Priority: 100% > 50% > 10%
        if self.config.valks_100_from > 0 and target_level >= self.config.valks_100_from:
            return "100"
        if self.config.valks_50_from > 0 and target_level >= self.config.valks_50_from:
            return "50"
        if self.config.valks_10_from > 0 and target_level >= self.config.valks_10_from:
            return "10"
        return None

    def _should_use_restoration(self, current_level: int) -> bool:
        """Determine if restoration should be used at current level."""
        if self.config.restoration_from == 0:
            return False
        return current_level >= self.config.restoration_from

    def _get_exquisite_crystal_cost(self) -> int:
        """Calculate the cost of one Exquisite Black Crystal in silver.

        Recipe: 1050 restoration scrolls + 2 valks 100% + 30 pristine crystals
        """
        prices = self.config.market_prices
        scroll_cost = (EXQUISITE_BLACK_CRYSTAL_RECIPE["restoration_scrolls"] *
                       prices.restoration_bundle_price) // RESTORATION_MARKET_BUNDLE_SIZE
        valks_cost = EXQUISITE_BLACK_CRYSTAL_RECIPE["valks_100"] * prices.valks_100_price
        crystal_cost = EXQUISITE_BLACK_CRYSTAL_RECIPE["pristine_black_crystal"] * prices.crystal_price
        return scroll_cost + valks_cost + crystal_cost

    def _should_use_hepta(self) -> bool:
        """Check if we should use Hepta path for VII→VIII."""
        return (self.config.use_hepta and
                self.gear.awakening_level == 7 and
                self.hepta_sub_progress < HEPTA_SUB_ENHANCEMENTS)

    def _should_use_okta(self) -> bool:
        """Check if we should use Okta path for VIII→IX."""
        return (self.config.use_okta and
                self.gear.awakening_level == 8 and
                self.okta_sub_progress < OKTA_SUB_ENHANCEMENTS)

    def _perform_hepta_okta_attempt(self, is_okta: bool) -> dict:
        """Perform a single Hepta/Okta sub-enhancement attempt.

        Returns dict with: success, anvil_triggered, sub_progress, sub_pity
        """
        prices = self.config.market_prices
        crystals_per_attempt = HEPTA_OKTA_CRYSTALS_PER_ATTEMPT
        anvil_pity = HEPTA_OKTA_ANVIL_PITY

        # Get current pity
        current_pity = self.okta_sub_pity if is_okta else self.hepta_sub_pity

        # Cost tracking
        self.total_exquisite_crystals += crystals_per_attempt
        exquisite_cost = self._get_exquisite_crystal_cost() * crystals_per_attempt
        self.total_silver += exquisite_cost
        self.attempt_count += 1
        self.target_attempts += 1

        # Check anvil pity
        anvil_triggered = current_pity >= anvil_pity

        if anvil_triggered:
            # Guaranteed success on this sub-enhancement
            if is_okta:
                self.okta_sub_progress += 1
                self.okta_sub_pity = 0
            else:
                self.hepta_sub_progress += 1
                self.hepta_sub_pity = 0

            return {
                "success": True,
                "anvil_triggered": True,
                "sub_progress": self.okta_sub_progress if is_okta else self.hepta_sub_progress,
                "sub_pity": 0,
            }

        # Roll for success (using same base rate as normal enhancement)
        # Hepta/Okta doesn't specify success rate - use arbitrary 10% per sub-attempt
        # This may need adjustment based on actual game mechanics
        base_rate = 0.10  # 10% per sub-enhancement attempt

        if self.simulator.rng.random() < base_rate:
            # Success on sub-enhancement
            if is_okta:
                self.okta_sub_progress += 1
                self.okta_sub_pity = 0
            else:
                self.hepta_sub_progress += 1
                self.hepta_sub_pity = 0

            return {
                "success": True,
                "anvil_triggered": False,
                "sub_progress": self.okta_sub_progress if is_okta else self.hepta_sub_progress,
                "sub_pity": 0,
            }

        # Failed - increment pity
        if is_okta:
            self.okta_sub_pity += 1
        else:
            self.hepta_sub_pity += 1

        return {
            "success": False,
            "anvil_triggered": False,
            "sub_progress": self.okta_sub_progress if is_okta else self.hepta_sub_progress,
            "sub_pity": self.okta_sub_pity if is_okta else self.hepta_sub_pity,
        }

    def _check_hepta_okta_complete(self) -> bool:
        """Check if Hepta/Okta is complete and level up if so.

        Returns True if level was increased.
        """
        if (self.config.use_hepta and
            self.gear.awakening_level == 7 and
            self.hepta_sub_progress >= HEPTA_SUB_ENHANCEMENTS):
            # Hepta complete - level up to VIII
            self.gear.awakening_level = 8
            self.gear.reset_energy(8)
            self.hepta_sub_progress = 0
            self.hepta_sub_pity = 0
            self.target_attempts = 0
            return True

        if (self.config.use_okta and
            self.gear.awakening_level == 8 and
            self.okta_sub_progress >= OKTA_SUB_ENHANCEMENTS):
            # Okta complete - level up to IX
            self.gear.awakening_level = 9
            self.gear.reset_energy(9)
            self.okta_sub_progress = 0
            self.okta_sub_pity = 0
            self.target_attempts = 0
            return True

        return False

    def _perform_enhancement(self) -> AttemptResult:
        """Perform a single enhancement attempt."""
        target_level = self.gear.awakening_level + 1
        valks_type = self._get_valks_for_level(target_level)

        # Get base rate
        base_rate = AWAKENING_ENHANCEMENT_RATES.get(target_level, 0.01)

        # Apply Valks multiplier (relative bonus, not additive!)
        # Example: 0.5% with +100% Valks = 0.5% × 2.0 = 1%
        if valks_type == "10":
            base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_10)
        elif valks_type == "50":
            base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_50)
        elif valks_type == "100":
            base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_100)

        # Check anvil pity
        current_energy = self.gear.get_energy(target_level)
        max_energy = ANVIL_THRESHOLDS_AWAKENING.get(target_level, 999)
        anvil_triggered = current_energy >= max_energy and max_energy > 0

        starting_level = self.gear.awakening_level
        materials = {"pristine_black_crystal": 1}

        # Track resources using custom market prices from config
        prices = self.config.market_prices
        self.attempt_count += 1
        self.target_attempts += 1  # Track attempts on this target level
        self.total_crystals += 1
        self.total_silver += prices.crystal_price

        # Track valks usage
        if valks_type:
            materials[f"valks_advice_{valks_type}"] = 1
            if valks_type == "10":
                self.total_valks_10 += 1
                self.total_silver += prices.valks_10_price
            elif valks_type == "50":
                self.total_valks_50 += 1
                self.total_silver += prices.valks_50_price
            elif valks_type == "100":
                self.total_valks_100 += 1
                self.total_silver += prices.valks_100_price

        if anvil_triggered:
            # Guaranteed success
            self.gear.awakening_level = target_level
            self.gear.reset_energy(target_level)
            # Only reset attempts if not at final target
            if target_level < self.config.target_level:
                self.target_attempts = 0
            return AttemptResult(
                success=True,
                starting_level=starting_level,
                ending_level=target_level,
                anvil_triggered=True,
                valks_used=valks_type,
                materials_cost=materials,
            )

        # Roll for success
        success = self.simulator.rng.random() < base_rate

        if success:
            self.gear.awakening_level = target_level
            self.gear.reset_energy(target_level)
            # Only reset attempts if not at final target
            if target_level < self.config.target_level:
                self.target_attempts = 0
            return AttemptResult(
                success=True,
                starting_level=starting_level,
                ending_level=target_level,
                valks_used=valks_type,
                materials_cost=materials,
            )

        # Failed - accumulate energy
        self.gear.add_energy(target_level)

        # Handle restoration
        restoration_attempted = False
        restoration_success = False
        ending_level = self.gear.awakening_level

        if self.gear.awakening_level > 0:
            use_restoration = self._should_use_restoration(self.gear.awakening_level)

            if use_restoration:
                restoration_attempted = True
                self.total_scrolls += RESTORATION_PER_ATTEMPT
                # Add silver cost for restoration attempt
                # 200 scrolls per attempt, 200K scrolls = 1T → 200 scrolls = 1B
                self.total_silver += prices.restoration_attempt_cost
                materials["restoration_scroll"] = RESTORATION_PER_ATTEMPT
                restoration_success = self.simulator.rng.random() < 0.5

                if not restoration_success:
                    self.gear.awakening_level -= 1
                    ending_level = self.gear.awakening_level
            else:
                self.gear.awakening_level -= 1
                ending_level = self.gear.awakening_level

        return AttemptResult(
            success=False,
            starting_level=starting_level,
            ending_level=ending_level,
            restoration_attempted=restoration_attempted,
            restoration_success=restoration_success,
            valks_used=valks_type,
            materials_cost=materials,
        )

    def _log_attempt(self, log: RichLog, result: AttemptResult) -> None:
        """Log an enhancement attempt to the RichLog."""
        from_level = ROMAN_NUMERALS[result.starting_level]
        to_level = ROMAN_NUMERALS[result.starting_level + 1]

        parts = [f"[bold]{from_level}[/bold] → [bold]{to_level}[/bold]: "]

        if result.anvil_triggered:
            parts.append("[yellow bold]ANVIL SUCCESS![/yellow bold]")
        elif result.success:
            parts.append("[green]SUCCESS[/green]")
        else:
            parts.append("[red]FAIL[/red]")

        if result.valks_used:
            parts.append(f" [cyan](Valks +{result.valks_used}%)[/cyan]")

        if result.restoration_attempted:
            if result.restoration_success:
                parts.append(" [blue]| Restoration: SAVED[/blue]")
            else:
                parts.append(" [red]| Restoration: FAILED[/red]")
                parts.append(f" [red bold]↓ {ROMAN_NUMERALS[result.ending_level]}[/red bold]")

        if result.success and not result.restoration_attempted:
            parts.append(f" [green bold]↑ Now at +{ROMAN_NUMERALS[result.ending_level]}[/green bold]")

        log.write("".join(parts))

        # Track max level
        if self.gear.awakening_level > self.max_level_reached:
            self.max_level_reached = self.gear.awakening_level

        # Update level displays
        self.query_one("#current-display", Static).update(
            f"Current: +{ROMAN_NUMERALS[self.gear.awakening_level]}"
        )
        self.query_one("#max-display", Static).update(
            f"Max: +{ROMAN_NUMERALS[self.max_level_reached]}"
        )
        self.query_one("#attempts-display", Static).update(
            f"Attempts: {self.target_attempts}"
        )

        # Update anvil pity display
        self._update_anvil_pity()

    def _log_hepta_okta_attempt(self, log: RichLog, result: dict, is_okta: bool) -> None:
        """Log a Hepta/Okta sub-enhancement attempt."""
        path_name = "Okta" if is_okta else "Hepta"
        target = "IX" if is_okta else "VIII"
        max_subs = OKTA_SUB_ENHANCEMENTS if is_okta else HEPTA_SUB_ENHANCEMENTS

        parts = [f"[cyan]{path_name}[/cyan] ({result['sub_progress']}/{max_subs}): "]

        if result["anvil_triggered"]:
            parts.append("[yellow bold]ANVIL SUCCESS![/yellow bold]")
        elif result["success"]:
            parts.append("[green]SUB SUCCESS[/green]")
        else:
            parts.append(f"[red]FAIL[/red] (pity: {result['sub_pity']}/{HEPTA_OKTA_ANVIL_PITY})")

        log.write("".join(parts))

        # Update displays
        self.query_one("#current-display", Static).update(
            f"Current: +{ROMAN_NUMERALS[self.gear.awakening_level]}"
        )
        self.query_one("#attempts-display", Static).update(
            f"Attempts: {self.target_attempts}"
        )

    def _log_hepta_okta_complete(self, log: RichLog, result: dict) -> None:
        """Log completion of Hepta/Okta enhancement path."""
        from_level = ROMAN_NUMERALS[result["from"]]
        to_level = ROMAN_NUMERALS[result["to"]]
        path = result["path"]

        log.write("")
        log.write(f"[bold magenta]═══ {path} COMPLETE! {from_level} → {to_level} ═══[/bold magenta]")
        log.write("")

        # Track max level
        if self.gear.awakening_level > self.max_level_reached:
            self.max_level_reached = self.gear.awakening_level

        # Update displays
        self.query_one("#current-display", Static).update(
            f"Current: +{ROMAN_NUMERALS[self.gear.awakening_level]}"
        )
        self.query_one("#max-display", Static).update(
            f"Max: +{ROMAN_NUMERALS[self.max_level_reached]}"
        )

    def _update_anvil_pity(self) -> None:
        """Update the anvil pity display for levels V-X."""
        # Update each level's anvil pity display
        for level in range(5, 11):
            current_energy = self.gear.get_energy(level)
            cap = ANVIL_THRESHOLDS_AWAKENING.get(level, 0)
            self.query_one(f"#anvil-{level}", Static).update(f"{current_energy}/{cap}")

    def _format_silver(self, silver: int) -> str:
        """Format silver amount with K/M/B suffix."""
        if silver >= 1_000_000_000:
            return f"{silver / 1_000_000_000:.1f}B"
        if silver >= 1_000_000:
            return f"{silver / 1_000_000:.1f}M"
        if silver >= 1_000:
            return f"{silver / 1_000:.1f}K"
        return str(silver)

    def _log_completion(self, log: RichLog) -> None:
        """Log completion message."""
        log.write("")
        log.write("[bold green]════════════════════════════════════════[/bold green]")
        log.write(f"[bold green]  REACHED +{ROMAN_NUMERALS[self.config.target_level]}![/bold green]")
        log.write("[bold green]════════════════════════════════════════[/bold green]")
        log.write("")
        log.write("[bold]Final Statistics:[/bold]")
        log.write(f"  Total Attempts: {self.attempt_count}")
        log.write("")
        log.write("[bold]Resources Spent:[/bold]")
        log.write(f"  Crystals: {self.total_crystals}")
        if self.total_exquisite_crystals > 0:
            log.write(f"  Exquisite Black Crystals: {self.total_exquisite_crystals}")
        log.write(f"  Restoration Scrolls: {self.total_scrolls:,}")
        if self.total_valks_10 > 0:
            log.write(f"  Valks +10%: {self.total_valks_10}")
        if self.total_valks_50 > 0:
            log.write(f"  Valks +50%: {self.total_valks_50}")
        if self.total_valks_100 > 0:
            log.write(f"  Valks +100%: {self.total_valks_100}")
        log.write(f"  [yellow bold]Silver Total: {self._format_silver(self.total_silver)}[/yellow bold]")

    def _update_stats(self) -> None:
        """Update statistics display."""
        # Left column: Anvil pity
        self._update_anvil_pity()

        # Hepta/Okta progress
        if self.config.use_hepta:
            hepta_text = f"{self.hepta_sub_progress}/{HEPTA_SUB_ENHANCEMENTS} ({self.hepta_sub_pity}/{HEPTA_OKTA_ANVIL_PITY})"
        else:
            hepta_text = "-"
        self.query_one("#hepta-progress", Static).update(hepta_text)

        if self.config.use_okta:
            okta_text = f"{self.okta_sub_progress}/{OKTA_SUB_ENHANCEMENTS} ({self.okta_sub_pity}/{HEPTA_OKTA_ANVIL_PITY})"
        else:
            okta_text = "-"
        self.query_one("#okta-progress", Static).update(okta_text)

        # Right column: Resources
        self.query_one("#stat-crystals", Static).update(str(self.total_crystals))
        self.query_one("#stat-exquisite", Static).update(str(self.total_exquisite_crystals))
        self.query_one("#stat-scrolls", Static).update(f"{self.total_scrolls:,}")
        self.query_one("#stat-valks-10", Static).update(str(self.total_valks_10))
        self.query_one("#stat-valks-50", Static).update(str(self.total_valks_50))
        self.query_one("#stat-valks-100", Static).update(str(self.total_valks_100))
        self.query_one("#stat-silver", Static).update(self._format_silver(self.total_silver))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-button":
            self.action_back()
        elif event.button.id == "restart-button":
            self.action_restart()

    def action_back(self) -> None:
        """Go back to config screen."""
        self.running = False
        self.app.pop_screen()

    def action_restart(self) -> None:
        """Restart the simulation."""
        self.running = False
        # Reset state
        self.gear = GearState()
        self.attempt_count = 0
        self.target_attempts = 0
        self.max_level_reached = 0
        # Resource tracking
        self.total_crystals = 0
        self.total_scrolls = 0
        self.total_valks_10 = 0
        self.total_valks_50 = 0
        self.total_valks_100 = 0
        self.total_silver = 0
        # Hepta/Okta tracking
        self.total_exquisite_crystals = 0
        self.hepta_sub_progress = 0
        self.okta_sub_progress = 0
        self.hepta_sub_pity = 0
        self.okta_sub_pity = 0

        # Clear log
        log = self.query_one("#log-container", RichLog)
        log.clear()

        # Update displays
        self._update_stats()
        self.query_one("#current-display", Static).update("Current: 0")
        self.query_one("#max-display", Static).update("Max: 0")
        self.query_one("#attempts-display", Static).update("Attempts: 0")

        # Restart
        self.run_simulation()

    def action_quit(self) -> None:
        self.running = False
        self.app.exit()


class HeptaOktaStrategyScreen(Screen):
    """Screen for Monte Carlo Hepta/Okta strategy analysis."""

    CSS = """
    HeptaOktaStrategyScreen {
        layout: vertical;
    }

    #strategy-header {
        height: 3;
        padding: 0 1;
        background: $surface;
        border-bottom: solid $primary;
    }

    #strategy-status {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
    }

    #results-container {
        height: 1fr;
        padding: 1;
        overflow-y: auto;
    }

    .results-table {
        width: 100%;
    }

    .best-strategy {
        background: $success-darken-2;
    }

    #strategy-controls {
        height: 3;
        padding: 0 1;
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "back", "Back to Config"),
    ]

    def __init__(self, config: SimConfig, num_simulations: int = 1000):
        super().__init__()
        self.config = config
        self.num_simulations = num_simulations
        self.running = False
        self.results = {}

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="strategy-header"):
            yield Static(f"Strategy Analysis for Target: +{ROMAN_NUMERALS[self.config.target_level]}", id="strategy-title")

        with Horizontal(id="strategy-status"):
            yield Static("Status: Ready", id="status")

        yield RichLog(id="results-container", highlight=True, markup=True)

        with Horizontal(id="strategy-controls"):
            yield Button("Back", id="back-button", variant="default")

        yield Footer()

    async def on_mount(self) -> None:
        """Start the analysis when screen is mounted."""
        self.running = True
        asyncio.create_task(self._run_analysis())

    async def _run_analysis(self) -> None:
        """Run Monte Carlo analysis for different Hepta/Okta strategies."""
        log = self.query_one("#results-container", RichLog)
        status = self.query_one("#status", Static)

        log.write("[bold]Monte Carlo Strategy Analysis[/bold]")
        log.write(f"Target: +{ROMAN_NUMERALS[self.config.target_level]}, Simulations: {self.num_simulations}")
        log.write("Restoration: from +VI (fixed)\n")

        # Test 4 Hepta/Okta combinations with restoration from VI
        # Format: (use_hepta, use_okta, label)
        strategies = [
            (True, True, "Hepta+Okta"),
            (True, False, "Hepta only"),
            (False, True, "Okta only"),
            (False, False, "Normal"),
        ]
        results = {}

        await self._redraw_table(log, results, strategies)
        await asyncio.sleep(0.01)

        # Run simulations for each strategy
        batch_size = max(10, self.num_simulations // 20)  # Update every 5%

        for use_hepta, use_okta, label in strategies:
            if not self.running:
                break

            status.update(f"Status: Testing {label}...")
            strategy_key = (use_hepta, use_okta)

            sim_results = []  # List of (crystals, scrolls, silver, exquisite)
            for i in range(self.num_simulations):
                result = self._run_single_simulation(
                    restoration_from=6,  # Fixed at +VI
                    use_hepta=use_hepta,
                    use_okta=use_okta
                )
                sim_results.append(result)

                # Update progress periodically
                if (i + 1) % batch_size == 0 or i == self.num_simulations - 1:
                    progress = int((i + 1) / self.num_simulations * 100)

                    # Sort by silver for percentiles
                    sorted_by_silver = sorted(sim_results, key=lambda x: x[2])
                    p50_idx = len(sorted_by_silver) // 2
                    p90_idx = int(len(sorted_by_silver) * 0.9)

                    results[strategy_key] = {
                        "p50": sorted_by_silver[p50_idx],
                        "p90": sorted_by_silver[p90_idx],
                        "worst": sorted_by_silver[-1],
                        "label": label,
                        "progress": progress,
                    }

                    # Redraw table
                    await self._redraw_table(log, results, strategies)
                    await asyncio.sleep(0.001)

        # Final redraw with best highlighted
        if results:
            await self._redraw_table(log, results, strategies, final=True)

        status.update("Status: Complete!")
        self.running = False

    async def _redraw_table(self, log: RichLog, results: dict, strategies: list, final: bool = False) -> None:
        """Redraw the results table."""
        log.clear()
        log.write("[bold]Monte Carlo Strategy Analysis[/bold]")
        log.write(f"Target: +{ROMAN_NUMERALS[self.config.target_level]}, Simulations: {self.num_simulations}")
        log.write("Restoration: from +VI (fixed)\n")

        # Header
        log.write(f"{'Strategy':<12} {'Prog.':>6} {'Crystals':>10} {'Exquisite':>10} {'Scrolls':>10} {'Silver':>12}")
        log.write("-" * 64)

        # Find best strategy if final
        best_strategy = None
        if final and results:
            best_strategy = min(results.keys(), key=lambda k: results[k]["p50"][2])  # Sort by silver

        # Sort by p50 silver if final, otherwise keep original order
        if final:
            display_order = sorted(results.keys(), key=lambda k: results[k]["p50"][2])
        else:
            display_order = [(h, o) for h, o, _ in strategies]

        for strategy_key in display_order:
            if strategy_key in results:
                r = results[strategy_key]
                label = r["label"]
                progress = f"{r['progress']}%"

                # P50 row (crystals, scrolls, silver, exquisite)
                p50_crystals, p50_scrolls, p50_silver, p50_exquisite = r["p50"]
                if final and strategy_key == best_strategy:
                    log.write(f"[green bold]{label:<12} {progress:>6} {p50_crystals:>10} {p50_exquisite:>10} {p50_scrolls:>10} {self._format_silver(p50_silver):>12} ★ P50[/green bold]")
                else:
                    log.write(f"{label:<12} {progress:>6} {p50_crystals:>10} {p50_exquisite:>10} {p50_scrolls:>10} {self._format_silver(p50_silver):>12}    P50")

                # P90 row
                p90_crystals, p90_scrolls, p90_silver, p90_exquisite = r["p90"]
                log.write(f"{'':12} {'':>6} {p90_crystals:>10} {p90_exquisite:>10} {p90_scrolls:>10} {self._format_silver(p90_silver):>12}    P90")

                # Worst row
                worst_crystals, worst_scrolls, worst_silver, worst_exquisite = r["worst"]
                log.write(f"{'':12} {'':>6} {worst_crystals:>10} {worst_exquisite:>10} {worst_scrolls:>10} {self._format_silver(worst_silver):>12}    Worst")
                log.write("")
            else:
                use_hepta, use_okta = strategy_key
                label = next((l for h, o, l in strategies if h == use_hepta and o == use_okta), "Unknown")
                log.write(f"{label:<12} {'wait':>6} {'-':>10} {'-':>10} {'-':>10} {'-':>12}")

        log.write("-" * 64)

        if final and best_strategy is not None:
            best_label = results[best_strategy]["label"]
            best_p50_silver = self._format_silver(results[best_strategy]["p50"][2])
            log.write(f"\n[bold green]★ Recommended: {best_label} (P50 Silver: {best_p50_silver})[/bold green]")

    def _get_exquisite_crystal_cost(self) -> int:
        """Calculate the cost of one Exquisite Black Crystal in silver."""
        prices = self.config.market_prices
        scroll_cost = (EXQUISITE_BLACK_CRYSTAL_RECIPE["restoration_scrolls"] *
                       prices.restoration_bundle_price) // RESTORATION_MARKET_BUNDLE_SIZE
        valks_cost = EXQUISITE_BLACK_CRYSTAL_RECIPE["valks_100"] * prices.valks_100_price
        crystal_cost = EXQUISITE_BLACK_CRYSTAL_RECIPE["pristine_black_crystal"] * prices.crystal_price
        return scroll_cost + valks_cost + crystal_cost

    def _run_single_simulation(self, restoration_from: int, use_hepta: bool = False, use_okta: bool = False) -> tuple[int, int, int, int]:
        """Run a single simulation and return (crystals, scrolls, silver, exquisite)."""
        simulator = AwakeningSimulator()
        gear = GearState()
        prices = self.config.market_prices
        total_crystals = 0
        total_scrolls = 0
        total_silver = 0
        total_exquisite = 0

        # Hepta/Okta state
        hepta_sub_progress = 0
        okta_sub_progress = 0
        hepta_sub_pity = 0
        okta_sub_pity = 0

        while gear.awakening_level < self.config.target_level:
            # Check if we should use Hepta path
            if (use_hepta and
                gear.awakening_level == 7 and
                hepta_sub_progress < HEPTA_SUB_ENHANCEMENTS):
                # Hepta sub-enhancement attempt
                total_exquisite += HEPTA_OKTA_CRYSTALS_PER_ATTEMPT
                total_silver += self._get_exquisite_crystal_cost() * HEPTA_OKTA_CRYSTALS_PER_ATTEMPT

                # Check pity
                if hepta_sub_pity >= HEPTA_OKTA_ANVIL_PITY:
                    hepta_sub_progress += 1
                    hepta_sub_pity = 0
                elif simulator.rng.random() < 0.10:  # 10% success rate
                    hepta_sub_progress += 1
                    hepta_sub_pity = 0
                else:
                    hepta_sub_pity += 1

                # Check if Hepta complete
                if hepta_sub_progress >= HEPTA_SUB_ENHANCEMENTS:
                    gear.awakening_level = 8
                    gear.reset_energy(8)
                    hepta_sub_progress = 0
                    hepta_sub_pity = 0
                continue

            # Check if we should use Okta path
            if (use_okta and
                gear.awakening_level == 8 and
                okta_sub_progress < OKTA_SUB_ENHANCEMENTS):
                # Okta sub-enhancement attempt
                total_exquisite += HEPTA_OKTA_CRYSTALS_PER_ATTEMPT
                total_silver += self._get_exquisite_crystal_cost() * HEPTA_OKTA_CRYSTALS_PER_ATTEMPT

                # Check pity
                if okta_sub_pity >= HEPTA_OKTA_ANVIL_PITY:
                    okta_sub_progress += 1
                    okta_sub_pity = 0
                elif simulator.rng.random() < 0.10:  # 10% success rate
                    okta_sub_progress += 1
                    okta_sub_pity = 0
                else:
                    okta_sub_pity += 1

                # Check if Okta complete
                if okta_sub_progress >= OKTA_SUB_ENHANCEMENTS:
                    gear.awakening_level = 9
                    gear.reset_energy(9)
                    okta_sub_progress = 0
                    okta_sub_pity = 0
                continue

            # Normal enhancement
            target_level = gear.awakening_level + 1

            # Determine valks
            valks_type = None
            if self.config.valks_100_from > 0 and target_level >= self.config.valks_100_from:
                valks_type = "100"
            elif self.config.valks_50_from > 0 and target_level >= self.config.valks_50_from:
                valks_type = "50"
            elif self.config.valks_10_from > 0 and target_level >= self.config.valks_10_from:
                valks_type = "10"

            # Crystal cost
            total_crystals += 1
            total_silver += prices.crystal_price

            # Valks cost
            if valks_type == "10":
                total_silver += prices.valks_10_price
            elif valks_type == "50":
                total_silver += prices.valks_50_price
            elif valks_type == "100":
                total_silver += prices.valks_100_price

            # Get success rate
            base_rate = AWAKENING_ENHANCEMENT_RATES.get(target_level, 0.01)
            if valks_type == "10":
                base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_10)
            elif valks_type == "50":
                base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_50)
            elif valks_type == "100":
                base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_100)

            # Check anvil pity
            current_energy = gear.get_energy(target_level)
            max_energy = ANVIL_THRESHOLDS_AWAKENING.get(target_level, 999)
            anvil_triggered = current_energy >= max_energy and max_energy > 0

            if anvil_triggered:
                gear.awakening_level = target_level
                gear.reset_energy(target_level)
                continue

            # Roll for success
            if simulator.rng.random() < base_rate:
                gear.awakening_level = target_level
                gear.reset_energy(target_level)
            else:
                # Failed
                gear.add_energy(target_level)

                if gear.awakening_level > 0:
                    use_restoration = restoration_from > 0 and gear.awakening_level >= restoration_from

                    if use_restoration:
                        total_scrolls += RESTORATION_PER_ATTEMPT
                        total_silver += prices.restoration_attempt_cost
                        if simulator.rng.random() >= 0.5:  # Restoration failed
                            gear.awakening_level -= 1
                    else:
                        gear.awakening_level -= 1

        return (total_crystals, total_scrolls, total_silver, total_exquisite)

    def _format_silver(self, silver: int) -> str:
        """Format silver amount with K/M/B/T suffix."""
        if silver >= 1_000_000_000_000:
            return f"{silver / 1_000_000_000_000:.1f}T"
        if silver >= 1_000_000_000:
            return f"{silver / 1_000_000_000:.1f}B"
        if silver >= 1_000_000:
            return f"{silver / 1_000_000:.1f}M"
        if silver >= 1_000:
            return f"{silver / 1_000:.1f}K"
        return str(silver)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-button":
            self.action_back()

    def action_back(self) -> None:
        self.running = False
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.running = False
        self.app.exit()


class RestorationStrategyScreen(Screen):
    """Screen for Monte Carlo restoration level strategy analysis."""

    CSS = """
    RestorationStrategyScreen {
        layout: vertical;
    }

    #strategy-header {
        height: 3;
        padding: 0 1;
        background: $surface;
        border-bottom: solid $primary;
    }

    #strategy-status {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
    }

    #results-container {
        height: 1fr;
        padding: 1;
        overflow-y: auto;
    }

    .results-table {
        width: 100%;
    }

    .best-strategy {
        background: $success-darken-2;
    }

    #strategy-controls {
        height: 3;
        padding: 0 1;
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "back", "Back to Config"),
    ]

    def __init__(self, config: SimConfig, num_simulations: int = 1000):
        super().__init__()
        self.config = config
        self.num_simulations = num_simulations
        self.running = False
        self.results = {}

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="strategy-header"):
            yield Static(f"Restoration Strategy Analysis for Target: +{ROMAN_NUMERALS[self.config.target_level]}", id="strategy-title")

        with Horizontal(id="strategy-status"):
            yield Static("Status: Ready", id="status")

        yield RichLog(id="results-container", highlight=True, markup=True)

        with Horizontal(id="strategy-controls"):
            yield Button("Back", id="back-button", variant="default")

        yield Footer()

    async def on_mount(self) -> None:
        """Start the analysis when screen is mounted."""
        self.running = True
        asyncio.create_task(self._run_analysis())

    async def _run_analysis(self) -> None:
        """Run Monte Carlo analysis for different restoration strategies."""
        log = self.query_one("#results-container", RichLog)
        status = self.query_one("#status", Static)

        log.write("[bold]Monte Carlo Restoration Strategy Analysis[/bold]")
        log.write(f"Target: +{ROMAN_NUMERALS[self.config.target_level]}, Simulations: {self.num_simulations}\n")

        # Test restoration starting from IV(4), V(5), VI(6), VII(7), VIII(8) up to target-1
        restoration_options = [i for i in range(4, self.config.target_level)]
        results = {}

        await self._redraw_table(log, results, restoration_options)
        await asyncio.sleep(0.01)

        # Run simulations for each strategy
        batch_size = max(10, self.num_simulations // 20)  # Update every 5%

        for rest_from in restoration_options:
            if not self.running:
                break

            rest_label = f"+{ROMAN_NUMERALS[rest_from]}"
            status.update(f"Status: Testing restoration from {rest_label}...")

            sim_results = []  # List of (crystals, scrolls, silver)
            for i in range(self.num_simulations):
                result = self._run_single_simulation(rest_from)
                sim_results.append(result)

                # Update progress periodically
                if (i + 1) % batch_size == 0 or i == self.num_simulations - 1:
                    progress = int((i + 1) / self.num_simulations * 100)

                    # Sort by silver for percentiles
                    sorted_by_silver = sorted(sim_results, key=lambda x: x[2])
                    p50_idx = len(sorted_by_silver) // 2
                    p90_idx = int(len(sorted_by_silver) * 0.9)

                    results[rest_from] = {
                        "p50": sorted_by_silver[p50_idx],
                        "p90": sorted_by_silver[p90_idx],
                        "worst": sorted_by_silver[-1],
                        "label": rest_label,
                        "progress": progress,
                    }

                    # Redraw table
                    await self._redraw_table(log, results, restoration_options)
                    await asyncio.sleep(0.001)

        # Final redraw with best highlighted
        if results:
            await self._redraw_table(log, results, restoration_options, final=True)

        status.update("Status: Complete!")
        self.running = False

    async def _redraw_table(self, log: RichLog, results: dict, restoration_options: list, final: bool = False) -> None:
        """Redraw the results table."""
        log.clear()
        log.write("[bold]Monte Carlo Restoration Strategy Analysis[/bold]")
        log.write(f"Target: +{ROMAN_NUMERALS[self.config.target_level]}, Simulations: {self.num_simulations}\n")

        # Header
        log.write(f"{'Rest.From':<10} {'Prog.':>6} {'Crystals':>10} {'Scrolls':>10} {'Silver':>12}")
        log.write("-" * 52)

        # Find best strategy if final
        best_strategy = None
        if final and results:
            best_strategy = min(results.keys(), key=lambda k: results[k]["p50"][2])  # Sort by silver

        # Sort by p50 silver if final, otherwise keep original order
        if final:
            display_order = sorted(results.keys(), key=lambda k: results[k]["p50"][2])
        else:
            display_order = restoration_options

        for rest_from in display_order:
            rest_label = f"+{ROMAN_NUMERALS[rest_from]}"

            if rest_from in results:
                r = results[rest_from]
                progress = f"{r['progress']}%"

                # P50 row
                p50_crystals, p50_scrolls, p50_silver = r["p50"]
                if final and rest_from == best_strategy:
                    log.write(f"[green bold]{rest_label:<10} {progress:>6} {p50_crystals:>10} {p50_scrolls:>10} {self._format_silver(p50_silver):>12} ★ P50[/green bold]")
                else:
                    log.write(f"{rest_label:<10} {progress:>6} {p50_crystals:>10} {p50_scrolls:>10} {self._format_silver(p50_silver):>12}    P50")

                # P90 row
                p90_crystals, p90_scrolls, p90_silver = r["p90"]
                log.write(f"{'':10} {'':>6} {p90_crystals:>10} {p90_scrolls:>10} {self._format_silver(p90_silver):>12}    P90")

                # Worst row
                worst_crystals, worst_scrolls, worst_silver = r["worst"]
                log.write(f"{'':10} {'':>6} {worst_crystals:>10} {worst_scrolls:>10} {self._format_silver(worst_silver):>12}    Worst")
                log.write("")
            else:
                log.write(f"{rest_label:<10} {'wait':>6} {'-':>10} {'-':>10} {'-':>12}")

        log.write("-" * 52)

        if final and best_strategy is not None:
            best_label = results[best_strategy]["label"]
            best_p50_silver = self._format_silver(results[best_strategy]["p50"][2])
            log.write(f"\n[bold green]★ Recommended: {best_label} (P50 Silver: {best_p50_silver})[/bold green]")

    def _run_single_simulation(self, restoration_from: int) -> tuple[int, int, int]:
        """Run a single simulation and return (crystals, scrolls, silver)."""
        simulator = AwakeningSimulator()
        gear = GearState()
        prices = self.config.market_prices
        total_crystals = 0
        total_scrolls = 0
        total_silver = 0

        while gear.awakening_level < self.config.target_level:
            target_level = gear.awakening_level + 1

            # Determine valks
            valks_type = None
            if self.config.valks_100_from > 0 and target_level >= self.config.valks_100_from:
                valks_type = "100"
            elif self.config.valks_50_from > 0 and target_level >= self.config.valks_50_from:
                valks_type = "50"
            elif self.config.valks_10_from > 0 and target_level >= self.config.valks_10_from:
                valks_type = "10"

            # Crystal cost
            total_crystals += 1
            total_silver += prices.crystal_price

            # Valks cost
            if valks_type == "10":
                total_silver += prices.valks_10_price
            elif valks_type == "50":
                total_silver += prices.valks_50_price
            elif valks_type == "100":
                total_silver += prices.valks_100_price

            # Get success rate
            base_rate = AWAKENING_ENHANCEMENT_RATES.get(target_level, 0.01)
            if valks_type == "10":
                base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_10)
            elif valks_type == "50":
                base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_50)
            elif valks_type == "100":
                base_rate = min(1.0, base_rate * VALKS_MULTIPLIER_100)

            # Check anvil pity
            current_energy = gear.get_energy(target_level)
            max_energy = ANVIL_THRESHOLDS_AWAKENING.get(target_level, 999)
            anvil_triggered = current_energy >= max_energy and max_energy > 0

            if anvil_triggered:
                gear.awakening_level = target_level
                gear.reset_energy(target_level)
                continue

            # Roll for success
            if simulator.rng.random() < base_rate:
                gear.awakening_level = target_level
                gear.reset_energy(target_level)
            else:
                # Failed
                gear.add_energy(target_level)

                if gear.awakening_level > 0:
                    use_restoration = restoration_from > 0 and gear.awakening_level >= restoration_from

                    if use_restoration:
                        total_scrolls += RESTORATION_PER_ATTEMPT
                        total_silver += prices.restoration_attempt_cost
                        if simulator.rng.random() >= 0.5:  # Restoration failed
                            gear.awakening_level -= 1
                    else:
                        gear.awakening_level -= 1

        return (total_crystals, total_scrolls, total_silver)

    def _format_silver(self, silver: int) -> str:
        """Format silver amount with K/M/B/T suffix."""
        if silver >= 1_000_000_000_000:
            return f"{silver / 1_000_000_000_000:.1f}T"
        if silver >= 1_000_000_000:
            return f"{silver / 1_000_000_000:.1f}B"
        if silver >= 1_000_000:
            return f"{silver / 1_000_000:.1f}M"
        if silver >= 1_000:
            return f"{silver / 1_000:.1f}K"
        return str(silver)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-button":
            self.action_back()

    def action_back(self) -> None:
        self.running = False
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.running = False
        self.app.exit()


class BDMEnhancementApp(App):
    """Main TUI application."""

    TITLE = "BDM Enhancement Simulator"
    CSS = """
    Screen {
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
    ]

    def on_mount(self) -> None:
        self.push_screen(ConfigScreen())


def main():
    """Entry point for the TUI."""
    app = BDMEnhancementApp()
    app.run()


if __name__ == "__main__":
    main()
