import pandas as pd
import numpy as np
import logging
import time

from panda_picks.db.database import get_connection
from panda_picks import config

# ---------------- New configuration / helper functions ---------------- #
SIGNIFICANCE_THRESHOLDS = {
    'Overall_Adv': 2.0,      # tune later via backtest
    'Offense_Adv': 2.0,
    'Defense_Adv': 2.0
}
K_PROB_SCALE = 0.10  # scaling factor to convert grade diff to win probability proxy

ADVANTAGE_BASE_COLUMNS = [
    ('Overall_Adv', lambda r: r['OVR'] - r['OPP_OVR']),
    ('Offense_Adv', lambda r: r['OFF'] - r['OPP_DEF']),
    ('Defense_Adv', lambda r: r['DEF'] - r['OPP_OFF']),
    ('Passing_Adv', lambda r: r['PASS'] - r['OPP_COV']),
    ('Pass_Block_Adv', lambda r: r['PBLK'] - r['OPP_PRSH']),
    ('Receiving_Adv', lambda r: r['RECV'] - r['OPP_COV']),
    ('Running_Adv', lambda r: r['RUN'] - r['OPP_RDEF']),
    ('Run_Block_Adv', lambda r: r['RBLK'] - r['OPP_RDEF']),
    ('Run_Defense_Adv', lambda r: r['RDEF'] - r['OPP_RUN']),
    ('Pass_Rush_Adv', lambda r: r['PRSH'] - r['OPP_PBLK']),
    ('Coverage_Adv', lambda r: r['COV'] - r['OPP_RECV']),
    ('Tackling_Adv', lambda r: r['TACK'] - r['OPP_RUN'])
]

PRIMARY_ADV_COLS = ['Overall_Adv', 'Offense_Adv', 'Defense_Adv']

# ---- Schema helpers ---- #

def _table_exists(conn, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None

def _ensure_columns(conn, table_name: str, cols_types: dict):
    if not _table_exists(conn, table_name):
        return
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    existing = {row[1] for row in cur.fetchall()}
    for col, col_type in cols_types.items():
        if col not in existing:
            logging.info(f"Altering table {table_name}: adding missing column {col} {col_type}")
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type}")
    conn.commit()


def _classify_significance(df: pd.DataFrame) -> pd.DataFrame:
    for col in PRIMARY_ADV_COLS:
        thresh = SIGNIFICANCE_THRESHOLDS.get(col, 0)
        sig_col = f'{col}_sig'
        df[sig_col] = np.select(
            [df[col] >= thresh, df[col] <= -thresh],
            ['home significant', 'away significant'],
            default='insignificant'
        )
    return df


def _compute_probabilities(df: pd.DataFrame) -> pd.DataFrame:
    # Simple logistic transform of Overall_Adv to approximate a win probability (home perspective)
    df['Home_Win_Prob'] = 1 / (1 + np.exp(-K_PROB_SCALE * df['Overall_Adv']))
    df['Away_Win_Prob'] = 1 - df['Home_Win_Prob']
    return df


def _decide_picks(df: pd.DataFrame) -> pd.DataFrame:
    # Strategy: if any primary advantage passes threshold and points consistently toward one side, pick that side; else pass.
    # Determine directional consensus (majority of significant signals) ignoring insignificant ones.
    pick_side = []
    for _, row in df.iterrows():
        signals = [row[f'{c}_sig'] for c in PRIMARY_ADV_COLS]
        home_votes = sum(s == 'home significant' for s in signals)
        away_votes = sum(s == 'away significant' for s in signals)
        # If all insignificant -> no pick to avoid random noise
        if home_votes == 0 and away_votes == 0:
            pick_side.append('No Pick')
            continue
        # Require at least one significant signal AND no conflicting significant signals
        if home_votes > 0 and away_votes == 0:
            pick_side.append(row['Home_Team'])
        elif away_votes > 0 and home_votes == 0:
            pick_side.append(row['Away_Team'])
        else:
            pick_side.append('No Pick')
    df['Game_Pick'] = pick_side
    return df


def _prepare_grades(conn):
    grades = pd.read_sql_query("SELECT * FROM grades", conn)
    # Normalize team column names (handle both TEAM / Team)
    if 'TEAM' in grades.columns:
        grades = grades.rename(columns={'TEAM': 'Home_Team'})
    elif 'Team' in grades.columns:
        grades = grades.rename(columns={'Team': 'Home_Team'})

    opp_grades = grades.copy().rename(columns={
        'Home_Team': 'Away_Team',
        'OVR': 'OPP_OVR',
        'OFF': 'OPP_OFF',
        'DEF': 'OPP_DEF',
        'PASS': 'OPP_PASS',
        'PBLK': 'OPP_PBLK',
        'RECV': 'OPP_RECV',
        'RUN': 'OPP_RUN',
        'RBLK': 'OPP_RBLK',
        'PRSH': 'OPP_PRSH',
        'COV': 'OPP_COV',
        'RDEF': 'OPP_RDEF',
        'TACK': 'OPP_TACK'
    })
    return grades, opp_grades


