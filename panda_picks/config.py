# panda_picks/config.py
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
GRADES_DIR = DATA_DIR / "grades"
MATCHUPS_DIR = DATA_DIR / "matchups"
PICKS_DIR = DATA_DIR / "picks"

# Database
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_PATH = DATABASE_DIR / "nfl_data.db"

# Ensure directories exist
for directory in [DATA_DIR, GRADES_DIR, MATCHUPS_DIR, PICKS_DIR, DATABASE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# File paths
TEAM_GRADES_CSV = GRADES_DIR / "team_grades.csv"
NFL_TRANSLATIONS_CSV = GRADES_DIR / "nfl_translations.csv"
PFF_TEAM_GRADES_PDF = GRADES_DIR / "pff_team_grades.pdf"