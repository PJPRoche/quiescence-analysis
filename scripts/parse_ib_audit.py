#!/usr/bin/env python3
"""
Parse Interactive Brokers audit trail XML files into CSV format.

This script parses IB audit trail files containing FIX protocol messages
and extracts order and fill information into a structured CSV format.

Usage:
    python scripts/parse_ib_audit.py --input /path/to/audit_file.tmp --output /path/to/output.csv
    python scripts/parse_ib_audit.py --input /path/to/audit_file.tmp  # Auto-generates output filename
"""

import argparse
import csv
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# FIX Protocol Tag Mappings (commonly used tags)
FIX_TAGS = {
    "11": "ClOrdID",           # Client Order ID
    "17": "ExecID",            # Execution ID
    "31": "LastPx",            # Last execution price
    "32": "LastQty",           # Last execution quantity
    "37": "OrderID",           # Order ID
    "38": "OrderQty",          # Total order quantity
    "39": "OrdStatus",         # Order status (0=New, 1=PartialFill, 2=Filled, 4=Canceled, 8=Rejected)
    "40": "OrdType",           # Order type (1=Market, 2=Limit, 3=Stop, 4=StopLimit)
    "44": "Price",             # Limit price
    "52": "SendingTime",       # Message sending time
    "54": "Side",              # Side (1=Buy, 2=Sell)
    "55": "Symbol",            # Symbol/Ticker
    "59": "TimeInForce",       # Time in force
    "60": "TransactTime",      # Transaction time
    "100": "ExDestination",    # Execution destination (exchange)
    "150": "ExecType",         # Execution type
    "151": "LeavesQty",        # Remaining quantity
    "167": "SecurityType",     # Security type (STK=Stock)
    "6010": "NautilusOrderID", # Custom Nautilus order ID
    "6119": "StrategyID",      # Strategy ID
    "6121": "ClientID",        # Client ID
}

# Order Status mappings
ORDER_STATUS = {
    "0": "New",
    "1": "PartiallyFilled",
    "2": "Filled",
    "3": "DoneForDay",
    "4": "Canceled",
    "5": "Replaced",
    "6": "PendingCancel",
    "7": "Stopped",
    "8": "Rejected",
    "9": "Suspended",
    "A": "PendingNew",
    "C": "Expired",
}

# Side mappings
SIDE_MAP = {
    "1": "Buy",
    "2": "Sell",
}

# Order Type mappings
ORDER_TYPE = {
    "1": "Market",
    "2": "Limit",
    "3": "Stop",
    "4": "StopLimit",
}


