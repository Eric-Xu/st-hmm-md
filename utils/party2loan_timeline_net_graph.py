import random
from collections import Counter
from datetime import date, datetime
from typing import Dict, List, Tuple

from streamlit_agraph import Config, Edge, Node, agraph

from constants.css import (
    BLACK_HEX,
    GREEN_HEX,
    GREEN_LIGHT_HEX,
    PURPLE_HEX,
    RED_HEX,
    YELLOW_HEX,
)
from constants.dataset import PARTY_TO_DATASET_KEY
from utils.formatting import to_currency

NODE_COLOR_CURRENT_ONE_TIME_BORROWER = RED_HEX
NODE_COLOR_CURRENT_REPEAT_BORROWER = PURPLE_HEX
NODE_COLOR_LOAN = YELLOW_HEX
NODE_COLOR_LOST_ONE_TIME_BORROWER = RED_HEX
NODE_COLOR_LOST_REPEAT_BORROWER = PURPLE_HEX
NODE_COLOR_MONTH = GREEN_HEX
NODE_X_VALUE_CURRENT_REPEAT_BORROWER = 0
NODE_X_VALUE_CURRENT_ONE_TIME_BORROWER = 50
NODE_X_VALUE_MONTH = 400
NODE_X_VALUE_LOST_ONE_TIME_BORROWER = 750
NODE_X_VALUE_LOST_REPEAT_BORROWER = 800


def _add_party_num_loans(data: List[Dict], party: str) -> List[Dict]:
    """
    Adds a '{lender/borrower}_selected_num_loans' key to each dict in the list,
    counting how many times each party name occurs in the list.
    """
    party_dataset_key: str = PARTY_TO_DATASET_KEY[party]

    # Count occurrences of each party_dataset_key
    party_counts = Counter(
        d.get(party_dataset_key) for d in data if d.get(party_dataset_key) is not None
    )

    # Add the count to each dict
    for d in data:
        party_name = d.get(party_dataset_key)
        d[f"{party}_selected_num_loans"] = party_counts.get(party_name, 0)

    return data


def _count_unique_members(data: List[Dict], party: str) -> int:
    party_dataset_key: str = PARTY_TO_DATASET_KEY[party]
    member_names = set()
    for d in data:
        member_name = d.get(party_dataset_key)
        if member_name:
            member_names.add(member_name)
    count: int = len(member_names)

    return count


def _create_loan_date_relationships(
    data: List[Dict], party: str, nodes: List, edges: List
) -> Tuple[List, List]:
    unique_members: int = _count_unique_members(data, party)
    y_scaling_factor: int = _get_y_scaling_factor(unique_members)

    latest_date: str | None = _get_latest_date(data)
    last_12_months: List[date] = _get_last_12_months(latest_date)
    date_to_month_node_label: Dict[date, str] = _get_date_to_month_node_label(
        last_12_months
    )
    month_node_ids = {}
    # Create month nodes in reverse chronological order
    for i, first_of_month in enumerate(sorted(last_12_months, reverse=True)):
        month_node_label: str | None = date_to_month_node_label.get(first_of_month)
        if not month_node_label:
            continue
        month_node_title: str = month_node_label
        month_node_id = f"month_{i+1}"
        month_node_ids[first_of_month] = month_node_id
        label_value: str = f"  {month_node_label}  "
        y_value = i * y_scaling_factor
        nodes.append(
            Node(
                id=month_node_id,
                title=month_node_title,
                label=label_value,
                shape="circle",
                color=NODE_COLOR_MONTH,
                labelColor=BLACK_HEX,
                borderWidth=0,
                physics=False,
                fixed={"x": True, "y": True},
                x=NODE_X_VALUE_MONTH,
                y=y_value,
            )
        )

    # Create loan-to-month relationships with error handling
    for datum in data:
        try:
            record_id: str = str(datum.get("id"))
            sale_date: str = datum.get("saleDate", None)
            if not sale_date:
                continue
            first_of_month = _get_first_of_month(sale_date)
            if first_of_month not in month_node_ids:
                continue
            loan_id: str = f"loan_{record_id}"
            source_id = loan_id
            target_id = month_node_ids[first_of_month]
            if not source_id or not target_id:
                continue
            edges.append(
                Edge(
                    source=source_id,
                    target=target_id,
                    color=GREEN_LIGHT_HEX,
                    width=5,
                )
            )
        except Exception as e:
            # Optionally log the error or pass
            pass

    return nodes, edges


