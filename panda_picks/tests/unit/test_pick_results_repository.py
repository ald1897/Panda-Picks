import os
import tempfile
import sqlite3
import math
import pytest

from panda_picks.data.repositories.pick_results_repository import PickResultsRepository
from panda_picks.ui.grade_utils import grade_pick, ResultStatus

# NOTE: We patch the database path so get_connection() points to a temp file DB.
@pytest.fixture()
def temp_db(monkeypatch):
    from panda_picks import config
    from panda_picks.db.database import get_connection
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    # Patch config.DATABASE_PATH to new temp path
    monkeypatch.setattr(config, 'DATABASE_PATH', path)
    # Build minimal schema (subset columns required by repository queries)
    conn = get_connection(); cur = conn.cursor()
    cur.execute('''CREATE TABLE picks_results (
        WEEK TEXT, Home_Team TEXT, Away_Team TEXT,
        Home_Score INTEGER, Away_Score INTEGER,
        Home_Odds_Close REAL, Away_Odds_Close REAL,
        Home_Line_Close REAL, Away_Line_Close REAL,
        Game_Pick TEXT, Winner TEXT,
        Correct_Pick INTEGER, Pick_Covered_Spread INTEGER,
        Overall_Adv REAL, Offense_Adv REAL, Defense_Adv REAL,
        Off_Comp_Adv REAL, Def_Comp_Adv REAL,
        Overall_Adv_Sig TEXT, Offense_Adv_Sig TEXT, Defense_Adv_Sig TEXT,
        Off_Comp_Adv_Sig TEXT, Def_Comp_Adv_Sig TEXT,
        PRIMARY KEY (WEEK, Home_Team, Away_Team)
    )''')
    cur.execute('''CREATE TABLE picks (
        WEEK TEXT, Home_Team TEXT, Away_Team TEXT,
        Home_Line_Close REAL, Away_Line_Close REAL,
        Game_Pick TEXT, Overall_Adv REAL,
        Offense_Adv REAL, Defense_Adv REAL,
        Off_Comp_Adv REAL, Def_Comp_Adv REAL,
        PRIMARY KEY (WEEK, Home_Team, Away_Team)
    )''')
    conn.commit()
    yield conn
    conn.close()
    if os.path.exists(path):
        os.remove(path)


