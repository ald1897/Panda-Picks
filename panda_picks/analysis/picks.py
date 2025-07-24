import pandas as pd
import numpy as np
import sqlite3
import logging
import time

from panda_picks.db.database import get_connection
from panda_picks import config

def makePicks():
    print(f"[{time.strftime('%H:%M:%S')}] makePicks started")
    logging.basicConfig(level=logging.DEBUG)
    weeks = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18']
    # weeks = ['9', '10', '11', '12', '13', '14', '15', '16', '17', '18']
    # Connect to SQLite database
    conn = get_connection()

    try:
        for w in weeks:
            # print(f"[{time.strftime('%H:%M:%S')}] Processing week {w}")
            pd.set_option("display.precision", 2)
            pd.options.display.float_format = '{:10,.2f}'.format

            # Query the grades table from the database
            grades = pd.read_sql_query("SELECT * FROM grades", conn)
            grades = grades.rename(columns={'TEAM': 'Home_Team'})
            logging.debug(f"Week {w}: Grades data fetched successfully")
            logging.debug(f"Week {w} Data: {grades}")

            opp_grades = grades.copy()
            opp_grades = opp_grades.rename(columns={
                'Home_Team': 'Away_Team',
                'OVR': 'OPP_OVR',
                'OFF': 'OPP_OFF',
                'DEF': 'OPP_DEF',
                'PASS': 'OPP_PASS',
                'PBLK': 'OPP_PBLK',
                'RECV': 'OPP_RECV',
                'RUN': 'OPP_RUN',
                'RBLK': 'OPP_RBLK',
                'PRSH': 'OPP_PRSH',
                'COV': 'OPP_COV',
                'RDEF': 'OPP_RDEF',
                'TACK': 'OPP_TACK'
            })

            # Query the matchups table from the database
            matchups = pd.read_sql_query(f"SELECT * FROM spreads WHERE Week = 'WEEK{w}'", conn)
            matchups = matchups.dropna(axis=0, how='all')
            matchups = pd.merge(matchups, grades, on="Home_Team")
            matchups = pd.merge(matchups, opp_grades, on="Away_Team")

            # Convert columns except for the home and away team cols in matchups to numeric types
            for col in matchups.columns:
                if col not in ['Home_Team', 'Away_Team', 'WEEK']:
                    matchups[col] = pd.to_numeric(matchups[col], errors='coerce')

            results = matchups.copy()
            # Calculate advantages based on PFF grades only
            results['Overall_Adv'] = results['OVR'] - results['OPP_OVR']
            results['Offense_Adv'] = results['OFF'] - results['OPP_DEF']
            results['Defense_Adv'] = results['DEF'] - results['OPP_OFF']
            results['Passing_Adv'] = results['PASS'] - results['OPP_COV']
            results['Pass_Block_Adv'] = results['PBLK'] - results['OPP_PRSH']
            results['Receving_Adv'] = results['RECV'] - results['OPP_COV']
            results['Running_Adv'] = results['RUN'] - results['OPP_RDEF']
            results['Run_Block_Adv'] = results['RBLK'] - results['OPP_RDEF']
            results['Run_Defense_Adv'] = results['RDEF'] - results['OPP_RUN']
            results['Pass_Rush_Adv'] = results['PRSH'] - ((results['OPP_PBLK'] + results['OPP_PASS']) / 2)
            results['Coverage_Adv'] = results['COV'] - ((results['OPP_RECV'] + results['OPP_PBLK']) / 2)
            results['Tackling_Adv'] = results['TACK'] - results['OPP_RUN']

            advantage_columns = [
                'Overall_Adv', 'Offense_Adv', 'Defense_Adv'
            ]

            # print(results.head(1))

            for col in advantage_columns:
                results[f'{col}_sig'] = np.where(results[col] > 0, 'home significant', np.where(
                    results[col] < 0, 'away significant', 'insignificant'))

            # Simplified pick logic based only on grade advantages
            results['Game_Pick'] = np.where(
                results[[f'{col}_sig' for col in advantage_columns]].eq('home significant').all(axis=1) |
                results[[f'{col}_sig' for col in advantage_columns]].eq('insignificant').all(axis=1),
                results['Home_Team'],
                np.where(
                    results[[f'{col}_sig' for col in advantage_columns]].eq('away significant').all(axis=1) |
                    results[[f'{col}_sig' for col in advantage_columns]].eq('insignificant').all(axis=1),
                    results['Away_Team'], 'No Pick'))

            results = results.sort_values(by=['Overall_Adv'], ascending=False)
            results = results[results['Game_Pick'] != 'No Pick']

            # Select only relevant columns
            results = results[['WEEK', 'Home_Team', 'Away_Team', 'Home_Line_Close', 'Away_Line_Close',
                               'Game_Pick', 'Overall_Adv', 'Offense_Adv', 'Defense_Adv',
                               'Overall_Adv_sig', 'Offense_Adv_sig', 'Defense_Adv_sig']]

            # Insert data into the SQLite database, append if the table already exists
            results.to_sql('picks', conn, if_exists='append', index=False)
            logging.debug(f"Week {w}: Data inserted successfully")
            # print(f"[{time.strftime('%H:%M:%S')}] Week {w} processed")
    except Exception as e:
        logging.error(f"Week {w}: Error occurred - {e}")

    # Commit and close the connection
    conn.commit()
    conn.close()
    print(f"[{time.strftime('%H:%M:%S')}] makePicks finished")

