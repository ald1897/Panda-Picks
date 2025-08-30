from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from .team import Team


@dataclass
class Matchup:
    week: int
    home_team: Team
    away_team: Team
    spread: Optional[float] = None
    total: Optional[float] = None
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None


@dataclass
class Advantage:
    overall_advantage: float
    offense_advantage: float
    defense_advantage: float


@dataclass
class Prediction:
    matchup: Matchup
    advantages: Advantage
    pick: str  # 'home', 'away', or 'PASS'
    confidence: float
    expected_value: Optional[float]
    home_win_probability: float
    timestamp: datetime

