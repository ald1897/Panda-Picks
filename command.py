import sqlite3, json
from panda_picks.ui.data import _grade_pick_row
import pandas as pd
path='database/nfl_data.db'
conn=sqlite3.connect(path)
cur=conn.cursor()
# Fetch week1 (assuming stored as WEEK1)
cur.execute("""
            SELECT WEEK, Home_Team, Away_Team, Game_Pick, Home_Score, Away_Score, Home_Line_Close, Away_Line_Close, Pick_Covered_Spread, Correct_Pick
            FROM picks_results
            WHERE TRIM(WEEK) IN ('WEEK1','Week1','week1')
            ORDER BY Home_Team
            """)
rows=cur.fetchall()
if not rows:
    print('No rows for WEEK1 in picks_results')
else:
    details=[]
    for wk, home, away, pick, hs, ascore, hline, aline, pcs, correct in rows:
        is_push, is_win = _grade_pick_row(home, away, pick, hs, ascore, hline, aline)
        details.append({
            'Week': wk,
            'Match': f"{away}@{home}",
            'Pick': pick,
            'Home_Score': hs,
            'Away_Score': ascore,
            'Home_Line': hline,
            'Away_Line': aline,
            'Pick_Covered_Spread(raw)': pcs,
            'Correct_Pick': correct,
            'Recalc_Is_Push': is_push,
            'Recalc_Is_Win': is_win,
            'Home_Adjusted_Score': None if hs is None or hline is None else hs + hline,
            'Computed_Home_Covers': None if hs is None or ascore is None or hline is None else (hs + hline) > ascore,
        })
    print(json.dumps(details, indent=2))
    wins=sum(1 for d in details if d['Recalc_Is_Win'])
    graded=sum(1 for d in details if d['Recalc_Is_Win'] is not None)
    print('\nSummary (excluding pushes):', wins,'wins out of', graded,'graded =>', round((wins/graded)*100,1) if graded else None)
conn.close()