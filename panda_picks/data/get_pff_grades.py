import requests
import pandas as pd
from panda_picks import config
from panda_picks.db import database as db
import os
from dotenv import load_dotenv
import time

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

# Get cookies once at module level
#
#
def load_cookies_from_file(file_path):
    """Load cookies from a text file and parse them into a dictionary."""
    try:
        with open(file_path, 'r') as file:
            cookie_string = file.read().strip()
        return dict(item.split("=", 1) for item in cookie_string.split("; "))
    except Exception as e:
        raise Exception(f"Error loading cookies from file: {e}")

# # Load cookies from the text file
cookies_file = "cookies.txt"  # Path to the text file containing the cookie string
cookies = load_cookies_from_file(cookies_file)


def fetch_pff_grades():
    """Fetch team grades from the PFF API."""
    global cookies
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        if response.status_code == 401:  # Unauthorized
            # Refresh cookies and try again
            cookies = get_cookies(force_refresh=True)
            response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise Exception(f"Error fetching data from PFF API: {e}")

def process_grades(data):
    """Process the API response into a structured DataFrame."""
    try:
        # Extract the team_overview list
        teams_data = data.get("team_overview", [])
        if not teams_data:
            raise ValueError("No team data found in API response.")

        # Convert to DataFrame
        df = pd.DataFrame(teams_data)

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
        df = df.rename(columns=column_mapping)

        # Keep only the required columns
        required_columns = list(column_mapping.values())
        df = df[required_columns]

        return df
    except Exception as e:
        raise Exception(f"Error processing grades data: {e}")

def save_grades_to_csv(df, output_path):
    """Save the processed grades DataFrame to a CSV file."""
    try:
        df.to_csv(output_path, index=False)
        # print(f"Team grades saved to {output_path}")
    except Exception as e:
        raise Exception(f"Error saving grades to CSV: {e}")

def getGrades():
    print(f"[{time.strftime('%H:%M:%S')}] getGrades started")
    """Fetch, process, and save team grades."""
    try:
        # Fetch data from the API
        raw_data = fetch_pff_grades()

        # Process the data into a structured format
        grades_df = process_grades(raw_data)

        # Save the processed data to a CSV file
        output_file = config.TEAM_GRADES_CSV
        save_grades_to_csv(grades_df, output_file)

        print(f"[{time.strftime('%H:%M:%S')}] getGrades finished successfully")
        return True
    except Exception as e:
        print(f"Error in getGrades: {e}")
        print(f"[{time.strftime('%H:%M:%S')}] getGrades finished with error")
        return False

if __name__ == "__main__":
    if getGrades():
        db.store_grades_data()