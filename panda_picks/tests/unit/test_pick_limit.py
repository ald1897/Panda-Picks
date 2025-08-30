import unittest
import pandas as pd
from pathlib import Path
import os

from panda_picks import config
from panda_picks.db.database import create_tables, get_connection
from panda_picks.analysis.services.pick_service import PickService
from panda_picks.config.settings import Settings

class TestPickLimit(unittest.TestCase):
    def setUp(self):
        # Temp DB
        self.db_path = Path('temp_test_pick_limit.db').resolve()
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except Exception:
                pass
        config.DATABASE_PATH = self.db_path
        create_tables()
        # Insert grades for 16 teams (8 games)
        teams = []
        for i in range(16):
            teams.append({
                'TEAM': f'TEAM_{i}',
                'OVR': 80 + (15 - i),  # decreasing so earlier teams stronger
                'OFF': 80 + (15 - i),
                'PASS': 80 + (15 - i),
                'RUN': 80 + (15 - i),
                'RECV': 80 + (15 - i),
                'PBLK': 80 + (15 - i),
                'RBLK': 80 + (15 - i),
                'DEF': 80 + (15 - i),
                'RDEF': 80 + (15 - i),
                'TACK': 80 + (15 - i),
                'PRSH': 80 + (15 - i),
                'COV': 80 + (15 - i),
                'WINS': 0,
                'LOSSES': 0,
                'TIES': 0,
                'PTS_SCORED': 0,
                'PTS_ALLOWED': 0,
            })
        grades_df = pd.DataFrame(teams)
        with get_connection() as conn:
            grades_df.to_sql('grades', conn, if_exists='append', index=False)
        # Create 8 spreads games week 1 where home team has higher index advantage
        spreads = []
        for g in range(8):
            home = f'TEAM_{g}'  # stronger team
            away = f'TEAM_{15-g}'  # weaker team
            spreads.append({
                'WEEK': 'WEEK1',
                'Home_Team': home,
                'Away_Team': away,
                'Home_Score': 0,
                'Away_Score': 0,
                'Home_Odds_Close': -140,  # implied ~58%
                'Away_Odds_Close': 130,
                'Home_Line_Close': -3.5,
                'Away_Line_Close': 3.5,
            })
        spreads_df = pd.DataFrame(spreads)
        with get_connection() as conn:
            spreads_df.to_sql('spreads', conn, if_exists='append', index=False)

    def tearDown(self):
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except Exception:
            pass

    def test_max_pick_limit_enforced(self):
        """Ensure generated picks never exceed Settings.MAX_PICKS_PER_WEEK."""
        service = PickService()
        df = service.generate_picks_for_week(1)
        # There are 8 potential picks, verify capped at MAX_PICKS_PER_WEEK
        self.assertLessEqual(len(df), Settings.MAX_PICKS_PER_WEEK)
        self.assertTrue(len(df) > 0)
        # Ensure sorted by Pick_Edge descending
        edges = df['Pick_Edge'].tolist()
        self.assertEqual(edges, sorted(edges, reverse=True))
        # Check picks table persisted count also <= limit
        with get_connection() as conn:
            picks_in_db = pd.read_sql_query("SELECT * FROM picks WHERE WEEK='WEEK1'", conn)
        self.assertLessEqual(len(picks_in_db), Settings.MAX_PICKS_PER_WEEK)

if __name__ == '__main__':
    unittest.main()
