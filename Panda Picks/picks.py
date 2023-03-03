import pandas as pd
import numpy as np


# w= 'WEEK1'

def makePicks():
    weeks = ["1", '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17']
    # weeks = ["1"]
    for w in weeks:
        # Set Grade Precision
        pd.set_option("display.precision", 2)
        pd.options.display.float_format = '{:10,.2f}'.format
        # Load Team Grades for each position
        grades = pd.read_csv("..\Panda Picks\Data\Grades\TeamGrades.csv")
        grades = grades.rename(columns={'TEAM': 'Home Team'})
        # Load & Matchups & spreads
        matchups = pd.read_csv(r"..\Panda Picks\Data\Matchups\matchups_WEEK" + w + ".csv")
        matchups = matchups.dropna(axis=0, how='all')

        # merge grades with home teams on TEAM column
        matchups = pd.merge(matchups, grades, on="Home Team")
        # print(matchups)

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

        # print(matchups)
        matchups.to_csv(r"..\Panda Picks\Data\Matchups\grades_matchups_WEEK" + w + ".csv", index=False)

        col_list = matchups.columns.tolist()

        matchups = matchups[[
            # 'Total',
            'Game Date',
            'Home Team',
            'Home Spread',
            'Away Team',
            'Away Spread',
            'OVR',
            'OFF',
            'PASS',
            'PBLK',
            'RECV',
            'RUN',
            'RBLK',
            'DEF',
            'RDEF',
            'TACK',
            'PRSH',
            'COV',
            'OPP OVR',
            'OPP OFF',
            'OPP PASS',
            'OPP PBLK',
            'OPP RECV',
            'OPP RUN',
            'OPP RBLK',
            'OPP DEF',
            'OPP RDEF',
            'OPP TACK',
            'OPP PRSH',
            'OPP COV'
        ]]
        # print(matchups)

        final = matchups
        # print(final)

        results = final[['Game Date', 'Home Team', 'Home Spread', 'Away Team', 'Away Spread']].copy()

        # Evaluate Offensive vs Defensive Matchups & Defensive vs OFfensive Matchups, Highlight any that win both
        results['Overall Adv'] = final['OVR'] - final['OPP OVR']
        results['Offense Adv'] = final['OFF'] - final['OPP DEF']
        results['Passing Adv'] = final['PASS'] - ((final['OPP PRSH'] + final['OPP COV']) / 2)
        results['Pass Block Adv'] = final['PBLK'] - final['OPP PRSH']
        results['Receving Adv'] = final['RECV'] - final['OPP COV']
        results['Running Adv'] = final['RUN'] - final['OPP RDEF']
        results['Run Block Adv'] = final['RBLK'] - final['OPP RDEF']
        results['Defense Adv'] = final['DEF'] - final['OPP OFF']
        results['Run Defense Adv'] = final['RDEF'] - ((final['OPP RUN'] + final['OPP RBLK']) / 2)
        results['Tackling Adv'] = final['TACK'] - ((final['OPP RUN'] + final['OPP RECV']) / 2)
        results['Pass Rush Adv'] = final['PRSH'] - ((final['OPP PBLK'] + final['OPP PASS']) / 2)
        results['Coverage Adv'] = final['COV'] - ((final['OPP RECV'] + final['OPP PBLK']) / 2)
        results['Game Pick'] = np.where(
            (results['Overall Adv'] >= 10) & (final['OVR'] > final['OPP OVR']) & (final['DEF'] > final['OPP OFF']),
            results['Home Team'], np.where(
                (results['Overall Adv'] <= -10) & (final['OVR'] < final['OPP OVR']) & (final['DEF'] < final['OPP OFF']),
                results['Away Team'], 'No Pick'))
        # results['Game Pick'] = np.where((results['Offense Adv']>6) & (results['Defense Adv']>6), results['TEAM'],'No Pick')
        # results['Game Pick'] = np.where((final['OVERALL'] - final['OPP OVERALL'] >= 5) & (final['OFFENSE'] - final['OPP DEFENSE'] >= 2.5) & (final['DEFENSE'] - final['OPP OFFENSE'] >= 2.5), results['TEAM'], 'No Pick')

        results = results.sort_values(by=['Overall Adv'], ascending=False)
        # print(results)

        results = results[results['Game Pick'] != 'No Pick']
        print("---------Dick's Picks: " + w + "-----------")
        # print(results)
        # # #Send to CSV in project folder
        results.to_csv(r"..\Panda Picks\Data\Picks\WEEK" + w + '.csv', index=False)
        # results.to_csv(r"..\FlaskPicks\sample_app\Picks\\WEEK"+ w + '.csv', index = False)
        # weeks.pop()[0]


if __name__ == '__main__':
    makePicks()
