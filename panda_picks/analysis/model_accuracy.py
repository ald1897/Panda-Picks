"""DEPRECATED: Logic moved to analysis.services.metrics_service.
This stub remains temporarily for backward compatibility.
Will be removed in a future cleanup release.
"""
from __future__ import annotations
from typing import Optional, Dict, Any
import pandas as pd
from panda_picks.db.database import get_connection


def calculate_model_accuracy() -> Optional[Dict[str, Any]]:
    try:
        conn = get_connection()
        picks_df = pd.read_sql_query("SELECT WEEK, Home_Team, Away_Team, Game_Pick FROM picks", conn)
        results_df = pd.read_sql_query("SELECT WEEK, Home_Team, Away_Team, Winner FROM picks_results", conn)
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass
    merged = picks_df.merge(results_df, on=['WEEK','Home_Team','Away_Team'], how='inner')
    if merged.empty:
        return {"overall_accuracy": None, "weekly_accuracy": pd.DataFrame(columns=['Week','Accuracy'])}
    merged['Correct'] = merged['Game_Pick'] == merged['Winner']
    overall = merged['Correct'].mean()
    weekly = merged.groupby('WEEK')['Correct'].mean().reset_index().rename(columns={'WEEK':'Week','Correct':'Accuracy'})
    return {"overall_accuracy": overall, "weekly_accuracy": weekly}
