# BDM Enhancement Simulator

A TUI (Terminal User Interface) simulator for Black Desert Mobile awakening enhancement system with Monte Carlo strategy analysis.

## Features

- **Enhancement Simulation**: Simulate awakening enhancements from 0 to +X with realistic success rates
- **Anvil Pity System**: Tracks the Ancient Anvil (고대의 모루) pity counter for guaranteed success
- **Restoration Scrolls**: Configurable restoration scroll usage with 50% success rate
- **Advice of Valks**: Support for +10%, +50%, +100% Valks with multiplicative bonuses
- **Monte Carlo Strategy Analysis**: Find the optimal restoration starting level to minimize silver costs
- **Resource Tracking**: Track crystals, scrolls, and silver spent

## Enhancement Rates

| Level | Success Rate | Anvil Pity |
|-------|-------------|------------|
| I     | 70%         | -          |
| II    | 60%         | -          |
| III   | 40%         | 2          |
| IV    | 20%         | 3          |
| V     | 10%         | 5          |
| VI    | 7%          | 8          |
| VII   | 5%          | 10         |
| VIII  | 3%          | 17         |
| IX    | 1%          | 50         |
| X     | 0.5%        | 100        |

## Installation

```bash
# Clone the repository
git clone https://github.com/sca33/bdm-enhancement-sim.git
cd bdm-enhancement-sim

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Usage

```bash
# Run the TUI
python -m src.tui
```

### Controls

- **Start Simulation**: Run a single enhancement simulation to target level
- **Calculate Winning Strategy**: Run Monte Carlo analysis to find optimal restoration level
- **Fast/Instant**: Toggle between animated and instant calculation modes
- **R**: Restart simulation
- **Q**: Quit

## Configuration

On the config screen, you can set:

- **Target Level**: Enhancement goal (I-X)
- **Valks Settings**: When to use +10%, +50%, +100% Valks
- **Restoration**: Starting level for using restoration scrolls
- **Market Prices**: Crystal and restoration scroll costs for silver calculation
- **Simulations**: Number of Monte Carlo runs for strategy analysis

## License

MIT License
