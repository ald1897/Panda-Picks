import re
import pandas as pd
from pathlib import Path

from panda_picks import config
from panda_picks.db.database import create_tables, get_connection
from panda_picks.data.get_pff_grades import _parse_weeks, _derive_weeks_from_db, build_pff_url


def _reset_db(tmp_path: Path):
    if tmp_path.exists():
        try: tmp_path.unlink()
        except Exception: pass
    config.DATABASE_PATH = tmp_path
    create_tables()


def test_parse_weeks_simple_list():
    assert _parse_weeks('1,2,3') == [1,2,3]


def test_parse_weeks_ranges_and_duplicates():
    # 1-3,5,7-9 plus stray duplicates and invalid tokens
    parsed = _parse_weeks('1-3,5,7-9, 5, xx, 2')
    assert parsed == [1,2,3,5,7,8,9]


def test_parse_weeks_empty_or_invalid():
    assert _parse_weeks('') == []
    assert _parse_weeks('foo,bar') == []  # nothing valid collected


def test_derive_weeks_from_db_completed(tmp_path):
    db_path = tmp_path / 'weeks.db'
    _reset_db(db_path)
    with get_connection() as conn:
        spreads = pd.DataFrame([
            {'WEEK':'WEEK1','Home_Team':'A','Away_Team':'B','Home_Score':21,'Away_Score':14},
            {'WEEK':'WEEK2','Home_Team':'C','Away_Team':'D','Home_Score':17,'Away_Score':20},
            {'WEEK':'WEEK3','Home_Team':'E','Away_Team':'F','Home_Score':None,'Away_Score':None},  # incomplete
        ])
        spreads.to_sql('spreads', conn, if_exists='append', index=False)
    derived = _derive_weeks_from_db()
    # Max completed week =2, function returns range 1..2
    assert derived == [1,2]


def test_build_pff_url_custom_params():
    url = build_pff_url(season=2026, weeks=[3,1,2,3])
    assert 'season=2026' in url
    # order should be sorted unique 1,2,3
    assert re.search(r'week=1,2,3($|&)', url) is not None


def test_build_pff_url_defaults_ensures_week_param_present():
    # Passing explicit weeks None to rely on module PARSED_WEEKS
    url = build_pff_url(season=2027, weeks=[4])
    assert 'season=2027' in url
    assert 'week=4' in url

