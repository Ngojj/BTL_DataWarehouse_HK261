"""Shared sidebar filter widgets reused across dashboard pages."""
from __future__ import annotations

from datetime import date

import streamlit as st

import queries


def date_range_filter(engine) -> tuple[date, date]:
    min_date, max_date = queries.get_date_bounds(engine)
    selected = st.sidebar.date_input(
        "Khoảng thời gian",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected, tuple) and len(selected) == 2:
        start_date, end_date = selected
    else:
        start_date, end_date = min_date, max_date
    if start_date > end_date:
        st.sidebar.error("Ngày bắt đầu phải trước ngày kết thúc.")
        st.stop()
    return start_date, end_date


def department_filter(engine) -> list[int] | None:
    departments = queries.get_departments(engine)
    selected_names = st.sidebar.multiselect(
        "Khoa (để trống = tất cả)", options=departments["department_name"].tolist(), default=[]
    )
    if not selected_names:
        return None
    return departments.loc[
        departments["department_name"].isin(selected_names), "department_id"
    ].tolist()
