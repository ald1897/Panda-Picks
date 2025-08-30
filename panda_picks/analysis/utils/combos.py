import itertools
import math
from typing import List, Dict, Any
import pandas as pd


def american_to_decimal(odds: float | int | str) -> float:
    try:
        o = float(odds)
    except (TypeError, ValueError):
        return math.nan
    if o > 0:
        return 1 + o / 100.0
    return 1 + 100.0 / abs(o)


def decimal_to_american(dec: float) -> float:
    try:
        d = float(dec)
        if d <= 1 or math.isnan(d):
            return math.nan
        if d >= 2.0:
            return (d - 1) * 100
        else:
            return -100 / (d - 1)
    except Exception:
        return math.nan


def _extract_pick_probability(row: pd.Series) -> float:
    # Prefer explicit Pick_Prob
    val = row.get('Pick_Prob')
    if pd.notna(val):
        return float(val)
    # Fallback to side-specific win prob
    if row.get('Game_Pick') == row.get('Home_Team'):
        return float(row.get('Home_Win_Prob', math.nan))
    if row.get('Game_Pick') == row.get('Away_Team'):
        return float(row.get('Away_Win_Prob', math.nan))
    return math.nan


def _extract_pick_decimal_odds(row: pd.Series) -> float:
    # Use the moneyline odds corresponding to the pick side
    if row.get('Game_Pick') == row.get('Home_Team'):
        return american_to_decimal(row.get('Home_Odds_Close'))
    if row.get('Game_Pick') == row.get('Away_Team'):
        return american_to_decimal(row.get('Away_Odds_Close'))
    return math.nan


def generate_bet_combinations(picks_df: pd.DataFrame, min_size: int = 2, max_size: int = 5) -> List[Dict[str, Any]]:
    """Generate all parlay combinations between min_size and max_size from picks_df.

    Returns list of dicts with keys:
      Size, Teams, Combined_Prob, Combined_Dec_Odds, Est_Payout_100
    Probabilities & odds gracefully degrade if inputs missing.
    """
    if picks_df is None or picks_df.empty:
        return []
    picks = picks_df.copy()
    combos: List[Dict[str, Any]] = []
    max_size = min(max_size, len(picks))

    def _format_line(val):
        try:
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return 'N/A'
            v = float(val)
            if abs(v) < 1e-9:
                return 'PK'
            return f"{v:+g}"  # includes sign, removes trailing zeros
        except Exception:
            return 'N/A'

    for r in range(min_size, max_size + 1):
        for indices in itertools.combinations(picks.index, r):
            rows = picks.loc[list(indices)]
            team_names = [row['Game_Pick'] for _, row in rows.iterrows()]
            probs = []
            odds_list = []
            leg_lines = []
            for _, row in rows.iterrows():
                p = _extract_pick_probability(row)
                if not math.isnan(p):
                    probs.append(p)
                o = _extract_pick_decimal_odds(row)
                if not math.isnan(o):
                    odds_list.append(o)
                # Line extraction
                current_line = math.nan
                if row.get('Game_Pick') == row.get('Home_Team'):
                    current_line = row.get('Home_Line_Close', math.nan)
                elif row.get('Game_Pick') == row.get('Away_Team'):
                    current_line = row.get('Away_Line_Close', math.nan)
                teaser_line = current_line + 6 if not (isinstance(current_line, float) and math.isnan(current_line)) else math.nan
                leg_lines.append({
                    'Team': row.get('Game_Pick'),
                    'Current_Line': current_line,
                    'Teaser_Line': teaser_line,
                    'Current_Line_Display': _format_line(current_line),
                    'Teaser_Line_Display': _format_line(teaser_line)
                })
            combined_prob = math.prod(probs) if probs and len(probs) == r else math.nan
            book_dec_odds = math.prod(odds_list) if odds_list and len(odds_list) == r else math.nan
            fair_dec_odds = (1/combined_prob) if combined_prob and not math.isnan(combined_prob) and combined_prob > 0 else math.nan
            fair_american = decimal_to_american(fair_dec_odds)
            book_american = decimal_to_american(book_dec_odds)
            # Edge vs book using probabilities (positive => value)
            book_implied_prob = (1/book_dec_odds) if book_dec_odds and not math.isnan(book_dec_odds) else math.nan
            parlay_edge = (combined_prob - book_implied_prob) if (not math.isnan(combined_prob) and not math.isnan(book_implied_prob)) else math.nan
            est_payout = (100 * (book_dec_odds - 1)) if not math.isnan(book_dec_odds) else math.nan
            combos.append({
                'Size': r,
                'Teams': ' / '.join(team_names),
                'Combined_Prob': combined_prob,
                'Book_Dec_Odds': book_dec_odds,
                'Book_American_Odds': book_american,
                'Fair_Dec_Odds': fair_dec_odds,
                'Fair_American_Odds': fair_american,
                'Parlay_Edge': parlay_edge,
                'Est_Payout_100': est_payout,
                'Leg_Lines': leg_lines
            })
    return combos
