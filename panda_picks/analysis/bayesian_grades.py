import logging
import pandas as pd
import numpy as np
import time  # added for timing
from panda_picks.config.settings import Settings

METRICS = ['OVR','OFF','DEF','PASS','PBLK','RECV','RUN','RBLK','PRSH','COV','RDEF','TACK']

BLENDED_TABLE = 'blended_grades'
BLENDED_WIDE_TABLE = 'blended_grades_wide'
PRIOR_TABLE = 'grades_prior'
CURRENT_TABLE = 'grades'       # current season partial grades


def _table_exists(conn, name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def _extract_week_number(conn) -> int:
    """Approximate current week using spreads/picks_results max WEEK with any completed score.
    Returns >=1; falls back to 1 if none.
    """
    cur = conn.cursor()
    week_num = 1
    try:
        if _table_exists(conn, 'spreads'):
            cur.execute("SELECT WEEK FROM spreads WHERE Home_Score IS NOT NULL AND Away_Score IS NOT NULL")
            weeks = [r[0] for r in cur.fetchall()]
            nums = [int(str(w).upper().replace('WEEK','')) for w in weeks if w and str(w).upper().startswith('WEEK') and str(w)[4:].isdigit()]
            if nums:
                week_num = max(nums)
    except Exception:
        pass
    return max(1, week_num)


def recompute_blended_grades(conn):
    start_ts = time.time()
    logging.info("Bayes: recompute_blended_grades invoked")
    if not Settings.USE_BAYES_GRADES:
        logging.info("Bayes: skipping (USE_BAYES_GRADES disabled)")
        return
    if not _table_exists(conn, PRIOR_TABLE) or not _table_exists(conn, CURRENT_TABLE):
        logging.warning("Bayes: prior or current table missing; aborting blend")
        return
    prior = pd.read_sql_query(f"SELECT * FROM {PRIOR_TABLE}", conn)
    current = pd.read_sql_query(f"SELECT * FROM {CURRENT_TABLE}", conn)
    logging.info(f"Bayes: loaded prior rows={len(prior)} current rows={len(current)}")
    if prior.empty or current.empty:
        logging.warning("Bayes: empty prior or current dataset; aborting blend")
        return
    # Normalize team column to Home_Team like elsewhere
    for df in (prior, current):
        if 'TEAM' in df.columns:
            df.rename(columns={'TEAM':'Home_Team'}, inplace=True)
        elif 'Team' in df.columns:
            df.rename(columns={'Team':'Home_Team'}, inplace=True)
    # Ensure all expected metric columns exist (add NaN where missing) to avoid KeyError when subset provided (tests)
    for df_name, df in [('prior', prior), ('current', current)]:
        missing = [m for m in METRICS if m not in df.columns]
        if missing:
            logging.debug(f"Bayes: adding missing metric cols to {df_name}: {missing}")
        for m in missing:
            df[m] = np.nan
    # Determine games played per team
    games_played = {}
    try:
        if _table_exists(conn, 'spreads'):
            spreads = pd.read_sql_query("SELECT Home_Team, Away_Team, Home_Score, Away_Score FROM spreads", conn)
            completed = spreads.dropna(subset=['Home_Score','Away_Score'])
            if not completed.empty:
                home_counts = completed.groupby('Home_Team').size()
                away_counts = completed.groupby('Away_Team').size()
                counts = home_counts.add(away_counts, fill_value=0).to_dict()
                games_played = {k:int(v) for k,v in counts.items()}
    except Exception as e:
        logging.warning(f"Bayes: error deriving games_played ({e})")
    current_week = _extract_week_number(conn)
    rows = []
    k_values = Settings.BAYES_K_VALUES
    cap_week = Settings.BAYES_MAX_RAMP_WEEK
    early_cap = Settings.BAYES_CAP_WEIGHT_EARLY

    merged = prior[['Home_Team'] + METRICS].merge(current[['Home_Team'] + METRICS], on='Home_Team', how='left', suffixes=('_PRIOR','_CUR'))
    logging.info(f"Bayes: merging prior+current teams merged_rows={len(merged)} week={current_week}")
    for _, r in merged.iterrows():
        team = r['Home_Team']
        n = games_played.get(team, 0)
        for m in METRICS:
            prior_val = r.get(f'{m}_PRIOR', np.nan)
            cur_val = r.get(f'{m}_CUR', np.nan)
            n_eff = 0 if pd.isna(cur_val) else n
            base_k = float(k_values.get(m, 5.0))
            effective_k = base_k * max(1e-6, Settings.BAYES_K_SCALE)
            weight_cur = n_eff / (n_eff + effective_k) if (n_eff + effective_k) > 0 else 0.0
            weight_cur *= max(0.0, Settings.BAYES_CURRENT_WEIGHT_MULTIPLIER)
            if current_week <= cap_week:
                ramp_frac = current_week / cap_week
                max_allowed = early_cap * ramp_frac
                if weight_cur > max_allowed:
                    weight_cur = max_allowed
            # Enforce minimum current season floor if at least one completed game
            if n_eff > 0 and weight_cur < Settings.BAYES_MIN_CURRENT_WEIGHT:
                logging.debug(f"Bayes: elevating weight floor team={team} metric={m} from {weight_cur:.4f} to floor {Settings.BAYES_MIN_CURRENT_WEIGHT:.4f}")
                weight_cur = Settings.BAYES_MIN_CURRENT_WEIGHT
            if weight_cur > 1:
                weight_cur = 1.0
            if weight_cur < 0:
                weight_cur = 0.0
            if pd.isna(prior_val) and pd.isna(cur_val):
                post = np.nan
            elif pd.isna(prior_val):
                post = cur_val
            elif pd.isna(cur_val) or weight_cur == 0:
                post = prior_val
            else:
                post = weight_cur * cur_val + (1 - weight_cur) * prior_val
            rows.append({
                'Home_Team': team,
                'Metric': m,
                'Prior': prior_val,
                'Current': cur_val,
                'Games_Played': n_eff,
                'k_value': base_k,
                'Effective_k': effective_k,
                'Weight_Current': weight_cur,
                'Blended': post,
                'Week_Number': current_week
            })
    blend_df = pd.DataFrame(rows)
    if blend_df.empty:
        logging.warning("Bayes: produced 0 blended rows")
        return
    zero_weight = (blend_df['Weight_Current'] == 0).sum()
    avg_weight = blend_df['Weight_Current'].mean()
    logging.info(f"Bayes: writing blended_grades rows={len(blend_df)} zero_weight_rows={zero_weight} avg_weight={avg_weight:.4f}")
    blend_df.to_sql(BLENDED_TABLE, conn, if_exists='replace', index=False)
    # Wide version (one row per team)
    wide = blend_df.pivot_table(index='Home_Team', columns='Metric', values='Blended').reset_index()
    wide.rename_axis(None, axis=1, inplace=True)
    wide.to_sql(BLENDED_WIDE_TABLE, conn, if_exists='replace', index=False)
    elapsed = (time.time() - start_ts) * 1000
    logging.info(f"Bayes: wrote wide table rows={len(wide)} elapsed_ms={elapsed:.1f}")


def load_blended_wide(conn) -> pd.DataFrame:
    """Return wide DataFrame with one row per team containing blended metric columns.
    Handles both legacy long-form (Metric/Blended) and new wide-form storage.
    """
    if not Settings.USE_BAYES_GRADES:
        return pd.DataFrame()
    if _table_exists(conn, BLENDED_WIDE_TABLE):
        try:
            df = pd.read_sql_query(f"SELECT * FROM {BLENDED_WIDE_TABLE}", conn)
            if df.empty:
                return pd.DataFrame()
            # Wide table already has columns per metric
            return df
        except Exception as e:
            logging.warning(f"Bayes: failed reading wide table ({e}); falling back to long form")
    if _table_exists(conn, BLENDED_TABLE):
        try:
            long_df = pd.read_sql_query(f"SELECT Home_Team, Metric, Blended FROM {BLENDED_TABLE}", conn)
            if long_df.empty:
                return pd.DataFrame()
            wide = long_df.pivot_table(index='Home_Team', columns='Metric', values='Blended').reset_index()
            wide.rename_axis(None, axis=1, inplace=True)
            return wide
        except Exception as e:
            logging.warning(f"Bayes: failed constructing wide from long ({e})")
    return pd.DataFrame()
