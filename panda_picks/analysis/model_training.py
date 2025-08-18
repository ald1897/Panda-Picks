import logging
import math
import time
from dataclasses import dataclass
from typing import List, Dict

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

from panda_picks.db.database import get_connection
from panda_picks.analysis.picks import ADVANTAGE_BASE_COLUMNS

FEATURES = [
    'Overall_Adv', 'Offense_Adv', 'Defense_Adv', 'Pass_Rush_Adv', 'Coverage_Adv',
    'Receiving_Adv', 'Running_Adv', 'Run_Block_Adv', 'Home_Line_Close',
    # Engineered mismatch interaction features (mirrors picks.py)
    'Pressure_Mismatch', 'Explosive_Pass_Mismatch', 'Script_Control_Mismatch'
]

SIMULATION_SEED = 777
SIM_K_MARGIN = 0.75
SIM_BASE_TOTAL = 44
SIM_TOTAL_JITTER = 7


def simulate_missing_scores(df: pd.DataFrame, adv_col: str = 'Overall_Adv') -> pd.DataFrame:
    rng = np.random.default_rng(SIMULATION_SEED)
    for col in ['Home_Score', 'Away_Score']:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors='coerce')
    mask = df['Home_Score'].isna() | df['Away_Score'].isna()
    if not mask.any():
        return df
    subset = df.loc[mask]
    for idx, row in subset.iterrows():
        adv = row.get(adv_col, 0)
        try:
            adv = float(adv)
        except (TypeError, ValueError):
            adv = 0
        exp_margin = SIM_K_MARGIN * adv
        total = SIM_BASE_TOTAL + rng.uniform(-SIM_TOTAL_JITTER, SIM_TOTAL_JITTER)
        margin = rng.normal(exp_margin, 7)
        home_pts = (total + margin) / 2
        away_pts = total - home_pts
        df.at[idx, 'Home_Score'] = int(max(0, round(home_pts)))
        df.at[idx, 'Away_Score'] = int(max(0, round(away_pts)))
    return df


def _compute_advantages(df: pd.DataFrame) -> pd.DataFrame:
    # ADVANTAGE_BASE_COLUMNS imported from picks module (list of tuples name, lambda)
    for new_col, func in ADVANTAGE_BASE_COLUMNS:
        if new_col not in df.columns:  # avoid recomputation collisions
            df[new_col] = df.apply(func, axis=1)
    # Engineered mismatch features
    if 'Pass_Block_Adv' in df.columns and 'Pass_Rush_Adv' in df.columns:
        df['Pressure_Mismatch'] = df['Pass_Block_Adv'] - df['Pass_Rush_Adv']
    else:
        df['Pressure_Mismatch'] = 0.0
    if 'Receiving_Adv' in df.columns and 'Coverage_Adv' in df.columns:
        df['Explosive_Pass_Mismatch'] = df['Receiving_Adv'] - df['Coverage_Adv']
    else:
        df['Explosive_Pass_Mismatch'] = 0.0
    if 'Run_Block_Adv' in df.columns and 'Run_Defense_Adv' in df.columns:
        df['Script_Control_Mismatch'] = df['Run_Block_Adv'] - df['Run_Defense_Adv']
    else:
        df['Script_Control_Mismatch'] = 0.0
    return df


def build_dataset(conn, simulate_missing: bool = False) -> pd.DataFrame:
    spreads = pd.read_sql_query("SELECT * FROM spreads", conn)
    grades = pd.read_sql_query("SELECT * FROM grades", conn)
    # Normalize grade team col
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
    merged = spreads.merge(grades, on='Home_Team', how='left').merge(opp_grades, on='Away_Team', how='left')
    merged = _compute_advantages(merged)
    if simulate_missing:
        merged = simulate_missing_scores(merged)
    # Outcome: only if both scores present
    merged['Home_Score'] = pd.to_numeric(merged['Home_Score'], errors='coerce')
    merged['Away_Score'] = pd.to_numeric(merged['Away_Score'], errors='coerce')
    merged['Has_Result'] = ~(merged['Home_Score'].isna() | merged['Away_Score'].isna())
    merged['Home_Win'] = merged.apply(lambda r: 1 if r['Has_Result'] and r['Home_Score'] > r['Away_Score'] else 0, axis=1)
    return merged


