from dataclasses import dataclass
from enum import Enum
from typing import Optional

class ResultStatus(str, Enum):
    PENDING = 'PENDING'
    WIN = 'WIN'
    LOSS = 'LOSS'
    PUSH = 'PUSH'
    NA = 'NA'  # Not gradable (e.g., missing line)

@dataclass
class GradedResult:
    status: ResultStatus
    picked_line: Optional[float]  # line relative to picked side (after adjustment if any)
    adjusted_score: Optional[float]


def resolve_line_for_pick(pick_side: str, home_team: str, away_team: str,
                          home_line: Optional[float], away_line: Optional[float]) -> Optional[float]:
    """Return the spread line relative to the picked side.
    Mirrors prior logic: use the line assigned to that team; if absent, invert opponent line if available.
    """
    if pick_side == home_team:
        if home_line is not None:
            return home_line
        if away_line is not None:
            return -away_line
    elif pick_side == away_team:
        if away_line is not None:
            return away_line
        if home_line is not None:
            return -home_line
    return None


def grade_pick(home_team: str, away_team: str, pick_side: str,
               home_score: Optional[int], away_score: Optional[int],
               home_line: Optional[float], away_line: Optional[float],
               line_adjust: float = 0.0) -> GradedResult:
    """Generic grading for straight or teaser picks.
    line_adjust: added (positive) points in favor of the picked side (e.g. 6 for a 6-pt teaser).
    """
    if home_score is None or away_score is None:
        return GradedResult(ResultStatus.PENDING, None, None)
    base_line = resolve_line_for_pick(pick_side, home_team, away_team, home_line, away_line)
    if base_line is None:
        return GradedResult(ResultStatus.NA, None, None)
    picked_score = home_score if pick_side == home_team else away_score
    opp_score = away_score if pick_side == home_team else home_score
    effective_line = base_line + line_adjust
    adjusted = picked_score + effective_line
    if adjusted == opp_score:
        return GradedResult(ResultStatus.PUSH, effective_line, adjusted)
    status = ResultStatus.WIN if adjusted > opp_score else ResultStatus.LOSS
    return GradedResult(status, effective_line, adjusted)


def format_line(line: Optional[float]) -> str:
    if line is None:
        return ''
    if abs(line) < 1e-4:
        return 'PK'
    return f"{line:+g}"


def compute_confidence(overall_adv: Optional[float], max_abs_adv: float) -> str:
    if overall_adv is None or max_abs_adv <= 0:
        return 'N/A'
    pct = (abs(overall_adv) / max_abs_adv) * 100
    return f"{pct:.1f}%"
