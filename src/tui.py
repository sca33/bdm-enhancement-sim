"""TUI for BDM Enhancement Simulator using Textual."""
import asyncio
from dataclasses import dataclass, field
from operator import itemgetter
from typing import Optional

from textual.app import App, ComposeResult
from textual.events import Click
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    RichLog,
    Rule,
)

# Import item_types to trigger module registration
from . import item_types  # noqa: F401
from .screens import ModuleSelectScreen
from .simulator import (
    AwakeningSimulator,
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
    RESTORATION_MARKET_BUNDLE_SIZE,
    RESTORATION_PER_ATTEMPT,
    HEPTA_SUB_ENHANCEMENTS,
    OKTA_SUB_ENHANCEMENTS,
    HEPTA_OKTA_ANVIL_PITY,
    HEPTA_OKTA_CRYSTALS_PER_ATTEMPT,
    EXQUISITE_BLACK_CRYSTAL_RECIPE,
)
from .simulation_engine import (
    EnhancementEngine,
    SimulationConfig as EngineConfig,
    MarketPrices,
)
from .utils import format_silver, format_time


ROMAN_NUMERALS = {
    0: "0", 1: "I", 2: "II", 3: "III", 4: "IV",
    5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X"
}


@dataclass
class SimConfig:
    """Configuration for a simulation run."""
    target_level: int = 9
    start_level: int = 0        # Starting awakening level (0-9)
    start_hepta: int = 0        # Starting Hepta sub-enhancement progress (0-4)
    start_okta: int = 0         # Starting Okta sub-enhancement progress (0-9)
    valks_10_from: int = 1      # Use +10% Valks starting from this level (0 = never)
    valks_50_from: int = 3      # Use +50% Valks starting from this level (0 = never)
    valks_100_from: int = 5     # Use +100% Valks starting from this level (0 = never)
    restoration_from: int = 6   # Use restoration from this level (0 = never)
    speed: float = 0.0          # -1 = instant, 0 = fast (default), 1 = regular (in-game)
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

    .hidden {
        display: none;
    }

    .strategy-buttons {
        height: auto;
        margin-top: 1;
    }

    .strategy-buttons Button {
        margin-right: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "back", "Back"),
        Binding("enter", "start", "Start Simulation"),
    ]

    def __init__(self):
        super().__init__()
        self.config = SimConfig()

    def action_back(self) -> None:
        """Go back to module selection screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        yield Header()

        with ScrollableContainer(id="config-container"):
            yield Static("BDM Awakening Enhancement Simulator", id="title")
            with Collapsible(title="Enhancement Rates & Anvil Pity", collapsed=True):
                yield Static(self._build_rates_table(), id="rates-table")
            yield Rule()

            # Target and Starting level
            yield Static("Target & Starting Settings", classes="section-title")
            with Horizontal(classes="config-row"):
                yield Label("Target Level:", classes="config-label")
                yield Select(
                    [(f"+{ROMAN_NUMERALS[i]} ({i})", i) for i in range(1, 11)],
                    value=9,
                    id="target-level",
                    classes="config-select",
                )
            with Horizontal(classes="config-row"):
                yield Label("Start Level:", classes="config-label")
                yield Select(
                    [(f"+{ROMAN_NUMERALS[i]} ({i})", i) for i in range(0, 10)],
                    value=0,
                    id="start-level",
                    classes="config-select",
                )
            with Horizontal(classes="config-row", id="start-hepta-row"):
                yield Label("Start Hepta Progress:", classes="config-label")
                yield Select(
                    [(f"{i}/5", i) for i in range(0, 5)],
                    value=0,
                    id="start-hepta",
                    classes="config-select",
                )
            with Horizontal(classes="config-row", id="start-okta-row"):
                yield Label("Start Okta Progress:", classes="config-label")
                yield Select(
                    [(f"{i}/10", i) for i in range(0, 10)],
                    value=0,
                    id="start-okta",
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
                        ("Regular", 1.0),   # ~1 second per enhancement (in-game speed)
                    ],
                    value=0.0,
                    id="speed",
                    classes="config-select",
                )

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
            with Horizontal(classes="strategy-buttons"):
                yield Button("Restoration Strategy", id="restoration-strategy-button", variant="primary")
                yield Button("Hepta/Okta Strategy", id="hepta-okta-strategy-button", variant="primary")

        yield Footer()

    def on_mount(self) -> None:
        """Hide Hepta/Okta starting rows initially."""
        self.query_one("#start-hepta-row").add_class("hidden")
        self.query_one("#start-okta-row").add_class("hidden")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle start level changes to show/hide Hepta/Okta rows."""
        if event.select.id == "start-level":
            start_level = event.value
            hepta_row = self.query_one("#start-hepta-row")
            okta_row = self.query_one("#start-okta-row")

            # Show Hepta row only if start level is VII (7)
            if start_level == 7:
                hepta_row.remove_class("hidden")
            else:
                hepta_row.add_class("hidden")
                # Reset Hepta progress if not at level VII
                self.query_one("#start-hepta", Select).value = 0

            # Show Okta row only if start level is VIII (8)
            if start_level == 8:
                okta_row.remove_class("hidden")
            else:
                okta_row.add_class("hidden")
                # Reset Okta progress if not at level VIII
                self.query_one("#start-okta", Select).value = 0

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

    def _get_price(self, price_key: str) -> int:
        """Get price from app-level market prices."""
        return self.app.market_prices.get(price_key, 0)

    def _parse_input(self, input_id: str, default: int = 0) -> int:
        """Parse integer from input field, returning default on error."""
        try:
            input_field = self.query_one(f"#{input_id}", Input)
            value = input_field.value.strip()
            if not value:
                return default
            return int(value)
        except (ValueError, Exception):
            return default

    def _start_simulation(self) -> None:
        # Collect config values
        target_select = self.query_one("#target-level", Select)
        start_level_select = self.query_one("#start-level", Select)
        start_hepta_select = self.query_one("#start-hepta", Select)
        start_okta_select = self.query_one("#start-okta", Select)
        valks_10_select = self.query_one("#valks-10", Select)
        valks_50_select = self.query_one("#valks-50", Select)
        valks_100_select = self.query_one("#valks-100", Select)
        restoration_select = self.query_one("#restoration-from", Select)
        speed_select = self.query_one("#speed", Select)
        use_hepta_checkbox = self.query_one("#use-hepta", Checkbox)
        use_okta_checkbox = self.query_one("#use-okta", Checkbox)

        # Collect market prices
        market_prices = MarketPrices(
            crystal_price=self._get_price("crystal"),
            restoration_bundle_price=self._get_price("restoration"),
            valks_10_price=self._get_price("valks_10"),
            valks_50_price=self._get_price("valks_50"),
            valks_100_price=self._get_price("valks_100"),
        )

        self.config = SimConfig(
            target_level=target_select.value,
            start_level=start_level_select.value,
            start_hepta=start_hepta_select.value,
            start_okta=start_okta_select.value,
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
        start_level_select = self.query_one("#start-level", Select)
        valks_10_select = self.query_one("#valks-10", Select)
        valks_50_select = self.query_one("#valks-50", Select)
        valks_100_select = self.query_one("#valks-100", Select)

        # Get number of simulations
        num_sims = self._parse_input("num-simulations", 1000)
        if num_sims < 100:
            num_sims = 100  # Minimum 100 simulations

        # Collect market prices
        market_prices = MarketPrices(
            crystal_price=self._get_price("crystal"),
            restoration_bundle_price=self._get_price("restoration"),
            valks_10_price=self._get_price("valks_10"),
            valks_50_price=self._get_price("valks_50"),
            valks_100_price=self._get_price("valks_100"),
        )

        self.config = SimConfig(
            target_level=target_select.value,
            start_level=start_level_select.value,
            start_hepta=0,  # Not used for normal enhancement
            start_okta=0,
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
        start_level_select = self.query_one("#start-level", Select)
        start_hepta_select = self.query_one("#start-hepta", Select)
        start_okta_select = self.query_one("#start-okta", Select)
        valks_10_select = self.query_one("#valks-10", Select)
        valks_50_select = self.query_one("#valks-50", Select)
        valks_100_select = self.query_one("#valks-100", Select)

        # Get number of simulations
        num_sims = self._parse_input("num-simulations", 1000)
        if num_sims < 100:
            num_sims = 100  # Minimum 100 simulations

        # Collect market prices
        market_prices = MarketPrices(
            crystal_price=self._get_price("crystal"),
            restoration_bundle_price=self._get_price("restoration"),
            valks_10_price=self._get_price("valks_10"),
            valks_50_price=self._get_price("valks_50"),
            valks_100_price=self._get_price("valks_100"),
        )

        self.config = SimConfig(
            target_level=target_select.value,
            start_level=start_level_select.value,
            start_hepta=start_hepta_select.value,
            start_okta=start_okta_select.value,
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
        Binding("space", "toggle_pause", "Pause/Resume"),
        Binding("escape", "back", "Back to Config"),
    ]

    def __init__(self, config: SimConfig):
        super().__init__()
        self.config = config
        self.simulator = AwakeningSimulator()
        # Initialize gear state from config starting values
        self.gear = GearState(awakening_level=config.start_level)
        self.running = False
        self.paused = False
        self.attempt_count = 0
        self.target_attempts = 0  # Attempts on current target level only
        self.max_level_reached = config.start_level  # Track highest level achieved
        # Resource tracking
        self.total_crystals = 0
        self.total_scrolls = 0
        self.total_valks_10 = 0
        self.total_valks_50 = 0
        self.total_valks_100 = 0
        self.total_silver = 0
        # Hepta/Okta tracking
        self.total_exquisite_crystals = 0  # Exquisite Black Crystals used
        self.hepta_sub_progress = config.start_hepta  # Starting Hepta progress (0-4)
        self.okta_sub_progress = config.start_okta    # Starting Okta progress (0-9)
        self.hepta_sub_pity = 0      # Current pity for active Hepta sub-enhancement
        self.okta_sub_pity = 0       # Current pity for active Okta sub-enhancement
        # Snapshot of anvil energy for display after reaching target
        self.final_anvil_snapshot: dict[int, int] | None = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="level-caption"):
            yield Static(f"Target: +{ROMAN_NUMERALS[self.config.target_level]}", id="target-display", classes="caption-field")
            yield Static(f"Current: +{ROMAN_NUMERALS[self.config.start_level]}", id="current-display", classes="caption-field")
            yield Static(f"Max: +{ROMAN_NUMERALS[self.config.start_level]}", id="max-display", classes="caption-field")
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
                    with Horizontal(classes="stat-row"):
                        yield Static("Time Spent:", classes="stat-label")
                        yield Static("0m 0s", id="stat-time", classes="stat-value")

        with Horizontal(id="controls"):
            yield Button("Back", id="back-button", variant="default")
            yield Button("Pause", id="pause-button", variant="primary")
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
                # Wait while paused
                while self.paused and self.running:
                    await asyncio.sleep(0.05)
                if not self.running:
                    break
                # Check if we should use Hepta/Okta paths
                if self._should_use_hepta():
                    result = self._perform_hepta_okta_attempt(is_okta=False)
                    await self._flash_attempt(result["success"], result["anvil_triggered"])
                    self._log_hepta_okta_attempt(log, result, is_okta=False)
                    self._update_stats()
                    if self._check_hepta_okta_complete():
                        self._log_hepta_okta_complete(log, {"from": 7, "to": 8, "path": "Hepta"})
                        self._update_stats()
                elif self._should_use_okta():
                    result = self._perform_hepta_okta_attempt(is_okta=True)
                    await self._flash_attempt(result["success"], result["anvil_triggered"])
                    self._log_hepta_okta_attempt(log, result, is_okta=True)
                    self._update_stats()
                    if self._check_hepta_okta_complete():
                        self._log_hepta_okta_complete(log, {"from": 8, "to": 9, "path": "Okta"})
                        self._update_stats()
                else:
                    result = self._perform_enhancement()
                    await self._flash_attempt(result.success, result.anvil_triggered)
                    self._log_attempt(log, result)
                    self._update_stats()

                # Use minimum 0.0001s delay for "fast" mode (10x faster)
                delay = max(0.0001, self.config.speed)
                await asyncio.sleep(delay)

            if self.running:
                await self._victory_celebration(log)
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
        """Check if we should use Hepta path for VII→VIII.

        Use Hepta if:
        - Hepta is enabled, OR there's existing Hepta progress to complete
        - Currently at level VII
        - Hepta not yet complete
        """
        return ((self.config.use_hepta or self.hepta_sub_progress > 0) and
                self.gear.awakening_level == 7 and
                self.hepta_sub_progress < HEPTA_SUB_ENHANCEMENTS)

    def _should_use_okta(self) -> bool:
        """Check if we should use Okta path for VIII→IX.

        Use Okta if:
        - Okta is enabled, OR there's existing Okta progress to complete
        - Currently at level VIII
        - Okta not yet complete
        """
        return ((self.config.use_okta or self.okta_sub_progress > 0) and
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
        # Only count attempts for final target (Hepta=VIII, Okta=IX)
        target_for_path = 8 if not is_okta else 9
        if target_for_path == self.config.target_level:
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

        # Roll for success
        # Hepta/Okta sub-enhancement has fixed 6% success rate
        base_rate = 0.06  # 6% per sub-enhancement attempt

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
        if ((self.config.use_hepta or self.hepta_sub_progress > 0) and
            self.gear.awakening_level == 7 and
            self.hepta_sub_progress >= HEPTA_SUB_ENHANCEMENTS):
            # Hepta complete - level up to VIII
            self.gear.awakening_level = 8
            self.gear.reset_energy(8)
            self.hepta_sub_progress = 0
            self.hepta_sub_pity = 0
            return True

        if ((self.config.use_okta or self.okta_sub_progress > 0) and
            self.gear.awakening_level == 8 and
            self.okta_sub_progress >= OKTA_SUB_ENHANCEMENTS):
            # Okta complete - level up to IX
            self.gear.awakening_level = 9
            self.gear.reset_energy(9)
            self.okta_sub_progress = 0
            self.okta_sub_pity = 0
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
        # Only count attempts for final target level
        if target_level == self.config.target_level:
            self.target_attempts += 1
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
            # Save anvil snapshot before reaching final target
            if target_level == self.config.target_level:
                self.final_anvil_snapshot = dict(self.gear.anvil_energy)
            self.gear.awakening_level = target_level
            self.gear.reset_energy(target_level)
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
            # Save anvil snapshot before reaching final target
            if target_level == self.config.target_level:
                self.final_anvil_snapshot = dict(self.gear.anvil_energy)
            self.gear.awakening_level = target_level
            self.gear.reset_energy(target_level)
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
        # Use snapshot if target was reached, otherwise use live values
        energy_source = self.final_anvil_snapshot if self.final_anvil_snapshot else self.gear.anvil_energy
        for level in range(5, 11):
            current_energy = energy_source.get(level, 0)
            cap = ANVIL_THRESHOLDS_AWAKENING.get(level, 0)
            self.query_one(f"#anvil-{level}", Static).update(f"{current_energy}/{cap}")

    def _format_silver(self, silver: int) -> str:
        """Format silver amount with K/M/B/T suffix."""
        return format_silver(silver)

    def _format_time(self, seconds: int) -> str:
        """Format seconds into human-readable time (hours/minutes/seconds)."""
        return format_time(seconds)

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

    def _is_regular_mode(self) -> bool:
        """Check if running in Regular (in-game speed) mode."""
        return self.config.speed >= 1.0

    async def _flash_effect(self, color: str, duration: float = 0.15) -> None:
        """Apply a flash effect by changing log container border color."""
        log_container = self.query_one("#log-container", RichLog)
        original_border = log_container.styles.border
        log_container.styles.border = ("heavy", color)
        self.refresh()
        await asyncio.sleep(duration)
        log_container.styles.border = original_border
        self.refresh()

    async def _flash_attempt(self, success: bool, anvil: bool = False) -> None:
        """Flash screen based on attempt result (only in Regular mode)."""
        if not self._is_regular_mode():
            return

        if anvil:
            await self._flash_effect("yellow", 0.25)
        elif success:
            await self._flash_effect("green", 0.2)
        else:
            await self._flash_effect("red", 0.12)

    async def _victory_celebration(self, log: RichLog) -> None:
        """Epic victory celebration animation (only in Regular mode)."""
        if not self._is_regular_mode():
            return

        target = ROMAN_NUMERALS[self.config.target_level]
        log_container = self.query_one("#log-container", RichLog)
        caption = self.query_one("#level-caption", Horizontal)

        # Rapid flash sequence - the "flashbang"
        for _ in range(4):
            log_container.styles.border = ("heavy", "white")
            caption.styles.background = "white"
            self.refresh()
            await asyncio.sleep(0.06)
            log_container.styles.border = ("heavy", "gold")
            caption.styles.background = "darkgoldenrod"
            self.refresh()
            await asyncio.sleep(0.08)

        # Hold victory glow with golden theme
        log_container.styles.border = ("double", "gold")
        caption.styles.background = "darkgoldenrod"
        self.refresh()

        # ASCII art celebration
        log.write("")
        log.write("[bold yellow]★ ═══════════════════════════════════════════ ★[/bold yellow]")
        log.write("[bold yellow]║                                               ║[/bold yellow]")
        await asyncio.sleep(0.15)
        log.write(f"[bold yellow]║      ✦  ✦  ✦   +{target} ACHIEVED!   ✦  ✦  ✦      ║[/bold yellow]")
        await asyncio.sleep(0.15)
        log.write("[bold yellow]║                                               ║[/bold yellow]")
        log.write("[bold yellow]★ ═══════════════════════════════════════════ ★[/bold yellow]")
        log.write("")

        # Keep the golden glow for the stats display
        await asyncio.sleep(1.5)

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
        # Time spent: 1 second per enhancement attempt
        self.query_one("#stat-time", Static).update(self._format_time(self.attempt_count))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-button":
            self.action_back()
        elif event.button.id == "pause-button":
            self.action_toggle_pause()
        elif event.button.id == "restart-button":
            self.action_restart()

    def action_toggle_pause(self) -> None:
        """Toggle pause state."""
        self.paused = not self.paused
        pause_btn = self.query_one("#pause-button", Button)
        if self.paused:
            pause_btn.label = "Resume"
            pause_btn.variant = "success"
        else:
            pause_btn.label = "Pause"
            pause_btn.variant = "primary"

    def action_back(self) -> None:
        """Go back to config screen."""
        self.running = False
        self.app.pop_screen()

    def action_restart(self) -> None:
        """Restart the simulation."""
        self.running = False
        self.paused = False
        # Reset pause button
        pause_btn = self.query_one("#pause-button", Button)
        pause_btn.label = "Pause"
        pause_btn.variant = "primary"
        # Reset state to starting values from config
        self.gear = GearState(awakening_level=self.config.start_level)
        self.attempt_count = 0
        self.target_attempts = 0
        self.max_level_reached = self.config.start_level
        # Resource tracking
        self.total_crystals = 0
        self.total_scrolls = 0
        self.total_valks_10 = 0
        self.total_valks_50 = 0
        self.total_valks_100 = 0
        self.total_silver = 0
        # Hepta/Okta tracking
        self.total_exquisite_crystals = 0
        self.hepta_sub_progress = self.config.start_hepta
        self.okta_sub_progress = self.config.start_okta
        self.hepta_sub_pity = 0
        self.okta_sub_pity = 0
        # Reset anvil snapshot
        self.final_anvil_snapshot = None

        # Clear log
        log = self.query_one("#log-container", RichLog)
        log.clear()

        # Update displays
        self._update_stats()
        self.query_one("#current-display", Static).update(f"Current: +{ROMAN_NUMERALS[self.config.start_level]}")
        self.query_one("#max-display", Static).update(f"Max: +{ROMAN_NUMERALS[self.config.start_level]}")
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
        self._task: asyncio.Task | None = None

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
        self._task = asyncio.create_task(self._run_analysis())

    async def on_unmount(self) -> None:
        """Cancel task when screen is unmounted."""
        await self._cancel_task()

    async def _cancel_task(self) -> None:
        """Cancel the running analysis task and clean up."""
        self.running = False
        if self._task is not None:
            if not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self._task = None

    async def _run_analysis(self) -> None:
        """Run Monte Carlo analysis for different Hepta/Okta strategies."""
        try:
            log = self.query_one("#results-container", RichLog)
            status = self.query_one("#status", Static)

            log.write("[bold]Monte Carlo Hepta/Okta Strategy Analysis[/bold]")
            start_info = f"Start: +{ROMAN_NUMERALS[self.config.start_level]}"
            if self.config.start_hepta > 0:
                start_info += f" (Hepta {self.config.start_hepta}/5)"
            if self.config.start_okta > 0:
                start_info += f" (Okta {self.config.start_okta}/10)"
            log.write(f"{start_info} → Target: +{ROMAN_NUMERALS[self.config.target_level]}, Simulations: {self.num_simulations}")
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

            # Pre-create engine prices once (avoid repeated object creation)
            prices = self.config.market_prices
            engine_prices = MarketPrices(
                crystal_price=prices.crystal_price,
                restoration_bundle_price=prices.restoration_bundle_price,
                valks_10_price=prices.valks_10_price,
                valks_50_price=prices.valks_50_price,
                valks_100_price=prices.valks_100_price,
            )

            # Run simulations for each strategy
            # Yield every 5 simulations for responsive UI
            batch_size = 5
            num_sims = self.num_simulations  # Local var for speed
            silver_key = itemgetter(2)  # Pre-create sort key

            for use_hepta, use_okta, label in strategies:
                if not self.running:
                    break

                status.update(f"Status: Testing {label}...")
                strategy_key = (use_hepta, use_okta)

                # Create config once per strategy
                engine_config = EngineConfig(
                    start_level=self.config.start_level,
                    target_level=self.config.target_level,
                    restoration_from=6,  # Fixed at +VI
                    use_hepta=use_hepta,
                    use_okta=use_okta,
                    start_hepta=self.config.start_hepta,
                    start_okta=self.config.start_okta,
                    valks_10_from=self.config.valks_10_from,
                    valks_50_from=self.config.valks_50_from,
                    valks_100_from=self.config.valks_100_from,
                    prices=engine_prices,
                )

                # Create engine once per strategy, reuse with reset()
                engine = EnhancementEngine(engine_config)
                sim_results = []  # List of (crystals, scrolls, silver, exquisite)

                for i in range(num_sims):
                    if not self.running:
                        break
                    # Use fast path - returns tuple directly, no dataclass overhead
                    result = engine.run_fast()
                    sim_results.append(result)
                    engine.reset()  # Reset for next simulation

                    # Update progress periodically (just status, not full table)
                    if (i + 1) % batch_size == 0:
                        progress = int((i + 1) / num_sims * 100)
                        status.update(f"Status: Testing {label}... {progress}%")
                        await asyncio.sleep(0)  # Yield to event loop

                if not self.running:
                    break

                # Sort only once at the end of each strategy
                if sim_results:
                    sorted_by_silver = sorted(sim_results, key=silver_key)
                    p50_idx = len(sorted_by_silver) // 2
                    p90_idx = int(len(sorted_by_silver) * 0.9)

                    results[strategy_key] = {
                        "p50": sorted_by_silver[p50_idx],
                        "p90": sorted_by_silver[p90_idx],
                        "worst": sorted_by_silver[-1],
                        "label": label,
                        "progress": 100,
                    }

                    # Redraw table after completing each strategy
                    await self._redraw_table(log, results, strategies)
                    await asyncio.sleep(0)

            # Final redraw with best highlighted
            if results and self.running:
                await self._redraw_table(log, results, strategies, final=True)

            status.update("Status: Complete!")
        except asyncio.CancelledError:
            # Task was cancelled - clean exit
            pass
        finally:
            self.running = False

    async def _redraw_table(self, log: RichLog, results: dict, strategies: list, final: bool = False) -> None:
        """Redraw the results table."""
        log.clear()
        log.write("[bold]Monte Carlo Hepta/Okta Strategy Analysis[/bold]")
        start_info = f"Start: +{ROMAN_NUMERALS[self.config.start_level]}"
        if self.config.start_hepta > 0:
            start_info += f" (Hepta {self.config.start_hepta}/5)"
        if self.config.start_okta > 0:
            start_info += f" (Okta {self.config.start_okta}/10)"
        log.write(f"{start_info} → Target: +{ROMAN_NUMERALS[self.config.target_level]}, Simulations: {self.num_simulations}")
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

    def _format_silver(self, silver: int) -> str:
        """Format silver amount with K/M/B/T suffix."""
        return format_silver(silver)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-button":
            await self.action_back()

    async def action_back(self) -> None:
        await self._cancel_task()
        self.app.pop_screen()

    async def action_quit(self) -> None:
        await self._cancel_task()
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
        self._task: asyncio.Task | None = None

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
        self._task = asyncio.create_task(self._run_analysis())

    async def on_unmount(self) -> None:
        """Cancel task when screen is unmounted."""
        await self._cancel_task()

    async def _cancel_task(self) -> None:
        """Cancel the running analysis task and clean up."""
        self.running = False
        if self._task is not None:
            if not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self._task = None

    async def _run_analysis(self) -> None:
        """Run Monte Carlo analysis for different restoration strategies."""
        try:
            log = self.query_one("#results-container", RichLog)
            status = self.query_one("#status", Static)

            log.write("[bold]Monte Carlo Restoration Strategy Analysis[/bold]")
            log.write(f"Start: +{ROMAN_NUMERALS[self.config.start_level]} → Target: +{ROMAN_NUMERALS[self.config.target_level]}, Simulations: {self.num_simulations}\n")

            # Test restoration starting from IV(4), V(5), VI(6), VII(7), VIII(8) up to target-1
            restoration_options = [i for i in range(4, self.config.target_level)]
            results = {}

            await self._redraw_table(log, results, restoration_options)
            await asyncio.sleep(0.01)

            # Pre-create engine prices once (avoid repeated object creation)
            prices = self.config.market_prices
            engine_prices = MarketPrices(
                crystal_price=prices.crystal_price,
                restoration_bundle_price=prices.restoration_bundle_price,
                valks_10_price=prices.valks_10_price,
                valks_50_price=prices.valks_50_price,
                valks_100_price=prices.valks_100_price,
            )

            # Run simulations for each strategy
            # Yield every 5 simulations for responsive UI
            batch_size = 5
            num_sims = self.num_simulations  # Local var for speed
            silver_key = itemgetter(2)  # Pre-create sort key

            for rest_from in restoration_options:
                if not self.running:
                    break

                rest_label = f"+{ROMAN_NUMERALS[rest_from]}"
                status.update(f"Status: Testing restoration from {rest_label}...")

                # Create config once per strategy
                engine_config = EngineConfig(
                    start_level=self.config.start_level,
                    target_level=self.config.target_level,
                    restoration_from=rest_from,
                    use_hepta=False,
                    use_okta=False,
                    start_hepta=self.config.start_hepta,
                    start_okta=self.config.start_okta,
                    valks_10_from=self.config.valks_10_from,
                    valks_50_from=self.config.valks_50_from,
                    valks_100_from=self.config.valks_100_from,
                    prices=engine_prices,
                )

                # Create engine once per strategy, reuse with reset()
                engine = EnhancementEngine(engine_config)
                sim_results = []  # List of (crystals, scrolls, silver)

                for i in range(num_sims):
                    if not self.running:
                        break
                    # Use fast path - returns tuple directly, no dataclass overhead
                    result = engine.run_fast()
                    # Only take first 3 elements (crystals, scrolls, silver) for this screen
                    sim_results.append((result[0], result[1], result[2]))
                    engine.reset()  # Reset for next simulation

                    # Update progress periodically (just status, not full table)
                    if (i + 1) % batch_size == 0:
                        progress = int((i + 1) / num_sims * 100)
                        status.update(f"Status: Testing restoration from {rest_label}... {progress}%")
                        await asyncio.sleep(0)  # Yield to event loop

                if not self.running:
                    break

                # Skip processing if cancelled mid-simulation
                if not sim_results:
                    continue

                # Sort only once at the end of each strategy
                sorted_by_silver = sorted(sim_results, key=silver_key)
                p50_idx = len(sorted_by_silver) // 2
                p90_idx = int(len(sorted_by_silver) * 0.9)

                results[rest_from] = {
                    "p50": sorted_by_silver[p50_idx],
                    "p90": sorted_by_silver[p90_idx],
                    "worst": sorted_by_silver[-1],
                    "label": rest_label,
                    "progress": 100,
                }

                # Redraw table after completing each strategy
                await self._redraw_table(log, results, restoration_options)
                await asyncio.sleep(0)

            # Final redraw with best highlighted
            if results and self.running:
                await self._redraw_table(log, results, restoration_options, final=True)

            status.update("Status: Complete!")
        except asyncio.CancelledError:
            # Task was cancelled - clean exit
            pass
        finally:
            self.running = False

    async def _redraw_table(self, log: RichLog, results: dict, restoration_options: list, final: bool = False) -> None:
        """Redraw the results table."""
        log.clear()
        log.write("[bold]Monte Carlo Restoration Strategy Analysis[/bold]")
        log.write(f"Start: +{ROMAN_NUMERALS[self.config.start_level]} → Target: +{ROMAN_NUMERALS[self.config.target_level]}, Simulations: {self.num_simulations}\n")

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

    def _format_silver(self, silver: int) -> str:
        """Format silver amount with K/M/B/T suffix."""
        return format_silver(silver)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-button":
            await self.action_back()

    async def action_back(self) -> None:
        await self._cancel_task()
        self.app.pop_screen()

    async def action_quit(self) -> None:
        await self._cancel_task()
        self.app.exit()


class BDMEnhancementApp(App):
    """Main TUI application."""

    TITLE = "BDM Enhancement Simulator"
    ALLOW_SELECT = True
    theme = "monokai"
    CSS = """
    Screen {
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self):
        super().__init__()
        # Shared market prices state
        self.market_prices = {
            "crystal": 34650000,
            "restoration": 1000000000000,
            "valks_10": 0,
            "valks_50": 0,
            "valks_100": 0,
        }

    def on_mount(self) -> None:
        self.push_screen(ModuleSelectScreen())

    def on_click(self, event: Click) -> None:
        """Handle right-click to copy selected text to clipboard."""
        if event.button == 3:  # Right mouse button
            selected_text = self.screen.get_selected_text()
            if selected_text:
                self.copy_to_clipboard(selected_text)
                self.notify("Copied to clipboard", timeout=1)


def main():
    """Entry point for the TUI."""
    app = BDMEnhancementApp()
    app.run()


if __name__ == "__main__":
    main()
