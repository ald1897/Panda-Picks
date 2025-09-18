import pandas as pd
import sqlite3
import gc
from pathlib import Path

from panda_picks import config
from panda_picks.db.database import create_tables, get_connection
from panda_picks.data.grades_migration import populate_grades_prior, snapshot_current_grades


def _reset_db(path: Path):
    if path.exists():
        try: path.unlink()
        except Exception: pass
    config.DATABASE_PATH = path
    create_tables()


def test_populate_grades_prior_from_table(tmp_path):
    db_path = tmp_path / 'prior_from_table.db'
    _reset_db(db_path)
    # Seed grades table
    with get_connection() as conn:
        df = pd.DataFrame([
            {'TEAM':'TEAM_A','OVR':80,'OFF':75,'DEF':70},
            {'TEAM':'TEAM_B','OVR':72,'OFF':68,'DEF':69},
        ])
        df.to_sql('grades', conn, if_exists='append', index=False)
    count = populate_grades_prior()
    assert count == 2
    with get_connection() as conn:
        prior = pd.read_sql_query('SELECT TEAM, OVR, OFF, DEF FROM grades_prior ORDER BY TEAM', conn)
    assert list(prior['TEAM']) == ['TEAM_A','TEAM_B']
    assert prior.loc[prior['TEAM']=='TEAM_A','OVR'].iloc[0] == 80


def test_populate_grades_prior_from_csv(tmp_path):
    db_path = tmp_path / 'prior_from_csv.db'
    _reset_db(db_path)
    csv_path = tmp_path / 'prior.csv'
    pd.DataFrame([
        {'TEAM':'TEAM_X','OVR':90,'OFF':88},
        {'TEAM':'TEAM_Y','OVR':85,'OFF':81},
    ]).to_csv(csv_path, index=False)
    count = populate_grades_prior(csv_path=csv_path, source_label='csv_import')
    assert count == 2
    with get_connection() as conn:
        prior = pd.read_sql_query('SELECT TEAM, OVR, OFF, DEF, SOURCE FROM grades_prior ORDER BY TEAM', conn)
    # DEF should be NULL (NaN in DataFrame)
    assert prior.loc[prior['TEAM']=='TEAM_X','SOURCE'].iloc[0] == 'csv_import'
    assert pd.isna(prior.loc[prior['TEAM']=='TEAM_X','DEF'].iloc[0])


def test_snapshot_current_grades(tmp_path):
    db_path = tmp_path / 'snapshot.db'
    _reset_db(db_path)
    with get_connection() as conn:
        df = pd.DataFrame([
            {'TEAM':'TEAM_A','OVR':80,'OFF':70,'DEF':60},
            {'TEAM':'TEAM_B','OVR':75,'OFF':69,'DEF':65},
        ])
        df.to_sql('grades', conn, if_exists='append', index=False)
    inserted = snapshot_current_grades(season=2025, week='WEEK1')
    assert inserted == 2
    with get_connection() as conn:
        snap = pd.read_sql_query("SELECT Season, Week, TEAM, OVR FROM grades_snapshots ORDER BY TEAM", conn)
    assert list(snap['TEAM']) == ['TEAM_A','TEAM_B']
    assert snap['Season'].unique().tolist() == [2025]
    assert snap['Week'].unique().tolist() == ['WEEK1']

