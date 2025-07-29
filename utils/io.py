import json
from typing import Any, Dict

import pandas as pd
from pandas import DataFrame

from utils.path import append_file_path


def load_df(path: str, sep=",", fillna="None") -> DataFrame:
    try:
        df = pd.read_csv(path, sep=sep, dtype=str)
        df = df.fillna(fillna)
    except FileNotFoundError as e:
        print(f"Error: {e}")

    return df


def load_json(path: str) -> Any:
    try:
        with open(path, "r") as file:
            json_dict = json.load(file)
    except FileNotFoundError as e:
        print(f"Error: {e}")

    return json_dict


def save_json(path: str, json_dict: Dict) -> None:
    append_file_path(path)

    with open(path, "w") as file:
        json.dump(json_dict, file)
