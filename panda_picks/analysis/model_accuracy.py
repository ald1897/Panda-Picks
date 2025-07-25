import pandas as pd
import sqlite3
import logging
from panda_picks.db.database import get_connection

def calculate_model_accuracy():
    """
    Calculate the accuracy of prediction models by week and overall.
    Uses SQLite MCP server to access prediction data and results.

    Returns:
        DataFrame: A summary of model accuracy by week and overall
    """
    conn = get_connection()

    try:
        # Fetch picks and results data
        picks_df = pd.read_sql_query("SELECT WEEK, Home_Team, Away_Team, Game_Pick FROM picks", conn)
        results_df = pd.read_sql_query("SELECT WEEK, Home_Team, Away_Team, Winner FROM picks_results", conn)

        # Merge picks with actual results
        merged_df = pd.merge(
            picks_df,
            results_df,
            on=['WEEK', 'Home_Team', 'Away_Team'],
            how='inner'
        )

        # Calculate if prediction was correct
        merged_df['Correct'] = merged_df['Game_Pick'] == merged_df['Winner']

        # Overall accuracy
        overall_accuracy = merged_df['Correct'].mean()

        # Accuracy by week
        weekly_accuracy = merged_df.groupby('WEEK')['Correct'].mean().reset_index()
        weekly_accuracy.columns = ['Week', 'Accuracy']

        # Save results to database
        weekly_accuracy.to_sql('model_accuracy', conn, if_exists='replace', index=False)

        return {
            'overall_accuracy': overall_accuracy,
            'weekly_accuracy': weekly_accuracy
        }

    except Exception as e:
        logging.error(f"Error calculating model accuracy: {e}")
        return None
    finally:
        conn.close()

def get_feature_importance():
    """
    Query the database to find the most important features in the prediction model.
    Uses data stored in the database from ML model training.
    """
    conn = get_connection()

    try:
        # Fetch feature importance if it exists
        features_df = pd.read_sql_query(
            """SELECT feature, importance 
               FROM model_features 
               ORDER BY importance DESC""",
            conn,
            params={}
        )
        return features_df
    except:
        # If table doesn't exist, return placeholder
        return pd.DataFrame({
            'feature': ['Overall_Adv', 'Defense_Adv', 'Offense_Adv'],
            'importance': [0.40, 0.35, 0.25]
        })
    finally:
        conn.close()
