"""Simple calibration utilities for mapping Net_Composite -> Expected_Margin and Cover_Prob.
Phase 3 implementation (no external deps beyond numpy/pandas/sqlite3).
"""
from __future__ import annotations
import sqlite3
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd
from datetime import datetime

from panda_picks.config.settings import Settings
from panda_picks.utils import normalize_df_team_cols


@dataclass
class LinearParams:
    intercept: float
    coeffs: Dict[str, float]
    resid_std: float
    n: int
    r2: float
    features: List[str]


def _collect_training_frame(conn: sqlite3.Connection, season: int, through_week: int,
                            features: List[str]) -> pd.DataFrame:
    """Build training frame from matchup_features joined with spreads (scores) for weeks < through_week.
    Columns returned: ['week','Home_Team','Away_Team'] + feature columns + ['Home_Line_Close','realized_margin']
    """
    # Map requested feature names (Title case) to DB columns (snake)
    feature_map = {
        'Net_Composite': 'net_composite',
        'Off_Comp_Diff': 'off_comp_diff',
        'Def_Comp_Diff': 'def_comp_diff',
    }
    mf_cols = [feature_map.get(f, f) for f in features]
    sel_cols = ', '.join(['mf.week', 'mf.Home_Team', 'mf.Away_Team'] + [f"mf.{c}" for c in mf_cols])
    q = (
        f"SELECT {sel_cols}, s.Home_Line_Close, s.Home_Score, s.Away_Score "
        "FROM matchup_features mf "
        "JOIN spreads s ON s.WEEK = ('WEEK' || mf.week) AND s.Home_Team = mf.Home_Team AND s.Away_Team = mf.Away_Team "
        "WHERE mf.season = ? AND mf.week < ? AND s.Home_Score IS NOT NULL AND s.Away_Score IS NOT NULL"
    )
    df = pd.read_sql_query(q, conn, params=[season, through_week])
    if df.empty:
        return df
    df = normalize_df_team_cols(df, ['Home_Team', 'Away_Team'])
    df['realized_margin'] = pd.to_numeric(df['Home_Score'], errors='coerce') - pd.to_numeric(df['Away_Score'], errors='coerce')
    # Ensure feature name columns exist in Title case for modeling convenience
    for f in features:
        src = feature_map.get(f, f)
        if src in df.columns:
            df[f] = pd.to_numeric(df[src], errors='coerce')
        else:
            df[f] = np.nan
    df['Home_Line_Close'] = pd.to_numeric(df['Home_Line_Close'], errors='coerce')
    df = df.dropna(subset=['realized_margin'])
    return df[['week', 'Home_Team', 'Away_Team'] + features + ['Home_Line_Close', 'realized_margin']]


