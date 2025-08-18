import pandas as pd
import sqlite3
from itertools import combinations
import logging
import math
import numpy as np  # added for probability metrics
from panda_picks.db.database import get_connection
from panda_picks import config
import time

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

def _moneyline_implied_prob(odds):
    try:
        odds = float(odds)
    except (TypeError, ValueError):
        return float('nan')
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

_DEF_MARGIN_SD = 13.5  # historical stdev of NFL scoring margin approximation
_SQRT2 = math.sqrt(2.0)

def _norm_cdf(x, mu=0.0, sigma=1.0):
    z = (x - mu) / (sigma * _SQRT2)
    return 0.5 * (1 + math.erf(z))

def _spread_implied_home_win_prob(home_spread):
    # home_spread is home line (negative if favorite). Expected home margin ~ -home_spread
    try:
        sp = float(home_spread)
    except (TypeError, ValueError):
        return float('nan')
    mean_margin = -sp
    # P(home margin > 0) = 1 - CDF(0)
    return 1 - _norm_cdf(0, mu=mean_margin, sigma=_DEF_MARGIN_SD)


def _bin_prob(p, bins):
    for i in range(len(bins) - 1):
        if bins[i] <= p < bins[i + 1]:
            return f"{bins[i]:.2f}-{bins[i+1]:.2f}"
    return f"{bins[-2]:.2f}-{bins[-1]:.2f}"  # last bin inclusive upper

SIMULATION_SEED = 42
SIM_K_MARGIN = 0.75  # multiplier converting Overall_Adv (approx) to expected margin
SIM_BASE_TOTAL = 44
SIM_TOTAL_JITTER = 7

def simulate_missing_scores(merged_picks_spreads: pd.DataFrame, adv_col: str = 'Overall_Adv') -> pd.DataFrame:
    """Fill in missing scores with simulated values for testing.
    Assumes presence of adv_col and uses simple linear mapping to expected margin.
    Adds column 'Simulated_Score' (bool) to indicate simulated rows.
    """
    rng = np.random.default_rng(SIMULATION_SEED)
    if 'Simulated_Score' not in merged_picks_spreads.columns:
        merged_picks_spreads['Simulated_Score'] = False
    # Ensure Home_Score/Away_Score numeric
    for col in ['Home_Score','Away_Score']:
        if col in merged_picks_spreads.columns:
            merged_picks_spreads[col] = pd.to_numeric(merged_picks_spreads[col], errors='coerce')
        else:
            merged_picks_spreads[col] = np.nan
    mask_missing = merged_picks_spreads['Home_Score'].isna() | merged_picks_spreads['Away_Score'].isna()
    if mask_missing.any():
        subset = merged_picks_spreads.loc[mask_missing]
        for idx, row in subset.iterrows():
            overall_adv = row.get(adv_col, 0)
            try:
                overall_adv = float(overall_adv)
            except (TypeError, ValueError):
                overall_adv = 0
            exp_margin = SIM_K_MARGIN * overall_adv  # positive favors home
            total = SIM_BASE_TOTAL + rng.uniform(-SIM_TOTAL_JITTER, SIM_TOTAL_JITTER)
            # Add noise to margin
            margin = rng.normal(exp_margin, 7)  # 7 point margin noise
            home_pts = (total + margin) / 2
            away_pts = total - home_pts
            # Clamp and round
            home_pts = int(max(0, round(home_pts)))
            away_pts = int(max(0, round(away_pts)))
            # Avoid ties rarely if desired (keep ties allowed for realism)
            merged_picks_spreads.at[idx, 'Home_Score'] = home_pts
            merged_picks_spreads.at[idx, 'Away_Score'] = away_pts
            merged_picks_spreads.at[idx, 'Simulated_Score'] = True
    return merged_picks_spreads

