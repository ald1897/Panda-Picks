import pandas as pd
import numpy as np
from pathlib import Path
import logging


def load_weekly_picks(week, data_dir):
    """Load picks data for a specific week."""
    picks_file = data_dir / "Picks" / f"{week}.csv"

    if not picks_file.exists():
        raise FileNotFoundError(f"Picks file not found: {picks_file}")

    # Load only needed columns
    picks = pd.read_csv(picks_file, usecols=['Game Date', 'Home Team', 'Away Team', 'Game Pick'])

    # Create game key in one operation
    picks['Game Key'] = picks['Home Team'] + picks['Away Team']
    return picks


def load_spreads(data_dir):
    """Load the spreads data and prepare it for analysis."""
    spreads_file = data_dir / "Spreads" / "spreads.csv"

    if not spreads_file.exists():
        raise FileNotFoundError(f"Spreads file not found: {spreads_file}")

    # Convert numeric columns during loading
    numeric_cols = ['Home Score', 'Away Score', 'Home Line Close',
                    'Away Line Close', 'Home Odds Close', 'Away Odds Close']
    dtype_dict = {col: 'float64' for col in numeric_cols}

    spreads = pd.read_csv(spreads_file, dtype=dtype_dict)

    # Create game key in one operation
    spreads['Game Key'] = spreads['Home Team'] + spreads['Away Team']

    # Return only needed columns
    cols_to_keep = ['Game Date', 'Home Team', 'Home Score', 'Away Score',
                    'Away Team', 'Home Line Close', 'Away Line Close',
                    'Home Odds Close', 'Away Odds Close', 'Game Key']
    return spreads[cols_to_keep]


def analyze_weekly_performance(picks, spreads, week):
    """Compare picks with actual results and calculate performance metrics."""
    # Filter spreads for the current week more efficiently
    spreads_for_week = spreads[spreads['Game Date'] == week]

    if spreads_for_week.empty:
        return pd.DataFrame()  # Return empty DataFrame if no data

    # Merge picks with spreads to compare - use suffixes for clarity
    compare = pd.merge(
        picks,
        spreads_for_week,
        on=['Game Key'],
        suffixes=('_picks', '_actual')
    )

    # Keep only rows with actual picks
    compare = compare[compare['Game Pick'] != 'No Pick']

    if compare.empty:
        return pd.DataFrame()  # Return empty DataFrame if no valid picks

    # Calculate point margin in one step
    compare['Margin'] = compare['Away Score'] - compare['Home Score']

    # Determine wins/losses more efficiently using numpy vectorization
    home_pick_mask = compare['Game Pick'] == compare['Home Team_actual']

    # ATS calculations (Against The Spread)
    home_ats_win = compare['Home Score'] + compare['Home Line Close'] > compare['Away Score']
    away_ats_win = compare['Away Score'] + compare['Away Line Close'] > compare['Home Score']

    # Create ATS win/loss column in one vectorized operation
    compare['ATS Win/Loss'] = np.where(
        home_pick_mask,
        np.where(home_ats_win, 1, 0),
        np.where(away_ats_win, 1, 0)
    )

    # ML calculations (Money Line)
    home_ml_win = compare['Home Score'] > compare['Away Score']
    away_ml_win = compare['Away Score'] > compare['Home Score']

    # Create ML win/loss column in one vectorized operation
    compare['ML Win/Loss'] = np.where(
        home_pick_mask,
        np.where(home_ml_win, 1, 0),
        np.where(away_ml_win, 1, 0)
    )

    # Rename columns for clarity
    compare = compare.rename(columns={
        'Home Team_actual': 'Home Team',
        'Away Team_actual': 'Away Team',
        'Game Date_actual': 'Game Date'
    })

    # Add wager amount
    compare['Wager'] = 100

    # Calculate payouts efficiently
    # ATS payout calculation (using numpy vectorization)
    win_payout = 1.9 * compare['Wager'] - compare['Wager']
    loss_payout = -compare['Wager']

    compare['ATS Payout'] = np.where(compare['ATS Win/Loss'] > 0, win_payout, loss_payout)

    # ML payout calculation (using numpy vectorization)
    home_odds_win = compare['Home Odds Close'] * compare['Wager'] - compare['Wager']
    away_odds_win = compare['Away Odds Close'] * compare['Wager'] - compare['Wager']

    compare['ML Payout'] = np.where(
        compare['ML Win/Loss'] > 0,
        np.where(home_pick_mask, home_odds_win, away_odds_win),
        loss_payout
    )

    # Add aggregated values
    ats_sum = compare['ATS Payout'].sum()
    ml_sum = compare['ML Payout'].sum()

    compare['Weekly ATS Payout'] = ats_sum
    compare['Weekly ML Payout'] = ml_sum
    compare['Total Payout'] = ats_sum + ml_sum

    return compare


