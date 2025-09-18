import itertools
import logging
import math
import time
from datetime import datetime

import numpy as np
import pandas as pd

from panda_picks.db.database import get_connection
from panda_picks.analysis.picks import ADVANTAGE_BASE_COLUMNS, K_PROB_SCALE
from panda_picks.config.settings import Settings
from panda_picks.analysis.utils.probability import calculate_win_probability

PRIMARY_ADV_COLS = ['Overall_Adv', 'Offense_Adv', 'Defense_Adv']


def _compute_advantages(df: pd.DataFrame) -> pd.DataFrame:
    for new_col, func in ADVANTAGE_BASE_COLUMNS:
        df[new_col] = df.apply(func, axis=1)
    return df


def _decide_pick(row, thresholds):
    votes = []
    for col, th in thresholds.items():
        val = row[col]
        if val >= th:
            votes.append('home')
        elif val <= -th:
            votes.append('away')
        else:
            votes.append('neutral')
    home_sig = any(v == 'home' for v in votes)
    away_sig = any(v == 'away' for v in votes)
    # Only pick if one-sided significance
    if home_sig and not away_sig:
        return row['Home_Team']
    if away_sig and not home_sig:
        return row['Away_Team']
    return 'PASS'


def _moneyline_profit(odds, stake=1.0):
    if pd.isna(odds):
        return 0.0
    odds = float(odds)
    if odds > 0:
        return stake * (odds / 100)
    return stake / (abs(odds) / 100)


def _logistic_prob(overall_adv):
    # Bridge to centralized function
    return calculate_win_probability(overall_adv)


def tune_thresholds(
    overall_range=range(1, 6),
    offense_range=range(1, 6),
    defense_range=range(1, 6),
    min_picks=1
):
    """Grid search thresholds and store results to DB using only real (recorded) scores.

    Args:
        overall_range: iterable of ints/floats for Overall_Adv threshold
        offense_range: thresholds for Offense_Adv
        defense_range: thresholds for Defense_Adv
        min_picks: minimum number of picks to include a result row
    """
    logging.info("Threshold tuning started")
    conn = get_connection()
    try:
        spreads = pd.read_sql_query("SELECT * FROM spreads", conn)
        grades = pd.read_sql_query("SELECT * FROM grades", conn)
        # Standardize team column names
        if 'TEAM' in grades.columns:
            grades = grades.rename(columns={'TEAM': 'Home_Team'})
        elif 'Team' in grades.columns:
            grades = grades.rename(columns={'Team': 'Home_Team'})
        opp_grades = grades.copy().rename(columns={
            'Home_Team': 'Away_Team',
            'OVR': 'OPP_OVR', 'OFF': 'OPP_OFF', 'DEF': 'OPP_DEF', 'PASS': 'OPP_PASS',
            'PBLK': 'OPP_PBLK', 'RECV': 'OPP_RECV', 'RUN': 'OPP_RUN', 'RBLK': 'OPP_RBLK',
            'PRSH': 'OPP_PRSH', 'COV': 'OPP_COV', 'RDEF': 'OPP_RDEF', 'TACK': 'OPP_TACK'
        })
        base = spreads.merge(grades, on='Home_Team', how='left').merge(opp_grades, on='Away_Team', how='left')
        base = _compute_advantages(base)
        # Determine outcomes (only for games with both scores present)
        base['Home_Score'] = pd.to_numeric(base['Home_Score'], errors='coerce')
        base['Away_Score'] = pd.to_numeric(base['Away_Score'], errors='coerce')
        base['Home_Win'] = base.apply(lambda r: 1 if (not pd.isna(r['Home_Score']) and not pd.isna(r['Away_Score']) and r['Home_Score'] > r['Away_Score']) else 0, axis=1)
        base['Has_Result'] = ~(base['Home_Score'].isna() | base['Away_Score'].isna())
        results_rows = []
        total_games = len(base)
        for o, off, d in itertools.product(overall_range, offense_range, defense_range):
            thresholds = {
                'Overall_Adv': float(o),
                'Offense_Adv': float(off),
                'Defense_Adv': float(d)
            }
            df = base.copy()
            df['Pick'] = df.apply(lambda r: _decide_pick(r, thresholds), axis=1)
            picked = df[df['Pick'] != 'PASS']
            if picked.empty or len(picked) < min_picks:
                continue
            eval_df = picked[picked['Has_Result']]
            if eval_df.empty:
                continue
            eval_df['Correct'] = eval_df.apply(lambda r: r['Pick'] == (r['Home_Team'] if r['Home_Win'] == 1 else r['Away_Team']), axis=1)
            accuracy = eval_df['Correct'].mean() if not eval_df.empty else np.nan
            # Profit using moneyline odds
            profits = []
            counted = 0
            for _, row in eval_df.iterrows():
                if row['Pick'] == row['Home_Team']:
                    odds = row.get('Home_Odds_Close')
                    if pd.isna(odds):
                        continue
                    profit = _moneyline_profit(odds) if row['Correct'] else -1.0
                else:
                    odds = row.get('Away_Odds_Close')
                    if pd.isna(odds):
                        continue
                    profit = _moneyline_profit(odds) if row['Correct'] else -1.0
                profits.append(profit)
                counted += 1
            total_profit = sum(profits)
            roi = total_profit / counted if counted else np.nan
            avg_prob = picked['Overall_Adv'].apply(_logistic_prob).mean()
            results_rows.append({
                'Overall_Thresh': o,
                'Offense_Thresh': off,
                'Defense_Thresh': d,
                'Total_Games': total_games,
                'Picks': len(picked),
                'Evaluated_Picks': counted,
                'Accuracy': accuracy,
                'Profit': total_profit,
                'ROI_per_Pick': roi,
                'Avg_Home_Win_Prob': avg_prob,
                'Timestamp': datetime.utcnow().isoformat()
            })
        if not results_rows:
            logging.warning("No threshold results generated (possibly no games with scores).")
            return pd.DataFrame()
        results_df = pd.DataFrame(results_rows)
        # Ranking metrics: sort by ROI then Accuracy then Picks (descending)
        results_df = results_df.sort_values(by=['ROI_per_Pick', 'Accuracy', 'Picks'], ascending=[False, False, False])
        # Store
        results_df.to_sql('threshold_tuning_results', conn, if_exists='replace', index=False)
        logging.info("Threshold tuning completed and results stored (threshold_tuning_results table).")
        return results_df
    finally:
        conn.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    df = tune_thresholds()
    if not df.empty:
        print(df.head(10))
