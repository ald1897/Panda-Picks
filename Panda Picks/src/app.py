import pandas as pd
import streamlit as st
import logging
import altair as alt
import sqlite3

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
        conn = sqlite3.connect('db/nfl_data.db')
        query = f'''
        SELECT Home_Team, Away_Team, home_spread, away_spread, overall_adv, offense_adv, defense_adv, off_comp_adv, def_comp_adv, game_pick
        FROM picks
        WHERE week = '{selected_week}'
        '''
        predictions_df = pd.read_sql(query, conn)
        conn.close()

        # Take absolute values of the relevant columns
        predictions_df['overall_adv'] = predictions_df['overall_adv']
        predictions_df['offense_adv'] = predictions_df['offense_adv']
        predictions_df['defense_adv'] = predictions_df['defense_adv']
        predictions_df['off_comp_adv'] = predictions_df['off_comp_adv']
        predictions_df['def_comp_adv'] = predictions_df['def_comp_adv']
        st.subheader(f"Predictions for {selected_week}")

        # Fill in spread columns with 0 if they are null
        predictions_df['home_spread'] = predictions_df['home_spread'].fillna(0)
        predictions_df['away_spread'] = predictions_df['away_spread'].fillna(0)

        # Define a function to apply styles
        def highlight_advantage(val):
            color = 'color: #80caf2' if val > 0 else 'color: lightcoral'
            return color

        def highlight_game_pick(row):
            if row['game_pick'] == row['Home_Team']:
                return ['color: #80caf2' if col == 'game_pick' else '' for col in row.index]
            elif row['game_pick'] == row['Away_Team']:
                return ['color: lightcoral' if col == 'game_pick' else '' for col in row.index]
            else:
                return ['' for col in row.index]

        # Apply the styles to the relevant columns
        styled_df = predictions_df.style.applymap(highlight_advantage, subset=['overall_adv', 'offense_adv', 'defense_adv', 'off_comp_adv', 'def_comp_adv'])
        styled_df = styled_df.apply(highlight_game_pick, axis=1)

        styled_df.format({
            'home_spread': '{:.1f}',
            'away_spread': '{:.1f}'
        })

        # Display the styled table
        st.table(styled_df)

        chart_df = predictions_df[['Home_Team', 'Away_Team', 'overall_adv', 'off_comp_adv', 'def_comp_adv', 'game_pick']]
        # Create columns for the charts
        col1, col2 = st.columns(2)

        with col1:
            # Create a chart to visualize the overall advantage predictions
            overall_chart = alt.Chart(chart_df).mark_bar().encode(
                x=alt.X('Home_Team:N', title='Home Team'),
                y=alt.Y('overall_adv:Q', title='Overall Advantage'),
                color=alt.Color('game_pick:N', title='Game Pick'),
                tooltip=['Home_Team:N', 'Away_Team:N', 'overall_adv:Q', 'game_pick:N']
            ).properties(
                height=600
            )

            st.altair_chart(overall_chart, use_container_width=True)

        with col2:
            # Create a bar chart to visualize the off_comp_adv and def_comp_adv predictions
            comp_adv_chart = alt.Chart(chart_df).transform_fold(
                ['off_comp_adv', 'def_comp_adv'],
                as_=['Metric', 'Value']
            ).mark_bar().encode(
                x=alt.X('Home_Team:N', title='Home Team'),
                y=alt.Y('Value:Q', title='Value'),
                color=alt.Color('Metric:N', title='Metric'),
                tooltip=['Home_Team:N', 'Away_Team:N', 'Metric:N', 'Value:Q', 'game_pick:N']
            ).properties(
                height=600
            )

            st.altair_chart(comp_adv_chart, use_container_width=True)

    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
    except pd.errors.EmptyDataError as e:
        st.error(f"Empty data error: {e}")

