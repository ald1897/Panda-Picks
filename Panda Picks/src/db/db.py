import sqlite3

def create_tables():
    conn = sqlite3.connect('nfl_data.db')
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
            COV REAL
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS picks (
            WEEK TEXT,
            Home_Team TEXT,
            Away_Team TEXT,
            Home_Spread REAL,
            Away_Spread REAL,
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
            WEEK TEXT PRIMARY KEY,
            total_wagered REAL,
            total_spread_wins INTEGER,
            total_spread_bets INTEGER,
            total_ml_wins INTEGER,
            total_ml_bets INTEGER,
            total_profit REAL,
            spread_win_percentage REAL,
            ml_win_percentage REAL,
            perfect_weeks INTEGER
        )
    ''')

    # Create matchups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matchups (
            Week TEXT,
            Home_Team TEXT,
            Away_Team TEXT,
            Home_Spread REAL,
            Away_Spread REAL,
            PRIMARY KEY (Week, Home_Team, Away_Team)
        )
    ''')

    # Create pick_results table
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
                    Home_Spread REAL,
                    Away_Spread REAL,
                    Game_Pick TEXT,
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
                    ATS_Pick_Correct INTEGER,
                    ATS_Winnings TEXT,
                    Winner TEXT,
                    ML_Winnings TEXT,
                    Winner_Pick_Correct INTEGER,
                    Total_Amount_Wagered REAL,
                    Total_Profit REAL,
                    PRIMARY KEY (WEEK, Home_Team, Away_Team)
                )
            ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_tables()