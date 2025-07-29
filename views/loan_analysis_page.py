import math
from typing import Dict, List, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from constants.css import GREEN_HEX, RED_HEX
from constants.dataset import END_DATE, LOCATION, START_DATE
from pipelines.prepare_loan_data import prep_data
from utils.formatting import to_currency
from utils.gui import show_default_footer, show_st_h1, show_st_h2, show_st_info
from utils.io import load_json
from utils.metrics import get_avg_loan_amount, get_loan_amounts, get_monthly_num_loans

ABBR_MONTH_KEYS = [
    "a. Jan",
    "b. Feb",
    "c. Mar",
    "d. Apr",
    "e. May",
    "f. Jun",
    "g. Jul",
    "h. Aug",
    "i. Sep",
    "j. Oct",
    "k. Nov",
    "l. Dec",
]

FULL_MONTH_KEYS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def _create_polar_bar_chart(prepped_data: List[Dict]) -> alt.LayerChart:
    monthly_num_loans: List[int] = get_monthly_num_loans(prepped_data)
    month_to_num_loans: Dict[str, int] = _get_month_to_num_loans(monthly_num_loans)
    max_num_loans_month: str = max(month_to_num_loans.items(), key=lambda x: x[1])[0]
    max_num_loans: int = month_to_num_loans[max_num_loans_month]

    source = pd.DataFrame(
        {
            "month": month_to_num_loans.keys(),
            "loan_count": month_to_num_loans.values(),
        }
    )

    polar_bars = (
        alt.Chart(source)
        .mark_arc(stroke="white", fill=GREEN_HEX, tooltip=True)
        .encode(
            theta=alt.Theta("month:O"),
            radius=alt.Radius("loan_count").scale(type="linear"),
            radius2=alt.datum(1),
            tooltip=[
                alt.Tooltip("month", title="Month"),
                alt.Tooltip("loan_count", title="# Loans"),
            ],
        )
    )

    # Create the circular tick marks for the number of loan count
    tick_mark_config: Dict[str, int] = _get_polar_bar_tick_mark_config(max_num_loans)
    tick_mark_rings = (
        alt.Chart(
            pd.DataFrame(
                {
                    "ring": range(
                        tick_mark_config["tm_min"],
                        tick_mark_config["tm_max"] + 1,
                        tick_mark_config["tm_step"],
                    )
                }
            )
        )
        .mark_arc(stroke="lightgrey", fill=None)
        .encode(theta=alt.value(2 * math.pi), radius=alt.Radius("ring").stack(False))
    )
    tick_mark_labels = tick_mark_rings.mark_text(
        color="grey", radiusOffset=5, align="left"
    ).encode(text="ring", theta=alt.value(math.pi / 4))

    # Create the straight axis lines for the time of the day
    axis_lines = (
        alt.Chart(
            pd.DataFrame(
                {
                    "radius": tick_mark_config["tm_max"],
                    "theta": math.pi / 2,
                    "month": ["0. Dec", "3. Mar", "6. Jun", "9. Sep"],
                }  # "month" values are sorted in ascending order.
            )
        )
        .mark_arc(stroke="lightgrey", fill=None)
        .encode(
            theta=alt.Theta("theta").stack(True),
            radius=alt.Radius("radius"),
            radius2=alt.datum(1),
        )
    )
    axis_lines_labels = axis_lines.mark_text(
        color="grey",
        radiusOffset=5,
        thetaOffset=-math.pi / 4,
        # These adjustments could be left out with a larger radius offset, but they make the label positioning a bit clearner
        align=alt.expr(
            'datum.month == "4. Sep" ? "right" : datum.month == "1. Mar" ? "left" : "center"'
        ),
        baseline=alt.expr(
            'datum.month == "0. Dec" ? "bottom" : datum.month == "2. Jun" ? "top" : "middle"'
        ),
    ).encode(text="month")

    chart = alt.layer(
        tick_mark_rings,
        axis_lines,
        polar_bars,
        tick_mark_labels,
        axis_lines_labels,
    ).properties(height=300)

    return chart