def display_picks_data():
    st.header("Picks Data")
    weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7', 'WEEK8', 'WEEK9', 'WEEK10', 'WEEK11', 'WEEK12', 'WEEK13', 'WEEK14', 'WEEK15', 'WEEK16', 'WEEK17', 'WEEK18']
    selected_week = st.selectbox("Select Week", weeks)

    try:
        picks_df = pd.read_csv(f'../Data/Picks/{selected_week}.csv')
        grades_df = pd.read_csv('../Data/Grades/TeamGrades.csv')
        st.subheader(f"Picks for {selected_week}")

        # Define a function to apply styles
        def highlight_advantage(val):
            color = 'color: #80caf2' if val > 0 else 'color: lightcoral'
            return color

        def highlight_game_pick(row):
            if row['Game Pick'] == row['Home Team']:
                return ['color: #80caf2' if col == 'Game Pick' else '' for col in row.index]
            elif row['Game Pick'] == row['Away Team']:
                return ['color: lightcoral' if col == 'Game Pick' else '' for col in row.index]
            else:
                return ['' for col in row.index]

        # Apply the styles to the relevant columns
        styled_df = picks_df.style.applymap(highlight_advantage, subset=['Overall Adv', 'Offense Adv', 'Defense Adv', 'Off Comp Adv', 'Def Comp Adv'])
        styled_df = styled_df.apply(highlight_game_pick, axis=1)

        styled_df.format({
            'Home Spread': '{:.1f}',
            'Away Spread': '{:.1f}'
        })

        # Display the styled table
        st.table(styled_df)

        # Add a dropdown menu to select a matchup
        matchups = picks_df[['Home Team', 'Away Team']].apply(lambda row: f"{row['Home Team']} vs {row['Away Team']}", axis=1)
        selected_matchup = st.selectbox("Select Matchup", matchups)

        # Display detailed matchup information and chart
        if selected_matchup:
            home_team, away_team = selected_matchup.split(" vs ")
            matchup_data = picks_df[(picks_df['Home Team'] == home_team) & (picks_df['Away Team'] == away_team)].iloc[0]
            st.altair_chart(create_comparison_chart(home_team, away_team, grades_df), use_container_width=True)

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
            height=600
        )

        return chart
    else:
        raise ValueError("All arrays must be of the same length")

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

def display_week_stats():
    st.header("Weekly Statistics")
    weeks = ['WEEK1', 'WEEK2', 'WEEK3', 'WEEK4', 'WEEK5', 'WEEK6', 'WEEK7', 'WEEK8', 'WEEK9', 'WEEK10', 'WEEK11', 'WEEK12', 'WEEK13', 'WEEK14', 'WEEK15', 'WEEK16', 'WEEK17', 'WEEK18']
    selected_week = st.selectbox("Select Week", weeks)

    try:
        # Read the picks data
        picks_df = pd.read_csv(f'../Data/Picks/{selected_week}.csv')

        # Read the results data
        results_df = pd.read_csv(f'../Data/Picks/Picks_Results_{selected_week}.csv')

        # Drop the duplicate columns from the results data compared to the pick_df except for Home Team and Away Team
        results_df = results_df.drop(columns=['WEEK','Home Spread', 'Away Spread', 'Game Pick', 'Overall Adv', 'Offense Adv', 'Defense Adv', 'Off Comp Adv', 'Def Comp Adv', 'Off Comp Adv_sig', 'Def Comp Adv_sig', 'Overall Adv_sig', 'Offense Adv_sig', 'Defense Adv_sig'])

        # Merge the picks data with the results data but do not duplicate columns only add new columns from results_df
        picks_df = pd.merge(picks_df, results_df, on=['Home Team', 'Away Team'], how='left')

        print(picks_df.columns)

        # Apply styles to the table
        def highlight_advantage(val):
            color = 'color: #80caf2' if val > 0 else 'color: lightcoral'
            return color

        display_list = ['Home Team', 'Away Team', 'Home Line Close', 'Home Odds Close', 'Game Pick', 'Winner', 'Overall Adv', 'Offense Adv', 'Defense Adv', 'Off Comp Adv', 'Def Comp Adv', 'ATS Pick Correct', 'Winner Pick Correct', 'ATS Winnings', 'ML Winnings']

        styled_picks_df = picks_df[display_list].style.applymap(highlight_advantage,
                                                                subset=['Overall Adv', 'Offense Adv', 'Defense Adv',
                                                                        'Off Comp Adv', 'Def Comp Adv'])

        styled_picks_df = styled_picks_df.format({
            'Home Spread': '{:.1f}',
            'Away Spread': '{:.1f}',
            'Home Line Close': '{:.1f}',
            'Home Odds Close': '{:.2f}',
            'ATS Pick Correct': lambda x: 'Yes' if x else 'No',
            'Winner Pick Correct': lambda x: 'Yes' if x else 'No'
            # 'ATS Winnings': lambda x: f"${float(x):,.2f}" if x else '$0.00',
            # 'ML Winnings': lambda x: f"${float(x):,.2f}" if x else '$0.00'
        })

        # Display the picks and support advantage information
        st.subheader("Picks and Support Advantage Information")
        # only display the columns in the display_list
        st.table(styled_picks_df)
        # Read the weekly stats data
        weekly_stats_df = pd.read_csv('../Data/WeeklyStats/weekly_stats.csv')
        week_data = weekly_stats_df[weekly_stats_df['week'] == selected_week].iloc[0]

        # Create a 4-column layout for the metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(label="Total Amount Wagered", value=f"${week_data['total_wagered']:,.2f}")
        with col2:
            st.metric(label="Spread Win Percentage", value=f"{week_data['spread_win_percentage']:.2f}%")
        with col3:
            st.metric(label="Money Line Win Percentage", value=f"{week_data['ml_win_percentage']:.2f}%")
        with col4:
            st.metric(label="Total Profit", value=f"${week_data['total_profit']:,.2f}")

    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
    except pd.errors.EmptyDataError as e:
        st.error(f"Empty data error: {e}")

