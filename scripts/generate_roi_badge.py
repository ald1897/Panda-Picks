"""Generate a Shields.io endpoint JSON for season-to-date picks ROI.

Logic:
- Reads picks_results table (if exists). If absent or empty creates a placeholder badge.
- Assumes unit stake = 1 per pick.
- Profit calculation per pick:
    * Identify odds column (home vs away) based on Game_Pick alignment.
    * If pick correct: profit = (odds/100) for positive odds, (100/abs(odds)) for negative odds.
    * If incorrect: profit = -1.
- ROI = total_profit / total_bets.
- Color thresholds:  ROI >= 0.10 green, >= 0 yellow, else red.
- Writes JSON to badges/roi.json.

This script is idempotent and safe to run in CI.
"""
from __future__ import annotations
import json
import math
import sqlite3
from pathlib import Path

from panda_picks import config  # uses DATABASE_PATH

BADGE_DIR = Path("badges")
BADGE_FILE = BADGE_DIR / "roi.json"

PLACEHOLDER = {
    "schemaVersion": 1,
    "label": "ROI (Season)",
    "message": "n/a",
    "color": "lightgrey"
}

def _compute_profit(odds: float, correct: bool) -> float:
    if math.isnan(odds):
        return 0.0
    if correct:
        if odds > 0:
            return odds / 100.0
        else:
            return 100.0 / abs(odds)
    else:
        return -1.0

def main() -> None:
    BADGE_DIR.mkdir(parents=True, exist_ok=True)
    db_path = config.DATABASE_PATH
    if not db_path.exists():
        BADGE_FILE.write_text(json.dumps(PLACEHOLDER))
        return
    try:
        conn = sqlite3.connect(db_path)
    except Exception:
        BADGE_FILE.write_text(json.dumps(PLACEHOLDER))
        return

    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='picks_results'")
        if cur.fetchone() is None:
            BADGE_FILE.write_text(json.dumps(PLACEHOLDER))
            return
        # Fetch needed columns; some rows may have NULL odds
        cur.execute("""
            SELECT Game_Pick, Home_Team, Away_Team, Home_Odds_Close, Away_Odds_Close, Correct_Pick
            FROM picks_results
        """)
        rows = cur.fetchall()
        if not rows:
            BADGE_FILE.write_text(json.dumps(PLACEHOLDER))
            return
        total_profit = 0.0
        total_bets = 0
        for game_pick, home, away, home_odds, away_odds, correct_flag in rows:
            # Only count rows where a pick exists
            if game_pick not in (home, away):
                continue
            odds = home_odds if game_pick == home else away_odds
            try:
                odds_val = float(odds) if odds is not None else float('nan')
            except (TypeError, ValueError):
                odds_val = float('nan')
            correct = bool(correct_flag) if correct_flag is not None else False
            total_profit += _compute_profit(odds_val, correct)
            total_bets += 1
        if total_bets == 0:
            BADGE_FILE.write_text(json.dumps(PLACEHOLDER))
            return
        roi = total_profit / total_bets  # unit stake basis
        # Color selection
        if roi >= 0.10:
            color = 'green'
        elif roi >= 0.0:
            color = 'yellow'
        else:
            color = 'red'
        badge = {
            "schemaVersion": 1,
            "label": "ROI (Season)",
            "message": f"{roi*100:.1f}%",
            "color": color
        }
        BADGE_FILE.write_text(json.dumps(badge))
    except Exception:
        BADGE_FILE.write_text(json.dumps(PLACEHOLDER))
    finally:
        conn.close()


if __name__ == "__main__":
    main()

