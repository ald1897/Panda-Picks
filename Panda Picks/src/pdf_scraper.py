import pandas as pd
from tabula import read_pdf
from pathlib import Path
import os


def extract_team_grades(pdf_path):
    """
    Extract NFL team grades from a PDF file using more efficient operations.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        DataFrame containing extracted grades
    """
    try:
        # Read the first page of the PDF
        tables = read_pdf(pdf_path, pages=1)
        if not tables or len(tables) == 0:
            raise ValueError("No tables found in PDF")

        # # Print tables to a txt fiile for debugging
        # with open("debug_tables.txt", "w") as f:
        #     print(tables)
        #     f.write(str(tables))
        # if len(tables) < 2:
        #     raise ValueError("Expected at least two tables in PDF, found: {}".format(len(tables)))
        # # Print the first table for debugging
        # print("Tables extracted from PDF:")
        # for i, table in enumerate(tables):
        #     print(f"Table {i}:")
        #     print(table.head())
        print(tables)
        df = tables[0]
        print(df.head())
        print(df.columns)

        # Keep only needed columns and rename in one operation
        cols_to_keep = ['OFFENSE', 'DEFENSE', 'SPEC'] + [col for col in df.columns if col.startswith('Unnamed:')]
        df = df[cols_to_keep]
        print(df.head())

        # Split the OFFENSE column more efficiently
        split_cols = df['OFFENSE'].str.split(" ", n=1, expand=True)
        df['PASS BLOCK'] = split_cols[0]
        df['RECEIVING'] = split_cols[1]

        # Drop processed columns and rename all at once
        df.drop(columns=['OFFENSE', 'SPEC'], inplace=True)

        # Create mapping dictionary for column renaming
        rename_map = {
            'Unnamed: 2': 'TEAM',
            'Unnamed: 4': 'OVR',
            'Unnamed: 5': 'OFF',
            'Unnamed: 6': 'PASS',
            'Unnamed: 7': 'RUN',
            'Unnamed: 8': 'RBLK',
            'Unnamed: 9': 'DEF',
            'Unnamed: 10': 'RDEF',
            'DEFENSE': 'TACK',
            'Unnamed: 11': 'PRSH',
            'Unnamed: 12': 'COV',
            'PASS BLOCK': 'PBLK',
            'RECEIVING': 'RECV'
        }

        # Rename columns and drop rows with NaN values
        df = df.rename(columns=rename_map).dropna()

        print("Extracted team grades successfully.")
        # print(df.head())  # Display the first few rows for verification

        return df

    except Exception as e:
        raise Exception(f"Error extracting team grades: {e}")


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
    getGrades()
