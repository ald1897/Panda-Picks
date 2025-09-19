import pandas as pd
import numpy as np
from datetime import datetime
from panda_picks.data.repositories.spread_repository import SpreadRepository
from panda_picks.data.repositories.grade_repository import GradeRepository
from panda_picks.data.repositories.pick_repository import PickRepository
from panda_picks.config.settings import Settings
from panda_picks.analysis.utils.probability import calculate_win_probability
from panda_picks.analysis.picks import ADVANTAGE_BASE_COLUMNS  # reuse existing logic for now
from panda_picks.db.database import get_connection
from panda_picks.utils import normalize_df_team_cols


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
    """Service layer for generating picks. Bridges old logic and new architecture.

    Selection rule: Prefer Blended_Adv significance with Offense/Defense; if blended missing, fall back to Overall_Adv.
    """

    def __init__(self, spread_repo=None, grade_repo=None, pick_repo=None, settings=Settings):
        self.spread_repo = spread_repo or SpreadRepository()
        self.grade_repo = grade_repo or GradeRepository()
        self.pick_repo = pick_repo or PickRepository()
        self.settings = settings

    def _attach_phase2_features(self, df: pd.DataFrame, week: int) -> pd.DataFrame:
        """Join matchup_features and compute normalized Net_Composite and Blended_Adv."""
        try:
            season = datetime.now().year
            with get_connection() as conn:
                feats = pd.read_sql_query(
                    "SELECT Home_Team, Away_Team, off_comp_diff AS Off_Comp_Diff, def_comp_diff AS Def_Comp_Diff, net_composite AS Net_Composite FROM matchup_features WHERE season=? AND week=?",
                    conn, params=[season, week]
                )
            if feats.empty:
                for c in ['Off_Comp_Diff','Def_Comp_Diff','Net_Composite','Net_Composite_norm','Blended_Adv']:
                    if c not in df.columns:
                        df[c] = np.nan
                return df
            feats = normalize_df_team_cols(feats, ['Home_Team','Away_Team'])
            merged = df.merge(feats, on=['Home_Team','Away_Team'], how='left')
            mu = merged['Net_Composite'].mean(skipna=True)
            sd = merged['Net_Composite'].std(skipna=True)
            merged['Net_Composite_norm'] = (merged['Net_Composite'] - mu) / sd if sd and sd > 0 else 0.0
            alpha = self.settings.BLEND_ALPHA
            merged['Blended_Adv'] = alpha * merged['Overall_Adv'].astype(float) + (1 - alpha) * merged['Net_Composite_norm'].astype(float)
            return merged
        except Exception:
            for c in ['Off_Comp_Diff','Def_Comp_Diff','Net_Composite','Net_Composite_norm','Blended_Adv']:
                if c not in df.columns:
                    df[c] = np.nan
            return df

    def generate_picks_for_week(self, week: int) -> pd.DataFrame:
        spreads_df = self.spread_repo.get_by_week(week)
        if spreads_df.empty:
            return pd.DataFrame()
        spreads_df = normalize_df_team_cols(spreads_df, ['Home_Team','Away_Team'])
        grades_df = self.grade_repo.get_all_grades()
        grades_df = normalize_df_team_cols(grades_df, ['Home_Team'])
        opp = grades_df.rename(columns={
            'Home_Team': 'Away_Team',
            'OVR': 'OPP_OVR', 'OFF': 'OPP_OFF', 'DEF': 'OPP_DEF', 'PASS': 'OPP_PASS', 'PBLK': 'OPP_PBLK', 'RECV': 'OPP_RECV',
            'RUN': 'OPP_RUN', 'RBLK': 'OPP_RBLK', 'PRSH': 'OPP_PRSH', 'COV': 'OPP_COV', 'RDEF': 'OPP_RDEF', 'TACK': 'OPP_TACK'
        })
        merged = spreads_df.merge(grades_df, on='Home_Team', how='left').merge(opp, on='Away_Team', how='left')
        for new_col, func in ADVANTAGE_BASE_COLUMNS:
            merged[new_col] = merged.apply(func, axis=1)
        # Phase 2: attach matchup features and blended adv
        merged = self._attach_phase2_features(merged, week)
        thresholds = self.settings.ADVANTAGE_THRESHOLDS
        # classify significance for classic three always
        for key in ['Overall_Adv','Offense_Adv','Defense_Adv']:
            thresh = thresholds.get(key, 0.0)
            sig_col = f"{key}_sig"
            merged[sig_col] = np.select(
                [merged[key] >= thresh, merged[key] <= -thresh],
                ['home significant', 'away significant'],
                default='insignificant'
            )
        # blended only if present and non-null anywhere
        if 'Blended_Adv' in merged.columns and merged['Blended_Adv'].notna().any():
            bth = thresholds.get('Blended_Adv', thresholds.get('Overall_Adv', 0.0))
            merged['Blended_Adv_sig'] = np.select(
                [merged['Blended_Adv'] >= bth, merged['Blended_Adv'] <= -bth],
                ['home significant', 'away significant'],
                default='insignificant'
            )
        # probabilities: prefer blended per row if non-null
        def _adv_for_row(r):
            bv = r.get('Blended_Adv')
            if pd.notna(bv):
                return float(bv)
            return float(r.get('Overall_Adv', 0.0))
        merged['Home_Win_Prob'] = merged.apply(lambda r: calculate_win_probability(_adv_for_row(r)), axis=1)
        merged['Away_Win_Prob'] = 1 - merged['Home_Win_Prob']

        def decide(row):
            sigs = [row.get(f'{c}_sig') for c in ['Overall_Adv','Offense_Adv','Defense_Adv']]
            if 'Blended_Adv_sig' in row.index:
                sigs = [row.get('Blended_Adv_sig')] + sigs
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
        # Sort by strongest edge then blended/overall advantage
        sort_adv = 'Blended_Adv' if 'Blended_Adv' in picks_df.columns else 'Overall_Adv'
        picks_df = picks_df.sort_values(by=['Pick_Edge', sort_adv], ascending=[False, False])
        # Enforce max picks per week
        if len(picks_df) > self.settings.MAX_PICKS_PER_WEEK:
            picks_df = picks_df.head(self.settings.MAX_PICKS_PER_WEEK)
        picks_df['Timestamp'] = datetime.utcnow().isoformat()
        if not picks_df.empty:
            self.pick_repo.save_picks(picks_df, week)
        return picks_df
