import pandas as pd

def calculate_winnings(bet_amount, odds):
    if odds > 0:
        profit = bet_amount * (odds / 100)
    else:
        profit = bet_amount / (abs(odds) / 100)
    total_payout = bet_amount + profit
    return total_payout

def backtest():
    weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7']
    final_results = pd.DataFrame()
    cumulative_profit = 0
    total_spread_bets = 0
    total_spread_wins = 0
    total_ml_bets = 0
    total_ml_wins = 0

    for week in weeks:
        # Read the spread data from the CSV file
        df = pd.read_csv('nflSpreads.csv')

        # Read the picks from the CSV file
        picks_df = pd.read_csv(f'Data/Picks/{week}.csv')

        # Merge the DataFrames on WEEK and Home Team
        merged_df = pd.merge(picks_df, df, left_on=['WEEK', 'Home Team', 'Away Team'],
                             right_on=['WEEK', 'Home Team', 'Away Team'])
        pd.set_option('display.max_rows', 200)
        pd.set_option('display.max_columns', 200)

        # Determine if the pick was correct and calculate wager and profit
        def check_pick(row):
            bet_amount = 10  # Example bet amount
            odds = -110  # Fixed odds for this calculation
            if row['Game Pick'] == row['Home Team']:
                correct = row['Home Score'] + row['Home Line Close'] > row['Away Score']
            else:
                correct = row['Away Score'] + row['Away Line Close'] > row['Home Score']

            winnings = calculate_winnings(bet_amount, odds) if correct else 0
            return correct, winnings

        # Determine if the team won and calculate ML winnings
        def check_win_and_calculate_winnings(row):
            bet_amount = 10  # Example bet amount
            if row['Home Score'] > row['Away Score']:
                winner = row['Home Team']
                winnings = calculate_winnings(bet_amount, row['Home Odds Close']) if row['Game Pick'] == row[
                    'Home Team'] else 0
            else:
                winner = row['Away Team']
                winnings = calculate_winnings(bet_amount, row['Away Odds Close']) if row['Game Pick'] == row[
                    'Away Team'] else 0
            return winner, winnings

        merged_df[['ATS Pick Correct', 'ATS Winnings']] = merged_df.apply(lambda row: pd.Series(check_pick(row)), axis=1)
        merged_df[['Winner', 'ML Winnings']] = merged_df.apply(lambda row: pd.Series(check_win_and_calculate_winnings(row)),
                                                               axis=1)
        merged_df['Winner Pick Correct'] = merged_df['Winner'] == merged_df['Game Pick']

        # Format the Winnings columns to 2 decimal places and as currency
        merged_df['ATS Winnings'] = merged_df['ATS Winnings'].apply(lambda x: f"${x:,.2f}")
        merged_df['ML Winnings'] = merged_df['ML Winnings'].apply(lambda x: f"${x:,.2f}")

        # Calculate total amount wagered and total profit
        total_wagered = merged_df.shape[0] * 20  # Assuming each bet is $100
        total_profit = merged_df['ATS Winnings'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum() + \
                       merged_df['ML Winnings'].apply(
                           lambda x: float(x.replace('$', '').replace(',', ''))).sum() - total_wagered

        # Calculate win percentages
        spread_bets = merged_df.shape[0]
        spread_wins = merged_df['ATS Pick Correct'].sum()
        ml_bets = merged_df.shape[0]
        ml_wins = merged_df['Winner Pick Correct'].sum()

        spread_win_percentage = (spread_wins / spread_bets) * 100
        ml_win_percentage = (ml_wins / ml_bets) * 100

        # Append results to final DataFrame
        merged_df['Total Amount Wagered'] = total_wagered
        merged_df['Total Profit'] = total_profit
        final_results = pd.concat([final_results, merged_df])

        # Update cumulative profit and win counts
        cumulative_profit += total_profit
        total_spread_bets += spread_bets
        total_spread_wins += spread_wins
        total_ml_bets += ml_bets
        total_ml_wins += ml_wins

        # Print the results for the current week
        print(f"Results for {week}:")
        print(merged_df[['Home Team', 'Away Team','Game Pick', 'Winner', 'ATS Pick Correct', 'Winner Pick Correct', 'ATS Winnings','ML Winnings', 'Total Amount Wagered', 'Total Profit']])
        print(f"Total Amount Wagered: ${total_wagered:,.2f}")
        print(f"Total Profit: ${total_profit:,.2f}")
        print(f"Spread Win Percentage: {spread_win_percentage:.2f}%")
        print(f"Money Line Win Percentage: {ml_win_percentage:.2f}%")
        print("\n")

    # Calculate overall win percentages
    overall_spread_win_percentage = (total_spread_wins / total_spread_bets) * 100
    overall_ml_win_percentage = (total_ml_wins / total_ml_bets) * 100

    # Print the cumulative profit and overall win percentages
    print(f"Cumulative Profit over all weeks: ${cumulative_profit:,.2f}")
    print(f"Overall Spread Win Percentage: {overall_spread_win_percentage:.2f}%")
    print(f"Overall Money Line Win Percentage: {overall_ml_win_percentage:.2f}%")

if __name__ == "__main__":
    backtest()