import pandas as pd
from panda_picks.db.database import get_connection


class SpreadRepository:
    """Data access for spreads table."""

    def get_by_week(self, week: int) -> pd.DataFrame:
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM spreads WHERE WEEK = ?", conn, params=[f"WEEK{week}"])

    def get_all(self) -> pd.DataFrame:
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM spreads", conn)

