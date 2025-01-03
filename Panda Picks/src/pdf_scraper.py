import pandas as pd
import tabula
import sqlite3
import logger

def getGrades():
    df = tabula.read_pdf(r"../Data/Grades/PFFTeamGrades.pdf", pages=1)
    abrevs = pd.read_csv(r"../Data/Grades/NFL_translations.csv")
    df = df[0]
    df = df.drop(columns=['Unnamed: 0', 'Unnamed: 1', 'POINTS', 'Unnamed: 3'])
    new = df['OFFENSE'].str.split(" ", n=1, expand=True)
    df['PASS BLOCK'] = new[0]
    df['RECEIVING'] = new[1]
    df.drop(columns=['OFFENSE'], inplace=True)
    df.drop(columns=['SPEC'], inplace=True)
    df = df.rename(columns={
        'Unnamed: 2': 'TEAM',
        'Unnamed: 4': 'OVR',
        'Unnamed: 5': 'OFF',
        'Unnamed: 6': 'PASS',
        'Unnamed: 7': 'RUN',
        'Unnamed: 8': 'RBLK',
        'Unnamed: 9': 'DEF',
        'Unnamed: 10': 'RDEF',
        'DEFENSE': 'TACK',
        'Unnamed: 11': 'PRSH',
        'Unnamed: 12': 'COV',
        'PASS BLOCK': 'PBLK',
        'RECEIVING': 'RECV'
    })
    df.dropna(inplace=True)
    new_teams = pd.merge(df, abrevs, on='TEAM')
    new_teams.drop(columns=[
        'TEAM',
        'Unnamed: 2',
        'Unnamed: 3',
        'Unnamed: 4',
        'Unnamed: 5',
        'Unnamed: 6',
        'Unnamed: 7',
        'Unnamed: 8',
        'Unnamed: 9',
        'Unnamed: 10',
        'Unnamed: 11',
        'Unnamed: 12',
        'Unnamed: 13',
        'Unnamed: 14',
        'Unnamed: 15',
        'Unnamed: 16'], inplace=True)
    new_teams = new_teams.rename(columns={'Abrev': 'TEAM'})
    new_teams = new_teams[
        ['TEAM', 'OVR', 'OFF', 'PASS', 'RUN', 'RECV', 'PBLK', 'RBLK', 'DEF', 'RDEF', 'TACK', 'PRSH', 'COV']]

    # Connect to SQLite database
    conn = sqlite3.connect('db/nfl_data.db')
    cursor = conn.cursor()


    # Insert data into the table
    new_teams.to_sql('grades', conn, if_exists='replace', index=False)

    # Commit and close the connection
    conn.commit()
    conn.close()

if __name__ == '__main__':
    getGrades()