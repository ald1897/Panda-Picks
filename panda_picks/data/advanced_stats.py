"""
Advanced NFL Stats Collection and Analysis Module

This module collects advanced offensive and defensive statistics through web scraping from Sumer Sports,
processes them to create composite scores, and stores the data in an SQLite database.
The processed data can be used for NFL game prediction and analysis.

Features:
- Web scrapes offensive and defensive stats from Sumer Sports website with advanced browser spoofing
- Cleans and standardizes raw statistics for NFL teams
- Stores raw stats and composite scores separately
- Handles error cases gracefully with retries and logging
"""

import requests
import pandas as pd
import numpy as np
import sqlite3
import logging
import time
import os
import random
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Try to import from the module, but fallback to direct connection if that fails
try:
    from panda_picks.db.database import get_connection
    from panda_picks import config
except ImportError:
    # Define a fallback function if the module import fails
    def get_connection():
        # Try the main database path first
        main_db_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'database', 'nfl_data.db')
        if os.path.exists(main_db_path):
            print(f"Using database at: {os.path.abspath(main_db_path)}")
            return sqlite3.connect(main_db_path)

        # Fallback to the secondary database path
        secondary_db_path = os.path.join(os.path.dirname(__file__), '..', 'nfl_data.db')
        if os.path.exists(secondary_db_path):
            print(f"Using database at: {os.path.abspath(secondary_db_path)}")
            return sqlite3.connect(secondary_db_path)

        # If neither exists, create in the main location
        os.makedirs(os.path.dirname(main_db_path), exist_ok=True)
        print(f"Creating new database at: {os.path.abspath(main_db_path)}")
        return sqlite3.connect(main_db_path)

# Configure logging - write to both file and console
log_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'panda_picks.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # This will output logs to console as well
    ]
)
logger = logging.getLogger('advanced_stats')

# Statistic weights for composite score calculation
WEIGHTS = {
    'offense': {
        'epa_per_play': 30,        # Overall offensive efficiency (highest weight)
        'epa_per_pass': 20,        # Passing efficiency (very important)
        'epa_per_rush': 10,        # Rushing efficiency (important but less than passing)
        'Success %': 15,           # Success rate (important contextual metric)
        'Comp %': 5,               # Completion percentage
        'YAC EPA/Att': 8,          # Value from yards after catch
        'ADoT': 3,                 # Average depth of target
        'Eckel %': 10,             # Drive success (reaching scoring position)
        'PROE': 3,                 # Pass Rate Over Expected (play-calling tendencies)
        'Sack %': -5,              # Negative impact of sacks (negative weight)
        'Scramble %': 2,           # Scrambling ability
        'Int %': -7                # Negative impact of interceptions (negative weight)
    },
    'defense': {
        'epa_per_play': -30,       # Overall defensive efficiency (negative because lower is better for defense)
        'epa_per_pass': -20,       # Pass defense efficiency
        'epa_per_rush': -10,       # Rush defense efficiency
        'Success %': -15,          # Success rate allowed (negative because lower is better)
        'Comp %': -5,              # Completion percentage allowed
        'YAC EPA/Att': -8,         # YAC allowed
        'ADoT': 2,                 # Higher depth of target often means better coverage underneath
        'Eckel %': -10,            # Drive success allowed
        'Sack %': 7,               # Positive impact of generating sacks
        'Int %': 7,                # Positive impact of generating interceptions
        'Pass Yards': -3,          # Pass yards allowed (minor factor)
        'Rush Yards': -2           # Rush yards allowed (minor factor)
    }
}

# Web scraping URLs
SCRAPE_URLS = {
    'offense': "https://sumersports.com/teams/offensive/",
    'defense': "https://sumersports.com/teams/defensive/"
}

# Team name standardization mapping
TEAM_NAME_MAP = {
    'CLE': 'CLV',
    'ARI': 'ARZ',
    'LAR': 'LA',
    'JAC': 'JAX',
    'WSH': 'WAS',
    'LV': 'LVR'
}

