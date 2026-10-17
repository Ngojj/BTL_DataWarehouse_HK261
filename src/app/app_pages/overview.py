"""Hospital overview page."""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import db  # noqa: E402
import filters  # noqa: E402
import queries  # noqa: E402

st.title("Hospital overview", icon=":material/local_hospital:")

try:
    engine = db.get_engine()
except RuntimeError as exc:
    st.error(str(exc), icon=":material/error:")
    st.stop()

st.sidebar.header("Bộ lọc", icon=":material/filter_list:")
start_date, end_date = filters.date_range_filter(engine)

kpis = queries.overview_kpis(engine, start_date, end_date)
avg_los = kpis["avg_los"]
rate = kpis["latest_occupancy_rate"]

with st.container(horizontal=True):
    st.metric("Tổng lượt nhập viện", f"{int(kpis['total_admissions']):,}", border=True)
    st.metric("Tổng số bệnh nhân", f"{int(kpis['total_patients']):,}", border=True)
    st.metric(
        "LOS trung bình (ngày)",
        f"{avg_los:.1f}" if avg_los is not None else "N/A",
        border=True,
    )
    st.metric("Tổng chi phí", f"{float(kpis['total_billing']):,.0f}", border=True)
    st.metric(
        "Công suất giường (mới nhất)",
        f"{float(rate) * 100:.1f}%" if rate is not None else "N/A",
        border=True,
    )

with st.container(border=True):
    st.subheader("Lượt nhập viện theo tháng", icon=":material/show_chart:")
    trend = queries.admissions_by_month(engine, start_date, end_date)
    if trend.empty:
        st.caption("Không có dữ liệu trong khoảng thời gian đã chọn.")
    else:
        fig = px.line(trend, x="month_start", y="admissions", markers=True)
        fig.update_layout(xaxis_title="Tháng", yaxis_title="Số lượt nhập viện")
        st.plotly_chart(fig, width="stretch", alt="Lượt nhập viện theo tháng")

st.caption("Dữ liệu đọc trực tiếp từ schema `dw` trên PostgreSQL.")
