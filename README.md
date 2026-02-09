# Quiescence Analysis

A self-contained analysis toolkit for backtesting and trading results from the Quiescence trading system. This repository is independent of the main strategy codebase.

## Quick Start

### 1. Setup Environment

```bash
# Install just command runner (if not already installed)
# On Linux: cargo install just
# On macOS: brew install just

# Setup Python environment with all dependencies
just setup

# Activate the virtual environment
source .venv/bin/activate
```

### 2. Setup Pre-commit Hooks

Pre-commit hooks automatically strip notebook outputs before commits to keep the repository clean:

```bash
# Install pre-commit hooks
pre-commit install

# (Optional) Run on all files manually
pre-commit run --all-files
```

### 3. Verify Installation

```bash
# Check environment setup
just env-info

# Test utilities import
just check-config
```

## Available Commands

- `just setup` - Create venv and install all dependencies
- `just update-deps` - Update all dependencies
- `just env-info` - Display Python environment information
- `just check-config` - Validate the utilities module
- `just clean` - Remove Python cache files
- `just clean-venv` - Remove virtual environment

## About This Toolkit

This repository contains a self-contained analysis toolkit for backtesting results. It is designed to be independent of the strategy modeling codebase.

## Structure

```
analysis/
├── README.md                 # This file
├── utilities.py             # Core utilities (scanning, loading, time conversion)
└── backtests/               # Analysis notebooks for backtest data
    ├── pnl_curves.ipynb              # P&L curve visualizations
    ├── time_of_day_returns.ipynb     # Time-of-day performance analysis
    ├── detailed_run_analysis.ipynb   # Comprehensive tabular statistics
    └── pnl_vs_duration.ipynb         # Duration vs profitability correlation
```

## Features

### Core Utilities (`utilities.py`)

**Data Loading Functions:**
- **`scan_backtest_runs()`**: Fast metadata scanning without loading full datasets
- **`load_run_data()`**: Selective loading of full backtest data (JSONL + CSV reports)
- **`create_runs_summary_dataframe()`**: Create filterable summary tables
- **`display_runs_summary()`**: Pretty-print run summaries

**Time Conversion Functions:**
- **`convert_utc_to_ny()`**: Convert UTC timestamps to NY local time
- **`convert_ny_to_utc()`**: Convert NY local time to UTC
- **`weekdays_between()`**: Generate weekday dates between two dates

### Analysis Notebooks

#### 1. **P&L Curves** (`pnl_curves.ipynb`)
- Overlay multiple P&L curves for visual comparison
- Interactive Plotly charts with hover tooltips
- Quick identification of best-performing parameter combinations
- Summary statistics table

#### 2. **Time of Day Returns** (`time_of_day_returns.ipynb`)
- Bucket trades by time of day
- Box plots showing return distributions
- Identify optimal/suboptimal trading hours
- Configurable time intervals (15min, 30min, etc.)

#### 3. **Detailed Run Analysis** (`detailed_run_analysis.ipynb`)
- Trade statistics (win rate, profit factor, avg win/loss)
- Position holding duration analysis
- Drawdown metrics and recovery times
- Combined summary report with top performers
- No heavy visualizations - optimized for quick statistics

#### 4. **P&L vs Duration** (`pnl_vs_duration.ipynb`)
- Scatter plots of trade P&L vs holding duration
- Correlation coefficients with interpretations
- Duration distribution analysis
- Profitability by duration buckets
- Actionable recommendations based on patterns

## Workflow

All notebooks follow a consistent workflow:

1. **Configuration**: Set stock symbol and data paths
2. **Scan**: Fast metadata-only scan of all runs
3. **Filter**: Use summary DataFrame to select runs of interest
4. **Load**: Selectively load full data for chosen runs
5. **Analyze**: Execute analysis-specific computations and visualizations

## Usage Example

```python
from pathlib import Path
from utilities import scan_backtest_runs, create_runs_summary_dataframe, load_run_data

# 1. Configure paths
BACKTEST_ROOT = Path("/data/quiescence/backtest")
stock_symbol = "MSFT"

# 2. Scan all runs (fast - metadata only)
runs_metadata = scan_backtest_runs(BACKTEST_ROOT, stock_symbol)

# 3. Create filterable summary
df_summary = create_runs_summary_dataframe(runs_metadata)
print(df_summary)

# 4. Filter runs (example: select specific frequencies)
filtered = df_summary[df_summary['Frequency'] == '1-MINUTE']
selected_indices = filtered['Run'].values - 1

# 5. Load selected runs
runs_data = [load_run_data(runs_metadata[i]) for i in selected_indices]

# 6. Now analyze with runs_data...
```

## Data Requirements

The toolkit expects backtest data in the following structure:

```
/data/quiescence/backtest/
└── {TICKER}/
    └── {DATE}/
        └── {TIME_RUNID}/
            ├── run_parameters.json
            ├── strategy_data.jsonl
            ├── orders.csv
            ├── positions.csv
            ├── fills.csv
            └── pnl_summary.json (optional)
```

## Dependencies

All dependencies are managed in [pyproject.toml](pyproject.toml) and installed with `just setup`:

- **Core**: Python 3.12, pandas, numpy, scipy, scikit-learn
- **Trading**: nautilus-trader (with IB and Docker support), polygon-api-client
- **Analysis**: jupyter, notebook, ipykernel, plotly, matplotlib
- **Development**: pytest, black, pre-commit, nbstripout
- **Utilities**: pyyaml, python-dotenv, watchdog

## Development Workflow

1. **Make changes** to notebooks or Python files
2. **Pre-commit hooks automatically**:
   - Strip notebook outputs (prevents large files in git)
   - Remove trailing whitespace
   - Ensure files end with newline
   - Validate YAML syntax
   - Check for large files
3. **Commit and push** as normal

## Making This Standalone

This repository is already standalone! It includes:

✓ Complete Python environment configuration ([pyproject.toml](pyproject.toml))
✓ Convenient task runners ([justfile](justfile))
✓ Git hooks for notebook management ([.pre-commit-config.yaml](.pre-commit-config.yaml))
✓ All required utilities in the analysis folder

To use elsewhere:
1. Clone this repository
2. Run `just setup`
3. Update data paths in notebooks to point to your backtest storage location

## Notes

- **Two-Phase Approach**: Scan first (fast), then load selectively (memory-efficient)
- **Memory Optimization**: Each notebook loads only what it needs for its specific analysis
- **Flexible Filtering**: Use pandas DataFrame operations to filter runs by any parameter
- **Self-Contained**: All required utilities are included in this folder

## Future Enhancements

Potential additions:

- Live trading run analysis (similar structure to backtests)
- Parameter optimization heatmaps
- Monte Carlo simulations
- Risk metrics (Sharpe ratio, Sortino ratio, etc.)
- Multi-ticker comparative analysis
