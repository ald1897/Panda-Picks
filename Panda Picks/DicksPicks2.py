import pandas as pd 
import numpy as np
# w= 'WEEK1'
weeks = ["1",'2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17']
for w in weeks:
    #Set Grade Precision
    pd.set_option("display.precision", 2)
    pd.options.display.float_format = '{:10,.2f}'.format
    #Load Team Grades for each position
    grades = pd.read_csv("..\Panda Picks\Grades\TeamGrades.csv")
    grades = grades.rename(columns={'TEAM':'Home Team'})
    #Load & Matchups & spreads 
    matchups = pd.read_csv(r"..\Panda Picks\Matchups\matchups_WEEK" + w +".csv")
    matchups = matchups.dropna(axis=0, how='all')

    #merge grades with home teams on TEAM column
    matchups = pd.merge(matchups, grades, on="Home Team")
    # print(matchups)

    grades = grades.rename(columns={
        'Home Team': 'Away Team',
        'OVERALL': 'OPP OVERALL',
        'OFFENSE': 'OPP OFFENSE',
        'PASSING': 'OPP PASSING',
        'PASS BLOCK': 'OPP PASS BLOCK',
        'RECEIVING': 'OPP RECEIVING',
        'RUNNING': 'OPP RUNNING',
        'RUN BLOCK': 'OPP RUN BLOCK',
        'DEFENSE': 'OPP DEFENSE',
        'RUN DEF': 'OPP RUN DEF',
        'TACKLING': 'OPP TACKLING',
        'PASS RUSH': 'OPP PASS RUSH',
        'COVERAGE': 'OPP COVERAGE',
        'SPEC':'OPP SPEC'
        })
    matchups = pd.merge(matchups, grades, on="Away Team")

    # print(matchups)
    matchups.to_csv(r"..\Pandas-Picks\v3\MatchupGrades\grades_matchups_WEEK" + w + ".csv", index = False)

    col_list = matchups.columns.tolist()

    matchups = matchups[[
        'Total',
        'Home Team',
        'Home Spread',
        'Away Team',
        'Away Spread',
        'OVERALL',
        'OFFENSE',
        'PASSING',
        'PASS BLOCK',
        'RECEIVING',
        'RUNNING',
        'RUN BLOCK',
        'DEFENSE',
        'RUN DEF',
        'TACKLING',
        'PASS RUSH',
        'COVERAGE',
        'OPP OVERALL',
        'OPP OFFENSE',
        'OPP PASSING',
        'OPP PASS BLOCK',
        'OPP RECEIVING',
        'OPP RUNNING',
        'OPP RUN BLOCK',
        'OPP DEFENSE',
        'OPP RUN DEF',
        'OPP TACKLING',
        'OPP PASS RUSH',
        'OPP COVERAGE'
    ]]
    # print(matchups)

    final = matchups
    # print(final)

    results = final[['Game Date','Home Team','Home Spread','Away Team','Away Spread']].copy()

    # Evaluate Offensive vs Defensive Matchups & Defensive vs OFfensive Matchups, Highlight any that win both
    results['Overall Adv'] = final['OVERALL'] - final['OPP OVERALL']
    results['Offense Adv'] = final['OFFENSE'] - final['OPP DEFENSE']
    results['Passing Adv'] = final['PASSING'] - ((final['OPP PASS RUSH']+final['OPP COVERAGE'])/2)
    results['Pass Block Adv'] = final['PASS BLOCK'] - final['OPP PASS RUSH']
    results['Receving Adv'] = final['RECEIVING'] - final['OPP COVERAGE']
    results['Running Adv'] = final['RUNNING'] - final['OPP RUN DEF']
    results['Run Block Adv'] = final['RUN BLOCK'] - final['OPP RUN DEF']
    results['Defense Adv'] = final['DEFENSE'] - final['OPP OFFENSE']
    results['Run Defense Adv'] = final['RUN DEF'] - ((final['OPP RUNNING']+final['OPP RUN BLOCK'])/2)
    results['Tackling Adv'] = final['TACKLING'] - ((final['OPP RUNNING']+final['OPP RECEIVING'])/2)
    results['Pass Rush Adv'] = final['PASS RUSH'] - ((final['OPP PASS BLOCK']+final['OPP PASSING'])/2)
    results['Coverage Adv'] = final['COVERAGE'] - ((final['OPP RECEIVING']+final['OPP PASS BLOCK'])/2)
    results['Game Pick'] = np.where((results['Overall Adv']>=10) & (final['OVERALL'] > final['OPP OVERALL']) & (final['DEFENSE'] > final['OPP OFFENSE']) , results['Home Team'], np.where((results['Overall Adv']<= -10) & (final['OVERALL'] < final['OPP OVERALL']) & (final['DEFENSE'] < final['OPP OFFENSE']) , results['Away Team'], 'No Pick'))
    # results['Game Pick'] = np.where((results['Offense Adv']>6) & (results['Defense Adv']>6), results['TEAM'],'No Pick')
    # results['Game Pick'] = np.where((final['OVERALL'] - final['OPP OVERALL'] >= 5) & (final['OFFENSE'] - final['OPP DEFENSE'] >= 2.5) & (final['DEFENSE'] - final['OPP OFFENSE'] >= 2.5), results['TEAM'], 'No Pick')

    results = results.sort_values(by=['Overall Adv'], ascending=False)
    # print(results)



    results = results[results['Game Pick'] != 'No Pick']
    print("---------Dick's Picks: "+ w +"-----------")
    print(results)
    # # #Send to CSV in project folder
    results.to_csv(r"..\Panda Picks\Picks\\WEEK"+ w + '.csv', index = False)
    # results.to_csv(r"..\FlaskPicks\sample_app\Picks\\WEEK"+ w + '.csv', index = False)
    # weeks.pop()[0]