def _get_month_to_num_loans(
    monthly_counts: List[int], month_key_type: str = "abbreviated"
) -> Dict[str, int]:
    if month_key_type == "abbreviated":
        month_keys = ABBR_MONTH_KEYS
    else:
        month_keys = FULL_MONTH_KEYS

    month_to_num_loans = dict(zip(month_keys, monthly_counts))
    return month_to_num_loans


def _get_selected_data(
    prepped_data: List[Dict], user_min_loan_amount: int, user_max_loan_amount: int
) -> List[Dict]:
    selected_data: List[Dict] = list()
    for borrower_activity in prepped_data:
        loan_amount: int = int(borrower_activity.get("loanAmount", 0))
        if loan_amount >= user_min_loan_amount and loan_amount <= user_max_loan_amount:
            selected_data.append(borrower_activity)

    return selected_data


def _prep_borrower_loan_data(selected_data: List[Dict]) -> List[Dict]:
    if not selected_data:
        return []

    # Extract loan amounts and create labels
    borrower_loan_data = []
    borrower_counts = {}  # Track how many times each borrower appears

    for i, activity in enumerate(selected_data):
        loan_amount = int(activity.get("loanAmount", 0))
        borrower_name = activity.get("buyerName", "N/A")

        # Count occurrences of this borrower name
        borrower_counts[borrower_name] = borrower_counts.get(borrower_name, 0) + 1

        # Create unique label - only add index if borrower appears multiple times
        if borrower_counts[borrower_name] > 1:
            unique_label = f"{borrower_name}_{borrower_counts[borrower_name]}"
        else:
            unique_label = borrower_name

        borrower_loan_data.append({"amount": loan_amount, "borrower": unique_label})

    # Sort by loan amount (highest to lowest)
    borrower_loan_data.sort(key=lambda x: x["amount"], reverse=True)

    return borrower_loan_data


def _show_bar_chart(borrower_loan_data: List[Dict]) -> None:
    """
    Display a bar chart of loan amounts ordered from lowest to highest. The
    native st.bar_chart cannot order the bar values so an Altair chart is
    used instead.
    """
    df = pd.DataFrame(borrower_loan_data)
    df = df.rename(columns={"borrower": "Borrower", "amount": "Loan Amount ($)"})
    df_sorted = df.sort_values(by="Loan Amount ($)", ascending=True)

    bar = (
        alt.Chart(df_sorted)
        .mark_bar(color=GREEN_HEX)
        .encode(
            x=alt.X("Borrower:N", sort=None, title="Borrower"),
            y=alt.Y("Loan Amount ($):Q", title="Loan Amount ($)"),
            tooltip=["Borrower", "Loan Amount ($)"],
        )
        .properties(height=500, width="container")
    )

    average_line = (
        alt.Chart(df_sorted)
        .mark_rule(color=RED_HEX, size=2)
        .encode(
            y="mean(Loan Amount ($)):Q",
            tooltip=[
                alt.Tooltip("mean(Loan Amount ($)):Q", title="Average Loan Amount")
            ],
        )
    )

    chart = alt.layer(bar, average_line)
    st.altair_chart(chart, use_container_width=True)


def _show_df(borrower_loan_data: List[Dict]) -> None:
    if not borrower_loan_data:
        show_st_info("no_data_selected")
        return

    amounts: List[int] = [int(item["amount"]) for item in borrower_loan_data]
    borrowers: List[str] = [item["borrower"] for item in borrower_loan_data]
    df = pd.DataFrame({"Borrower Name": borrowers, "Loan Amount": amounts})
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Borrower Name": st.column_config.TextColumn(
                "Borrower Name", width="medium"
            ),
            "Loan Amount": st.column_config.NumberColumn(
                "Loan Amount", width="small", format="dollar"
            ),
        },
    )


def _show_introduction(prepped_data: List[Dict]) -> None:
    total_loans: int = len(prepped_data)
    average_amount: float = get_avg_loan_amount(prepped_data)

    st.markdown(
        f"""
        Between {START_DATE} to {END_DATE}, a total of **{total_loans:,}** loans 
        were originated, with an average amount of **${average_amount:,.0f}**. 
        """
    )