def _create_party_loan_relationships(
    data: List[Dict], party: str, nodes: List, edges: List
) -> Tuple[List, List]:
    party_dataset_key: str = PARTY_TO_DATASET_KEY[party]

    member_name_to_node_id: Dict[str, str] = dict()  # Map member name to node ID

    data = _add_party_num_loans(data, party)
    unique_members: int = _count_unique_members(data, party)
    mass: float = _get_scaled_mass(unique_members)

    for datum in data:
        record_id: str = str(datum.get("id"))
        party_node_id: str = f"{party}_{record_id}"
        member_name: str = datum.get(party_dataset_key, "N/A")
        party_node_title: str = f"{party.capitalize()}: {member_name}"
        party_num_loans: int = datum.get(f"{party}_selected_num_loans", 0)

        # Assign different node style for repeat members.
        color: str = (
            NODE_COLOR_CURRENT_REPEAT_BORROWER
            if party_num_loans > 1
            else NODE_COLOR_CURRENT_ONE_TIME_BORROWER
        )
        x_value: int = _get_party_node_x_value(
            party_num_loans, unique_members, member_name
        )
        label: str | None = member_name if party_num_loans > 1 else None

        # Only create new party nodes based on the member name.
        if member_name not in member_name_to_node_id:
            nodes.append(
                Node(
                    id=party_node_id,
                    title=party_node_title,
                    label=label,
                    color=color,
                    labelColor=BLACK_HEX,
                    size=20,
                    borderWidth=0,
                    mass=mass,
                    fixed={"x": True},
                    x=x_value,
                )
            )
            member_name_to_node_id[member_name] = party_node_id

        # Create loan nodes
        loan_amount: int = int(datum.get("loanAmount", 0))
        sale_date: str = datum.get("saleDate", "N/A")
        address: str = datum.get("address", "N/A")
        loan_currency_amount: str = to_currency(loan_amount)
        loan_node_id: str = f"loan_{record_id}"
        loan_node_title: str = (
            f"Loan Amount: {loan_currency_amount}\nSale Date: {sale_date}\nProperty: {address}"
        )
        nodes.append(
            Node(
                id=loan_node_id,
                title=loan_node_title,
                label=None,
                color=NODE_COLOR_LOAN,
                labelColor=BLACK_HEX,
                size=20,
                borderWidth=0,
            )
        )

        # Create party-loan relationships
        source_id = member_name_to_node_id[member_name]
        target_id = loan_node_id
        edges.append(
            Edge(
                source=source_id,
                target=target_id,
                color=GREEN_LIGHT_HEX,
                width=5,
            )
        )

    return nodes, edges


def _get_date_to_month_node_label(last_12_months: List[date]) -> Dict[date, str]:
    """Return a dict mapping each date to a label like "DEC '25"."""

    return {d: d.strftime("%b '%y").upper() for d in last_12_months}


def _get_first_of_month(date_str: str) -> date:
    """
    Convert a date string like '2025-05-10' to a date object for the
    first of that month (e.g., date(2025, 5, 1)).
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d").date()

    return date(dt.year, dt.month, 1)


def _get_last_12_months(latest_date: str | None) -> List[date]:
    """
    Return a list of 12 date objects, each the first of the month,
    going back from latest_date (inclusive).
    """
    months: List[date] = []
    if not latest_date:
        dt: date = date.today()
    else:
        dt: date = datetime.strptime(latest_date, "%Y-%m-%d").date()
    year, month = dt.year, dt.month
    for _ in range(12):
        months.append(date(year, month, 1))
        # Move to previous month
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1

    return months


def _get_latest_date(data: List[Dict]) -> str | None:
    """
    Return the latest 'saleDate' in YYYY-MM-DD format from data,
    or None if not found.
    """
    if not data:
        return None
    dates: List[str] = [d["saleDate"] for d in data if d.get("saleDate") is not None]
    if not dates:
        return None

    return max(dates)


def _get_party_node_x_value(
    party_num_loans: int, unique_members: int, member_name: str
) -> int:
    """
    Returns the x position for a party node. For one-time borrowers, a
    deterministic pseudo-random offset is generated using a random number
    generator seeded with the member's name. This ensures each node's position
    is stable across rerenders and user interactions (such as clicking),
    preventing the chart from jumping or rerendering unpredictably. For repeat
    borrowers, a fixed x position is used.
    """
    spread = 0
    if party_num_loans > 1:
        base = NODE_X_VALUE_CURRENT_REPEAT_BORROWER
        if unique_members > 10:
            spread = 25
    else:
        base = NODE_X_VALUE_CURRENT_ONE_TIME_BORROWER
        if unique_members > 100:
            spread = 75
        elif unique_members > 20:
            spread = 50
        else:
            spread = 0

    if spread > 0:
        rng = random.Random(member_name)
        x_value = rng.randint(base, base + spread)
    else:
        x_value = base

    return x_value


def _get_scaled_mass(unique_members: int) -> float:
    # Higher mass means stronger repulsion between nodes
    if unique_members > 100:
        mass = 0.25
    elif unique_members > 50:
        mass = 0.5
    elif unique_members > 20:
        mass = 0.7
    else:
        mass = 1.0

    return mass


def _get_y_scaling_factor(unique_members: int) -> int:
    # Increase vertical spacing for more members
    if unique_members > 100:
        y_scaling_factor = 400
    elif unique_members > 80:
        y_scaling_factor = 250
    elif unique_members > 60:
        y_scaling_factor = 200
    elif unique_members > 40:
        y_scaling_factor = 150
    elif unique_members > 20:
        y_scaling_factor = 125
    else:
        y_scaling_factor = 100

    return y_scaling_factor


def get_timeline_network_graph_nodes_edges(
    data: List[Dict], party: str
) -> Tuple[List, List]:
    nodes, edges = [], []
    nodes, edges = _create_party_loan_relationships(data, party, nodes, edges)
    nodes, edges = _create_loan_date_relationships(data, party, nodes, edges)

    return nodes, edges


def show_timeline_network_graph(nodes: List, edges: List) -> None:
    height = 1000
    config = Config(
        height=height,
        directed=True,
        nodeHighlightBehavior=True,
        node={"labelProperty": "label"},
        link={"labelProperty": "label"},
    )

    agraph(nodes=nodes, edges=edges, config=config)
