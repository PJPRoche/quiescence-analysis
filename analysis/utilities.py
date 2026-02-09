"""
Backtest Analysis Utilities

This module provides utilities for scanning, loading, and analyzing backtest data.
Includes time conversion functions for handling UTC <-> NY timezone conversions.
"""

import datetime
import io
import json
import pandas as pd
import pytz
from pathlib import Path
from typing import Optional


# ========================================
# TIME CONVERSION UTILITIES
# ========================================

def convert_ny_to_utc(ny_dt: datetime.datetime) -> datetime.datetime:
    """Converts New York local datetime to UTC datetime."""
    # Define the UTC and New York time zones
    utc_tz = pytz.utc
    ny_tz = pytz.timezone('America/New_York')

    # Localize the New York datetime to New York timezone
    ny_dt_localized = ny_tz.localize(ny_dt)

    # Convert to UTC
    utc_dt = ny_dt_localized.astimezone(utc_tz)

    return utc_dt


def convert_utc_to_ny(utc_dt: float) -> datetime.datetime:
    """Converts UTC datetime to New York local datetime.

    Args:
        utc_dt (float): UTC datetime as a timestamp (seconds since epoch).

    Returns:
        datetime.datetime: Local datetime in New York timezone.
    """

    # Localize the UTC datetime to UTC timezone
    utc_dt_localized = datetime.datetime.fromtimestamp(utc_dt, tz=pytz.utc)

    # Convert to New York time
    ny_dt = utc_dt_localized.astimezone(pytz.timezone('America/New_York'))

    return ny_dt


def weekdays_between(start_date: datetime.date, end_date: datetime.date):
    """
        Generates all weekdays between start_date and end_date (inclusive).
        Args:
            start_date (datetime.date): The start date.
            end_date (datetime.date): The end date.
        Yields:
            datetime.date: Each weekday date between start_date and end_date.
    """
    day = start_date
    while day <= end_date:
        if day.weekday() < 5:  # 0-4 denotes Monday to Friday
            yield day
        day += datetime.timedelta(days=1)


# ========================================
# PNL ANALYSIS UTILITIES
# ========================================

def build_cumulative_pnl_from_positions(positions_report: pd.DataFrame) -> pd.Series:
    """
    Build cumulative P&L series from positions_report.

    Args:
        positions_report: DataFrame with realized_pnl and ts_closed columns

    Returns:
        pandas.Series: Cumulative P&L indexed by exit timestamps
    """
    # Handle empty positions
    if 'realized_pnl' not in positions_report.columns or len(positions_report) == 0:
        return pd.Series(dtype=float)

    # Clean realized_pnl column - handle both string format ("65.62 USD") and numeric format
    if positions_report['realized_pnl'].dtype == 'object':
        # String format: "65.62 USD" -> 65.62
        realized_pnl_clean = positions_report['realized_pnl'].str.replace(' USD', '').astype(float)
    else:
        # Already numeric
        realized_pnl_clean = positions_report['realized_pnl']

    # Convert ts_closed from nanoseconds to datetime
    exit_datetimes = pd.to_datetime(positions_report['ts_closed'], unit='ns').apply(
        lambda x: convert_utc_to_ny(x.timestamp())
    )

    # Create series with exit times and P&L, then calculate cumulative sum
    pnl_series = pd.Series(realized_pnl_clean.values, index=exit_datetimes)
    cumulative_pnl = pnl_series.sort_index().cumsum()

    return cumulative_pnl


# ========================================
# BACKTEST DATA SCANNING & LOADING
# ========================================