def _calculate_advantages(matchups: pd.DataFrame) -> pd.DataFrame:
    for new_col, func in ADVANTAGE_BASE_COLUMNS:
        matchups[new_col] = matchups.apply(func, axis=1)
    return matchups


def makePicks():
    print(f"[{time.strftime('%H:%M:%S')}] makePicks started")
    logging.basicConfig(level=logging.INFO)
    weeks = [str(i) for i in range(1, 19)]
    conn = get_connection()

    try:
        grades, opp_grades = _prepare_grades(conn)

        for w in weeks:
            # Read spreads (correct column name is WEEK)
            spreads_query = f"SELECT * FROM spreads WHERE WEEK = 'WEEK{w}'"
            matchups = pd.read_sql_query(spreads_query, conn)
            if matchups.empty:
                logging.info(f"Week {w}: no spreads data; skipping")
                continue
            matchups = pd.merge(matchups, grades, on='Home_Team', how='left')
            matchups = pd.merge(matchups, opp_grades, on='Away_Team', how='left')

            # Convert numeric columns (skip identifiers)
            for col in matchups.columns:
                if col not in ['Home_Team', 'Away_Team', 'WEEK']:
                    matchups[col] = pd.to_numeric(matchups[col], errors='coerce')

            results = _calculate_advantages(matchups.copy())
            results = _classify_significance(results)
            results = _compute_probabilities(results)
            results = _decide_picks(results)

            # Filter out passes
            results = results[results['Game_Pick'] != 'No Pick']
            if results.empty:
                logging.info(f"Week {w}: no confident picks after filtering")
                continue

            # Sort by higher absolute overall advantage (confidence proxy)
            results = results.sort_values(by=['Overall_Adv'], ascending=False)

            # Prepare output columns (retain backward compatibility)
            output_cols = [
                'WEEK', 'Home_Team', 'Away_Team', 'Home_Line_Close', 'Away_Line_Close',
                'Game_Pick', 'Overall_Adv', 'Offense_Adv', 'Defense_Adv',
                'Overall_Adv_sig', 'Offense_Adv_sig', 'Defense_Adv_sig',
                'Home_Win_Prob', 'Away_Win_Prob'
            ]
            missing_cols = [c for c in output_cols if c not in results.columns]
            for c in missing_cols:
                results[c] = np.nan
            results = results[output_cols]

            # Idempotent insert: delete existing rows for these games/week first
            with conn:  # ensures transaction
                cur = conn.cursor()
                # Ensure new columns exist if table pre-exists (schema migration)
                _ensure_columns(conn, 'picks', {
                    'Home_Win_Prob': 'REAL',
                    'Away_Win_Prob': 'REAL'
                })
                teams_pairs = list(zip(results['Home_Team'], results['Away_Team']))
                for home, away in teams_pairs:
                    cur.execute("DELETE FROM picks WHERE WEEK = ? AND Home_Team = ? AND Away_Team = ?", (f"WEEK{w}", home, away))
                results.to_sql('picks', conn, if_exists='append', index=False)
            logging.info(f"Week {w}: inserted {len(results)} picks")
    except Exception as e:
        logging.exception(f"makePicks failed: {e}")
    finally:
        conn.close()
        print(f"[{time.strftime('%H:%M:%S')}] makePicks finished")


def generate_week_picks(week):
    """Generate picks for a specific week (refactored to reuse core logic)"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    week_str = str(week)
    conn = get_connection()

    try:
        grades, opp_grades = _prepare_grades(conn)
        matchups = pd.read_sql_query("SELECT * FROM spreads WHERE WEEK = ?", conn, params=[f"WEEK{week_str}"])
        if matchups.empty:
            logger.warning(f"Week {week_str}: no spreads data")
            return pd.DataFrame()
        merged = pd.merge(matchups, grades, on='Home_Team', how='left')
        merged = pd.merge(merged, opp_grades, on='Away_Team', how='left')
        merged = _calculate_advantages(merged)
        merged = _classify_significance(merged)
        merged = _compute_probabilities(merged)
        merged = _decide_picks(merged)
        merged = merged[merged['Game_Pick'] != 'No Pick']
        if merged.empty:
            logger.info(f"Week {week_str}: no confident picks")
            return merged
        merged = merged.sort_values(by='Overall_Adv', ascending=False)
        output_cols = [
            'WEEK', 'Home_Team', 'Away_Team', 'Home_Line_Close', 'Away_Line_Close',
            'Game_Pick', 'Overall_Adv', 'Offense_Adv', 'Defense_Adv',
            'Overall_Adv_sig', 'Offense_Adv_sig', 'Defense_Adv_sig',
            'Home_Win_Prob', 'Away_Win_Prob'
        ]
        for c in output_cols:
            if c not in merged.columns:
                merged[c] = np.nan
        picks_df = merged[output_cols]

        # Save CSV (optional)
        output_path = f"{config.DATA_DIR}/picks/WEEK{week_str}.csv"
        picks_df.to_csv(output_path, index=False)
        logger.info(f"Week {week_str}: picks saved to {output_path}")
        return picks_df
    except Exception as e:
        logger.exception(f"generate_week_picks error for week {week_str}: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


if __name__ == '__main__':
    makePicks()