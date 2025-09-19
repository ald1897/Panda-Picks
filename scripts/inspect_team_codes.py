import sys, os
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from panda_picks.db.database import get_connection
from datetime import datetime

def main():
    season = datetime.now().year
    with get_connection() as conn:
        cur = conn.cursor()
        print('Distinct spreads Home_Team:')
        cur.execute("SELECT DISTINCT Home_Team FROM spreads ORDER BY Home_Team")
        print([r[0] for r in cur.fetchall()])
        print('Distinct spreads Away_Team:')
        cur.execute("SELECT DISTINCT Away_Team FROM spreads ORDER BY Away_Team")
        print([r[0] for r in cur.fetchall()])
        print('Distinct advanced_stats TEAM (week1):')
        cur.execute("SELECT DISTINCT TEAM FROM advanced_stats WHERE season=? AND week=1 ORDER BY TEAM", (season,))
        print([r[0] for r in cur.fetchall()])

if __name__ == '__main__':
    main()
