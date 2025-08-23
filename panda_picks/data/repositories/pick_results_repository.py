from typing import List, Tuple, Optional
from panda_picks.db.database import get_connection

# Type aliases for clarity
BasicScoredRow = Tuple[str, str, str, str, int, int, Optional[float], Optional[float]]
ExtendedScoredRow = Tuple[str, str, str, str, int, int, Optional[float], Optional[float], Optional[int], Optional[int]]
UpcomingJoinRow = Tuple[str, str, str, str, Optional[float], Optional[int], Optional[int], Optional[float], Optional[float]]

class PickResultsRepository:
    """Repository abstraction around picks_results (and joins with picks) to reduce duplicated SQL."""

    def get_scored_basic(self) -> List[BasicScoredRow]:
        """All scored rows (scores not NULL) with core columns used for grading/metrics."""
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("""
                SELECT WEEK, Home_Team, Away_Team, Game_Pick, Home_Score, Away_Score, Home_Line_Close, Away_Line_Close
                FROM picks_results
                WHERE Home_Score IS NOT NULL AND Away_Score IS NOT NULL
            """)
            rows = cur.fetchall(); conn.close(); return rows
        except Exception:
            return []

    def get_scored_extended(self) -> List[ExtendedScoredRow]:
        """Scored rows including Pick_Covered_Spread and Correct_Pick flags."""
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("""
                SELECT WEEK, Home_Team, Away_Team, Game_Pick, Home_Score, Away_Score,
                       Home_Line_Close, Away_Line_Close, Pick_Covered_Spread, Correct_Pick
                FROM picks_results
                WHERE Home_Score IS NOT NULL AND Away_Score IS NOT NULL
            """)
            rows = cur.fetchall(); conn.close(); return rows
        except Exception:
            return []

    def get_recent(self, limit: int = 30) -> List[BasicScoredRow]:
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute(f"""
                SELECT WEEK, Home_Team, Away_Team, Game_Pick, Home_Score, Away_Score, Home_Line_Close, Away_Line_Close
                FROM picks_results
                ORDER BY CAST(REPLACE(UPPER(WEEK),'WEEK','') AS INTEGER), Home_Team, Away_Team
                LIMIT {int(limit)}
            """)
            rows = cur.fetchall(); conn.close(); return rows
        except Exception:
            return []

    def get_upcoming_join(self) -> List[UpcomingJoinRow]:
        """Join picks with any existing scored rows and optionally spreads to surface best-available closing lines.
        Updated priority: spreads (latest) > picks_results (historical) > picks (stored).
        Falls back gracefully if spreads table not present.
        """
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='spreads' LIMIT 1")
            has_spreads = cur.fetchone() is not None
            if has_spreads:
                cur.execute("""
                    SELECT p.WEEK, p.Home_Team, p.Away_Team, p.Game_Pick, p.Overall_Adv,
                           pr.Home_Score, pr.Away_Score,
                           COALESCE(s.Home_Line_Close, pr.Home_Line_Close, p.Home_Line_Close) AS Home_Line_Close,
                           COALESCE(s.Away_Line_Close, pr.Away_Line_Close, p.Away_Line_Close) AS Away_Line_Close
                    FROM picks p
                    LEFT JOIN picks_results pr
                      ON pr.WEEK = p.WEEK AND pr.Home_Team = p.Home_Team AND pr.Away_Team = p.Away_Team
                    LEFT JOIN spreads s
                      ON s.WEEK = p.WEEK AND s.Home_Team = p.Home_Team AND s.Away_Team = p.Away_Team
                """)
            else:
                cur.execute("""
                    SELECT p.WEEK, p.Home_Team, p.Away_Team, p.Game_Pick, p.Overall_Adv,
                           pr.Home_Score, pr.Away_Score,
                           COALESCE(pr.Home_Line_Close, p.Home_Line_Close) AS Home_Line_Close,
                           COALESCE(pr.Away_Line_Close, p.Away_Line_Close) AS Away_Line_Close
                    FROM picks p
                    LEFT JOIN picks_results pr
                      ON pr.WEEK = p.WEEK AND pr.Home_Team = p.Home_Team AND pr.Away_Team = p.Away_Team
                """)
            rows = cur.fetchall(); conn.close(); return rows
        except Exception:
            try: conn.close()
            except Exception: pass
            return []

    def get_scored_for_fallback_join(self) -> List[BasicScoredRow]:
        """Original fallback join used when picks_results may be empty (legacy support)."""
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("""
                SELECT TRIM(p.WEEK) as WK,
                       p.Home_Team, p.Away_Team, p.Game_Pick,
                       s.Home_Score, s.Away_Score, s.Home_Line_Close, s.Away_Line_Close
                FROM picks p
                JOIN spreads s ON TRIM(p.WEEK)=TRIM(s.WEEK) AND p.Home_Team=s.Home_Team AND p.Away_Team=s.Away_Team
                WHERE s.Home_Score IS NOT NULL AND s.Away_Score IS NOT NULL
            """)
            rows = cur.fetchall(); conn.close(); return rows
        except Exception:
            return []
