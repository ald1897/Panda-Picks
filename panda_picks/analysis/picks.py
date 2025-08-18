import pandas as pd
import numpy as np
import logging
import time

from panda_picks.db.database import get_connection
from panda_picks import config
from panda_picks.config.settings import Settings
from panda_picks.analysis.utils.probability import calculate_win_probability

# ---------------- Centralized configuration via Settings ---------------- #
SIGNIFICANCE_THRESHOLDS = Settings.ADVANTAGE_THRESHOLDS  # shared mutable dict
K_PROB_SCALE = Settings.K_PROB_SCALE
EDGE_MIN = Settings.EDGE_MIN
MARGIN_K = Settings.MARGIN_K
MARGIN_SD = Settings.MARGIN_SD

# Features expected by calibrated model
LOGIT_FEATURES = [
    'Overall_Adv', 'Offense_Adv', 'Defense_Adv', 'Pass_Rush_Adv', 'Coverage_Adv',
    'Receiving_Adv', 'Running_Adv', 'Run_Block_Adv', 'Home_Line_Close',
    # New engineered mismatch interaction features
    'Pressure_Mismatch', 'Explosive_Pass_Mismatch', 'Script_Control_Mismatch'
]
_LOGIT_MODEL = None  # cached model artifacts

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
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=\"" + table_name + "\"")
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


def _sigmoid(x):
    return 1 / (1 + np.exp(-x))


def _load_logit_model(conn):
    global _LOGIT_MODEL
    if _LOGIT_MODEL is not None:
        return _LOGIT_MODEL
    try:
        coeffs = pd.read_sql_query("SELECT feature, coefficient FROM model_logit_coeffs", conn)
        scaler = pd.read_sql_query("SELECT feature, mean, std FROM model_logit_scaler", conn)
        if coeffs.empty or scaler.empty:
            return None
        intercept_row = coeffs[coeffs['feature'] == 'intercept']
        intercept = 0.0 if intercept_row.empty else float(intercept_row['coefficient'].iloc[0])
        coeff_map = {r.feature: r.coefficient for r in coeffs.itertuples(index=False) if r.feature != 'intercept'}
        scaler_map = {r.feature: {'mean': r.mean, 'std': (r.std if r.std != 0 else 1.0)} for r in scaler.itertuples(index=False)}
        _LOGIT_MODEL = {
            'intercept': intercept,
            'coeffs': coeff_map,
            'scaler': scaler_map
        }
        logging.info("Loaded calibrated logistic model coefficients")
        return _LOGIT_MODEL
    except Exception as e:
        logging.info(f"Could not load calibrated model ({e}); using fallback probability")
        return None


def _compute_probabilities(df: pd.DataFrame, conn=None) -> pd.DataFrame:
    """Compute win probabilities using calibrated model if available, else fallback."""
    model = None
    if conn is not None:
        model = _load_logit_model(conn)
    if model:
        # Ensure required feature columns exist (fill missing with 0)
        for f in LOGIT_FEATURES:
            if f not in df.columns:
                df[f] = 0.0
        # Standardize & compute linear term
        linear_terms = np.full(len(df), model['intercept'], dtype=float)
        for f, coeff in model['coeffs'].items():
            if f not in df.columns:
                continue
            stats = model['scaler'].get(f, {'mean': 0.0, 'std': 1.0})
            std = stats['std'] if stats['std'] != 0 else 1.0
            standardized = (df[f].fillna(0.0) - stats['mean']) / std
            linear_terms += coeff * standardized
        probs = _sigmoid(linear_terms)
        df['Home_Win_Prob'] = probs.clip(0, 1)
        df['Away_Win_Prob'] = 1 - df['Home_Win_Prob']
    else:
        # Fallback simple logistic on overall advantage
        df['Home_Win_Prob'] = df['Overall_Adv'].apply(calculate_win_probability)
        df['Away_Win_Prob'] = 1 - df['Home_Win_Prob']
    return df


def _decide_picks(df: pd.DataFrame) -> pd.DataFrame:
    """Assign Game_Pick based on one-sided significant advantages.
    Only pick if at least one primary advantage is significant and no opposing significant signals.
    """
    pick_side = []
    for _, row in df.iterrows():
        signals = [row.get(f'{c}_sig', 'insignificant') for c in PRIMARY_ADV_COLS]
        home_sig = any(s == 'home significant' for s in signals)
        away_sig = any(s == 'away significant' for s in signals)
        if home_sig and not away_sig:
            pick_side.append(row['Home_Team'])
        elif away_sig and not home_sig:
            pick_side.append(row['Away_Team'])
        else:
            pick_side.append('No Pick')
    df['Game_Pick'] = pick_side
    return df


def _compute_market_and_edges(df: pd.DataFrame) -> pd.DataFrame:
    # Moneyline implied probabilities
    df['Home_ML_Implied'], df['Away_ML_Implied'] = zip(*df.apply(lambda r: _implied_probs(r.get('Home_Odds_Close'), r.get('Away_Odds_Close')), axis=1))
    # Edge for pick side (will compute after pick chosen, so placeholder here)
    return df