def scan_backtest_runs(backtest_root: Path, ticker: Optional[str] = None):
	"""
	Scan backtest runs from the new folder structure and extract metadata.

	Args:
		backtest_root: Path to the backtest directory (e.g., /data/quiescence/backtest)
		ticker: Optional stock ticker to filter runs. If None, returns all runs.

	Returns:
		List of dictionaries containing run metadata
	"""
	runs_metadata = []

	# Navigate structure: backtest_root/{ticker}/{date}/{time_runid}/
	for ticker_dir in backtest_root.iterdir():
		if not ticker_dir.is_dir():
			continue

		# Filter by ticker if specified
		if ticker and ticker_dir.name != ticker:
			continue

		for date_dir in ticker_dir.iterdir():
			if not date_dir.is_dir():
				continue

			for run_dir in date_dir.iterdir():
				if not run_dir.is_dir():
					continue

				# Check if run_parameters.json exists
				params_file = run_dir / "run_parameters.json"
				if not params_file.exists():
					continue

				# Load run parameters
				try:
					with open(params_file, 'r') as f:
						params = json.load(f)
				except Exception as e:
					print(f"Error loading parameters from {params_file}: {e}")
					continue

				metadata = {
					"ticker": ticker_dir.name,
					"date": date_dir.name,
					"run_directory": run_dir.name,
					"run_path": run_dir,
					"strategy_data_file": run_dir / "strategy_data.jsonl",
					**params  # Include all parameters from run_parameters.json
				}

				# Load PnL summary if available
				pnl_file = run_dir / "pnl_summary.json"
				if pnl_file.exists():
					try:
						with open(pnl_file, 'r') as f:
							pnl_data = json.load(f)
							# Prefix metrics with 'metric_' for consistency
							for key, value in pnl_data.items():
								if isinstance(value, (int, float)):
									metadata[f"metric_{key.lower().replace(' ', '_').replace('(', '').replace(')', '')}"] = value
					except Exception as e:
						print(f"Error loading PnL summary from {pnl_file}: {e}")

				runs_metadata.append(metadata)

	return runs_metadata


def scan_live_runs(live_runs_root: Path, ticker: Optional[str] = None):
	"""
	Scan live trading runs from the new folder structure and extract metadata.

	Args:
		live_runs_root: Path to the live_runs directory (e.g., /data/quiescence/live_runs)
		ticker: Optional stock ticker to filter runs. If None, returns all runs.

	Returns:
		List of dictionaries containing run metadata
	"""
	runs_metadata = []

	# Navigate structure: live_runs_root/{ticker}/{date}/{time}/
	for ticker_dir in live_runs_root.iterdir():
		if not ticker_dir.is_dir():
			continue

		# Filter by ticker if specified
		if ticker and ticker_dir.name != ticker:
			continue

		for date_dir in ticker_dir.iterdir():
			if not date_dir.is_dir():
				continue

			for run_dir in date_dir.iterdir():
				if not run_dir.is_dir():
					continue

				# Check if run_parameters.json exists
				params_file = run_dir / "run_parameters.json"
				if not params_file.exists():
					continue

				# Load run parameters
				try:
					with open(params_file, 'r') as f:
						params = json.load(f)
				except Exception as e:
					print(f"Error loading parameters from {params_file}: {e}")
					continue

				metadata = {
					"ticker": ticker_dir.name,
					"date": date_dir.name,
					"run_directory": run_dir.name,
					"run_path": run_dir,
					"strategy_data_file": run_dir / "strategy_data.jsonl",
					**params  # Include all parameters from run_parameters.json
				}

				runs_metadata.append(metadata)

	return runs_metadata


