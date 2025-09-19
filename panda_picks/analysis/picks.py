import pandas as pd
import numpy as np
import logging
import time
from datetime import datetime

from panda_picks.db.database import get_connection
from panda_picks import config
from panda_picks.config.settings import Settings
from panda_picks.analysis.utils.probability import calculate_win_probability
# Added Bayesian blending imports
from panda_picks.analysis.bayesian_grades import recompute_blended_grades, load_blended_wide
# NEW: ensure prior snapshot exists automatically
from panda_picks.data.grades_migration import ensure_prior_populated
# NEW: team normalizer
from panda_picks.utils import normalize_df_team_cols
# NEW PHASE 3: model calibration utilities
from panda_picks.analysis.model_calibration import fit_margin_linear, compute_model_metrics

# ---------------- Centralized configuration via Settings ---------------- #
SIGNIFICANCE_THRESHOLDS = Settings.ADVANTAGE_THRESHOLDS  # shared mutable dict
K_PROB_SCALE = Settings.K_PROB_SCALE
EDGE_MIN = Settings.EDGE_MIN
MARGIN_K = Settings.MARGIN_K
MARGIN_SD = Settings.MARGIN_SD
MAX_PICKS_PER_WEEK = Settings.MAX_PICKS_PER_WEEK

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

def _round_numeric_cols(df: pd.DataFrame, decimals: int = 3) -> pd.DataFrame:
    try:
        num_cols = df.select_dtypes(include=[np.number]).columns
        if len(num_cols) > 0:
            df[num_cols] = df[num_cols].round(decimals)
    except Exception:
        pass
    return df

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
    # Always classify the classic three
    for col in PRIMARY_ADV_COLS:
        if col not in df.columns:
            continue
        thresh = SIGNIFICANCE_THRESHOLDS.get(col, 0)
        sig_col = f'{col}_sig'
        df[sig_col] = np.select(
            [df[col] >= thresh, df[col] <= -thresh],
            ['home significant', 'away significant'],
            default='insignificant'
        )
    # Also classify blended if available and non-null in this dataset
    if 'Blended_Adv' in df.columns and df['Blended_Adv'].notna().any():
        bthresh = SIGNIFICANCE_THRESHOLDS.get('Blended_Adv', SIGNIFICANCE_THRESHOLDS.get('Overall_Adv', 0))
        df['Blended_Adv_sig'] = np.select(
            [df['Blended_Adv'] >= bthresh, df['Blended_Adv'] <= -bthresh],
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
        # Fallback simple logistic preferring Blended_Adv when available per-row
        def _adv_for_row(r):
            bv = r.get('Blended_Adv')
            if pd.notna(bv):
                return float(bv)
            return float(r.get('Overall_Adv', 0.0))
        df['Home_Win_Prob'] = df.apply(lambda r: calculate_win_probability(_adv_for_row(r)), axis=1)
        df['Away_Win_Prob'] = 1 - df['Home_Win_Prob']
    return df


def _decide_picks(df: pd.DataFrame) -> pd.DataFrame:
    """Assign Game_Pick based on one-sided significant advantages.
    Prioritize blended significance if available alongside Offense/Defense.
    """
    pick_side = []
    use_cols = ['Offense_Adv', 'Defense_Adv']
    if 'Blended_Adv_sig' in df.columns:
        use_cols = ['Blended_Adv'] + use_cols
    else:
        use_cols = ['Overall_Adv'] + use_cols
    for _, row in df.iterrows():
        signals = [row.get(f'{c}_sig', 'insignificant') for c in use_cols]
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
    # Normalize team names centrally
    grades = normalize_df_team_cols(grades, ['Home_Team'])

  # USE_BAYES_GRADES:
    try:
        prior_rows = ensure_prior_populated()
        logging.info(f"Bayes: ensure_prior_populated -> {prior_rows} rows in grades_prior")
        recompute_blended_grades(conn)
        blended = load_blended_wide(conn)
        if not blended.empty:
            metric_cols = [c for c in ['OVR','OFF','DEF','PASS','PBLK','RECV','RUN','RBLK','PRSH','COV','RDEF','TACK'] if c in grades.columns]
            grades = grades.merge(blended, on='Home_Team', how='left', suffixes=('', '_BLEND'))
            replaced = 0
            for m in metric_cols:
                if m+'_BLEND' in grades.columns:
                    mask = grades[m + '_BLEND'].notna()
                    if mask.any():
                        grades.loc[mask, m] = grades.loc[mask, m + '_BLEND']
                        replaced += mask.sum()
            logging.info(f"Bayes: applied blended metrics to {replaced} team rows.")
            # Simple diagnostic: average weight if available
            try:
                weight_df = pd.read_sql_query("SELECT Metric, AVG(Weight_Current) avg_w FROM blended_grades GROUP BY Metric", conn)
                logging.info("Bayes: average weights -> " + ", ".join(f"{r.Metric}:{r.avg_w:.3f}" for r in weight_df.itertuples()))
            except Exception:
                pass
        else:
            logging.warning("Bayes: blended table empty after recompute (check prior & current grades)")
    except Exception as e:
        logging.warning(f"Bayesian grade blending failed; using raw grades ({e})")

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


def makePicks(weeks: list[int] | list[str] | None = None):
    """Generate picks for specified weeks (default all weeks 1..18).

    Args:
        weeks: Optional list of week numbers (ints) or strings (e.g., ['2','3']).
               If None, processes all weeks 1..18.
    """
    print(f"[{time.strftime('%H:%M:%S')}] makePicks started")
    logging.basicConfig(level=logging.INFO)
    if weeks is None:
        week_numbers = list(range(1,19))
    else:
        # Normalize
        norm = []
        for w in weeks:
            try:
                norm.append(int(str(w).strip()))
            except Exception:
                continue
        week_numbers = sorted({w for w in norm if 1 <= w <= 18})
        if not week_numbers:
            logging.warning("No valid weeks supplied; defaulting to full season 1-18")
            week_numbers = list(range(1,19))
    logging.info(f"Processing weeks: {week_numbers}")
    conn = get_connection()

    try:
        # Dynamically load tuned thresholds if available
        _load_best_thresholds(conn)
        grades, opp_grades = _prepare_grades(conn)

        for w in week_numbers:
            w_str = str(w)
            spreads_query = f"SELECT * FROM spreads WHERE WEEK = 'WEEK{w_str}'"
            matchups = pd.read_sql_query(spreads_query, conn)
            if matchups.empty:
                logging.info(f"Week {w_str}: no spreads data; skipping")
                continue
            # Normalize team codes from spreads to be resilient across feeds
            matchups = normalize_df_team_cols(matchups, ['Home_Team','Away_Team'])
            matchups = pd.merge(matchups, grades, on='Home_Team', how='left')
            matchups = pd.merge(matchups, opp_grades, on='Away_Team', how='left')

            for col in matchups.columns:
                if col not in ['Home_Team', 'Away_Team', 'WEEK']:
                    matchups[col] = pd.to_numeric(matchups[col], errors='coerce')

            results = _calculate_advantages(matchups.copy())
            # Attach Phase 2 features
            results = _attach_advanced_matchup_features(conn, results, int(w))
            results = _classify_significance(results)
            results = _compute_probabilities(results, conn)
            results = _decide_picks(results)
            results = _compute_market_and_edges(results)
            results = results[results['Game_Pick'] != 'No Pick']
            if results.empty:
                logging.info(f"Week {w_str}: no confident picks after filtering")
                continue
            results = _apply_edge_filter(results)
            if results.empty:
                logging.info(f"Week {w_str}: no picks passed edge filter")
                continue
            # PHASE 3: fit linear margin model on prior weeks and compute model metrics
            model_params = None
            if Settings.MODEL_ENABLED and int(w) > Settings.MODEL_MIN_TRAIN_WEEKS:
                try:
                    season_now = datetime.now().year
                    model_params = fit_margin_linear(conn, season_now, int(w), None)
                    if model_params:
                        logging.info(f"Week {w_str}: fitted margin model with n={model_params.n}, r2={model_params.r2:.3f}, resid_std={model_params.resid_std:.2f}")
                    else:
                        logging.info(f"Week {w_str}: insufficient data to fit margin model; using fallback")
                except Exception as e:
                    logging.info(f"Week {w_str}: model fit failed ({e}); using fallback")
            results = compute_model_metrics(results, model_params, int(w))
            # Apply model-edge gating only if model trained
            if Settings.MODEL_ENABLED and model_params is not None:
                before_model = len(results)
                results = results[results['Model_Edge'] >= Settings.MODEL_MIN_EDGE]
                logging.info(f"Week {w_str}: model edge gate {before_model} -> {len(results)} (MIN_EDGE={Settings.MODEL_MIN_EDGE})")
                if results.empty:
                    logging.info(f"Week {w_str}: no picks passed model edge gate")
                    continue
            # Existing cover probability (normal approx) retained as Pick_Cover_Prob for comparison
            results = _compute_cover_probabilities(results)
            # Prefer sorting by blended advantage if available
            sort_adv_col = 'Blended_Adv' if 'Blended_Adv' in results.columns else 'Overall_Adv'
            results = results.sort_values(by=['Pick_Edge', sort_adv_col], ascending=[False, False])
            if len(results) > MAX_PICKS_PER_WEEK:
                # Log trimmed games for diagnostics
                trimmed = results.iloc[MAX_PICKS_PER_WEEK:][['Home_Team','Away_Team','Pick_Edge',sort_adv_col,'Game_Pick']].copy()
                if not trimmed.empty:
                    logging.info(
                        "Week %s: trimmed %d games due to MAX_PICKS_PER_WEEK=%d. Trimmed list: %s",
                        w_str, len(trimmed), MAX_PICKS_PER_WEEK,
                        '; '.join(f"{r.Away_Team}@{r.Home_Team} pick={r.Game_Pick} edge={r.Pick_Edge:.4f} adv={getattr(r, sort_adv_col):+.1f}" for r in trimmed.itertuples())
                    )
                results = results.head(MAX_PICKS_PER_WEEK)
                logging.info(f"Week {w_str}: limited to top {MAX_PICKS_PER_WEEK} picks by Pick_Edge")
            output_cols = [
                'WEEK', 'Home_Team', 'Away_Team', 'Home_Line_Close', 'Away_Line_Close', 'Home_Odds_Close', 'Away_Odds_Close',
                'Game_Pick', 'Overall_Adv', 'Offense_Adv', 'Defense_Adv',
                'Overall_Adv_sig', 'Offense_Adv_sig', 'Defense_Adv_sig', 'Blended_Adv_sig',
                'Pressure_Mismatch', 'Explosive_Pass_Mismatch', 'Script_Control_Mismatch',
                'Off_Comp_Diff','Def_Comp_Diff','Net_Composite','Net_Composite_norm','Blended_Adv',
                # Phase 3 additions
                'Expected_Margin','Cover_Prob','Model_Edge','Confidence_Score',
                'Home_Win_Prob', 'Away_Win_Prob', 'Home_ML_Implied', 'Away_ML_Implied', 'Pick_Prob', 'Pick_Implied_Prob', 'Pick_Edge', 'Pick_Cover_Prob'
            ]
            for c in output_cols:
                if c not in results.columns:
                    results[c] = np.nan
            results = results[output_cols]
            # Round numeric columns before persisting to DB
            results = _round_numeric_cols(results, 3)
            with conn:
                cur = conn.cursor()
                _ensure_columns(conn, 'picks', {
                    'Home_Win_Prob': 'REAL', 'Away_Win_Prob': 'REAL',
                    'Home_Odds_Close': 'REAL', 'Away_Odds_Close': 'REAL',
                    'Home_ML_Implied': 'REAL', 'Away_ML_Implied': 'REAL',
                    'Pick_Prob': 'REAL', 'Pick_Implied_Prob': 'REAL', 'Pick_Edge': 'REAL', 'Pick_Cover_Prob': 'REAL',
                    'Pressure_Mismatch': 'REAL', 'Explosive_Pass_Mismatch': 'REAL', 'Script_Control_Mismatch': 'REAL',
                    'Off_Comp_Diff': 'REAL','Def_Comp_Diff': 'REAL','Net_Composite': 'REAL','Net_Composite_norm': 'REAL','Blended_Adv': 'REAL',
                    'Blended_Adv_sig': 'TEXT',
                    # Phase 3 columns
                    'Expected_Margin': 'REAL','Cover_Prob': 'REAL','Model_Edge': 'REAL','Confidence_Score': 'REAL'
                })
                for home, away in zip(results['Home_Team'], results['Away_Team']):
                    cur.execute("DELETE FROM picks WHERE WEEK = ? AND Home_Team = ? AND Away_Team = ?", (f"WEEK{w_str}", home, away))
                results.to_sql('picks', conn, if_exists='append', index=False)
            logging.info(f"Week {w_str}: inserted {len(results)} picks")
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
        # Normalize team codes
        matchups = normalize_df_team_cols(matchups, ['Home_Team','Away_Team'])
        merged = pd.merge(matchups, grades, on='Home_Team', how='left')
        merged = pd.merge(merged, opp_grades, on='Away_Team', how='left')
        merged = _calculate_advantages(merged)
        # Attach Phase 2 features
        merged = _attach_advanced_matchup_features(conn, merged, int(week))
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
        # PHASE 3: fit and score model for a single week
        model_params = None
        if Settings.MODEL_ENABLED and int(week) > Settings.MODEL_MIN_TRAIN_WEEKS:
            try:
                season_now = datetime.now().year
                model_params = fit_margin_linear(conn, season_now, int(week), None)
                if model_params:
                    logger.info(f"Week {week_str}: fitted margin model with n={model_params.n}, r2={model_params.r2:.3f}, resid_std={model_params.resid_std:.2f}")
                else:
                    logger.info(f"Week {week_str}: insufficient data to fit margin model; using fallback")
            except Exception as e:
                logger.info(f"Week {week_str}: model fit failed ({e}); using fallback")
        merged = compute_model_metrics(merged, model_params, int(week))
        if Settings.MODEL_ENABLED and model_params is not None:
            before_model = len(merged)
            merged = merged[merged['Model_Edge'] >= Settings.MODEL_MIN_EDGE]
            logger.info(f"Week {week_str}: model edge gate {before_model} -> {len(merged)} (MIN_EDGE={Settings.MODEL_MIN_EDGE})")
            if merged.empty:
                logger.info(f"Week {week_str}: no picks passed model edge gate")
                return merged
        # Retain existing cover probability calc
        merged = _compute_cover_probabilities(merged)
        sort_adv_col = 'Blended_Adv' if 'Blended_Adv' in merged.columns else 'Overall_Adv'
        merged = merged.sort_values(by=['Pick_Edge', sort_adv_col], ascending=[False, False])
        # Enforce max picks per week
        if len(merged) > MAX_PICKS_PER_WEEK:
            merged = merged.head(MAX_PICKS_PER_WEEK)
            logger.info(f"Week {week_str}: limited to top {MAX_PICKS_PER_WEEK} picks by Pick_Edge")
        output_cols = [
            'WEEK', 'Home_Team', 'Away_Team', 'Home_Line_Close', 'Away_Line_Close', 'Home_Odds_Close', 'Away_Odds_Close',
            'Game_Pick', 'Overall_Adv', 'Offense_Adv', 'Defense_Adv',
            'Overall_Adv_sig', 'Offense_Adv_sig', 'Defense_Adv_sig', 'Blended_Adv_sig',
            'Pressure_Mismatch', 'Explosive_Pass_Mismatch', 'Script_Control_Mismatch',
            'Off_Comp_Diff','Def_Comp_Diff','Net_Composite','Net_Composite_norm','Blended_Adv',
            'Expected_Margin','Cover_Prob','Model_Edge','Confidence_Score',
            'Home_Win_Prob', 'Away_Win_Prob', 'Home_ML_Implied', 'Away_ML_Implied', 'Pick_Prob', 'Pick_Implied_Prob', 'Pick_Edge', 'Pick_Cover_Prob'
        ]
        for c in output_cols:
            if c not in merged.columns:
                merged[c] = np.nan
        picks_df = merged[output_cols]

        # Save CSV (optional)
        output_path = f"{config.DATA_DIR}/picks/WEEK{week_str}.csv"
        # Round numeric columns before saving/returning
        picks_df = _round_numeric_cols(picks_df, 3)
        picks_df.to_csv(output_path, index=False)
        logger.info(f"Week {week_str}: picks saved to {output_path}")
        return picks_df
    except Exception as e:
        logger.exception(f"generate_week_picks error for week {week_str}: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def _attach_advanced_matchup_features(conn, df: pd.DataFrame, week_int: int) -> pd.DataFrame:
    """Join matchup_features by Home/Away for the current season/week and compute normalization and blended advantage."""
    try:
        season = datetime.now().year
        feats = pd.read_sql_query(
            "SELECT Home_Team, Away_Team, off_comp_diff AS Off_Comp_Diff, def_comp_diff AS Def_Comp_Diff, net_composite AS Net_Composite "
            "FROM matchup_features WHERE season=? AND week=?",
            conn, params=[season, week_int]
        )
        if feats.empty:
            # Add empty columns
            for c in ['Off_Comp_Diff','Def_Comp_Diff','Net_Composite','Net_Composite_norm','Blended_Adv']:
                df[c] = np.nan
            return df
        # Normalize team codes
        feats = normalize_df_team_cols(feats, ['Home_Team','Away_Team'])
        merged = df.merge(feats, on=['Home_Team','Away_Team'], how='left')
        # Normalize Net_Composite within week (z-score)
        mu = merged['Net_Composite'].mean(skipna=True)
        sd = merged['Net_Composite'].std(skipna=True)
        if sd and sd > 0:
            merged['Net_Composite_norm'] = (merged['Net_Composite'] - mu) / sd
        else:
            merged['Net_Composite_norm'] = 0.0
        # Blended advantage
        alpha = Settings.BLEND_ALPHA
        merged['Blended_Adv'] = alpha * merged['Overall_Adv'].astype(float) + (1 - alpha) * merged['Net_Composite_norm'].astype(float)
        return merged
    except Exception as e:
        logging.warning(f"Failed to attach advanced matchup features for week {week_int}: {e}")
        for c in ['Off_Comp_Diff','Def_Comp_Diff','Net_Composite','Net_Composite_norm','Blended_Adv']:
            if c not in df.columns:
                df[c] = np.nan
        return df


if __name__ == '__main__':
    makePicks()