def _show_loans_by_month(prepped_data: List[Dict]) -> None:
    monthly_num_loans: List[int] = get_monthly_num_loans(prepped_data)
    month_to_num_loans: Dict[str, int] = _get_month_to_num_loans(
        monthly_num_loans, month_key_type="full"
    )
    max_num_loans_month: str = max(month_to_num_loans.items(), key=lambda x: x[1])[0]
    max_num_loans: int = month_to_num_loans[max_num_loans_month]
    min_num_loans_month: str = min(month_to_num_loans.items(), key=lambda x: x[1])[0]
    min_num_loans: int = month_to_num_loans[min_num_loans_month]

    st.markdown(
        f"""
        #### Number of Loans by Month

        **{max_num_loans_month}** had the highest lending activity with 
        **{max_num_loans:,}** loan originations, while **{min_num_loans_month}** 
        was the slowest month with **{min_num_loans:,}**.
        """
    )


def _show_metrics_selected_data(borrower_loan_data: List[Dict]) -> None:
    amounts = [item["amount"] for item in borrower_loan_data]

    col1, col2, col3 = st.columns(3)
    col1.metric("Selected Loans", len(amounts))
    col2.metric("Average Amount", f"${sum(amounts)/len(amounts):,.0f}")
    col3.metric("Highest Amount", f"${max(amounts):,.0f}")


def _show_donut_chart(prepped_data: List[Dict]) -> None:
    bins_to_loan_amounts: Dict[str, List[int]] = {
        "(a)_under_100k": [],
        "(b)_100k_250k": [],
        "(c)_250k_500k": [],
        "(d)_500k_1m": [],
        "(e)_1m_2m": [],
        "(f)_over_2m": [],
    }

    for item in prepped_data:
        loan_amount = int(item.get("loanAmount", 0))
        if loan_amount < 100_000:
            bins_to_loan_amounts["(a)_under_100k"].append(loan_amount)
        elif 100_000 <= loan_amount < 250_000:
            bins_to_loan_amounts["(b)_100k_250k"].append(loan_amount)
        elif 250_000 <= loan_amount < 500_000:
            bins_to_loan_amounts["(c)_250k_500k"].append(loan_amount)
        elif 500_000 <= loan_amount < 1_000_000:
            bins_to_loan_amounts["(d)_500k_1m"].append(loan_amount)
        elif 1_000_000 <= loan_amount < 2_000_000:
            bins_to_loan_amounts["(e)_1m_2m"].append(loan_amount)
        else:
            bins_to_loan_amounts["(f)_over_2m"].append(loan_amount)

    source = pd.DataFrame(
        {
            "category": bins_to_loan_amounts.keys(),
            "num_loans": [len(v) for v in bins_to_loan_amounts.values()],
        }
    )

    donut_chart = (
        alt.Chart(source)
        .mark_arc(innerRadius=50)
        .encode(
            theta="num_loans",
            color=alt.Color(
                "category:N",
                legend=alt.Legend(
                    orient="bottom",
                    title="Categories",
                    titleAlign="center",
                ),
            ),
            tooltip=[
                alt.Tooltip("category", title="Loan Amount ($)"),
                alt.Tooltip("num_loans", title="Number of Loans"),
            ],
        )
        .properties(height=300)
    )

    st.altair_chart(donut_chart, use_container_width=True)


def _show_polar_bar_all_data(prepped_data: List[Dict]) -> None:
    polar_bar_chart: alt.LayerChart = _create_polar_bar_chart(prepped_data)
    st.altair_chart(polar_bar_chart, use_container_width=True)


