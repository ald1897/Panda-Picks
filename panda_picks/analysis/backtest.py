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

def backtest():
    print(f"[{time.strftime('%H:%M:%S')}] backtest started")
    weeks = ['WEEK1','WEEK2','WEEK3','WEEK4','WEEK5','WEEK6','WEEK7','WEEK8','WEEK9', 'WEEK10', 'WEEK11', 'WEEK12', 'WEEK13', 'WEEK14', 'WEEK15', 'WEEK16', 'WEEK17', 'WEEK18']
    final_results = pd.DataFrame()
    cumulative_profit = 0
    initial_balance = 500  # Starting balance
    current_balance = initial_balance

    # Remove redundant direct sqlite3.connect; rely on configured connection
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

        # Consolidate duplicated line columns first
        if 'Home_Line_Close_y' in merged_df.columns:
            merged_df = merged_df.drop(columns=['Home_Line_Close_y', 'Away_Line_Close_y'])
            merged_df = merged_df.rename(columns={'Home_Line_Close_x': 'Home_Line_Close', 'Away_Line_Close_x': 'Away_Line_Close'})

        # NEW: Consolidate duplicated odds columns (avoid KeyError 'Home_Odds_Close')
        for base in ['Home_Odds_Close', 'Away_Odds_Close', 'Home_Odds_Open', 'Away_Odds_Open']:
            x_col, y_col = f"{base}_x", f"{base}_y"
            if x_col in merged_df.columns and y_col in merged_df.columns:
                # Prefer picks (x) unless it's entirely NaN and y has data
                if merged_df[x_col].notna().any() or not merged_df[y_col].notna().any():
                    merged_df[base] = merged_df[x_col]
                else:
                    merged_df[base] = merged_df[y_col]
                merged_df = merged_df.drop(columns=[x_col, y_col])
            elif x_col in merged_df.columns:
                merged_df = merged_df.rename(columns={x_col: base})
            elif y_col in merged_df.columns:
                merged_df = merged_df.rename(columns={y_col: base})
            # else: column absent in both; leave missing, later guards will skip usage

        # Rename win/loss/tie columns if present (guard against absence)
        for suffix in ['WINS', 'LOSSES', 'TIES']:
            hx, hy = f"{suffix}_x", f"{suffix}_y"
            if hx in merged_df.columns:
                merged_df = merged_df.rename(columns={hx: f"Home_{suffix.title()}"})
            if hy in merged_df.columns:
                merged_df = merged_df.rename(columns={hy: f"Away_{suffix.title()}"})

        # Ensure numeric scores & add placeholder flags BEFORE probability calcs
        for col in ['Home_Score', 'Away_Score']:
            merged_df[col] = pd.to_numeric(merged_df.get(col, np.nan), errors='coerce')
        merged_df['Score_Placeholder'] = merged_df['Home_Score'].isna() | merged_df['Away_Score'].isna()
        # Assign temporary 0-0 for missing scores (will be ignored in metrics/combo logic via flag)
        merged_df.loc[merged_df['Score_Placeholder'], ['Home_Score', 'Away_Score']] = 0

        # Probability + edges
        if 'Home_Win_Prob' in merged_df.columns:
            # Guard: only compute implied probabilities if odds columns exist
            if 'Home_Odds_Close' in merged_df.columns:
                merged_df['Home_Odds_Implied_Prob'] = merged_df['Home_Odds_Close'].apply(_moneyline_implied_prob)
            else:
                merged_df['Home_Odds_Implied_Prob'] = math.nan
            if 'Away_Odds_Close' in merged_df.columns:
                merged_df['Away_Odds_Implied_Prob'] = merged_df['Away_Odds_Close'].apply(_moneyline_implied_prob)
            else:
                merged_df['Away_Odds_Implied_Prob'] = math.nan
            merged_df['Home_Spread_Implied_Prob'] = merged_df['Home_Line_Close'].apply(_spread_implied_home_win_prob) if 'Home_Line_Close' in merged_df.columns else math.nan
            merged_df['Home_Edge_ML'] = merged_df['Home_Win_Prob'] - merged_df['Home_Odds_Implied_Prob']
            merged_df['Home_Edge_Spread'] = merged_df['Home_Win_Prob'] - merged_df['Home_Spread_Implied_Prob']
            def _actual(row):
                # Ignore placeholder games for actual result
                if row.get('Score_Placeholder'):
                    return math.nan
                return 1.0 if row['Home_Score'] > row['Away_Score'] else 0.0
            merged_df['Home_Win_Actual'] = merged_df.apply(_actual, axis=1)
            merged_df['Pick_Edge_ML'] = merged_df.apply(lambda r: (r['Home_Edge_ML'] if r['Game_Pick'] == r['Home_Team'] else -r['Home_Edge_ML']) if not math.isnan(r.get('Home_Edge_ML', float('nan'))) else float('nan'), axis=1)
            merged_df['Pick_Edge_Spread'] = merged_df.apply(lambda r: (r['Home_Edge_Spread'] if r['Game_Pick'] == r['Home_Team'] else -r['Home_Edge_Spread']) if not math.isnan(r.get('Home_Edge_Spread', float('nan'))) else float('nan'), axis=1)
            # Ordered list of available columns (removed Simulated_Score)
            prob_cols_order = ['WEEK','Home_Team','Away_Team','Home_Line_Close','Home_Odds_Close','Away_Odds_Close','Home_Win_Prob','Home_Odds_Implied_Prob','Home_Spread_Implied_Prob','Home_Edge_ML','Home_Edge_Spread','Home_Win_Actual','Game_Pick','Pick_Edge_ML','Pick_Edge_Spread','Score_Placeholder']
            available_cols = [c for c in prob_cols_order if c in merged_df.columns]
            probability_game_rows.extend(merged_df[available_cols].dropna(subset=['Home_Win_Actual']).to_dict('records'))
            real_week = merged_df[(~merged_df['Score_Placeholder']) & merged_df['Home_Win_Actual'].notna()]
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

        # Teaser evaluation only over completed (non-placeholder) games
        merged_df = merged_df.apply(adjust_spread, axis=1)
        completed_mask = ~merged_df['Score_Placeholder']
        teams = merged_df.loc[completed_mask, 'Game_Pick'].unique()
        logging.info(f'{week} backtest (completed games: {len(teams)}, placeholders: {merged_df["Score_Placeholder"].sum()})')

        if len(teams) == 0:
            logging.warning(f"Week {week}: all games pending (placeholders). Skipping teaser evaluation.")
            continue

        # Winner / grading only for completed games
        merged_df['Winner'] = merged_df.apply(lambda x: (x['Home_Team'] if x['Home_Score'] > x['Away_Score'] else x['Away_Team']) if not x['Score_Placeholder'] else None, axis=1)
        merged_df['Correct_Pick'] = merged_df.apply(lambda x: (x['Game_Pick'] == x['Winner']) if x['Winner'] else None, axis=1)
        merged_df['Pick_Covered_Spread'] = merged_df.apply(lambda x: ((x['Game_Pick'] == x['Home_Team']) if (x['Home_Score'] + x['Home_Line_Close'] > x['Away_Score']) else (x['Game_Pick'] == x['Away_Team'])) if not x['Score_Placeholder'] else None, axis=1)

        two_team_combos = list(combinations(teams, 2))
        three_team_combos = list(combinations(teams, 3))
        four_team_combos = list(combinations(teams, 4))

        def calculate_teaser_winnings(combo, odds):
            bet_amount = 10
            correct = True
            for team in combo:
                team_row = merged_df[(merged_df['Game_Pick'] == team) & (completed_mask)]
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

        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM picks_results WHERE WEEK = ?", (week,))
            cur.execute("DELETE FROM teaser_results WHERE WEEK = ?", (week,))
            deprecated_cols = ['Off_Comp_Adv_sig','Def_Comp_Adv_sig','Off_Comp_Adv','Def_Comp_Adv']
            drop_cols = [c for c in deprecated_cols if c in merged_df.columns]
            if drop_cols:
                merged_df = merged_df.drop(columns=drop_cols)
            _ensure_sql_columns(conn, 'picks_results', merged_df)
            _ensure_sql_columns(conn, 'teaser_results', teaser_df)
        merged_df.to_sql('picks_results', conn, if_exists='append', index=False)
        teaser_df.to_sql('teaser_results', conn, if_exists='append', index=False)

    # Probability calibration aggregating only non-placeholder real games
    if probability_game_rows:
        game_df = pd.DataFrame(probability_game_rows)
        real_games = game_df[(game_df['Home_Win_Actual'].notna()) & (~game_df.get('Score_Placeholder', False))]
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
                logging.debug(f"(suppressed duplicate) Column {col} already exists in {table_name}")
            else:
                raise
    conn.commit()

if __name__ == "__main__":
    backtest()