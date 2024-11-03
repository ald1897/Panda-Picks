# import pandas as pd
# import sqlite3
#
# def calculate_winnings(bet_amount, odds):
#     if odds > 0:
#         profit = bet_amount * (odds / 100)
#     else:
#         profit = bet_amount / (abs(odds) / 100)
#     total_payout = bet_amount + profit
#     return total_payout
#
# def backtest():
#     weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7', 'WEEK8']
#     final_results = pd.DataFrame()
#     cumulative_profit = 0
#     total_spread_bets = 0
#     total_spread_wins = 0
#     total_ml_bets = 0
#     total_ml_wins = 0
#
#     weekly_stats = []
#
#     conn = sqlite3.connect('db/nfl_data.db')
#     cursor = conn.cursor()
#
#     for week in weeks:
#         # Query the spread data from the database
#         df = pd.read_sql_query("SELECT * FROM spreads", conn)
#         # print("DF",df)
#
#
#         # Query the picks from the database
#         picks_df = pd.read_sql_query(f"SELECT * FROM picks WHERE WEEK = '{week}'", conn)
#         # print("Picks DF",picks_df)
#
#         # Merge the DataFrames on WEEK and Home Team
#         merged_df = pd.merge(picks_df, df, left_on=['WEEK', 'Home_Team', 'Away_Team'],
#                              right_on=['WEEK', 'Home_Team', 'Away_Team'])
#         pd.set_option('display.max_rows', 200)
#         pd.set_option('display.max_columns', 200)
#
#         # Check if Home_Line_Close_y and Away_Line_Close_y are present, if so, drop the _y columns and rename the _x columns
#         if 'Home_Line_Close_y' in merged_df.columns:
#             merged_df = merged_df.drop(columns=['Home_Line_Close_y', 'Away_Line_Close_y'])
#             merged_df = merged_df.rename(columns={'Home_Line_Close_x': 'Home_Line_Close', 'Away_Line_Close_x': 'Away_Line_Close'})
#
#         # print("Merged DF", merged_df)
#
#         def check_pick(row):
#             bet_amount = 5  # Example bet amount
#             odds = -110  # Fixed odds for this calculation
#             if row['Game_Pick'] == row['Home_Team']:
#                 correct = row['Home_Score'] + row['Home_Line_Close'] > row['Away_Score']
#                 # print("Home:", row['Home_Score'] + row['Home_Line_Close'])
#             else:
#                 correct = row['Away_Score'] + row['Away_Line_Close'] > row['Home_Score']
#                 # print("Away:", row['Away_Score'] + row['Away_Line_Close'])
#
#             winnings = calculate_winnings(bet_amount, odds) if correct else 0
#             # print("Winnings:", winnings)
#             # print("Correct:", correct)
#             return correct, winnings
#
#
#         # Determine if the team won and calculate ML winnings
#         def check_win_and_calculate_winnings(row):
#             bet_amount = 5  # Example bet amount
#             if row['Home_Score'] > row['Away_Score']:
#                 winner = row['Home_Team']
#                 winnings = calculate_winnings(bet_amount, row['Home_Odds_Close']) if row['Game_Pick'] == row['Home_Team'] else 0
#             else:
#                 winner = row['Away_Team']
#                 winnings = calculate_winnings(bet_amount, row['Away_Odds_Close']) if row['Game_Pick'] == row['Away_Team'] else 0
#             return winner, winnings
#
#         # print(merged_df)
#         # Ensure check_pick returns exactly two values
#         merged_df[['ATS_Pick_Correct', 'ATS_Winnings']] = merged_df.apply(lambda row: pd.Series(check_pick(row)),
#                                                                               axis=1)
#
#         merged_df[['Winner', 'ML_Winnings']] = merged_df.apply(lambda row: pd.Series(check_win_and_calculate_winnings(row)), axis=1)
#         merged_df['Winner_Pick_Correct'] = merged_df['Winner'] == merged_df['Game_Pick']
#
#         # Format the Winnings columns to 2 decimal places and as currency
#         merged_df['ATS_Winnings'] = merged_df['ATS_Winnings'].apply(lambda x: f"${x:,.2f}")
#         merged_df['ML_Winnings'] = merged_df['ML_Winnings'].apply(lambda x: f"${x:,.2f}")
#
#         # Save merged df into the db
#         merged_df.to_sql('picks_results', conn, if_exists='append', index=False)
#
#         # Calculate total amount wagered and total profit
#         total_wagered = merged_df.shape[0] * 10  # Assuming each bet is $10
#         total_profit = merged_df['ATS_Winnings'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum() + \
#                        merged_df['ML_Winnings'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum() - total_wagered
#
#         # Calculate win percentages
#         spread_bets = merged_df.shape[0]
#         spread_wins = merged_df['ATS_Pick_Correct'].sum()
#         ml_bets = merged_df.shape[0]
#         ml_wins = merged_df['Winner_Pick_Correct'].sum()
#
#         spread_win_percentage = (spread_wins / spread_bets) * 100
#         ml_win_percentage = (ml_wins / ml_bets) * 100
#
#         # Append results to final DataFrame
#         merged_df['Total_Amount_Wagered'] = total_wagered
#         merged_df['Total_Profit'] = total_profit
#         final_results = pd.concat([final_results, merged_df])
#
#         # Update cumulative profit and win counts
#         cumulative_profit += total_profit
#         total_spread_bets += spread_bets
#         total_spread_wins += spread_wins
#         total_ml_bets += ml_bets
#         total_ml_wins += ml_wins
#
#         # Save weekly stats
#         weekly_stats.append({
#             'WEEK': week,
#             'total_wagered': total_wagered,
#             'total_spread_wins': spread_wins,
#             'total_spread_bets': spread_bets,
#             'total_ml_wins': ml_wins,
#             'total_ml_bets': ml_bets,
#             'total_profit': total_profit,
#             'spread_win_percentage': spread_win_percentage,
#             'ml_win_percentage': ml_win_percentage,
#             'perfect_weeks': 1 if spread_wins == spread_bets and ml_wins == ml_bets else 0
#         })
#
#     # Save weekly stats to the database
#     weekly_stats_df = pd.DataFrame(weekly_stats)
#     weekly_stats_df.to_sql('backtest_results', conn, if_exists='replace', index=False)
#
#     # Calculate overall win percentages
#     overall_spread_win_percentage = (total_spread_wins / total_spread_bets) * 100
#     overall_ml_win_percentage = (total_ml_wins / total_ml_bets) * 100
#
#     # Print the cumulative profit and overall win percentages
#     print(f"Cumulative Profit over all weeks: ${cumulative_profit:,.2f}")
#     print(f"Overall Spread Win Percentage: {overall_spread_win_percentage:.2f}%")
#     print(f"Overall Money Line Win Percentage: {overall_ml_win_percentage:.2f}%")
#
#     conn.close()
#
# if __name__ == "__main__":
import pandas as pd
import sqlite3
from itertools import combinations
import logging