def generate_week_picks(week):
    """Generate picks for a specific week

    Args:
        week (int): The week number to generate picks for

    Returns:
        pandas.DataFrame: DataFrame containing the picks for the week
    """
    # Configure logging to use a file handler instead of printing to stdout
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Convert week to string if it's an int
    week_str = str(week)

    # Connect to SQLite database
    conn = get_connection()

    pd.set_option("display.precision", 2)
    pd.options.display.float_format = '{:10,.2f}'.format

    # Query the grades table from the database
    grades = pd.read_sql_query("SELECT * FROM grades", conn)
    grades = grades.rename(columns={'Team': 'Home_Team'})

    opp_grades = grades.copy()
    opp_grades = opp_grades.rename(columns={'Home_Team': 'Away_Team'})

    # Query the matchups for the specified week
    matchups_query = f"SELECT * FROM spreads WHERE Week = '{week_str}'"
    try:
        matchups = pd.read_sql_query(matchups_query, conn)
    except Exception as e:
        logger.error(f"Error querying matchups for week {week_str}: {e}")
        # Fallback to reading from CSV
        try:
            matchups = pd.read_csv(f"{config.DATA_DIR}/matchups/matchups_WEEK{week_str}.csv")
            logger.info(f"Successfully loaded matchups from CSV for week {week_str}")
        except Exception as csv_e:
            logger.error(f"Error reading matchups CSV for week {week_str}: {csv_e}")
            return pd.DataFrame()  # Return empty DataFrame if no data available

    # Skip if no matchups found
    if matchups.empty:
        logger.warning(f"No matchups found for week {week_str}")
        return pd.DataFrame()

    # Merge grades with matchups
    merged = pd.merge(matchups, grades, on='Home_Team', how='left')
    merged = pd.merge(merged, opp_grades, left_on='Away_Team', right_on='Away_Team', how='left',
                      suffixes=('_Home', '_Away'))

    # Calculate advantage values
    merged['Overall_Advantage'] = merged['Overall_Grade_Home'] - merged['Overall_Grade_Away']
    merged['Off_Advantage'] = merged['Off_Grade_Home'] - merged['Off_Grade_Away']
    merged['Def_Advantage'] = merged['Def_Grade_Home'] - merged['Def_Grade_Away']

    # Calculate score prediction
    merged['Predicted_Home_Score'] = 24 + round(merged['Overall_Advantage'] / 2)
    merged['Predicted_Away_Score'] = 24 - round(merged['Overall_Advantage'] / 2)
    merged['Predicted_Point_Diff'] = merged['Predicted_Home_Score'] - merged['Predicted_Away_Score']

    # Calculate spread coverage
    if 'Spread' in merged.columns:
        merged['Pick_Covers_Spread'] = merged.apply(
            lambda row: row['Home_Team'] if row['Predicted_Point_Diff'] > row['Spread'] else row['Away_Team'],
            axis=1
        )
    else:
        # Default to home team if no spread available
        merged['Pick_Covers_Spread'] = merged['Home_Team']

    # Add confidence calculation
    merged['Confidence'] = merged['Overall_Advantage'].abs() / 10
    merged['Confidence'] = merged['Confidence'].apply(lambda x: min(round(x, 2), 0.9))

    # Select relevant columns for output
    picks_df = merged[[
        'Week', 'Home_Team', 'Away_Team',
        'Overall_Grade_Home', 'Overall_Grade_Away', 'Overall_Advantage',
        'Predicted_Home_Score', 'Predicted_Away_Score', 'Predicted_Point_Diff',
        'Pick_Covers_Spread', 'Confidence'
    ]]

    # Save to CSV (optional) - using logger instead of print
    output_path = f"{config.DATA_DIR}/picks/WEEK{week_str}.csv"
    picks_df.to_csv(output_path, index=False)
    logger.info(f"Picks saved to {output_path}")

    return picks_df

if __name__ == '__main__':
    makePicks()