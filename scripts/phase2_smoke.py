"""Phase 2 smoke test: generate picks and verify advanced fields are present.
Usage:
  python scripts/phase2_smoke.py --weeks 1,2
"""
from __future__ import annotations
import argparse, sys, os
from datetime import datetime

# Ensure project root on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from panda_picks.db.database import get_connection, create_tables, store_grades_data
from panda_picks.analysis.picks import makePicks
from panda_picks.analysis.spreads import fetch_and_process, _upsert_spreads
from panda_picks.data.advanced_stats import main as adv_main
from panda_picks.analysis.advanced_features import build_and_store_matchup_features


def ensure_data(weeks):
    create_tables()
    # spreads
    for w in weeks:
        try:
            df = fetch_and_process(w)
            _upsert_spreads(df, w)
            print(f"[spreads] week {w}: {len(df)} games")
        except Exception as e:
            print(f"[spreads] week {w}: error {e}")
    # advanced stats
    season = datetime.now().year
    for w in weeks:
        try:
            adv_main(season=season, week=w)
            print(f"[advanced] week {w}: done")
        except Exception as e:
            print(f"[advanced] week {w}: error {e}")
    # matchup features
    try:
        build_and_store_matchup_features(season, weeks)
        print("[features] matchup_features built")
    except Exception as e:
        print(f"[features] error {e}")
    # grades from CSV
    try:
        ok = store_grades_data()
        print(f"[grades] stored from CSV: {ok}")
    except Exception as e:
        print(f"[grades] error {e}")


def run(weeks):
    print('=== Phase 2 Smoke Test ===')
    ensure_data(weeks)
    print('Generating picks...')
    makePicks(weeks)
    print('Querying picks table for sample rows...')
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute('PRAGMA table_info(picks)')
        cols = [r[1] for r in cur.fetchall()]
        print('picks columns ({}):'.format(len(cols)))
        print(', '.join(cols))
        q = ("SELECT WEEK, Home_Team, Away_Team, Overall_Adv, Off_Comp_Diff, Def_Comp_Diff, Net_Composite, Net_Composite_norm, Blended_Adv, "
             "Home_Win_Prob, Pick_Edge FROM picks ORDER BY WEEK, Home_Team LIMIT 10")
        for row in cur.execute(q):
            print(row)
    print('=== Done ===')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--weeks', type=str, default='1,2')
    args = ap.parse_args()
    weeks = [int(w.strip()) for w in args.weeks.split(',') if w.strip().isdigit()]
    run(weeks)
