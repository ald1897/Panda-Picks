import requests
import pandas as pd
import time
import concurrent.futures
from panda_picks.db.database import get_connection

# Function to fetch data from the API with retry logic
def fetch_data(week, max_retries=3):
    url = f"https://www.pff.com/api/scoreboard/ticker?league=nfl&season=2025&week={week}"

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, requests.Timeout) as e:
            if attempt == max_retries - 1:
                print(f"Failed to fetch data for week {week} after {max_retries} attempts: {e}")
                return None
            time.sleep(1)  # Wait before retrying

# Function to process the data and create a DataFrame
def process_data(data, week):
    if not data or 'weeks' not in data or not data['weeks']:
        return pd.DataFrame()  # Return empty dataframe if data is invalid

    games = data['weeks'][0]['games']
    processed_data = []

    for game in games:
        home_team = game['home_franchise']['abbreviation']
        away_team = game['away_franchise']['abbreviation']
        home_score = game['home_score']
        away_score = game['away_score']
        home_odds_close = game['home_team_money_line']
        away_odds_close = game['away_team_money_line']
        home_line_close = game['point_spread']
        away_line_close = -home_line_close if home_line_close is not None else None

        processed_data.append({
            "WEEK": f"WEEK{week}",
            "Home_Team": home_team,
            "Away_Team": away_team,
            "Home_Score": home_score,
            "Away_Score": away_score,
            "Home_Odds_Close": home_odds_close,
            "Away_Odds_Close": away_odds_close,
            "Home_Line_Close": home_line_close,
            "Away_Line_Close": away_line_close
        })

    return pd.DataFrame(processed_data)

# Function to fetch and process data for a single week
def fetch_and_process(week):
    data = fetch_data(week)
    if data:
        return process_data(data, week)
    return pd.DataFrame()

# Main function to fetch, process, and save the data
def main():
    start_time = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] spreads main started")

    # Use parallel processing to fetch data for all weeks
    all_dfs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_week = {executor.submit(fetch_and_process, week): week for week in range(1, 19)}
        for future in concurrent.futures.as_completed(future_to_week):
            week_df = future.result()
            if not week_df.empty:
                all_dfs.append(week_df)

    # Combine all dataframes
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)

        # Single database operation
        with get_connection() as conn:
            combined_df.to_sql('spreads', conn, if_exists='append', index=False)

    elapsed_time = time.time() - start_time
    print(f"[{time.strftime('%H:%M:%S')}] spreads main finished in {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()

# import requests
# import pandas as pd
# import sqlite3
# import time
#
# from panda_picks.db.database import get_connection
# from panda_picks import config
#
# # Function to fetch data from the API
# def fetch_data(week):
#     url = f"https://www.pff.com/api/scoreboard/ticker?league=nfl&season=2025&week={week}"
#     response = requests.get(url)
#     response.raise_for_status()  # Raise an error for bad status codes
#     return response.json()
#
# # Function to process the data and create a DataFrame
# def process_data(data, week):
#     games = data['weeks'][0]['games']
#     processed_data = []
#
#     for game in games:
#         home_team = game['home_franchise']['abbreviation']
#         away_team = game['away_franchise']['abbreviation']
#         home_score = game['home_score']
#         away_score = game['away_score']
#         home_odds_close = game['home_team_money_line']
#         away_odds_close = game['away_team_money_line']
#         home_line_close = game['point_spread']
#         away_line_close = -home_line_close if home_line_close is not None else None
#
#         processed_data.append({
#             "WEEK": f"WEEK{week}",
#             "Home_Team": home_team,
#             "Away_Team": away_team,
#             "Home_Score": home_score,
#             "Away_Score": away_score,
#             "Home_Odds_Close": home_odds_close,
#             "Away_Odds_Close": away_odds_close,
#             "Home_Line_Close": home_line_close,
#             "Away_Line_Close": away_line_close
#         })
#
#     return pd.DataFrame(processed_data)
#
# # Main function to fetch, process, and save the data
# def main():
#     print(f"[{time.strftime('%H:%M:%S')}] spreads main started")
#     conn = sqlite3.connect('nfl_data.db')
#     conn = get_connection()
#
#
#     for week in range(1, 19):  # Change the range as needed
#         # print(f"[{time.strftime('%H:%M:%S')}] Fetching data for week {week}")
#         data = fetch_data(week)
#         week_df = process_data(data, week)
#         week_df.to_sql('spreads', conn, if_exists='append', index=False)
#
#     # Commit and close the connection
#     conn.commit()
#     conn.close()
#     print(f"[{time.strftime('%H:%M:%S')}] spreads main finished")
#
# if __name__ == "__main__":
#     main()