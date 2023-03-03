import pandas as pd
from tabula import read_pdf

# df = read_csv(r"Data/Grades/PFFTeamGrades.pdf", pages=1)
df = pd.read_csv(r"Data/Spreads/nflSpreads.csv")
abrevs = pd.read_csv(r"Data/Grades/NFL_translations.csv")
# df = df.rename(columns=df.iloc[0])
# df = df[0]
# print(df)
# print(abrevs)
# Home team abrevs into spreads csv
abrevs = abrevs.rename(columns={
    'TEAM': 'Home Team'})
new_teams = pd.merge(df, abrevs, on='Home Team')
# Rename team column to bring in away team abrevs
abrevs = abrevs.rename(columns={
    'Home Team': 'Away Team'})
# merge spreads
new_teams.drop(columns=[
    # 'RANK',
    'Home Team',
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

abrevs = abrevs.rename(columns={
    'Abrev': 'Home Team'})

spreads = pd.merge(new_teams, abrevs, on='Away Team')

spreads.drop(columns=[
    # 'RANK',
    'Away Team',
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

spreads = spreads.rename(columns={
    'Abrev': 'Away Team',
    'Date': 'Game Date'})
# print(new_teams)
# print(newer_teams.head())
# new_teams.to_csv('./Data/Spreads/new_teams.csv', index=False)
spreads.to_csv('./Data/Spreads/spreads.csv', index=False)
