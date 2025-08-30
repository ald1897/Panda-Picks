import sqlite3
import time
from panda_picks import config

import os
import pandas as pd
from datetime import datetime
import threading
import weakref

# Environment flag to force reset
FORCE_RESET = os.getenv("PANDA_FORCE_RESET_DB", "0") == "1"

# Track open connections to allow coordinated shutdown / reset on Windows
_OPEN_CONNS = set()
_OPEN_CONNS_LOCK = threading.Lock()

class _ManagedConnection:
    """Wrapper so that `with get_connection()` auto-closes (sqlite3.Connection alone does not)."""
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        # Register in global set
        with _OPEN_CONNS_LOCK:
            _OPEN_CONNS.add(conn)
        # Finalizer to attempt removal when GC'ed
        weakref.finalize(self, self._finalize, conn)

    def _finalize(self, conn):
        with _OPEN_CONNS_LOCK:
            _OPEN_CONNS.discard(conn)

    # Delegate attribute access
    def __getattr__(self, item):
        return getattr(self._conn, item)

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc, tb):
        try:
            self.close()
        except Exception:
            pass

    def close(self):  # explicit close propagates and untracks
        try:
            self._conn.close()
        finally:
            with _OPEN_CONNS_LOCK:
                _OPEN_CONNS.discard(self._conn)


def close_all_connections():
    """Force-close all tracked SQLite connections (use before DB file operations)."""
    with _OPEN_CONNS_LOCK:
        conns = list(_OPEN_CONNS)
        _OPEN_CONNS.clear()
    for c in conns:
        try:
            c.close()
        except Exception:
            pass

# --- SQLite file validation & recovery helpers --- #

def _is_valid_sqlite_file(path: str) -> bool:
    try:
        if not os.path.exists(path):
            return True  # new file is fine
        if os.path.isdir(path):
            return False
        with open(path, 'rb') as f:
            header = f.read(16)
        return header.startswith(b'SQLite format 3')
    except Exception:
        return False


def _timestamp() -> str:
    return datetime.utcnow().strftime('%Y%m%d_%H%M%S')


def _rename_corrupt(path: str, reason: str):
    if not os.path.exists(path):
        return
    # Ensure no handles are open (important on Windows)
    close_all_connections()
    # Check if file is still locked by another process
    try:
        with open(path, 'a+b'):
            pass
    except Exception as lock_exc:
        print(f"[DB] ERROR: Database file '{path}' is still locked by another process and cannot be renamed or deleted.\nDetails: {lock_exc}\nPlease close all applications or processes that may be using this file and try again.")
        # Abort further DB operations by raising a custom exception
        raise RuntimeError(f"Database file '{path}' is locked and cannot be reset.")
    base = f"{path}.corrupt.{_timestamp()}"
    try:
        os.replace(path, base)
        print(f"[DB] Renamed corrupt DB ({reason}) -> {base}")
    except Exception as e:
        print(f"[DB] Could not rename corrupt DB ({e}); attempting delete")
        try:
            os.remove(path)
            print(f"[DB] Deleted corrupt DB {path}")
        except Exception as e2:
            print(f"[DB] Failed to remove corrupt DB {path}: {e2}")
            raise RuntimeError(f"Database file '{path}' could not be removed: {e2}")


def _ensure_dir():
    db_dir = os.path.dirname(str(config.DATABASE_PATH))
    os.makedirs(db_dir, exist_ok=True)


def _ensure_valid_db():
    _ensure_dir()
    db_path = str(config.DATABASE_PATH)
    try:
        if FORCE_RESET and os.path.exists(db_path):
            _rename_corrupt(db_path, 'FORCE_RESET')
            return
        if not _is_valid_sqlite_file(db_path):
            _rename_corrupt(db_path, 'bad header')
    except RuntimeError as e:
        print(f"[DB] ABORT: {e}")
        raise


