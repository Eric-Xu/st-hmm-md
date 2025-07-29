from collections import Counter
from typing import Dict, List, Set, Tuple

import pandas as pd

from utils.borrower import get_borrower_to_last_lender


def get_fromto_lenders_w_borrower(
    prepped_data: List[Dict],
) -> List[Tuple[str, str, str]]:
    """
    For each lender, find borrowers who have churned (i.e., their last loan was to a different lender),
    and create a list of (churned_borrower, from_lender, to_lender) triplets representing the migration
    of each churned borrower from their previous lender to their new lender.

    Args:
        prepped_data (List[Dict]): List of loan records, each as a dictionary.

    Returns:
        List[Tuple[str, str, str]]: List of (churned_borrower, from_lender, to_lender)
            triplets for each churned borrower.
    """
    borrower_fromto_lenders: List[Tuple[str, str, str]] = []

    borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(prepped_data)
    lender_to_churned_borrowers: Dict[str, Set[str]] = get_lender_to_lost_borrowers(
        prepped_data
    )

    for from_lender, churned_borrowers in lender_to_churned_borrowers.items():
        for churned_borrower in churned_borrowers:
            to_lender = borrower_to_last_lender.get(churned_borrower)
            if to_lender and to_lender != from_lender:
                borrower_fromto_lenders.append(
                    (churned_borrower, from_lender, to_lender)
                )

    return borrower_fromto_lenders


def get_fromto_lenders_w_counts(prepped_data: List[Dict]) -> List[Tuple[str, str, int]]:
    """
    Count the number of times that a borrower migrated from one lender to another
    (churned), and return a list of [from_lender, to_lender, count] records.

    Args:
        prepped_data (List[Dict]): List of loan records, each as a dictionary.

    Returns:
        List[Tuple[str, str, int]]: List of [from_lender, to_lender, count] records, where count is the number of borrowers
            who migrated from from_lender to to_lender.
    """
    borrower_fromto_lenders: List[Tuple[str, str, str]] = get_fromto_lenders_w_borrower(
        prepped_data
    )
    fromto_lenders: List[Tuple[str, str]] = [
        (from_lender, to_lender)
        for _, from_lender, to_lender in borrower_fromto_lenders
    ]
    fromto_counter = Counter(fromto_lenders)
    fromto_lenders_w_counts: List[Tuple[str, str, int]] = [
        (from_lender, to_lender, count)
        for (from_lender, to_lender), count in fromto_counter.items()
    ]

    return fromto_lenders_w_counts


def get_lender_to_borrowers(prepped_data: List[Dict]) -> Dict[str, Set[str]]:
    """
    For each lender (lenderName), collect a list of all borrowers (buyerName) they've lent to.
    Returns a dict mapping lender name to a list of borrower names.
    """
    lender_to_borrowers: Dict[str, Set[str]] = {}
    for record in prepped_data:
        lender = record.get("lenderName")
        borrower = record.get("buyerName")
        if not lender or not borrower:
            continue
        if lender not in lender_to_borrowers:
            lender_to_borrowers[lender] = set()
        lender_to_borrowers[lender].add(borrower)

    return lender_to_borrowers


def get_lender_to_loan_amount_bins(
    df: pd.DataFrame, bin_edges: List[int], bin_labels: List[str]
) -> pd.DataFrame:
    # Make a copy to avoid pandas warning when modifying DataFrame that might be a view/slice
    df = df.copy()
    df["loan_amount_bin"] = pd.cut(
        df["loanAmount"], bins=bin_edges, labels=bin_labels, right=False
    )
    # Group by lender and bin, count number of loans
    grouped = (
        df.groupby(["lenderName", "loan_amount_bin"], observed=True)
        .size()
        .reset_index()
    )
    grouped = grouped.rename(columns={0: "num_loans", "lenderName": "lender"})

    return grouped


def get_lender_to_lost_borrowers(prepped_data: List[Dict]) -> Dict[str, Set[str]]:
    """
    For each lender, find borrowers who have churned (last loan was to a different lender).
    Returns a dict mapping lender name to a list of unique churned borrower names.
    """
    lender_to_lost_borrowers: Dict[str, Set[str]] = {}

    borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(prepped_data)
    lender_to_all_borrowers: Dict[str, Set[str]] = get_lender_to_borrowers(prepped_data)

    for lender, borrowers in lender_to_all_borrowers.items():
        lost_borrowers = set()
        for borrower in borrowers:
            if borrower_to_last_lender.get(borrower) != lender:
                lost_borrowers.add(borrower)
        if lost_borrowers:
            lender_to_lost_borrowers[lender] = lost_borrowers

    return lender_to_lost_borrowers


