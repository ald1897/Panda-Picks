import pandas as pd
import numpy as np
import scipy.stats as stats


def makePicks():
    weeks = ['9', '10', '11', '12', '13', '14', '15', '16', '17', '18']

    for w in weeks:
        pd.set_option("display.precision", 2)
        pd.options.display.float_format = '{:10,.2f}'.format

        grades = pd.read_csv("../Data/Grades/TeamGrades.csv")
        grades = grades.rename(columns={'TEAM': 'Home Team'})

        matchups = pd.read_csv(f"../Data/Matchups/matchups_WEEK{w}.csv")
        matchups = matchups.dropna(axis=0, how='all')
        matchups = pd.merge(matchups, grades, on="Home Team")

        grades = grades.rename(columns={
            'Home Team': 'Away Team',
            'OVR': 'OPP OVR',
            'OFF': 'OPP OFF',
            'PASS': 'OPP PASS',
            'PBLK': 'OPP PBLK',
            'RECV': 'OPP RECV',
            'RUN': 'OPP RUN',
            'RBLK': 'OPP RBLK',
            'DEF': 'OPP DEF',
            'RDEF': 'OPP RDEF',
            'TACK': 'OPP TACK',
            'PRSH': 'OPP PRSH',
            'COV': 'OPP COV'
        })
        matchups = pd.merge(matchups, grades, on="Away Team")
        matchups.to_csv(f"../Data/Matchups/grades_matchups_WEEK{w}.csv", index=False)

        final = matchups
        results = final[['WEEK', 'Home Team', 'Home Spread', 'Away Team', 'Away Spread']].copy()

        results['Overall Adv'] = final['OVR'] - final['OPP OVR']
        results['Offense Adv'] = final['OFF'] - final['OPP DEF']
        results['Defense Adv'] = final['DEF'] - final['OPP OFF']
        results['Passing Adv'] = final['PASS'] - final['OPP COV']
        results['Pass Block Adv'] = final['PBLK'] - final['OPP PRSH']
        results['Receving Adv'] = final['RECV'] - final['OPP COV']
        results['Running Adv'] = final['RUN'] - final['OPP RDEF']
        results['Run Block Adv'] = final['RBLK'] - final['OPP RDEF']
        results['Run Defense Adv'] = final['RDEF'] - final['OPP RUN']
        results['Pass Rush Adv'] = final['PRSH'] - ((final['OPP PBLK'] + final['OPP PASS']) / 2)
        results['Coverage Adv'] = final['COV'] - ((final['OPP RECV'] + final['OPP PBLK']) / 2)

        advantage_columns = [
            'Overall Adv', 'Offense Adv', 'Defense Adv'
        ]

        for col in advantage_columns:
            results[f'{col}_sig'] = np.where(results[col] > 2, 'home significant', np.where(
                results[col] < -2, 'away significant', 'insignificant'))
            print(f'{col}_sig: {results[f"{col}_sig"]}')

        # Game Pick logic
        results['Game Pick'] = np.where(
            (results[[f'{col}_sig' for col in advantage_columns]].eq('home significant').all(axis=1)) |
            (results[[f'{col}_sig' for col in advantage_columns]].eq('insignificant').all(axis=1)),
            results['Home Team'], np.where(
                (results[[f'{col}_sig' for col in advantage_columns]].eq('away significant').all(axis=1)) |
                (results[[f'{col}_sig' for col in advantage_columns]].eq('insignificant').all(axis=1)),
                results['Away Team'], 'No Pick'))


        results = results.sort_values(by=['Overall Adv'], ascending=False)
        results = results[results['Game Pick'] != 'No Pick']
        results.to_csv(f"../Data/Picks/WEEK{w}.csv", index=False)

if __name__ == '__main__':
    makePicks()