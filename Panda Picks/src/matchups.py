import pandas as pd
import numpy as np
import sqlite3


def matchups():
    season = "2024"
    weeks = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18']

    # Connect to SQLite database
    conn = sqlite3.connect('db/nfl_data.db')
    cursor = conn.cursor()

    for w in weeks:
        # Scrape WEB DATA INTO table
        df = pd.read_html(f"https://nflgamedata.com/schedule.php?season={season}&week={w}")
        df = df[4]

        df = df.drop([0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 14, 15, 17, 18, 19, 20, 21, 22, 23], axis=1)

        df['Away_Team'] = df[8].copy()
        df['Away_Spread'] = df[11].copy()
        df['Home_Spread'] = df[13].copy()
        df['Home_Team'] = df[16].copy()

        df = df.drop(columns=[8, 11, 13, 16])
        df = df.drop([0])

        df = df[df['Home_Team'] != '-- BYE --']

        df['WEEK'] = 'WEEK' + w

        df['Away_Spread'] = df['Away_Spread'].replace('--', np.nan)
        df['Away_Spread'] = df['Away_Spread'].fillna(df['Home_Spread'].astype(float) * -1)
        df['Home_Spread'] = df['Home_Spread'].replace('--', np.nan)
        df['Home_Spread'] = df['Home_Spread'].fillna(df['Away_Spread'].astype(float) * -1)

        df = df.rename(columns={8: 'Away_Team', 11: 'Away_Spread', 13: 'Home_Spread', 16: 'Home_Team'})

        df.reset_index(drop=True, inplace=True)

        # Insert data into the SQLite database
        df.to_sql('matchups', conn, if_exists='append', index=False)

    # Commit and close the connection
    conn.commit()
    conn.close()


if __name__ == '__main__':
    matchups()