def _integrity_ok(conn: sqlite3.Connection) -> bool:
    try:
        cur = conn.cursor()
        cur.execute('PRAGMA quick_check')
        rows = cur.fetchall()
        if not rows:
            return False
        # quick_check returns [('ok',)] when fine
        return all(r[0] == 'ok' for r in rows if len(r) > 0)
    except Exception:
        return False


def get_connection():
    """Get a managed connection to the database; recover if corrupt.

    Returns a wrapper so that `with get_connection()` will close the connection
    (sqlite3's native context manager only manages transactions, not closing).
    """
    _ensure_valid_db()
    db_path = str(config.DATABASE_PATH)
    try:
        conn = sqlite3.connect(db_path, timeout=30, isolation_level=None)  # autocommit mode
    except sqlite3.OperationalError as e:
        if 'unsupported file format' in str(e).lower():
            _rename_corrupt(db_path, 'unsupported file format on connect')
            conn = sqlite3.connect(db_path, timeout=30, isolation_level=None)
        else:
            raise
    # Apply pragmas for better concurrent read/write behavior
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA foreign_keys=ON')
    except Exception:
        pass
    # Integrity check
    if not _integrity_ok(conn):
        try:
            conn.close()
        except Exception:
            pass
        _rename_corrupt(db_path, 'integrity check failed')
        conn = sqlite3.connect(db_path, timeout=30, isolation_level=None)
        try:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA foreign_keys=ON')
        except Exception:
            pass
    return _ManagedConnection(conn)


def store_grades_data():
    """Store team grades data in the database from a CSV file."""
    try:
        start_time = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] Starting grades data storage process...")

        csv_path = config.TEAM_GRADES_CSV
        print(f"[{time.strftime('%H:%M:%S')}] Using database at: {config.DATABASE_PATH}")

        if not csv_path.exists():
            print(f"[{time.strftime('%H:%M:%S')}] ERROR: CSV file not found at {csv_path}")
            raise FileNotFoundError(f"Grades CSV file not found: {csv_path}")

        grades_df = pd.read_csv(csv_path)
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM grades')
        except sqlite3.OperationalError:
            pass
        grades_df.to_sql('grades', conn, if_exists='append', index=False)
        print(f"[{time.strftime('%H:%M:%S')}] Grades data stored successfully in the database.")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[time.strftime('%H:%M:%S')] ERROR: {e}")
        return False


