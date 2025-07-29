from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple

import pandas as pd
import streamlit as st

from pipelines.prepare_loan_data import prep_data
from utils.borrower import get_borrower_to_last_lender
from utils.formatting import to_currency
from utils.gui import show_default_footer, show_st_h1, show_st_h2, show_st_info
from utils.io import load_json
from utils.lender import (
    get_lender_to_borrowers,
    get_lender_to_loan_amounts,
    get_lender_to_lost_borrowers,
    get_lender_to_repeat_borrowers,
)
from utils.party2loan_timeline_net_graph import (
    NODE_COLOR_CURRENT_ONE_TIME_BORROWER,
    NODE_COLOR_CURRENT_REPEAT_BORROWER,
    NODE_COLOR_LOST_ONE_TIME_BORROWER,
    NODE_COLOR_LOST_REPEAT_BORROWER,
    NODE_X_VALUE_LOST_ONE_TIME_BORROWER,
    NODE_X_VALUE_LOST_REPEAT_BORROWER,
    get_timeline_network_graph_nodes_edges,
    show_timeline_network_graph,
)

NUM_NODE_MAX_THRESHOLD = 800


def _get_df_data(prepped_data: List[Dict], lender: str) -> List[Dict]:
    borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(prepped_data)
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

            last_lender = borrower_to_last_lender.get(borrower, "")

            row = {
                "buyerName": borrower,
                "has_churned": "Yes" if last_lender != lender else "",
                "is_repeat": "Yes" if borrower in repeat_borrowers else "",
                "loanAmount": record.get("loanAmount"),
                "saleDate": record.get("saleDate"),
            }
            records.append(row)

    return records


def _get_selected_data(prepped_data: List[Dict], lender: str) -> List[Dict]:
    return [d for d in prepped_data if d.get("lenderName", "") == lender]


def _get_top_lenders_by_repeat_borrower_pct(
    prepped_data: List[Dict], min_num_loans, top_n: int = 5
) -> list[tuple[str, float, int, int, int]]:
    """
    Returns a list of tuples:
        (lender_name, repeat_borrower_pct, repeat_borrower_count, unique_borrower_count, num_loans)
    for the top_n lenders by repeat borrower percentage.
    Only considers lenders with more than min_num_loans.
    """
    # Group all records by lender
    lender_to_records = defaultdict(list)
    for d in prepped_data:
        lender = d.get("lenderName")
        if lender:
            lender_to_records[lender].append(d)

    results = []
    for lender, records in lender_to_records.items():
        borrower_counts = Counter(
            d.get("buyerName") for d in records if d.get("buyerName")
        )
        num_unique = len(borrower_counts)
        num_loans = len(records)
        if num_unique == 0 or num_loans <= min_num_loans:
            continue
        # Count repeat borrowers
        repeat_borrowers = [
            name for name, count in borrower_counts.items() if count > 1
        ]
        num_repeat = len(repeat_borrowers)
        pct = (num_repeat / num_unique) * 100 if num_unique > 0 else 0
        results.append((lender, pct, num_repeat, num_unique, num_loans))

    # Sort by repeat borrower percentage, descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_n]


def _show_df(prepped_data: List[Dict], lender: str) -> None:
    records: List[Dict] = _get_df_data(prepped_data, lender)

    if not records:
        return

    column_order = [
        "saleDate",
        "buyerName",
        "is_repeat",
        "has_churned",
        "loanAmount",
    ]
    df = pd.DataFrame(records)[column_order].drop_duplicates()
    df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")
    df = df.sort_values("saleDate", ascending=False).reset_index(drop=True)

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "buyerName": st.column_config.TextColumn("Borrower Name"),
            "has_churned": st.column_config.TextColumn("Has Churned"),
            "is_repeat": st.column_config.TextColumn("Is Repeat"),
            "loanAmount": st.column_config.NumberColumn("Loan Amount", format="dollar"),
            "saleDate": st.column_config.TextColumn("Sale Date"),
        },
    )


def _show_introduction() -> None:
    top_n = 5
    min_num_loans = 10

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)
    top_lenders = _get_top_lenders_by_repeat_borrower_pct(
        prepped_data, min_num_loans, top_n
    )

    top_lender_lines = []
    for i, (lender, pct, num_repeat, num_unique, num_loans) in enumerate(
        top_lenders, 1
    ):
        top_lender_lines.append(f"{lender} ({int(round(pct))}%, {num_loans} loans)")

    st.markdown(
        f"""
        The top {top_n} lenders (with at least {min_num_loans} loans) ranked 
        by the **percentage of repeat borrowers** are:
        1. {top_lender_lines[0] if len(top_lender_lines) > 0 else ""}
        2. {top_lender_lines[1] if len(top_lender_lines) > 1 else ""}
        3. {top_lender_lines[2] if len(top_lender_lines) > 2 else ""}
        4. {top_lender_lines[3] if len(top_lender_lines) > 3 else ""}
        5. {top_lender_lines[4] if len(top_lender_lines) > 4 else ""}

        Use the chart below to view a lender's most recent origination activities
        over a 12-month period.
        """
    )


