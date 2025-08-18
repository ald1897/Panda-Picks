import pandas as pd
from panda_picks.db.database import get_connection


class GradeRepository:
    """Data access for grades table."""

    def get_all(self) -> pd.DataFrame:
        with get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM grades", conn)
        # Normalize column for joins
        if 'TEAM' in df.columns:
            df = df.rename(columns={'TEAM': 'Home_Team'})
        elif 'Team' in df.columns:
            df = df.rename(columns={'Team': 'Home_Team'})
        return df

    def get_all_grades(self) -> pd.DataFrame:
        return self.get_all()

