def to_currency(loan_amount: str | int | float) -> str:
    """
    Converts a loan amount (string, int, or float) to a formatted currency string
    (e.g., $1,234,567). Returns 'N/A' if the input is not a valid number.
    """
    try:
        amount = float(loan_amount)
        return f"${amount:,.0f}"
    except (ValueError, TypeError):
        return "N/A"
