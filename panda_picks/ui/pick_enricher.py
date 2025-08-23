from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Optional, Sequence, Tuple, Dict, Any
from .grade_utils import grade_pick, resolve_line_for_pick, format_line, compute_confidence, ResultStatus

# Repository row type aliases (mirroring pick_results_repository)
UpcomingJoinRow = Tuple[str, str, str, str, Optional[float], Optional[int], Optional[int], Optional[float], Optional[float]]
ScoredBasicRow = Tuple[str, str, str, str, int, int, Optional[float], Optional[float]]

@dataclass
class EnrichedPick:
    week: str
    home_team: str
    away_team: str
    pick_side: str
    base_line: Optional[float]
    spread_home: Optional[float]
    home_score: Optional[int]
    away_score: Optional[int]
    confidence: str
    straight_status: str
    teaser_pick: str
    teaser_status: str
    predicted_pick: str  # pick + line string

    def to_row_dict(self) -> Dict[str, Any]:
        return {
            'Row_ID': f"{self.week}-{self.home_team}-{self.away_team}",
            'Week': self.week,
            'Home_Team': self.home_team,
            'Away_Team': self.away_team,
            'Spread': format_line(self.spread_home),
            'Predicted_Pick': self.predicted_pick,
            'Teaser_Pick': self.teaser_pick,
            'Teaser_Result': self.teaser_status,
            'Confidence_Score': self.confidence,
            'Home_Score': '' if self.home_score is None else self.home_score,
            'Away_Score': '' if self.away_score is None else self.away_score,
            'Result': self.straight_status,
        }

class PickEnricher:
    """Centralized enrichment / grading for picks and results.

    Responsibilities:
      - Confidence normalization (per batch)
      - Straight & teaser grading via grade_pick
      - Formatting of pick with line & teaser pick
      - Returning consistent EnrichedPick objects
    """

    def enrich_upcoming(self, rows: Sequence[UpcomingJoinRow]) -> List[EnrichedPick]:
        if not rows:
            return []
        # Compute max abs advantage for confidence normalization (index 4)
        max_adv = max((abs(r[4]) for r in rows if r[4] is not None), default=1) or 1
        enriched: List[EnrichedPick] = []
        for (week, home, away, pick, overall_adv, home_score, away_score, home_line, away_line) in rows:
            confidence_pct = compute_confidence(overall_adv, max_adv)
            base_line = resolve_line_for_pick(pick, home, away, home_line, away_line)
            spread_home = home_line if home_line is not None else (-away_line if away_line is not None else None)
            # Straight result
            straight_res = grade_pick(home, away, pick, home_score, away_score, home_line, away_line)
            # Teaser result (only if base line exists)
            if base_line is not None:
                teaser_res = grade_pick(home, away, pick, home_score, away_score, home_line, away_line, line_adjust=6)
                teaser_line = base_line + 6
                teaser_pick = f"{pick} {format_line(teaser_line)}"
                teaser_status = teaser_res.status.value
            else:
                teaser_pick = pick
                teaser_status = ResultStatus.PENDING.value if (home_score is None or away_score is None) else ResultStatus.NA.value
            predicted_pick = f"{pick} {format_line(base_line)}" if base_line is not None else pick
            if (home_score is None or away_score is None) and straight_res.status == ResultStatus.PENDING:
                straight_status = ResultStatus.PENDING.value
            else:
                straight_status = straight_res.status.value
            enriched.append(EnrichedPick(
                week=week,
                home_team=home,
                away_team=away,
                pick_side=pick,
                base_line=base_line,
                spread_home=spread_home,
                home_score=home_score,
                away_score=away_score,
                confidence=confidence_pct,
                straight_status=straight_status,
                teaser_pick=teaser_pick,
                teaser_status=teaser_status,
                predicted_pick=predicted_pick,
            ))
        return enriched

    def enrich_scored(self, rows: Sequence[ScoredBasicRow]) -> List[EnrichedPick]:
        if not rows:
            return []
        # For scored rows, confidence not available by default; set to 'N/A'
        enriched: List[EnrichedPick] = []
        for (week, home, away, pick, home_score, away_score, home_line, away_line) in rows:
            base_line = resolve_line_for_pick(pick, home, away, home_line, away_line)
            straight_res = grade_pick(home, away, pick, home_score, away_score, home_line, away_line)
            predicted_pick = f"{pick} {format_line(base_line)}" if base_line is not None else pick
            # Teaser outcome (if base line exists)
            if base_line is not None:
                teaser_res = grade_pick(home, away, pick, home_score, away_score, home_line, away_line, line_adjust=6)
                teaser_line = base_line + 6
                teaser_pick = f"{pick} {format_line(teaser_line)}"
                teaser_status = teaser_res.status.value
            else:
                teaser_pick = pick
                teaser_status = ResultStatus.NA.value
            straight_status = straight_res.status.value
            enriched.append(EnrichedPick(
                week=week,
                home_team=home,
                away_team=away,
                pick_side=pick,
                base_line=base_line,
                spread_home=home_line if home_line is not None else (-away_line if away_line is not None else None),
                home_score=home_score,
                away_score=away_score,
                confidence='N/A',
                straight_status=straight_status,
                teaser_pick=teaser_pick,
                teaser_status=teaser_status,
                predicted_pick=predicted_pick,
            ))
        return enriched