def calculate_winnings(bet_amount, odds):
    if odds > 0:
        profit = bet_amount * (odds / 100)
    else:
        profit = bet_amount / (abs(odds) / 100)
    total_payout = bet_amount + profit
    return total_payout

# Add some logging to the adjust spread function
def adjust_spread(row, teaser_points=6):
    print(f"Adjusting spread for {row['Home_Team']} vs {row['Away_Team']}")
    if row['Home_Line_Close'] < 0:
        print(f"Adjusting Home Line Close: {row['Home_Line_Close']} by {teaser_points}")
        row['Home_Line_Close'] += teaser_points
        print(f'New Home Line Close: {row["Home_Line_Close"]}')
    else:
        print(f"Adjusting Home Line Close: {row['Home_Line_Close']} by {teaser_points}")
        row['Home_Line_Close'] -= teaser_points
        print(f'New Home Line Close: {row["Home_Line_Close"]}')

    print(f"Adjusting spread for {row['Home_Team']} vs {row['Away_Team']}")
    if row['Away_Line_Close'] < 0:
        print(f"Adjusting Away Line Close: {row['Away_Line_Close']} by {teaser_points}")
        row['Away_Line_Close'] += teaser_points
        print(f'New Away Line Close: {row["Away_Line_Close"]}')
    else:
        print(f"Adjusting Away Line Close: {row['Away_Line_Close']} by {teaser_points}")
        row['Away_Line_Close'] -= teaser_points
        print(f'New Away Line Close: {row["Away_Line_Close"]}')
    return row


