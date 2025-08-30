from __future__ import annotations
from typing import Tuple
import pandas as pd


def compute_model_accuracy(picks: pd.DataFrame, results: pd.DataFrame) -> Tuple[float | None, pd.DataFrame]:
    """Compute overall and weekly accuracy.

    Args:
        picks: DataFrame with columns WEEK, Home_Team, Away_Team, Game_Pick
        results: DataFrame with columns WEEK, Home_Team, Away_Team, Winner
    Returns:
        (overall_accuracy or None if no rows, weekly_accuracy_df[Week, Accuracy])
    """
    required_picks = {"WEEK", "Home_Team", "Away_Team", "Game_Pick"}
    required_results = {"WEEK", "Home_Team", "Away_Team", "Winner"}
    if not required_picks.issubset(picks.columns) or not required_results.issubset(results.columns):
        return None, pd.DataFrame(columns=["Week", "Accuracy"])

    merged = picks.merge(results, on=["WEEK", "Home_Team", "Away_Team"], how="inner")
    if merged.empty:
        return None, pd.DataFrame(columns=["Week", "Accuracy"])
    merged["Correct"] = merged["Game_Pick"] == merged["Winner"]
    overall = float(merged["Correct"].mean()) if not merged.empty else None
    weekly = (
        merged.groupby("WEEK")["Correct"].mean()
        .reset_index()
        .rename(columns={"WEEK": "Week", "Correct": "Accuracy"})
    )
    return overall, weekly

__all__ = ["compute_model_accuracy"]

