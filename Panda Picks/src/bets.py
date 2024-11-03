from itertools import combinations
import pandas as pd
import sqlite3

# Week to generate combinations for
# weeks = ['9', '10', '11', '12', '13', '14', '15', '16', '17', '18']
weeks = ['9']

def adjust_spread(row, teaser_points=6):
    if row['Home_Line_Close'] < 0:
        row['Home_Line_Close'] += teaser_points
    else:
        row['Home_Line_Close'] -= teaser_points

    if row['Away_Line_Close'] < 0:
        row['Away_Line_Close'] += teaser_points
    else:
        row['Away_Line_Close'] -= teaser_points
    return row

for week in weeks:
    conn = sqlite3.connect('db/nfl_data.db')
    cursor = conn.cursor()
    # List of teams from the picks table in nfl_data.db
    df = pd.read_sql_query(f"SELECT * FROM picks WHERE week = 'WEEK{week}'", conn)
    teams = df['Game_Pick'].unique()

    # Adjust the spread for each team
    df = df.apply(adjust_spread, axis=1)

    # Generate combinations
    two_team_combos = list(combinations(teams, 2))
    three_team_combos = list(combinations(teams, 3))
    four_team_combos = list(combinations(teams, 4))

    # Display results
    print("Week:", week)
    print("2-Team Combos:", two_team_combos)
    print("3-Team Combos:", three_team_combos)
    print("4-Team Combos:", four_team_combos)
    print("Total Bets:", len(two_team_combos) + len(three_team_combos) + len(four_team_combos))

    # Save results to csv
    pd.DataFrame(two_team_combos).to_csv(f'combos_2_TEAM_WEEK{week}.csv', index=False)
    pd.DataFrame(three_team_combos).to_csv(f'combos_3_TEAM_WEEK{week}.csv', index=False)
    pd.DataFrame(four_team_combos).to_csv(f'combos_4_TEAM_WEEK{week}.csv', index=False)

    # Place bets on each combination
    for combo in two_team_combos + three_team_combos + four_team_combos:
        print(f"Placing bet on combination: {combo}")

    conn.close()