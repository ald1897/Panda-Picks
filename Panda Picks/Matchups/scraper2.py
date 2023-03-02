import logging

import pandas as pd
import numpy as np

season = "2022"
weeks = ['1']
# weeks = ['1']
# w = "1"
for w in weeks:
    # Scrape table
    print("SCRAPING NFL GAME DATA.....")
    df = pd.read_html('https://nflgamedata.com/schedule.php?season=' + season + '&week=' + w)
    # print(df)
    # print(pd.read_html('http://nflgamedata.com/schedule.php?season='+ season +'&week='+ w))
    print("SETTING DATAFRAME.....")
    df = df[4]
    print("PRINTING DATAFRAME AS IS")
    # print(df)
    # df.head()
    df = df.drop([0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22, 23], axis=1)
    print("CLEANING.....DROPPING COLUMNS 0,1,2,3,6,7,9,10,11,12,13,14,15,17,18,19,20,21,22,23")
    # print(df)
    print("CLEANING.....DROPPING ROWS 2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32")
    df = df.drop([2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32])
    # print(df)
    # # Assign row as column headers
    header_row = 0
    df.columns = df.iloc[header_row]
    print("CLEANING.....COL HEADERS ASSIGNED")

    # Convert row to column header using DataFrame.iloc[]
    df.columns = df.iloc[0]
    # print(df)
    print("CLEANING.....COL HEADERS ASSIGNED AFTER DROPPING ROW 0")
    df = df.drop([0])
    # df = df.drop(columns=[0])
    print("FINAL DATAFRAME FINISHED")
    # print(df)

    # drop empty columns
    # df = df.drop([0,1,2,6,7,10,11,14,16,17,18,19],axis=1)
    # # print(df)
    # df.drop()
    # set col headers
    # df = df.rename(columns=df.iloc[0])
    # df = df.drop(df.index[0])
    # # print(df)
    #
    # # rename duplicate cols for removal
    # cols=pd.Series(df.columns)
    # for dup in cols[cols.duplicated()].unique():
    #     cols[cols[cols == dup].index.values.tolist()] = [dup + '.' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
    #
    # # rename the columns with the cols list
    #
    # df.columns=cols
    # # print(df)
    #
    # # rename duplicated columns
    # df = df.rename(columns={
    #     'Away Team.1': 'Away Spread',
    #     'Home Team.1': 'Home Spread'})
    # # print(df)
    #
    # df['Away Spread'] = np.where(df['Away Spread'] == '-- BYE --', 100, df['Away Spread'])
    # df['Home Spread'] = np.where(df['Home Spread'] == '-- BYE --', 100, df['Home Spread'])
    #
    # df = df.fillna(0)
    #
    # df = df.astype({'Away Spread':'float64',
    #                 'Home Spread': 'float64',
    #                 'Game Date': 'datetime64',
    #                 'Total': 'float64'})
    #
    # # print(df)
    # df['Away Team'] = np.where(df['Away Team'] == 'BAL', 'BLT', np.where(df['Away Team'] == 'HOU', 'HST', np.where(df['Away Team'] == 'CLE', 'CLV', np.where(df['Away Team'] == 'ARI', 'ARZ', np.where(df['Away Team'] == 'LA', 'LAR', df['Away Team'])))))
    # df['Home Team'] = np.where(df['Home Team'] == 'BAL', 'BLT', np.where(df['Home Team'] == 'HOU', 'HST', np.where(df['Home Team'] == 'CLE', 'CLV', np.where(df['Home Team'] == 'ARI', 'ARZ', np.where(df['Home Team'] == 'LA', 'LAR', df['Home Team'])))))
    # df['Away Spread'] = np.where(df['Away Spread'] == 0, df['Home Spread']*(-1), df['Away Spread'])
    # df['Home Spread'] = np.where(df['Home Spread'] == 0, df['Away Spread']*(-1), df['Home Spread'])
    # df['Game Date'] = 'WEEK'+ w
    #
    # print(df)
    #
    df.to_csv(r"..\Panda Picks\Matchups\matchups_WEEK" + w +".csv", index = False)
    print("Saved Week " + w + " Matchups to CSV")
    # #
