import numpy as np
import pandas as pd
from pandas import DataFrame


def modified_zscore_outlier_strategy(
    df: DataFrame, column: str, threshold: float = 5.0
) -> pd.Series:
    """
    Returns a boolean Series where True indicates an outlier in the specified column using the Modified Z-Score method.
    Also prints the median, MAD, threshold, and outlier bounds.
    """
    values = pd.to_numeric(df[column], errors="coerce")
    median = float(np.median(values.dropna()))
    mad = float(np.median(np.abs(values.dropna() - median)))
    if mad == 0:
        # Avoid division by zero; treat all as non-outliers
        print(f"Median: {median:.2f}, MAD: {mad:.2f}")
        print("MAD is zero; no outliers detected.")
        return pd.Series([False] * len(df), index=df.index)
    modified_z_scores = 0.6745 * (values - median) / mad
    lower_bound = median - (threshold * mad / 0.6745)
    upper_bound = median + (threshold * mad / 0.6745)
    print(f"Outlier threshold (modified z-score): ±{threshold}")
    print(f"Median: {median:.2f}, MAD: {mad:.2f}")
    print(f"Outlier bounds: [{lower_bound:.2f}, {upper_bound:.2f}]")
    outliers = np.abs(modified_z_scores) > threshold

    return pd.Series(outliers, index=df.index)


def stddev_outlier_strategy(
    df: DataFrame, column: str, threshold: float = 3.0
) -> pd.Series:
    """
    Returns a boolean Series where True indicates an outlier in the specified
    column using the standard deviation method.
    Also prints the mean, std, threshold, and outlier bounds.

    Parameters:
        df (DataFrame): The input DataFrame.
        column (str): The column to check for outliers.
        threshold (float): Number of standard deviations from the mean to use
            as the cutoff for outliers. Higher values are less sensitive;
            lower values are more sensitive.
    """
    values = pd.to_numeric(df[column], errors="coerce")
    mean = float(np.mean(values.dropna()))
    std = float(np.std(values.dropna()))
    if std == 0:
        # Avoid division by zero; treat all as non-outliers
        print(f"Mean: {mean:.2f}, Std: {std:.2f}")
        print("Standard deviation is zero; no outliers detected.")
        return pd.Series([False] * len(df), index=df.index)
    lower_bound = mean - (threshold * std)
    upper_bound = mean + (threshold * std)
    print(f"Outlier threshold (standard deviations): ±{threshold}")
    print(f"Mean: {mean:.2f}, Std: {std:.2f}")
    print(f"Outlier bounds: [{lower_bound:.2f}, {upper_bound:.2f}]")
    outliers = (values < lower_bound) | (values > upper_bound)

    return pd.Series(outliers, index=df.index)
