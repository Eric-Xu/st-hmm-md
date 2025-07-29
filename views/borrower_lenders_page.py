from typing import Dict, List

import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from constants.css import BLACK_HEX, BLUE_HEX, GREEN_HEX, GREEN_LIGHT_HEX
from constants.dataset import END_DATE, LOCATION, START_DATE
from pipelines.prepare_loan_data import prep_data
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json

HIDE_BORROWER_LABEL_THRESHOLD = 1
HIDE_LENDER_LABEL_THRESHOLD = 1


def _get_selected_data(prepped_data: List[Dict], slider_data: Dict) -> List[Dict]:
    user_min_num_lenders: int = slider_data["user_min_num_lenders"]
    user_max_num_lenders: int = slider_data["user_max_num_lenders"]

    selected_data: List[Dict] = list()
    for borrower_activity in prepped_data:
        num_lenders: int = borrower_activity.get("borrower_num_lenders", 0)
        if num_lenders >= user_min_num_lenders and num_lenders <= user_max_num_lenders:
            selected_data.append(borrower_activity)

    return selected_data


def _show_introduction(prepped_data: List[Dict]) -> None:
    unique_borrowers: int = len(set(item.get("buyerName", "") for item in prepped_data))
    unique_lenders: int = len(set(item.get("lenderName", "") for item in prepped_data))

    st.markdown(
        f"""
        There are a total of **{unique_lenders}** lenders and **{unique_borrowers}** borrowers.
        """
    )


def _show_metrics_all_data(prepped_data: List[Dict]) -> None:
    unique_borrowers: int = len(set(item.get("buyerName", "") for item in prepped_data))
    unique_lenders: int = len(set(item.get("lenderName", "") for item in prepped_data))

    col1, col2 = st.columns(2)
    col1.metric("Number of Lenders", unique_lenders, border=True)
    col2.metric("Number of Borrowers", unique_borrowers, border=True)


def _show_network_graph(selected_data: List[Dict]) -> None:
    nodes, edges = [], []
    borrower_index, lender_index = 1, 1
    borrower_name_to_node_id: Dict[str, str] = dict()  # Map borrower name to node ID
    lender_name_to_node_id: Dict[str, str] = dict()

    # Create a set to track unique borrower-lender relationships
    unique_relationships = set()

    # Create nodes and edges of the network graph
    for borrower_activity in selected_data:
        borrower_name: str = borrower_activity.get("buyerName", "N/A")
        lender_name: str = borrower_activity.get("lenderName", "N/A")

        # Skip if we've already processed this borrower-lender relationship
        relationship = (borrower_name, lender_name)
        if relationship in unique_relationships:
            continue
        unique_relationships.add(relationship)

        num_lenders: int = borrower_activity.get("borrower_num_lenders", 0)
        borrower_node_title: str = f"Borrower: {borrower_name}"
        borrower_name_value = (
            borrower_name if num_lenders > HIDE_BORROWER_LABEL_THRESHOLD else None
        )

        if borrower_name not in borrower_name_to_node_id:
            borrower_node_id: str = f"borrower_{borrower_index}"
            nodes.append(
                Node(
                    id=borrower_node_id,
                    title=borrower_node_title,
                    label=borrower_name_value,
                    color=BLUE_HEX,
                    labelColor=BLACK_HEX,
                    size=20,
                    borderWidth=0,
                    font={"size": 24},
                )
            )
            borrower_name_to_node_id[borrower_name] = borrower_node_id
            borrower_index += 1  # Increment borrower index

        lender_node_title: str = f"Lender: {lender_name}"
        # lender_name_value = (
        #     lender_name if num_borrowers > HIDE_LENDER_LABEL_THRESHOLD else None
        # )
        lender_name_value = None
        if lender_name not in lender_name_to_node_id:
            lender_node_id: str = f"lender_{lender_index}"
            nodes.append(
                Node(
                    id=lender_node_id,
                    title=lender_node_title,
                    label=lender_name_value,
                    color=GREEN_HEX,
                    labelColor=BLACK_HEX,
                    size=20,
                    borderWidth=0,
                    font={"size": 24},
                )
            )
            lender_name_to_node_id[lender_name] = lender_node_id
            lender_index += 1  # Increment lender index

        source_id = borrower_name_to_node_id[borrower_name]
        target_id = lender_name_to_node_id[lender_name]
        new_edge_node: Edge = Edge(
            source=source_id,
            target=target_id,
            color=GREEN_LIGHT_HEX,
            width=5,
        )
        edges.append(new_edge_node)

    # Create the network graph
    config = Config(
        physics=True,
        directed=False,
        nodeHighlightBehavior=True,
        node={"labelProperty": "label"},
        link={"labelProperty": "label"},
    )
    agraph(nodes=nodes, edges=edges, config=config)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        Blue represents borrowers, and green represents lenders.
        Light green lines represent borrower-lender relationships.
        """
    )


def _show_slider(prepped_data: List[Dict]) -> Dict:
    if prepped_data:
        max_num_lenders: int = max(
            item.get("borrower_num_lenders", 0) for item in prepped_data
        )
    else:
        max_num_lenders = 0

    # Use a tiered filter to improve rendering speed
    if max_num_lenders > 20:
        offset = int(max_num_lenders / 10)
        slider_min = offset
        slider_max = max_num_lenders
        value_min = slider_min + offset
        value_max = max_num_lenders - offset
    elif max_num_lenders > 10:
        slider_min = 1
        slider_max = max_num_lenders
        value_min = slider_min + 1
        value_max = max_num_lenders - 1
    else:
        slider_min = 1
        slider_max = max_num_lenders + 1
        value_min = slider_min + 1
        value_max = max_num_lenders + 1

    st.markdown("#### Lenders-Per-Borrower")
    user_min_num_lenders, user_max_num_lenders = st.slider(
        "**Select borrowers by adjusting the range for number of lenders-per-borrower.**",
        min_value=slider_min,
        max_value=slider_max,
        value=(value_min, value_max),
        step=1,
    )

    slider_data: Dict = {
        "user_min_num_lenders": user_min_num_lenders,
        "user_max_num_lenders": user_max_num_lenders,
    }
    return slider_data


def render_page():
    show_st_h1("Borrower Lender Relationships")
    show_st_h2(LOCATION, w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.write("")
    _show_introduction(prepped_data)

    _show_metrics_all_data(prepped_data)

    slider_data: Dict = _show_slider(prepped_data)

    selected_data: List[Dict] = _get_selected_data(prepped_data, slider_data)

    st.write("")
    _show_network_graph(selected_data)


render_page()
