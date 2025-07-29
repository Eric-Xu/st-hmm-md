from typing import Dict, List, Set

import altair as alt
import pandas as pd
import streamlit as st

from constants.css import GRAY_HEX, RED_HEX
from pipelines.prepare_loan_data import prep_data
from utils.borrower import (
    get_borrower_to_last_lender,
    get_borrower_to_lender_num_loans,
    get_borrower_to_lenders,
    get_borrower_to_volume,
)
from utils.gui import show_default_footer, show_st_h1, show_st_h2
from utils.io import load_json
from utils.lender import (
    get_borrower_to_last_lender,
    get_lender_to_borrowers,
    get_lender_to_lost_borrowers,
)

HIDE_SCATTERPLOT_LINE_THRESHOLD = 10


def _create_scatterplot(chart_data: pd.DataFrame) -> alt.LayerChart:
    scatter = (
        alt.Chart(chart_data)
        .mark_circle(size=120, color=RED_HEX, opacity=0.8)
        .encode(
            x=alt.X("lender_num_loans", title="Number of Loans"),
            y=alt.Y("num_churned_borrowers", title="Number of Churned Borrowers"),
            tooltip=[
                alt.Tooltip("lender", title="Lender"),
                alt.Tooltip("lender_num_loans", title="# Loans"),
                alt.Tooltip("num_churned_borrowers", title="# Churned Borrowers"),
            ],
        )
        .properties(width="container")
    )
    if len(chart_data) > HIDE_SCATTERPLOT_LINE_THRESHOLD:
        line = (
            alt.Chart(chart_data)
            .transform_regression("lender_num_loans", "num_churned_borrowers")
            .mark_line(color=GRAY_HEX)
            .encode(x="lender_num_loans", y="num_churned_borrowers")
        )
        chart = alt.layer(line, scatter)
    else:
        chart = alt.layer(scatter)

    chart = chart.properties(
        title={
            "text": "Comparison of Borrower Churn Among Lenders",
            "anchor": "middle",
        }
    )

    return chart


def _get_df_data(prepped_data: List[Dict], lender: str) -> List[Dict]:
    borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(prepped_data)
    borrower_to_all_lenders: Dict[str, Set[str]] = get_borrower_to_lenders(prepped_data)
    borrower_to_total_volume: Dict[str, int] = get_borrower_to_volume(prepped_data)
    borrower_to_lender_num_loans: Dict[str, int] = get_borrower_to_lender_num_loans(
        prepped_data, lender
    )

    records: List[Dict] = []
    for record in prepped_data:
        if record.get("lenderName", "") == lender:
            borrower = record.get("buyerName")
            if not isinstance(borrower, str):
                continue

            all_lenders = borrower_to_all_lenders.get(borrower, set())
            last_lender = borrower_to_last_lender.get(borrower, "")

            row = {
                "all_lenders": " | ".join([str(l) for l in all_lenders]),
                "borrower_num_loans_w_lender": borrower_to_lender_num_loans.get(
                    borrower, 0
                ),
                "borrower_num_loans": record.get("borrower_num_loans"),
                "buyerName": borrower,
                "has_churned": "Yes" if last_lender != lender else "",
                "last_lender": borrower_to_last_lender.get(borrower, ""),
                "total_volume": borrower_to_total_volume.get(borrower, 0),
            }
            records.append(row)

    return records


def _get_scatterplot_data(
    prepped_data: List[Dict], lender_to_churned_borrowers: Dict[str, Set[str]]
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns: lender, lender_num_loans, num_churned_borrowers
    for use in the churn scatter plot.
    """
    lender_points = []
    for lender, churned_borrowers in lender_to_churned_borrowers.items():
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
        y_val = len(churned_borrowers)
        if lender_num_loans is not None:
            lender_points.append(
                {
                    "lender": lender,
                    "lender_num_loans": lender_num_loans,
                    "num_churned_borrowers": y_val,
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
        "has_churned",
        "last_lender",
        "all_lenders",
    ]
    df = pd.DataFrame(records)[column_order].drop_duplicates().reset_index(drop=True)

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "all_lenders": st.column_config.TextColumn("Lenders Used"),
            "borrower_num_loans_w_lender": st.column_config.NumberColumn(
                "Lender # Loans"
            ),
            "borrower_num_loans": st.column_config.NumberColumn("Total # Loans"),
            "buyerName": st.column_config.TextColumn("Borrower Name"),
            "has_churned": st.column_config.TextColumn("Has Churned"),
            "last_lender": st.column_config.TextColumn("Last Lender"),
            "total_volume": st.column_config.NumberColumn(
                "Total Loan Volume", format="dollar"
            ),
        },
    )


def _show_introduction() -> None:
    st.write(
        """
        A "churned borrower" is defined as someone who previously received one or
        more loans from the lender but has not returned for additional financing 
        on their latest project.
    """
    )


def _show_metrics_selected_data(prepped_data: List[Dict], lender: str) -> None:
    selected_data: List[Dict] = [
        d for d in prepped_data if d.get("lenderName", "") == lender
    ]
    if not selected_data:
        return

    lender_to_all_borrowers: Dict[str, Set[str]] = get_lender_to_borrowers(prepped_data)
    lender_to_churned_borrowers: Dict[str, Set[str]] = get_lender_to_lost_borrowers(
        prepped_data
    )
    all_borrowers = set(lender_to_all_borrowers.get(lender, []))
    churned_borrowers = set(lender_to_churned_borrowers.get(lender, []))
    num_all_borrowers = len(all_borrowers)
    num_churned_borrowers = len(churned_borrowers)
    churn_rate = (
        (num_churned_borrowers / num_all_borrowers) * 100
        if num_all_borrowers > 0
        else 0
    )

    col1, col2 = st.columns(2)
    col1.metric(
        "Churned Borrowers", f"{num_churned_borrowers}/{num_all_borrowers}", border=True
    )
    col2.metric("Churn Rate", f"{round(churn_rate, 1)}%", border=True)


def _show_scatterplot(prepped_data: List[Dict]) -> None:
    """
    Recently churned borrowers (scatterplot of "num recently churned" to "lender num loans").
        - Given a lender, list any recently churned borrowers (last loan went to a different lender)
    """
    lender_to_churned_borrowers: Dict[str, Set[str]] = get_lender_to_lost_borrowers(
        prepped_data
    )

    # Prepare data for scatter plot: x = lender_num_loans, y = number of churned borrowers
    chart_data: pd.DataFrame = _get_scatterplot_data(
        prepped_data, lender_to_churned_borrowers
    )
    if chart_data.empty:
        st.warning("Not enough data to display chart.", icon=":material/warning:")
        return

    scatterplot: alt.LayerChart = _create_scatterplot(chart_data)
    st.altair_chart(scatterplot, use_container_width=True)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        Each point represents a lender, with its position corresponding to the 
        total number of loans originated on the X-axis and the number of borrowers
        who have churned on the Y-axis. For datasets with 10 or more points, a 
        line of best fit is also shown. The farther a point lies above the line, 
        the higher the churn rate relative to other lenders, and vice versa.
        """
    )


def _show_selectbox(prepped_data: List[Dict]) -> str:
    lenders = sorted(
        set(d.get("lenderName", "") for d in prepped_data if d.get("lenderName", ""))
    )
    option: str = st.selectbox(
        "Enter a lender’s name to view their churned borrowers, if any.",
        lenders,
    )

    return option


def render_page() -> None:
    show_st_h1("Lender Analysis")
    show_st_h2("Churned Borrowers", w_divider=True)

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
