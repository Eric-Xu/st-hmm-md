from datetime import datetime
from typing import Dict, List


def get_avg_loan_amount(prepped_data: List[Dict]) -> float:
    total_loans: int = len(prepped_data)
    loan_amounts: List[int] = get_loan_amounts(prepped_data)
    avg_loan_amount: float = sum(loan_amounts) / total_loans if total_loans > 0 else 0

    return avg_loan_amount


def get_loan_amounts(prepped_data: List[Dict]) -> List[int]:
    loan_amounts: List[int] = [int(item.get("loanAmount", 0)) for item in prepped_data]

    return loan_amounts


def get_monthly_num_loans(prepped_data: List[Dict]) -> List[int]:
    """
    Counts the number of loans for each month based on the 'saleDate'
    field in the input data.
    Returns a list of 12 integers, where each element represents the number
    of loans originated in that month (index 0 = January, 11 = December).
    Months with no loans will have a count of 0.
    """
    # Initialize counts for each month (0-11 for Jan-Dec)
    monthly_counts = [0] * 12

    for loan in prepped_data:
        sale_date = loan.get("saleDate")
        if sale_date:
            try:
                # Parse the date string (format: YYYY-MM-DD)
                date_obj = datetime.strptime(sale_date, "%Y-%m-%d")
                # Get month (0-11, where 0=January)
                month_index = date_obj.month - 1
                monthly_counts[month_index] += 1
            except (ValueError, TypeError):
                # Skip invalid dates
                continue

    return monthly_counts


def get_total_loan_volume(prepped_data: List[Dict]) -> int:
    loan_amounts: List[int] = get_loan_amounts(prepped_data)
    total_volume: int = sum(loan_amounts)

    return total_volume
