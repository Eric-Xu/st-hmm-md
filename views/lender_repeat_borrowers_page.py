from typing import Dict, List, Set

import altair as alt
import pandas as pd
import streamlit as st

from constants.css import GRAY_HEX, GREEN_HEX
from pipelines.prepare_loan_data import prep_data
from utils.borrower import get_borrower_to_lender_num_loans, get_borrower_to_volume
from utils.gui import show_default_footer, show_st_h1, show_st_h2
from utils.io import load_json
from utils.lender import get_lender_to_repeat_borrowers

HIDE_SCATTERPLOT_LINE_THRESHOLD = 10


def _create_scatterplot(chart_data: pd.DataFrame) -> alt.LayerChart:
    scatter = (
        alt.Chart(chart_data)
        .mark_circle(size=120, color=GREEN_HEX, opacity=0.8)
        .encode(
            x=alt.X("lender_num_loans", title="Number of Loans"),
            y=alt.Y("num_repeat_borrowers", title="Number of Repeat Borrowers"),
            tooltip=[
                alt.Tooltip("lender", title="Lender"),
                alt.Tooltip("lender_num_loans", title="# Loans"),
                alt.Tooltip("num_repeat_borrowers", title="# Repeat Borrowers"),
            ],
        )
        .properties(width="container")
    )
    if len(chart_data) > HIDE_SCATTERPLOT_LINE_THRESHOLD:
        line = (
            alt.Chart(chart_data)
            .transform_regression("lender_num_loans", "num_repeat_borrowers")
            .mark_line(color=GRAY_HEX)
            .encode(x="lender_num_loans", y="num_repeat_borrowers")
        )
        chart = alt.layer(line, scatter)
    else:
        chart = alt.layer(scatter)

    chart = chart.properties(
        title={
            "text": "Comparison of Repeat Borrowers Among Lenders",
            "anchor": "middle",
        }
    )

    return chart


def _get_df_data(prepped_data: List[Dict], lender: str) -> List[Dict]:
    borrower_to_total_volume: Dict[str, int] = get_borrower_to_volume(prepped_data)
    borrower_to_lender_num_loans: Dict[str, int] = get_borrower_to_lender_num_loans(
        prepped_data, lender
    )
    lender_to_repeat_borrowers: Dict[str, Set[str]] = get_lender_to_repeat_borrowers(
        prepped_data
    )
    repeat_borrowers: Set[str] = lender_to_repeat_borrowers.get(lender, set())

    records: List[Dict] = []
    for record in prepped_data:
        if record.get("lenderName", "") == lender:
            borrower = record.get("buyerName")
            if not isinstance(borrower, str):
                continue

            row = {
                "borrower_num_loans_w_lender": borrower_to_lender_num_loans.get(
                    borrower, 0
                ),
                "borrower_num_loans": record.get("borrower_num_loans"),
                "buyerName": borrower,
                "is_repeat": "Yes" if borrower in repeat_borrowers else "",
                "total_volume": borrower_to_total_volume.get(borrower, 0),
            }
            records.append(row)

    return records


def _get_scatterplot_data(prepped_data: List[Dict]) -> pd.DataFrame:
    """
    Returns a DataFrame with columns: lender, lender_num_loans, num_repeat_borrowers
    for use in the repeat borrowers scatter plot.
    """
    lender_points = []
    lender_to_repeat_borrowers: Dict[str, Set[str]] = get_lender_to_repeat_borrowers(
        prepped_data
    )
    for lender, repeat_borrowers in lender_to_repeat_borrowers.items():
        # Find a record for this lender to get lender_num_loans
        lender_records = [
            rec for rec in prepped_data if rec.get("lenderName") == lender
        ]
        if not lender_records:
            continue
        try:
            lender_num_loans = lender_records[0].get("lender_num_loans")
        except (TypeError, ValueError):
            lender_num_loans = None
        y_val = len(repeat_borrowers)
        if lender_num_loans is not None:
            lender_points.append(
                {
                    "lender": lender,
                    "lender_num_loans": lender_num_loans,
                    "num_repeat_borrowers": y_val,
                }
            )

    return pd.DataFrame(lender_points)