def backtest(simulate_missing: bool = True):
    print(f"[{time.strftime('%H:%M:%S')}] backtest started")
    weeks = ['WEEK1','WEEK2','WEEK3','WEEK4','WEEK5','WEEK6','WEEK7','WEEK8','WEEK9', 'WEEK10', 'WEEK11', 'WEEK12', 'WEEK13', 'WEEK14', 'WEEK15', 'WEEK16', 'WEEK17', 'WEEK18']
    final_results = pd.DataFrame()
    cumulative_profit = 0
    initial_balance = 500  # Starting balance
    current_balance = initial_balance

    conn = sqlite3.connect('nfl_data.db')
    conn = get_connection()

    probability_game_rows = []
    weekly_prob_metrics = []

    for week in weeks:
        df = pd.read_sql_query("SELECT * FROM spreads", conn)
        picks_df = pd.read_sql_query(f"SELECT * FROM picks WHERE WEEK = '{week}'", conn)
        if picks_df.empty:
            logging.info(f"{week}: no picks; skipping")
            continue
        merged_df = pd.merge(picks_df, df, left_on=['WEEK', 'Home_Team', 'Away_Team'],
                             right_on=['WEEK', 'Home_Team', 'Away_Team'])
        pd.set_option('display.max_rows', 200)
        pd.set_option('display.max_columns', 200)

        if 'Home_Line_Close_y' in merged_df.columns:
            merged_df = merged_df.drop(columns=['Home_Line_Close_y', 'Away_Line_Close_y'])
            merged_df = merged_df.rename(columns={'Home_Line_Close_x': 'Home_Line_Close', 'Away_Line_Close_x': 'Away_Line_Close'})

        merged_df = merged_df.rename(columns={'WINS_x': 'Home_Wins', 'LOSSES_x': 'Home_Losses', 'TIES_x': 'Home_Ties'})
        merged_df = merged_df.rename(columns={'WINS_y': 'Away_Wins', 'LOSSES_y': 'Away_Losses', 'TIES_y': 'Away_Ties'})

        # Simulate scores if missing (adds Simulated_Score flag)
        if simulate_missing:
            merged_df = simulate_missing_scores(merged_df, adv_col='Overall_Adv')
        else:
            if 'Simulated_Score' not in merged_df.columns:
                merged_df['Simulated_Score'] = False

        # Probability + edges (before teaser spread adjustment, using original closing line)
        if 'Home_Win_Prob' in merged_df.columns:
            merged_df['Home_Odds_Implied_Prob'] = merged_df['Home_Odds_Close'].apply(_moneyline_implied_prob)
            merged_df['Away_Odds_Implied_Prob'] = merged_df['Away_Odds_Close'].apply(_moneyline_implied_prob)
            merged_df['Home_Spread_Implied_Prob'] = merged_df['Home_Line_Close'].apply(_spread_implied_home_win_prob)
            merged_df['Home_Edge_ML'] = merged_df['Home_Win_Prob'] - merged_df['Home_Odds_Implied_Prob']
            merged_df['Home_Edge_Spread'] = merged_df['Home_Win_Prob'] - merged_df['Home_Spread_Implied_Prob']
            # Actual outcome only for non-simulated rows with scores
            def _actual(row):
                if row.get('Simulated_Score', False):
                    return np.nan
                if pd.isna(row.get('Home_Score')) or pd.isna(row.get('Away_Score')):
                    return np.nan
                return 1.0 if row['Home_Score'] > row['Away_Score'] else 0.0
            merged_df['Home_Win_Actual'] = merged_df.apply(_actual, axis=1)
            merged_df['Pick_Edge_ML'] = merged_df.apply(lambda r: (r['Home_Edge_ML'] if r['Game_Pick'] == r['Home_Team'] else -r['Home_Edge_ML']) if not math.isnan(r.get('Home_Edge_ML', float('nan'))) else float('nan'), axis=1)
            merged_df['Pick_Edge_Spread'] = merged_df.apply(lambda r: (r['Home_Edge_Spread'] if r['Game_Pick'] == r['Home_Team'] else -r['Home_Edge_Spread']) if not math.isnan(r.get('Home_Edge_Spread', float('nan'))) else float('nan'), axis=1)
            # Store per-game probability metrics including simulation flag
            probability_game_rows.extend(merged_df[[
                'WEEK','Home_Team','Away_Team','Home_Line_Close','Home_Odds_Close','Away_Odds_Close','Home_Win_Prob','Home_Odds_Implied_Prob','Home_Spread_Implied_Prob','Home_Edge_ML','Home_Edge_Spread','Home_Win_Actual','Game_Pick','Pick_Edge_ML','Pick_Edge_Spread','Simulated_Score'
            ]].to_dict('records'))
            # Weekly metrics only for real games
            real_week = merged_df[(merged_df['Simulated_Score'] == False) & merged_df['Home_Win_Actual'].notna()]
            if not real_week.empty:
                eps = 1e-6
                p = real_week['Home_Win_Prob'].clip(eps, 1-eps)
                brier = ((real_week['Home_Win_Prob'] - real_week['Home_Win_Actual']) ** 2).mean()
                log_loss = -(real_week['Home_Win_Actual'] * np.log(p) + (1 - real_week['Home_Win_Actual']) * np.log(1 - p)).mean()
                weekly_prob_metrics.append({
                    'WEEK': week,
                    'Games': len(real_week),
                    'Brier': brier,
                    'Log_Loss': log_loss,
                    'Avg_Home_Edge_ML': real_week['Home_Edge_ML'].mean(),
                    'Avg_Pick_Edge_ML': real_week['Pick_Edge_ML'].mean()
                })

        # Continue existing logic (teaser adjustments / profit) AFTER probability metrics
        merged_df = merged_df.apply(adjust_spread, axis=1)
        teams = merged_df['Game_Pick'].unique()
        logging.info(f'{week} backtest')
        logging.info(f"Teams: {teams}")

        # Require scores (simulated accepted) for teaser evaluation
        if merged_df['Home_Score'].isnull().any() or merged_df['Away_Score'].isnull().any():
            logging.warning(f"Missing scores for week {week}. Skipping this week.")
            continue
        merged_df['Home_Score'] = pd.to_numeric(merged_df['Home_Score'], errors='coerce')
        merged_df['Away_Score'] = pd.to_numeric(merged_df['Away_Score'], errors='coerce')
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

        # Idempotent delete previous week's results before inserting new
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM picks_results WHERE WEEK = ?", (week,))
            cur.execute("DELETE FROM teaser_results WHERE WEEK = ?", (week,))
            _ensure_sql_columns(conn, 'picks_results', merged_df)
            _ensure_sql_columns(conn, 'teaser_results', teaser_df)
        merged_df.to_sql('picks_results', conn, if_exists='append', index=False)
        teaser_df.to_sql('teaser_results', conn, if_exists='append', index=False)

    # After loop: probability calibration & aggregates
    if probability_game_rows:
        game_df = pd.DataFrame(probability_game_rows)
        # Calibration only on real games
        real_games = game_df[(game_df['Simulated_Score'] == False) & game_df['Home_Win_Actual'].notna()]
        if not real_games.empty:
            bins = [i/10 for i in range(11)]
            real_games['Prob_Bin'] = real_games['Home_Win_Prob'].apply(lambda p: _bin_prob(p, bins) if not math.isnan(p) else 'nan')
            calib = real_games.groupby('Prob_Bin').agg(
                Predicted_Mean=('Home_Win_Prob','mean'),
                Actual_Freq=('Home_Win_Actual','mean'),
                Count=('Home_Win_Actual','count')
            ).reset_index()
            calib['Abs_Calibration_Error'] = (calib['Predicted_Mean'] - calib['Actual_Freq']).abs()
        else:
            calib = pd.DataFrame(columns=['Prob_Bin','Predicted_Mean','Actual_Freq','Count','Abs_Calibration_Error'])
        game_df.to_sql('probability_game_metrics', conn, if_exists='replace', index=False)
        calib.to_sql('probability_calibration', conn, if_exists='replace', index=False)

    if weekly_prob_metrics:
        weekly_df = pd.DataFrame(weekly_prob_metrics)
        weekly_df.to_sql('probability_week_metrics', conn, if_exists='replace', index=False)

    # Existing summary
    final_results = pd.read_sql_query("SELECT * FROM teaser_results", conn)
    final_results['Total_Profit'] = cumulative_profit
    final_results.to_sql('backtest_results', conn, if_exists='replace', index=False)

    if final_results.shape[0] > 0:
        win_percentage = final_results[final_results['Winnings'] > 0].shape[0] / final_results.shape[0]
        print(f"Individual Bet Win Percentage: {win_percentage * 100:.2f}%")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] No bet results available to calculate win percentage.")

    conn.close()
    print(f"[{time.strftime('%H:%M:%S')}] backtest finished")

def _ensure_sql_columns(conn, table_name: str, df: pd.DataFrame):
    """Ensure all columns in df exist in SQLite table; add if missing."""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if cur.fetchone() is None:
        return  # table will be created automatically by to_sql
    cur.execute(f"PRAGMA table_info({table_name})")
    existing = {row[1] for row in cur.fetchall()}
    add_cols = [c for c in df.columns if c not in existing]
    if not add_cols:
        return
    def _col_type(series: pd.Series):
        if pd.api.types.is_integer_dtype(series):
            return 'INTEGER'
        if pd.api.types.is_float_dtype(series):
            return 'REAL'
        if pd.api.types.is_bool_dtype(series):
            return 'INTEGER'
        return 'TEXT'
    for col in add_cols:
        col_type = _col_type(df[col])
        logging.info(f"Altering {table_name}: adding column {col} {col_type}")
        try:
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type}")
        except Exception as e:
            if 'duplicate column name' in str(e).lower():
                logging.warning(f"Column {col} already exists in {table_name}, skipping")
            else:
                raise
    conn.commit()

if __name__ == "__main__":
    backtest()