"""Database connection helper for the Streamlit dashboard."""
from __future__ import annotations

import os

import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    """Build a cached SQLAlchemy engine from the DW_DSN environment variable."""
    dsn = os.getenv("DW_DSN")
    if not dsn:
        raise RuntimeError(
            "Chưa đặt biến môi trường DW_DSN. Ví dụ: "
            "export DW_DSN='postgresql://postgres:MAT_KHAU@localhost:5432/healthcare_dw'"
        )
    if dsn.startswith("postgresql://"):
        dsn = dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(dsn, pool_pre_ping=True)