def _compute_cover_probabilities(df: pd.DataFrame) -> pd.DataFrame:
    # Approximate margin ~ Normal(mean = MARGIN_K * Overall_Adv, sd = MARGIN_SD)
    mean_margin = MARGIN_K * df['Overall_Adv']
    # Home spread = home line (negative means favorite). Probability home covers spread: P(margin > -home_line)
    # If pick is away, cover condition becomes margin < -home_line
    home_line = pd.to_numeric(df.get('Home_Line_Close'), errors='coerce')
    df['Home_Cover_Prob'] = 1 - _norm_cdf(-home_line, mu=mean_margin, sigma=MARGIN_SD)
    df['Away_Cover_Prob'] = 1 - df['Home_Cover_Prob']  # symmetry assumption
    # Pick cover probability
    df['Pick_Cover_Prob'] = df.apply(lambda r: r['Home_Cover_Prob'] if r['Game_Pick'] == r['Home_Team'] else (r['Away_Cover_Prob'] if r['Game_Pick'] == r['Away_Team'] else np.nan), axis=1)
    return df


def _apply_edge_filter(df: pd.DataFrame) -> pd.DataFrame:
    # After picks decided; compute pick-specific edge
    df['Pick_Prob'] = df.apply(lambda r: r['Home_Win_Prob'] if r['Game_Pick'] == r['Home_Team'] else (r['Away_Win_Prob'] if r['Game_Pick'] == r['Away_Team'] else np.nan), axis=1)
    df['Pick_Implied_Prob'] = df.apply(lambda r: r['Home_ML_Implied'] if r['Game_Pick'] == r['Home_Team'] else (r['Away_ML_Implied'] if r['Game_Pick'] == r['Away_Team'] else np.nan), axis=1)
    df['Pick_Edge'] = df['Pick_Prob'] - df['Pick_Implied_Prob']
    before = len(df)
    df = df[df['Pick_Edge'].abs() >= EDGE_MIN]
    logging.info(f"Edge filter: {before} -> {len(df)} picks (EDGE_MIN={EDGE_MIN})")
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
    # Engineered interaction / mismatch features
    matchups['Pressure_Mismatch'] = matchups['Pass_Block_Adv'] - matchups['Pass_Rush_Adv']
    matchups['Explosive_Pass_Mismatch'] = matchups['Receiving_Adv'] - matchups['Coverage_Adv']
    matchups['Script_Control_Mismatch'] = matchups['Run_Block_Adv'] - matchups['Run_Defense_Adv']
    return matchups


def _load_best_thresholds(conn):
    """Load best thresholds from threshold_tuning_results if available.
    Ordering priority: ROI_per_Pick desc, Accuracy desc, Picks desc.
    Falls back silently if table or columns missing.
    """
    try:
        df = pd.read_sql_query("SELECT * FROM threshold_tuning_results", conn)
        if df.empty:
            return
        sort_cols = [c for c in ['ROI_per_Pick', 'Accuracy', 'Picks'] if c in df.columns]
        if not sort_cols:
            return
        df = df.sort_values(by=sort_cols, ascending=[False]*len(sort_cols))
        best = df.iloc[0]
        global SIGNIFICANCE_THRESHOLDS
        # Only update if columns exist
        for k, col in [('Overall_Adv','Overall_Thresh'), ('Offense_Adv','Offense_Thresh'), ('Defense_Adv','Defense_Thresh')]:
            if col in best and not pd.isna(best[col]):
                SIGNIFICANCE_THRESHOLDS[k] = float(best[col])
        Settings.update_thresholds(**{k: SIGNIFICANCE_THRESHOLDS[k] for k in SIGNIFICANCE_THRESHOLDS})
        logging.info(f"Loaded tuned thresholds: {SIGNIFICANCE_THRESHOLDS}")
    except Exception as e:
        logging.info(f"Threshold tuning table not used ({e}) - using defaults {SIGNIFICANCE_THRESHOLDS}")


def _american_to_decimal(odds):
    try:
        odds = float(odds)
    except (TypeError, ValueError):
        return np.nan
    if odds > 0:
        return 1 + odds / 100.0
    return 1 + 100.0 / abs(odds)

def _implied_probs(home_odds, away_odds):
    home_dec = _american_to_decimal(home_odds)
    away_dec = _american_to_decimal(away_odds)
    if np.isnan(home_dec) and np.isnan(away_dec):
        return (np.nan, np.nan)
    raw_home = (1 / home_dec) if not np.isnan(home_dec) else np.nan
    raw_away = (1 / away_dec) if not np.isnan(away_dec) else np.nan
    # Handle single-sided availability
    if np.isnan(raw_home) and not np.isnan(raw_away):
        return (1 - raw_away, raw_away)
    if np.isnan(raw_away) and not np.isnan(raw_home):
        return (raw_home, 1 - raw_home)
    total = raw_home + raw_away
    if total == 0:
        return (np.nan, np.nan)
    return (raw_home / total, raw_away / total)

