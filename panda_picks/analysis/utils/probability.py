import math
import numpy as np
from panda_picks.config.settings import Settings


def calculate_win_probability(advantage: float) -> float:
    """Logistic transformation mapping advantage to win probability."""
    try:
        x = float(advantage)
    except (TypeError, ValueError):
        return 0.5
    return 1.0 / (1 + math.exp(-Settings.K_PROB_SCALE * x))


def simulate_score(advantage: float, rng: np.random.Generator | None = None) -> tuple[int, int]:
    """Simulate a plausible (home_points, away_points) pair given an advantage.

    Uses a simple margin model with configurable jitter and total scoring baseline.
    """
    if rng is None:
        rng = np.random.default_rng(Settings.SIMULATION_SEED)
    try:
        adv = float(advantage)
    except (TypeError, ValueError):
        adv = 0.0
    exp_margin = Settings.SIM_K_MARGIN * adv
    total = Settings.SIM_BASE_TOTAL + rng.uniform(-Settings.SIM_TOTAL_JITTER, Settings.SIM_TOTAL_JITTER)
    margin = rng.normal(exp_margin, 7)
    home_pts = (total + margin) / 2
    away_pts = total - home_pts
    return int(max(0, round(home_pts))), int(max(0, round(away_pts)))

