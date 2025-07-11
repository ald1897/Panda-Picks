import pandas as pd
import numpy as np
from pathlib import Path
import logging


def makePicks(season="2022", data_dir=None):
    """
    Generate weekly NFL game picks based on team grades and matchups.

    Args:
        season (str): NFL season year
        data_dir (Path, optional): Base directory for data files
    """
    try:
        # Set up logging
        logger = logging.getLogger("PandaPicks") if logging.getLogger("PandaPicks").handlers else None
        log = logger.info if logger else print

        # Define paths using Path objects
        if data_dir is None:
            data_dir = Path("Data")

        grades_file = data_dir / "Grades" / "TeamGrades.csv"
        matchups_dir = data_dir / "Matchups"
        picks_dir = data_dir / "Picks"
        picks_dir.mkdir(parents=True, exist_ok=True)

        # Check if grades file exists
        if not grades_file.exists():
            raise FileNotFoundError(f"Team grades file not found: {grades_file}")

        # Load team grades once for efficiency
        log(f"Loading team grades from {grades_file}")
        grades = pd.read_csv(grades_file)

        # Create away team grades mapping in one operation
        away_grades = grades.copy()
        rename_map = {col: f'OPP {col}' for col in away_grades.columns if col != 'TEAM'}
        away_grades = away_grades.rename(columns=rename_map)

        # Process each week
        for week in range(1, 19):
            week_str = str(week)
            matchup_file = matchups_dir / f"matchups_WEEK{week_str}.csv"

            if not matchup_file.exists():
                log(f"Matchup file for WEEK {week_str} not found. Skipping...")
                continue

            log(f"Processing WEEK {week_str}...")

            # Load matchup data efficiently
            matchups = pd.read_csv(matchup_file).dropna(how="all")

            # Perform merge operations more efficiently
            # First rename team column for home team merge
            home_grades = grades.rename(columns={'TEAM': 'Home Team'})
            matchups = pd.merge(matchups, home_grades, on="Home Team")

            # Then rename team column for away team merge
            away_grades = away_grades.rename(columns={'TEAM': 'Away Team'})
            matchups = pd.merge(matchups, away_grades, on="Away Team")

            # Calculate all advantages in a single step using vectorized operations
            results = matchups.copy()

            # Define advantage calculations in a dictionary for cleaner code
            advantage_calcs = {
                'Overall Adv': 'OVR - `OPP OVR`',
                'Offense Adv': 'OFF - `OPP DEF`',
                'Passing Adv': 'PASS - ((`OPP PRSH` + `OPP COV`) / 2)',
                'Pass Block Adv': 'PBLK - `OPP PRSH`',
                'Receving Adv': 'RECV - `OPP COV`',
                'Running Adv': 'RUN - `OPP RDEF`',
                'Run Block Adv': 'RBLK - `OPP RDEF`',
                'Defense Adv': 'DEF - `OPP OFF`',
                'Run Defense Adv': 'RDEF - ((`OPP RUN` + `OPP RBLK`) / 2)',
                'Tackling Adv': 'TACK - ((`OPP RUN` + `OPP RECV`) / 2)',
                'Pass Rush Adv': 'PRSH - ((`OPP PBLK` + `OPP PASS`) / 2)',
                'Coverage Adv': 'COV - ((`OPP RECV` + `OPP PBLK`) / 2)'
            }

            # Apply all advantage calculations
            for adv_name, formula in advantage_calcs.items():
                results[adv_name] = results.eval(formula)

            # Generate game picks using vectorized conditions
            conditions = [
                (results['Overall Adv'] >= 10) &
                (matchups['OVR'] > matchups['OPP OVR']) &
                (matchups['DEF'] > matchups['OPP OFF']),

                (results['Overall Adv'] <= -10) &
                (matchups['OVR'] < matchups['OPP OVR']) &
                (matchups['DEF'] < matchups['OPP OFF'])
            ]
            choices = [results['Home Team'], results['Away Team']]
            results['Game Pick'] = np.select(conditions, choices, default='No Pick')

            # Filter and save results
            results = results[results['Game Pick'] != 'No Pick']

            # Select only needed columns for output
            pick_columns = [
                               'Game Date', 'Home Team', 'Home Spread', 'Away Team',
                               'Away Spread', 'Game Pick', 'Overall Adv'
                           ] + list(advantage_calcs.keys())

            # Filter out empty results
            if len(results) == 0:
                log(f"No picks generated for WEEK {week_str}")
                continue

            # Sort by advantage and save
            results = results[pick_columns].sort_values(by=['Overall Adv'], ascending=False)
            output_file = picks_dir / f"WEEK{week_str}.csv"
            results.to_csv(output_file, index=False, float_format='%.2f')
            log(f"Saved {len(results)} picks for WEEK {week_str} to {output_file}")

        return True

    except FileNotFoundError as e:
        log(f"File not found: {e}")
        return False
    except Exception as e:
        log(f"Error processing picks: {e}")
        return False


if __name__ == '__main__':
    makePicks()