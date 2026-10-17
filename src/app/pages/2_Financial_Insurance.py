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

recon = queries.billing_reconciliation(engine)
mismatch_pct = (
    recon["mismatched_bills"] / recon["total_bills"] * 100 if recon["total_bills"] else 0
)
st.warning(
    f"Lưu ý chất lượng dữ liệu: {int(recon['mismatched_bills']):,}/{int(recon['total_bills']):,} hóa đơn "
    f"({mismatch_pct:.1f}%) có tổng `billing_detail.amount` không khớp `billing.total_amount`. "
    "Toàn bộ số liệu tổng/chi phí trên trang này dùng `fact_billing.total_amount` làm nguồn chính; "
    "`fact_billing_detail` chỉ dùng để xem cơ cấu theo loại khoản mục, không dùng để đối chiếu tổng.",
    icon="⚠️",
)
with st.expander("Vì sao có cảnh báo này? (bằng chứng, tính trực tiếp từ DB hiện tại)"):
    st.markdown(
        f"- Hệ số tương quan giữa `billing.total_amount` và tổng `billing_detail.amount` theo hóa đơn: "
        f"**{recon['correlation']:.4f}** (≈0 nghĩa là không có liên hệ thống kê — hai giá trị được "
        "sinh độc lập trong dữ liệu synthetic, không phải do làm tròn hay thiếu khoản mục).\n"
        f"- Không có công thức nào quy đổi lại cho khớp; đây là giới hạn của dữ liệu nguồn, không phải "
        "lỗi tính toán có thể sửa.\n"
        "- Vì vậy: dùng `fact_billing.total_amount` cho mọi KPI tổng; dùng `fact_billing_detail` "
        "chỉ cho câu hỏi \"cơ cấu chi phí theo loại khoản mục trông như thế nào\", không cho \"tổng là bao nhiêu\"."
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

st.subheader("Cơ cấu chi phí theo loại khoản mục")
st.caption(
    "Mô tả tỷ trọng theo `charge_type` từ `fact_billing_detail` — KHÔNG đối chiếu được với tổng "
    "chi phí ở trên (xem cảnh báo đầu trang)."
)
composition = queries.billing_detail_composition(engine, start_date, end_date)
if composition.empty:
    st.info("Không có dữ liệu trong khoảng thời gian đã chọn.")
else:
    fig_comp = px.pie(composition, names="charge_type", values="total_amount", hole=0.4)
    st.plotly_chart(fig_comp, width="stretch")
    st.dataframe(composition, width="stretch", hide_index=True)
