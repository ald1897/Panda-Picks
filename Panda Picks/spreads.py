import pandas as pd
from pathlib import Path
import logging


def getSpreads(data_dir=None):
    """
    Process NFL betting spread data by merging with team abbreviations
    and cleaning the dataset for backtesting.

    Args:
        data_dir (Path, optional): Base directory for data files

    Returns:
        bool: True if processing was successful, False otherwise
    """
    try:
        # Set up logging
        logger = logging.getLogger("PandaPicks") if logging.getLogger("PandaPicks").handlers else None
        log = logger.info if logger else print

        # Define paths using Path objects
        if data_dir is None:
            data_dir = Path("Data")

        spreads_file = data_dir / "Spreads" / "nflSpreads.csv"
        abrevs_file = data_dir / "Grades" / "NFL_translations.csv"
        output_file = data_dir / "Spreads" / "spreads.csv"

        # Check if input files exist
        if not spreads_file.exists():
            raise FileNotFoundError(f"Spreads file not found: {spreads_file}")

        if not abrevs_file.exists():
            raise FileNotFoundError(f"Abbreviations file not found: {abrevs_file}")

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Read input files
        log(f"Loading spread data from {spreads_file}")
        spreads_df = pd.read_csv(spreads_file)

        log(f"Loading team abbreviations from {abrevs_file}")
        abrevs_df = pd.read_csv(abrevs_file, usecols=['TEAM', 'Abrev'])  # Only read needed columns

        # Process home team data
        log("Processing home team data...")
        home_abrevs = abrevs_df.rename(columns={"TEAM": "Home Team"})
        merged_df = pd.merge(spreads_df, home_abrevs, on="Home Team")

        # Filter unnamed columns in one operation
        home_cols_to_drop = ["Home Team"] + [col for col in merged_df.columns if col.startswith("Unnamed:")]
        merged_df = merged_df.drop(columns=home_cols_to_drop)

        # Process away team data
        log("Processing away team data...")
        away_abrevs = abrevs_df.rename(columns={"TEAM": "Away Team"})
        merged_df = pd.merge(merged_df, away_abrevs, on="Away Team")

        # Filter unnamed columns in one operation
        away_cols_to_drop = ["Away Team"] + [col for col in merged_df.columns if col.startswith("Unnamed:")]
        merged_df = merged_df.drop(columns=away_cols_to_drop)

        # Rename columns for consistency
        result_df = merged_df.rename(columns={
            "Abrev_x": "Home Team",
            "Abrev_y": "Away Team",
            "Date": "Game Date"
        })

        # Save processed data with optimized settings
        log(f"Saving processed spread data to {output_file}")
        result_df.to_csv(output_file, index=False, float_format='%.2f')

        log(f"Successfully processed spread data and saved to {output_file}")
        return True

    except FileNotFoundError as e:
        if logger:
            logger.error(f"Error: Could not find file - {e}")
        else:
            print(f"Error: Could not find file - {e}")
        return False
    except Exception as e:
        if logger:
            logger.error(f"Error processing spread data: {e}")
        else:
            print(f"Error processing spread data: {e}")
        return False


if __name__ == "__main__":
    getSpreads()