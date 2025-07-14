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

def adjust_spread(row, teaser_points=6):
    row['Home_Line_Close'] += teaser_points
    row['Away_Line_Close'] += teaser_points
    return row

def check_teaser_pick(row, team):
    if team == row['Home_Team']:
        return row['Home_Score'] + row['Home_Line_Close'] > row['Away_Score']
    else:
        return row['Away_Score'] + row['Away_Line_Close'] > row['Home_Score']

def backtest():
    weeks = ['WEEK1','WEEK2','WEEK3','WEEK4','WEEK5','WEEK6','WEEK7','WEEK8','WEEK9']
    final_results = pd.DataFrame()
    cumulative_profit = 0
    initial_balance = 500  # Starting balance
    current_balance = initial_balance

    conn = sqlite3.connect('nfl_data.db')
    cursor = conn.cursor()

    for week in weeks:
        df = pd.read_sql_query("SELECT * FROM spreads", conn)
        picks_df = pd.read_sql_query(f"SELECT * FROM picks WHERE WEEK = '{week}'", conn)
        merged_df = pd.merge(picks_df, df, left_on=['WEEK', 'Home_Team', 'Away_Team'],
                             right_on=['WEEK', 'Home_Team', 'Away_Team'])
        pd.set_option('display.max_rows', 200)
        pd.set_option('display.max_columns', 200)

        if 'Home_Line_Close_y' in merged_df.columns:
            merged_df = merged_df.drop(columns=['Home_Line_Close_y', 'Away_Line_Close_y'])
            merged_df = merged_df.rename(columns={'Home_Line_Close_x': 'Home_Line_Close', 'Away_Line_Close_x': 'Away_Line_Close'})

        merged_df = merged_df.apply(adjust_spread, axis=1)
        teams = merged_df['Game_Pick'].unique()
        logging.info(f'{week} backtest')
        logging.info(f"Teams: {teams}")

        merged_df['Winner'] = merged_df.apply(lambda x: x['Home_Team'] if x['Home_Score'] > x['Away_Score'] else x['Away_Team'], axis=1)
        merged_df['Correct_Pick'] = merged_df.apply(lambda x: x['Game_Pick'] == x['Winner'], axis=1)
        merged_df['Pick_Covered_Spread'] = merged_df.apply(lambda x: x['Game_Pick'] == x['Home_Team'] if x['Home_Score'] + x['Home_Line_Close'] > x['Away_Score'] else x['Game_Pick'] == x['Away_Team'], axis=1)

        two_team_combos = list(combinations(teams, 2))
        three_team_combos = list(combinations(teams, 3))
        four_team_combos = list(combinations(teams, 4))

        def calculate_teaser_winnings(combo, odds):
            bet_amount = 10
            correct = True
            for team in combo:
                team_row = merged_df[merged_df['Game_Pick'] == team]
                if team_row.empty:
                    correct = False
                    break
                correct = correct and check_teaser_pick(team_row.iloc[0], team)
            return calculate_winnings(bet_amount, odds) if correct else 0

        teaser_results = []
        for combo in two_team_combos:
            winnings = calculate_teaser_winnings(combo, -135)
            teaser_results.append({'Combo': str(combo), 'Winnings': winnings, 'Type': '2-Team'})
        for combo in three_team_combos:
            winnings = calculate_teaser_winnings(combo, 140)
            teaser_results.append({'Combo': str(combo), 'Winnings': winnings, 'Type': '3-Team'})
        for combo in four_team_combos:
            winnings = calculate_teaser_winnings(combo, 240)
            teaser_results.append({'Combo': str(combo), 'Winnings': winnings, 'Type': '4-Team'})

        teaser_df = pd.DataFrame(teaser_results)
        if teaser_df.empty:
            teaser_df = pd.DataFrame(columns=['Combo', 'Winnings', 'Type'])
            teaser_df['Combo'] = "N/A"
            teaser_df['Winnings'] = 0
            teaser_df['Type'] = "N/A"
            teaser_df['WEEK'] = week
            total_teaser_wagered = 0
            total_teaser_profit = 0
        else:
            teaser_df['WEEK'] = week
            total_teaser_wagered = len(teaser_results) * 10
            total_teaser_profit = teaser_df['Winnings'].sum() - total_teaser_wagered

        teaser_df['Total_Amount_Wagered'] = total_teaser_wagered
        teaser_df['Weekly_Profit'] = total_teaser_profit

        cumulative_profit += total_teaser_profit
        current_balance += total_teaser_profit
        teaser_df['Total_Profit_Over_All_Weeks'] = cumulative_profit
        teaser_df['Total_Balance'] = current_balance

        merged_df.to_sql('picks_results', conn, if_exists='append', index=False)
        teaser_df.to_sql('teaser_results', conn, if_exists='append', index=False)

    final_results = pd.read_sql_query("SELECT * FROM teaser_results", conn)
    final_results['Total_Profit'] = cumulative_profit
    final_results.to_sql('backtest_results', conn, if_exists='replace', index=False)
    print(final_results[['WEEK', 'Total_Amount_Wagered', 'Weekly_Profit', 'Total_Balance']])

    print(f"Max Weekly Wagered: ${final_results['Total_Amount_Wagered'].max()}")
    print(f"Cumulative Profit over all weeks: ${cumulative_profit:,.2f}")
    print(f"Final Balance: ${current_balance:,.2f}")

    # Calculate individual bet win percentage. A win is when winnings is > 0
    win_percentage = final_results[final_results['Winnings'] > 0].shape[0] / final_results.shape[0]
    print(f"Individual Bet Win Percentage: {win_percentage * 100:.2f}%")
    conn.close()

if __name__ == "__main__":
    backtest()