# Column name mappings (web scraped column name -> our database column name)
COLUMN_MAPPING = {
    'Team': 'team',
    'EPA/Play': 'epa_per_play',
    'EPA/Pass': 'epa_per_pass',
    'EPA/Dropback': 'epa_per_dropback',
    'YAC EPA': 'yac_epa',
    'EPA/Rush': 'epa_per_rush',
    'Comp%': 'comp_pct',
    'Scramble Rate': 'scramble_rate',
    'Pressure Rate': 'pressure_rate',
    'INT%': 'int_rate',
    'Sack%': 'sack_rate'
}

# Browser user agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
]

# Common cookies for browser simulation
COOKIES_STRING = '_cs_c=0; _hp2_ses_props.2415233196=%7B%22r%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%2C%22ts%22%3A1753412329569%2C%22d%22%3A%22sumersports.com%22%2C%22h%22%3A%22%2Fteams%2Fdefensive%2F%22%7D; _vcrcs=1.1753412652.3600.NmMwYzcyMTUyNzllM2Q4MTI0Y2RiNzI4MDJhZWQ4NjA=.066c163b6f9b429dffe7add196a3805a'

class AdvancedStatsCollector:
    """
    Collects and processes advanced NFL team statistics.
    """

    def __init__(self, season: int = datetime.now().year):
        """
        Initialize the stats collector.

        Args:
            season: NFL season year (default: current year)
        """
        self.season = season
        try:
            self.conn = get_connection()
            # Test the database connection
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(advanced_stats)")
            tables = cursor.fetchall()
            logger.info(f"Connected to database. Found table schema: {tables}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            print(f"Error connecting to database: {str(e)}")
            raise

        self.session = self._create_browser_session()

    def _create_browser_session(self) -> requests.Session:
        """
        Create a browser-like session with proper headers and cookies.

        Returns:
            Configured requests.Session object
        """
        session = requests.Session()

        # Set a realistic user agent
        user_agent = random.choice(USER_AGENTS)

        # Set headers to mimic a real browser
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'Cache-Control': 'max-age=0',
        })

        # Parse and set cookies
        cookies_dict = {}
        for cookie_part in COOKIES_STRING.split('; '):
            if '=' in cookie_part:
                name, value = cookie_part.split('=', 1)
                cookies_dict[name] = value

        # Add cookies to the session
        session.cookies.update(cookies_dict)

        return session

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def _get_referrer(self, url: str) -> str:
        """
        Generate a plausible referrer URL for the given URL.

        Args:
            url: Target URL

        Returns:
            Referrer URL
        """
        parsed_url = urlparse(url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # Possible referrers
        referrers = [
            f"{domain}/",  # Homepage
            "https://www.google.com/",  # Google search
            f"{domain}/teams/",  # Teams page
        ]

        # Use the most specific referrer for the defensive page
        if "defensive" in url:
            return f"{domain}/teams/defensive/personnel-tendency/"
        elif "offensive" in url:
            return f"{domain}/teams/offensive/personnel-tendency/"
        else:
            return random.choice(referrers)

    def scrape_team_data(self, stats_type: str, max_retries: int = 3) -> Optional[pd.DataFrame]:
        """
        Scrape team statistics data from Sumer Sports website.

        Args:
            stats_type: Type of statistics ('offense' or 'defense')
            max_retries: Maximum number of retry attempts

        Returns:
            DataFrame containing the scraped statistics data or None if scraping failed
        """
        url = SCRAPE_URLS.get(stats_type)
        if not url:
            logger.error(f"Invalid stats type: {stats_type}")
            return None

        # First, visit the homepage to establish session and cookies
        try:
            logger.info("Visiting homepage to establish session")
            self.session.get("https://sumersports.com/", timeout=10)
            time.sleep(2)  # Pause to be more human-like
        except Exception as e:
            logger.warning(f"Failed to visit homepage: {e}")

        retries = 0
        while retries < max_retries:
            try:
                # Add specific headers for this request
                referrer = self._get_referrer(url)
                self.session.headers.update({'Referer': referrer})

                # Slight delay between requests (more human-like)
                time.sleep(1 + random.random())

                logger.info(f"Scraping {stats_type} data from {url}")
                response = self.session.get(url, timeout=15)
                response.raise_for_status()

                if 'text/html' not in response.headers.get('Content-Type', ''):
                    logger.warning(f"Unexpected content type: {response.headers.get('Content-Type')}")

                # Save response for debugging
                debug_file = os.path.join(os.path.dirname(__file__), f"{stats_type}_response.html")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.info(f"Saved raw HTML response to {debug_file}")

                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find the main data table - more robust selector
                tables = soup.find_all('table')
                if not tables:
                    logger.error(f"No tables found on {url}")
                    with open(debug_file, 'a', encoding='utf-8') as f:
                        f.write("\n\n--- No tables found in HTML ---\n")
                    retries += 1
                    time.sleep(5)  # Longer delay after failure
                    continue

                table = tables[0]  # Use the first table found

                # Try to find headers - more robust approach
                headers = []
                header_rows = table.find_all('tr')
                for row in header_rows:
                    th_elements = row.find_all(['th', 'td'])  # Look for th or td elements
                    if th_elements:
                        headers = [th.text.strip() for th in th_elements]
                        if headers and len(headers) > 2:  # Ensure we have reasonable headers
                            break

                if not headers:
                    logger.error("Could not find headers in table")
                    with open(debug_file, 'a', encoding='utf-8') as f:
                        f.write("\n\n--- No headers found in table ---\n")
                    retries += 1
                    time.sleep(5)
                    continue

                # Extract data rows - more robust approach
                rows = []
                body = table.find('tbody') if table.find('tbody') else table
                for tr in body.find_all('tr'):
                    td_elements = tr.find_all('td')
                    if td_elements and len(td_elements) > 2:  # Skip header rows
                        row_data = [td.text.strip() for td in td_elements]
                        if row_data and len(row_data) == len(headers):
                            rows.append(row_data)

                if not rows:
                    logger.error("No data rows found in table")
                    with open(debug_file, 'a', encoding='utf-8') as f:
                        f.write("\n\n--- No data rows found in table ---\n")
                    retries += 1
                    time.sleep(5)
                    continue

                # Create DataFrame
                df = pd.DataFrame(rows, columns=headers)

                # Clean and transform data
                df = self._clean_scraped_data(df, stats_type)

                if df.empty:
                    logger.error("DataFrame is empty after cleaning")
                    retries += 1
                    time.sleep(5)
                    continue

                logger.info(f"Successfully scraped {stats_type} data with {len(df)} rows")
                return df

            except requests.exceptions.RequestException as e:
                retries += 1
                wait_time = 2 ** retries  # Exponential backoff
                logger.warning(f"Request failed: {e}. Retry {retries}/{max_retries} in {wait_time}s")
                time.sleep(wait_time)

                # Create a new session with fresh cookies on failure
                self.session = self._create_browser_session()

            except Exception as e:
                logger.error(f"Unexpected error scraping {stats_type} data: {str(e)}")
                retries += 1
                wait_time = 2 ** retries
                logger.warning(f"Retrying {retries}/{max_retries} in {wait_time}s")
                time.sleep(wait_time)

                # Create a new session with fresh cookies on failure
                self.session = self._create_browser_session()

        logger.error(f"Failed to scrape {stats_type} data from {url} after {max_retries} attempts")
        return None

    def _clean_scraped_data(self, df: pd.DataFrame, stats_type: str) -> pd.DataFrame:
        """
        Clean and transform scraped data into the format needed for analysis.

        Args:
            df: Raw scraped DataFrame
            stats_type: Type of statistics ('offense' or 'defense')

        Returns:
            Cleaned DataFrame
        """
        # Handle empty DataFrame
        if df.empty:
            logger.error(f"Received empty DataFrame for {stats_type}")
            return pd.DataFrame()

        # Make a copy to avoid modifying the original
        result = df.copy()

        try:
            # Log the original columns for debugging
            logger.info(f"Original columns: {result.columns.tolist()}")

            # Rename columns according to our mapping
            column_renamed = False
            for original, new_name in COLUMN_MAPPING.items():
                if original in result.columns:
                    result.rename(columns={original: new_name}, inplace=True)
                    column_renamed = True

            if not column_renamed:
                logger.warning("No columns were renamed - column names might not match expected format")

            # Ensure team column exists
            team_col = None
            for col in result.columns:
                if col.lower() in ['team', 'team name', 'name', 'team abbr', 'team_abbr']:
                    team_col = col
                    break

            if team_col:
                logger.info(f"Found team column: {team_col}")
                result.rename(columns={team_col: 'team'}, inplace=True)

            if 'team' not in result.columns:
                logger.error(f"Team column not found in scraped {stats_type} data")
                logger.info(f"Available columns: {result.columns.tolist()}")
                return pd.DataFrame()

            # Clean team names - remove leading numbers and period (e.g., "1. Baltimore Ravens" -> "Baltimore Ravens")
            result['team'] = result['team'].astype(str).apply(lambda x: re.sub(r'^\d+\.\s*', '', x.strip()))

            # Log team names for debugging
            logger.info(f"Team names (after cleaning): {result['team'].tolist()}")

            # list the columns after renaming
            logger.info(f"Columns after renaming: {result.columns.tolist()}")

            # Standardize team names but ensure there is only one 'team' column
            if 'team' in result.columns:
                result['team'] = result['team'].replace(TEAM_NAME_MAP)
                result['TEAM'] = result['team']

            # Make sure 'TEAM' column exists and 'team' column is dropped
            if 'TEAM' not in result.columns:
                logger.error("TEAM column not found after renaming team names")
                return pd.DataFrame()
            if 'team' in result.columns:
                result.drop(columns=['team'], inplace=True)

            # Make sure 'Season' column exists and 'season' column is dropped
            if 'Season' in result.columns:
                result.rename(columns={'Season': 'season'}, inplace=True)
            if 'season' not in result.columns:
                logger.error("season column not found in scraped data")
                return pd.DataFrame()
            if 'season' in result.columns:
                result.drop(columns=['season'], inplace=True)
            # Log columns after standardizing



            logger.info(f"Columns after standardizing: {result.columns.tolist()}")


        # Convert percentage strings to floats
            for col in result.columns:
                if col == 'team' or col == 'TEAM':
                    continue

                if result[col].dtype == 'object':
                    # Check if the column contains percentage values
                    if result[col].astype(str).str.contains('%').any():
                        # Remove % and convert to float
                        result[col] = result[col].astype(str).str.replace('%', '').astype(float) / 100
                    else:
                        # Try to convert to numeric if possible
                        try:
                            result[col] = pd.to_numeric(result[col], errors='coerce')
                        except:
                            pass

            # Add season information
            result['season'] = self.season

            # Add type information
            result['type'] = stats_type

            logger.info(f"Columns after cleaning: {result.columns.tolist()}")

            return result

        except Exception as e:
            logger.error(f"Error cleaning scraped {stats_type} data: {str(e)}")
            return pd.DataFrame()

    def extract_raw_stats(self) -> Dict[str, pd.DataFrame]:
        """
        Extract and store raw stats for both offense and defense without calculating composites.

        Returns:
            Dictionary with raw offensive and defensive stats DataFrames
        """
        results = {}

        # Extract offensive stats
        off_df = self.scrape_team_data('offense')
        if off_df is not None:
            results['offense'] = off_df
            # Save raw stats to database
            self._save_raw_stats(off_df, 'raw_stats', if_exists='replace')
            # Export to CSV
            self._export_raw_stats_to_csv(off_df, 'offense')

        # Extract defensive stats
        def_df = self.scrape_team_data('defense')
        if def_df is not None:
            results['defense'] = def_df
            # Save raw stats to database (append to the same table as offensive stats)
            self._save_raw_stats(def_df, 'raw_stats', if_exists='append')
            # Export to CSV
            self._export_raw_stats_to_csv(def_df, 'defense')

        return results

    def _save_raw_stats(self, df: pd.DataFrame, table_name: str, if_exists: str = 'append') -> bool:
        """
        Save raw statistics data to database.

        Args:
            df: DataFrame to save
            table_name: Name of the table to save to
            if_exists: How to behave if the table exists ('fail', 'replace', 'append')

        Returns:
            Success status
        """
        try:
            # Add timestamp
            df['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Create a copy of the dataframe to avoid modifying the original
            df_to_save = df.copy()

            # For offense stats (replace mode), just save the data directly
            if if_exists == 'replace':
                print(f"Saving {len(df_to_save)} records to {table_name} table...")
                df_to_save.to_sql(table_name, self.conn, if_exists='replace', index=False)
                self.conn.commit()
                logger.info(f"Successfully saved {len(df_to_save)} raw stats records to {table_name} table")
                return True

            # For defensive stats (append mode), we need to be more careful
            # Log the columns for debugging
            logger.info(f"Columns before saving: {df_to_save.columns.tolist()}")

            # Check if table exists and get the schema
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
            existing_columns = [description[0] for description in cursor.description]
            logger.info(f"Existing table columns: {existing_columns}")

            # Check if the table has records
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            record_count = cursor.fetchone()[0]

            if record_count == 0:
                # Table exists but is empty, so we can just write directly
                df_to_save.to_sql(table_name, self.conn, if_exists='replace', index=False)
                self.conn.commit()
                logger.info(f"Successfully saved {len(df_to_save)} records to empty {table_name} table")
                return True

            # For appending to a non-empty table, we need to handle the column differences
            # Create a new DataFrame with the same columns as the existing table
            new_df = pd.DataFrame(columns=existing_columns)

            # Map columns from our data to the existing table schema
            for col in existing_columns:
                if col in df_to_save.columns:
                    new_df[col] = df_to_save[col]
                else:
                    # Fill in NULL for columns we don't have
                    new_df[col] = None

            # For our columns that don't exist in the target table, add them
            missing_cols = [col for col in df_to_save.columns if col not in existing_columns]
            for col in missing_cols:
                # Add new columns to the database table
                data_type = self._get_sqlite_type(df_to_save[col].dtype)
                try:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN '{col}' {data_type}")
                    self.conn.commit()
                    # Now add the data to our target dataframe
                    new_df[col] = df_to_save[col]
                except Exception as e:
                    logger.warning(f"Could not add column {col}: {str(e)}")

            # Now append the data
            print(f"Saving {len(new_df)} records to {table_name} table...")
            new_df.to_sql(table_name, self.conn, if_exists='append', index=False)
            self.conn.commit()
            logger.info(f"Successfully saved {len(new_df)} raw stats records to {table_name} table")
            return True

        except Exception as e:
            logger.error(f"Database error saving raw stats: {str(e)}")
            print(f"Error saving to database: {str(e)}")
            return False

    def _get_sqlite_type(self, dtype):
        """
        Map pandas dtype to SQLite data type

        Args:
            dtype: Pandas data type

        Returns:
            SQLite data type string
        """
        if pd.api.types.is_integer_dtype(dtype):
            return "INTEGER"
        elif pd.api.types.is_float_dtype(dtype):
            return "REAL"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return "TEXT"
        else:
            return "TEXT"

    def _export_raw_stats_to_csv(self, df: pd.DataFrame, stats_type: str, output_dir: str = None) -> str:
        """
        Export raw statistics to CSV file.

        Args:
            df: DataFrame to export
            stats_type: Type of statistics ('offense' or 'defense')
            output_dir: Directory to save CSV files (default: data folder)

        Returns:
            Path to the saved CSV file
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d')
        filepath = os.path.join(output_dir, f'{stats_type}_stats_{timestamp}.csv')

        try:
            df.to_csv(filepath, index=False)
            logger.info(f"Exported raw {stats_type} stats to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error exporting {stats_type} stats to CSV: {str(e)}")
            return ""

    def calculate_composite_scores(self, stats_df: pd.DataFrame, stats_type: str) -> pd.DataFrame:
        """
        Calculate composite scores for a stats DataFrame.
        This is now separated from the extraction process.

        Args:
            stats_df: DataFrame containing raw statistics
            stats_type: Type of statistics ('offense' or 'defense')

        Returns:
            DataFrame with added composite scores
        """
        result_df = stats_df.copy()

        # Get weights for this stats type
        weights = WEIGHTS.get(stats_type, {})
        if not weights:
            logger.error(f"No weights defined for stats type: {stats_type}")
            result_df['composite_score'] = 0
            return result_df

        # Get list of stats that exist in the dataframe
        available_stats = [col for col in weights.keys() if col in stats_df.columns]

        if not available_stats:
            logger.error(f"No valid stats columns found in dataframe for {stats_type}")
            result_df['composite_score'] = 0
            return result_df

        # Normalize available stats
        normalized_df = self.normalize_dataframe(stats_df, available_stats)

        # Adjust metrics where lower/higher values are better
        inverse_metrics = ['int_rate', 'sack_rate']
        for column in available_stats:
            if stats_type == 'offense' and column in inverse_metrics:
                # For offense, lower int_rate and sack_rate are better
                normalized_df[column] = 1 - normalized_df[column]
            elif stats_type == 'defense' and column not in inverse_metrics:
                # For defense, lower values are better except for int_rate and sack_rate
                normalized_df[column] = 1 - normalized_df[column]

        # Apply weights
        weighted_columns = []
        for column in available_stats:
            weighted_column = f"{column}_weighted"
            normalized_df[weighted_column] = normalized_df[column] * weights[column]
            weighted_columns.append(weighted_column)

        # Sum weighted values for composite score
        result_df['composite_score'] = normalized_df[weighted_columns].sum(axis=1)

        # Add z-score to see how many standard deviations from mean
        mean = result_df['composite_score'].mean()
        std = result_df['composite_score'].std()
        if std > 0:  # Avoid division by zero
            result_df['z_score'] = (result_df['composite_score'] - mean) / std
        else:
            result_df['z_score'] = 0

        # Create unique ID
        result_df['unique_id'] = result_df['TEAM'] + '_' + stats_type

        # Add timestamp
        result_df['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return result_df

    def normalize_dataframe(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        Normalize columns in a dataframe to values between 0 and 1.

        Args:
            df: Input dataframe
            columns: Columns to normalize

        Returns:
            Dataframe with normalized columns
        """
        result = df.copy()
        for column in columns:
            if column in df.columns:
                max_value = df[column].max()
                min_value = df[column].min()

                # Avoid division by zero
                if max_value == min_value:
                    result[column] = 0.5  # Neutral value if all teams have same stat
                else:
                    result[column] = (df[column] - min_value) / (max_value - min_value)
            else:
                logger.warning(f"Column {column} not found in dataframe")

        return result

    def save_composite_scores(self, df: pd.DataFrame, if_exists: str = 'append') -> bool:
        """
        Save composite scores to database.

        Args:
            df: DataFrame with composite scores
            if_exists: How to behave if the table exists ('fail', 'replace', 'append')

        Returns:
            Success status
        """
        try:
            print(f"Saving {len(df)} composite scores to database...")

            # Create a copy of the dataframe to avoid modifying the original
            df_to_save = df.copy()

            # For offense stats (replace mode), just save the data directly
            if if_exists == 'replace':
                df_to_save.to_sql('advanced_stats', self.conn, if_exists='replace', index=False)
                self.conn.commit()
                logger.info(f"Successfully saved {len(df_to_save)} composite scores to database")
                return True

            # For defensive stats (append mode), we need to be more careful
            # Check if table exists and get the schema
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT * FROM advanced_stats LIMIT 0")
                existing_columns = [description[0] for description in cursor.description]
                logger.info(f"Existing advanced_stats table columns: {existing_columns}")

                # Check if the table has records
                cursor.execute("SELECT COUNT(*) FROM advanced_stats")
                record_count = cursor.fetchone()[0]

                if record_count == 0:
                    # Table exists but is empty, so we can just write directly
                    df_to_save.to_sql('advanced_stats', self.conn, if_exists='replace', index=False)
                    self.conn.commit()
                    logger.info(f"Successfully saved {len(df_to_save)} composite scores to empty table")
                    return True
            except Exception as e:
                # Table doesn't exist or other issue
                logger.info(f"Creating new advanced_stats table: {str(e)}")
                df_to_save.to_sql('advanced_stats', self.conn, if_exists='replace', index=False)
                self.conn.commit()
                logger.info(f"Created new advanced_stats table with {len(df_to_save)} records")
                return True

            # For appending to a non-empty table, we need to handle the column differences
            # Create a new DataFrame with the same columns as the existing table
            new_df = pd.DataFrame(columns=existing_columns)

            # Map columns from our data to the existing table schema
            for col in existing_columns:
                if col in df_to_save.columns:
                    new_df[col] = df_to_save[col]
                else:
                    # Fill in NULL for columns we don't have
                    new_df[col] = None

            # For our columns that don't exist in the target table, add them
            missing_cols = [col for col in df_to_save.columns if col not in existing_columns]
            for col in missing_cols:
                # Add new columns to the database table
                data_type = self._get_sqlite_type(df_to_save[col].dtype)
                try:
                    cursor.execute(f"ALTER TABLE advanced_stats ADD COLUMN '{col}' {data_type}")
                    self.conn.commit()
                    # Now add the data to our target dataframe
                    new_df[col] = df_to_save[col]
                except Exception as e:
                    logger.warning(f"Could not add column {col} to advanced_stats: {str(e)}")

            # Now append the data
            new_df.to_sql('advanced_stats', self.conn, if_exists='append', index=False)
            self.conn.commit()
            logger.info(f"Successfully saved {len(new_df)} composite scores to database")
            return True

        except Exception as e:
            logger.error(f"Database error saving composite scores: {str(e)}")
            print(f"Error saving composite scores: {str(e)}")
            return False

    def process_all_stats(self) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        """
        Process all stats: extract raw data and calculate composite scores.

        Returns:
            Tuple of dictionaries containing (raw_stats, composite_scores)
        """
        # Initialize empty dictionaries to avoid returning None
        raw_stats = {}
        composite_scores = {}

        # First extract raw stats
        offense_df = self.scrape_team_data('offense')
        if offense_df is not None:
            raw_stats['offense'] = offense_df
            # Save raw stats to database - even if this fails, continue with the process
            save_success = self._save_raw_stats(offense_df, 'raw_stats', if_exists='replace')
            if not save_success:
                logger.warning("Failed to save offensive stats to database, but continuing with processing")
            # Export to CSV
            self._export_raw_stats_to_csv(offense_df, 'offense')

            # Calculate composite scores for offense
            composite_df = self.calculate_composite_scores(offense_df, 'offense')
            composite_scores['offense'] = composite_df

            # Save composite scores - even if this fails, continue
            save_success = self.save_composite_scores(composite_df, if_exists='replace')
            if not save_success:
                logger.warning("Failed to save offensive composite scores to database, but continuing with processing")

        # Extract defensive stats
        defense_df = self.scrape_team_data('defense')
        if defense_df is not None:
            raw_stats['defense'] = defense_df
            # Save raw stats to database - even if this fails, continue with the process
            save_success = self._save_raw_stats(defense_df, 'raw_stats', if_exists='append')
            if not save_success:
                logger.warning("Failed to save defensive stats to database, but continuing with processing")
            # Export to CSV
            self._export_raw_stats_to_csv(defense_df, 'defense')

            # Calculate composite scores for defense
            composite_df = self.calculate_composite_scores(defense_df, 'defense')
            composite_scores['defense'] = composite_df

            # Save composite scores - even if this fails, continue
            save_success = self.save_composite_scores(composite_df, if_exists='append')
            if not save_success:
                logger.warning("Failed to save defensive composite scores to database, but continuing with processing")

        return raw_stats, composite_scores

def main():
    """
    Main function to collect and process advanced stats.
    """
    try:
        print("Starting advanced stats collection...")
        logger.info("Starting advanced stats collection")

        with AdvancedStatsCollector() as collector:
            # Process all stats (extract raw data and calculate composites)
            print("Collecting stats data...")
            raw_stats, composite_scores = collector.process_all_stats()

            if not raw_stats:
                logger.error("Failed to collect any stats")
                print("Failed to collect any stats")
                return

            # Log summary
            logger.info(f"Successfully processed {len(raw_stats.get('offense', []))} offensive teams")
            logger.info(f"Successfully processed {len(raw_stats.get('defense', []))} defensive teams")

            print(f"Stats collection complete. Processed {len(raw_stats.get('offense', []))} offensive teams and {len(raw_stats.get('defense', []))} defensive teams")
            print(f"Check '{os.path.join(os.path.dirname(__file__), '..', '..', '..', 'panda_picks.log')}' for details.")

    except Exception as e:
        logger.exception(f"Error in main function: {str(e)}")
        print(f"Error in main function: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
