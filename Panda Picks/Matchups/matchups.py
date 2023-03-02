import pandas as pd
import numpy as np

season = "2022"
# weeks = ['1', '2', '3', '4', '5', '6''7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18']
weeks = ['1']
# w = "1"
for w in weeks:
    # Scrape WEB DATA INTO table
    print("SCRAPING NFLGAMEDATA.COM.....")
    df = pd.read_html('https://nflgamedata.com/schedule.php?season=' + season + '&week=' + w)
    # keep only matchup table, get rid of other stuff
    print("SETTING DATAFRAME.....")
    df = df[4]
    print("CLEANING.....DROPPING COLUMNS 0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 14, 15, 17, 18, 19, 20, 21, 22, 23")
    df = df.drop([0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 14, 15, 17, 18, 19, 20, 21, 22, 23], axis=1)
    print('CREATING NEW COLUMNS')
    df['Away Team'] = df[8].copy()
    df['Away Spread'] = df[11].copy()
    df['Home Spread'] = df[13].copy()
    df['Home Team'] = df[16].copy()
    print('DROPPING OLD COLUMNS / ROWS')
    df = df.drop(columns=[8, 11, 13, 16])
    df = df.drop([0])
    print('REMOVING BYE WEEK TEAMS')
    df = df[df['Home Team'] != '-- BYE --']
    print('SETTING WEEK COLUMN')
    df['Game Date'] = 'WEEK' + w
    print("PRINTING FINAL DATAFRAME")
    # print(df)
    df.dropna()
    print(df)
    df.to_csv('./matchups_WEEK' + w + '.csv', index=False)
