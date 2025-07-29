from typing import Dict, List, Set


def get_borrower_to_last_lender(prepped_data: List[Dict]) -> Dict[str, str]:
    """
    For each borrower (buyerName), find the lender (lenderName) from their most recent loan (by saleDate).
    Returns a dict mapping borrower name to last lender name.
    """
    borrower_to_latest: Dict[str, Dict] = {}
    for record in prepped_data:
        borrower = record.get("buyerName")
        date = record.get("saleDate")
        if not borrower or not date:
            continue
        if (
            borrower not in borrower_to_latest
            or date > borrower_to_latest[borrower]["saleDate"]
        ):
            borrower_to_latest[borrower] = record
    # Map borrower to their last lender
    return {
        borrower: rec.get("lenderName", "")
        for borrower, rec in borrower_to_latest.items()
    }


def get_borrower_to_lender_num_loans(
    prepped_data: List[Dict], lender: str
) -> Dict[str, int]:
    """
    Returns a dictionary mapping each borrower to the number of loans
    they have taken from the specified lender.
    """
    borrower_to_num_loans: Dict[str, int] = {}
    for record in prepped_data:
        if record.get("lenderName") != lender:
            continue
        borrower = record.get("buyerName")
        if not borrower:
            continue
        borrower_to_num_loans[borrower] = borrower_to_num_loans.get(borrower, 0) + 1

    return borrower_to_num_loans


def get_borrower_to_lender_volume(
    prepped_data: List[Dict], lender: str
) -> Dict[str, int]:
    borrower_to_volume: Dict[str, int] = {}
    for record in prepped_data:
        if record.get("lenderName") != lender:
            continue
        borrower = record.get("buyerName")
        amount = record.get("loanAmount", 0)
        if not borrower:
            continue
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            amount = 0
        borrower_to_volume[borrower] = borrower_to_volume.get(borrower, 0) + amount
    return borrower_to_volume


def get_borrower_to_lenders(prepped_data: List[Dict]) -> Dict[str, Set[str]]:
    """
    For each borrower (buyerName), return a list of unique lender names they've used.
    """
    borrower_to_lenders: Dict[str, set] = {}
    for record in prepped_data:
        borrower = record.get("buyerName")
        lender = record.get("lenderName")
        if not borrower or not lender:
            continue
        if borrower not in borrower_to_lenders:
            borrower_to_lenders[borrower] = set()
        borrower_to_lenders[borrower].add(lender)

    return borrower_to_lenders


def get_borrower_to_volume(prepped_data: List[Dict]) -> Dict[str, int]:
    """
    For each borrower (buyerName), return the sum of loanAmount for that
    borrower in prepped_data with all lenders.
    """
    borrower_to_total: Dict[str, float] = {}
    for record in prepped_data:
        borrower = record.get("buyerName")
        loan_amount = record.get("loanAmount")
        if loan_amount in (None, ""):
            continue
        try:
            loan_amount = float(loan_amount)
        except (TypeError, ValueError):
            continue
        if not borrower:
            continue
        if borrower not in borrower_to_total:
            borrower_to_total[borrower] = 0.0
        borrower_to_total[borrower] += loan_amount
    # Convert to int for display
    return {k: int(v) for k, v in borrower_to_total.items()}
