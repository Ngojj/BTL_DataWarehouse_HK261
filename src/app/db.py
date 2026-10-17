"""Database connection helper for the Streamlit dashboard."""
from __future__ import annotations

import os

import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    """Build a cached SQLAlchemy engine from DW_DSN.

    Checks the DW_DSN environment variable first (local dev, scripts/load_facts.py,
    src/dss CLI), then falls back to st.secrets["DW_DSN"] (Streamlit Community Cloud,
    where secrets are configured in the app's Settings UI, not as env vars).
    """
    dsn = os.getenv("DW_DSN")
    if not dsn:
        try:
            dsn = st.secrets.get("DW_DSN")
        except FileNotFoundError:
            dsn = None
    if not dsn:
        raise RuntimeError(
            "Chưa cấu hình DW_DSN. Local: đặt biến môi trường, ví dụ "
            "export DW_DSN='postgresql://postgres:MAT_KHAU@localhost:5432/healthcare_dw'. "
            "Trên Streamlit Community Cloud: thêm DW_DSN vào App settings → Secrets."
        )
    if dsn.startswith("postgresql://"):
        dsn = dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(dsn, pool_pre_ping=True)
