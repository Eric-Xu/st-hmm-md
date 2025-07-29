from typing import Dict, List, Set, Tuple

import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
from pycirclize import Circos
from pycirclize.parser import Matrix

from constants.css import GRAY_HEX, GREEN_HEX
from pipelines.prepare_loan_data import prep_data
from utils.gui import show_default_footer, show_st_h1, show_st_h2
from utils.io import load_json
from utils.lender import get_fromto_lenders_w_counts

MIN_BORROWER_CHURN_THRESHOLD = 1


def _create_chord_diagram(fromto_lenders_w_counts_df: pd.DataFrame) -> Figure:
    matrix = Matrix.parse_fromto_table(fromto_lenders_w_counts_df)

    # Dynamically set space to avoid exceeding 360 degrees
    n_sectors = len(fromto_lenders_w_counts_df)
    max_space = min(4, int(360 / max(1, n_sectors)))
    # Build cmap dict mapping each unique lender to GREEN_HEX
    segment_labels: Set = set(fromto_lenders_w_counts_df["from_lender"]).union(
        set(fromto_lenders_w_counts_df["to_lender"])
    )
    cmap = {label: GREEN_HEX for label in segment_labels}

    circos = Circos.chord_diagram(
        matrix,
        space=max_space,
        cmap=cmap,
        ticks_interval=2,
        label_kws=dict(alpha=0.0),  # Hide default sector.text()
        link_kws=dict(direction=1),
        ticks_kws=dict(outer=True, text_kws=dict(color=GRAY_HEX)),
    )

    # Create annotation labels to avoid overlapping texts.
    for sector in circos.sectors:
        for track in sector.tracks:
            label_pos = sector.center
            track.annotate(x=label_pos, label=sector.name, label_size=10, shorten=100)

    fig: Figure = circos.plotfig()

    return fig


def _get_chord_diagram_data(prepped_data: List[Dict]) -> pd.DataFrame:
    # Count occurrences of each (from_lender, to_lender) pair
    fromto_lenders_w_counts: List[Tuple[str, str, int]] = get_fromto_lenders_w_counts(
        prepped_data
    )

    # Remove records to reduce chart clutter
    fromto_lender_w_min_counts: List[Tuple[str, str, int]] = [
        row
        for row in fromto_lenders_w_counts
        if int(row[2]) > MIN_BORROWER_CHURN_THRESHOLD
    ]

    fromto_lenders_w_counts_df = pd.DataFrame(
        fromto_lender_w_min_counts,
        columns=["from_lender", "to_lender", "churned_borrower_cnt"],
    )

    return fromto_lenders_w_counts_df


def _show_chord_diagram(prepped_data: List[Dict]) -> None:
    fromto_lenders_w_counts_df: pd.DataFrame = _get_chord_diagram_data(prepped_data)

    chord_diagram: Figure = _create_chord_diagram(fromto_lenders_w_counts_df)

    st.pyplot(chord_diagram, use_container_width=True)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        TODO
        """
    )

    st.dataframe(fromto_lenders_w_counts_df)


def _show_introduction() -> None:
    st.write(
        """
        TODO: 
        - Change chord diagram segment color to indicate net change.
    """
    )


def render_page() -> None:
    show_st_h1("Lender Analysis")
    show_st_h2("Lender Appeal", w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.write("")
    _show_introduction()

    st.write("")
    st.write("")
    st.markdown("#### Where did churned borrowers go for new loans?")

    _show_chord_diagram(prepped_data)

    show_default_footer()


render_page()
