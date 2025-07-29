from typing import Dict, List, Tuple

from streamlit_agraph import Config, Edge, Node, agraph

from constants.css import BLACK_HEX, GREEN_HEX, GREEN_LIGHT_HEX, YELLOW_HEX
from constants.dataset import PARTY_TO_COUNTERPARTY, PARTY_TO_DATASET_KEY
from utils.formatting import to_currency

HIDE_BORROWER_LABEL_THRESHOLD_PCT = 0.4
HIDE_BORROWER_LABEL_THRESHOLD = 1
HIDE_LENDER_LABEL_THRESHOLD = 4


def _create_party_loan_relationships(
    party, data: List[Dict], nodes: List, edges: List
) -> Tuple[List, List]:
    party_dataset_key: str = PARTY_TO_DATASET_KEY[party]

    member_name_to_node_id: Dict[str, str] = dict()

    loan_amount_to_scaled = _scale_loan_amounts(
        data
    )  # Compute scaling for loan amounts

    hide_label_threshold: int = _get_hide_label_threshold(
        party, data
    )  # Compute dynamic threshold value

    # Create nodes and edges of the network graph
    for datum in data:
        record_id: str = str(datum.get("id"))
        member_name: str = datum.get(party_dataset_key, "N/A")
        num_loans: int = datum.get(f"{party}_num_loans", 0)
        party_node_title: str = f"{party.capitalize()}: {member_name}"
        member_name_value = member_name if num_loans > hide_label_threshold else None
        if member_name not in member_name_to_node_id:
            party_node_id: str = f"{party}_{record_id}"
            nodes.append(
                Node(
                    id=party_node_id,
                    title=party_node_title,
                    label=member_name_value,
                    color=YELLOW_HEX,
                    labelColor=BLACK_HEX,
                    size=20,
                    borderWidth=0,
                    font={"size": 24},
                )
            )
            member_name_to_node_id[member_name] = party_node_id

        counterparty: str = PARTY_TO_COUNTERPARTY[party]
        counterparty_dataset_key: str = PARTY_TO_DATASET_KEY[counterparty]
        counterparty_name: str = datum.get(counterparty_dataset_key, "N/A")
        address: str = datum.get("address", "N/A")
        loan_amount: int = int(datum.get("loanAmount", 0))
        loan_currency_amount: str = to_currency(loan_amount)
        scaled_size_value: float = loan_amount_to_scaled[loan_amount]

        loan_node_id: str = f"loan_{record_id}"
        if party == "borrower":
            association: str = "loan by"
        else:
            association: str = "loan to"
        loan_node_title: str = (
            f"{loan_currency_amount} {association} {counterparty_name}\nProperty: {address}"
        )
        new_loan_node: Node = Node(
            id=loan_node_id,
            title=loan_node_title,
            label=None,
            color=GREEN_HEX,
            labelColor=BLACK_HEX,
            size=int(scaled_size_value),
            borderWidth=0,
        )

        source_id = member_name_to_node_id[member_name]
        target_id = loan_node_id
        new_edge_node: Edge = Edge(
            source=source_id,
            target=target_id,
            color=GREEN_LIGHT_HEX,
            width=5,
        )

        nodes.append(new_loan_node)
        edges.append(new_edge_node)

    return nodes, edges


def _get_hide_label_threshold(party: str, selected_data: List[Dict]) -> int:
    if party == "lender":
        hide_label_threshold = HIDE_LENDER_LABEL_THRESHOLD
    else:
        max_num_loans: int = max(
            [int(d.get("borrower_num_loans", 0)) for d in selected_data]
        )
        hide_label_threshold: int = int(
            max_num_loans * HIDE_BORROWER_LABEL_THRESHOLD_PCT
        )
        hide_label_threshold = (
            hide_label_threshold
            if hide_label_threshold > HIDE_BORROWER_LABEL_THRESHOLD
            else HIDE_BORROWER_LABEL_THRESHOLD
        )

    return hide_label_threshold


def _scale_loan_amounts(
    data: List[Dict], min_size: int = 10, max_size: int = 40
) -> Dict:
    """
    Returns a dict mapping loanAmount to scaled size between min_size and max_size.
    """
    loan_amounts: List[int] = [int(d.get("loanAmount", 0)) for d in data]
    if not loan_amounts:
        return {}
    min_amt = min(loan_amounts)
    max_amt = max(loan_amounts)
    if min_amt == max_amt:
        # All values are the same, return mid value
        return {amt: (min_size + max_size) // 2 for amt in loan_amounts}

    def scale(val: int) -> float:
        return min_size + (max_size - min_size) * (val - min_amt) / (max_amt - min_amt)

    return {amt: scale(amt) for amt in loan_amounts}


def show_relationship_network_graph(party: str, data: List[Dict]) -> None:
    nodes, edges = [], []
    nodes, edges = _create_party_loan_relationships(party, data, nodes, edges)

    # Create the network graph
    config = Config(
        physics=True,
        directed=True,
        nodeHighlightBehavior=True,
        node={"labelProperty": "label"},
        link={"labelProperty": "label"},
    )
    agraph(nodes=nodes, edges=edges, config=config)
