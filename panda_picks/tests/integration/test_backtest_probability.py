import os
import sqlite3
from pathlib import Path
import pandas as pd
import unittest
import gc

from panda_picks import config
from panda_picks.db.database import create_tables, get_connection
from panda_picks.analysis.backtest import backtest

class TestBacktestProbabilityMetrics(unittest.TestCase):
    def setUp(self):
        # Explicit temp DB file under project root tests directory
        self.db_path = Path('temp_test_backtest.db').resolve()
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except Exception:
                pass
        config.DATABASE_PATH = self.db_path
        create_tables()
        with get_connection() as conn:
            spreads = pd.DataFrame([
                {
                    'WEEK': 'WEEK1', 'Home_Team': 'TEAM_A', 'Away_Team': 'TEAM_B',
                    'Home_Score': 24, 'Away_Score': 17,
                    'Home_Odds_Close': -120, 'Away_Odds_Close': 110,
                    'Home_Line_Close': -3.5, 'Away_Line_Close': 3.5,
                }
            ])
            spreads.to_sql('spreads', conn, if_exists='append', index=False)
            picks = pd.DataFrame([
                {
                    'WEEK': 'WEEK1', 'Home_Team': 'TEAM_A', 'Away_Team': 'TEAM_B',
                    'Home_Line_Close': -3.5, 'Away_Line_Close': 3.5,
                    'Game_Pick': 'TEAM_A', 'Overall_Adv': 4.0,
                    'Offense_Adv': 2.0, 'Defense_Adv': 1.0,
                }
            ])
            picks.to_sql('picks', conn, if_exists='append', index=False)
            try:
                conn.execute("ALTER TABLE picks ADD COLUMN Home_Win_Prob REAL")
            except Exception:
                pass
            conn.execute("UPDATE picks SET Home_Win_Prob=? WHERE WEEK='WEEK1'", (0.62,))
            conn.commit()

    def tearDown(self):
        # Force GC to help close any lingering connections
        gc.collect()
        # Attempt to close any stray connections by opening and closing one
        try:
            sqlite3.connect(self.db_path).close()
        except Exception:
            pass
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except Exception:
            # Final fallback: ignore if still locked
            pass

    def test_probability_metrics_generated(self):
        backtest(simulate_missing=False)
        with get_connection() as conn:
            df = pd.read_sql_query('SELECT * FROM probability_game_metrics', conn)
            self.assertFalse(df.empty, 'probability_game_metrics is empty')
            for col in ['Home_Odds_Implied_Prob','Home_Spread_Implied_Prob','Home_Edge_ML','Home_Edge_Spread']:
                self.assertIn(col, df.columns)
            self.assertTrue((df['Home_Odds_Implied_Prob'].notna()).any())
            self.assertTrue((df['Home_Edge_ML'].notna()).any())

if __name__ == '__main__':
    unittest.main()