def display_summary_stats():
    st.header("Summary Statistics")

    # Read the weekly stats data
    weekly_stats_df = pd.read_csv('../Data/WeeklyStats/weekly_stats.csv')

    # Calculate overall statistics
    overall_stats['cumulative_profit'] = weekly_stats_df['total_profit'].sum()
    overall_stats['total_spread_bets'] = weekly_stats_df['total_spread_bets'].sum()
    overall_stats['total_spread_wins'] = weekly_stats_df['total_spread_wins'].sum()
    overall_stats['total_ml_bets'] = weekly_stats_df['total_ml_bets'].sum()
    overall_stats['total_ml_wins'] = weekly_stats_df['total_ml_wins'].sum()
    overall_stats['total_amount_wagered'] = weekly_stats_df['total_wagered'].sum()
    overall_stats['total_wins'] = weekly_stats_df['total_ml_wins'].sum() + weekly_stats_df['total_spread_wins'].sum()
    overall_stats['total_bets'] = weekly_stats_df['total_ml_bets'].sum() + weekly_stats_df['total_spread_bets'].sum()
    overall_stats['total_losses'] = overall_stats['total_bets'] - overall_stats['total_wins']
    # Calculate perfect weeks by check if total wins == total bets, if yes then perfect week
    overall_stats['perfect_weeks'] = weekly_stats_df['perfect_weeks'].sum()
    overall_stats['weekly_profits'] = weekly_stats_df['total_profit'].cumsum()
    overall_stats['weekly_wagered'] = weekly_stats_df['total_wagered']

    print(overall_stats)

    # Calculate overall win percentages and profit
    overall_spread_win_percentage = (overall_stats['total_spread_wins'] / overall_stats['total_spread_bets']) * 100 if overall_stats['total_spread_bets'] > 0 else 0
    overall_ml_win_percentage = (overall_stats['total_ml_wins'] / overall_stats['total_ml_bets']) * 100 if overall_stats['total_ml_bets'] > 0 else 0


    # Create a 3-column layout for the metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Cumulative Profit", value=f"${overall_stats['cumulative_profit']:,.2f}")
        st.metric(label="Overall Spread Win Percentage", value=f"{overall_spread_win_percentage:.2f}%")
        st.metric(label="Total Wins", value=overall_stats['total_wins'])
    with col2:
        st.metric(label="Overall Money Line Win Percentage", value=f"{overall_ml_win_percentage:.2f}%")
        st.metric(label="Cumulative Amount Wagered", value=f"${overall_stats['total_amount_wagered']:,.2f}")
        st.metric(label="Total Losses", value=overall_stats['total_losses'])
    with col3:
        st.metric(label="Starting Balance", value=f"${overall_stats['rolling_balance']:,.2f}")
        st.metric(label="Perfect Weeks", value=overall_stats['perfect_weeks'])
    with col4:
        st.metric(label="Total Spread Bets", value=overall_stats['total_spread_bets'])
        st.metric(label="Total Spread Wins", value=overall_stats['total_spread_wins'])
        st.metric(label="Total ML Bets", value=overall_stats['total_ml_bets'])
        st.metric(label="Total ML Wins", value=overall_stats['total_ml_wins'])

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
        height=600
    )
    st.altair_chart(combined_chart, use_container_width=True)

