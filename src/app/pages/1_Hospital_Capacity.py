"""Hospital Capacity dashboard page: bed occupancy and admissions by department."""
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

st.set_page_config(page_title="Hospital Capacity", layout="wide")
st.title("Hospital Capacity")

try:
    engine = db.get_engine()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

st.sidebar.header("Bộ lọc")
start_date, end_date = filters.date_range_filter(engine)

ward_df = queries.bed_occupancy_by_ward(engine)

if ward_df.empty:
    st.warning("Chưa có dữ liệu `fact_bed_occupancy`. Hãy chạy loader trước (xem docs/huong_dan_chay_tv3.md).")
else:
    high_pressure = ward_df[ward_df["occupancy_rate"] >= 0.85]
    watch = ward_df[(ward_df["occupancy_rate"] >= 0.70) & (ward_df["occupancy_rate"] < 0.85)]

    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng số giường", f"{int(ward_df['capacity_beds'].sum()):,}")
    col2.metric("Giường đang dùng", f"{int(ward_df['occupied_beds'].sum()):,}")
    col3.metric("Khu vực áp lực cao (>=85%)", f"{len(high_pressure)}")

    if len(high_pressure):
        st.error("Áp lực công suất cao: " + ", ".join(high_pressure["ward_name"]))
    if len(watch):
        st.warning("Cần theo dõi (70-85%): " + ", ".join(watch["ward_name"]))

    st.subheader("Tỷ lệ lấp đầy giường theo khu (snapshot mới nhất)")
    fig = px.bar(
        ward_df, x="ward_name", y="occupancy_rate", color="occupancy_rate",
        color_continuous_scale=["#2ecc71", "#f1c40f", "#e74c3c"], range_color=[0, 1],
    )
    fig.update_layout(xaxis_title="Khu", yaxis_title="Tỷ lệ lấp đầy", yaxis_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Xu hướng tỷ lệ lấp đầy giường theo tháng")
trend = queries.occupancy_trend(engine, start_date, end_date)
if trend.empty:
    st.info("Không có dữ liệu trong khoảng thời gian đã chọn.")
else:
    fig2 = px.line(trend, x="month_start", y="occupancy_rate", markers=True)
    fig2.update_layout(yaxis_tickformat=".0%", xaxis_title="Tháng", yaxis_title="Tỷ lệ lấp đầy")
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Lượt nhập viện & LOS trung bình theo khoa")
dept_df = queries.admissions_by_department(engine, start_date, end_date)
if dept_df.empty:
    st.info("Không có dữ liệu trong khoảng thời gian đã chọn.")
else:
    fig3 = px.bar(dept_df, x="department_name", y="admissions")
    fig3.update_layout(xaxis_title="Khoa", yaxis_title="Số lượt nhập viện")
    st.plotly_chart(fig3, use_container_width=True)
    st.dataframe(dept_df, use_container_width=True, hide_index=True)