def parse_timestamp(ts_str: str) -> str:
    """Convert FIX timestamp format to readable format."""
    try:
        # FIX format: YYYYMMDD-HH:MM:SS
        dt = datetime.strptime(ts_str, "%Y%m%d-%H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return ts_str


def parse_entry(entry: ET.Element) -> Optional[Dict[str, str]]:
    """Parse a single Entry element and extract field values."""
    entry_type = entry.get("type")
    msg_id = entry.get("msgId")

    # Only process relevant entry types
    if entry_type not in ["PlaceOrder", "Filled", "PartiallyFilled", "Canceled", "Rejected", "Acknowledged"]:
        return None

    # Extract fields into a dictionary
    fields = {}
    fields["EntryType"] = entry_type
    fields["MsgId"] = msg_id

    for field in entry.findall("field"):
        tag = field.get("tag")
        val = field.get("val")

        # Map tag to human-readable name if available
        field_name = FIX_TAGS.get(tag, f"Tag_{tag}")
        fields[field_name] = val

    # Apply mappings for coded values
    if "OrdStatus" in fields:
        status_code = fields["OrdStatus"]
        fields["OrdStatusDesc"] = ORDER_STATUS.get(status_code, status_code)

    if "Side" in fields:
        side_code = fields["Side"]
        fields["SideDesc"] = SIDE_MAP.get(side_code, side_code)

    if "OrdType" in fields:
        type_code = fields["OrdType"]
        fields["OrdTypeDesc"] = ORDER_TYPE.get(type_code, type_code)

    # Parse timestamps
    if "SendingTime" in fields:
        fields["SendingTime"] = parse_timestamp(fields["SendingTime"])

    if "TransactTime" in fields:
        fields["TransactTime"] = parse_timestamp(fields["TransactTime"])

    return fields


def parse_audit_file(input_path: Path) -> List[Dict[str, str]]:
    """Parse the entire audit XML file and return list of records."""
    print(f"Parsing audit file: {input_path}")
    print(f"File size: {input_path.stat().st_size / (1024*1024):.2f} MB")

    records = []

    try:
        # Parse XML incrementally for large files
        context = ET.iterparse(str(input_path), events=("start", "end"))
        context = iter(context)

        entry_count = 0
        processed_count = 0

        for event, elem in context:
            if event == "end" and elem.tag == "Entry":
                entry_count += 1

                # Parse the entry
                record = parse_entry(elem)
                if record:
                    records.append(record)
                    processed_count += 1

                # Clear element to free memory
                elem.clear()

                # Progress indicator
                if entry_count % 10000 == 0:
                    print(f"Processed {entry_count:,} entries, extracted {processed_count:,} records...")

        print(f"\nCompleted: Processed {entry_count:,} total entries")
        print(f"Extracted {processed_count:,} relevant records")

    except ET.ParseError as e:
        print(f"XML Parse Error: {e}")
        raise

    return records


def write_csv(records: List[Dict[str, str]], output_path: Path):
    """Write records to CSV file."""
    if not records:
        print("No records to write!")
        return

    # Determine all unique columns across all records
    all_columns = set()
    for record in records:
        all_columns.update(record.keys())

    # Define preferred column order (most important fields first)
    priority_columns = [
        "EntryType", "SendingTime", "TransactTime", "Symbol",
        "SideDesc", "OrdTypeDesc", "OrdStatusDesc",
        "OrderQty", "LastQty", "LeavesQty",
        "Price", "LastPx",
        "ClOrdID", "OrderID", "ExecID", "NautilusOrderID",
        "ExDestination", "StrategyID", "ClientID"
    ]

    # Add priority columns that exist, then add remaining columns alphabetically
    columns = [col for col in priority_columns if col in all_columns]
    remaining = sorted(all_columns - set(columns))
    columns.extend(remaining)

    print(f"\nWriting {len(records):,} records to: {output_path}")
    print(f"Columns: {len(columns)}")

    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)

    print(f"Successfully written to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Parse IB audit trail XML files into CSV format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert audit file to CSV (auto-generate output filename)
  python scripts/parse_ib_audit.py --input /data/quiescence/live_runs/audit_reports/2026-01-30.tmp

  # Specify output filename
  python scripts/parse_ib_audit.py --input audit.tmp --output orders.csv

  # Process all .tmp files in a directory
  for f in /data/quiescence/live_runs/audit_reports/*.tmp; do
      python scripts/parse_ib_audit.py --input "$f"
  done
        """
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Path to IB audit trail XML file (.tmp)"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output CSV file path (default: input_file.csv)"
    )

    args = parser.parse_args()

    # Resolve input path
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 1

    # Determine output path
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        # Auto-generate: same name but .csv extension
        output_path = input_path.with_suffix('.csv')

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse and convert
    try:
        records = parse_audit_file(input_path)
        write_csv(records, output_path)

        # Print summary statistics
        print("\n" + "="*60)
        print("SUMMARY STATISTICS")
        print("="*60)

        # Count by entry type
        entry_types = {}
        for record in records:
            entry_type = record.get("EntryType", "Unknown")
            entry_types[entry_type] = entry_types.get(entry_type, 0) + 1

        print("\nRecords by Entry Type:")
        for entry_type, count in sorted(entry_types.items()):
            print(f"  {entry_type:20s}: {count:>6,}")

        # Count by symbol
        symbols = {}
        for record in records:
            symbol = record.get("Symbol", "Unknown")
            if symbol and symbol != "*":
                symbols[symbol] = symbols.get(symbol, 0) + 1

        if symbols:
            print("\nRecords by Symbol (top 10):")
            for symbol, count in sorted(symbols.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {symbol:10s}: {count:>6,}")

        print("\n" + "="*60)

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
