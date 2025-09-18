import sqlite3
from pathlib import Path
import pandas as pd
import math
import os

from panda_picks import config
from panda_picks.config.settings import Settings
from panda_picks.db.database import create_tables, get_connection
from panda_picks.analysis.bayesian_grades import recompute_blended_grades


def _init_temp_db(tmp_name: str):
    db_path = Path(tmp_name).resolve()
    if db_path.exists():
        try: db_path.unlink()
        except Exception: pass
    config.DATABASE_PATH = db_path
    create_tables()  # creates base tables (doesn't create grades_prior, etc.)
    return db_path


def test_bayesian_blend_weight_capped_early():
    original_flag = Settings.USE_BAYES_GRADES
    original_k = Settings.BAYES_K_VALUES.copy()
    try:
        Settings.USE_BAYES_GRADES = True
        Settings.BAYES_K_VALUES['OVR'] = 4  # k=4
        Settings.BAYES_MAX_RAMP_WEEK = 5
        Settings.BAYES_CAP_WEIGHT_EARLY = 0.75

        _init_temp_db('temp_test_bayes_early.db')
        with get_connection() as conn:
            # Prior season grades
            prior_df = pd.DataFrame([
                {'TEAM': 'TEAM_A', 'OVR': 80},
                {'TEAM': 'TEAM_B', 'OVR': 70},
            ])
            prior_df.to_sql('grades_prior', conn, if_exists='replace', index=False)
            # Current partial grades (only TEAM_A present)
            current_df = pd.DataFrame([
                {'TEAM': 'TEAM_A', 'OVR': 70},  # current lower
            ])
            current_df.to_sql('grades', conn, if_exists='replace', index=False)
            # Spreads with two completed games (Week1 and Week2)
            spreads = pd.DataFrame([
                {'WEEK':'WEEK1','Home_Team':'TEAM_A','Away_Team':'TEAM_B','Home_Score':21,'Away_Score':14},
                {'WEEK':'WEEK2','Home_Team':'TEAM_B','Away_Team':'TEAM_A','Home_Score':17,'Away_Score':24},
            ])
            spreads.to_sql('spreads', conn, if_exists='append', index=False)
            recompute_blended_grades(conn)
            blend = pd.read_sql_query("SELECT * FROM blended_grades WHERE Home_Team='TEAM_A' AND Metric='OVR'", conn)
            assert not blend.empty, 'Blended grade row missing for TEAM_A'
            row = blend.iloc[0]
            # Base weight without cap = n/(n+k)=2/(2+4)=0.3333; cap: ramp_frac=2/5=0.4 -> max_allowed=0.75*0.4=0.30
            expected_weight = 0.75 * (2/5)
            assert math.isclose(row['Weight_Current'], expected_weight, rel_tol=1e-6), f"Weight capped mismatch {row['Weight_Current']} vs {expected_weight}"
            expected_blend = expected_weight * 70 + (1-expected_weight) * 80
            assert math.isclose(row['Blended'], expected_blend, rel_tol=1e-6), f"Blended value mismatch {row['Blended']} vs {expected_blend}"
            # TEAM_B missing current row -> blended should equal prior 70
            blend_b = pd.read_sql_query("SELECT * FROM blended_grades WHERE Home_Team='TEAM_B' AND Metric='OVR'", conn)
            assert not blend_b.empty
            assert blend_b.iloc[0]['Weight_Current'] == 0
            assert blend_b.iloc[0]['Blended'] == 70
    finally:
        Settings.USE_BAYES_GRADES = original_flag
        Settings.BAYES_K_VALUES = original_k


def test_bayesian_blend_after_ramp_week():
    original_flag = Settings.USE_BAYES_GRADES
    original_k = Settings.BAYES_K_VALUES.copy()
    try:
        Settings.USE_BAYES_GRADES = True
        Settings.BAYES_K_VALUES['OVR'] = 4
        Settings.BAYES_MAX_RAMP_WEEK = 5
        Settings.BAYES_CAP_WEIGHT_EARLY = 0.75

        _init_temp_db('temp_test_bayes_post_ramp.db')
        with get_connection() as conn:
            prior_df = pd.DataFrame([
                {'TEAM': 'TEAM_A', 'OVR': 80},
            ])
            prior_df.to_sql('grades_prior', conn, if_exists='replace', index=False)
            current_df = pd.DataFrame([
                {'TEAM': 'TEAM_A', 'OVR': 60},
            ])
            current_df.to_sql('grades', conn, if_exists='replace', index=False)
            # Provide six completed games across weeks 1..6 to set current_week=6 and n=6
            rows = []
            for wk in range(1,7):
                rows.append({'WEEK':f'WEEK{wk}','Home_Team':'TEAM_A','Away_Team':f'OPP{wk}','Home_Score':20+wk,'Away_Score':10})
            spreads = pd.DataFrame(rows)
            spreads.to_sql('spreads', conn, if_exists='append', index=False)
            recompute_blended_grades(conn)
            blend = pd.read_sql_query("SELECT * FROM blended_grades WHERE Home_Team='TEAM_A' AND Metric='OVR'", conn)
            assert not blend.empty
            row = blend.iloc[0]
            # After ramp: weight = 6/(6+4)=0.6 (no cap because week=6>5)
            expected_weight = 6/(6+4)
            assert math.isclose(row['Weight_Current'], expected_weight, rel_tol=1e-6)
            expected_blend = expected_weight * 60 + (1-expected_weight) * 80
            assert math.isclose(row['Blended'], expected_blend, rel_tol=1e-6)
    finally:
        Settings.USE_BAYES_GRADES = original_flag
        Settings.BAYES_K_VALUES = original_k

