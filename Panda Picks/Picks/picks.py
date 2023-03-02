import pandas as pd
import numpy as np

# w= 'WEEK1'
weeks = ['7']
for w in weeks:
    # Set Grade Precision
    pd.set_option("display.precision", 2)
    pd.options.display.float_format = '{:10,.2f}'.format
    # Load Team Grades for each position
    scores = pd.read_csv(r'H:\Projects\Python\Pandas-Picks\v4\Rankings\Data\TeamScores.csv')
    scores = scores.drop(columns=['Unnamed: 0'])
    scores = scores.rename(columns={'Team': 'Home Team'})
    print(scores.head())
    # Load & Matchups & spreads

    matchups = pd.read_csv(r'H:\Projects\Python\Pandas-Picks\v4\Matchups\matchups_WEEK' + w + '.csv')
    print(matchups)
    # matchups = matchups.dropna(axis=0, how='all')

    # merge grades with home teams on TEAM column
    matchups = pd.merge(matchups, scores, on="Home Team")
    print(matchups)
    #
    scores = scores.rename(columns={
        'Home Team': 'Away Team',
        'PPG_DEF_SCORE': 'OPP_PPG_DEF_SCORE',
        'PPG_OFF_SCORE': 'OPP_PPG_OFF_SCORE',
        'PASS_DEF_SCORE': 'OPP_PASS_DEF_SCORE',
        'PASS_OFF_SCORE': 'OPP_PASS_OFF_SCORE',
        'RUSH_DEF_SCORE': 'OPP_RUSH_DEF_SCORE',
        'RUSH_OFF_SCORE': 'OPP_RUSH_OFF_SCORE',
        'REC_DEF_SCORE': 'OPP_REC_DEF_SCORE',
        'REC_OFF_SCORE': 'OPP_REC_OFF_SCORE'
    })
    matchups = pd.merge(matchups, scores, on="Away Team")
    print(matchups.head())

    matchups.to_csv(r'H:\Projects\Python\Pandas-Picks\v4\Matchups\matchup_Scores_WEEK' + w + '.csv', index=False)

    final = matchups
    print(final)
    #
    results = final[['Game Date', 'Home Team', 'Home Spread', 'Away Team', 'Away Spread']].copy()

    # Evaluate Offensive vs Defensive Matchups & Defensive vs OFfensive Matchups, Highlight any that win both
    results['DEF_PPG_ADV'] = final['PPG_DEF_SCORE'] - final['OPP_PPG_DEF_SCORE']
    results['OFF_PPG_ADV'] = final['PPG_OFF_SCORE'] - final['OPP_PPG_OFF_SCORE']
    # results['OFF_PPG_ADV'] = final['PPG_OFF_SCORE'] - final['OPP_PPG_OFF_SCORE']
    # results['OFF_PPG_ADV'] = final['PPG_OFF_SCORE'] - final['OPP_PPG_OFF_SCORE']
    # results['OFF_PPG_ADV'] = final['PPG_OFF_SCORE'] - final['OPP_PPG_OFF_SCORE']
    # results['OFF_PPG_ADV'] = final['PPG_OFF_SCORE'] - final['OPP_PPG_OFF_SCORE']
    # results['OFF_PPG_ADV'] = final['PPG_OFF_SCORE'] - final['OPP_PPG_OFF_SCORE']
    # results['OFF_PPG_ADV'] = final['PPG_OFF_SCORE'] - final['OPP_PPG_OFF_SCORE']
    # results['OFF_PPG_ADV'] = final['PPG_OFF_SCORE'] - final['OPP_PPG_OFF_SCORE']

    # results['Offense Adv'] = final['OFFENSE'] - final['OPP DEFENSE']
    # results['Passing Adv'] = final['PASSING'] - ((final['OPP PASS RUSH']+final['OPP COVERAGE'])/2)
    # results['Pass Block Adv'] = final['PASS BLOCK'] - final['OPP PASS RUSH']
    # results['Receving Adv'] = final['RECEIVING'] - final['OPP COVERAGE']
    # results['Running Adv'] = final['RUNNING'] - final['OPP RUN DEF']
    # results['Run Block Adv'] = final['RUN BLOCK'] - final['OPP RUN DEF']
    # results['Defense Adv'] = final['DEFENSE'] - final['OPP OFFENSE']
    # results['Run Defense Adv'] = final['RUN DEF'] - ((final['OPP RUNNING']+final['OPP RUN BLOCK'])/2)
    # results['Tackling Adv'] = final['TACKLING'] - ((final['OPP RUNNING']+final['OPP RECEIVING'])/2)
    # results['Pass Rush Adv'] = final['PASS RUSH'] - ((final['OPP PASS BLOCK']+final['OPP PASSING'])/2)
    # results['Coverage Adv'] = final['COVERAGE'] - ((final['OPP RECEIVING']+final['OPP PASS BLOCK'])/2)
    # results['Game Pick'] = np.where((results['Overall Adv']>=10) & (final['OVERALL'] > final['OPP OVERALL']) & (final['DEFENSE'] > final['OPP OFFENSE']) , results['Home Team'], np.where((results['Overall Adv']<= -10) & (final['OVERALL'] < final['OPP OVERALL']) & (final['DEFENSE'] < final['OPP OFFENSE']) , results['Away Team'], 'No Pick'))
    # # results['Game Pick'] = np.where((results['Offense Adv']>6) & (results['Defense Adv']>6), results['TEAM'],'No Pick')
    # # results['Game Pick'] = np.where((final['OVERALL'] - final['OPP OVERALL'] >= 5) & (final['OFFENSE'] - final['OPP DEFENSE'] >= 2.5) & (final['DEFENSE'] - final['OPP OFFENSE'] >= 2.5), results['TEAM'], 'No Pick')
    #
    # results = results.sort_values(by=['OFF_PPG_ADV'], ascending=False)
    print(results)
    #
    #
    #
    # results = results[results['Game Pick'] != 'No Pick']
    # print("---------Dick's Picks: "+ w +"-----------")
    # print(results)
    # # # #Send to CSV in project folder
    # results.to_csv(r"..\Pandas-Picks\v3\Picks\\WEEK"+ w + '.csv', index = False)
    # results.to_csv(r"..\FlaskPicks\sample_app\Picks\\WEEK"+ w + '.csv', index = False)
    # # weeks.pop()[0]
