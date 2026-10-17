"""Healthcare DW dashboard - entry point (Hospital Overview).

Run from the repo root:
    export DW_DSN='postgresql://postgres:MAT_KHAU@localhost:5432/healthcare_dw'
    streamlit run src/app/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import db  # noqa: E402
import filters  # noqa: E402
import queries  # noqa: E402

st.set_page_config(page_title="Healthcare DW Dashboard", layout="wide")
st.title("Hospital Overview")

try:
    engine = db.get_engine()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

st.sidebar.header("Bộ lọc")
start_date, end_date = filters.date_range_filter(engine)

kpis = queries.overview_kpis(engine, start_date, end_date)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Tổng lượt nhập viện", f"{int(kpis['total_admissions']):,}")
col2.metric("Tổng số bệnh nhân", f"{int(kpis['total_patients']):,}")
avg_los = kpis["avg_los"]
col3.metric("LOS trung bình (ngày)", f"{avg_los:.1f}" if avg_los is not None else "N/A")
col4.metric("Tổng chi phí", f"{float(kpis['total_billing']):,.0f}")
rate = kpis["latest_occupancy_rate"]
col5.metric("Công suất giường (mới nhất)", f"{float(rate) * 100:.1f}%" if rate is not None else "N/A")

st.subheader("Lượt nhập viện theo tháng")
trend = queries.admissions_by_month(engine, start_date, end_date)
if trend.empty:
    st.info("Không có dữ liệu trong khoảng thời gian đã chọn.")
else:
    fig = px.line(trend, x="month_start", y="admissions", markers=True)
    fig.update_layout(xaxis_title="Tháng", yaxis_title="Số lượt nhập viện")
    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Dữ liệu đọc trực tiếp từ schema `dw` trên PostgreSQL. "
    "Dùng menu Pages ở sidebar để xem Hospital Capacity, Financial & Insurance, "
    "Pharmacy & Diagnostic, DSS Alerts."
)
