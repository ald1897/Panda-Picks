import pandas as pd
from panda_picks.db.database import get_connection


class PickRepository:
    """Data access for picks table."""

    def save_picks(self, picks_df: pd.DataFrame, week: int) -> None:
        if picks_df.empty:
            return
        week_key = f"WEEK{week}"
        with get_connection() as conn:
            cur = conn.cursor()
            for home, away in zip(picks_df['Home_Team'], picks_df['Away_Team']):
                cur.execute("DELETE FROM picks WHERE WEEK = ? AND Home_Team = ? AND Away_Team = ?", (week_key, home, away))
            picks_df.to_sql('picks', conn, if_exists='append', index=False)

    def get_week_picks(self, week: int) -> pd.DataFrame:
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM picks WHERE WEEK = ?", conn, params=[f"WEEK{week}"])

