import pandas as pd
import numpy as np

def matchups():
    season = "2024"
    weeks = ['1', '2', '3', '4', '5', '6','7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18']
    # weeks = ['9']
    # w = "1"
    # print("SCRAPING GAME DATA...")
    for w in weeks:
        # Scrape WEB DATA INTO table
        df = pd.read_html(f"https://nflgamedata.com/schedule.php?season={season}&week={w}")
        # keep only matchup table, get rid of other stuff
        # print("SETTING DATAFRAME.....")
        df = df[4]

        # print("CLEANING...")
        df = df.drop([0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 14, 15, 17, 18, 19, 20, 21, 22, 23], axis=1)

        # print('CREATING NEW COLUMNS')
        df['Away Team'] = df[8].copy()
        df['Away Spread'] = df[11].copy()
        df['Home Spread'] = df[13].copy()
        df['Home Team'] = df[16].copy()

        # print('DROPPING OLD COLUMNS / ROWS')
        df = df.drop(columns=[8, 11, 13, 16])
        df = df.drop([0])

        # print('REMOVING BYE WEEK TEAMS')
        df = df[df['Home Team'] != '-- BYE --']

        # print('SETTING WEEK COLUMN')
        df['WEEK'] = 'WEEK' + w

        # fill in NaN values under Away Spread with the value of Home Spread multiplied by -1
        # print('FILLING NaN VALUES')
        df['Away Spread'] = df['Away Spread'].replace('--', np.nan)
        df['Away Spread'] = df['Away Spread'].fillna(df['Home Spread'].astype(float) * -1)
        df['Home Spread'] = df['Home Spread'].replace('--', np.nan)
        df['Home Spread'] = df['Home Spread'].fillna(df['Away Spread'].astype(float) * -1)

        # print('CHANGING COLUMN NAMES')
        df = df.rename(columns={8: 'Away Team', 11: 'Away Spread', 13: 'Home Spread', 16: 'Home Team'})

        # print('RESETTING INDEX')
        df.reset_index(drop=True, inplace=True)

        # print('SAVING DATA')
        df.to_csv(f"../Data/Matchups/matchups_WEEK{w}.csv", index=False)

        # print(df)
    # print("DONE WITH GAME DATA")

if __name__ == '__main__':
    matchups()
