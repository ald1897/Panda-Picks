"""Advanced feature engineering from advanced_stats + spreads.
Phase 1: build team-week and matchup features with diffs, momentum, trend placeholders.
"""
from __future__ import annotations
import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple
import pandas as pd
from panda_picks.db.database import get_connection
from panda_picks.utils import normalize_df_team_cols

TEAM_WEEK_COLS = ["TEAM","season","week","off_composite","def_composite"]

# Helper: fetch prior weeks composites for momentum/trend
def _fetch_team_history(conn: sqlite3.Connection, season: int, team: str, current_week: int) -> pd.DataFrame:
    q = """SELECT week, type, composite_score FROM advanced_stats
           WHERE season=? AND TEAM=? AND week < ?"""
    return pd.read_sql_query(q, conn, params=[season, team, current_week])

def _calc_momentum_and_trend(history: pd.DataFrame, stat_type: str, current_week: int) -> Tuple[float|None,float|None]:
    # history rows for given type only, last up to 3 weeks
    sub = history[history['type']==stat_type].copy()
    if sub.empty:
        return None, None
    sub = sub.sort_values('week').tail(3)
    if sub.empty:
        return None, None
    # momentum = mean of last up to 3 composite scores
    momentum = float(sub['composite_score'].mean()) if len(sub)>0 else None
    # trend: slope via simple linear regression week vs composite if >=2 points
    trend = None
    if len(sub) >= 2:
        x = sub['week'].values
        y = sub['composite_score'].values
        # slope = cov(x,y)/var(x)
        varx = ((x - x.mean())**2).sum()
        if varx > 0:
            cov = ((x - x.mean())*(y - y.mean())).sum()
            trend = float(cov/varx)
    return momentum, trend

def build_team_week_features(conn: sqlite3.Connection, season: int, week: int) -> pd.DataFrame:
    """Return team-level offensive & defensive composite scores for a week.
    Adds no momentum/trend here (computed per matchup for clarity)."""
    q = "SELECT TEAM, type, composite_score FROM advanced_stats WHERE season=? AND week=?"
    df = pd.read_sql_query(q, conn, params=[season, week])
    if df.empty:
        return pd.DataFrame(columns=TEAM_WEEK_COLS)
    # Normalize team codes in advanced stats
    df = normalize_df_team_cols(df, ['TEAM'])
    pivot = df.pivot_table(index='TEAM', columns='type', values='composite_score', aggfunc='first').reset_index()
    pivot.rename(columns={'offense':'off_composite','defense':'def_composite'}, inplace=True)
    pivot['season'] = season
    pivot['week'] = week
    if 'off_composite' not in pivot:
        pivot['off_composite'] = None
    if 'def_composite' not in pivot:
        pivot['def_composite'] = None
    return pivot[TEAM_WEEK_COLS]

def _impute_and_flag(row: pd.Series, league_means: Dict[str,float], flag: int) -> Tuple[pd.Series,int]:
    # Determine proper mean key (off_composite/def_composite) for each comp column
    for col in ['home_off_comp','home_def_comp','away_off_comp','away_def_comp']:
        if pd.isna(row.get(col)):
            mean_key = 'off_composite' if 'off_' in col else 'def_composite'
            row = row.copy()
            row[col] = league_means.get(mean_key, 0.0)
            flag = 1
    return row, flag

