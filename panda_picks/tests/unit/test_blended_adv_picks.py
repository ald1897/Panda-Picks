import unittest
import pandas as pd
from pathlib import Path
from datetime import datetime

from panda_picks import config
from panda_picks.db.database import create_tables, get_connection
from panda_picks.analysis.advanced_features import build_matchup_features
from panda_picks.analysis.services.pick_service import PickService
from panda_picks.analysis.utils.probability import calculate_win_probability
from panda_picks.config.settings import Settings


class TestBlendedAdvInPicks(unittest.TestCase):
    def setUp(self):
        # Temp DB
        self.db_path = Path('temp_test_blended_adv.db').resolve()
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except Exception:
                pass
        config.DATABASE_PATH = self.db_path
        create_tables()
        self.season = datetime.now().year
        self.week = 1
        # Seed grades (strong home vs weaker away for 2 games)
        teams = []
        for name, base in [('AAA', 85), ('BBB', 72), ('CCC', 84), ('DDD', 70)]:
            teams.append({
                'TEAM': name,
                'OVR': base,
                'OFF': base,
                'PASS': base,
                'RUN': base,
                'RECV': base,
                'PBLK': base,
                'RBLK': base,
                'DEF': base - 5,
                'RDEF': base - 5,
                'TACK': base - 5,
                'PRSH': base - 5,
                'COV': base - 5,
                'WINS': 0,
                'LOSSES': 0,
                'TIES': 0,
                'PTS_SCORED': 0,
                'PTS_ALLOWED': 0,
            })
        grades_df = pd.DataFrame(teams)
        with get_connection() as conn:
            grades_df.to_sql('grades', conn, if_exists='append', index=False)
        # Seed spreads for 2 games
        spreads = [
            {'WEEK': f'WEEK{self.week}', 'Home_Team': 'AAA', 'Away_Team': 'BBB', 'Home_Score': None, 'Away_Score': None, 'Home_Odds_Close': -140, 'Away_Odds_Close': 130, 'Home_Line_Close': -3.0, 'Away_Line_Close': 3.0},
            {'WEEK': f'WEEK{self.week}', 'Home_Team': 'CCC', 'Away_Team': 'DDD', 'Home_Score': None, 'Away_Score': None, 'Home_Odds_Close': -150, 'Away_Odds_Close': 135, 'Home_Line_Close': -3.5, 'Away_Line_Close': 3.5},
        ]
        with get_connection() as conn:
            pd.DataFrame(spreads).to_sql('spreads', conn, if_exists='append', index=False)
        # Seed advanced_stats offense/defense composites to ensure matchup_features exist
        adv_rows = [
            (self.season, self.week, 'offense', 'AAA', 15.0, 1.0, 'ts'),
            (self.season, self.week, 'defense', 'AAA', 10.0, 0.5, 'ts'),
            (self.season, self.week, 'offense', 'BBB', 8.0, -0.4, 'ts'),
            (self.season, self.week, 'defense', 'BBB', 7.0, -0.6, 'ts'),
            (self.season, self.week, 'offense', 'CCC', 14.0, 0.9, 'ts'),
            (self.season, self.week, 'defense', 'CCC', 9.0, 0.4, 'ts'),
            (self.season, self.week, 'offense', 'DDD', 6.0, -0.8, 'ts'),
            (self.season, self.week, 'defense', 'DDD', 5.0, -1.0, 'ts'),
        ]
        with get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(
                "INSERT OR REPLACE INTO advanced_stats (season, week, type, TEAM, composite_score, z_score, last_updated) VALUES (?,?,?,?,?,?,?)",
                adv_rows
            )
            conn.commit()
        # Build matchup_features in DB
        with get_connection() as conn:
            _ = build_matchup_features(conn, self.season, self.week)

    def tearDown(self):
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except Exception:
            pass

    def test_generated_picks_include_blended_columns(self):
        service = PickService()
        df = service.generate_picks_for_week(self.week)
        # Should produce picks
        self.assertTrue(len(df) > 0)
        # Required columns
        required = ['Off_Comp_Diff','Def_Comp_Diff','Net_Composite','Net_Composite_norm','Blended_Adv','Home_Win_Prob','Away_Win_Prob']
        for c in required:
            self.assertIn(c, df.columns, f"Missing column {c}")
        # Non-null when matchup_features exist
        self.assertTrue(df['Off_Comp_Diff'].notna().all())
        self.assertTrue(df['Def_Comp_Diff'].notna().all())
        self.assertTrue(df['Net_Composite'].notna().all())
        self.assertTrue(df['Net_Composite_norm'].notna().all())
        self.assertTrue(df['Blended_Adv'].notna().all())
        # Sig column present (blended preferred)
        self.assertIn('Blended_Adv_sig', df.columns)
        # Probability mapping uses Blended_Adv
        alpha = Settings.BLEND_ALPHA
        row = df.iloc[0]
        blended = alpha * float(row['Overall_Adv']) + (1 - alpha) * float(row['Net_Composite_norm'])
        expected_prob = calculate_win_probability(blended)
        self.assertAlmostEqual(float(row['Home_Win_Prob']), expected_prob, places=6)
        # Persisted picks table has blended columns
        with get_connection() as conn:
            picks_in_db = pd.read_sql_query("SELECT * FROM picks WHERE WEEK=?", conn, params=[f"WEEK{self.week}"])
        for c in ['Blended_Adv','Net_Composite_norm','Off_Comp_Diff','Def_Comp_Diff']:
            self.assertIn(c, picks_in_db.columns)
            self.assertTrue(picks_in_db[c].notna().all())


if __name__ == '__main__':
    unittest.main()

