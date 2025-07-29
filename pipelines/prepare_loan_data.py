import os

import pandas as pd
import streamlit as st
from pandas import DataFrame

from constants.file import DATA_DIR, DATA_FILE, TMP_DATA_JSON, TMP_DIR
from utils.formatting import to_currency
from utils.io import load_df
from utils.outlier_detection import stddev_outlier_strategy

LOAN_AMOUNT_MAX_THRESHOLD = 10_000_000
OUTLIER_STD_DEV_THRESHOLD = 3.0


def _load_data() -> DataFrame:
    borrower_activities_df: DataFrame = load_df(os.path.join(DATA_DIR, DATA_FILE))
    print(f"Number of borrower activity records: {borrower_activities_df.size}")

    return borrower_activities_df


def _transform_data(borrower_activities_df: DataFrame) -> DataFrame:
    df_sorted = borrower_activities_df.sort_values(by="buyerName").copy()

    # Add a new column "borrower_num_loans" counting occurrences of each buyerName
    df_sorted["borrower_num_loans"] = df_sorted["buyerName"].map(
        df_sorted["buyerName"].value_counts()
    )

    # Add a new column "lender_num_loans" counting occurrences of each lenderName
    df_sorted["lender_num_loans"] = df_sorted["lenderName"].map(
        df_sorted["lenderName"].value_counts()
    )

    # Add a new column "borrower_num_lenders" counting unique lenderName for each buyerName
    lender_counts = df_sorted.groupby("buyerName")["lenderName"].nunique()
    df_sorted["borrower_num_lenders"] = df_sorted["buyerName"].map(lender_counts)

    # Add a new column "lender_num_borrowers" counting unique buyerName for each lenderName
    borrower_counts = df_sorted.groupby("lenderName")["buyerName"].nunique()
    df_sorted["lender_num_borrowers"] = df_sorted["lenderName"].map(borrower_counts)

    return df_sorted


def _remove_outliers(
    borrower_activities_df: DataFrame,
    strategy,
    column: str = "loanAmount",
    **strategy_kwargs,
) -> None:
    """
    Remove records from borrower_activities_df where the strategy function returns True for outliers.
    """
    # Convert column to numeric
    borrower_activities_df[column] = pd.to_numeric(
        borrower_activities_df[column], errors="coerce"
    )
    initial_count = len(borrower_activities_df)

    # Remove None values
    borrower_activities_df.dropna(subset=[column], inplace=True)
    after_conversion_count = len(borrower_activities_df)
    if initial_count != after_conversion_count:
        print(
            f"Removed {initial_count - after_conversion_count} records with invalid {column} values"
        )

    # Remove any loans over $10 million
    over_10m_count = (borrower_activities_df[column] > LOAN_AMOUNT_MAX_THRESHOLD).sum()
    if over_10m_count > 0:
        borrower_activities_df.drop(
            borrower_activities_df[
                borrower_activities_df[column] > LOAN_AMOUNT_MAX_THRESHOLD
            ].index,
            inplace=True,
        )
        print(
            f"Removed {over_10m_count} records with {column} > {to_currency(LOAN_AMOUNT_MAX_THRESHOLD)}"
        )

    # Use the strategy to get outlier mask (strategy prints its own bounds/statistics)
    outlier_mask = strategy(borrower_activities_df, column, **strategy_kwargs)
    before_outlier_count = len(borrower_activities_df)
    borrower_activities_df.drop(
        borrower_activities_df[outlier_mask].index, inplace=True
    )
    final_count = len(borrower_activities_df)
    removed_count = before_outlier_count - final_count

    print(f"Removed {removed_count} outlier records from {column}")
    print(f"Records before: {initial_count}, Records after: {final_count}")


def _save_data(prepped_data_df: DataFrame, prepped_data_file_path: str) -> None:
    print(f"Saving transformed borrower activities data to {prepped_data_file_path}")
    prepped_data_df.to_json(prepped_data_file_path, orient="records", lines=False)


@st.cache_data
def prep_data() -> str:
    borrower_activities_df: DataFrame = _load_data()

    _remove_outliers(
        borrower_activities_df,
        stddev_outlier_strategy,
        column="loanAmount",
        threshold=OUTLIER_STD_DEV_THRESHOLD,
    )

    prepped_data_df: DataFrame = _transform_data(borrower_activities_df)

    prepped_data_file_path = os.path.join(TMP_DIR, TMP_DATA_JSON)
    _save_data(prepped_data_df, prepped_data_file_path)

    return prepped_data_file_path
