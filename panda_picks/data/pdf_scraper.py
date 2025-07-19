# panda_picks/data/pdf_scraper.py
import pandas as pd
from tabula import read_pdf
from panda_picks import config
from panda_picks.db import database as db


def extract_team_grades(pdf_path):
    try:
        print(f"Reading PDF file: {pdf_path}")
        # Extract all tables from first page
        tables = read_pdf(pdf_path, pages=1, multiple_tables=True)

        if len(tables) == 0:
            raise ValueError("No tables found in PDF")

        # Get the table (even if only one)
        main_table = tables[0].copy()

        # Extract team names from the data
        team_names = []
        for i in range(1, 33):  # Assuming 32 teams
            team_row = main_table.iloc[i]
            if pd.notna(team_row.get('Unnamed: 2')):
                team_name = team_row['Unnamed: 2']
                team_names.append(team_name)
            else:
                print(f"Warning: No team name found in row {i}: {team_row}")

        print(f"Extracted team names count: {len(team_names)}")

        # Extract grades (first 32 rows after header)
        grades_df = main_table.iloc[1:33].reset_index(drop=True)
        # Looking at the column list in the output, we need to map them correctly
        # Fixed column mapping - properly aligned and no duplicates
        column_mapping = {
            'Unnamed: 0': 'RANK',      # This is correct
            'Unnamed: 1': 'TEAM_PLACEHOLDER',  # Temporary column
            'Unnamed: 2': 'TEAM',  # Verified team name is in Unnamed: 2
            'Unnamed: 4': 'OVR',   # Verified OVR is in Unnamed: 4
            'Unnamed: 5': 'OFF',   # Verified OFF is in Unnamed: 5
            'Unnamed: 6': 'PASS',  # Verified PASS is in Unnamed: 6
            'Unnamed: 10': 'RDEF',  # Verified RDEF is in Unnamed: 10
            'Unnamed: 8': 'RBLK',
            'Unnamed: 9': 'DEF',
            'Unnamed: 7': 'RUN',
            'DEFENSE': 'TACK',
            'Unnamed: 11': 'PRSH',
            'Unnamed: 12' : 'COV' # SPEC maps to PRSH
        }
    # DEFENSE header maps to DEF values
        # Rename columns first
        grades_df = grades_df.rename(columns=column_mapping)

        # Split the OFFENSE column which contains both PBLK and RECV values
        if 'OFFENSE' in grades_df.columns:
            # Split the OFFENSE column into PBLK and RECV
            grades_df[['PBLK', 'RECV']] = grades_df['OFFENSE'].str.split(' ', expand=True)
            # Drop the original OFFENSE column
            grades_df = grades_df.drop(columns=['OFFENSE'])

        # Only keep the final columns we need
        final_columns = ['TEAM', 'OVR', 'OFF', 'PASS', 'PBLK', 'RECV', 'RUN', 'RBLK', 'DEF', 'RDEF', 'TACK', 'PRSH', 'COV']
        grades_df = grades_df[final_columns]

        # Verify team names match after column renaming
        if 'TEAM' in grades_df.columns:
            # Team column already exists from renaming
            team_count = grades_df['TEAM'].notna().sum()
            if team_count != len(team_names):
                print(f"WARNING: Expected {len(team_names)} teams but found {team_count}")

        # Ensure all required columns exist
        required_columns = ['TEAM', 'OVR', 'OFF', 'PASS', 'RUN', 'RECV', 'PBLK', 'RBLK', 'DEF', 'RDEF', 'TACK', 'PRSH', 'COV']
        for col in required_columns:
            if col not in grades_df.columns:
                print(f"WARNING: Required column {col} is missing!")

        print(f"Final grades table (first 5 rows):\n{grades_df.head(5)}")
        return grades_df

    except Exception as e:
        print(f"ERROR in extract_team_grades: {e}")
        raise

def merge_with_abbreviations(grades_df, abbrev_path):
    """
    Merge team grades with abbreviation data more efficiently.

    Args:
        grades_df: DataFrame with team grades
        abbrev_path: Path to the abbreviations CSV file

    Returns:
        DataFrame with merged data
    """
    try:
        # Load team abbreviations with only needed columns
        abbrevs = pd.read_csv(abbrev_path, usecols=['TEAM', 'Abrev'])

        # Merge grades with abbreviations
        merged_df = pd.merge(grades_df, abbrevs, on='TEAM', how='inner')

        # Filter unnamed columns in one operation
        unnamed_cols = [col for col in merged_df.columns if col.startswith('Unnamed:')]

        # Create final dataframe with correct columns in one operation
        result_df = merged_df.drop(columns=['TEAM'] + unnamed_cols).rename(columns={'Abrev': 'TEAM'})

        # Define desired column order
        column_order = [
            'TEAM', 'OVR', 'OFF', 'PASS', 'RUN', 'RECV',
            'PBLK', 'RBLK', 'DEF', 'RDEF', 'TACK', 'PRSH', 'COV'
        ]

        # Check if all columns exist
        missing_cols = [col for col in column_order if col not in result_df.columns]
        if missing_cols:
            raise ValueError(f"Missing columns in dataframe: {missing_cols}")

        return result_df[column_order]

    except Exception as e:
        raise Exception(f"Error merging with abbreviations: {e}")

def getGrades():
    """Process NFL team grades from PDF and save to CSV."""
    try:
        pdf_file = config.PFF_TEAM_GRADES_PDF
        abbrev_file = config.NFL_TRANSLATIONS_CSV
        output_file = config.TEAM_GRADES_CSV

        # Check if files exist
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_file}")

        if not abbrev_file.exists():
            raise FileNotFoundError(f"Abbreviations file not found: {abbrev_file}")

        # Extract grades and process
        grades_df = extract_team_grades(pdf_file)
        processed_df = merge_with_abbreviations(grades_df, abbrev_file)

        # Save to CSV
        processed_df.to_csv(output_file, index=False)
        print(f"Team grades saved to {output_file}")
        return True

    except Exception as e:
        print(f"Error processing team grades: {e}")
        return False

if __name__ == '__main__':
    # First get and process the grades data
    if getGrades():
        # Then store it in the database
        db.store_grades_data()