def _norm_cdf(x, mu=0.0, sigma=1.0):
    try:
        return 0.5 * (1 + np.math.erf((x - mu) / (sigma * np.sqrt(2))))
    except Exception:
        return np.nan


def makePicks():
    print(f"[{time.strftime('%H:%M:%S')}] makePicks started")
    logging.basicConfig(level=logging.INFO)
    weeks = [str(i) for i in range(1, 19)]
    conn = get_connection()

    try:
        # Dynamically load tuned thresholds if available
        _load_best_thresholds(conn)
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
            results = _compute_probabilities(results, conn)
            results = _decide_picks(results)
            results = _compute_market_and_edges(results)
            # Filter out passes pre-edge
            results = results[results['Game_Pick'] != 'No Pick']
            if results.empty:
                logging.info(f"Week {w}: no confident picks after filtering")
                continue
            # Edge filtering
            results = _apply_edge_filter(results)
            if results.empty:
                logging.info(f"Week {w}: no picks passed edge filter")
                continue
            # Cover probability
            results = _compute_cover_probabilities(results)
            # Sort by absolute edge descending, then Overall Advantage
            results = results.sort_values(by=['Pick_Edge','Overall_Adv'], ascending=[False, False])
            # Prepare output columns (retain backward compatibility + new metrics)
            output_cols = [
                'WEEK', 'Home_Team', 'Away_Team', 'Home_Line_Close', 'Away_Line_Close', 'Home_Odds_Close', 'Away_Odds_Close',
                'Game_Pick', 'Overall_Adv', 'Offense_Adv', 'Defense_Adv',
                'Overall_Adv_sig', 'Offense_Adv_sig', 'Defense_Adv_sig',
                'Pressure_Mismatch', 'Explosive_Pass_Mismatch', 'Script_Control_Mismatch',
                'Home_Win_Prob', 'Away_Win_Prob', 'Home_ML_Implied', 'Away_ML_Implied', 'Pick_Prob', 'Pick_Implied_Prob', 'Pick_Edge', 'Pick_Cover_Prob'
            ]
# Ensure only the desired columns are present (drop others like Home_Score / Away_Score)
            for c in output_cols:
                if c not in results.columns:
                    results[c] = np.nan
            results = results[output_cols]
            with conn:  # ensures transaction
                cur = conn.cursor()
                _ensure_columns(conn, 'picks', {
                    'Home_Win_Prob': 'REAL', 'Away_Win_Prob': 'REAL',
                    'Home_Odds_Close': 'REAL', 'Away_Odds_Close': 'REAL',
                    'Home_ML_Implied': 'REAL', 'Away_ML_Implied': 'REAL',
                    'Pick_Prob': 'REAL', 'Pick_Implied_Prob': 'REAL', 'Pick_Edge': 'REAL', 'Pick_Cover_Prob': 'REAL',
                    'Pressure_Mismatch': 'REAL', 'Explosive_Pass_Mismatch': 'REAL', 'Script_Control_Mismatch': 'REAL'
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
        _load_best_thresholds(conn)
        grades, opp_grades = _prepare_grades(conn)
        matchups = pd.read_sql_query("SELECT * FROM spreads WHERE WEEK = ?", conn, params=[f"WEEK{week_str}"])
        if matchups.empty:
            logger.warning(f"Week {week_str}: no spreads data")
            return pd.DataFrame()
        merged = pd.merge(matchups, grades, on='Home_Team', how='left')
        merged = pd.merge(merged, opp_grades, on='Away_Team', how='left')
        merged = _calculate_advantages(merged)
        merged = _classify_significance(merged)
        merged = _compute_probabilities(merged, conn)
        merged = _compute_market_and_edges(merged)
        merged = _decide_picks(merged)
        merged = merged[merged['Game_Pick'] != 'No Pick']
        if merged.empty:
            logger.info(f"Week {week_str}: no confident picks")
            return merged
        merged = _apply_edge_filter(merged)
        if merged.empty:
            logger.info(f"Week {week_str}: no picks passed edge filter")
            return merged
        merged = _compute_cover_probabilities(merged)
        merged = merged.sort_values(by=['Pick_Edge','Overall_Adv'], ascending=[False, False])
        output_cols = [
            'WEEK', 'Home_Team', 'Away_Team', 'Home_Line_Close', 'Away_Line_Close', 'Home_Odds_Close', 'Away_Odds_Close',
            'Game_Pick', 'Overall_Adv', 'Offense_Adv', 'Defense_Adv',
            'Overall_Adv_sig', 'Offense_Adv_sig', 'Defense_Adv_sig',
            'Pressure_Mismatch', 'Explosive_Pass_Mismatch', 'Script_Control_Mismatch',
            'Home_Win_Prob', 'Away_Win_Prob', 'Home_ML_Implied', 'Away_ML_Implied', 'Pick_Prob', 'Pick_Implied_Prob', 'Pick_Edge', 'Pick_Cover_Prob'
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