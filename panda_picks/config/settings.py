import os
from pathlib import Path
from typing import Dict, Any

# Early .env load so env vars are available before class attribute evaluation
try:
    from dotenv import load_dotenv  # type: ignore
    _ROOT = Path(__file__).resolve().parent.parent.parent
    load_dotenv(_ROOT / '.env', override=False)
except Exception:
    pass


class Settings:
    """Central application settings.
    Values can be overridden via environment variables where practical.
    """
    # Environment
    ENV: str = os.getenv("PANDA_ENV", "development")
    DEBUG: bool = ENV == "development"

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DATABASE_PATH: Path = BASE_DIR / "database" / "nfl_data.db"

    # Advantage thresholds (can be tuned & updated at runtime)
    ADVANTAGE_THRESHOLDS: Dict[str, float] = {
        "Overall_Adv": float(os.getenv("PP_OVERALL_THRESH", 2.0)),
        "Offense_Adv": float(os.getenv("PP_OFFENSE_THRESH", 2.0)),
        "Defense_Adv": float(os.getenv("PP_DEFENSE_THRESH", 2.0)),
    }

    # Probability scaling
    K_PROB_SCALE: float = float(os.getenv("PP_K_PROB_SCALE", 0.10))

    # Pick filtering / edge metrics
    EDGE_MIN: float = float(os.getenv("PP_EDGE_MIN", -100.0))

    # Margin distribution approximation
    MARGIN_K: float = float(os.getenv("PP_MARGIN_K", 0.75))
    MARGIN_SD: float = float(os.getenv("PP_MARGIN_SD", 13.5))

    # Simulation parameters (legacy; retained for compatibility)
    SIMULATION_SEED: int = int(os.getenv("PP_SIM_SEED", 123))
    SIM_K_MARGIN: float = float(os.getenv("PP_SIM_K_MARGIN", 0.75))
    SIM_BASE_TOTAL: float = float(os.getenv("PP_SIM_BASE_TOTAL", 44))
    SIM_TOTAL_JITTER: float = float(os.getenv("PP_SIM_TOTAL_JITTER", 7))

    # Max picks constraint
    MAX_PICKS_PER_WEEK: int = int(os.getenv("PP_MAX_PICKS_PER_WEEK", 8))

    # Bayesian grade blending flags (phase one)
    USE_BAYES_GRADES: bool = os.getenv("PP_USE_BAYES_GRADES", "false").lower() in ("1","true","yes","on")
    BAYES_K_VALUES: Dict[str, float] = {
        'OVR': float(os.getenv('PP_BAYES_K_OVR', 4)),
        'OFF': float(os.getenv('PP_BAYES_K_OFF', 5)),
        'DEF': float(os.getenv('PP_BAYES_K_DEF', 5)),
        'PASS': float(os.getenv('PP_BAYES_K_PASS', 6)),
        'PBLK': float(os.getenv('PP_BAYES_K_PBLK', 6)),
        'RECV': float(os.getenv('PP_BAYES_K_RECV', 6)),
        'RUN': float(os.getenv('PP_BAYES_K_RUN', 5)),
        'RBLK': float(os.getenv('PP_BAYES_K_RBLK', 6)),
        'PRSH': float(os.getenv('PP_BAYES_K_PRSH', 6)),
        'COV': float(os.getenv('PP_BAYES_K_COV', 7)),
        'RDEF': float(os.getenv('PP_BAYES_K_RDEF', 6)),
        'TACK': float(os.getenv('PP_BAYES_K_TACK', 7)),
    }
    BAYES_MAX_RAMP_WEEK: int = int(os.getenv('PP_BAYES_MAX_RAMP_WEEK', 5))
    BAYES_CAP_WEIGHT_EARLY: float = float(os.getenv('PP_BAYES_CAP_WEIGHT_EARLY', 0.75))
    BAYES_K_SCALE: float = float(os.getenv('PP_BAYES_K_SCALE', 1.0))
    BAYES_CURRENT_WEIGHT_MULTIPLIER: float = float(os.getenv('PP_BAYES_CURRENT_WEIGHT_MULTIPLIER', 1.0))
    # NEW: minimum current season weight floor once at least one completed game exists
    BAYES_MIN_CURRENT_WEIGHT: float = float(os.getenv('PP_BAYES_MIN_CURRENT_WEIGHT', 0.55))

    @classmethod
    def load_from_file(cls, path: Path) -> None:
        """Placeholder for future: load overrides from a file (e.g. JSON/YAML)."""
        pass

    @classmethod
    def update_thresholds(cls, **kwargs: Any) -> None:
        """Update advantage thresholds at runtime (used by tuning logic)."""
        for k, v in kwargs.items():
            if k in cls.ADVANTAGE_THRESHOLDS and v is not None:
                try:
                    cls.ADVANTAGE_THRESHOLDS[k] = float(v)
                except (TypeError, ValueError):
                    continue

    @classmethod
    def refresh_env(cls):
        """Re-read environment-driven dynamic flags mid-process."""
        cls.USE_BAYES_GRADES = os.getenv("PP_USE_BAYES_GRADES", "false").lower() in ("1","true","yes","on")
        for k in [
            ('BAYES_K_SCALE','PP_BAYES_K_SCALE'),
            ('BAYES_CURRENT_WEIGHT_MULTIPLIER','PP_BAYES_CURRENT_WEIGHT_MULTIPLIER'),
            ('BAYES_MIN_CURRENT_WEIGHT','PP_BAYES_MIN_CURRENT_WEIGHT'),
            ('BAYES_CAP_WEIGHT_EARLY','PP_BAYES_CAP_WEIGHT_EARLY'),
            ('BAYES_MAX_RAMP_WEEK','PP_BAYES_MAX_RAMP_WEEK')
        ]:
            try:
                setattr(cls, k[0], type(getattr(cls, k[0]))(os.getenv(k[1], getattr(cls, k[0]))))
            except Exception:
                pass


# Ensure data directory exists (common expectation in code)
Settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATABASE_DIR := Settings.DATABASE_PATH.parent).mkdir(parents=True, exist_ok=True)
