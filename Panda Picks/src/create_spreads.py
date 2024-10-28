import requests
import pandas as pd


# Function to fetch data from the API
def fetch_data(week):
    url = f"https://www.pff.com/api/scoreboard/ticker?league=nfl&season=2024&week={week}"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()


# Function to process the data and create a DataFrame
def process_data(data, week):
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
            "Home Team": home_team,
            "Away Team": away_team,
            "Home Score": home_score,
            "Away Score": away_score,
            "Home Odds Close": home_odds_close,
            "Away Odds Close": away_odds_close,
            "Home Line Close": home_line_close,
            "Away Line Close": away_line_close
        })

    return pd.DataFrame(processed_data)


# Main function to fetch, process, and save the data
def main():
    all_weeks_data = pd.DataFrame()
    for week in range(1, 18):  # Change the range as needed
        data = fetch_data(week)
        week_df = process_data(data, week)
        all_weeks_data = pd.concat([all_weeks_data, week_df], ignore_index=True)

    all_weeks_data.to_csv(r"../Data/Spreads/nflSpreads.csv", index=False)


if __name__ == "__main__":
    main()