def time_split_cv(df: pd.DataFrame, week_col: str = 'WEEK') -> pd.DataFrame:
    # WEEK format like 'WEEK1'; extract integer
    df = df.copy()
    df['WeekNum'] = df[week_col].str.extract(r'(\d+)').astype(int)
    df = df.sort_values('WeekNum')
    records = []
    weeks = sorted(df['WeekNum'].unique())
    # Require at least 2 weeks for a split
    for i, wk in enumerate(weeks):
        if i < 2:  # need at least 2 prior weeks to train
            continue
        train_weeks = weeks[:i]
        valid_week = wk
        train_df = df[df['WeekNum'].isin(train_weeks) & df['Has_Result']]
        valid_df = df[(df['WeekNum'] == valid_week) & df['Has_Result']]
        if train_df.empty or valid_df.empty:
            continue
        X_train = train_df[FEATURES].fillna(0.0)
        y_train = train_df['Home_Win']
        X_valid = valid_df[FEATURES].fillna(0.0)
        y_valid = valid_df['Home_Win']
        scaler = StandardScaler().fit(X_train)
        X_train_s = scaler.transform(X_train)
        X_valid_s = scaler.transform(X_valid)
        model = LogisticRegression(max_iter=1000)
        model.fit(X_train_s, y_train)
        prob = model.predict_proba(X_valid_s)[:, 1]
        try:
            brier = brier_score_loss(y_valid, prob)
        except ValueError:
            brier = math.nan
        try:
            ll = log_loss(y_valid, prob, labels=[0, 1])
        except ValueError:
            ll = math.nan
        try:
            auc = roc_auc_score(y_valid, prob)
        except ValueError:
            auc = math.nan
        records.append({
            'Validation_Week': valid_week,
            'Train_Weeks': len(train_weeks),
            'Brier': brier,
            'LogLoss': ll,
            'AUC': auc,
            'Pick_Count': len(valid_df)
        })
    return pd.DataFrame(records)


def train_final(df: pd.DataFrame) -> dict:
    train_df = df[df['Has_Result']]
    if train_df.empty:
        raise ValueError('No completed games available for training')
    X = train_df[FEATURES].fillna(0.0)
    y = train_df['Home_Win']
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    model = LogisticRegression(max_iter=1000)
    model.fit(Xs, y)
    coeffs = dict(zip(FEATURES, model.coef_[0]))
    intercept = float(model.intercept_[0])
    scaler_stats = {f: {'mean': float(m), 'std': float(s)} for f, m, s in zip(FEATURES, scaler.mean_, scaler.scale_)}
    return {
        'coeffs': coeffs,
        'intercept': intercept,
        'scaler': scaler_stats
    }


def persist_model(conn, model_artifacts: dict, cv_metrics: pd.DataFrame):
    coeff_rows = [{'feature': 'intercept', 'coefficient': model_artifacts['intercept']}]
    coeff_rows += [{'feature': f, 'coefficient': c} for f, c in model_artifacts['coeffs'].items()]
    coeff_df = pd.DataFrame(coeff_rows)
    coeff_df.to_sql('model_logit_coeffs', conn, if_exists='replace', index=False)

    scaler_rows = []
    for f, stats in model_artifacts['scaler'].items():
        scaler_rows.append({'feature': f, 'mean': stats['mean'], 'std': stats['std']})
    scaler_df = pd.DataFrame(scaler_rows)
    scaler_df.to_sql('model_logit_scaler', conn, if_exists='replace', index=False)

    if not cv_metrics.empty:
        cv_metrics.to_sql('model_logit_cv_metrics', conn, if_exists='replace', index=False)


def train(simulate_missing: bool = True):
    logging.info('Model training started')
    conn = get_connection()
    try:
        dataset = build_dataset(conn, simulate_missing=simulate_missing)
        # Ensure feature presence (Home_Line_Close present in spreads)
        for f in FEATURES:
            if f not in dataset.columns:
                dataset[f] = 0.0
        cv_df = time_split_cv(dataset)
        model_artifacts = train_final(dataset)
        persist_model(conn, model_artifacts, cv_df)
        logging.info('Model training completed and artifacts stored')
        return model_artifacts, cv_df
    finally:
        conn.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    artifacts, metrics = train(simulate_missing=True)
    print('Coefficients:', artifacts['coeffs'])
    print('Intercept:', artifacts['intercept'])
    print(metrics.head())
