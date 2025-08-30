from dataclasses import dataclass
from typing import Optional


@dataclass
class Team:
    name: str
    overall: float
    offense: float
    defense: float
    pass_offense: float
    run_offense: float
    receiving: Optional[float] = None
    pass_block: Optional[float] = None
    run_block: Optional[float] = None
    pass_rush: Optional[float] = None
    coverage: Optional[float] = None
    run_defense: Optional[float] = None
    tackling: Optional[float] = None