def fit_margin_linear(conn: sqlite3.Connection, season: int, through_week: int,
                      features: Optional[List[str]] = None) -> Optional[LinearParams]:
    """Fit OLS: realized_margin ~ intercept + sum_i coef_i * feature_i using weeks < through_week.
    Returns None if insufficient data; else LinearParams with residual std and simple R^2.
    """
    feats = features or Settings.MODEL_USE_FEATURES
    train = _collect_training_frame(conn, season, through_week, feats)
    if train.empty or len(train) < max(8, Settings.MODEL_MIN_TRAIN_ROWS):
        return None
    # Design matrix with intercept
    X_cols = feats
    X = train[X_cols].fillna(train[X_cols].mean()).to_numpy(dtype=float)
    y = train['realized_margin'].to_numpy(dtype=float)
    # Add intercept column
    X_design = np.column_stack([np.ones(len(X)), X])
    try:
        beta, residuals, rank, s = np.linalg.lstsq(X_design, y, rcond=None)
    except Exception:
        return None
    intercept = float(beta[0])
    coeffs = {col: float(val) for col, val in zip(X_cols, beta[1:])}
    y_hat = X_design @ beta
    resid = y - y_hat
    resid_std = float(np.std(resid, ddof=min(len(beta), len(y)) if len(y) > len(beta) else 1))
    # R^2 (guard division by zero)
    ss_tot = float(np.var(y) * len(y))
    ss_res = float(np.sum(resid ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    return LinearParams(intercept=intercept, coeffs=coeffs, resid_std=resid_std, n=len(train), r2=r2, features=X_cols)


def predict_margin(df: pd.DataFrame, params: LinearParams) -> np.ndarray:
    """Predict expected margin for rows in df given params. Missing features -> 0 contribution."""
    if params is None:
        return np.zeros(len(df))
    out = np.full(len(df), params.intercept, dtype=float)
    for f, w in params.coeffs.items():
        vals = pd.to_numeric(df.get(f), errors='coerce') if f in df.columns else np.zeros(len(df))
        vals = vals.fillna(0.0) if isinstance(vals, pd.Series) else np.nan_to_num(vals)
        out += w * vals.to_numpy(dtype=float) if isinstance(vals, pd.Series) else w * vals
    return out


def _logistic(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-x))


def cover_probability(expected_margin: np.ndarray | float, home_line: np.ndarray | float, scale: float) -> np.ndarray | float:
    """Approximate P(home covers spread) using logistic on margin + home_line.
    Cover condition: margin > -home_line => margin + home_line > 0.
    """
    x = (np.asarray(expected_margin) + np.asarray(home_line)) / max(scale, 1e-6)
    return _logistic(x)


def breakeven_prob(american_odds: Optional[float]) -> float:
    """Return breakeven probability for given American odds (default -110 if None/NaN)."""
    try:
        odds = float(american_odds)
    except (TypeError, ValueError):
        odds = float(Settings.MODEL_DEFAULT_SPREAD_PRICE)
    if odds >= 0:
        return 100.0 / (odds + 100.0)
    return (-odds) / ((-odds) + 100.0)


def compute_model_metrics(df: pd.DataFrame, params: Optional[LinearParams], week_int: int) -> pd.DataFrame:
    """Compute Expected_Margin, Cover_Prob (for pick side), Model_Edge, Confidence_Score for current rows.
    Assumes df has columns: ['Home_Team','Away_Team','Game_Pick','Home_Line_Close'] and requested features.
    """
    if df.empty:
        for c in ['Expected_Margin','Cover_Prob','Model_Edge','Confidence_Score']:
            if c not in df.columns:
                df[c] = np.nan
        return df
    # Determine scale
    if params is None or Settings.MODEL_COVER_SCALE_STRATEGY == 'fixed':
        scale = float(Settings.MODEL_COVER_SCALE_FIXED)
    else:
        # Clamp resid_std to reasonable bounds
        scale = float(np.clip(params.resid_std if params.resid_std > 0 else Settings.MODEL_COVER_SCALE_FIXED,
                              Settings.MODEL_COVER_SCALE_MIN, Settings.MODEL_COVER_SCALE_MAX))
    # Predict expected margin
    if params is None:
        exp_margin = np.zeros(len(df))
    else:
        exp_margin = predict_margin(df, params)
    df['Expected_Margin'] = exp_margin
    # Home cover probability via logistic; pick cover prob depends on side
    home_line = pd.to_numeric(df.get('Home_Line_Close'), errors='coerce').to_numpy(dtype=float)
    hc = cover_probability(exp_margin, home_line, scale)
    hc = np.asarray(hc, dtype=float)
    n = len(df)
    if hc.shape == ():
        hc = np.full(n, float(hc))
    # Build pick-side masks and vectorize
    mask_home = (df['Game_Pick'] == df['Home_Team']).to_numpy()
    mask_away = (df['Game_Pick'] == df['Away_Team']).to_numpy()
    cover = np.full(n, np.nan, dtype=float)
    cover[mask_home] = hc[mask_home]
    cover[mask_away] = 1.0 - hc[mask_away]
    df['Cover_Prob'] = cover
    # Edge vs default spread price (no per-side juice in DB, so use config)
    be = breakeven_prob(Settings.MODEL_DEFAULT_SPREAD_PRICE)
    df['Model_Edge'] = df['Cover_Prob'] - be
    # Confidence: distance from tipping point (margin + line == 0), normalized by 2*scale
    dist = np.abs(exp_margin + np.nan_to_num(home_line))
    df['Confidence_Score'] = np.minimum(1.0, (dist / (2.0 * max(scale, 1e-6))).astype(float))
    return df

