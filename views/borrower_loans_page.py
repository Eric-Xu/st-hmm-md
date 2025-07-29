from typing import Dict, List

import pandas as pd
import streamlit as st

from constants.dataset import END_DATE, LOCATION, START_DATE
from pipelines.prepare_loan_data import prep_data
from utils.formatting import to_currency
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json
from utils.party2loan_rel_net_graph import show_relationship_network_graph


def _get_selected_data(prepped_data: List[Dict], slider_data: Dict) -> List[Dict]:
    user_min_num_loans: int = slider_data["user_min_num_loans"]
    user_max_num_loans: int = slider_data["user_max_num_loans"]

    selected_data: List[Dict] = list()
    for borrower_activity in prepped_data:
        num_loans: int = borrower_activity.get("borrower_num_loans", 0)
        if num_loans >= user_min_num_loans and num_loans <= user_max_num_loans:
            selected_data.append(borrower_activity)

    return selected_data


def _show_df(selected_data: List[Dict]) -> None:
    if selected_data:
        df = pd.DataFrame(selected_data)

        columns_to_keep = ["buyerName", "lenderName", "loanAmount"]
        df = df[columns_to_keep]
        df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")

        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "buyerName": st.column_config.TextColumn(
                    "Borrower Name", width="medium"
                ),
                "lenderName": st.column_config.TextColumn(
                    "Lender Name", width="medium"
                ),
                "loanAmount": st.column_config.NumberColumn(
                    "Loan Amount", width="small", format="dollar"
                ),
            },
        )
    else:
        st.info("No borrower activity data available.")


def _show_introduction(df: pd.DataFrame) -> None:
    top_n = 3
    min_num_loans = 3

    # Top by number of loans (no filter)
    top_count_series = (
        df.groupby("buyerName")["loanAmount"]
        .count()
        .sort_values(ascending=False)
        .head(top_n)
    )
    top_count = top_count_series.index.tolist()
    top_count_loans = top_count_series.values.tolist()

    # Top by average loan amount (filter to borrowers with at least min_num_loans loans)
    filtered_df = df[df["borrower_num_loans"] >= min_num_loans]
    grouped = (
        filtered_df.groupby("buyerName")
        .agg(avg_loan_amount=("loanAmount", "mean"), num_loans=("loanAmount", "count"))
        .sort_values("avg_loan_amount", ascending=False)
        .head(top_n)
    )
    top_avg = grouped.index.tolist()
    top_avg_loans = grouped["avg_loan_amount"].tolist()
    top_avg_num_loans = grouped["num_loans"].tolist()

    st.markdown(
        f"""
        View all business purpose loans used to purchase properties in {LOCATION}. 
        Discover the most active borrowers and examine their purchase activity 
        by both volume and loan size.

        The top {top_n} borrowers based on the **number of loans** are:
        
        1. {f'{top_count[0]} ({top_count_loans[0]} loans)' if len(top_count) > 0 else ''}
        1. {f'{top_count[1]} ({top_count_loans[1]} loans)' if len(top_count) > 1 else ''}
        1. {f'{top_count[2]} ({top_count_loans[2]} loans)' if len(top_count) > 2 else ''}

        The top {top_n} borrowers (with at least {min_num_loans} loans) ranked 
        by their **average loan amount** are:
        
        1. {f'{top_avg[0]} ({to_currency(top_avg_loans[0])} for {top_avg_num_loans[0]} loans)' if len(top_avg) > 0 else ''}
        1. {f'{top_avg[1]} ({to_currency(top_avg_loans[1])} for {top_avg_num_loans[1]} loans)' if len(top_avg) > 1 else ''}
        1. {f'{top_avg[2]} ({to_currency(top_avg_loans[2])} for {top_avg_num_loans[2]} loans)' if len(top_avg) > 2 else ''}

        To get started, adjust the slider below to filter borrowers by the 
        number of properties they have purchased with loans.
        """
    )


def _show_metrics_all_data(df: pd.DataFrame) -> None:
    total_borrowers: int = df["buyerName"].nunique()
    avg_loan_amount: float = df["loanAmount"].mean()
    max_loan_count: int = df.groupby("buyerName")["loanAmount"].count().max()

    st.write("")
    st.write("")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Borrowers", total_borrowers, border=True)
    col2.metric("Highest # of Loans", max_loan_count, border=True)
    col3.metric("Average Loan Amount", to_currency(avg_loan_amount), border=True)


def _show_metrics_selected_data(selected_data: List[Dict]) -> None:
    num_borrowers: int = len(set(d.get("buyerName", "") for d in selected_data))
    if num_borrowers == 0:
        avg_loans_per_borrower = 0
        avg_loan_amount = 0
    else:
        avg_loans_per_borrower = len(selected_data) / num_borrowers
        loan_amounts = [
            float(d.get("loanAmount", 0))
            for d in selected_data
            if d.get("loanAmount") not in (None, "", "N/A")
        ]
        avg_loan_amount = sum(loan_amounts) / len(loan_amounts) if loan_amounts else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Selected Borrowers", f"{num_borrowers}")
    col2.metric("Average # of Loans", f"{int(round(avg_loans_per_borrower))}")
    col3.metric("Average Loan Amount", to_currency(int(avg_loan_amount)))


def _show_network_graph(selected_data: List[Dict]) -> None:
    party = "borrower"
    show_relationship_network_graph(party, selected_data)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        Yellow represents {party}s, and green represents loans. 
        Shape sizes are proportional to loan values. 
        Arrows connect each {party} to their respective loans.
        """
    )


def _show_slider_loans_per_borrower(prepped_data: List[Dict]) -> Dict:
    if prepped_data:
        max_num_loans: int = max(
            item.get("borrower_num_loans", 0) for item in prepped_data
        )
    else:
        max_num_loans = 0

    # Use a tiered filter to improve rendering speed
    if max_num_loans > 40:
        offset = int(max_num_loans / 10)
        slider_min = offset
        slider_max = max_num_loans
        value_min = offset * 2
        value_max = offset * 4
    elif max_num_loans > 10:
        offset = int(max_num_loans / 10)
        slider_min = offset
        slider_max = max_num_loans
        value_min = offset * 2
        value_max = 10
    else:
        slider_min = 1
        slider_max = max_num_loans + 1
        value_min = slider_min + 1
        value_max = max_num_loans + 1

    user_min_num_loans, user_max_num_loans = st.slider(
        "**Select borrowers by adjusting the range for the number of loans per borrower.**",
        min_value=slider_min,
        max_value=slider_max,
        value=(value_min, value_max),
        step=1,
    )

    slider_data: Dict = {
        "user_min_num_loans": user_min_num_loans,
        "user_max_num_loans": user_max_num_loans,
    }
    return slider_data


def render_page():
    show_st_h1("Borrower Analysis")
    show_st_h2(LOCATION, w_divider=True)  # Borrower Marketshare?

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    df = pd.DataFrame(prepped_data)
    df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")

    st.write("")
    _show_introduction(df)

    _show_metrics_all_data(df)

    st.write("")
    st.markdown("#### Loans Per Borrower")

    slider_data: Dict = _show_slider_loans_per_borrower(prepped_data)

    selected_data: List[Dict] = _get_selected_data(prepped_data, slider_data)

    st.write("")
    _show_df(selected_data)

    st.write("")
    st.write("")
    _show_metrics_selected_data(selected_data)

    st.write("")
    _show_network_graph(selected_data)


render_page()
