import sqlite3, os
from panda_picks import config

def dump(team_home='BUF', team_away='BLT'):
    db_path = getattr(config, 'DATABASE_PATH', 'database/nfl_data.db')
    if not os.path.exists(db_path):
        print('DB missing', db_path)
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    tables = ['picks','picks_results','spreads']
    for t in tables:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,))
        if not cur.fetchone():
            print(f'Table {t} missing')
            continue
        cur.execute(f"PRAGMA table_info({t})")
        cols = [c[1] for c in cur.fetchall()]
        # Case-insensitive match
        cur.execute(f"SELECT * FROM {t} WHERE UPPER(Home_Team)=? AND UPPER(Away_Team)=?", (team_home.upper(), team_away.upper()))
        rows = cur.fetchall()
        print('\nTABLE', t, 'cols:', cols)
        for r in rows:
            rowd = dict(zip(cols, r))
            print(rowd)
    conn.close()

if __name__ == '__main__':
    dump()

