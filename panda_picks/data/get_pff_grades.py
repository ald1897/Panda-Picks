import requests
import pandas as pd
from panda_picks import config
from panda_picks.db import database as db
import os
from dotenv import load_dotenv
import logging
from pathlib import Path
from datetime import datetime

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

# Environment configuration
DEFAULT_SEASON = datetime.utcnow().year
PFF_SEASON = int(os.getenv('PFF_SEASON', DEFAULT_SEASON))
PFF_FORCE_MANUAL_COOKIES = os.getenv('PFF_FORCE_MANUAL_COOKIES', 'true').lower() in ('1','true','yes','on')
FULL_SEASON_WEEKS_PARAM = '1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18'

def build_pff_url(season: int | None = None) -> str:
    """Construct the PFF API URL for the full list of weeks (1..18)."""
    season = season or PFF_SEASON
    return f"https://premium.pff.com/api/v1/teams/overview?league=nfl&season={season}&week={FULL_SEASON_WEEKS_PARAM}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://premium.pff.com/",
}

def manual_cookie_capture():
    print("\n" + "="*80)
    print("MANUAL COOKIE CAPTURE")
    print("="*80)
    print("1. Open Chrome and go to https://premium.pff.com")
    print("2. Log in to your PFF account if needed")
    print("3. Press F12 (DevTools) -> Network tab")
    print("4. Filter: teams/overview")
    print("5. Open the request with full-season weeks (any season)")
    print("6. Copy the Cookie header value")
    print("7. Paste below:")
    cookies_input = input("Paste cookies here: ")
    try:
        cookies_dict = {}
        for pair in cookies_input.split(';'):
            if '=' in pair:
                name, value = pair.strip().split('=',1)
                cookies_dict[name] = value
        with open('cookies.txt','w') as f:
            f.write('; '.join([f"{k}={v}" for k,v in cookies_dict.items()]))
        logger.info('Cookies captured and saved to cookies.txt')
        return cookies_dict
    except Exception as e:
        logger.error(f"Error parsing cookies: {e}")
        return None

def load_cookies_from_file(file_path: str):
    logger.info(f"Loading cookies from {file_path}")
    with open(file_path,'r') as f:
        cookie_string = f.read().strip()
    return dict(item.split('=',1) for item in cookie_string.split('; '))

def get_cookies(force_manual: bool | None = None):
    if force_manual is None:
        force_manual = PFF_FORCE_MANUAL_COOKIES
    path = Path('cookies.txt')
    if force_manual or not path.exists():
        return manual_cookie_capture()
    try:
        return load_cookies_from_file(str(path))
    except Exception as e:
        logger.warning(f"Failed reading cookies file: {e}; falling back to manual capture")
        return manual_cookie_capture()

logger.info("Initializing cookies")
try:
    cookies = get_cookies()
except Exception as e:
    logger.critical(f"Cookie initialization failed: {e}")
    cookies = None

def fetch_pff_grades(season: int | None = None):
    global cookies
    target_url = build_pff_url(season)
    logger.info(f"Requesting PFF grades: {target_url}")
    try:
        resp = requests.get(target_url, headers=headers, cookies=cookies)
        logger.info(f"Status {resp.status_code}")
        if resp.status_code == 401:
            logger.warning("401 Unauthorized; refreshing cookies via manual capture")
            cookies = get_cookies(force_manual=True)
            resp = requests.get(target_url, headers=headers, cookies=cookies)
            logger.info(f"Retry status {resp.status_code}")
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"Fetch error: {e}")
        raise Exception(f"Error fetching PFF data: {e}")

def process_grades(data):
    logger.info("Processing PFF grades JSON")
    teams = data.get('team_overview', [])
    if not teams:
        raise ValueError('No team_overview payload found')
    df = pd.DataFrame(teams)
    mapping = {
        'abbreviation':'TEAM',
        'grades_overall':'OVR',
        'grades_offense':'OFF',
        'grades_pass':'PASS',
        'grades_run':'RUN',
        'grades_defense':'DEF',
        'grades_run_defense':'RDEF',
        'grades_pass_rush_defense':'PRSH',
        'grades_coverage_defense':'COV',
        'grades_tackle':'TACK',
        'grades_pass_block':'PBLK',
        'grades_run_block':'RBLK',
        'grades_pass_route':'RECV',
        'wins':'WINS',
        'losses':'LOSSES',
        'ties':'TIES',
        'points_scored':'PTS_SCORED',
        'points_allowed':'PTS_ALLOWED'
    }
    df = df.rename(columns=mapping)
    required = list(mapping.values())
    missing = [c for c in required if c not in df.columns]
    if missing:
        logger.warning(f"Missing expected columns: {missing}")
    df = df[[c for c in required if c in df.columns]]
    logger.info(f"Processed grades shape {df.shape}")
    return df

def save_grades_to_csv(df: pd.DataFrame, path: Path):
    df.to_csv(path, index=False)
    logger.info(f"Grades saved to {path}")

def getGrades(season: int | None = None):
    try:
        raw = fetch_pff_grades(season)
        df = process_grades(raw)
        save_grades_to_csv(df, config.TEAM_GRADES_CSV)
        return True
    except Exception as e:
        logger.error(f"getGrades failure: {e}")
        print(f"Error in getGrades: {e}")
        return False

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fetch full-season PFF team grades (weeks 1-18)')
    parser.add_argument('--season', type=int, help='Season year override')
    args = parser.parse_args()
    if getGrades(season=args.season):
        print('Storing grades data in database...')
        db.store_grades_data()
        print('Done.')
    else:
        print('Failed to fetch grades.')
