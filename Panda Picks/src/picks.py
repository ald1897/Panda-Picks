import pandas as pd
import numpy as np
import sqlite3
import scipy.stats as stats
import logging

def makePicks():
    logging.basicConfig(level=logging.DEBUG)
    weeks = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18']
    # weeks = ['9', '10', '11', '12', '13', '14', '15', '16', '17', '18']
    # Connect to SQLite database
    conn = sqlite3.connect('nfl_data.db')
    cursor = conn.cursor()

    try:
        for w in weeks:
            pd.set_option("display.precision", 2)
            pd.options.display.float_format = '{:10,.2f}'.format

            # Query the grades table from the database
            grades = pd.read_sql_query("SELECT * FROM grades", conn)
            grades = grades.rename(columns={'TEAM': 'Home_Team'})
            logging.debug(f"Week {w}: Grades data fetched successfully")
            logging.debug(f"Week {w} Data: {grades}")

            # Query the advanced stats tables from the database
            off_adv_stats = pd.read_sql_query("SELECT * FROM advanced_stats WHERE season = 2024 AND type = 'offense'", conn)
            def_adv_stats = pd.read_sql_query("SELECT * FROM advanced_stats WHERE season = 2024 AND type = 'defense'", conn)

            off_adv_stats = off_adv_stats.rename(columns={
                'TEAM': 'Home_Team',
                'composite_score': 'OFF_COMPOSITE',
            })

            def_adv_stats = def_adv_stats.rename(columns={
                'TEAM': 'Home_Team',
                'composite_score': 'DEF_COMPOSITE',
            })

            off_std = off_adv_stats['OFF_COMPOSITE'].std()
            def_std = def_adv_stats['DEF_COMPOSITE'].std()
            std = (off_std + def_std) / 2

            off_adv_stats = off_adv_stats[['Home_Team', 'OFF_COMPOSITE']]
            def_adv_stats = def_adv_stats[['Home_Team', 'DEF_COMPOSITE']]

            grades = pd.merge(grades, off_adv_stats, on="Home_Team")
            grades = pd.merge(grades, def_adv_stats, on="Home_Team")

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
                'TACK': 'OPP_TACK',
                'DEF_COMPOSITE': 'AWAY_DEF_COMPOSITE',
                'OFF_COMPOSITE': 'AWAY_OFF_COMPOSITE'
            })

            # Query the matchups table from the database
            matchups = pd.read_sql_query(f"SELECT * FROM spreads WHERE Week = 'WEEK{w}'", conn)
            matchups = matchups.dropna(axis=0, how='all')
            matchups = pd.merge(matchups, grades, on="Home_Team")
            matchups = pd.merge(matchups, opp_grades, on="Away_Team")

            # Convert columns except for the home and away team cols in matchups to numeric types, do it in a loop
            for col in matchups.columns:
                if col not in ['Home_Team', 'Away_Team', 'WEEK']:
                    matchups[col] = pd.to_numeric(matchups[col], errors='coerce')


            results = matchups.copy()
            # print(results.columns)
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
            results['Off_Comp_Adv'] = results['OFF_COMPOSITE'] - results['AWAY_DEF_COMPOSITE']
            results['Def_Comp_Adv'] = results['DEF_COMPOSITE'] - results['AWAY_OFF_COMPOSITE']

            advantage_columns = [
                'Overall_Adv', 'Offense_Adv', 'Defense_Adv'
            ]

            for col in advantage_columns:
                results[f'{col}_sig'] = np.where(results[col] > 0, 'home significant', np.where(
                    results[col] < 0, 'away significant', 'insignificant'))

            composite_columns = [
                'Off_Comp_Adv', 'Def_Comp_Adv'
            ]

            for col in composite_columns:
                results[f'{col}_sig'] = np.where(results[col] > std/3, 'home significant', np.where(
                    results[col] < -(std/3), 'away significant', 'insignificant'))

            results['Game_Pick'] = (
                np.where(
                    (results[[f'{col}_sig' for col in advantage_columns]].eq('home significant').all(axis=1) | results[[f'{col}_sig' for col in advantage_columns]].eq('insignificant').all(axis=1)) &
                    (results[[f'{col}_sig' for col in composite_columns]].eq('home significant').all(axis=1) | results[[f'{col}_sig' for col in composite_columns]].eq('insignificant').all(axis=1)),
                results['Home_Team'],
                np.where(
                    (results[[f'{col}_sig' for col in advantage_columns]].eq('away significant').all(axis=1) | results[[f'{col}_sig' for col in advantage_columns]].eq('insignificant').all(axis=1)) &
                    (results[[f'{col}_sig' for col in composite_columns]].eq('away significant').all(axis=1) | results[[f'{col}_sig' for col in composite_columns]].eq('insignificant').all(axis=1)),
                results['Away_Team'], 'No Pick')))

            results = results.sort_values(by=['Overall_Adv'], ascending=False)
            results = results[results['Game_Pick'] != 'No Pick']
            # print(results)
            # print(results.columns)
            results = results[['WEEK', 'Home_Team', 'Away_Team', 'Home_Line_Close', 'Away_Line_Close', 'Game_Pick', 'Overall_Adv', 'Offense_Adv', 'Defense_Adv', 'Off_Comp_Adv', 'Def_Comp_Adv', 'Off_Comp_Adv_sig', 'Def_Comp_Adv_sig', 'Overall_Adv_sig', 'Offense_Adv_sig', 'Defense_Adv_sig']]

            # Insert data into the SQLite database, append if the table already exists
            results.to_sql('picks', conn, if_exists='append', index=False)
            logging.debug(f"Week {w}: Data inserted successfully")

    except Exception as e:
        logging.error(f"Week {w}: Error occurred - {e}")

    # Commit and close the connection
    conn.commit()
    conn.close()

if __name__ == '__main__':
    makePicks()