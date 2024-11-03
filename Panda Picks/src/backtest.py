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
    # print(f"Adjusting spread for {row['Home_Team']} vs {row['Away_Team']}")
    if row['Home_Line_Close'] < 0:
        # print(f"Adjusting Home Line Close: {row['Home_Line_Close']} by {teaser_points}")
        row['Home_Line_Close'] += teaser_points
        # print(f'New Home Line Close: {row["Home_Line_Close"]}')
    else:
        # print(f"Adjusting Home Line Close: {row['Home_Line_Close']} by {teaser_points}")
        row['Home_Line_Close'] += teaser_points
        # print(f'New Home Line Close: {row["Home_Line_Close"]}')

    # print(f"Adjusting spread for {row['Home_Team']} vs {row['Away_Team']}")
    if row['Away_Line_Close'] < 0:
        # print(f"Adjusting Away Line Close: {row['Away_Line_Close']} by {teaser_points}")
        row['Away_Line_Close'] += teaser_points
        # print(f'New Away Line Close: {row["Away_Line_Close"]}')
    else:
        # print(f"Adjusting Away Line Close: {row['Away_Line_Close']} by {teaser_points}")
        row['Away_Line_Close'] += teaser_points
        # print(f'New Away Line Close: {row["Away_Line_Close"]}')
    return row


def check_teaser_pick(row, team):
    # print(f"Checking teaser pick for {team}")
    if team == row['Home_Team']:
        # print(f"Checking if {row['Home_Score']} + {row['Home_Line_Close']} > {row['Away_Score']}")
        # print(row['Home_Score'] + row['Home_Line_Close'] > row['Away_Score'])
        return row['Home_Score'] + row['Home_Line_Close'] > row['Away_Score']
    else:
        # print(f"Checking if {row['Away_Score']} + {row['Away_Line_Close']} > {row['Home_Score']}")
        # print(row['Away_Score'] + row['Away_Line_Close'] > row['Home_Score'])
        return row['Away_Score'] + row['Away_Line_Close'] > row['Home_Score']


def backtest():
    weeks = [ 'WEEK1', 'WEEK2','WEEK3','WEEK4','WEEK5', 'WEEK6', 'WEEK7', 'WEEK8']
    # weeks = ['WEEK6']
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
        # teaser_df['Total_Winnings'] = teaser_df['Winnings'].sum()
        teaser_df['Winnings'] = teaser_df['Winnings'].apply(lambda x: f"${x:,.2f}")
        teaser_df['Total_Profit'] = teaser_df['Total_Profit'].apply(lambda x: f"${x:,.2f}")
        # teaser_df['Total_Winnings'] = teaser_df['Total_Winnings'].apply(lambda x: f"${x:,.2f}")

        # Concatenate the teaser_df to the final_results DataFrame
        final_results = pd.concat([final_results, teaser_df])
        # print(f"Results for {week}")
        # print(teaser_df)
        # print(final_results)
        cumulative_profit += total_teaser_profit

    # final_results.to_sql('teaser_results', conn, if_exists='replace', index=False)

    print(f"Total Amount Wagered: ${total_teaser_wagered:,.2f}")
    print(f"Cumulative Profit over all weeks: ${cumulative_profit:,.2f}")
    print(final_results.head(100))

    conn.close()


if __name__ == "__main__":
    backtest()