def _show_df(prepped_data: List[Dict], lender: str) -> None:
    records: List[Dict] = _get_df_data(prepped_data, lender)

    if not records:
        return

    column_order = [
        "buyerName",
        "borrower_num_loans_w_lender",
        "borrower_num_loans",
        "total_volume",
        "is_repeat",
    ]
    df = pd.DataFrame(records)[column_order].drop_duplicates().reset_index(drop=True)

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "borrower_num_loans_w_lender": st.column_config.NumberColumn(
                "Lender # Loans"
            ),
            "borrower_num_loans": st.column_config.NumberColumn("Total # Loans"),
            "buyerName": st.column_config.TextColumn("Borrower Name"),
            "is_repeat": st.column_config.TextColumn("Is Repeat"),
            "total_volume": st.column_config.NumberColumn(
                "Total Loan Volume", format="dollar"
            ),
        },
    )


def _show_introduction() -> None:
    st.write(
        """
        A "repeat borrower" is defined as someone who has taken out at least two loans from the same lender.
        """
    )


def _show_metrics_selected_data(prepped_data: List[Dict], lender: str) -> None:
    # Get all unique borrowers for this lender
    all_borrowers = set(
        d.get("buyerName")
        for d in prepped_data
        if d.get("lenderName") == lender and d.get("buyerName")
    )
    num_all_borrowers: int = len(all_borrowers)

    lender_to_repeat_borrowers: Dict[str, Set[str]] = get_lender_to_repeat_borrowers(
        prepped_data
    )
    repeat_borrowers = lender_to_repeat_borrowers.get(lender, set())
    num_repeat_borrowers: int = len(repeat_borrowers)
    repeat_borrower_pct: float = (
        (num_repeat_borrowers / num_all_borrowers) * 100
        if num_all_borrowers > 0
        else 0.0
    )

    col1, col2 = st.columns(2)
    col1.metric(
        "Repeat Borrowers", f"{num_repeat_borrowers}/{num_all_borrowers}", border=True
    )
    col2.metric("Repeat Borrower Pct", f"{round(repeat_borrower_pct, 1)}%", border=True)


def _show_scatterplot(prepped_data: List[Dict]) -> None:
    """
    Scatterplot of "num repeat borrowers" to "lender num loans").
    """
    chart_data: pd.DataFrame = _get_scatterplot_data(prepped_data)
    if chart_data.empty:
        st.warning("Not enough data to display chart.", icon=":material/warning:")
        return

    scatterplot: alt.LayerChart = _create_scatterplot(chart_data)
    st.altair_chart(scatterplot, use_container_width=True)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        Each point represents a lender, with its position corresponding to the total number of loans originated on the X-axis and the number of repeat borrowers on the Y-axis. For datasets with 10 or more points, a line of best fit is also shown. The farther a point lies above the line, the higher the repeat borrower rate relative to other lenders, and vice versa.
        """
    )


def _show_selectbox(prepped_data: List[Dict]) -> str:
    lenders = sorted(
        set(d.get("lenderName", "") for d in prepped_data if d.get("lenderName", ""))
    )
    option: str = st.selectbox(
        "Enter a lender’s name to view their repeat borrowers, if any.",
        lenders,
    )

    return option


def render_page() -> None:
    show_st_h1("Lender Analysis")
    show_st_h2("Repeat Borrowers", w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.write("")
    _show_introduction()

    st.write("")
    st.write("")
    _show_scatterplot(prepped_data)

    st.write("")
    st.write("")
    selected_lender: str = _show_selectbox(prepped_data)

    st.write("")
    st.write("")
    _show_metrics_selected_data(prepped_data, selected_lender)

    st.write("")
    _show_df(prepped_data, selected_lender)

    show_default_footer()


render_page()
