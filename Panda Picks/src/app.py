import pandas as pd
import streamlit as st
import logging
import altair as alt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variable to store overall statistics
overall_stats = {
    'cumulative_profit': 0,
    'total_spread_bets': 0,
    'total_spread_wins': 0,
    'total_ml_bets': 0,
    'total_ml_wins': 0,
    'weekly_profits': [],
    'total_amount_wagered': 0,
    'rolling_balance': 120,  # Starting bankroll
    'banked_profit': 0,
    'total_wins': 0,
    'total_losses': 0,
    'perfect_weeks': 0,
    'weekly_wagered': []  # Store weekly amount wagered
}


def display_predictions():
    st.header("Predictions for Future Matchups")
    weeks = ['WEEK9', 'WEEK10', 'WEEK11', 'WEEK12', 'WEEK13', 'WEEK14', 'WEEK15', 'WEEK16', 'WEEK17', 'WEEK18']
    selected_week = st.selectbox("Select Week", weeks)

    try:
        predictions_df = pd.read_csv(f'../Data/Picks/{selected_week}.csv')
        predictions_df = predictions_df[
            ['Home Team', 'Away Team', 'Home Spread', 'Overall Adv', 'Offense Adv', 'Defense Adv', 'Game Pick']]

        # Take absolute values of the relevant columns
        predictions_df['Overall Adv'] = predictions_df['Overall Adv'].abs()
        predictions_df['Offense Adv'] = predictions_df['Offense Adv'].abs()
        predictions_df['Defense Adv'] = predictions_df['Defense Adv'].abs()

        st.subheader(f"Predictions for {selected_week}")

        # Display the table with better styling
        st.dataframe(predictions_df.style.format({
            'Home Spread': '{:.1f}',
            'Away Spread': '{:.1f}'
        }))

        # Create a chart to visualize the predictions
        chart = alt.Chart(predictions_df).mark_bar().encode(
            x='Home Team',
            y='Overall Adv',
            color='Game Pick',
            tooltip=['Home Team', 'Away Team', 'Overall Adv', 'Game Pick']
        ).properties(
            width=600,
            height=400
        )

        st.altair_chart(chart)

    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
    except pd.errors.EmptyDataError as e:
        st.error(f"Empty data error: {e}")

def create_comparison_chart(home_team, away_team, grades_df):
    home_grades = grades_df[grades_df['TEAM'] == home_team].iloc[0]
    away_grades = grades_df[grades_df['TEAM'] == away_team].iloc[0]

    categories = ['OVR', 'OFF', 'PASS', 'RUN', 'RECV', 'PBLK', 'RBLK', 'DEF', 'RDEF', 'TACK', 'PRSH', 'COV']
    home_values = [home_grades[cat] for cat in categories]
    away_values = [away_grades[cat] for cat in categories]

    # Ensure all arrays are of the same length
    if len(categories) == len(home_values) == len(away_values):
        data = pd.DataFrame({
            'Category': categories * 2,
            'Team': [home_team] * len(categories) + [away_team] * len(categories),
            'Grade': home_values + away_values
        })

        chart = alt.Chart(data).mark_bar().encode(
            x=alt.X('Category:N', title='Category'),
            y=alt.Y('Grade:Q', title='Grade'),
            color='Team:N',
            xOffset='Team:N'
        ).properties(
            width=800,
            height=800
        )

        return chart
    else:
        raise ValueError("All arrays must be of the same length")

# def display_picks_data():
#     st.header("Picks Data")
#     weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7', 'WEEK8', 'WEEK9', 'WEEK10', 'WEEK11', 'WEEK12', 'WEEK13', 'WEEK14', 'WEEK15', 'WEEK16', 'WEEK17', 'WEEK18']
#     selected_week = st.selectbox("Select Week", weeks)
#
#     try:
#         picks_df = pd.read_csv(f'../Data/Picks/{selected_week}.csv')
#         st.subheader(f"Picks for {selected_week}")
#         st.table(picks_df)
#     except FileNotFoundError as e:
#         st.error(f"File not found: {e}")
#     except pd.errors.EmptyDataError as e:
#         st.error(f"Empty data error: {e}")

