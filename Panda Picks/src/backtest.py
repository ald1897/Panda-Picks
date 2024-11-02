# # import pandas as pd
# #
# # def calculate_winnings(bet_amount, odds):
# #     if odds > 0:
# #         profit = bet_amount * (odds / 100)
# #     else:
# #         profit = bet_amount / (abs(odds) / 100)
# #     total_payout = bet_amount + profit
# #     return total_payout
# #
# # def backtest():
# #     weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7', 'WEEK8']
# #     final_results = pd.DataFrame()
# #     cumulative_profit = 0
# #     total_spread_bets = 0
# #     total_spread_wins = 0
# #     total_ml_bets = 0
# #     total_ml_wins = 0
# #
# #     weekly_stats = []
# #
# #     for week in weeks:
# #         # Read the spread data from the CSV file
# #         df = pd.read_csv(r"../Data/Spreads/nflSpreads.csv")
# #
# #         # Read the picks from the CSV file
# #         picks_df = pd.read_csv(f'../Data/Picks/{week}.csv')
# #
# #         # Merge the DataFrames on WEEK and Home Team
# #         merged_df = pd.merge(picks_df, df, left_on=['WEEK', 'Home Team', 'Away Team'],
# #                              right_on=['WEEK', 'Home Team', 'Away Team'])
# #         pd.set_option('display.max_rows', 200)
# #         pd.set_option('display.max_columns', 200)
# #
# #         # Determine if the pick was correct and calculate wager and profit
# #         def check_pick(row):
# #             bet_amount = 5  # Example bet amount
# #             odds = -110  # Fixed odds for this calculation
# #             if row['Game Pick'] == row['Home Team']:
# #                 correct = row['Home Score'] + row['Home Line Close'] > row['Away Score']
# #             else:
# #                 correct = row['Away Score'] + row['Away Line Close'] > row['Home Score']
# #
# #             winnings = calculate_winnings(bet_amount, odds) if correct else 0
# #             return correct, winnings
# #
# #         # Determine if the team won and calculate ML winnings
# #         def check_win_and_calculate_winnings(row):
# #             bet_amount = 5  # Example bet amount
# #             if row['Home Score'] > row['Away Score']:
# #                 winner = row['Home Team']
# #                 winnings = calculate_winnings(bet_amount, row['Home Odds Close']) if row['Game Pick'] == row['Home Team'] else 0
# #             else:
# #                 winner = row['Away Team']
# #                 winnings = calculate_winnings(bet_amount, row['Away Odds Close']) if row['Game Pick'] == row['Away Team'] else 0
# #             return winner, winnings
# #
# #         merged_df[['ATS Pick Correct', 'ATS Winnings']] = merged_df.apply(lambda row: pd.Series(check_pick(row)), axis=1)
# #         merged_df[['Winner', 'ML Winnings']] = merged_df.apply(lambda row: pd.Series(check_win_and_calculate_winnings(row)), axis=1)
# #         merged_df['Winner Pick Correct'] = merged_df['Winner'] == merged_df['Game Pick']
# #
# #         # Format the Winnings columns to 2 decimal places and as currency
# #         merged_df['ATS Winnings'] = merged_df['ATS Winnings'].apply(lambda x: f"${x:,.2f}")
# #         merged_df['ML Winnings'] = merged_df['ML Winnings'].apply(lambda x: f"${x:,.2f}")
# #
# #         # put merged df into a csv
# #         merged_df.to_csv(f'../Data/Picks/Picks_Results_{week}.csv', index=False)
# #
# #         # Calculate total amount wagered and total profit
# #         total_wagered = merged_df.shape[0] * 10  # Assuming each bet is $10
# #         total_profit = merged_df['ATS Winnings'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum() + \
# #                        merged_df['ML Winnings'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum() - total_wagered
# #
# #         # Calculate win percentages
# #         spread_bets = merged_df.shape[0]
# #         spread_wins = merged_df['ATS Pick Correct'].sum()
# #         ml_bets = merged_df.shape[0]
# #         ml_wins = merged_df['Winner Pick Correct'].sum()
# #
# #         spread_win_percentage = (spread_wins / spread_bets) * 100
# #         ml_win_percentage = (ml_wins / ml_bets) * 100
# #
# #         # Append results to final DataFrame
# #         merged_df['Total Amount Wagered'] = total_wagered
# #         merged_df['Total Profit'] = total_profit
# #         final_results = pd.concat([final_results, merged_df])
# #
# #         # Update cumulative profit and win counts
# #         cumulative_profit += total_profit
# #         total_spread_bets += spread_bets
# #         total_spread_wins += spread_wins
# #         total_ml_bets += ml_bets
# #         total_ml_wins += ml_wins
# #
# #         # Save weekly stats
# #         weekly_stats.append({
# #             'week': week,
# #             'total_wagered': total_wagered,
# #             'total_spread_wins': spread_wins,
# #             'total_spread_bets': spread_bets,
# #             'total_ml_wins': ml_wins,
# #             'total_ml_bets': ml_bets,
# #             'total_profit': total_profit,
# #             'spread_win_percentage': spread_win_percentage,
# #             'ml_win_percentage': ml_win_percentage,
# #             'perfect_weeks': 1 if spread_wins == spread_bets and ml_wins == ml_bets else 0
# #         })
# #
# #     # Save weekly stats to a CSV file
# #     weekly_stats_df = pd.DataFrame(weekly_stats)
# #     weekly_stats_df.to_csv('../Data/WeeklyStats/weekly_stats.csv', index=False)
# #
# #     # Calculate overall win percentages
# #     overall_spread_win_percentage = (total_spread_wins / total_spread_bets) * 100
# #     overall_ml_win_percentage = (total_ml_wins / total_ml_bets) * 100
# #
# #     # Print the cumulative profit and overall win percentages
# #     print(f"Cumulative Profit over all weeks: ${cumulative_profit:,.2f}")
# #     print(f"Overall Spread Win Percentage: {overall_spread_win_percentage:.2f}%")
# #     print(f"Overall Money Line Win Percentage: {overall_ml_win_percentage:.2f}%")
# #
# # if __name__ == "__main__":
# #     backtest()
#
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
#     conn = sqlite3.connect('../src/nfl_data.db')
#
#     for week in weeks:
#         # Query the spread data from the database
#         df = pd.read_sql_query("SELECT * FROM spreads", conn)
#
#         # Query the picks from the database
#         picks_df = pd.read_sql_query(f"SELECT * FROM picks WHERE WEEK = '{week}'", conn)
#
#         # Merge the DataFrames on WEEK and Home Team
#         merged_df = pd.merge(picks_df, df, left_on=['WEEK', 'Home_Team', 'Away_Team'],
#                              right_on=['WEEK', 'Home_Team', 'Away_Team'])
#         pd.set_option('display.max_rows', 200)
#         pd.set_option('display.max_columns', 200)
#
#         # Determine if the pick was correct and calculate wager and profit
#         def check_pick(row):
#             bet_amount = 5  # Example bet amount
#             odds = -110  # Fixed odds for this calculation
#             if row['Game_Pick'] == row['Home_Team']:
#                 correct = row['Home_Score'] + row['Home_Line_Close'] > row['Away_Score']
#             else:
#                 correct = row['Away_Score'] + row['Away_Line_Close'] > row['Home_Score']
#
#             winnings = calculate_winnings(bet_amount, odds) if correct else 0
#             return correct, winnings
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
#         merged_df[['ATS_Pick_Correct', 'ATS_Winnings']] = merged_df.apply(lambda row: pd.Series(check_pick(row)), axis=1)
#         merged_df[['Winner', 'ML_Winnings']] = merged_df.apply(lambda row: pd.Series(check_win_and_calculate_winnings(row)), axis=1)
#         merged_df['Winner_Pick_Correct'] = merged_df['Winner'] == merged_df['Game_Pick']
#
#         # Format the Winnings columns to 2 decimal places and as currency
#         merged_df['ATS_Winnings'] = merged_df['ATS_Winnings'].apply(lambda x: f"${x:,.2f}")
#         merged_df['ML_Winnings'] = merged_df['ML_Winnings'].apply(lambda x: f"${x:,.2f}")
#
#         # Save merged df into a CSV
#         merged_df.to_csv(f'../Data/Picks/Picks_Results_{week}.csv', index=False)
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
#             'week': week,
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
#     # Save weekly stats to a CSV file
#     weekly_stats_df = pd.DataFrame(weekly_stats)
#     weekly_stats_df.to_csv('../Data/WeeklyStats/weekly_stats.csv', index=False)
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
#     backtest()

