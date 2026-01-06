"""Module selection screen for choosing enhancement type."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static, Rule

from src.core import ItemTypeRegistry, ItemTypeInfo
from .market_prices import MarketPricesScreen


class ModuleButton(Button):
    """Button representing a selectable module."""

    def __init__(self, module_info: ItemTypeInfo, index: int):
        self.module_info = module_info
        status_text = "Ready" if module_info.implemented else "Coming Soon"
        label = f"[{index}] {module_info.name}  [{status_text}]"
        super().__init__(label, id=f"module-btn-{module_info.id}")
        self.disabled = not module_info.implemented


class ModuleSelectScreen(Screen):
    """Starting screen for selecting which enhancement type to simulate.

    Displays all registered item type modules, showing which ones
    are implemented and available for use.
    """

    CSS = """
    ModuleSelectScreen {
        layout: vertical;
    }

    #module-list-container {
        height: 1fr;
        padding: 1 2;
    }

    #module-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    ModuleButton {
        width: 100%;
        margin: 1 0;
    }

    .module-description {
        color: $text-muted;
        margin-left: 4;
        margin-bottom: 1;
    }

    #market-prices-button {
        margin-top: 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "select_1", "Select 1", show=False),
        Binding("2", "select_2", "Select 2", show=False),
        Binding("3", "select_3", "Select 3", show=False),
        Binding("4", "select_4", "Select 4", show=False),
        Binding("5", "select_5", "Select 5", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.modules = ItemTypeRegistry.get_all_info()

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="module-list-container"):
            yield Static("Select Enhancement Type:", id="module-title")

            for i, module_info in enumerate(self.modules, 1):
                yield ModuleButton(module_info, i)
                yield Static(module_info.description, classes="module-description")

            yield Rule()
            yield Button("Market Prices", id="market-prices-button", variant="default")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if isinstance(event.button, ModuleButton):
            self._select_module(event.button.module_info)
        elif event.button.id == "market-prices-button":
            self.app.push_screen(MarketPricesScreen())

    def _select_module(self, module_info: ItemTypeInfo) -> None:
        """Handle selection of a module."""
        if module_info.implemented:
            # Get the module class and its config screen
            module_class = ItemTypeRegistry.get(module_info.id)
            if module_class:
                config_screen_class = module_class.get_config_screen_class()
                self.app.push_screen(config_screen_class())
        else:
            self.notify(
                f"{module_info.name} is not yet implemented",
                title="Coming Soon",
                severity="warning",
            )

    def _select_by_index(self, index: int) -> None:
        """Select a module by its index (1-based)."""
        if 0 < index <= len(self.modules):
            self._select_module(self.modules[index - 1])

    def action_select_1(self) -> None:
        self._select_by_index(1)

    def action_select_2(self) -> None:
        self._select_by_index(2)

    def action_select_3(self) -> None:
        self._select_by_index(3)

    def action_select_4(self) -> None:
        self._select_by_index(4)

    def action_select_5(self) -> None:
        self._select_by_index(5)

    def action_quit(self) -> None:
        self.app.exit()
