from __future__ import annotations
from typing import Dict, Iterable
import pandas as pd
import os
from panda_picks import config

# Build a normalization map from known abbreviations and aliases to canonical full team names
# Primary source: NFL_translations.csv (Abrev -> TEAM)
_ABBREV_TO_TEAM: Dict[str, str] = {}
try:
    if config.NFL_TRANSLATIONS_CSV.exists():
        df = pd.read_csv(config.NFL_TRANSLATIONS_CSV)
        # Expect columns Abrev, TEAM
        if 'Abrev' in df.columns and 'TEAM' in df.columns:
            for r in df.itertuples(index=False):
                ab = str(getattr(r, 'Abrev')).strip().upper()
                team = str(getattr(r, 'TEAM')).strip()
                if ab:
                    _ABBREV_TO_TEAM[ab] = team
except Exception:
    # Best effort only
    pass

# Common alias corrections across feeds
_ALIAS_TO_TEAM: Dict[str, str] = {
    # Abbrev variants
    'BAL': 'Baltimore Ravens', 'BLT': 'Baltimore Ravens',
    'ARI': 'Arizona Cardinals', 'ARZ': 'Arizona Cardinals',
    'JAC': 'Jacksonville Jaguars', 'JAX': 'Jacksonville Jaguars',
    'LAC': 'Los Angeles Chargers', 'SD': 'Los Angeles Chargers', 'SDG': 'Los Angeles Chargers', 'SDC': 'Los Angeles Chargers', 'SAN DIEGO CHARGERS': 'Los Angeles Chargers', 'LA CHARGERS': 'Los Angeles Chargers',
    'LAR': 'Los Angeles Rams', 'STL': 'Los Angeles Rams', 'ST. LOUIS RAMS': 'Los Angeles Rams', 'LA RAMS': 'Los Angeles Rams',
    'WSH': 'Washington Commanders', 'WAS': 'Washington Commanders', 'WASHINGTON FOOTBALL TEAM': 'Washington Commanders',
    'OAK': 'Las Vegas Raiders', 'OAKLAND RAIDERS': 'Las Vegas Raiders', 'LV': 'Las Vegas Raiders',
    'NO': 'New Orleans Saints', 'NOR': 'New Orleans Saints',
    'NE': 'New England Patriots', 'NWE': 'New England Patriots',
    'SF': 'San Francisco 49ers', 'SFO': 'San Francisco 49ers', 'SAN FRANCISCO 49ERS': 'San Francisco 49ers',
    'TB': 'Tampa Bay Buccaneers', 'TAM': 'Tampa Bay Buccaneers',
    'GB': 'Green Bay Packers', 'GNB': 'Green Bay Packers',
    'KC': 'Kansas City Chiefs', 'KAN': 'Kansas City Chiefs',
    'LA': '',  # ambiguous, leave blank so we don't map incorrectly
}
# Merge CSV map (upper-case keys) into alias map but don't overwrite explicit aliases
for k, v in list(_ABBREV_TO_TEAM.items()):
    _ALIAS_TO_TEAM.setdefault(k.upper(), v)

# Direct name remapping (case-insensitive) for some feeds that use city only
_NAME_CANONICAL: Dict[str, str] = {
    'NEW YORK GIANTS': 'New York Giants',
    'NEW YORK JETS': 'New York Jets',
    'LOS ANGELES CHARGERS': 'Los Angeles Chargers',
    'LOS ANGELES RAMS': 'Los Angeles Rams',
}


def normalize_team(name: str | None) -> str | None:
    """Return canonical full team name from various abbreviations/aliases.
    Preserves None; trims whitespace; case-insensitive.
    """
    if name is None:
        return None
    s = str(name).strip()
    if not s:
        return s
    up = s.upper()
    # If s already looks like a full team name and is in canonical set, return canonical capitalization
    if up in _NAME_CANONICAL:
        return _NAME_CANONICAL[up]
    # Abbrev/alias mapping
    if up in _ALIAS_TO_TEAM:
        mapped = _ALIAS_TO_TEAM[up]
        return mapped or s  # if ambiguous blank, fall back to original
    # If s matches a known TEAM from CSV as-is, keep it
    if s in _ABBREV_TO_TEAM.values():
        return s
    return s


def normalize_df_team_cols(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    """Normalize the specified team columns in-place to canonical names."""
    for c in cols:
        if c in df.columns:
            df[c] = df[c].apply(normalize_team)
    return df

