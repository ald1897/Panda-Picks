import pandas as pd
from tabula import read_pdf
from pathlib import Path
import os
import db.db as db


# def extract_team_grades(pdf_path):
#     """
#     Extract NFL team grades from a PDF file using more efficient operations.
#
#     Args:
#         pdf_path: Path to the PDF file
#
#     Returns:
#         DataFrame containing extracted grades
#     """
#     try:
#         # Read the first page of the PDF
#         tables = read_pdf(pdf_path, pages=1)
#         if not tables or len(tables) == 0:
#             raise ValueError("No tables found in PDF")
#
#         # # Print tables to a txt fiile for debugging
#         # with open("debug_tables.txt", "w") as f:
#         #     print(tables)
#         #     f.write(str(tables))
#         # if len(tables) < 2:
#         #     raise ValueError("Expected at least two tables in PDF, found: {}".format(len(tables)))
#         # # Print the first table for debugging
#         # print("Tables extracted from PDF:")
#         # for i, table in enumerate(tables):
#         #     print(f"Table {i}:")
#         #     print(table.head())
#         print(tables)
#         df = tables[0]
#         print(df.head())
#         print(df.columns)
#
#         # Keep only needed columns and rename in one operation
#         cols_to_keep = ['OFFENSE', 'DEFENSE', 'SPEC'] + [col for col in df.columns if col.startswith('Unnamed:')]
#         df = df[cols_to_keep]
#         print(df)
#
#         # Split the OFFENSE column more efficiently
#         split_cols = df['OFFENSE'].str.split(" ", n=1, expand=True)
#         df['PASS BLOCK'] = split_cols[0]
#         df['RECEIVING'] = split_cols[1]
#
#         # Drop processed columns and rename all at once
#         df.drop(columns=['OFFENSE', 'SPEC'], inplace=True)
#
#         # Create mapping dictionary for column renaming
#         rename_map = {
#             'Unnamed: 1': 'TEAM',
#             'Unnamed: 4': 'OVR',
#             'Unnamed: 5': 'OFF',
#             'Unnamed: 6': 'PASS',
#             'Unnamed: 7': 'RUN',
#             'Unnamed: 8': 'RBLK',
#             'Unnamed: 9': 'DEF',
#             'Unnamed: 10': 'RDEF',
#             'DEFENSE': 'TACK',
#             'Unnamed: 11': 'PRSH',
#             'Unnamed: 12': 'COV',
#             'PASS BLOCK': 'PBLK',
#             'RECEIVING': 'RECV'
#         }
#
#         # Rename columns and drop rows with NaN values
#         df = df.rename(columns=rename_map).dropna()
#
#         print("Extracted team grades successfully.")
#         # print(df.head())  # Display the first few rows for verification
#
#         return df
#
#     except Exception as e:
#         raise Exception(f"Error extracting team grades: {e}")
def extract_team_grades(pdf_path):
    try:
        print(f"Reading PDF file: {pdf_path}")
        # Extract all tables from first page
        tables = read_pdf(pdf_path, pages=1, multiple_tables=True)
        print(f"Number of tables extracted: {len(tables)}")

        for i, table in enumerate(tables):
            print(f"Table {i} shape: {table.shape}")
            print(f"Table {i} preview:\n{table.head(5)}")
            print(f"Table {i} columns: {table.columns.tolist()}")

        if len(tables) == 0:
            raise ValueError("No tables found in PDF")

        # Get the table (even if only one)
        main_table = tables[0].copy()
        print(f"Main table shape: {main_table.shape}")

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
        print(f"Extracted team names: {team_names}")

        # Extract grades (first 32 rows after header)
        grades_df = main_table.iloc[1:33].reset_index(drop=True)
        print(f"Grades DataFrame shape: {grades_df.shape}")
        print(f"Grades DataFrame columns: {grades_df.columns.tolist()}")
        # print each column in the grades DataFrame
        for col in grades_df.columns:
            print(f"Column '{col}' preview:\n{grades_df[col].head(5)}")
        # Print the first 5 rows of the grades DataFrame
        print(f"Grades DataFrame preview:\n{grades_df.head(5)}")

        # Looking at the column list in the output, we need to map them correctly
        # The 'DEFENSE' column probably contains 'TACK' data and needs to be included
        # Corrected column mapping to fix the misalignment
        column_mapping = {
            'Unnamed: 0': 'RANK',  # This is correct
            'Unnamed: 2': 'TEAM',  # Team name is in Unnamed: 2
            'Unnamed: 4': 'OVR',   # Shift each value one column to the left
            'Unnamed: 5': 'OFF',
            'Unnamed: 6': 'PASS',
            'Unnamed: 7': 'PBLK',
            'Unnamed: 8': 'RECV',
            'Unnamed: 9': 'RUN',
            'Unnamed: 10': 'RBLK',
            'DEFENSE': 'DEF',     # DEFENSE header maps to DEF values
            'Unnamed: 11': 'RDEF',
            'Unnamed: 11': 'TACK',
            'Unnamed: 12': 'PRSH',
            'SPEC': 'COV'         # SPEC header maps to COV values
        }

        # Add RDEF column (not in original mapping)
        grades_df['RDEF'] = grades_df['Unnamed: 10']  # Copy DEF column as RDEF for now

        # Only keep columns we need for mapping
        columns_to_keep = [col for col in grades_df.columns if col in column_mapping or col == 'RDEF']
        grades_df = grades_df[columns_to_keep]

        # Rename columns
        grades_df = grades_df.rename(columns=column_mapping)
        print(f"Columns after renaming: {grades_df.columns.tolist()}")
        print(f"Grades DataFrame shape: {grades_df.shape}")
        print(f"Grades DataFrame preview:\n{grades_df.head(5)}")

        # Add team column
        if len(team_names) == grades_df.shape[0]:
            grades_df.insert(0, 'TEAM', team_names)
        else:
            print(f"WARNING: Team count ({len(team_names)}) does not match grades count ({grades_df.shape[0]})")
            raise ValueError(f"Mismatch: {len(team_names)} teams vs {grades_df.shape[0]} grades")

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
    """
    Process NFL team grades from PDF and save to CSV using optimized methods.
    """
    try:

        # Get the directory where the script is located
        script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        # Then construct paths relative to that
        pdf_file = script_dir.parent / "Data" / "Grades" / "PFFTeamGrades.pdf"
        print(f"Current working directory: {os.getcwd()}")
        print(f"Looking for PDF at: {pdf_file.absolute()}")
        # Define file paths using Path
        # pdf_file = Path("Panda Picks/Data/Grades/PFFTeamGrades.pdf")
        # pdf_file = data_dir / "Grades" / "PFFTeamGrades.pdf"
        abbrev_file = script_dir.parent / "Data" / "Grades" / "NFL_Translations.csv"
        output_file = script_dir.parent / "Data" / "Grades" / "TeamGrades.csv"

        # Check if files exist
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_file}")

        if not abbrev_file.exists():
            raise FileNotFoundError(f"Abbreviations file not found: {abbrev_file}")

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        print(f"Extracting team grades from {pdf_file}...")

        grades_df = extract_team_grades(pdf_file)

        print(f"Merging with team abbreviations from {abbrev_file}...")
        processed_df = merge_with_abbreviations(grades_df, abbrev_file)

        # Save to CSV efficiently
        processed_df.to_csv(output_file, index=False)
        print(f"Team grades saved to {output_file}")
        return True

    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
        return False
    except Exception as e:
        print(f"Error processing team grades: {e}")
        return False


if __name__ == '__main__':
    # First get and process the grades data
    if getGrades():
        # Then store it in the database
        db.store_grades_data()