def drop_tables():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for tbl in ['grades','advanced_stats','spreads','picks','backtest_results','picks_results','teaser_results']:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS {tbl}')
            except sqlite3.OperationalError as e:
                print(f"[DB] Warning dropping {tbl}: {e}")
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as e:
        if 'unsupported file format' in str(e).lower():
            print('[DB] Drop failed due to unsupported format; forcing recreate')
            _rename_corrupt(str(config.DATABASE_PATH), 'unsupported file format during drop')
        else:
            raise


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    # Create grades table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS grades (        
         TEAM TEXT PRIMARY KEY,
         OVR REAL,
         OFF REAL,
         PASS REAL,
         RUN REAL,
         RECV REAL,
         PBLK REAL,
         RBLK REAL,
         DEF REAL,
         RDEF REAL,
         TACK REAL,
         PRSH REAL,
         COV REAL,
         WINS INTEGER,
         LOSSES INTEGER,
         TIES INTEGER,
         PTS_SCORED INTEGER,
         PTS_ALLOWED INTEGER,
         LAST_UPDATED TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
                   ''')

    # Create advanced_stats table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS advanced_stats (
                                                                 season INTEGER,
                                                                 type TEXT,
                                                                 TEAM TEXT,
                                                                 composite_score REAL,
                                                                 PRIMARY KEY (season, type, TEAM)
                       )
                   ''')

    # Create spreads table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS spreads (
                                                          WEEK TEXT,
                                                          Home_Team TEXT,
                                                          Away_Team TEXT,
                                                          Home_Score INTEGER,
                                                          Away_Score INTEGER,
                                                          Home_Odds_Close REAL,
                                                          Away_Odds_Close REAL,
                                                          Home_Line_Close REAL,
                                                          Away_Line_Close REAL,
                                                          PRIMARY KEY (WEEK, Home_Team, Away_Team)
                       )
                   ''')

    # Create picks table (expanded schema to align with analysis outputs)
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS picks (
                                                        WEEK TEXT,
                                                        Home_Team TEXT,
                                                        Away_Team TEXT,
                                                        Home_Line_Close REAL,
                                                        Away_Line_Close REAL,
                                                        Home_Odds_Close REAL,
                                                        Away_Odds_Close REAL,
                                                        Game_Pick TEXT,
                                                        Overall_Adv REAL,
                                                        Offense_Adv REAL,
                                                        Defense_Adv REAL,
                                                        Overall_Adv_sig TEXT,
                                                        Offense_Adv_sig TEXT,
                                                        Defense_Adv_sig TEXT,
                                                        Pressure_Mismatch REAL,
                                                        Explosive_Pass_Mismatch REAL,
                                                        Script_Control_Mismatch REAL,
                                                        Home_Win_Prob REAL,
                                                        Away_Win_Prob REAL,
                                                        Home_ML_Implied REAL,
                                                        Away_ML_Implied REAL,
                                                        Pick_Prob REAL,
                                                        Pick_Implied_Prob REAL,
                                                        Pick_Edge REAL,
                                                        Pick_Cover_Prob REAL,
                                                        PRIMARY KEY (WEEK, Home_Team, Away_Team)
                       )
                   ''')

    # Create backtest_results table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS backtest_results (
                                                                   WEEK TEXT PRIMARY KEY,
                                                                   total_wagered REAL,
                                                                   total_spread_wins INTEGER,
                                                                   total_spread_bets INTEGER,
                                                                   total_ml_wins INTEGER,
                                                                   total_ml_bets INTEGER,
                                                                   total_profit REAL,
                                                                   spread_win_percentage REAL,
                                                                   ml_win_percentage REAL,
                                                                   perfect_weeks INTEGER,
                                                                   weekly_profit REAL
                       )
                   ''')

    # Create picks_results table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS picks_results (
                                                                WEEK TEXT,
                                                                Home_Team TEXT,
                                                                Away_Team TEXT,
                                                                Home_Score INTEGER,
                                                                Away_Score INTEGER,
                                                                Home_Odds_Close REAL,
                                                                Away_Odds_Close REAL,
                                                                Home_Line_Close REAL,
                                                                Away_Line_Close REAL,
                                                                Game_Pick TEXT,
                                                                Winner TEXT,
                                                                Correct_Pick INTEGER,
                                                                Pick_Covered_Spread INTEGER,
                                                                Overall_Adv REAL,
                                                                Offense_Adv REAL,
                                                                Defense_Adv REAL,
                                                                Off_Comp_Adv REAL,
                                                                Def_Comp_Adv REAL,
                                                                Overall_Adv_Sig TEXT,
                                                                Offense_Adv_Sig TEXT,
                                                                Defense_Adv_Sig TEXT,
                                                                Off_Comp_Adv_Sig TEXT,
                                                                Def_Comp_Adv_Sig TEXT,
                                                                PRIMARY KEY (WEEK, Home_Team, Away_Team)
                       )
                   ''')

    # Create teaser_results table (single definition)
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS teaser_results (
                                                                 Combo TEXT,
                                                                 Winnings REAL,
                                                                 Type TEXT,
                                                                 WEEK TEXT,
                                                                 Total_Amount_Wagered REAL,
                                                                 Weekly_Profit REAL,
                                                                 Total_Profit REAL,
                                                                 Total_Profit_Over_All_Weeks REAL,
                                                                 Total_Balance REAL,
                                                                 PRIMARY KEY (Combo, WEEK)
                       )
                   ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    drop_tables()
    create_tables()