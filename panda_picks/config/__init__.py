from pathlib import Path
from .settings import Settings

# Backward-compatible constants originally defined in module config.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
GRADES_DIR = DATA_DIR / "grades"
MATCHUPS_DIR = DATA_DIR / "matchups"
PICKS_DIR = DATA_DIR / "picks"
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_PATH = DATABASE_DIR / "nfl_data.db"

# New: specific resource file paths migrated from legacy_config
TEAM_GRADES_CSV = GRADES_DIR / "team_grades.csv"
NFL_TRANSLATIONS_CSV = GRADES_DIR / "NFL_translations.csv"
PFF_TEAM_GRADES_PDF = GRADES_DIR / "pff_team_grades.pdf"

# Ensure directories exist
for directory in [DATA_DIR, GRADES_DIR, MATCHUPS_DIR, PICKS_DIR, DATABASE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Re-export Settings for convenience
__all__ = [
    "Settings",
    "PROJECT_ROOT",
    "DATA_DIR",
    "GRADES_DIR",
    "MATCHUPS_DIR",
    "PICKS_DIR",
    "DATABASE_DIR",
    "DATABASE_PATH",
    "TEAM_GRADES_CSV",
    "NFL_TRANSLATIONS_CSV",
    "PFF_TEAM_GRADES_PDF",
]
