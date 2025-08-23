import os
from pathlib import Path
from typing import Dict, Any


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
    EDGE_MIN: float = float(os.getenv("PP_EDGE_MIN", 0.035))

    # Margin distribution approximation
    MARGIN_K: float = float(os.getenv("PP_MARGIN_K", 0.75))
    MARGIN_SD: float = float(os.getenv("PP_MARGIN_SD", 13.5))

    # Simulation parameters
    SIMULATION_SEED: int = int(os.getenv("PP_SIM_SEED", 123))
    SIM_K_MARGIN: float = float(os.getenv("PP_SIM_K_MARGIN", 0.75))
    SIM_BASE_TOTAL: float = float(os.getenv("PP_SIM_BASE_TOTAL", 44))
    SIM_TOTAL_JITTER: float = float(os.getenv("PP_SIM_TOTAL_JITTER", 7))

    # Max picks constraint (default raised from 4 -> 5)
    MAX_PICKS_PER_WEEK: int = int(os.getenv("PP_MAX_PICKS_PER_WEEK", 5))

    @classmethod
    def load_from_file(cls, path: Path) -> None:
        """Placeholder for future: load overrides from a file (e.g. JSON/YAML)."""
        # Not yet implemented; stub for future expansion.
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


# Ensure data directory exists (common expectation in code)
Settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATABASE_DIR := Settings.DATABASE_PATH.parent).mkdir(parents=True, exist_ok=True)
