"""Financial & Insurance dashboard page."""
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

st.set_page_config(page_title="Financial & Insurance", layout="wide")
st.title("Financial & Insurance")

try:
    engine = db.get_engine()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

st.sidebar.header("Bộ lọc")
start_date, end_date = filters.date_range_filter(engine)
dept_ids = filters.department_filter(engine)

st.info(
    "Lưu ý chất lượng dữ liệu: ~99,9% hóa đơn có tổng `billing_detail.amount` không khớp "
    "`billing.total_amount` (xem `docs/huong_dan_chay_tv3.md`). Các số liệu dưới đây dùng "
    "`fact_billing.total_amount` làm nguồn chính; không dùng `fact_billing_detail` để đối chiếu tổng.",
    icon="⚠️",
)

summary = queries.billing_summary(engine, start_date, end_date, dept_ids)

col1, col2, col3 = st.columns(3)
col1.metric("Tổng chi phí", f"{float(summary['total_billing']):,.0f}")
col2.metric("Bảo hiểm chi trả", f"{float(summary['total_insurance_covered']):,.0f}")
col3.metric("Bệnh nhân tự chi trả", f"{float(summary['total_patient_payable']):,.0f}")

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Chi phí theo thời gian")
    trend = queries.billing_trend(engine, start_date, end_date, dept_ids)
    if trend.empty:
        st.info("Không có dữ liệu trong khoảng thời gian đã chọn.")
    else:
        fig = px.line(trend, x="month_start", y="total_billing", markers=True)
        fig.update_layout(xaxis_title="Tháng", yaxis_title="Tổng chi phí")
        st.plotly_chart(fig, width="stretch")

with col_b:
    st.subheader("Bảo hiểm vs. bệnh nhân tự trả")
    pie_df = {
        "Nguồn chi trả": ["Bảo hiểm chi trả", "Bệnh nhân tự trả"],
        "Số tiền": [summary["total_insurance_covered"], summary["total_patient_payable"]],
    }
    fig_pie = px.pie(pie_df, names="Nguồn chi trả", values="Số tiền")
    st.plotly_chart(fig_pie, width="stretch")

st.subheader("Chi phí theo khoa")
by_dept = queries.billing_by_department(engine, start_date, end_date)
if by_dept.empty:
    st.info("Không có dữ liệu trong khoảng thời gian đã chọn.")
else:
    fig_dept = px.bar(by_dept, x="department_name", y="total_billing")
    fig_dept.update_layout(xaxis_title="Khoa", yaxis_title="Tổng chi phí")
    st.plotly_chart(fig_dept, width="stretch")
    st.dataframe(by_dept, width="stretch", hide_index=True)