# import pandas as pd
# from tabula import read_pdf
# from pathlib import Path
#
#
# def extract_team_grades(pdf_path):
#     """
#     Extract NFL team grades from a PDF file.
#
#     Args:
#         pdf_path: Path to the PDF file
#
#     Returns:
#         DataFrame containing extracted grades
#     """
#     # Read the first page of the PDF
#     df = read_pdf(pdf_path, pages=1)[0]
#
#     # Drop unnecessary columns
#     df = df.drop(columns=['Unnamed: 0', 'Unnamed: 1', 'POINTS', 'Unnamed: 3'])
#
#     # Split the OFFENSE column into PASS BLOCK and RECEIVING
#     new = df['OFFENSE'].str.split(" ", n=1, expand=True)
#     df['PASS BLOCK'] = new[0]
#     df['RECEIVING'] = new[1]
#
#     # Drop processed columns
#     df.drop(columns=['OFFENSE', 'SPEC'], inplace=True)
#
#     # Rename columns for clarity
#     df = df.rename(columns={
#         'Unnamed: 2': 'TEAM',
#         'Unnamed: 4': 'OVR',
#         'Unnamed: 5': 'OFF',
#         'Unnamed: 6': 'PASS',
#         'Unnamed: 7': 'RUN',
#         'Unnamed: 8': 'RBLK',
#         'Unnamed: 9': 'DEF',
#         'Unnamed: 10': 'RDEF',
#         'DEFENSE': 'TACK',
#         'Unnamed: 11': 'PRSH',
#         'Unnamed: 12': 'COV',
#         'PASS BLOCK': 'PBLK',
#         'RECEIVING': 'RECV'
#     })
#
#     # Remove rows with missing values
#     df.dropna(inplace=True)
#
#     return df
#
#
# def merge_with_abbreviations(grades_df, abbrev_path):
#     """
#     Merge team grades with abbreviation data.
#
#     Args:
#         grades_df: DataFrame with team grades
#         abbrev_path: Path to the abbreviations CSV file
#
#     Returns:
#         DataFrame with merged data
#     """
#     # Load team abbreviations
#     abbrevs = pd.read_csv(abbrev_path)
#
#     # Merge grades with abbreviations
#     merged_df = pd.merge(grades_df, abbrevs, on='TEAM')
#
#     # Drop unnamed columns efficiently
#     drop_cols = [col for col in merged_df.columns if col.startswith('Unnamed:')]
#     merged_df.drop(columns=['TEAM'] + drop_cols, inplace=True)
#
#     # Rename and reorder columns
#     merged_df = merged_df.rename(columns={'Abrev': 'TEAM'})
#
#     column_order = [
#         'TEAM', 'OVR', 'OFF', 'PASS', 'RUN', 'RECV',
#         'PBLK', 'RBLK', 'DEF', 'RDEF', 'TACK', 'PRSH', 'COV'
#     ]
#
#     return merged_df[column_order]
#
#
# def getGrades():
#     """
#     Process NFL team grades from PDF and save to CSV.
#     """
#     try:
#         # Define file paths using Path
#         data_dir = Path("Data")
#         pdf_file = data_dir / "Grades" / "PFFTeamGrades.pdf"
#         abbrev_file = data_dir / "Grades" / "NFL_translations.csv"
#         output_file = data_dir / "Grades" / "TeamGrades.csv"
#
#         # Ensure output directory exists
#         output_file.parent.mkdir(parents=True, exist_ok=True)
#
#         print(f"Extracting team grades from {pdf_file}...")
#         grades_df = extract_team_grades(pdf_file)
#
#         print("Merging with team abbreviations...")
#         processed_df = merge_with_abbreviations(grades_df, abbrev_file)
#
#         # Save to CSV
#         processed_df.to_csv(output_file, index=False)
#         print(f"Team grades saved to {output_file}")
#
#     except FileNotFoundError as e:
#         print(f"Error: Could not find file - {e}")
#     except Exception as e:
#         print(f"Error processing team grades: {e}")
#
#
# if __name__ == '__main__':
#     getGrades()
# # import pandas as pd
# # from tabula import read_pdf
# #
# #
# # def getGrades():
# #     df = read_pdf(r"Data/Grades/PFFTeamGrades.pdf", pages=1)
# #     abrevs = pd.read_csv(r"Data/Grades/NFL_translations.csv")
# #     df = df[0]
# #     df = df.drop(columns=['Unnamed: 0', 'Unnamed: 1', 'POINTS', 'Unnamed: 3'])
# #     new = df['OFFENSE'].str.split(" ", n=1, expand=True)
# #     # making separate PBLK column from new data frame
# #     df['PASS BLOCK'] = new[0]
# #     # making separate RCEV column from new data frame
# #     df['RECEIVING'] = new[1]
# #     # Dropping old Name columns
# #     df.drop(columns=['OFFENSE'], inplace=True)
# #     df.drop(columns=['SPEC'], inplace=True)
# #     df = df.rename(columns={
# #         'Unnamed: 2': 'TEAM',
# #         'Unnamed: 4': 'OVR',
# #         'Unnamed: 5': 'OFF',
# #         'Unnamed: 6': 'PASS',
# #         'Unnamed: 7': 'RUN',
# #         'Unnamed: 8': 'RBLK',
# #         'Unnamed: 9': 'DEF',
# #         'Unnamed: 10': 'RDEF',
# #         'DEFENSE': 'TACK',
# #         'Unnamed: 11': 'PRSH',
# #         'Unnamed: 12': 'COV',
# #         'PASS BLOCK': 'PBLK',
# #         'RECEIVING': 'RECV'
# #     })
# #     df.dropna(inplace=True)
# #     new_teams = pd.merge(df, abrevs, on='TEAM')
# #     new_teams.drop(columns=[
# #         # 'RANK',
# #         'TEAM',
# #         'Unnamed: 2',
# #         'Unnamed: 3',
# #         'Unnamed: 4',
# #         'Unnamed: 5',
# #         'Unnamed: 6',
# #         'Unnamed: 7',
# #         'Unnamed: 8',
# #         'Unnamed: 9',
# #         'Unnamed: 10',
# #         'Unnamed: 11',
# #         'Unnamed: 12',
# #         'Unnamed: 13',
# #         'Unnamed: 14',
# #         'Unnamed: 15',
# #         'Unnamed: 16'], inplace=True)
# #     new_teams = new_teams.rename(columns={'Abrev': 'TEAM'})
# #     new_teams = new_teams[
# #         ['TEAM', 'OVR', 'OFF', 'PASS', 'RUN', 'RECV', 'PBLK', 'RBLK', 'DEF', 'RDEF', 'TACK', 'PRSH', 'COV']]
# #     new_teams.to_csv(r"Data/Grades/TeamGrades.csv", index=False)
# #
# #
# # if __name__ == '__main__':
# #     getGrades()