import pandas as pd
import sqlite3

def calculate_winnings(bet_amount, odds):
    if odds > 0:
        profit = bet_amount * (odds / 100)
    else:
        profit = bet_amount / (abs(odds) / 100)
    total_payout = bet_amount + profit
    return total_payout

def backtest():
    weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7', 'WEEK8']
    final_results = pd.DataFrame()
    cumulative_profit = 0
    total_spread_bets = 0
    total_spread_wins = 0
    total_ml_bets = 0
    total_ml_wins = 0

    weekly_stats = []

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

        # Determine if the pick was correct and calculate wager and profit
        def check_pick(row):
            bet_amount = 5  # Example bet amount
            odds = -110  # Fixed odds for this calculation
            if row['Game_Pick'] == row['Home_Team']:
                correct = row['Home_Score'] + row['Home_Line_Close'] > row['Away_Score']
            else:
                correct = row['Away_Score'] + row['Away_Line_Close'] > row['Home_Score']

            winnings = calculate_winnings(bet_amount, odds) if correct else 0
            return correct, winnings

        # Determine if the team won and calculate ML winnings
        def check_win_and_calculate_winnings(row):
            bet_amount = 5  # Example bet amount
            if row['Home_Score'] > row['Away_Score']:
                winner = row['Home_Team']
                winnings = calculate_winnings(bet_amount, row['Home_Odds_Close']) if row['Game_Pick'] == row['Home_Team'] else 0
            else:
                winner = row['Away_Team']
                winnings = calculate_winnings(bet_amount, row['Away_Odds_Close']) if row['Game_Pick'] == row['Away_Team'] else 0
            return winner, winnings

        merged_df[['ATS_Pick_Correct', 'ATS_Winnings']] = merged_df.apply(lambda row: pd.Series(check_pick(row)), axis=1)
        merged_df[['Winner', 'ML_Winnings']] = merged_df.apply(lambda row: pd.Series(check_win_and_calculate_winnings(row)), axis=1)
        merged_df['Winner_Pick_Correct'] = merged_df['Winner'] == merged_df['Game_Pick']

        # Format the Winnings columns to 2 decimal places and as currency
        merged_df['ATS_Winnings'] = merged_df['ATS_Winnings'].apply(lambda x: f"${x:,.2f}")
        merged_df['ML_Winnings'] = merged_df['ML_Winnings'].apply(lambda x: f"${x:,.2f}")


        # Save merged df into the db
        merged_df.to_sql('picks_results', conn, if_exists='append', index=False)
        # merged_df.to_csv(f'../Data/Picks/Picks_Results_{week}.csv', index=False)

        # Calculate total amount wagered and total profit
        total_wagered = merged_df.shape[0] * 10  # Assuming each bet is $10
        total_profit = merged_df['ATS_Winnings'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum() + \
                       merged_df['ML_Winnings'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum() - total_wagered

        # Calculate win percentages
        spread_bets = merged_df.shape[0]
        spread_wins = merged_df['ATS_Pick_Correct'].sum()
        ml_bets = merged_df.shape[0]
        ml_wins = merged_df['Winner_Pick_Correct'].sum()

        spread_win_percentage = (spread_wins / spread_bets) * 100
        ml_win_percentage = (ml_wins / ml_bets) * 100

        # Append results to final DataFrame
        merged_df['Total_Amount_Wagered'] = total_wagered
        merged_df['Total_Profit'] = total_profit
        final_results = pd.concat([final_results, merged_df])

        # Update cumulative profit and win counts
        cumulative_profit += total_profit
        total_spread_bets += spread_bets
        total_spread_wins += spread_wins
        total_ml_bets += ml_bets
        total_ml_wins += ml_wins

        # Save weekly stats
        weekly_stats.append({
            'WEEK': week,
            'total_wagered': total_wagered,
            'total_spread_wins': spread_wins,
            'total_spread_bets': spread_bets,
            'total_ml_wins': ml_wins,
            'total_ml_bets': ml_bets,
            'total_profit': total_profit,
            'spread_win_percentage': spread_win_percentage,
            'ml_win_percentage': ml_win_percentage,
            'perfect_weeks': 1 if spread_wins == spread_bets and ml_wins == ml_bets else 0
        })

    # Save weekly stats to the database
    weekly_stats_df = pd.DataFrame(weekly_stats)
    weekly_stats_df.to_sql('backtest_results', conn, if_exists='append', index=False)

    # Calculate overall win percentages
    overall_spread_win_percentage = (total_spread_wins / total_spread_bets) * 100
    overall_ml_win_percentage = (total_ml_wins / total_ml_bets) * 100

    # Print the cumulative profit and overall win percentages
    print(f"Cumulative Profit over all weeks: ${cumulative_profit:,.2f}")
    print(f"Overall Spread Win Percentage: {overall_spread_win_percentage:.2f}%")
    print(f"Overall Money Line Win Percentage: {overall_ml_win_percentage:.2f}%")

    conn.close()

if __name__ == "__main__":
    backtest()