def build_matchup_features(conn: sqlite3.Connection, season: int, week: int) -> pd.DataFrame:
    """Create matchup-level features with diffs, momentum, trend, placeholders.
    Columns:
      core comps, diffs (off_comp_diff, def_comp_diff, net_composite), net_home_adv,
      momentum_* (last 3 weeks avg), trend_* (slope), pressure_mismatch, turnover_index, impute_flag.
    """
    team_feats = build_team_week_features(conn, season, week)
    if team_feats.empty:
        return pd.DataFrame()
    spreads = pd.read_sql_query("SELECT Home_Team, Away_Team FROM spreads WHERE WEEK=?", conn, params=[f"WEEK{week}"])
    if spreads.empty:
        return pd.DataFrame()
    # Normalize team codes in spreads as well
    spreads = normalize_df_team_cols(spreads, ['Home_Team','Away_Team'])

    # League means for imputation
    league_means = {
        'off_composite': float(team_feats['off_composite'].mean()) if not team_feats['off_composite'].isna().all() else 0.0,
        'def_composite': float(team_feats['def_composite'].mean()) if not team_feats['def_composite'].isna().all() else 0.0,
    }

    home = spreads.merge(team_feats, left_on='Home_Team', right_on='TEAM', how='left').rename(
        columns={'off_composite':'home_off_comp','def_composite':'home_def_comp'}
    )
    away = spreads.merge(team_feats, left_on='Away_Team', right_on='TEAM', how='left').rename(
        columns={'off_composite':'away_off_comp','def_composite':'away_def_comp'}
    )
    merged = home[['Home_Team','Away_Team','home_off_comp','home_def_comp']].merge(
        away[['Home_Team','Away_Team','away_off_comp','away_def_comp']], on=['Home_Team','Away_Team'], how='left'
    )

    # Compute diffs
    merged['off_comp_diff'] = merged['home_off_comp'] - merged['away_off_comp']
    merged['def_comp_diff'] = merged['home_def_comp'] - merged['away_def_comp']
    merged['net_composite'] = merged['off_comp_diff'] + merged['def_comp_diff']

    # Existing directional advantages
    merged['home_off_vs_away_def'] = merged['home_off_comp'] - merged['away_def_comp']
    merged['home_def_vs_away_off'] = merged['home_def_comp'] - merged['away_off_comp']
    merged['net_home_adv'] = merged['home_off_vs_away_def'] + merged['home_def_vs_away_off']

    # Initialize placeholders
    placeholder_cols = [
        'pressure_mismatch','turnover_index',
        'momentum_home_off','momentum_home_def','momentum_away_off','momentum_away_def',
        'trend_home_off','trend_home_def','trend_away_off','trend_away_def'
    ]
    for c in placeholder_cols:
        merged[c] = None
    merged['impute_flag'] = 0

    # Momentum & trend calculation per team (home & away separately)
    # Cache histories
    cache: Dict[str,pd.DataFrame] = {}
    def get_hist(team: str):
        if team not in cache:
            cache[team] = _fetch_team_history(conn, season, team, week)
        return cache[team]

    for idx, row in merged.iterrows():
        home_team = row['Home_Team']
        away_team = row['Away_Team']
        h_hist = get_hist(home_team)
        a_hist = get_hist(away_team)
        h_off_mom, h_off_trend = _calc_momentum_and_trend(h_hist, 'offense', week)
        h_def_mom, h_def_trend = _calc_momentum_and_trend(h_hist, 'defense', week)
        a_off_mom, a_off_trend = _calc_momentum_and_trend(a_hist, 'offense', week)
        a_def_mom, a_def_trend = _calc_momentum_and_trend(a_hist, 'defense', week)
        merged.at[idx, 'momentum_home_off'] = h_off_mom
        merged.at[idx, 'momentum_home_def'] = h_def_mom
        merged.at[idx, 'momentum_away_off'] = a_off_mom
        merged.at[idx, 'momentum_away_def'] = a_def_mom
        merged.at[idx, 'trend_home_off'] = h_off_trend
        merged.at[idx, 'trend_home_def'] = h_def_trend
        merged.at[idx, 'trend_away_off'] = a_off_trend
        merged.at[idx, 'trend_away_def'] = a_def_trend

    # Imputation pass
    for idx, row in merged.iterrows():
        updated, flag = _impute_and_flag(row, league_means, int(row.get('impute_flag', 0)))
        merged.loc[idx, ['home_off_comp','home_def_comp','away_off_comp','away_def_comp']] = [
            updated['home_off_comp'], updated['home_def_comp'], updated['away_off_comp'], updated['away_def_comp']
        ]
        merged.at[idx,'impute_flag'] = flag

    merged['season'] = season
    merged['week'] = week
    merged['created_at'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # Upsert (extended schema)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS matchup_features (
        season INTEGER, week INTEGER, Home_Team TEXT, Away_Team TEXT,
        home_off_comp REAL, home_def_comp REAL, away_off_comp REAL, away_def_comp REAL,
        home_off_vs_away_def REAL, home_def_vs_away_off REAL, net_home_adv REAL,
        off_comp_diff REAL, def_comp_diff REAL, net_composite REAL,
        pressure_mismatch REAL, turnover_index REAL,
        momentum_home_off REAL, momentum_home_def REAL, momentum_away_off REAL, momentum_away_def REAL,
        trend_home_off REAL, trend_home_def REAL, trend_away_off REAL, trend_away_def REAL,
        impute_flag INTEGER, created_at TEXT,
        PRIMARY KEY (season, week, Home_Team, Away_Team))""")

    stmt = ("INSERT OR REPLACE INTO matchup_features (season, week, Home_Team, Away_Team, home_off_comp, home_def_comp, "
            "away_off_comp, away_def_comp, home_off_vs_away_def, home_def_vs_away_off, net_home_adv, off_comp_diff, def_comp_diff, net_composite, "
            "pressure_mismatch, turnover_index, momentum_home_off, momentum_home_def, momentum_away_off, momentum_away_def, trend_home_off, trend_home_def, trend_away_off, trend_away_def, impute_flag, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
    rows = [(
        season, week, r.Home_Team, r.Away_Team,
        None if pd.isna(r.home_off_comp) else float(r.home_off_comp),
        None if pd.isna(r.home_def_comp) else float(r.home_def_comp),
        None if pd.isna(r.away_off_comp) else float(r.away_off_comp),
        None if pd.isna(r.away_def_comp) else float(r.away_def_comp),
        None if pd.isna(r.home_off_vs_away_def) else float(r.home_off_vs_away_def),
        None if pd.isna(r.home_def_vs_away_off) else float(r.home_def_vs_away_off),
        None if pd.isna(r.net_home_adv) else float(r.net_home_adv),
        None if pd.isna(r.off_comp_diff) else float(r.off_comp_diff),
        None if pd.isna(r.def_comp_diff) else float(r.def_comp_diff),
        None if pd.isna(r.net_composite) else float(r.net_composite),
        None if pd.isna(r.pressure_mismatch) else float(r.pressure_mismatch),
        None if pd.isna(r.turnover_index) else float(r.turnover_index),
        None if pd.isna(r.momentum_home_off) else float(r.momentum_home_off),
        None if pd.isna(r.momentum_home_def) else float(r.momentum_home_def),
        None if pd.isna(r.momentum_away_off) else float(r.momentum_away_off),
        None if pd.isna(r.momentum_away_def) else float(r.momentum_away_def),
        None if pd.isna(r.trend_home_off) else float(r.trend_home_off),
        None if pd.isna(r.trend_home_def) else float(r.trend_home_def),
        None if pd.isna(r.trend_away_off) else float(r.trend_away_off),
        None if pd.isna(r.trend_away_def) else float(r.trend_away_def),
        int(r.impute_flag),
        r.created_at
    ) for r in merged.itertuples(index=False)]
    if rows:
        cur.executemany(stmt, rows)
        conn.commit()
    return merged

def build_and_store_matchup_features(season: int, weeks: List[int]):
    conn = get_connection()
    try:
        out = []
        for w in weeks:
            out.append(build_matchup_features(conn, season, w))
        return out
    finally:
        conn.close()