def load_run_data(run_metadata: dict):
	"""
	Load the full data (JSONL and reports) for a specific run.

	Args:
		run_metadata: Dictionary from scan_backtest_runs() or scan_live_runs() containing run metadata

	Returns:
		Dictionary with the same metadata plus loaded data and reports
	"""
	run_data = run_metadata.copy()

	# Load strategy data JSONL
	try:
		strategy_file = run_metadata["strategy_data_file"]
		if strategy_file.exists():
			with open(strategy_file, 'r') as f:
				jsonl_content_string = f.read()
				df = pd.read_json(io.StringIO(jsonl_content_string), lines=True)
				run_data["data"] = df
		else:
			run_data["data"] = pd.DataFrame()
	except Exception as e:
		print(f"Error loading data from {run_metadata['strategy_data_file']}: {e}")
		run_data["data"] = pd.DataFrame()

	# Load CSV reports (orders, positions, fills)
	run_path = run_metadata["run_path"]

	for report_name in ["orders", "positions", "fills"]:
		report_path = run_path / f"{report_name}.csv"
		try:
			if report_path.exists():
				df_report = pd.read_csv(report_path)
				run_data[f"{report_name}_report"] = df_report
			else:
				run_data[f"{report_name}_report"] = pd.DataFrame()
		except Exception as e:
			print(f"Error loading {report_name} report from {report_path}: {e}")
			run_data[f"{report_name}_report"] = pd.DataFrame()

	return run_data


def create_runs_summary_dataframe(runs_metadata: list) -> pd.DataFrame:
	"""
	Create a summary DataFrame for easy comparison of runs using metadata only.
	This function extracts and formats key parameters from run metadata into a
	pandas DataFrame for filtering and comparison.

	Args:
		runs_metadata: List of run metadata from scan_backtest_runs() or scan_live_runs()

	Returns:
		pandas.DataFrame with formatted run summaries including:
			- Run number (1-indexed for user display)
			- Ticker symbol
			- Bar frequency (extracted from bar_type)
			- Date range (burn-in and backtest)
			- Trading hours (start and end times)
			- Key strategy parameters
			- Run filepath
	"""
	import re

	summary_data = []
	for i, run in enumerate(runs_metadata):
		# Extract frequency from bar_type (e.g., "MSFT.POLYGON-1-MINUTE-LAST-EXTERNAL" -> "1-MINUTE")
		bar_type = run.get('bar_type', '')
		if bar_type:
			parts = bar_type.split('-')
			frequency = f"{parts[1]}-{parts[2]}" if len(parts) >= 3 else 'N/A'
		else:
			frequency = 'N/A'

		# Extract trading hours - stored as string representation of dict
		trading_hours = run.get('trading_hours', '')

		if trading_hours and isinstance(trading_hours, str):
			# Parse string like "{'start': datetime.time(8, 0), 'end': datetime.time(16, 0)}"
			start_match = re.search(r"'start':\s*datetime\.time\((\d+),\s*(\d+)\)", trading_hours)
			end_match = re.search(r"'end':\s*datetime\.time\((\d+),\s*(\d+)\)", trading_hours)

			if start_match:
				hour = int(start_match.group(1))
				minute = int(start_match.group(2))
				trading_start = f"{hour}:{minute:02d}"
			else:
				trading_start = 'N/A'

			if end_match:
				hour = int(end_match.group(1))
				minute = int(end_match.group(2))
				trading_end = f"{hour}:{minute:02d}"
			else:
				trading_end = 'N/A'
		elif isinstance(trading_hours, dict):
			# Already a dict with start/end keys
			trading_start = str(trading_hours.get('start', 'N/A'))
			trading_end = str(trading_hours.get('end', 'N/A'))
		else:
			# Fallback for old format
			trading_start = str(run.get('trading_start_time', 'N/A'))
			trading_end = str(run.get('trading_end_time', 'N/A'))

		summary_data.append({
			'Run': i + 1,
			'Ticker': run.get('ticker', 'N/A'),
			'Frequency': frequency,
			'Burn-in Start': run.get('burnin_start_date', 'N/A'),
			'Burn-in End': run.get('burnin_end_date', 'N/A'),
			'Backtest End': run.get('backtest_end_date', 'N/A'),
			'Trading Start': trading_start,
			'Trading End': trading_end,
			'Entry P Top': run.get('entry_bound_p_top', 'N/A'),
			'Sig Val long top': run.get('signal_value_long_top', 'N/A'),
			'Max Pos Bars': run.get('max_position_bars', 'N/A'),
			'Filepath': str(run.get('run_path', 'N/A')),
		})

	return pd.DataFrame(summary_data)


