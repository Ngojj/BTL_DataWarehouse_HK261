"""Generate transparent operational alerts from the DW and inventory CSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = ROOT / "data" / "processed" / "drug_inventory.csv"


BED_ALERTS_SQL = """
WITH latest AS (
    SELECT MAX(d.full_date) AS full_date
    FROM dw.fact_bed_occupancy f
    JOIN dw.dim_date d ON d.date_key = f.date_key
), ward_snapshot AS (
    SELECT w.ward_id, w.ward_name, d.full_date,
           SUM(f.occupied_bed_count)::INT AS occupied_beds,
           SUM(f.available_bed_count)::INT AS available_beds,
           SUM(f.capacity_bed_count)::INT AS capacity_beds
    FROM dw.fact_bed_occupancy f
    JOIN dw.dim_date d ON d.date_key = f.date_key
    JOIN dw.dim_ward w ON w.ward_key = f.ward_key
    CROSS JOIN latest l
    WHERE d.full_date = l.full_date
    GROUP BY w.ward_id, w.ward_name, d.full_date
)
SELECT ward_id, ward_name, full_date, occupied_beds, available_beds,
       capacity_beds,
       occupied_beds::NUMERIC / NULLIF(capacity_beds, 0) AS occupancy_rate
FROM ward_snapshot
ORDER BY occupancy_rate DESC NULLS LAST, ward_name
"""


AREA_ATTENTION_SQL = """
WITH latest AS (
    SELECT MAX(d.full_date) AS full_date
    FROM dw.fact_bed_occupancy f
    JOIN dw.dim_date d ON d.date_key = f.date_key
), occupancy AS (
    SELECT f.ward_key,
           SUM(f.occupied_bed_count)::INT AS occupied_beds,
           SUM(f.capacity_bed_count)::INT AS capacity_beds
    FROM dw.fact_bed_occupancy f
    JOIN dw.dim_date d ON d.date_key = f.date_key
    CROSS JOIN latest l
    WHERE d.full_date = l.full_date
    GROUP BY f.ward_key
), admissions AS (
    SELECT f.ward_key,
           SUM(f.admission_count)::INT AS admissions_in_window,
           AVG(f.length_of_stay_days)::NUMERIC(10,2) AS avg_length_of_stay_days
    FROM dw.fact_admission f
    JOIN dw.dim_date d ON d.date_key = f.admission_date_key
    CROSS JOIN latest l
    WHERE d.full_date > l.full_date - (%s * INTERVAL '1 day')
      AND d.full_date <= l.full_date
    GROUP BY f.ward_key
), staffing AS (
    SELECT ward_key, SUM(assignment_count)::INT AS staff_assignments
    FROM dw.fact_staff_assignment
    GROUP BY ward_key
), metrics AS (
    SELECT w.ward_key, w.ward_id, w.ward_name,
           COALESCE(o.occupied_beds, 0) AS occupied_beds,
           COALESCE(o.capacity_beds, 0) AS capacity_beds,
           CASE WHEN COALESCE(o.capacity_beds, 0) = 0 THEN NULL
                ELSE o.occupied_beds::NUMERIC / o.capacity_beds END AS occupancy_rate,
           COALESCE(a.admissions_in_window, 0) AS admissions_in_window,
           a.avg_length_of_stay_days,
           COALESCE(s.staff_assignments, 0) AS staff_assignments
    FROM dw.dim_ward w
    LEFT JOIN occupancy o ON o.ward_key = w.ward_key
    LEFT JOIN admissions a ON a.ward_key = w.ward_key
    LEFT JOIN staffing s ON s.ward_key = w.ward_key
), baselines AS (
    SELECT AVG(admissions_in_window)::NUMERIC AS avg_admissions,
           AVG(avg_length_of_stay_days)::NUMERIC AS avg_length_of_stay,
           AVG(staff_assignments)::NUMERIC AS avg_staff_assignments
    FROM metrics
), flags AS (
    SELECT m.*, l.full_date AS snapshot_date,
           COALESCE(m.occupancy_rate >= 0.70, FALSE) AS high_occupancy_flag,
           COALESCE(m.admissions_in_window > b.avg_admissions, FALSE) AS high_admissions_flag,
           COALESCE(m.avg_length_of_stay_days > b.avg_length_of_stay, FALSE) AS long_stay_flag,
           COALESCE(m.staff_assignments < b.avg_staff_assignments, FALSE) AS low_staffing_flag
    FROM metrics m
    CROSS JOIN baselines b
    CROSS JOIN latest l
)
SELECT *,
       (high_occupancy_flag::INT + high_admissions_flag::INT +
        long_stay_flag::INT + low_staffing_flag::INT) AS attention_score
