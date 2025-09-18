import unittest
from pathlib import Path
import pandas as pd

from panda_picks import config
from panda_picks.db.database import create_tables, get_connection
from panda_picks.analysis.services.pick_service import PickService

class TestPickAnySignal(unittest.TestCase):
    def setUp(self):
        self.db_path = Path('temp_test_multi_threshold.db').resolve()
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except Exception:
                pass
        config.DATABASE_PATH = self.db_path
        create_tables()
        home = {
            'TEAM': 'HOME',
            'OVR': 85,   # Overall adv 3
            'OFF': 81,   # Offense adv 1 (below threshold)
            'PASS': 80,
            'RUN': 80,
            'RECV': 80,
            'PBLK': 80,
            'RBLK': 80,
            'DEF': 85,   # Defense adv 3
            'RDEF': 80,
            'TACK': 80,
            'PRSH': 80,
            'COV': 80,
            'WINS': 0,'LOSSES':0,'TIES':0,'PTS_SCORED':0,'PTS_ALLOWED':0
        }
        away = {
            'TEAM': 'AWAY',
            'OVR': 82,
            'OFF': 82,
            'PASS': 80,
            'RUN': 80,
            'RECV': 80,
            'PBLK': 80,
            'RBLK': 80,
            'DEF': 80,
            'RDEF': 80,
            'TACK': 80,
            'PRSH': 80,
            'COV': 80,
            'WINS': 0,'LOSSES':0,'TIES':0,'PTS_SCORED':0,'PTS_ALLOWED':0
        }
        grades_df = pd.DataFrame([home, away])
        with get_connection() as conn:
            grades_df.to_sql('grades', conn, if_exists='append', index=False)
        spreads = [{
            'WEEK': 'WEEK1',
            'Home_Team': 'HOME',
            'Away_Team': 'AWAY',
            'Home_Score': 0,
            'Away_Score': 0,
            'Home_Odds_Close': -120,
            'Away_Odds_Close': 110,
            'Home_Line_Close': -2.5,
            'Away_Line_Close': 2.5,
        }]
        spreads_df = pd.DataFrame(spreads)
        with get_connection() as conn:
            spreads_df.to_sql('spreads', conn, if_exists='append', index=False)

    def tearDown(self):
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except Exception:
            pass

    def test_pick_created_when_any_signal(self):
        service = PickService()
        df = service.generate_picks_for_week(1)
        # Should produce a pick (HOME) because Overall or Defense significant (any-signal rule)
        self.assertTrue(len(df) >= 1, 'Expected at least one pick')
        self.assertIn('HOME', df['Game_Pick'].values, 'Expected HOME to be selected')

if __name__ == '__main__':
    unittest.main()