def display_runs_summary(runs_metadata: list, max_runs: Optional[int] = None, show_all_keys: bool = True, as_dataframe: bool = False):
	"""
	Display a formatted summary of scanned runs with all available keys.

	Args:
		runs_metadata: List of run metadata from scan_backtest_runs() or scan_live_runs()
		max_runs: Maximum number of runs to display (None = all)
		show_all_keys: If True, show ALL keys for each run (default: True)
		as_dataframe: If True, return a pandas DataFrame instead of printing
	"""
	if not runs_metadata:
		print("No runs found.")
		return None if as_dataframe else None

	# Collect all unique keys across all runs
	all_keys = set()
	for run in runs_metadata:
		all_keys.update(run.keys())

	# If returning as DataFrame
	if as_dataframe:
		# Create DataFrame with all runs and all keys
		df_data = []
		for i, run in enumerate(runs_metadata):
			row = {'run_number': i + 1}
			for key in sorted(all_keys):
				if key in ['strategy_data_file', 'run_path']:
					row[key] = str(run.get(key, 'N/A'))
				else:
					row[key] = run.get(key, 'N/A')
			df_data.append(row)

		df = pd.DataFrame(df_data)
		# Move run_number to first column
		cols = ['run_number'] + [col for col in df.columns if col != 'run_number']
		return df[cols]

	# Otherwise print formatted output
	print(f"\n{'='*120}")
	print(f"FOUND {len(runs_metadata)} RUNS")
	print(f"{'='*120}\n")

	# Show all available keys
	print(f"Available keys across all runs: {len(all_keys)}")
	print(f"Keys: {', '.join(sorted(all_keys))}")
	print()

	display_count = len(runs_metadata) if max_runs is None else min(max_runs, len(runs_metadata))

	for i, run in enumerate(runs_metadata[:display_count]):
		print(f"Run {i+1}:")

		if show_all_keys:
			# Show ALL keys for this run
			for key in sorted(all_keys):
				if key in run:
					value = run[key]
					# Format the key name nicely
					display_key = key.replace('_', ' ').title()

					# Format different value types appropriately
					if isinstance(value, float):
						print(f"  {display_key}: {value:.6f}")
					elif isinstance(value, Path):
						print(f"  {display_key}: {value.name}")
					elif key.startswith('metric_'):
						metric_name = key.replace('metric_', '').replace('_', ' ').title()
						print(f"  Metric - {metric_name}: {value:.6f}" if isinstance(value, (int, float)) else f"  Metric - {metric_name}: {value}")
					else:
						print(f"  {display_key}: {value}")
				else:
					# Show that this key is missing for this run
					display_key = key.replace('_', ' ').title()
					print(f"  {display_key}: <not available>")
		else:
			# Simplified view - show only key fields
			print(f"  Ticker: {run.get('ticker', 'N/A')}")
			print(f"  Date: {run.get('date', 'N/A')}")
			print(f"  Run Directory: {run.get('run_directory', 'N/A')}")
			print(f"  Strategy: {run.get('strategy_class', 'N/A')}")

			# Display key parameters
			if 'bar_type' in run:
				print(f"  Bar Type: {run['bar_type']}")
			if 'entry_bound_p_top' in run:
				print(f"  Entry Bound P Top: {run['entry_bound_p_top']}")
			if 'entry_bound_p_bottom' in run:
				print(f"  Entry Bound P Bottom: {run['entry_bound_p_bottom']}")

			# Display any metrics
			metrics = {k: v for k, v in run.items() if k.startswith('metric_')}
			if metrics:
				print(f"  Metrics:")
				for metric_name, metric_value in metrics.items():
					clean_name = metric_name.replace('metric_', '').replace('_', ' ').title()
					print(f"    {clean_name}: {metric_value:.4f}")

		print()

	if max_runs and len(runs_metadata) > max_runs:
		print(f"... and {len(runs_metadata) - max_runs} more runs")

	return None
