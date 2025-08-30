import unittest
from pathlib import Path
from uuid import uuid4
from panda_picks import config
from panda_picks.db.database import create_tables, get_connection
from panda_picks.ui.data import get_available_weeks, get_week_matchups, get_matchup_details

class TestMatchupDetails(unittest.TestCase):
    def setUp(self):
        # isolated temp db (unique per test to avoid locking / leftover data)
        self.db_path = Path(f'temp_test_matchup_details_{uuid4().hex}.db').resolve()
        config.DATABASE_PATH = self.db_path
        create_tables()
        # Insert grades
        with get_connection() as conn:
            conn.execute("INSERT INTO grades (TEAM, OVR, OFF, PASS, RUN, RECV, PBLK, RBLK, DEF, RDEF, TACK, PRSH, COV, WINS, LOSSES, TIES, PTS_SCORED, PTS_ALLOWED) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         ('HOME_T',90,88,87,86,85,84,83,82,81,80,79,78,0,0,0,0,0))
            conn.execute("INSERT INTO grades (TEAM, OVR, OFF, PASS, RUN, RECV, PBLK, RBLK, DEF, RDEF, TACK, PRSH, COV, WINS, LOSSES, TIES, PTS_SCORED, PTS_ALLOWED) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         ('AWAY_T',70,69,68,67,66,65,64,63,62,61,60,59,0,0,0,0,0))
        # Insert spreads & pick
        with get_connection() as conn:
            conn.execute("INSERT INTO spreads (WEEK, Home_Team, Away_Team, Home_Line_Close, Away_Line_Close, Home_Odds_Close, Away_Odds_Close) VALUES (?,?,?,?,?,?,?)",
                         ('WEEK1','HOME_T','AWAY_T', -4.5, 4.5, -180, 160))
            conn.execute("INSERT INTO picks (WEEK, Home_Team, Away_Team, Game_Pick, Home_Line_Close, Away_Line_Close, Overall_Adv, Offense_Adv, Defense_Adv, Off_Comp_Adv, Def_Comp_Adv) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         ('WEEK1','HOME_T','AWAY_T','HOME_T', -4.5, 4.5, 6.1, 3.2, 2.9, 1.4, 1.1))

    def tearDown(self):
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except Exception:
            pass

    def test_matchup_details_with_pick(self):
        weeks = get_available_weeks()
        self.assertIn('WEEK1', weeks)
        matchups = get_week_matchups('WEEK1')
        self.assertTrue(matchups)
        label = matchups[0]['Label']
        away, _, home = label.partition(' @ ')
        details = get_matchup_details('WEEK1', home, away)
        self.assertIn('Home_Line_Close', details['spread'])
        # Ensure pick metrics present
        self.assertIn('Overall_Adv', details['pick'])
        self.assertIn('OVR', details['home_grades'])
        self.assertIn('OVR', details['away_grades'])

    def test_matchup_details_without_pick(self):
        # Remove pick row
        with get_connection() as conn:
            conn.execute("DELETE FROM picks WHERE WEEK='WEEK1' AND Home_Team='HOME_T' AND Away_Team='AWAY_T'")
        details = get_matchup_details('WEEK1', 'HOME_T', 'AWAY_T')
        self.assertIn('Home_Line_Close', details['spread'])
        self.assertEqual(details['pick'], {})  # No pick data
        self.assertIn('OVR', details['home_grades'])
        self.assertIn('OVR', details['away_grades'])

if __name__ == '__main__':
    unittest.main()
