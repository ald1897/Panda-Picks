import pandas as pd 
import numpy as np 
#Set Grade Precision
pd.set_option("display.precision", 4)
pd.options.display.float_format = '{:10,.2f}'.format

#Load Offensive Player Grades for each position
weeks =['WEEK1','WEEK2','WEEK3','WEEK4','WEEK5','WEEK6','WEEK7','WEEK8','WEEK9','WEEK10','WEEK11','WEEK12','WEEK13','WEEK14','WEEK15']
final = pd.DataFrame()
for w in weeks:
    games = {'week':[w]}
    games = pd.DataFrame(data=games)
    week = pd.read_csv(r"\Projects\Pandas-Picks\Picks\\" + w +".csv")
    # print(week)
    spreads = pd.read_csv(r"\Projects\Pandas-Picks\Spreads\\" + w + "_spreads.csv") 
    spreads = spreads.drop(columns=['Total', 'Moneyline'])
    spreads = spreads.dropna(axis=1, how='all')
    spreads = spreads.rename(columns={'Score':'Opponent Score','Opp Score':'Team Score'})
    spreads['Spread'] = spreads['Spread']*(-1)
    
    spreads = spreads[[w,'Team Score','Opponent Score', 'Spread']]
    # print(spreads)
    # print(week)
    # print(spreads)

    picks = week[['TEAM', w,'Game Pick']].copy()

    # print(picks)
    # print(games)
    stats = pd.DataFrame(games, columns = ['week','ATS Wins','ATS Losses','ML Wins', 'ML Losses', 'Overall Wins'])

    compare = pd.merge(picks, spreads, on=[w])
    compare = compare[compare['Game Pick'] != 'No Pick']
    # np.where(compare['Spread'] == 'PK', compare['Spread'].replace({'PK':0}), compare['Spread'])
    # compare['Spread'] = pd.to_numeric(compare['Spread'])
    # print(compare)
#     compare['Spread 2'] = compare['Spread']

    compare['Margin'] = compare['Opponent Score'] - compare['Team Score']
    
    compare['ATS Win'] = np.where(compare['Game Pick'] != 'No Pick' , np.where(compare['Margin'] < compare['Spread'], 1, np.where(compare['Margin'] > compare['Spread'], 0,0)),0)
    compare['ATS Loss'] = np.where(compare['Game Pick'] != 'No Pick' , np.where(compare['Margin'] < compare['Spread'], 0, np.where(compare['Margin'] > compare['Spread'], 1,0)),0)
    compare['ATS Push'] = np.where(compare['Margin'] == compare['Spread'], 1,0)
    compare['ML Win'] = np.where(compare['Game Pick'] != 'No Pick' , np.where(compare['Team Score'] > compare['Opponent Score'], 1, np.where(compare['Team Score'] < compare['Opponent Score'], 0,0)),0)
    compare['ML Loss'] = np.where(compare['Game Pick'] != 'No Pick' , np.where(compare['Team Score'] < compare['Opponent Score'], 1, np.where(compare['Team Score'] > compare['Opponent Score'], 0,0)),0)
    compare['ML Push'] = np.where(compare['Team Score'] == compare['Opponent Score'], 1,0)
    compare['Spread Odds'] = -110
    compare['ML Odds'] = -165
    compare['Wager'] = 100
    compare['ATS Payout'] = np.where(compare['ATS Win']==1,((100/110)*(compare['Wager']/2)), ((compare['Wager']/2)*-1))
    compare['ML Payout'] = np.where(compare['ML Win']==1,((100/165)*(compare['Wager']/2)), ((compare['Wager']/2)*-1))
    compare['Total Payout'] = compare['ATS Payout'] + compare['ML Payout']
    # print(compare)
#     compare.to_csv('G:\Projects\DicksPicks\Picks\\'+ w + '_pickTable.csv', index = False)


    
    games['ATS Wins'] = compare['ATS Win'].sum(axis=0)
    games['ATS Losses'] = compare['ATS Loss'].sum(axis=0)
    games['ATS Pushes'] = compare['ATS Push'].sum(axis=0)
    games['ML Wins'] = compare['ML Win'].sum(axis=0)
    games['ML Losses'] = compare['ML Loss'].sum(axis=0)
    games['ML Pushes'] = compare['ML Push'].sum(axis=0)
    games['Weekly Wins'] = compare['ATS Win'].sum(axis=0) + compare['ML Win'].sum(axis=0)
    games['Weekly Losses'] = compare['ATS Loss'].sum(axis=0) + compare['ML Loss'].sum(axis=0)
    games['Weekly Pushes'] = compare['ATS Push'].sum(axis=0) + compare['ML Push'].sum(axis=0)
    games['Weekly Risk'] =   compare['Wager'].sum(axis=0)
    games['Weekly Profit'] = compare['Total Payout'].sum(axis=0)
    # print(games)
    final = final.append(games, ignore_index=True)
    # print(final)

print(final)

final['Total ATS Wins'] = final['ATS Wins'].sum(axis=0)
final['Total ATS Losses'] = final['ATS Losses'].sum(axis=0) 
final['Total ATS Pushes'] = final['ATS Pushes'].sum(axis=0) 
final['Total ML Wins'] = final['ML Wins'].sum(axis=0) 
final['Total ML Losses'] = final['ML Losses'].sum(axis=0) 
final['Total ML Pushes'] = final['ML Pushes'].sum(axis=0) 
final['Total Wins'] = final['Weekly Wins'].sum(axis=0) 
final['Total Losses'] = final['Weekly Losses'].sum(axis=0)
final['Total Pushes'] = final['Weekly Pushes'].sum(axis=0)
final['Weekly ATS Win%'] = final['ATS Wins']/(final['ATS Wins']+final['ATS Losses'])
final['Weekly ML Win%'] = final['ML Wins']/(final['ML Wins']+final['ML Losses'])
final['Season ATS Winning %'] = final['Total ATS Wins']/(final['Total ATS Wins']+final['Total ATS Losses'])
final['Season ML Winning %'] = final['Total ML Wins']/(final['Total ML Wins']+final['Total ML Losses'])
final['Season Overall Winning %'] = final['Total Wins']/(final['Total Wins']+final['Total Losses'])
final['Season Risk'] = final['Weekly Risk'].max(axis=0)
final['Season Profit'] = final['Weekly Profit'].sum(axis=0)
stats = final[['week','Weekly ATS Win%','Weekly ML Win%','Total ATS Wins','Total ATS Losses', 'Total ATS Pushes','Season ATS Winning %','Total ML Wins','Total ML Losses', 'Total ML Pushes','Season ML Winning %','Season Overall Winning %','Season Risk','Season Profit']].copy()

print(stats)





# stats['ats_wins'] = np.where(compare['ATS'] == 'W', 1, 0 )