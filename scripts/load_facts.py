#!/usr/bin/env python3
"""Validate processed HMIS CSVs or load dimensions and TV3 facts into PostgreSQL."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
FACT_SQL = ROOT / "sql" / "healthcare_dw_facts.sql"

TABLES = (
    "admission", "bed", "billing", "billing_detail", "department", "diagnostic_test",
    "disease", "doctor", "drug", "drug_inventory", "drug_manufacturer", "employee",
    "insurance_provider", "patient", "patient_diagnostic", "patient_insurance",
    "prescription", "staff_assignment", "ward",
)

PRIMARY_KEYS = {
    "admission": "admission_id", "bed": "bed_id", "billing": "bill_id",
    "billing_detail": "billing_detail_id", "department": "department_id",
    "diagnostic_test": "test_id", "disease": "disease_id", "doctor": "doctor_id",
    "drug": "drug_id", "drug_inventory": "inventory_id",
    "drug_manufacturer": "manufacturer_id", "employee": "employee_id",
    "insurance_provider": "insurance_provider_id", "patient": "patient_id",
    "patient_diagnostic": "patient_diagnostic_id",
    "patient_insurance": "patient_insurance_id", "prescription": "prescription_id",
    "staff_assignment": "assignment_id", "ward": "ward_id",
}

REQUIRED_COLUMNS = {
    "admission": {"admission_date", "discharge_date", "admission_type", "admission_status",
                  "patient_id", "department_id", "ward_id", "bed_id", "disease_id",
                  "length_of_stay_days", "overlapping_stay_flag"},
    "bed": {"bed_number", "bed_status", "ward_id"},
    "billing": {"bill_date", "total_amount", "insurance_covered_amount",
                "patient_payable_amount", "payment_status", "payment_mode", "admission_id"},
    "billing_detail": {"charge_type", "reference_id", "amount", "bill_id"},
    "department": {"department_name", "department_type", "floor_number", "status"},
    "diagnostic_test": {"test_name", "test_category", "standard_cost", "department_id"},
    "disease": {"disease_name", "disease_category"},
    "doctor": {"employee_id", "specialization", "qualification", "experience_years"},
    "drug": {"drug_name", "brand_name", "drug_category", "unit_cost", "manufacturer_id"},
    "drug_inventory": {"drug_id"},
    "drug_manufacturer": {"manufacturer_name", "country", "reliability_rating", "contract_status"},
    "employee": {"employee_name", "gender", "role", "employment_type", "date_of_joining", "department_id"},
    "insurance_provider": {"provider_name", "provider_type", "coverage_limit"},
    "patient": {"gender", "date_of_birth", "blood_group", "city", "contact_number"},
    "patient_diagnostic": {"test_date", "result_status", "admission_id", "test_id", "doctor_id"},
    "patient_insurance": {"policy_number", "coverage_percentage", "policy_start_date",
                          "policy_end_date", "patient_id", "insurance_provider_id"},
    "prescription": {"dosage", "frequency", "duration_days", "admission_id", "drug_id"},
    "staff_assignment": {"employee_id", "ward_id", "shift"},
    "ward": {"ward_name", "ward_type", "total_beds", "department_id"},
}

FOREIGN_KEYS = (
    ("ward", "department_id", "department", "department_id"),
    ("bed", "ward_id", "ward", "ward_id"),
    ("drug", "manufacturer_id", "drug_manufacturer", "manufacturer_id"),
    ("drug_inventory", "drug_id", "drug", "drug_id"),
    ("diagnostic_test", "department_id", "department", "department_id"),
    ("employee", "department_id", "department", "department_id"),
    ("doctor", "employee_id", "employee", "employee_id"),
    ("patient_insurance", "patient_id", "patient", "patient_id"),
    ("patient_insurance", "insurance_provider_id", "insurance_provider", "insurance_provider_id"),
    ("admission", "patient_id", "patient", "patient_id"),
    ("admission", "department_id", "department", "department_id"),
    ("admission", "ward_id", "ward", "ward_id"),
    ("admission", "bed_id", "bed", "bed_id"),
    ("admission", "disease_id", "disease", "disease_id"),
    ("billing", "admission_id", "admission", "admission_id"),
    ("billing_detail", "bill_id", "billing", "bill_id"),
    ("patient_diagnostic", "admission_id", "admission", "admission_id"),
    ("patient_diagnostic", "test_id", "diagnostic_test", "test_id"),
    ("patient_diagnostic", "doctor_id", "doctor", "doctor_id"),
    ("prescription", "admission_id", "admission", "admission_id"),
    ("prescription", "drug_id", "drug", "drug_id"),
    ("staff_assignment", "employee_id", "employee", "employee_id"),
    ("staff_assignment", "ward_id", "ward", "ward_id"),
)


def read_table(name: str) -> tuple[list[str], list[dict[str, str]]]:
    path = DATA_DIR / f"{name}.csv"
    if not path.is_file():
        raise ValueError(f"Missing input file: {path.relative_to(ROOT)}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path.relative_to(ROOT)}")
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field or "") for field in reader.fieldnames):
            raise ValueError(f"Unsafe or empty column name in {path.relative_to(ROOT)}")
        return list(reader.fieldnames), list(reader)


def validate_inputs() -> dict[str, tuple[list[str], list[dict[str, str]]]]:
    data = {name: read_table(name) for name in TABLES}
    errors: list[str] = []
    key_sets: dict[str, set[str]] = {}

    for table, (columns, rows) in data.items():
        missing_columns = REQUIRED_COLUMNS[table] - set(columns)
        if missing_columns:
            errors.append(f"{table}: missing required column(s): {', '.join(sorted(missing_columns))}")
        key = PRIMARY_KEYS[table]
        if key not in columns:
            errors.append(f"{table}: missing primary-key column {key}")
            continue
        keys = [row.get(key, "").strip() for row in rows]
        if any(not value for value in keys):
            errors.append(f"{table}: {sum(not value for value in keys)} empty {key} value(s)")
        duplicates = len(keys) - len(set(keys))
        if duplicates:
            errors.append(f"{table}: {duplicates} duplicate {key} value(s)")
        key_sets[table] = set(keys)

    for child, fk, parent, pk in FOREIGN_KEYS:
        child_rows = data[child][1]
        if fk not in data[child][0]:
            errors.append(f"{child}: missing foreign-key column {fk}")
            continue
        if parent not in key_sets:
            continue
        orphaned = sum(
            bool(value := row.get(fk, "").strip()) and value not in key_sets[parent]
            for row in child_rows
        )
        if orphaned:
            errors.append(f"{child}.{fk}: {orphaned} orphan reference(s) to {parent}.{pk}")

    for table, column in (("admission", "admission_date"), ("billing", "bill_date"),
                          ("patient_diagnostic", "test_date")):
        columns, rows = data[table]
        if column not in columns:
            errors.append(f"{table}: missing required date column {column}")
            continue
        for row_number, row in enumerate(rows, start=2):
            try:
                date.fromisoformat(row[column].strip())
            except (TypeError, ValueError):
                errors.append(f"{table}:{row_number}: invalid {column} value {row.get(column)!r}")
                if len(errors) >= 30:
                    break

    if errors:
        raise ValueError("Input validation failed:\n- " + "\n- ".join(errors[:30]))

    return data


def load_to_postgres(data: dict[str, tuple[list[str], list[dict[str, str]]]], dsn: str) -> None:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install the PostgreSQL driver with: pip install -r requirements.txt") from exc

    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            for table, (columns, _) in data.items():
                column_sql = ", ".join(f'"{column}" TEXT' for column in columns)
                cursor.execute(f'CREATE TEMP TABLE "stg_{table}" ({column_sql}) ON COMMIT DROP')
                copy_columns = ", ".join(f'"{column}"' for column in columns)
                with (DATA_DIR / f"{table}.csv").open("r", encoding="utf-8-sig", newline="") as source:
                    with cursor.copy(
                        f'COPY "stg_{table}" ({copy_columns}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL \'\')'
                    ) as copy:
                        while chunk := source.read(1024 * 1024):
                            copy.write(chunk)

            statements = [
                statement.strip()
                for statement in FACT_SQL.read_text(encoding="utf-8").split(";")
                if statement.strip()
            ]
            for index, statement in enumerate(statements, start=1):
                label = next((line.strip() for line in statement.splitlines() if line.strip()), "SQL")
                print(f"Running SQL {index}/{len(statements)}: {label[:100]}", flush=True)
                cursor.execute(statement)

            fact_tables = (
                "fact_admission", "fact_bed_occupancy", "fact_billing", "fact_billing_detail",
                "fact_diagnostic", "fact_prescription", "fact_staff_assignment",
            )
            counts = {}
            for table in fact_tables:
                cursor.execute(f"SELECT COUNT(*) FROM dw.{table}")
                counts[table] = cursor.fetchone()[0]

    print("Load committed successfully:")
    for table, count in counts.items():
        print(f"  {table}: {count:,} rows")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="Check CSV schema, PKs, FKs, and dates; do not connect to PostgreSQL")
    parser.add_argument("--dsn", default=os.getenv("DW_DSN"), help="PostgreSQL DSN (or set DW_DSN)")
    args = parser.parse_args()

    try:
        data = validate_inputs()
        print("Input validation passed:")
        for table, (_, rows) in data.items():
            print(f"  {table}: {len(rows):,} rows")
        if args.validate_only:
            return 0
        if not args.dsn:
            raise ValueError("Provide --dsn or set the DW_DSN environment variable")
        load_to_postgres(data, args.dsn)
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
