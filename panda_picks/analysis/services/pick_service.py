import pandas as pd
import numpy as np
from datetime import datetime
from panda_picks.data.repositories.spread_repository import SpreadRepository
from panda_picks.data.repositories.grade_repository import GradeRepository
from panda_picks.data.repositories.pick_repository import PickRepository
from panda_picks.config.settings import Settings
from panda_picks.analysis.utils.probability import calculate_win_probability
from panda_picks.analysis.picks import ADVANTAGE_BASE_COLUMNS  # reuse existing logic for now


class PickService:
    """Service layer for generating picks. Bridges old logic and new architecture."""

    def __init__(self, spread_repo=None, grade_repo=None, pick_repo=None, settings=Settings):
        self.spread_repo = spread_repo or SpreadRepository()
        self.grade_repo = grade_repo or GradeRepository()
        self.pick_repo = pick_repo or PickRepository()
        self.settings = settings

    def generate_picks_for_week(self, week: int) -> pd.DataFrame:
        spreads_df = self.spread_repo.get_by_week(week)
        if spreads_df.empty:
            return pd.DataFrame()
        grades_df = self.grade_repo.get_all_grades()
        opp = grades_df.rename(columns={
            'Home_Team': 'Away_Team',
            'OVR': 'OPP_OVR', 'OFF': 'OPP_OFF', 'DEF': 'OPP_DEF', 'PASS': 'OPP_PASS', 'PBLK': 'OPP_PBLK', 'RECV': 'OPP_RECV',
            'RUN': 'OPP_RUN', 'RBLK': 'OPP_RBLK', 'PRSH': 'OPP_PRSH', 'COV': 'OPP_COV', 'RDEF': 'OPP_RDEF', 'TACK': 'OPP_TACK'
        })
        merged = spreads_df.merge(grades_df, on='Home_Team', how='left').merge(opp, on='Away_Team', how='left')
        for new_col, func in ADVANTAGE_BASE_COLUMNS:
            merged[new_col] = merged.apply(func, axis=1)
        thresholds = self.settings.ADVANTAGE_THRESHOLDS
        for key, thresh in thresholds.items():
            sig_col = f"{key}_sig"
            merged[sig_col] = np.select(
                [merged[key] >= thresh, merged[key] <= -thresh],
                ['home significant', 'away significant'],
                default='insignificant'
            )
        merged['Home_Win_Prob'] = merged['Overall_Adv'].apply(calculate_win_probability)
        merged['Away_Win_Prob'] = 1 - merged['Home_Win_Prob']

        def decide(row):
            sigs = [row.get(f'{c}_sig') for c in ['Overall_Adv', 'Offense_Adv', 'Defense_Adv']]
            home_sig = any(s == 'home significant' for s in sigs)
            away_sig = any(s == 'away significant' for s in sigs)
            if home_sig and not away_sig:
                return row['Home_Team']
            if away_sig and not home_sig:
                return row['Away_Team']
            return 'No Pick'

        merged['Game_Pick'] = merged.apply(decide, axis=1)
        picks_df = merged[merged['Game_Pick'] != 'No Pick'].copy()
        picks_df['Timestamp'] = datetime.utcnow().isoformat()
        if not picks_df.empty:
            self.pick_repo.save_picks(picks_df, week)
        return picks_df

