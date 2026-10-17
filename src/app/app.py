"""Healthcare DW dashboard - entry point / router.

Run from the repo root:
    export DW_DSN='postgresql://postgres:MAT_KHAU@localhost:5432/healthcare_dw'
    streamlit run src/app/app.py
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Healthcare DW Dashboard",
    page_icon=":material/local_hospital:",
    layout="wide",
)

pg = st.navigation(
    [
        st.Page(
            "app_pages/overview.py",
            title="Hospital overview",
            icon=":material/local_hospital:",
            default=True,
        ),
        st.Page(
            "app_pages/hospital_capacity.py",
            title="Hospital capacity",
            icon=":material/bed:",
        ),
        st.Page(
            "app_pages/financial_insurance.py",
            title="Financial & insurance",
            icon=":material/payments:",
        ),
        st.Page(
            "app_pages/pharmacy_diagnostic.py",
            title="Pharmacy & diagnostic",
            icon=":material/medication:",
        ),
        st.Page(
            "app_pages/dss_alerts.py",
            title="DSS alerts",
            icon=":material/warning:",
        ),
    ]
)
pg.run()
