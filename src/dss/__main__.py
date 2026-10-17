"""Command line entry point: python -m src.dss."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal
import json
import os
import sys
from pathlib import Path

from .engine import DEFAULT_INVENTORY, build_dss_report


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__} to JSON")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate basic healthcare DW DSS alerts")
    parser.add_argument("--dsn", default=os.getenv("DW_DSN"), help="PostgreSQL DSN (or set DW_DSN)")
    parser.add_argument("--inventory-csv", type=Path, default=DEFAULT_INVENTORY,
                        help="Processed drug_inventory.csv path")
    parser.add_argument("--lookback-days", type=int, default=30,
                        help="Admission/LOS analysis window anchored at the latest occupancy date")
    args = parser.parse_args()

    if not args.dsn:
        parser.error("provide --dsn or set DW_DSN")

    try:
        import psycopg

        with psycopg.connect(args.dsn) as connection:
            report = build_dss_report(connection, args.inventory_csv, args.lookback_days)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default))
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ImportError as exc:
        print("Install the PostgreSQL driver with: pip install -r requirements.txt", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