def display_welcome_page():
    st.title("Welcome to the NFL Betting Analysis App")
    st.write("""
    ## Overview
    This app provides a comprehensive analysis of NFL betting data, including predictions for future matchups, picks data, weekly statistics, and summary statistics. The data analysis process involves several steps to ensure accurate and insightful results.

    ## Data Analysis Process
    1. **Data Collection**: The app collects data from various sources, including PDFs, APIs, and web scraping. This data includes team grades, advanced statistics, matchups, and spreads. The data is gathered from reliable sources to ensure accuracy and relevance.
    2. **Data Processing**: The collected data is processed and cleaned to ensure accuracy. This includes merging data from different sources, normalizing statistics, and calculating composite scores. Data processing ensures that the data is in a usable format for analysis.
    3. **Picks Generation**: Based on the processed data, the app generates picks for each matchup. The picks are determined by comparing the advantages of each team in various categories, such as overall, offense, defense, and composite scores. This step involves complex calculations to determine the best picks.
    4. **Backtesting**: The app backtests the generated picks to evaluate their performance. This involves calculating winnings based on historical data and updating overall statistics. Backtesting helps in understanding the effectiveness of the picks and improving future predictions.

    ## Calculations for Generating Picks
    - **Overall Advantage**: This is calculated as the difference between the overall grades of the home team and the away team. It gives an idea of the general strength of each team.
      - Formula: `Overall Advantage = Home Team Overall Grade - Away Team Overall Grade`
    - **Offense Advantage**: This is calculated as the difference between the offensive grade of the home team and the defensive grade of the away team. It focuses on the offensive capabilities of the home team against the defensive capabilities of the away team.
      - Formula: `Offense Advantage = Home Team Offense Grade - Away Team Defense Grade`
    - **Defense Advantage**: This is calculated as the difference between the defensive grade of the home team and the offensive grade of the away team. It focuses on the defensive capabilities of the home team against the offensive capabilities of the away team.
      - Formula: `Defense Advantage = Home Team Defense Grade - Away Team Offense Grade`
    - **Composite Scores**: Composite scores are calculated by normalizing various statistics and applying weights to them. The composite scores are then used to determine the overall strength of each team. This involves a weighted sum of different metrics to get a single score representing the team's performance.
      - **Normalization**: Each statistic is normalized to a scale of 0 to 1.
      - **Weighting**: Each normalized statistic is multiplied by a predefined weight.
      - **Summation**: The weighted values are summed to get the composite score.
      - Formula: `Composite Score = Σ (Normalized Statistic * Weight)`

    ## Page Descriptions
    - **Welcome**: This page provides an overview of the app, the data analysis process, and the calculations used for generating picks. It serves as the landing page for the app.
    - **Week Stats**: This page displays the results for each week, including the total amount wagered, total profit, and win percentages for spread and money line bets. It provides detailed statistics for each week to help users understand the performance of their bets.
    - **Summary Stats**: This page provides summary statistics, including cumulative profit, overall win percentages, and other key metrics. It gives a high-level overview of the betting performance over the entire season.
    - **Picks Data**: This page shows the picks data for each week, including the advantages of each team in various categories. It provides detailed information on the picks made for each matchup.
    - **Predictions**: This page displays predictions for future matchups, including visualizations of the overall advantage and composite scores. It helps users make informed decisions for future bets by providing detailed predictions.

    We hope you find this app useful for your NFL betting analysis!
    """)

def main():
    st.set_page_config(layout="wide")  # Set the page layout to wide
    st.title("NFL Betting Backtest Results")

    # Add input fields for bankroll and bet amount
    bankroll = st.sidebar.number_input("Starting Bankroll", value=120, step=10)
    bet_amount = st.sidebar.number_input("Bet Amount", value=10, step=1)

    # Update the global variable with the dynamic bankroll
    overall_stats['rolling_balance'] = bankroll

    pages = ["Welcome", "Week Stats", "Summary Stats", "Picks Data", "Predictions"]
    selected_page = st.sidebar.selectbox("Select Page", pages)

    if selected_page == "Welcome":
        display_welcome_page()
    elif selected_page == "Week Stats":
        display_week_stats()
    elif selected_page == "Summary Stats":
        display_summary_stats()
    elif selected_page == "Picks Data":
        display_picks_data()
    elif selected_page == "Predictions":
        display_predictions()

if __name__ == "__main__":
    main()