def calculate_winnings(bet_amount, odds):
    try:
        if odds > 0:
            profit = bet_amount * (odds / 100)
        else:
            profit = bet_amount / (abs(odds) / 100)
        total_payout = bet_amount + profit
        return total_payout
    except Exception as e:
        logging.error(f"Error calculating winnings: {e}")
        return 0

def process_week_data(week, bet_amount, bankroll):
    try:
        df = pd.read_csv('../Data/Spreads/nflSpreads.csv')
        picks_df = pd.read_csv(f'../Data/Picks/{week}.csv')
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        return None
    except pd.errors.EmptyDataError as e:
        logging.error(f"Empty data error: {e}")
        return None

    merged_df = pd.merge(picks_df, df, left_on=['WEEK', 'Home Team', 'Away Team'], right_on=['WEEK', 'Home Team', 'Away Team'])
    pd.set_option('display.max_rows', 200)
    pd.set_option('display.max_columns', 200)

    def check_pick(row):
        odds = -110
        if row['Game Pick'] == row['Home Team']:
            correct = row['Home Score'] + row['Home Line Close'] > row['Away Score']
        else:
            correct = row['Away Score'] + row['Away Line Close'] > row['Home Score']
        winnings = calculate_winnings(bet_amount, odds) if correct else 0
        return correct, winnings

    def check_win_and_calculate_winnings(row):
        if row['Home Score'] > row['Away Score']:
            winner = row['Home Team']
            winnings = calculate_winnings(bet_amount, row['Home Odds Close']) if row['Game Pick'] == row['Home Team'] else 0
        else:
            winner = row['Away Team']
            winnings = calculate_winnings(bet_amount, row['Away Odds Close']) if row['Game Pick'] == row['Away Team'] else 0
        return winner, winnings

    merged_df[['ATS Pick Correct', 'ATS Winnings']] = merged_df.apply(lambda row: pd.Series(check_pick(row)), axis=1)
    merged_df[['Winner', 'ML Winnings']] = merged_df.apply(lambda row: pd.Series(check_win_and_calculate_winnings(row)), axis=1)
    merged_df['Winner Pick Correct'] = merged_df['Winner'] == merged_df['Game Pick']
    merged_df['ATS Winnings'] = merged_df['ATS Winnings'].apply(lambda x: f"${x:,.2f}")
    merged_df['ML Winnings'] = merged_df['ML Winnings'].apply(lambda x: f"${x:,.2f}")

    total_wagered = merged_df.shape[0] * bet_amount * 2
    total_profit = merged_df['ATS Winnings'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum() + \
                   merged_df['ML Winnings'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum() - total_wagered

    spread_bets = merged_df.shape[0]
    spread_wins = merged_df['ATS Pick Correct'].sum()
    ml_bets = merged_df.shape[0]
    ml_wins = merged_df['Winner Pick Correct'].sum()

    spread_win_percentage = (spread_wins / spread_bets) * 100
    ml_win_percentage = (ml_wins / ml_bets) * 100

    # Update overall statistics
    overall_stats['total_spread_bets'] += spread_bets
    overall_stats['total_spread_wins'] += spread_wins
    overall_stats['total_ml_bets'] += ml_bets
    overall_stats['total_ml_wins'] += ml_wins
    overall_stats['total_amount_wagered'] += total_wagered

    # Update rolling balance and banked profit
    if total_profit < 0:
        overall_stats['rolling_balance'] += total_profit
    else:
        overall_stats['banked_profit'] += total_profit
        overall_stats['rolling_balance'] = bankroll

    overall_stats['cumulative_profit'] = overall_stats['banked_profit'] + overall_stats['rolling_balance'] - bankroll
    overall_stats['weekly_profits'].append(overall_stats['cumulative_profit'])
    overall_stats['weekly_wagered'].append(total_wagered)  # Store weekly amount wagered

    # Update win/loss statistics
    overall_stats['total_wins'] += spread_wins + ml_wins
    overall_stats['total_losses'] += (spread_bets - spread_wins) + (ml_bets - ml_wins)

    # Check for perfect week
    if spread_wins == spread_bets and ml_wins == ml_bets:
        overall_stats['perfect_weeks'] += 1

    return {
        'data': merged_df,
        'total_wagered': total_wagered,
        'total_profit': total_profit,
        'spread_win_percentage': spread_win_percentage,
        'ml_win_percentage': ml_win_percentage
    }

def display_matchup_info(matchup_data):
    logging.info(f"Displaying matchup information for {matchup_data['Home Team']} vs {matchup_data['Away Team']}")
    logging.info(f"Matchup data: {matchup_data}")
    st.subheader(f"Matchup: {matchup_data['Home Team']} vs {matchup_data['Away Team']}")
    st.write("### Game Details")
    st.write(f"**Home Team:** {matchup_data['Home Team']}")
    st.write(f"**Away Team:** {matchup_data['Away Team']}")
    st.write(f"**Game Pick:** {matchup_data['Game Pick']}")
    st.write(f"**Winner:** {matchup_data['Game Pick']}")
    st.write(f"**ATS Pick Correct:** {matchup_data['ATS Pick Correct']}")
    st.write(f"**Winner Pick Correct:** {matchup_data['Winner Pick Correct']}")
    st.write(f"**ATS Winnings:** {matchup_data['ATS Winnings']}")
    st.write(f"**ML Winnings:** {matchup_data['ML Winnings']}")
    st.write(f"**Home Score:** {matchup_data['Home Score']}")
    st.write(f"**Away Score:** {matchup_data['Away Score']}")
    st.write(f"**Home Line Close:** {matchup_data['Home Line Close']}")
    st.write(f"**Away Line Close:** {matchup_data['Away Line Close']}")
    st.write(f"**Home Odds Close:** {matchup_data['Home Odds Close']}")
    st.write(f"**Away Odds Close:** {matchup_data['Away Odds Close']}")

def display_picks_data():
    st.header("Picks Data")
    weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7', 'WEEK8', 'WEEK9', 'WEEK10', 'WEEK11', 'WEEK12', 'WEEK13', 'WEEK14', 'WEEK15', 'WEEK16', 'WEEK17', 'WEEK18']
    selected_week = st.selectbox("Select Week", weeks)

    try:
        picks_df = pd.read_csv(f'../Data/Picks/{selected_week}.csv')
        grades_df = pd.read_csv('../Data/Grades/TeamGrades.csv')
        st.subheader(f"Picks for {selected_week}")
        st.table(picks_df)

        # Add a dropdown menu to select a matchup
        matchups = picks_df[['Home Team', 'Away Team']].apply(lambda row: f"{row['Home Team']} vs {row['Away Team']}", axis=1)
        selected_matchup = st.selectbox("Select Matchup", matchups)

        # Display detailed matchup information and chart
        if selected_matchup:
            home_team, away_team = selected_matchup.split(" vs ")
            matchup_data = picks_df[(picks_df['Home Team'] == home_team) & (picks_df['Away Team'] == away_team)].iloc[0]
            st.altair_chart(create_comparison_chart(home_team, away_team, grades_df))

    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
    except pd.errors.EmptyDataError as e:
        st.error(f"Empty data error: {e}")

def display_week_stats(week_data, week):
    st.subheader(f"Results for {week}")
    st.table(week_data['data'][['Home Team', 'Away Team', 'Game Pick', 'Winner', 'ATS Pick Correct', 'Winner Pick Correct', 'ATS Winnings', 'ML Winnings']])

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Total Amount Wagered", value=f"${week_data['total_wagered']:,.2f}")
        st.metric(label="Total Profit", value=f"${week_data['total_profit']:,.2f}")
    with col2:
        st.metric(label="Spread Win Percentage", value=f"{week_data['spread_win_percentage']:.2f}%")
        st.metric(label="Money Line Win Percentage", value=f"{week_data['ml_win_percentage']:.2f}%")

    # # Add a dropdown menu to select a matchup
    # matchups = week_data['data'][['Home Team', 'Away Team']].apply(lambda row: f"{row['Home Team']} vs {row['Away Team']}", axis=1)
    # selected_matchup = st.selectbox("Select Matchup", matchups)
    #
    # # Display detailed matchup information
    # if selected_matchup:
    #     matchup_data = week_data['data'][matchups == selected_matchup].iloc[0]
    #     display_matchup_info(matchup_data)

def display_summary_stats():
    st.header("Summary Statistics")
    overall_spread_win_percentage = (overall_stats['total_spread_wins'] / overall_stats['total_spread_bets']) * 100 if overall_stats['total_spread_bets'] > 0 else 0
    overall_ml_win_percentage = (overall_stats['total_ml_wins'] / overall_stats['total_ml_bets']) * 100 if overall_stats['total_ml_bets'] > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Cumulative Profit", value=f"${overall_stats['cumulative_profit']:,.2f}")
        st.metric(label="Overall Spread Win Percentage", value=f"{overall_spread_win_percentage:.2f}%")
        st.metric(label="Total Wins", value=overall_stats['total_wins'])
    with col2:
        st.metric(label="Overall Money Line Win Percentage", value=f"{overall_ml_win_percentage:.2f}%")
        st.metric(label="Total Amount Wagered", value=f"${overall_stats['total_amount_wagered']:,.2f}")
        st.metric(label="Total Losses", value=overall_stats['total_losses'])
    with col3:
        st.metric(label="Rolling Balance", value=f"${overall_stats['rolling_balance']:,.2f}")
        st.metric(label="Banked Profit", value=f"${overall_stats['banked_profit']:,.2f}")
        st.metric(label="Perfect Weeks", value=overall_stats['perfect_weeks'])

    # Create a DataFrame for the combined chart
    chart_data = pd.DataFrame({
        'Week': list(range(1, len(overall_stats['weekly_profits']) + 1)),
        'Cumulative Profit': overall_stats['weekly_profits'],
        'Weekly Wagered': overall_stats['weekly_wagered']
    })

    # Create the combined chart using Altair with the same y-axis
    line1 = alt.Chart(chart_data).mark_line(color='blue').encode(
        x='Week',
        y='Cumulative Profit'
    )

    line2 = alt.Chart(chart_data).mark_line(color='orange').encode(
        x='Week',
        y='Weekly Wagered'
    )

    combined_chart = alt.layer(line1, line2).resolve_scale(
        y='shared'
    ).properties(
        width=600,
        height=400
    )

    st.altair_chart(combined_chart)


def main():
    st.title("NFL Betting Backtest Results")

    # Add input fields for bankroll and bet amount
    bankroll = st.sidebar.number_input("Starting Bankroll", value=120, step=10)
    bet_amount = st.sidebar.number_input("Bet Amount", value=10, step=1)

    # Update the global variable with the dynamic bankroll
    overall_stats['rolling_balance'] = bankroll

    pages = ["Week Stats", "Summary Stats", "Picks Data", "Predictions"]
    selected_page = st.sidebar.selectbox("Select Page", pages)

    if selected_page == "Week Stats":
        weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7', 'WEEK8']
        selected_week = st.selectbox("Select Week", weeks)
        week_data = process_week_data(selected_week, bet_amount, bankroll)
        if week_data:
            display_week_stats(week_data, selected_week)
    elif selected_page == "Summary Stats":
        # Process all weeks to update overall_stats
        weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7', 'WEEK8']
        for week in weeks:
            process_week_data(week, bet_amount, bankroll)
        display_summary_stats()
    elif selected_page == "Picks Data":
        display_picks_data()
    elif selected_page == "Predictions":
        display_predictions()

if __name__ == "__main__":
    main()