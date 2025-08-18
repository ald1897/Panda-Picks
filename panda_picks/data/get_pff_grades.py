import requests
import pandas as pd
from panda_picks import config
from panda_picks.db import database as db
import os
from dotenv import load_dotenv
import time
import logging
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('panda_picks.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('pff_grades')

# Load environment variables
load_dotenv()

# API endpoint
url = "https://premium.pff.com/api/v1/teams/overview?league=nfl&season=2024&week=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18"

# Headers and cookies for the API request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://premium.pff.com/",
}

def manual_cookie_capture():
    """
    Guide the user through manually capturing cookies directly from the Network tab.

    Returns:
        dict: Dictionary of cookies from manual input
    """
    print("\n" + "="*80)
    print("MANUAL COOKIE CAPTURE")
    print("="*80)
    print("Please follow these simple steps to capture cookies:")
    print("1. Open Chrome and go to https://premium.pff.com")
    print("2. Log in to your PFF account if needed")
    print("3. Press F12 to open DevTools")
    print("4. Go to the 'Network' tab")
    print("5. In the filter box, type 'teams/overview' to find the API request")
    print("6. Click on the request that matches this URL:")
    print("   https://premium.pff.com/api/v1/teams/overview?league=nfl&season=2024&week=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18")
    print("7. In the Headers tab, scroll down to find the 'Cookie:' header")
    print("8. Right-click the cookie value and select 'Copy value'")
    print("9. Paste the copied cookies below:")

    cookies_input = input("Paste cookies here: ")

    # Parse the cookies input
    try:
        # Parse as cookie string
        cookies_dict = {}
        cookie_pairs = cookies_input.split(';')
        for pair in cookie_pairs:
            if '=' in pair:
                name, value = pair.strip().split('=', 1)
                cookies_dict[name] = value

        # Save cookies to file
        cookies_file = "cookies.txt"
        cookie_string = "; ".join([f"{name}={value}" for name, value in cookies_dict.items()])
        with open(cookies_file, 'w') as f:
            f.write(cookie_string)

        print(f"\nCookies saved to {cookies_file}")
        logger.info(f"Manually captured cookies saved to {cookies_file}")
        return cookies_dict

    except Exception as e:
        logger.error(f"Error parsing cookies: {e}", exc_info=True)
        print(f"Error parsing cookies: {e}")
        print("Please make sure you've copied the cookies correctly.")
        return None

def load_cookies_from_file(file_path):
    """Load cookies from a text file and parse them into a dictionary."""
    logger.info(f"Attempting to load cookies from {file_path}")
    try:
        with open(file_path, 'r') as file:
            cookie_string = file.read().strip()
        cookies_dict = dict(item.split("=", 1) for item in cookie_string.split("; "))
        logger.debug(f"Successfully loaded cookies with keys: {list(cookies_dict.keys())}")
        return cookies_dict
    except Exception as e:
        logger.error(f"Error loading cookies from file: {e}", exc_info=True)
        raise Exception(f"Error loading cookies from file: {e}")

def get_cookies(force_manual=True):
    """
    Get cookies for PFF website authentication.

    Args:
        force_manual (bool): If True, always prompt for manual cookie entry

    Returns:
        dict: Dictionary of cookies
    """
    cookies_file = "cookies.txt"
    cookies_path = Path(cookies_file)

    # If force_manual is True or no cookies file exists, use manual entry
    if force_manual or not cookies_path.exists():
        logger.info("Using manual cookie capture as requested")
        return manual_cookie_capture()

    # Otherwise, try to use existing cookies
    logger.info("Using existing cookies from file")
    try:
        return load_cookies_from_file(cookies_file)
    except Exception as e:
        logger.warning(f"Error loading existing cookies: {e}")
        return manual_cookie_capture()

# Load cookies for the API request
cookies_file = "cookies.txt"  # Path to the text file containing the cookie string
logger.info("Initializing cookies")
try:
    # Always use manual cookie capture when the script starts
    cookies = get_cookies(force_manual=True)
except Exception as e:
    logger.critical(f"Failed to initialize cookies: {e}")
    cookies = None