def _get_network_graph_nodes_edges(
    selected_data: List[Dict], lost_borrowers: Set[str]
) -> Tuple[List, List]:
    party = "borrower"
    nodes, edges = get_timeline_network_graph_nodes_edges(selected_data, party)

    if not lost_borrowers:
        return nodes, edges

    for record in selected_data:
        borrower = record.get("buyerName")
        if borrower not in lost_borrowers:
            continue
        record_id = str(record.get("id"))
        lost_borrower_node_id: str = f"{party}_{record_id}"
        for node in nodes:
            if (
                node.id == lost_borrower_node_id
                and node.color == NODE_COLOR_CURRENT_REPEAT_BORROWER
            ):
                node.color = NODE_COLOR_LOST_REPEAT_BORROWER
                node.x = NODE_X_VALUE_LOST_REPEAT_BORROWER
            elif (
                node.id == lost_borrower_node_id
                and node.color == NODE_COLOR_CURRENT_ONE_TIME_BORROWER
            ):
                node.color = NODE_COLOR_LOST_ONE_TIME_BORROWER
                node.x = NODE_X_VALUE_LOST_ONE_TIME_BORROWER

    return nodes, edges


def _show_network_graph(selected_data: List[Dict], lost_borrowers: Set[str]) -> None:
    nodes, edges = _get_network_graph_nodes_edges(selected_data, lost_borrowers)

    if len(nodes) > NUM_NODE_MAX_THRESHOLD:
        show_st_info("chart_disabled")
        return

    show_timeline_network_graph(nodes, edges)

    lender_name: str = selected_data[0]["lenderName"]
    st.info(
        f"""
        ##### :material/cognition:  How to Interpret the Chart
        In this visualization, **purple** shows borrowers who have taken out multiple 
        loans from the lender {lender_name}, while **red** shows one-time borrowers. 
        **Yellow** indicates individual loans, and **green** represents the twelve-month 
        period since the lender's last loan origination date within the provided dataset.
        **Arrows** connect each borrower to their respective loans, and each loan to 
        the month in which it was originated.
        Borrowers on **the right side** are ones who used a different lender to fund
        their latest project.
        """
    )


def _show_selectbox(prepped_data: List[Dict]) -> str:
    lenders = sorted(
        set(d.get("lenderName", "") for d in prepped_data if d.get("lenderName", ""))
    )
    option: str = st.selectbox(
        "**Enter the lender's name.**",
        lenders,
    )
    return option


def _show_metrics_selected_data(prepped_data: List[Dict], lender: str) -> None:
    lender_to_borrowers: Dict[str, Set[str]] = get_lender_to_borrowers(prepped_data)
    num_borrowers: int = len(lender_to_borrowers.get(lender, set()))
    if num_borrowers == 0:
        return

    lender_to_churned_borrowers: Dict[str, Set[str]] = get_lender_to_lost_borrowers(
        prepped_data
    )
    churned_borrower_count: int = len(lender_to_churned_borrowers.get(lender, set()))
    lender_to_repeat_borrowers: Dict[str, Set[str]] = get_lender_to_repeat_borrowers(
        prepped_data
    )
    repeat_borrower_count: int = len(lender_to_repeat_borrowers.get(lender, set()))
    lender_to_loan_amounts: Dict[str, List[int]] = get_lender_to_loan_amounts(
        prepped_data
    )

    loan_amounts: List[int] = lender_to_loan_amounts.get(lender, [])
    avg_loan_amount = sum(loan_amounts) / len(loan_amounts) if loan_amounts else 0

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Repeat Borrowers",
        f"{repeat_borrower_count}/{num_borrowers}",
        border=True,
    )
    col2.metric(
        "Churned Borrowers",
        f"{churned_borrower_count}/{num_borrowers}",
        border=True,
    )
    col3.metric(
        "Average Loan Amount",
        to_currency(int(avg_loan_amount)),
        border=True,
    )


def render_page():
    show_st_h1("Lender Analysis")
    show_st_h2("Origination Timeline", w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.write("")
    _show_introduction()

    st.write("")
    st.write("")
    selected_lender: str = _show_selectbox(prepped_data)

    st.write("")
    st.write("")
    _show_metrics_selected_data(prepped_data, selected_lender)

    selected_data: List[Dict] = _get_selected_data(prepped_data, selected_lender)

    if not selected_data:
        show_st_info("no_data_selected")
        return

    lender_to_lost_borrowers: Dict[str, Set[str]] = get_lender_to_lost_borrowers(
        prepped_data
    )
    lost_borrowers: Set[str] = lender_to_lost_borrowers.get(selected_lender, set())
    _show_network_graph(selected_data, lost_borrowers)

    st.write("")
    _show_df(prepped_data, selected_lender)

    show_default_footer()


render_page()
