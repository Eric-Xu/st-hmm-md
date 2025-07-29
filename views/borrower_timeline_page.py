from collections import Counter, defaultdict
from typing import Dict, List

import pandas as pd
import streamlit as st

from pipelines.prepare_loan_data import prep_data
from utils.formatting import to_currency
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json
from utils.party2loan_timeline_net_graph import (
    get_timeline_network_graph_nodes_edges,
    show_timeline_network_graph,
)


def _count_repeat_lenders(selected_data: List[Dict]) -> int:
    """
    Returns the number of lenders who have taken out more than one loan (repeat lenders).
    """
    lender_names = [d.get("lenderName") for d in selected_data if d.get("lenderName")]
    counts = Counter(lender_names)
    repeat_lenders = [name for name, count in counts.items() if count > 1]

    return len(repeat_lenders)


def _get_selected_data(prepped_data: List[Dict], borrower: str) -> List[Dict]:
    return [d for d in prepped_data if d.get("buyerName", "") == borrower]


def _get_top_borrowers_by_repeat_lender_pct(
    prepped_data: List[Dict], min_num_loans, top_n: int = 5
) -> list[tuple[str, float, str, int, int]]:
    """
    Returns a list of tuples:
        (borrower_name, max_lender_pct, max_lender_name, num_loans_from_max_lender, num_loans)
    for the top_n borrowers by the highest percentage of loans from a single lender.
    Only considers borrowers with more than min_num_loans.
    """
    # Group all records by borrower
    borrower_to_records = defaultdict(list)
    for d in prepped_data:
        borrower = d.get("buyerName")
        if borrower:
            borrower_to_records[borrower].append(d)

    results = []
    for borrower, records in borrower_to_records.items():
        num_loans = len(records)
        if num_loans < min_num_loans:
            continue
        lender_counts = Counter(
            d.get("lenderName") for d in records if d.get("lenderName")
        )
        if not lender_counts:
            continue
        max_lender_name, max_lender_count = lender_counts.most_common(1)[0]
        max_lender_pct = (max_lender_count / num_loans) * 100 if num_loans > 0 else 0
        results.append(
            (borrower, max_lender_pct, max_lender_name, max_lender_count, num_loans)
        )

    # Sort by highest single-lender percentage, descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_n]


def _show_df(selected_data: List[Dict]) -> None:
    if not selected_data:
        return

    df = pd.DataFrame(selected_data)

    columns_to_keep = ["saleDate", "lenderName", "loanAmount"]
    df = df[columns_to_keep]
    df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")
    df = df.sort_values("saleDate", ascending=False).reset_index(drop=True)

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "saleDate": st.column_config.TextColumn("Sale Date", width="small"),
            "lenderName": st.column_config.TextColumn("Lender Name", width="medium"),
            "loanAmount": st.column_config.NumberColumn(
                "Loan Amount", width="small", format="dollar"
            ),
        },
    )


def _show_introduction() -> None:
    top_n = 5
    min_num_loans = 4

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)
    top_borrowers = _get_top_borrowers_by_repeat_lender_pct(
        prepped_data, min_num_loans, top_n
    )

    top_borrower_lines = []
    for i, (
        borrower,
        pct,
        max_lender_name,
        num_loans_from_max_lender,
        num_loans,
    ) in enumerate(top_borrowers, 1):
        pct_value: int = int(round(pct))
        top_borrower_lines.append(
            f"{borrower} (**{pct_value}%** of {num_loans} total loans)"
        )

    st.markdown(
        f"""
        View any borrower's financing activities over a 12-month period. 
        Explore their lender relationships to identify loyal borrowers who 
        consistently use the same funding source versus those who borrow from 
        different lenders each time.

        The top {top_n} borrowers (with at least {min_num_loans} loans) ranked 
        by the percentage of loans from a single lender.
        
        1. {top_borrower_lines[0] if len(top_borrower_lines) > 0 else ""}
        1. {top_borrower_lines[1] if len(top_borrower_lines) > 1 else ""}
        1. {top_borrower_lines[2] if len(top_borrower_lines) > 2 else ""}
        1. {top_borrower_lines[3] if len(top_borrower_lines) > 3 else ""}
        1. {top_borrower_lines[4] if len(top_borrower_lines) > 4 else ""}
        
        Simply type or select the borrower's name in the search field below to begin.
        """
    )


def _show_metrics_selected_data(selected_data: List[Dict]) -> None:
    num_lenders: int = len(set(d.get("lenderName", "") for d in selected_data))
    if num_lenders == 0:
        return

    repeat_lender_count: int = _count_repeat_lenders(selected_data)
    repeat_lender_pct: float = (
        (repeat_lender_count / num_lenders) * 100 if num_lenders > 0 else 0
    )

    loan_amounts = [
        float(d.get("loanAmount", 0))
        for d in selected_data
        if d.get("loanAmount") not in (None, "", "N/A")
    ]
    avg_loan_amount = sum(loan_amounts) / len(loan_amounts) if loan_amounts else 0

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Repeat Lender Count",
        f"{repeat_lender_count}/{num_lenders}",
        border=True,
    )
    col2.metric(
        "Repeat Lender Pct",
        f"{int(round(repeat_lender_pct))}%",
        border=True,
    )
    col3.metric(
        "Average Loan Amount",
        to_currency(int(avg_loan_amount)),
        border=True,
    )


def _show_network_graph(selected_data: List[Dict]) -> None:
    if not selected_data:
        return

    party = "lender"
    nodes, edges = get_timeline_network_graph_nodes_edges(selected_data, party)
    show_timeline_network_graph(nodes, edges)

    borrower_name: str = selected_data[0]["buyerName"]
    st.info(
        f"""
        ##### :material/cognition:  How to Interpret the Chart
        In this visualization, **purple** shows lenders who have provided multiple 
        loans to the borrower {borrower_name}, while **red** shows one-time lenders. 
        **Yellow** indicates individual loans, and **green** represents the twelve-month 
        period since the borrower's last property purchase date within the provided
        dataset.
        **Arrows** connect each lender to their respective loans, and each loan to 
        the month in which it was originated.
        """
    )


def _show_selectbox(prepped_data: List[Dict]) -> str:
    borrowers = sorted(
        set(d.get("buyerName", "") for d in prepped_data if d.get("buyerName", ""))
    )
    option: str = st.selectbox(
        "Enter the borrower's name.",
        borrowers,
    )

    return option


def render_page():
    show_st_h1("Borrower Analysis")
    show_st_h2("Borrowing Timeline", w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.write("")
    _show_introduction()

    st.write("")
    st.write("")
    selected_borrower: str = _show_selectbox(prepped_data)

    selected_data: List[Dict] = _get_selected_data(prepped_data, selected_borrower)

    st.write("")
    st.write("")
    _show_metrics_selected_data(selected_data)

    _show_network_graph(selected_data)

    _show_df(selected_data)


render_page()
