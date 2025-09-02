import logging
from typing import List
from panda_picks.db.database import get_connection

class ExcludedTeamsRepository:
    """Persist and retrieve manually excluded teams per week for combos UI.

    Schema (lazy): excluded_teams(WEEK TEXT, Team TEXT, PRIMARY KEY (WEEK, Team))
    """

    def _ensure_table(self, conn):
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS excluded_teams (
                WEEK TEXT,
                Team TEXT,
                PRIMARY KEY (WEEK, Team)
            )
            """
        )
        conn.commit()

    def get_exclusions(self, week: str) -> List[str]:
        try:
            with get_connection() as conn:
                self._ensure_table(conn)
                cur = conn.cursor()
                cur.execute("SELECT Team FROM excluded_teams WHERE WEEK = ? ORDER BY Team", (week,))
                return [r[0] for r in cur.fetchall()]
        except Exception as e:
            logging.warning(f"Failed to fetch exclusions for {week}: {e}")
            return []

    def set_exclusions(self, week: str, teams: List[str]):
        try:
            uniq = sorted({t for t in teams if t})
            with get_connection() as conn:
                self._ensure_table(conn)
                cur = conn.cursor()
                cur.execute("DELETE FROM excluded_teams WHERE WEEK = ?", (week,))
                if uniq:
                    cur.executemany("INSERT INTO excluded_teams (WEEK, Team) VALUES (?, ?)", [(week, t) for t in uniq])
                conn.commit()
        except Exception as e:
            logging.error(f"Failed to set exclusions for {week}: {e}")

