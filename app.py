import streamlit as st
import streamlit_analytics2 as streamlit_analytics
from streamlit.navigation.page import StreamlitPage

from utils.st_app import (
    check_password,
    initialize_session_state,
    load_css,
    setup_page_navigation,
)


class MultiApp:
    def __init__(self):
        load_css()

        initialize_session_state()

    def run(self):
        pg: StreamlitPage = setup_page_navigation()
        pg.run()


with streamlit_analytics.track(
    unsafe_password=st.secrets.get("st_analytics_password", "test123")
):
    app = MultiApp()

    # if not check_password():
    #     st.stop()

    app.run()
