import pandas as pd
import numpy as np
from pathlib import Path
import logging


def scrape_matchups(season="2022", start_week=1, end_week=18):
    """
    Scrape NFL matchup data for the specified season and weeks with optimized
    data processing.

    Args:
        season (str): NFL season year
        start_week (int): First week to scrape
        end_week (int): Last week to scrape
    """
    try:
        # Define data directory and create if it doesn't exist
        data_dir = Path("Data") / "Matchups"
        data_dir.mkdir(parents=True, exist_ok=True)

        # Get logger if available, otherwise use print
        logger = logging.getLogger("PandaPicks") if logging.getLogger("PandaPicks").handlers else None
        log = logger.info if logger else print

        for week in range(start_week, end_week + 1):
            try:
                week_str = str(week)
                log(f"SCRAPING WEEK {week_str} GAME DATA...")

                # Scrape web data into table
                url = f'https://nflgamedata.com/schedule.php?season={season}&week={week_str}'
                tables = pd.read_html(url)

                # Extract the matchup table (index 4)
                if len(tables) < 5:
                    log(f"Warning: Expected table not found for week {week_str}")
                    continue

                # More efficient approach: select only needed columns directly
                raw_df = tables[4]

                # Check if table has expected structure
                needed_cols = [8, 11, 13, 16]
                if not all(col in raw_df.columns for col in needed_cols):
                    log(f"Warning: Table for week {week_str} doesn't have expected columns")
                    continue

                # Create dataframe with only required columns
                matchup_data = {
                    'Away Team': raw_df[8],
                    'Away Spread': raw_df[11],
                    'Home Spread': raw_df[13],
                    'Home Team': raw_df[16]
                }

                # Create dataframe directly with correct structure - avoids copying
                df = pd.DataFrame(matchup_data)

                # Drop the header row more efficiently
                df = df.iloc[1:].reset_index(drop=True)

                # Filter out bye weeks and empty rows in one operation
                df = df[(df['Home Team'] != '-- BYE --') & df['Home Team'].notna()]

                # Add week identifier
                df['Game Date'] = f'WEEK{week_str}'

                # Save to CSV with optimized settings
                output_file = data_dir / f"matchups_WEEK{week_str}.csv"
                df.to_csv(output_file, index=False, float_format='%.2f')
                log(f"Saved matchup data for Week {week_str} to {output_file}")

            except Exception as e:
                log(f"Error processing Week {week_str}: {e}")
                continue

    except Exception as e:
        if logger:
            logger.error(f"Error scraping matchups: {e}")
        else:
            print(f"Error scraping matchups: {e}")


if __name__ == '__main__':
    # Example usage with default parameters
    scrape_matchups()