def create_weekly_stats(compare, week):
    """Create summary statistics for the week."""
    # Create DataFrame with week information
    games = pd.DataFrame({'week': [week]})

    if len(compare) > 0:
        # Calculate all stats in one go
        games['ATS Win %'] = compare['ATS Win/Loss'].mean()
        games['ML Win %'] = compare['ML Win/Loss'].mean()
        games['Weekly Risk'] = compare['Wager'].sum()
        games['ATS Payout'] = compare['ATS Payout'].sum()
        games['ML Payout'] = compare['ML Payout'].sum()
        games['Weekly Profit'] = games['ATS Payout'] + games['ML Payout']
    else:
        # Assign default values if no picks
        games['ATS Win %'] = 0
        games['ML Win %'] = 0
        games['Weekly Risk'] = 0
        games['ATS Payout'] = 0
        games['ML Payout'] = 0
        games['Weekly Profit'] = 0

    return games


def run_tests():
    """Run backtests on picks against actual results."""
    try:
        # Set up logging
        logger = logging.getLogger("PandaPicks") if logging.getLogger("PandaPicks").handlers else None
        log = logger.info if logger else print

        # Set numeric display options
        pd.set_option("display.precision", 4)
        pd.options.display.float_format = '{:10,.2f}'.format

        # Define data directory and weeks to analyze
        data_dir = Path("Data")
        weeks = [f'WEEK{w}' for w in range(1, 19)]  # Weeks 1 to 18

        # Load spreads data once - more efficient
        log("Loading spreads data...")
        try:
            spreads = load_spreads(data_dir)
        except FileNotFoundError as e:
            log(f"Error: {e}")
            return False

        # Create output directory if it doesn't exist
        picks_dir = data_dir / "Picks"
        picks_dir.mkdir(parents=True, exist_ok=True)

        # Process each week - use an empty list and concat once at the end
        weekly_stats_list = []

        for week in weeks:
            log(f"Generating stats for {week}...")

            try:
                # Load and analyze picks for this week
                picks = load_weekly_picks(week, data_dir)
                compare = analyze_weekly_performance(picks, spreads, week)

                if not compare.empty:
                    # Save detailed comparison for the week
                    comparison_file = picks_dir / f"compare_{week}.csv"
                    compare.to_csv(comparison_file, index=False, float_format='%.2f')

                    # Generate and store weekly stats
                    weekly_stats = create_weekly_stats(compare, week)
                    weekly_stats_list.append(weekly_stats)
                    log(f"Processed {len(compare)} picks for {week}")
                else:
                    log(f"No valid picks found for {week}")

            except FileNotFoundError:
                log(f"No picks file found for {week}, skipping...")
                continue
            except Exception as e:
                log(f"Error processing {week}: {e}")
                continue

        # Combine all weekly stats efficiently
        if weekly_stats_list:
            all_weekly_stats = pd.concat(weekly_stats_list, ignore_index=True)

            # Calculate season stats efficiently
            all_weekly_stats['Season ATS Winning %'] = all_weekly_stats['ATS Win %'].mean()
            all_weekly_stats['Season ML Winning %'] = all_weekly_stats['ML Win %'].mean()
            all_weekly_stats['Season Risk'] = all_weekly_stats['Weekly Risk'].sum()
            all_weekly_stats['Season Profit'] = all_weekly_stats['Weekly Profit'].sum()

            # Save season stats
            stats_file = picks_dir / "stats.csv"
            all_weekly_stats.to_csv(stats_file, index=False, float_format='%.2f')
            log(f"Saved season stats to {stats_file}")
            return True
        else:
            log("No weekly stats generated. Check input data.")
            return False

    except Exception as e:
        if logger:
            logger.error(f"Error running backtest: {e}")
        else:
            print(f"Error running backtest: {e}")
        return False


if __name__ == "__main__":
    run_tests()