FROM flags
ORDER BY attention_score DESC, occupancy_rate DESC NULLS LAST, ward_name
"""


def _rows(cursor: Any) -> list[dict[str, Any]]:
    columns = [column.name for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_bed_occupancy_alerts(connection: Any) -> list[dict[str, Any]]:
    """Return the latest occupancy snapshot and M1 threshold classification."""
    with connection.cursor() as cursor:
        cursor.execute(BED_ALERTS_SQL)
        results = _rows(cursor)

    for row in results:
        rate = row["occupancy_rate"]
        if rate is None:
            row["alert_level"] = "NO_CAPACITY_DATA"
        elif rate < 0.70:
            row["alert_level"] = "NORMAL"
        elif rate < 0.85:
            row["alert_level"] = "WATCH"
        else:
            row["alert_level"] = "HIGH_PRESSURE"
    return results


def get_low_stock_alerts(inventory_csv: Path = DEFAULT_INVENTORY) -> list[dict[str, Any]]:
    """Return medicines whose current stock is below their configured reorder level."""
    with inventory_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"drug_id", "current_stock", "reorder_level"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{inventory_csv}: missing column(s): {', '.join(sorted(missing))}")

        alerts = []
        for line, row in enumerate(reader, start=2):
            try:
                stock = int(row["current_stock"])
                reorder = int(row["reorder_level"])
                drug_id = int(row["drug_id"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{inventory_csv}:{line}: invalid inventory quantity or drug_id") from exc
            if stock < reorder:
                alerts.append({
                    "drug_id": drug_id,
                    "drug_name": row.get("drug_name") or None,
                    "current_stock": stock,
                    "reorder_level": reorder,
                    "shortfall": reorder - stock,
                    "alert_level": "LOW_STOCK",
                })
    return alerts


def get_area_attention(connection: Any, lookback_days: int = 30) -> list[dict[str, Any]]:
    """Rank wards using occupancy, recent admissions/LOS, and assigned staff.

    Since M1 defines no numeric thresholds for this combined alert, each of the
    four indicators is compared with the hospital-wide ward average. A ward is
    flagged when at least two indicators are adverse. This is a DSS heuristic,
    not a clinical or staffing standard.
    """
    if lookback_days < 1:
        raise ValueError("lookback_days must be at least 1")

    with connection.cursor() as cursor:
        cursor.execute(AREA_ATTENTION_SQL, (lookback_days,))
        results = _rows(cursor)

    reason_labels = {
        "high_occupancy_flag": "occupancy >= 70%",
        "high_admissions_flag": f"admissions above ward average in {lookback_days}-day window",
        "long_stay_flag": "average LOS above hospital ward average",
        "low_staffing_flag": "staff assignments below ward average",
    }
    for row in results:
        row["attention_flag"] = row["attention_score"] >= 2
        row["reasons"] = [
            label for key, label in reason_labels.items() if row[key]
        ]
    return results


def build_dss_report(
    connection: Any,
    inventory_csv: Path = DEFAULT_INVENTORY,
    lookback_days: int = 30,
) -> dict[str, Any]:
    """Build all three TV3 alert outputs."""
    low_stock = get_low_stock_alerts(inventory_csv)
    if low_stock:
        drug_ids = [row["drug_id"] for row in low_stock]
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT drug_id, drug_name FROM dw.dim_drug WHERE drug_id = ANY(%s)",
                (drug_ids,),
            )
            names = {drug_id: drug_name for drug_id, drug_name in cursor.fetchall()}
        for row in low_stock:
            row["drug_name"] = names.get(row["drug_id"])

    return {
        "bed_occupancy_alerts": get_bed_occupancy_alerts(connection),
        "low_stock_alerts": low_stock,
        "area_attention": get_area_attention(connection, lookback_days),
        "notes": {
            "area_attention_rule": (
                "Flag when at least 2 of 4 indicators are adverse versus ward averages; "
                "heuristic for management review, not a clinical standard."
            ),
            "admission_lookback_days": lookback_days,
        },
    }
