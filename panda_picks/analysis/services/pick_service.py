import pandas as pd
import numpy as np
from datetime import datetime
from panda_picks.data.repositories.spread_repository import SpreadRepository
from panda_picks.data.repositories.grade_repository import GradeRepository
from panda_picks.data.repositories.pick_repository import PickRepository
from panda_picks.config.settings import Settings
from panda_picks.analysis.utils.probability import calculate_win_probability
from panda_picks.analysis.picks import ADVANTAGE_BASE_COLUMNS  # reuse existing logic for now


def _american_to_decimal(odds):
    try:
        odds = float(odds)
    except (TypeError, ValueError):
        return np.nan
    if odds > 0:
        return 1 + odds / 100.0
    return 1 + 100.0 / abs(odds)


def _implied_probs(home_odds, away_odds):
    home_dec = _american_to_decimal(home_odds)
    away_dec = _american_to_decimal(away_odds)
    if np.isnan(home_dec) and np.isnan(away_dec):
        return (np.nan, np.nan)
    raw_home = (1 / home_dec) if not np.isnan(home_dec) else np.nan
    raw_away = (1 / away_dec) if not np.isnan(away_dec) else np.nan
    if np.isnan(raw_home) and not np.isnan(raw_away):
        return (1 - raw_away, raw_away)
    if np.isnan(raw_away) and not np.isnan(raw_home):
        return (raw_home, 1 - raw_home)
    total = raw_home + raw_away
    if total == 0:
        return (np.nan, np.nan)
    return (raw_home / total, raw_away / total)


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
        if picks_df.empty:
            return picks_df

        # Implied probabilities and edge
        picks_df['Home_ML_Implied'], picks_df['Away_ML_Implied'] = zip(*picks_df.apply(lambda r: _implied_probs(r.get('Home_Odds_Close'), r.get('Away_Odds_Close')), axis=1))
        picks_df['Pick_Prob'] = picks_df.apply(lambda r: r['Home_Win_Prob'] if r['Game_Pick'] == r['Home_Team'] else (r['Away_Win_Prob'] if r['Game_Pick'] == r['Away_Team'] else np.nan), axis=1)
        picks_df['Pick_Implied_Prob'] = picks_df.apply(lambda r: r['Home_ML_Implied'] if r['Game_Pick'] == r['Home_Team'] else (r['Away_ML_Implied'] if r['Game_Pick'] == r['Away_Team'] else np.nan), axis=1)
        picks_df['Pick_Edge'] = picks_df['Pick_Prob'] - picks_df['Pick_Implied_Prob']
        # Edge filter
        before = len(picks_df)
        picks_df = picks_df[picks_df['Pick_Edge'].abs() >= self.settings.EDGE_MIN]
        # Sort by strongest edge then overall advantage
        picks_df = picks_df.sort_values(by=['Pick_Edge','Overall_Adv'], ascending=[False, False])
        # Enforce max picks per week
        if len(picks_df) > self.settings.MAX_PICKS_PER_WEEK:
            picks_df = picks_df.head(self.settings.MAX_PICKS_PER_WEEK)
        picks_df['Timestamp'] = datetime.utcnow().isoformat()
        if not picks_df.empty:
            self.pick_repo.save_picks(picks_df, week)
        return picks_df
