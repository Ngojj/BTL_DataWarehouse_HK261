"""Pharmacy & Diagnostic dashboard page."""
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

st.title("Pharmacy & diagnostic", icon=":material/medication:")

try:
    engine = db.get_engine()
except RuntimeError as exc:
    st.error(str(exc), icon=":material/error:")
    st.stop()

st.sidebar.header("Bộ lọc", icon=":material/filter_list:")
start_date, end_date = filters.date_range_filter(engine)

col_a, col_b = st.columns(2)

with col_a:
    with st.container(border=True, height="stretch"):
        st.subheader("Top thuốc được kê nhiều nhất", icon=":material/medication:")
        usage = queries.drug_usage(engine, start_date, end_date, top_n=15)
        if usage.empty:
            st.caption("Không có dữ liệu trong khoảng thời gian đã chọn.")
        else:
            fig = px.bar(
                usage.sort_values("prescription_count"), x="prescription_count", y="drug_name", orientation="h"
            )
            fig.update_layout(xaxis_title="Số lần kê đơn", yaxis_title="Thuốc")
            st.plotly_chart(fig, width="stretch", alt="Top thuốc được kê nhiều nhất")

with col_b:
    with st.container(border=True, height="stretch"):
        st.subheader("Thuốc tồn kho thấp", icon=":material/inventory_2:")
        st.caption("Dưới mức `reorder_level`.")
        low_stock = queries.low_stock_drugs()
        if low_stock.empty:
            st.success("Không có thuốc nào dưới ngưỡng tồn kho tối thiểu.", icon=":material/check_circle:")
        else:
            st.dataframe(low_stock, width="stretch", hide_index=True, alt="Thuốc tồn kho thấp")

st.subheader("Thống kê hoạt động chẩn đoán", icon=":material/lab_research:")
col_c, col_d = st.columns(2)
with col_c:
    with st.container(border=True, height="stretch"):
        by_category = queries.diagnostic_by_category(engine, start_date, end_date)
        if by_category.empty:
            st.caption("Không có dữ liệu trong khoảng thời gian đã chọn.")
        else:
            fig_cat = px.bar(by_category, x="test_category", y="diagnostic_count")
            fig_cat.update_layout(xaxis_title="Loại xét nghiệm", yaxis_title="Số lượt")
            st.plotly_chart(fig_cat, width="stretch", alt="Hoạt động chẩn đoán theo loại")

with col_d:
    with st.container(border=True, height="stretch"):
        trend = queries.diagnostic_trend(engine, start_date, end_date)
        if trend.empty:
            st.caption("Không có dữ liệu trong khoảng thời gian đã chọn.")
        else:
            fig_trend = px.line(trend, x="month_start", y="diagnostic_count", markers=True)
            fig_trend.update_layout(xaxis_title="Tháng", yaxis_title="Số lượt chẩn đoán")
            st.plotly_chart(fig_trend, width="stretch", alt="Xu hướng hoạt động chẩn đoán theo tháng")