def get_lender_to_gained_borrowers(prepped_data: List[Dict]) -> Dict[str, Set[str]]:
    """
    For each lender, find borrowers they have gained (borrowers whose last loan
    was with this lender, but who previously borrowed from a different lender).
    Returns a dict mapping lender name to a set of unique gained borrower names.
    """
    lender_to_gained_borrowers: Dict[str, Set[str]] = {}

    borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(prepped_data)
    lender_to_all_borrowers: Dict[str, Set[str]] = get_lender_to_borrowers(prepped_data)

    for borrower, last_lender in borrower_to_last_lender.items():
        # Only consider borrowers who have a last lender
        if not last_lender:
            continue
        # If the borrower has ever borrowed from a different lender
        for lender, borrowers in lender_to_all_borrowers.items():
            if lender == last_lender:
                if borrower in borrowers:
                    # Check if borrower has ever borrowed from another lender
                    borrowed_from_others = any(
                        borrower in bset and l != last_lender
                        for l, bset in lender_to_all_borrowers.items()
                    )
                    if borrowed_from_others:
                        if last_lender not in lender_to_gained_borrowers:
                            lender_to_gained_borrowers[last_lender] = set()
                        lender_to_gained_borrowers[last_lender].add(borrower)

    return lender_to_gained_borrowers


def get_lender_to_loan_amounts(prepped_data: List[Dict]) -> Dict[str, List[int]]:
    """
    Returns a dictionary mapping each lender to a list of their loan amounts.
    """
    lender_to_loan_amounts: Dict[str, List[int]] = {}
    for item in prepped_data:
        lender = item.get("lenderName", "")
        loan_amount = int(item.get("loanAmount", 0))
        if lender:
            if lender not in lender_to_loan_amounts:
                lender_to_loan_amounts[lender] = []
            lender_to_loan_amounts[lender].append(loan_amount)

    return lender_to_loan_amounts


def get_lender_to_num_loans(prepped_data: List[Dict]) -> Dict[str, int]:
    """
    Returns a dictionary mapping each lender to their number of loans.
    Assumes each item in prepped_data has a 'lenderName' field.
    """
    lender_to_num_loans: Dict[str, int] = {}
    for item in prepped_data:
        lender = item.get("lenderName")
        if lender:
            lender_to_num_loans[lender] = lender_to_num_loans.get(lender, 0) + 1

    return lender_to_num_loans


def get_lender_to_repeat_borrowers(prepped_data: List[Dict]) -> Dict[str, Set[str]]:
    """
    Returns a dictionary mapping each lender to the set of repeat borrowers
    (those who have taken more than one loan from that lender).
    """
    lender_to_borrower_counts: Dict[str, Dict[str, int]] = {}
    for record in prepped_data:
        lender = record.get("lenderName")
        borrower = record.get("buyerName")
        if not lender or not borrower:
            continue
        if lender not in lender_to_borrower_counts:
            lender_to_borrower_counts[lender] = {}
        if borrower not in lender_to_borrower_counts[lender]:
            lender_to_borrower_counts[lender][borrower] = 0
        lender_to_borrower_counts[lender][borrower] += 1

    lender_to_repeat_borrowers: Dict[str, Set[str]] = {}
    for lender, borrower_counts in lender_to_borrower_counts.items():
        repeat_borrowers: Set[str] = {
            borrower for borrower, count in borrower_counts.items() if count > 1
        }
        if repeat_borrowers:
            lender_to_repeat_borrowers[lender] = repeat_borrowers

    return lender_to_repeat_borrowers


def get_lender_to_volume(prepped_data: List[Dict]) -> Dict[str, int]:
    """
    Returns a dictionary mapping each lender to their total loan amount.
    """
    lender_to_volume: Dict[str, int] = {}
    for item in prepped_data:
        lender = item.get("lenderName")
        loan_amount = int(item.get("loanAmount", 0))
        if lender:
            lender_to_volume[lender] = lender_to_volume.get(lender, 0) + loan_amount

    return lender_to_volume


def get_top_lenders_by_num_loans(prepped_data: List[Dict], top_n: int) -> List[Dict]:
    """
    Returns the records from prepped_data for the top_n lenders ordered
    by their number of loans.
    """
    lender_to_num_loans: Dict[str, int] = get_lender_to_num_loans(prepped_data)
    # Get the top_n lenders by number of loans
    top_lenders = sorted(lender_to_num_loans.items(), key=lambda x: x[1], reverse=True)[
        :top_n
    ]
    top_lender_names = set(lender for lender, _ in top_lenders)
    # Filter prepped_data for records belonging to top lenders
    top_lender_records = [
        item for item in prepped_data if item.get("lenderName") in top_lender_names
    ]

    return top_lender_records


def get_top_lenders_by_volume(prepped_data: List[Dict], top_n: int) -> List[Dict]:
    """
    Returns the records from prepped_data for the top_n lenders ordered
    by their total loan volume (loanAmount).
    """
    lender_to_volume: Dict[str, int] = get_lender_to_volume(prepped_data)
    # Get the top_n lenders by total loan volume
    top_lenders = sorted(lender_to_volume.items(), key=lambda x: x[1], reverse=True)[
        :top_n
    ]
    top_lender_names = set(lender for lender, _ in top_lenders)
    # Filter prepped_data for records belonging to top lenders
    top_lender_records = [
        item for item in prepped_data if item.get("lenderName") in top_lender_names
    ]
    return top_lender_records
