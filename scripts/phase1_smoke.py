"""Phase 1 smoke test.
Runs a clean cycle:
 1. Drop & recreate tables
 2. Fetch spreads for given weeks (fallback dummy if API empty/fails)
 3. Collect advanced stats for same weeks (fallback dummy rows if scrape fails)
 4. Build matchup features
 5. Print sample rows and basic integrity checks
Usage:
  python scripts/phase1_smoke.py --weeks 1,2
"""
from __future__ import annotations
import argparse, sys, os
from datetime import datetime
import traceback
import pandas as pd

# Add project root so 'panda_picks' is importable when running from scripts/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from panda_picks.db.database import drop_tables, create_tables, get_connection
from panda_picks.analysis.spreads import fetch_and_process, _upsert_spreads
from panda_picks.data.advanced_stats import main as adv_main
from panda_picks.analysis.advanced_features import build_and_store_matchup_features

DUMMY_TEAMS = ["AAA","BBB","CCC","DDD"]


def _ensure_spreads(weeks, season):
    print("[spreads] fetching...")
    for w in weeks:
        try:
            df = fetch_and_process(w)
            if df.empty:
                print(f"  week {w}: API returned empty, inserting dummy spreads")
                dummy = pd.DataFrame([
                    {"WEEK": f"WEEK{w}", "Home_Team": DUMMY_TEAMS[0], "Away_Team": DUMMY_TEAMS[1]},
                    {"WEEK": f"WEEK{w}", "Home_Team": DUMMY_TEAMS[2], "Away_Team": DUMMY_TEAMS[3]},
                ])
                _upsert_spreads(dummy, w)
            else:
                _upsert_spreads(df, w)
                print(f"  week {w}: {len(df)} games")
        except Exception as e:
            print(f"  week {w}: spreads fetch error {e}; inserting dummy")
            dummy = pd.DataFrame([
                {"WEEK": f"WEEK{w}", "Home_Team": DUMMY_TEAMS[0], "Away_Team": DUMMY_TEAMS[1]},
                {"WEEK": f"WEEK{w}", "Home_Team": DUMMY_TEAMS[2], "Away_Team": DUMMY_TEAMS[3]},
            ])
            _upsert_spreads(dummy, w)


def _ensure_advanced_stats(weeks, season):
    print("[advanced_stats] collecting...")
    for w in weeks:
        try:
            adv_main(season=season, week=w)
        except Exception as e:
            print(f"  week {w}: advanced stats error {e}")
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM advanced_stats WHERE season=? AND week=?", (season, w))
            cnt = cur.fetchone()[0]
            if cnt == 0:
                print(f"  week {w}: inserting dummy advanced stats rows")
                rows = []
                for idx, t in enumerate(DUMMY_TEAMS):
                    rows.append((season, w, 'offense', t, 10+idx, 0.0, 'dummy'))
                    rows.append((season, w, 'defense', t, 8+idx, 0.0, 'dummy'))
                cur.executemany("INSERT OR REPLACE INTO advanced_stats (season,week,type,TEAM,composite_score,z_score,last_updated) VALUES (?,?,?,?,?,?,?)", rows)
                conn.commit()


def _build_features(weeks, season):
    print("[features] building matchup features...")
    build_and_store_matchup_features(season, weeks)


def _print_samples(weeks, season, limit=10):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(matchup_features)")
        cols = [c[1] for c in cur.fetchall()]
        print("matchup_features columns ({}):".format(len(cols)))
        print(", ".join(cols))
        print("Sample rows:")
        q = ("SELECT season,week,Home_Team,Away_Team,off_comp_diff,def_comp_diff,net_composite,net_home_adv,"
             "momentum_home_off,momentum_home_def,momentum_away_off,momentum_away_def,impute_flag "
             "FROM matchup_features ORDER BY week, Home_Team LIMIT ?")
        for row in cur.execute(q, (limit,)):
            print(row)
        # Basic integrity checks
        print("\nIntegrity checks:")
        # Net composite equals sum of diffs
        cur.execute("SELECT COUNT(*) FROM matchup_features WHERE ABS((off_comp_diff + def_comp_diff) - net_composite) > 1e-6")
        bad = cur.fetchone()[0]
        print(f"  net_composite consistency failures: {bad}")
        # Any null composites -> impute flag should be 1 (spot check)
        cur.execute("SELECT COUNT(*) FROM matchup_features WHERE (home_off_comp IS NULL OR away_off_comp IS NULL) AND impute_flag=0")
        miss_flag = cur.fetchone()[0]
        print(f"  missing composite without impute_flag: {miss_flag}")


def run_smoke(weeks, season):
    print("=== Phase 1 Smoke Test ===")
    print(f"Season {season}, Weeks {weeks}")
    print("Resetting tables ...")
    drop_tables(); create_tables()
    _ensure_spreads(weeks, season)
    _ensure_advanced_stats(weeks, season)
    _build_features(weeks, season)
    _print_samples(weeks, season)
    print("=== Done ===")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--weeks', type=str, default='1,2', help='Comma sep weeks (e.g. 1,2,3)')
    ap.add_argument('--season', type=int, default=datetime.now().year)
    return ap.parse_args()

if __name__ == '__main__':
    args = parse_args()
    weeks = [int(w.strip()) for w in args.weeks.split(',') if w.strip().isdigit()]
    try:
        run_smoke(weeks, args.season)
    except Exception as e:
        print('Smoke test failed:', e)
        traceback.print_exc()
        sys.exit(1)
