import sqlite3
import time
from pathlib import Path
import os
import pandas as pd

def store_grades_data(csv_path=None, db_path=None):
    """
    Store team grades data in the database from a CSV file.

    Args:
        csv_path: Path to the CSV file containing grades data (optional)
        db_path: Path to the database file (optional)

    Returns:
        bool: True if successful, False otherwise
    """
    try:


        start_time = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] Starting grades data storage process...")

        # Determine paths if not provided
        script_dir = Path(os.path.dirname(os.path.abspath(__file__)))

        if csv_path is None:
            csv_path = script_dir.parent / "Data" / "Grades" / "TeamGrades.csv"
            print(f"[{time.strftime('%H:%M:%S')}] CSV path not provided, using default: {csv_path}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Using provided CSV path: {csv_path}")

        # Set absolute database path - important to avoid creating multiple DB files
        if db_path is None:
            # Use root project directory for database
            db_path = script_dir.parent / "nfl_data.db"
            print(f"[{time.strftime('%H:%M:%S')}] Using database at: {db_path}")

        # Verify file exists
        if not Path(csv_path).exists():
            print(f"[{time.strftime('%H:%M:%S')}] ERROR: CSV file not found at {csv_path}")
            raise FileNotFoundError(f"Grades CSV file not found: {csv_path}")

        print(f"[{time.strftime('%H:%M:%S')}] Loading grades data from {csv_path}...")

        # Load the data
        grades_df = pd.read_csv(csv_path)
        print(f"[{time.strftime('%H:%M:%S')}] Loaded grades dataframe with shape: {grades_df.shape}")
        print(f"[{time.strftime('%H:%M:%S')}] Columns in grades data: {grades_df.columns.tolist()}")

        # Connect to the database using absolute path
        print(f"[{time.strftime('%H:%M:%S')}] Connecting to database at: {db_path}")
        conn = sqlite3.connect(db_path)

        # Clear existing grades data
        cursor = conn.cursor()
        cursor.execute('DELETE FROM grades')
        print(f"[{time.strftime('%H:%M:%S')}] Cleared existing grades data")

        # Insert the new data
        print(f"[{time.strftime('%H:%M:%S')}] Inserting {len(grades_df)} team grade records...")
        grades_df.to_sql('grades', conn, if_exists='append', index=False)

        # Verify the data was inserted
        cursor.execute('SELECT COUNT(*) FROM grades')
        count = cursor.fetchone()[0]
        print(f"[{time.strftime('%H:%M:%S')}] Verified {count} records in grades table")

        conn.commit()
        conn.close()
        print(f"[{time.strftime('%H:%M:%S')}] Successfully stored team grades in the database")
        return True

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def drop_tables():
    conn = sqlite3.connect('nfl_data.db')
    cursor = conn.cursor()

    cursor.execute('DROP TABLE IF EXISTS grades')
    cursor.execute('DROP TABLE IF EXISTS advanced_stats')
    cursor.execute('DROP TABLE IF EXISTS spreads')
    cursor.execute('DROP TABLE IF EXISTS picks')
    cursor.execute('DROP TABLE IF EXISTS backtest_results')
    cursor.execute('DROP TABLE IF EXISTS picks_results')
    cursor.execute('DROP TABLE IF EXISTS teaser_results')

    conn.commit()
    conn.close()

def create_tables():
    conn = sqlite3.connect('nfl_data.db')
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
         PRIMARY KEY (TEAM)
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

    conn.commit()
    conn.close()

if __name__ == '__main__':
    drop_tables()
    create_tables()