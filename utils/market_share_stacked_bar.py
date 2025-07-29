from typing import Dict, List, Tuple

import altair as alt
import pandas as pd
import streamlit as st

BIN_EDGE_TO_LABEL = {
    50_000: "$0 - $50K",
    100_000: "$50K - $100K",
    250_000: "$100K - $250K",
    500_000: "$250K - $500K",
    1_000_000: "$500K - $1M",
    2_500_000: "$1M - $2.5M",
    5_000_000: "$2.5M - $5M",
    10_000_000: "$5M - $10M",
}
BIN_EDGE_TO_UNDER_LABEL = {
    50_000: "Under $50K",
    100_000: "Under $100K",
    250_000: "Under $250K",
    500_000: "Under $500K",
    1_000_000: "Under $1M",
}
BIN_EDGE_TO_OVER_LABEL = {
    250_000: "Over $250K",
    500_000: "Over $250K",
    1_000_000: "Over $500K",
    2_500_000: "Over $1M",
    5_000_000: "Over $2.5M",
    10_000_000: "Over $5M",
}
LABEL_SEPARATOR = "  |  "


def _get_max_bin_edge(df: pd.DataFrame, bin_edges: List[int], min_count: int) -> int:
    sorted_edges = sorted(bin_edges, reverse=True)
    for i, edge in enumerate(sorted_edges):
        count = (df["loanAmount"] >= edge).sum()
        print(f"max edge: {edge}, count: {count}, min_count: {min_count}")
        if count > min_count:
            if i == 1:
                return sorted_edges[0]
            else:
                return sorted_edges[i - 1]

    return sorted_edges[-2]


def _get_min_bin_edge(df: pd.DataFrame, bin_edges: List[int], min_count: int) -> int:
    sorted_edges = sorted(bin_edges)
    for edge in sorted_edges:
        count = (df["loanAmount"] < edge).sum()
        print(f"min edge: {edge}, count: {count}, min_count: {min_count}")
        if count > min_count:
            return edge

    return sorted_edges[-1]


def get_edge_range(label: str) -> Tuple[int, int]:
    """
    Given a label like "$500K - $1M", find the matching value from BIN_EDGE_TO_LABEL
    and return a tuple of (upper_edge, lower_edge). For example, for "$500K - $1M"
    it should return (1_000_000, 500_000).
    """
    # Find all (edge, lbl) pairs that match the label
    matches = [(edge, lbl) for edge, lbl in BIN_EDGE_TO_LABEL.items() if lbl == label]
    if not matches:
        raise ValueError(f"Label '{label}' not found in BIN_EDGE_TO_LABEL.")
    upper_edge = matches[0][0]
    # Find the next lower edge (the next key below this one)
    sorted_edges = sorted(BIN_EDGE_TO_LABEL.keys(), reverse=True)
    idx = sorted_edges.index(upper_edge)
    if idx + 1 < len(sorted_edges):
        lower_edge = sorted_edges[idx + 1]
    else:
        lower_edge = 0  # If it's the lowest bin, lower edge is 0

    return (lower_edge, upper_edge)


def get_stacked_bar_edges_labels(
    df: pd.DataFrame, required_item_count: int
) -> Tuple[List[int], List[str]]:
    min_edge_value = _get_min_bin_edge(
        df,
        list(BIN_EDGE_TO_UNDER_LABEL.keys()),
        required_item_count,
    )
    max_edge_value = _get_max_bin_edge(
        df,
        list(BIN_EDGE_TO_OVER_LABEL.keys()),
        required_item_count,
    )

    prepped_bin_edge_to_label: Dict[int, str] = {
        k: v
        for k, v in BIN_EDGE_TO_LABEL.items()
        if k >= min_edge_value and k <= max_edge_value
    }

    if min_edge_value in prepped_bin_edge_to_label:
        prepped_bin_edge_to_label[min_edge_value] = BIN_EDGE_TO_UNDER_LABEL[
            min_edge_value
        ]
    if max_edge_value in prepped_bin_edge_to_label:
        prepped_bin_edge_to_label[max_edge_value] = BIN_EDGE_TO_OVER_LABEL[
            max_edge_value
        ]

    prepped_bin_edge_to_label = dict(sorted(prepped_bin_edge_to_label.items()))
    prepped_bin_labels: List[str] = list(prepped_bin_edge_to_label.values())
    prepped_bin_edges: List[int] = [0] + list(prepped_bin_edge_to_label.keys())

    return prepped_bin_edges, prepped_bin_labels


def show_lender_market_share_stacked_bar(
    chart_data: pd.DataFrame,
    bin_labels: List[str],
    height: int,
    y_title: str | None,
    y_label_limit: int = 180,
) -> None:
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("sum(num_loans)", title="Lender Market Share").stack("normalize"),
            y=alt.Y(
                "loan_amount_bin",
                title=y_title,
                sort=bin_labels,
                axis=alt.Axis(labelLimit=y_label_limit),
            ),
            color=alt.Color("lender", legend=None),
            tooltip=[
                alt.Tooltip("num_loans", title="Number of Loans"),
                alt.Tooltip("lender", title="Lender"),
            ],
        )
        .properties(height=height)
    )

    st.altair_chart(chart, use_container_width=True)