def check_teaser_pick(row, team):
    print(f"Checking teaser pick for {team}")
    if team == row['Home_Team']:
        print(f"Checking if {row['Home_Score']} + {row['Home_Line_Close']} > {row['Away_Score']}")
        print(row['Home_Score'] + row['Home_Line_Close'] > row['Away_Score'])
        return row['Home_Score'] + row['Home_Line_Close'] > row['Away_Score']
    else:
        print(f"Checking if {row['Away_Score']} + {row['Away_Line_Close']} > {row['Home_Score']}")
        print(row['Away_Score'] + row['Away_Line_Close'] > row['Home_Score'])
        return row['Away_Score'] + row['Away_Line_Close'] > row['Home_Score']


def backtest():
    # weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7', 'WEEK8']
    weeks = ['WEEK6']
    final_results = pd.DataFrame()

    cumulative_profit = 0

    conn = sqlite3.connect('db/nfl_data.db')
    cursor = conn.cursor()

    for week in weeks:
        # Query the spread data from the database
        df = pd.read_sql_query("SELECT * FROM spreads", conn)

        # Query the picks from the database
        picks_df = pd.read_sql_query(f"SELECT * FROM picks WHERE WEEK = '{week}'", conn)

        # Merge the DataFrames on WEEK and Home Team
        merged_df = pd.merge(picks_df, df, left_on=['WEEK', 'Home_Team', 'Away_Team'],
                             right_on=['WEEK', 'Home_Team', 'Away_Team'])
        pd.set_option('display.max_rows', 200)
        pd.set_option('display.max_columns', 200)

        # Check if Home_Line_Close_y and Away_Line_Close_y are present, if so, drop the _y columns and rename the _x columns
        if 'Home_Line_Close_y' in merged_df.columns:
            merged_df = merged_df.drop(columns=['Home_Line_Close_y', 'Away_Line_Close_y'])
            merged_df = merged_df.rename(
                columns={'Home_Line_Close_x': 'Home_Line_Close', 'Away_Line_Close_x': 'Away_Line_Close'})

        # Teaser Strategy Implementation
        merged_df = merged_df.apply(adjust_spread, axis=1)
        teams = merged_df['Game_Pick'].unique()

        two_team_combos = list(combinations(teams, 2))
        three_team_combos = list(combinations(teams, 3))
        four_team_combos = list(combinations(teams, 4))

        def calculate_teaser_winnings(combo, odds):
            bet_amount = 5
            correct = all(check_teaser_pick(merged_df[merged_df['Game_Pick'] == team].iloc[0], team) for team in combo)
            return calculate_winnings(bet_amount, odds) if correct else 0

        teaser_results = []
        for combo in two_team_combos:
            winnings = calculate_teaser_winnings(combo, -135)
            teaser_results.append({'Combo': combo, 'Winnings': winnings, 'Type': '2-Team'})
        for combo in three_team_combos:
            winnings = calculate_teaser_winnings(combo, 140)
            teaser_results.append({'Combo': combo, 'Winnings': winnings, 'Type': '3-Team'})
        for combo in four_team_combos:
            winnings = calculate_teaser_winnings(combo, 240)
            teaser_results.append({'Combo': combo, 'Winnings': winnings, 'Type': '4-Team'})


        teaser_df = pd.DataFrame(teaser_results)
        teaser_df['WEEK'] = week
        total_teaser_wagered = len(teaser_results) * 5
        total_teaser_profit = teaser_df['Winnings'].sum() - total_teaser_wagered

        teaser_df['Total_Amount_Wagered'] = total_teaser_wagered
        teaser_df['Total_Profit'] = total_teaser_profit
        final_results = pd.concat([final_results, teaser_df])

        cumulative_profit += total_teaser_profit



    final_results['Winnings'] = final_results['Winnings'].apply(lambda x: f"${x:,.2f}")
    final_results['Total_Profit'] = final_results['Total_Profit'].apply(lambda x: f"${x:,.2f}")

    print(final_results.head(50))
    final_results.to_sql('teaser_results', conn, if_exists='replace', index=False)

    print(f"Cumulative Profit over all weeks: ${cumulative_profit:,.2f}")

    conn.close()


if __name__ == "__main__":
    backtest()