def fetch_pff_grades():
    """Fetch team grades from the PFF API."""
    global cookies
    logger.info("Fetching PFF grades from API")
    try:
        logger.debug(f"Making request to {url}")
        response = requests.get(url, headers=headers, cookies=cookies)
        logger.info(f"Received response with status code: {response.status_code}")

        if response.status_code == 401:  # Unauthorized
            logger.warning("Received 401 Unauthorized response, attempting to refresh cookies")
            # Refresh cookies and try again
            cookies = get_cookies(force_manual=True)
            logger.info("Retrying request with refreshed cookies")
            response = requests.get(url, headers=headers, cookies=cookies)
            logger.info(f"Retry response status code: {response.status_code}")

        response.raise_for_status()
        json_data = response.json()
        logger.info("Successfully parsed JSON response")
        return json_data
    except requests.RequestException as e:
        logger.error(f"Request exception when fetching data from PFF API: {e}", exc_info=True)
        raise Exception(f"Error fetching data from PFF API: {e}")

def process_grades(data):
    """Process the API response into a structured DataFrame."""
    logger.info("Processing PFF grades data")
    try:
        # Extract the team_overview list
        teams_data = data.get("team_overview", [])
        if not teams_data:
            logger.error("No team data found in API response")
            raise ValueError("No team data found in API response.")

        logger.info(f"Found data for {len(teams_data)} teams")

        # Convert to DataFrame
        df = pd.DataFrame(teams_data)
        logger.debug(f"Created DataFrame with shape: {df.shape}")

        # Select and rename columns to match the desired format
        column_mapping = {
            "abbreviation": "TEAM",
            "grades_overall": "OVR",
            "grades_offense": "OFF",
            "grades_pass": "PASS",
            "grades_run": "RUN",
            "grades_defense": "DEF",
            "grades_run_defense": "RDEF",
            "grades_pass_rush_defense": "PRSH",
            "grades_coverage_defense": "COV",
            "grades_tackle": "TACK",
            "grades_pass_block": "PBLK",
            "grades_run_block": "RBLK",
            "grades_pass_route": "RECV",
            "wins": "WINS",
            "losses": "LOSSES",
            "ties": "TIES",
            "points_scored": "PTS_SCORED",
            "points_allowed": "PTS_ALLOWED",
        }
        logger.debug("Renaming columns according to mapping")
        df = df.rename(columns=column_mapping)

        # Keep only the required columns
        required_columns = list(column_mapping.values())
        logger.debug(f"Keeping only required columns: {required_columns}")

        # Check if all required columns exist in the DataFrame
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"Missing columns in API response: {missing_columns}")
            print(f"Warning: Missing columns in API response: {missing_columns}")

        df = df[required_columns]
        logger.info(f"Processed DataFrame has shape: {df.shape}")

        return df
    except Exception as e:
        logger.error(f"Error processing grades data: {e}", exc_info=True)
        raise Exception(f"Error processing grades data: {e}")

def save_grades_to_csv(df, output_path):
    """Save the processed grades DataFrame to a CSV file."""
    logger.info(f"Saving grades to CSV at {output_path}")
    try:
        df.to_csv(output_path, index=False)
        logger.info(f"Successfully saved team grades to {output_path}")
        print(f"Successfully saved team grades to {output_path}")
    except Exception as e:
        logger.error(f"Error saving grades to CSV: {e}", exc_info=True)
        raise Exception(f"Error saving grades to CSV: {e}")

def getGrades():
    """Fetch, process, and save team grades."""
    logger.info("Starting getGrades function")
    try:
        # Fetch data from the API
        logger.info("Fetching raw data from API")
        raw_data = fetch_pff_grades()

        # Process the data into a structured format
        logger.info("Processing raw data into structured format")
        grades_df = process_grades(raw_data)

        # Save the processed data to a CSV file
        output_file = config.TEAM_GRADES_CSV
        logger.info(f"Saving processed data to {output_file}")
        save_grades_to_csv(grades_df, output_file)

        logger.info("getGrades finished successfully")
        return True
    except Exception as e:
        logger.error(f"Error in getGrades: {e}", exc_info=True)
        print(f"Error in getGrades: {e}")
        return False

if __name__ == "__main__":
    logger.info("Script started as main")
    print("PFF Grades Fetcher")
    print("=================")
    if getGrades():
        logger.info("Calling db.store_grades_data()")
        print("Storing grades data in database...")
        db.store_grades_data()
        print("Process completed successfully!")
    else:
        logger.error("getGrades failed, not storing data in database")
        print("Failed to get grades, data not stored in database.")
