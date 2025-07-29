import hmac
import os
from pathlib import Path

import streamlit as st
from streamlit.navigation.page import StreamlitPage

from constants.file import (
    BORROWER_LENDERS_PAGE_FILE,
    BORROWER_LOANS_PAGE_FILE,
    BORROWER_TIMELINE_PAGE_FILE,
    CSS_DIR,
    CSS_FILE,
    LENDER_APPEAL_PAGE_FILE,
    LENDER_BORROWER_MIGRATION_PAGE_FILE,
    LENDER_CHURNED_BORROWERS_PAGE_FILE,
    LENDER_MARKET_SHARE_PAGE_FILE,
    LENDER_ORIGINATION_TIMELINE_PAGE_FILE,
    LENDER_REPEAT_BORROWERS_PAGE_FILE,
    LOAN_ANALYSIS_PAGE_FILE,
    MARKET_MONOPOLY_PAGE_FILE,
    PAGE_DIR,
)


def check_password():
    def password_entered():
        if hmac.compare_digest(
            st.session_state["password"], st.secrets["login_password"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        return True


def initialize_session_state() -> None:
    st.session_state["subj_prop_address"] = "123 Main St"


def load_css() -> None:
    current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
    css_file_path = os.path.join(current_dir, CSS_DIR, CSS_FILE)

    with open(css_file_path) as f:
        st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)


def setup_page_navigation() -> StreamlitPage:
    lender_market_share_page = st.Page(
        os.path.join(PAGE_DIR, LENDER_MARKET_SHARE_PAGE_FILE),
        title="Market Share",
        icon=":material/clock_loader_10:",
    )
    lender_churned_borrowers_page = st.Page(
        os.path.join(PAGE_DIR, LENDER_CHURNED_BORROWERS_PAGE_FILE),
        title="Churned Borrowers",
        icon=":material/person_cancel:",
    )
    lender_borrower_migration_page = st.Page(
        os.path.join(PAGE_DIR, LENDER_BORROWER_MIGRATION_PAGE_FILE),
        title="Borrower Migration",
        icon=":material/directions_walk:",
    )
    market_monopoly_page = st.Page(
        os.path.join(PAGE_DIR, MARKET_MONOPOLY_PAGE_FILE),
        title="Market Concentration",
        icon=":material/crown:",
    )

    pages = {
        "Lender Analysis": [
            lender_market_share_page,
            lender_churned_borrowers_page,
            lender_borrower_migration_page,
        ],
        "Market Analysis": [market_monopoly_page],
    }
    pg: StreamlitPage = st.navigation(pages)

    return pg
