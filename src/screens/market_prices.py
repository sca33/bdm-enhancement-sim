"""Market prices configuration screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static, Rule


class MarketPricesScreen(Screen):
    """Screen for configuring market prices used in cost calculations."""

    CSS = """
    MarketPricesScreen {
        layout: vertical;
    }

    #prices-container {
        padding: 1 2;
        height: auto;
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

    .config-row {
        height: 3;
        margin-bottom: 1;
    }

    .config-label {
        width: 30;
        content-align: left middle;
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

    #save-button {
        margin-top: 2;
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "save", "Save"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with ScrollableContainer(id="prices-container"):
            yield Static("Market Prices Configuration", id="title")
            yield Rule()

            yield Static("Material Prices", classes="section-title")
            yield Static("(Set to 0 if not applicable or unknown)")

            with Horizontal(classes="config-row"):
                yield Label("Pristine Black Crystal:", classes="config-label")
                yield Input(
                    value=str(self.app.market_prices.get("crystal", 34650000)),
                    placeholder="34650000",
                    id="price-crystal",
                    classes="config-input-small",
                    type="integer",
                )
                yield Static("silver", classes="price-unit")

            with Horizontal(classes="config-row"):
                yield Label("200K Restoration Scrolls:", classes="config-label")
                yield Input(
                    value=str(self.app.market_prices.get("restoration", 1000000000000)),
                    placeholder="1T",
                    id="price-restoration",
                    classes="config-input",
                    type="integer",
                )
                yield Static("silver", classes="price-unit")

            yield Rule()

            yield Static("Advice of Valks Prices", classes="section-title")

            with Horizontal(classes="config-row"):
                yield Label("Valks +10% price:", classes="config-label")
                yield Input(
                    value=str(self.app.market_prices.get("valks_10", 0)),
                    placeholder="0",
                    id="price-valks-10",
                    classes="config-input-small",
                    type="integer",
                )
                yield Static("silver", classes="price-unit")

            with Horizontal(classes="config-row"):
                yield Label("Valks +50% price:", classes="config-label")
                yield Input(
                    value=str(self.app.market_prices.get("valks_50", 0)),
                    placeholder="0",
                    id="price-valks-50",
                    classes="config-input-small",
                    type="integer",
                )
                yield Static("silver", classes="price-unit")

            with Horizontal(classes="config-row"):
                yield Label("Valks +100% price:", classes="config-label")
                yield Input(
                    value=str(self.app.market_prices.get("valks_100", 0)),
                    placeholder="0",
                    id="price-valks-100",
                    classes="config-input-small",
                    type="integer",
                )
                yield Static("silver", classes="price-unit")

            yield Rule()

            yield Button("Save & Return", id="save-button", variant="success")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "save-button":
            self._save_prices()

    def action_save(self) -> None:
        """Save prices and return."""
        self._save_prices()

    def action_back(self) -> None:
        """Return without saving."""
        self.app.pop_screen()

    def _save_prices(self) -> None:
        """Save prices to app state and return."""
        try:
            self.app.market_prices["crystal"] = int(self.query_one("#price-crystal", Input).value or 0)
            self.app.market_prices["restoration"] = int(self.query_one("#price-restoration", Input).value or 0)
            self.app.market_prices["valks_10"] = int(self.query_one("#price-valks-10", Input).value or 0)
            self.app.market_prices["valks_50"] = int(self.query_one("#price-valks-50", Input).value or 0)
            self.app.market_prices["valks_100"] = int(self.query_one("#price-valks-100", Input).value or 0)
            self.notify("Prices saved", timeout=1)
            self.app.pop_screen()
        except ValueError:
            self.notify("Invalid price value", severity="error")
