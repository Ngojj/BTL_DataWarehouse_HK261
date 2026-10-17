"""DSS Alerts dashboard page.

Reuses src/dss/engine.py (TV3) for the actual alert logic instead of
duplicating SQL here. That module currently lives on the `TV3` branch; once
merged into the branch this app runs from, this page lights up automatically.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

st.title("DSS alerts", icon=":material/warning:")

try:
    from src.dss import build_dss_report
except ImportError:
    st.warning(
        "Chưa có module `src/dss` trên nhánh hiện tại (phần việc của TV3, nhánh `TV3` trên remote). "
        "Merge nhánh đó vào đây để bật trang này: `git merge origin/TV3`.",
        icon=":material/hourglass_empty:",
    )
    st.stop()

import os  # noqa: E402

import psycopg  # noqa: E402

dsn = os.getenv("DW_DSN")
if not dsn:
    st.error(
        "Chưa đặt biến môi trường DW_DSN. Ví dụ: "
        "export DW_DSN='postgresql://postgres:MAT_KHAU@localhost:5432/healthcare_dw'",
        icon=":material/error:",
    )
    st.stop()

lookback_days = st.sidebar.slider("Cửa sổ xét nhập viện/LOS gần nhất (ngày)", 7, 90, 30)

with psycopg.connect(dsn) as connection:
    report = build_dss_report(connection, lookback_days=lookback_days)

with st.container(border=True):
    st.subheader("Cảnh báo công suất giường theo khu", icon=":material/bed:")
    bed_df = pd.DataFrame(report["bed_occupancy_alerts"])
    if bed_df.empty:
        st.caption("Không có dữ liệu công suất giường.")
    else:
        level_order = {"HIGH_PRESSURE": 0, "WATCH": 1, "NORMAL": 2, "NO_CAPACITY_DATA": 3}
        bed_df["_order"] = bed_df["alert_level"].map(level_order)
        bed_df = bed_df.sort_values("_order").drop(columns="_order")

        def _highlight(row):
            color = {"HIGH_PRESSURE": "#f8d7da", "WATCH": "#fff3cd", "NORMAL": "#d4edda"}.get(row["alert_level"], "")
            return [f"background-color: {color}"] * len(row)

        st.dataframe(
            bed_df.style.apply(_highlight, axis=1), width="stretch", hide_index=True,
            alt="Cảnh báo công suất giường theo khu",
        )

with st.container(border=True):
    st.subheader("Cảnh báo tồn kho thuốc thấp", icon=":material/inventory_2:")
    stock_df = pd.DataFrame(report["low_stock_alerts"])
    if stock_df.empty:
        st.success("Không có thuốc nào dưới ngưỡng tồn kho tối thiểu.", icon=":material/check_circle:")
    else:
        st.dataframe(stock_df, width="stretch", hide_index=True, alt="Cảnh báo tồn kho thuốc thấp")

with st.container(border=True):
    st.subheader("Khu vực cần chú ý", icon=":material/visibility:")
    st.caption(report["notes"]["area_attention_rule"])
    area_df = pd.DataFrame(report["area_attention"])
    if area_df.empty:
        st.caption("Không có dữ liệu.")
    else:
        flagged = area_df[area_df["attention_flag"]]
        st.dataframe(
            area_df[["ward_name", "occupancy_rate", "admissions_in_window", "avg_length_of_stay_days",
                     "staff_assignments", "attention_score", "reasons"]],
            width="stretch", hide_index=True, alt="Khu vực cần chú ý",
        )
        if len(flagged):
            st.warning("Khu vực được gắn cờ: " + ", ".join(flagged["ward_name"]), icon=":material/flag:")
