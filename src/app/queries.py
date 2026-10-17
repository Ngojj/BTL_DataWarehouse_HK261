"""SQL query helpers for the healthcare DW dashboard.

Each function reads from the `dw` schema (see sql/healthcare_dw_dimensions.sql
and sql/healthcare_dw_facts.sql) and returns a pandas DataFrame or a dict of
scalars. The leading underscore on the `_engine` parameter tells Streamlit's
cache not to try to hash the SQLAlchemy Engine object.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import text


def _dept_clause(dept_ids: list[int] | None, alias: str = "dep") -> str:
    return f"AND {alias}.department_id = ANY(:dept_ids)" if dept_ids else ""


@st.cache_data(ttl=600, show_spinner=False)
def get_date_bounds(_engine) -> tuple[date, date]:
    df = pd.read_sql_query(
        text("SELECT MIN(full_date) AS min_date, MAX(full_date) AS max_date FROM dw.dim_date"),
        _engine,
    )
    row = df.iloc[0]
    return row["min_date"], row["max_date"]


@st.cache_data(ttl=600, show_spinner=False)
def get_departments(_engine) -> pd.DataFrame:
    return pd.read_sql_query(
        text("SELECT department_id, department_name FROM dw.dim_department ORDER BY department_name"),
        _engine,
    )


@st.cache_data(ttl=300, show_spinner=False)
def overview_kpis(_engine, start: date, end: date) -> dict[str, Any]:
    sql = text("""
        SELECT
            (SELECT COALESCE(SUM(f.admission_count), 0)
               FROM dw.fact_admission f JOIN dw.dim_date d ON d.date_key = f.admission_date_key
              WHERE d.full_date BETWEEN :start AND :end) AS total_admissions,
            (SELECT COUNT(DISTINCT f.patient_key)
               FROM dw.fact_admission f JOIN dw.dim_date d ON d.date_key = f.admission_date_key
              WHERE d.full_date BETWEEN :start AND :end) AS total_patients,
            (SELECT AVG(f.length_of_stay_days)
               FROM dw.fact_admission f JOIN dw.dim_date d ON d.date_key = f.admission_date_key
              WHERE d.full_date BETWEEN :start AND :end AND f.length_of_stay_days IS NOT NULL) AS avg_los,
            (SELECT COALESCE(SUM(b.total_amount), 0)
               FROM dw.fact_billing b JOIN dw.dim_date d ON d.date_key = b.billing_date_key
              WHERE d.full_date BETWEEN :start AND :end) AS total_billing,
            (SELECT SUM(f.occupied_bed_count)::NUMERIC / NULLIF(SUM(f.capacity_bed_count), 0)
               FROM dw.fact_bed_occupancy f
              WHERE f.date_key = (
                  SELECT dd.date_key FROM dw.dim_date dd
                   WHERE dd.full_date = (
                       SELECT MAX(d.full_date) FROM dw.fact_admission a
                       JOIN dw.dim_date d ON d.date_key = a.admission_date_key
                   )
              )) AS latest_occupancy_rate
    """)
    df = pd.read_sql_query(sql, _engine, params={"start": start, "end": end})
    return df.iloc[0].to_dict()


@st.cache_data(ttl=300, show_spinner=False)
def admissions_by_month(_engine, start: date, end: date) -> pd.DataFrame:
    sql = text("""
        SELECT DATE_TRUNC('month', d.full_date)::DATE AS month_start,
               SUM(f.admission_count) AS admissions
          FROM dw.fact_admission f
          JOIN dw.dim_date d ON d.date_key = f.admission_date_key
         WHERE d.full_date BETWEEN :start AND :end
         GROUP BY 1 ORDER BY 1
    """)
    return pd.read_sql_query(sql, _engine, params={"start": start, "end": end})


@st.cache_data(ttl=300, show_spinner=False)
def bed_occupancy_by_ward(_engine) -> pd.DataFrame:
    """Latest daily snapshot per ward (fact_bed_occupancy is a periodic-snapshot fact).

    "Latest" is anchored on the last admission_date rather than MAX(date_key) in
    dim_date: dim_date's calendar extends past the last admission because a few
    discharge_date values trail beyond it, so the absolute last calendar day can
    be a nearly-empty tail day (e.g. 1/415 beds) that misrepresents real occupancy.
    """
    sql = text("""
        SELECT w.ward_name,
               SUM(f.occupied_bed_count) AS occupied_beds,
               SUM(f.available_bed_count) AS available_beds,
               SUM(f.capacity_bed_count) AS capacity_beds,
               SUM(f.occupied_bed_count)::NUMERIC / NULLIF(SUM(f.capacity_bed_count), 0) AS occupancy_rate
          FROM dw.fact_bed_occupancy f
          JOIN dw.dim_ward w ON w.ward_key = f.ward_key
         WHERE f.date_key = (
             SELECT dd.date_key FROM dw.dim_date dd
              WHERE dd.full_date = (
                  SELECT MAX(d.full_date) FROM dw.fact_admission a
                  JOIN dw.dim_date d ON d.date_key = a.admission_date_key
              )
         )
         GROUP BY w.ward_name
         ORDER BY occupancy_rate DESC NULLS LAST
    """)
    return pd.read_sql_query(sql, _engine)


@st.cache_data(ttl=300, show_spinner=False)
def occupancy_trend(_engine, start: date, end: date) -> pd.DataFrame:
    """Monthly occupancy rate: sum occupied/capacity within the bucket, not an average of rates."""
    sql = text("""
        SELECT DATE_TRUNC('month', d.full_date)::DATE AS month_start,
               SUM(f.occupied_bed_count)::NUMERIC / NULLIF(SUM(f.capacity_bed_count), 0) AS occupancy_rate
          FROM dw.fact_bed_occupancy f
          JOIN dw.dim_date d ON d.date_key = f.date_key
         WHERE d.full_date BETWEEN :start AND :end
         GROUP BY 1 ORDER BY 1
    """)
    return pd.read_sql_query(sql, _engine, params={"start": start, "end": end})


@st.cache_data(ttl=300, show_spinner=False)
def admissions_by_department(_engine, start: date, end: date) -> pd.DataFrame:
    sql = text("""
        SELECT COALESCE(dep.department_name, 'Không xác định') AS department_name,
               SUM(f.admission_count) AS admissions,
               AVG(f.length_of_stay_days) AS avg_los
          FROM dw.fact_admission f
          JOIN dw.dim_date d ON d.date_key = f.admission_date_key
          LEFT JOIN dw.dim_department dep ON dep.department_key = f.department_key
         WHERE d.full_date BETWEEN :start AND :end
         GROUP BY dep.department_name
         ORDER BY admissions DESC
    """)
    return pd.read_sql_query(sql, _engine, params={"start": start, "end": end})


@st.cache_data(ttl=300, show_spinner=False)
def billing_summary(_engine, start: date, end: date, dept_ids: list[int] | None) -> dict[str, Any]:
    sql = text(f"""
        SELECT COALESCE(SUM(b.total_amount), 0) AS total_billing,
               COALESCE(SUM(b.insurance_covered_amount), 0) AS total_insurance_covered,
               COALESCE(SUM(b.patient_payable_amount), 0) AS total_patient_payable
          FROM dw.fact_billing b
          JOIN dw.dim_date d ON d.date_key = b.billing_date_key
          LEFT JOIN dw.dim_department dep ON dep.department_key = b.department_key
         WHERE d.full_date BETWEEN :start AND :end
         {_dept_clause(dept_ids)}
    """)
    params: dict[str, Any] = {"start": start, "end": end}
    if dept_ids:
        params["dept_ids"] = dept_ids
    df = pd.read_sql_query(sql, _engine, params=params)
    return df.iloc[0].to_dict()


@st.cache_data(ttl=300, show_spinner=False)
def billing_trend(_engine, start: date, end: date, dept_ids: list[int] | None) -> pd.DataFrame:
    sql = text(f"""
        SELECT DATE_TRUNC('month', d.full_date)::DATE AS month_start,
               SUM(b.total_amount) AS total_billing
          FROM dw.fact_billing b
          JOIN dw.dim_date d ON d.date_key = b.billing_date_key
          LEFT JOIN dw.dim_department dep ON dep.department_key = b.department_key
         WHERE d.full_date BETWEEN :start AND :end
         {_dept_clause(dept_ids)}
         GROUP BY 1 ORDER BY 1
    """)
    params: dict[str, Any] = {"start": start, "end": end}
    if dept_ids:
        params["dept_ids"] = dept_ids
    return pd.read_sql_query(sql, _engine, params=params)


@st.cache_data(ttl=300, show_spinner=False)
def billing_by_department(_engine, start: date, end: date) -> pd.DataFrame:
    sql = text("""
        SELECT COALESCE(dep.department_name, 'Không xác định') AS department_name,
               SUM(b.total_amount) AS total_billing,
               SUM(b.insurance_covered_amount) AS total_insurance_covered,
               SUM(b.patient_payable_amount) AS total_patient_payable
          FROM dw.fact_billing b
          JOIN dw.dim_date d ON d.date_key = b.billing_date_key
          LEFT JOIN dw.dim_department dep ON dep.department_key = b.department_key
         WHERE d.full_date BETWEEN :start AND :end
         GROUP BY dep.department_name
         ORDER BY total_billing DESC
    """)
    return pd.read_sql_query(sql, _engine, params={"start": start, "end": end})


@st.cache_data(ttl=300, show_spinner=False)
def billing_detail_composition(_engine, start: date, end: date) -> pd.DataFrame:
    """Descriptive mix by charge_type. Does NOT reconcile to fact_billing.total_amount
    (see billing_reconciliation) — use only to show relative composition, never absolute totals."""
    sql = text("""
        SELECT bd.charge_type,
               SUM(bd.amount) AS total_amount,
               COUNT(*) AS line_count
          FROM dw.fact_billing_detail bd
          JOIN dw.dim_date d ON d.date_key = bd.billing_date_key
         WHERE d.full_date BETWEEN :start AND :end
         GROUP BY bd.charge_type
         ORDER BY total_amount DESC
    """)
    return pd.read_sql_query(sql, _engine, params={"start": start, "end": end})


@st.cache_data(ttl=300, show_spinner=False)
def billing_reconciliation(_engine) -> dict[str, Any]:
    """Live evidence for the billing vs. billing_detail mismatch, computed from the
    currently loaded DW (not a hardcoded figure from a one-off analysis)."""
    sql = text("""
        WITH detail_sums AS (
            SELECT bill_id, SUM(amount) AS sum_detail
            FROM dw.fact_billing_detail
            GROUP BY bill_id
        )
        SELECT
            COUNT(*) AS total_bills,
            COUNT(*) FILTER (
                WHERE ABS(COALESCE(ds.sum_detail, 0) - b.total_amount) > 0.01
            ) AS mismatched_bills,
            CORR(b.total_amount, COALESCE(ds.sum_detail, 0)) AS correlation
        FROM dw.fact_billing b
        LEFT JOIN detail_sums ds ON ds.bill_id = b.bill_id
    """)
    df = pd.read_sql_query(sql, _engine)
    return df.iloc[0].to_dict()


@st.cache_data(ttl=300, show_spinner=False)
def drug_usage(_engine, start: date, end: date, top_n: int = 15) -> pd.DataFrame:
    """Prescriptions per drug, dated via the parent admission (fact_prescription has no date FK)."""
    sql = text("""
        SELECT dr.drug_name, COUNT(*) AS prescription_count
          FROM dw.fact_prescription p
          JOIN dw.dim_drug dr ON dr.drug_key = p.drug_key
          JOIN dw.fact_admission a ON a.admission_id = p.admission_id
          JOIN dw.dim_date d ON d.date_key = a.admission_date_key
         WHERE d.full_date BETWEEN :start AND :end
         GROUP BY dr.drug_name
         ORDER BY prescription_count DESC
         LIMIT :top_n
    """)
    return pd.read_sql_query(sql, _engine, params={"start": start, "end": end, "top_n": top_n})


@st.cache_data(ttl=300, show_spinner=False)
def diagnostic_by_category(_engine, start: date, end: date) -> pd.DataFrame:
    sql = text("""
        SELECT t.test_category, COUNT(*) AS diagnostic_count
          FROM dw.fact_diagnostic f
          JOIN dw.dim_diagnostic_test t ON t.test_key = f.test_key
          JOIN dw.dim_date d ON d.date_key = f.diagnostic_date_key
         WHERE d.full_date BETWEEN :start AND :end
         GROUP BY t.test_category
         ORDER BY diagnostic_count DESC
    """)
    return pd.read_sql_query(sql, _engine, params={"start": start, "end": end})


@st.cache_data(ttl=300, show_spinner=False)
def diagnostic_trend(_engine, start: date, end: date) -> pd.DataFrame:
    sql = text("""
        SELECT DATE_TRUNC('month', d.full_date)::DATE AS month_start, COUNT(*) AS diagnostic_count
          FROM dw.fact_diagnostic f
          JOIN dw.dim_date d ON d.date_key = f.diagnostic_date_key
         WHERE d.full_date BETWEEN :start AND :end
         GROUP BY 1 ORDER BY 1
    """)
    return pd.read_sql_query(sql, _engine, params={"start": start, "end": end})


@st.cache_data(ttl=600, show_spinner=False)
def low_stock_drugs() -> pd.DataFrame:
    """drug_inventory is not modeled in the DW yet, so read the processed CSVs directly."""
    data_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
    inventory = pd.read_csv(data_dir / "drug_inventory.csv")
    drug = pd.read_csv(data_dir / "drug.csv")[["drug_id", "drug_name", "drug_category"]]
    merged = inventory.merge(drug, on="drug_id", how="left")
    low = merged[merged["current_stock"] < merged["reorder_level"]].copy()
    low["shortfall"] = low["reorder_level"] - low["current_stock"]
    return low.sort_values("shortfall", ascending=False)[
        ["drug_name", "drug_category", "current_stock", "reorder_level", "shortfall"]
    ]