def _get_polar_bar_tick_mark_config(max_num_loans: int) -> Dict[str, int]:
    tick_mark_config: Dict[str, int] = dict()

    unit: int = int(max_num_loans * 0.25)
    if unit > 250:
        step = 500
    elif unit > 100:
        step = 250
    elif unit > 50:
        step = 100
    elif unit > 25:
        step = 50
    elif unit > 10:
        step = 25
    elif unit > 5:
        step = 10
    else:
        step = 5

    # Calculate the next number higher than max_num_loans that is divisible by step
    if max_num_loans % step == 0:
        tm_max = max_num_loans
    else:
        tm_max = ((max_num_loans // step) + 1) * step

    tick_mark_config["tm_max"] = tm_max
    tick_mark_config["tm_min"] = step
    tick_mark_config["tm_step"] = step

    return tick_mark_config


def _show_metrics_all_data(prepped_data: List[Dict]) -> None:
    loan_amounts: List[int] = get_loan_amounts(prepped_data)
    min_amount: int = min(loan_amounts)
    average_amount: float = get_avg_loan_amount(prepped_data)
    max_amount: int = max(loan_amounts)

    col1, col2, col3 = st.columns(3)
    col1.metric("Min Amount", to_currency(min_amount), border=True)
    col2.metric("Average Amount", to_currency(average_amount), border=True)
    col3.metric("Max Amount", to_currency(max_amount), border=True)


def _show_slider(prepped_data: List[Dict]) -> Tuple[int, int]:
    max_loan_amount: int = max(int(item.get("loanAmount", 0)) for item in prepped_data)
    if max_loan_amount > 2_000_000:
        step = 100_000
    elif max_loan_amount > 1_000_000:
        step = 50_000
    else:
        step = 10_000

    col1, col2 = st.columns(2)
    min_amount_input = col1.text_input("Min Loan Amount:")
    max_amount_input = col2.text_input("Max Loan Amount:")
    try:
        min_amount_input = int(min_amount_input)
        max_amount_input = int(max_amount_input)
    except ValueError:
        min_amount_input = None
        max_amount_input = None

    slider_default_min = int(max_loan_amount * 0.1)
    slider_default_max = int(max_loan_amount * 0.9)

    # Validate user input
    valid_min = (
        isinstance(min_amount_input, int) and 0 <= min_amount_input <= max_loan_amount
    )
    valid_max = (
        isinstance(max_amount_input, int) and 0 <= max_amount_input <= max_loan_amount
    )
    if (min_amount_input is not None and not valid_min) or (
        max_amount_input is not None and not valid_max
    ):
        st.warning(
            f"Please enter valid numbers between 0 and {max_loan_amount:,} for both min and max loan amounts."
        )
        return slider_default_min, slider_default_max

    slider_min = min_amount_input if valid_min else slider_default_min
    slider_max = max_amount_input if valid_max else slider_default_max

    # Ensure both are int and not None
    if slider_min is None:
        slider_min = slider_default_min
    if slider_max is None:
        slider_max = slider_default_max
    slider_min = int(slider_min)
    slider_max = int(slider_max)

    user_min_loan_amount, user_max_loan_amount = st.slider(
        "**Select loans by adjusting the minimum and maximum loan amount.**",
        min_value=0,
        max_value=max_loan_amount,
        value=(slider_min, slider_max),
        step=step,
    )

    return user_min_loan_amount, user_max_loan_amount


def render_page() -> None:
    show_st_h1("Loan Analysis")
    show_st_h2(f"Market Overview: {LOCATION}", w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.write("")
    _show_introduction(prepped_data)

    st.write("")
    st.write("")
    _show_donut_chart(prepped_data)

    _show_metrics_all_data(prepped_data)

    st.write("")
    _show_loans_by_month(prepped_data)

    st.write("")
    _show_polar_bar_all_data(prepped_data)

    st.markdown("#### Loan Amount Distribution")

    st.write("")
    user_min_loan_amount, user_max_loan_amount = _show_slider(prepped_data)

    st.write("")
    selected_data: List[Dict] = _get_selected_data(
        prepped_data, user_min_loan_amount, user_max_loan_amount
    )

    borrower_loan_data: List[Dict] = _prep_borrower_loan_data(selected_data)

    if not borrower_loan_data:
        show_st_info("no_data_selected")
        return

    _show_bar_chart(borrower_loan_data)

    _show_metrics_selected_data(borrower_loan_data)

    st.write("")
    st.write("")
    _show_df(borrower_loan_data)

    show_default_footer()


render_page()
