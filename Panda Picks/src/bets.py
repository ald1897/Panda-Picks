from itertools import combinations
import pandas as pd

# Week to generate combinations for
weeks = ['9', '10', '11', '12', '13', '14', '15', '16', '17', '18']

for week in weeks:

    # List of teams from the csv file
    df = pd.read_csv(f'../Data/Picks/WEEK{week}.csv')
    teams = df['Game Pick'].unique()

    # Generate combinations
    two_team_combos = list(combinations(teams, 2))
    three_team_combos = list(combinations(teams, 3))
    four_team_combos = list(combinations(teams, 4))

    # Display results
    print("2-Team Combos:", two_team_combos)
    print("3-Team Combos:", three_team_combos)
    print("4-Team Combos:", four_team_combos)

    print("Total Bets:", len(two_team_combos) + len(three_team_combos) + len(four_team_combos))

    # Save results to csv
    pd.DataFrame(two_team_combos).to_csv(f'../Data/Picks/combos_2_TEAM_WEEK{week}.csv', index=False)
    pd.DataFrame(three_team_combos).to_csv(f'../Data/Picks/combos_3_TEAM_WEEK{week}.csv', index=False)
    pd.DataFrame(four_team_combos).to_csv(f'../Data/Picks/combos_4_TEAM_WEEK{week}.csv', index=False)
