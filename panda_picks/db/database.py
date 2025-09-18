import sqlite3
import time
from panda_picks import config


import pandas as pd


def get_connection():
    """Get a connection to the database."""
    return sqlite3.connect(config.DATABASE_PATH)

def store_grades_data():
    """Store team grades data in the database from a CSV file."""
    try:
        start_time = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] Starting grades data storage process...")

        csv_path = config.TEAM_GRADES_CSV
        # print(f"[{time.strftime('%H:%M:%S')}] Using CSV path: {csv_path}")
        print(f"[{time.strftime('%H:%M:%S')}] Using database at: {config.DATABASE_PATH}")

        # Verify file exists
        if not csv_path.exists():
            print(f"[{time.strftime('%H:%M:%S')}] ERROR: CSV file not found at {csv_path}")
            raise FileNotFoundError(f"Grades CSV file not found: {csv_path}")

        # Load the data
        grades_df = pd.read_csv(csv_path)

        # Connect to the database using absolute path
        conn = get_connection()

        # Clear existing grades data
        cursor = conn.cursor()
        cursor.execute('DELETE FROM grades')

        # Insert the new data
        grades_df.to_sql('grades', conn, if_exists='append', index=False)
        print(f"[{time.strftime('%H:%M:%S')}] Grades data stored successfully in the database.")

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ERROR: {e}")
        return False

def drop_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # drop all tables
    cursor.execute('DROP TABLE IF EXISTS grades')
    cursor.execute('DROP TABLE IF EXISTS advanced_stats')
    cursor.execute('DROP TABLE IF EXISTS spreads')
    cursor.execute('DROP TABLE IF EXISTS picks')
    cursor.execute('DROP TABLE IF EXISTS backtest_results')
    cursor.execute('DROP TABLE IF EXISTS picks_results')
    cursor.execute('DROP TABLE IF EXISTS teaser_results')
    cursor.execute('DROP TABLE IF EXISTS excluded_teams')  # newly added



    conn.commit()
    conn.close()

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    # Create grades table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS grades (        
         TEAM TEXT,
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
         LAST_UPDATED TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         PRIMARY KEY (TEAM)
)
                   ''')

    # Prior season grades snapshot (single row per team, no week dimension)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS grades_prior (
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
         SOURCE TEXT,
         CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Weekly snapshots of current season grades (audit trail)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS grades_snapshots (
         Season INTEGER,
         Week TEXT,
         TEAM TEXT,
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
         SNAPSHOT_TS TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         PRIMARY KEY (Season, Week, TEAM)
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

    # Create picks table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS picks (
                                                        WEEK TEXT,
                                                        Home_Team TEXT,
                                                        Away_Team TEXT,
                                                        Home_Line_Close REAL,
                                                        Away_Line_Close REAL,
                                                        Game_Pick TEXT,
                                                        Overall_Adv REAL,
                                                        Offense_Adv REAL,
                                                        Defense_Adv REAL,
                                                        Off_Comp_Adv REAL,
                                                        Def_Comp_Adv REAL,
                                                        Off_Comp_Adv_sig TEXT,
                                                        Def_Comp_Adv_sig TEXT,
                                                        Overall_Adv_sig TEXT,
                                                        Offense_Adv_sig TEXT,
                                                        Defense_Adv_sig TEXT,
                                                        PRIMARY KEY (WEEK, Home_Team, Away_Team)
                       )
                   ''')

    # Create backtest_results table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS backtest_results (
                                                                   WEEK TEXT,
                                                                   total_wagered REAL,
                                                                   total_spread_wins INTEGER,
                                                                   total_spread_bets INTEGER,
                                                                   total_ml_wins INTEGER,
                                                                   total_ml_bets INTEGER,
                                                                   total_profit REAL,
                                                                   spread_win_percentage REAL,
                                                                   ml_win_percentage REAL,
                                                                   perfect_weeks INTEGER,
                                                                   weekly_profit REAL,
                                                                   PRIMARY KEY (WEEK)
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

    # create teaser_results table
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


    # Excluded teams (manual UI exclusions for combos)
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS excluded_teams (
                                                                 WEEK TEXT,
                                                                 Team TEXT,
                                                                 PRIMARY KEY (WEEK, Team)
                       )
                   ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    drop_tables()
    create_tables()