def insert_picks_results(conn, rows):
    cur = conn.cursor()
    cur.executemany('''INSERT INTO picks_results (
        WEEK, Home_Team, Away_Team, Home_Score, Away_Score,
        Home_Odds_Close, Away_Odds_Close, Home_Line_Close, Away_Line_Close,
        Game_Pick, Winner, Correct_Pick, Pick_Covered_Spread,
        Overall_Adv, Offense_Adv, Defense_Adv, Off_Comp_Adv, Def_Comp_Adv,
        Overall_Adv_Sig, Offense_Adv_Sig, Defense_Adv_Sig, Off_Comp_Adv_Sig, Def_Comp_Adv_Sig
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', rows)
    conn.commit()


def insert_picks(conn, rows):
    cur = conn.cursor()
    cur.executemany('''INSERT INTO picks (
        WEEK, Home_Team, Away_Team, Home_Line_Close, Away_Line_Close,
        Game_Pick, Overall_Adv, Offense_Adv, Defense_Adv, Off_Comp_Adv, Def_Comp_Adv
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)''', rows)
    conn.commit()


def test_repository_basic_fetch_matches_raw(temp_db):
    # Data includes win, loss, push, and a row missing scores (excluded from scored_basic)
    rows = [
        ('WEEK1','A','B', 24,17,None,None,-3.5,None,'A',None,1,1, 5,0,0,0,0,None,None,None,None,None),  # A -3.5 wins
        ('WEEK1','C','D', 20,20,None,None,-3.0,None,'C',None,0,0, 3,0,0,0,0,None,None,None,None,None),  # push if line -3? Actually 20-3=17<20 loss; adjust better push case next
        ('WEEK1','E','F', 21,21,None,None,0.0,None,'E',None,0,0, 2,0,0,0,0,None,None,None,None,None),   # PK push
        ('WEEK2','G','H', 14,17,None,None,-2.5,None,'G',None,0,0, 4,0,0,0,0,None,None,None,None,None),  # G -2.5 loses
    ]
    # Correct a true push row: use E-F PK already; remove flawed C-D example
    rows = [r for r in rows if not (r[1]=='C')]
    insert_picks_results(temp_db, rows)
    repo = PickResultsRepository()
    scored = repo.get_scored_basic()
    assert len(scored) == 3
    # Compare with direct raw query
    cur = temp_db.cursor()
    cur.execute("SELECT WEEK, Home_Team, Away_Team, Game_Pick, Home_Score, Away_Score, Home_Line_Close, Away_Line_Close FROM picks_results WHERE Home_Score IS NOT NULL AND Away_Score IS NOT NULL")
    direct = cur.fetchall()
    assert scored == direct


def test_upcoming_join_includes_unscored(temp_db):
    # Insert a future pick (no scores) and a completed one
    insert_picks(temp_db, [
        ('WEEK3','X','Y', -4.0, None, 'X', 7,0,0,0,0),
        ('WEEK3','M','N', -2.0, None, 'M', 5,0,0,0,0),
    ])
    insert_picks_results(temp_db, [
        ('WEEK3','M','N', 28,14,None,None,-2.0,None,'M',None,1,1,5,0,0,0,0,None,None,None,None,None),
    ])
    repo = PickResultsRepository()
    rows = repo.get_upcoming_join()
    # Should have two rows (one with scores, one without)
    assert len(rows) == 2
    # Identify scored vs unscored
    scored = [r for r in rows if r[5] is not None and r[6] is not None]
    unscored = [r for r in rows if r[5] is None or r[6] is None]
    assert len(scored) == 1 and len(unscored) == 1


def test_grading_contract_with_repository(temp_db):
    # Insert mixed outcomes
    test_rows = [
        ('WEEK4','HOM','AWY', 21,17,None,None,-3.0,None,'HOM',None,1,1,3,0,0,0,0,None,None,None,None,None),  # cover
        ('WEEK4','AAA','BBB', 20,20,None,None,0.0,None,'AAA',None,0,0,2,0,0,0,0,None,None,None,None,None),   # push PK
        ('WEEK4','DOG','FAV', 14,17,None,None,2.5,None,'FAV',None,1,1,4,0,0,0,0,None,None,None,None,None),  # favorite -2.5 wins 17-14
        ('WEEK4','LOS','WIN', 10,21,None,None,-6.5,None,'LOS',None,0,0,1,0,0,0,0,None,None,None,None,None), # loss
    ]
    insert_picks_results(temp_db, test_rows)
    repo = PickResultsRepository()
    scored = repo.get_scored_basic()
    # Contract: Grading from repository rows == grading from direct raw
    cur = temp_db.cursor(); cur.execute("SELECT WEEK, Home_Team, Away_Team, Game_Pick, Home_Score, Away_Score, Home_Line_Close, Away_Line_Close FROM picks_results WHERE Home_Score IS NOT NULL AND Away_Score IS NOT NULL")
    direct = cur.fetchall()
    assert scored == direct
    # Compute win/loss ignoring pushes both ways
    def compute_stats(rows):
        wins=0; graded=0
        for wk, home, away, pick, hs, ascore, hline, aline in rows:
            res = grade_pick(home, away, pick, hs, ascore, hline, aline)
            if res.status in (ResultStatus.PENDING, ResultStatus.PUSH, ResultStatus.NA):
                continue
            graded += 1
            if res.status == ResultStatus.WIN:
                wins += 1
        return wins, graded
    wins_repo, graded_repo = compute_stats(scored)
    wins_direct, graded_direct = compute_stats(direct)
    assert (wins_repo, graded_repo) == (wins_direct, graded_direct)
    # Spot check a push and a win
    push_row = next(r for r in scored if r[1]=='AAA')
    res_push = grade_pick(push_row[1], push_row[2], push_row[3], push_row[4], push_row[5], push_row[6], push_row[7])
    assert res_push.status == ResultStatus.PUSH
    win_row = next(r for r in scored if r[1]=='HOM')
    res_win = grade_pick(win_row[1], win_row[2], win_row[3], win_row[4], win_row[5], win_row[6], win_row[7])
    assert res_win.status == ResultStatus.WIN

