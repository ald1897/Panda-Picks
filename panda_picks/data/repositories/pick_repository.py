import pandas as pd
from panda_picks.db.database import get_connection
import logging


class PickRepository:
    """Data access for picks table."""

    _EXTRA_COL_TYPES = {
        'Home_Win_Prob': 'REAL', 'Away_Win_Prob': 'REAL',
        'Home_ML_Implied': 'REAL', 'Away_ML_Implied': 'REAL',
        'Pick_Prob': 'REAL', 'Pick_Implied_Prob': 'REAL', 'Pick_Edge': 'REAL',
        'Timestamp': 'TEXT'
    }

    def _ensure_columns(self, conn):
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(picks)")
        existing = {row[1] for row in cur.fetchall()}
        for col, col_type in self._EXTRA_COL_TYPES.items():
            if col not in existing:
                try:
                    cur.execute(f"ALTER TABLE picks ADD COLUMN {col} {col_type}")
                except Exception as e:
                    logging.warning(f"Could not add column {col} to picks: {e}")
        conn.commit()

    def save_picks(self, picks_df: pd.DataFrame, week: int) -> None:
        if picks_df.empty:
            return
        week_key = f"WEEK{week}"
        with get_connection() as conn:
            self._ensure_columns(conn)
            cur = conn.cursor()
            # Limit to existing columns in picks table (avoid Home_Score, Away_Score etc.)
            cur.execute("PRAGMA table_info(picks)")
            existing_cols = [row[1] for row in cur.fetchall()]
            filtered_df = picks_df[[c for c in picks_df.columns if c in existing_cols]].copy()
            if 'WEEK' in filtered_df.columns:
                # ensure correct WEEK formatting
                filtered_df['WEEK'] = filtered_df['WEEK'].apply(lambda _: week_key)
            else:
                filtered_df['WEEK'] = week_key
            for home, away in zip(filtered_df['Home_Team'], filtered_df['Away_Team']):
                cur.execute("DELETE FROM picks WHERE WEEK = ? AND Home_Team = ? AND Away_Team = ?", (week_key, home, away))
            filtered_df.to_sql('picks', conn, if_exists='append', index=False)

    def get_week_picks(self, week: int) -> pd.DataFrame:
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM picks WHERE WEEK = ?", conn, params=[f"WEEK{week}"])
