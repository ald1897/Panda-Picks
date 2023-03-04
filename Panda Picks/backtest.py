import pandas as pd
import numpy as np


def runTests():
    # Set Grade Precision
    pd.set_option("display.precision", 4)
    pd.options.display.float_format = '{:10,.2f}'.format

    # Load Offensive Player Grades for each position
    weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7', 'WEEK8', 'WEEK9', 'WEEK10', 'WEEK11',
             'WEEK12', 'WEEK13', 'WEEK14', 'WEEK15', 'WEEK16', 'WEEK17', 'WEEK18']
    # weeks = ['WEEK1']
    final = pd.DataFrame()
    last = pd.DataFrame()
    for w in weeks:
        print("Generating Stats for " + w + '...')
        games = {'week': [w]}
        games = pd.DataFrame(data=games)
        week = pd.read_csv(r'Data/Picks/' + w + '.csv')

        spreads = pd.read_csv(r"Data/Spreads/spreads.csv")
        spreads['Game Key'] = spreads['Home Team'] + spreads['Away Team']
        spreads = spreads[
            ['Game Date', 'Home Team', 'Home Score', 'Away Score', 'Away Team', 'Home Line Close', 'Away Line Close', 'Home Odds Close', 'Away Odds Close', 'Game Key']]
        spreads = spreads.loc[spreads['Game Date'] == w]

        picks = week[['Game Date', 'Home Team', 'Away Team', 'Game Pick']].copy()
        picks['Game Key'] = picks['Home Team'] + picks['Away Team']

        stats = pd.DataFrame(games,
                             columns=['Game Date', 'ATS Wins', 'ATS Losses', 'ML Wins', 'ML Losses', 'Overall Wins'])

        compare = pd.merge(picks, spreads, on=['Game Key'])
        compare = compare.drop(columns=['Home Team_x', 'Away Team_x', 'Game Date_x'])
        compare = compare[compare['Game Pick'] != 'No Pick']
        # np.where(compare['Spread'] == 'PK', compare['Spread'].replace({'PK':0}), compare['Spread'])
        compare['Home Line Close'] = pd.to_numeric(compare['Home Line Close'])
        compare['Away Line Close'] = pd.to_numeric(compare['Away Line Close'])
        compare['Home Odds Close'] = pd.to_numeric(compare['Home Odds Close'])
        compare['Away Odds Close'] = pd.to_numeric(compare['Away Odds Close'])

        compare['Margin'] = compare['Away Score'] - compare['Home Score']
        # print(compare)
        compare['ATS Win/Loss'] = np.where(compare['Game Pick'] == compare['Home Team_y'],
                                           np.where(compare['Home Score'] + compare['Home Line Close'] <= compare[
                                               'Away Score'], 0, 1),
                                           np.where(compare['Away Score'] + compare['Away Line Close'] <= compare[
                                               'Home Score'], 0, 1))
        compare['ML Win/Loss'] = np.where(compare['Game Pick'] == compare['Home Team_y'],
                                          np.where(compare['Home Score'] > compare['Away Score'], 1, 0),
                                          np.where(compare['Away Score'] > compare['Home Score'], 1, 0))
        # print(compare)
        compare = compare.rename(columns={
            'Home Team_y': 'Home Team',
            'Away Team_y': 'Away Team'})
        final = compare[
            ['Game Pick', 'Home Team', 'Away Team', 'Home Score', 'Away Score', 'Home Line Close', 'ATS Win/Loss',
             'ML Win/Loss']]
        compare['Wager'] = 100


        conditions = [
            (compare['Game Pick'] == compare['Home Team']) & (compare['ATS Win/Loss'] > 0),
            (compare['Game Pick'] == compare['Away Team']) & (compare['ATS Win/Loss'] > 0),
            (compare['Game Pick'] == compare['Home Team']) & (compare['ATS Win/Loss'] == 0),
            (compare['Game Pick'] == compare['Away Team']) & (compare['ATS Win/Loss'] == 0)]

        choices = [1.9 * compare['Wager'] - compare['Wager'],
                   1.9 * compare['Wager'] - compare['Wager'],
                   compare['Wager']*-1,
                   compare['Wager']*-1]

        compare['ATS Payout'] = np.select(conditions, choices, 0)

        conditions = [
            (compare['Game Pick'] == compare['Home Team']) & (compare['ML Win/Loss'] > 0),
            (compare['Game Pick'] == compare['Away Team']) & (compare['ML Win/Loss'] > 0),
            (compare['Game Pick'] == compare['Home Team']) & (compare['ML Win/Loss'] == 0),
            (compare['Game Pick'] == compare['Away Team']) & (compare['ML Win/Loss'] == 0)]

        choices = [compare['Home Odds Close'] * compare['Wager'] - compare['Wager'],
                   compare['Away Odds Close'] * compare['Wager'] - compare['Wager'],
                   compare['Wager']*-1,
                   compare['Wager']*-1]

        compare['ML Payout'] = np.select(conditions, choices, 0)
        compare['Weekly ATS Payout'] = compare['ATS Payout'].sum(axis=0)
        compare['Weekly ML Payout'] = compare['ML Payout'].sum(axis=0)
        compare['Total Payout'] = compare['ATS Payout'].sum(axis=0) + compare['ML Payout'].sum(axis=0)
        compare.to_csv('./Data/Picks/compare.csv', index=False)
        games['ATS Win %'] = compare['ATS Win/Loss'].sum(axis=0) / len(compare.index)
        games['ML Win %'] = compare['ML Win/Loss'].sum(axis=0) / len(compare.index)
        games['Weekly Risk'] = compare['Wager'].sum(axis=0)
        games['ATS Payout'] = compare['ATS Payout'].sum(axis=0)
        games['ML Payout'] = compare['ML Payout'].sum(axis=0)
        games['Weekly Profit'] = games['ATS Payout'] + games['ML Payout']

        # games['Bank'] = compare['Wager']+games['Weekly Profit']

        last = pd.concat([games, last])

    last['Season ATS Winning %'] = np.average(last['ATS Win %'])
    last['Season ML Winning %'] = np.average(last['ML Win %'])
    # last['Season Overall Winning %'] = final['Total Wins']/(final['Total Wins']+final['Total Losses'])
    last['Season Risk'] = last['Weekly Risk'].max(axis=0)
    last['Season Profit'] = last['Weekly Profit'].sum(axis=0)
    # print(last)

    last.to_csv('./Data/Picks/stats.csv', index=False)

    # stats['ats_wins'] = np.where(compare['ATS'] == 'W', 1, 0 )


if __name__ == "__main__":
    runTests()
