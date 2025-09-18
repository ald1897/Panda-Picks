import sys
import os
from typing import Optional

# Allow running from scripts/ by adding project root to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from panda_picks.db.database import get_connection
from panda_picks.ui.grade_utils import grade_pick, ResultStatus, resolve_line_for_pick, format_line


def summarize_week(week_num: Optional[int] = None):
    if week_num is None:
        if len(sys.argv) > 1:
            try:
                week_num = int(sys.argv[1])
            except Exception:
                week_num = None
    if week_num is None:
        print("Usage: python scripts/summarize_week.py <week_number>")
        sys.exit(1)
    week_key = f"WEEK{week_num}"
    conn = get_connection(); cur = conn.cursor()
    cur.execute(
        """
        SELECT p.WEEK, p.Home_Team, p.Away_Team, p.Game_Pick,
               COALESCE(pr.Home_Score, s.Home_Score) AS Home_Score,
               COALESCE(pr.Away_Score, s.Away_Score) AS Away_Score,
               COALESCE(s.Home_Line_Close, pr.Home_Line_Close, p.Home_Line_Close) AS Home_Line_Close,
               COALESCE(s.Away_Line_Close, pr.Away_Line_Close, p.Away_Line_Close) AS Away_Line_Close,
               p.Overall_Adv
        FROM picks p
        LEFT JOIN picks_results pr
          ON pr.WEEK = p.WEEK AND pr.Home_Team = p.Home_Team AND pr.Away_Team = p.Away_Team
        LEFT JOIN spreads s
          ON s.WEEK = p.WEEK AND s.Home_Team = p.Home_Team AND s.Away_Team = p.Away_Team
        WHERE p.WEEK = ?
        ORDER BY p.Home_Team, p.Away_Team
        """,
        (week_key,)
    )
    rows = cur.fetchall(); conn.close()
    if not rows:
        print(f"No picks found for {week_key}. Make sure picks and scores are loaded.")
        return
    wins=losses=pushes=pending=graded=0
    profit=0.0
    lines = []
    for (wk, home, away, pick, hs, ascore, hline, aline, oadv) in rows:
        base_line = resolve_line_for_pick(pick, home, away, hline, aline)
        res = grade_pick(home, away, pick, hs, ascore, hline, aline)
        status = res.status
        if status == ResultStatus.PENDING or hs is None or ascore is None:
            pending += 1; outcome = 'PENDING'
        elif status == ResultStatus.PUSH:
            pushes += 1; outcome = 'PUSH'
        elif status == ResultStatus.WIN:
            wins += 1; graded += 1; profit += 91.0; outcome = 'WIN'
        elif status == ResultStatus.LOSS:
            losses += 1; graded += 1; profit -= 100.0; outcome = 'LOSS'
        else:
            pending += 1; outcome = status.value
        score_str = 'TBD' if hs is None or ascore is None else f"{int(ascore)}-{int(hs)}"
        line_str = format_line(base_line) if base_line is not None else 'N/A'
        lines.append(f"{away} @ {home} | Pick: {pick} {line_str} | Score: {score_str} | Result: {outcome}")
    win_rate = (wins/graded*100.0) if graded else 0.0
    roi = ((profit/(graded*100.0))*100.0) if graded else 0.0
    print(f"Summary for {week_key}:")
    print(f"- Picks: {len(rows)} | Graded: {graded} | Wins: {wins} | Losses: {losses} | Pushes: {pushes} | Pending: {pending}")
    print(f"- Straight Win Rate: {win_rate:.1f}% | ROI: {roi:.1f}% | Profit: ${profit:.2f}")
    print("Details:")
    for ln in lines:
        print("  - "+ln)


if __name__ == '__main__':
    wk = None
    if len(sys.argv) > 1:
        try:
            wk = int(sys.argv[1])
        except Exception:
            wk = None
    summarize_week(wk)
