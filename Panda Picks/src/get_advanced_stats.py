import requests
import pandas as pd
import sqlite3

# Define the weights for each statistic
offensive_weights = {
    'epa_per_play': 35,
    'epa_per_pass': 15,
    'air_epa_per_att': 10,
    'yac_epa_per_att': 10,
    'epa_per_rush': 15,
    'comp_perc': 5,
    'scramble_rate': 3,
    'int_rate': 5,
    'sack_rate': 2
}

defensive_weights = {
    'epa_per_play': 35,
    'epa_per_pass': 15,
    'air_epa_per_att': 10,
    'yac_epa_per_att': 10,
    'epa_per_rush': 15,
    'comp_perc': 5,
    'scramble_rate': 3,
    'int_rate': 5,
    'sack_rate': 2
}

def fetch_advanced_stats(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()

def normalize(df, columns):
    result = df.copy()
    for column in columns:
        max_value = df[column].max()
        min_value = df[column].min()
        result[column] = (df[column] - min_value) / (max_value - min_value)
    return result

def calculate_offensive_composite_score(df, weights):
    # Normalize the statistics
    normalized_df = normalize(df, weights.keys())

    # Adjust metrics where lower is better
    for column in ['int_rate', 'sack_rate']:
        if column in normalized_df.columns:
            normalized_df[column] = 1 - normalized_df[column]

    # Apply weights and calculate the composite score
    for column, weight in weights.items():
        normalized_df[column] = normalized_df[column] * weight

    # Sum the weighted values to get the composite score
    df['composite_score'] = normalized_df[list(weights.keys())].sum(axis=1)
    return df

def calculate_defensive_composite_score(df, weights):
    # Normalize the statistics
    normalized_df = normalize(df, weights.keys())

    # Adjust metrics where lower is better
    for column in weights.keys():
        if column not in ['int_rate', 'sack_rate']:
            normalized_df[column] = 1 - normalized_df[column]

    # Apply weights and calculate the composite score
    for column, weight in weights.items():
        normalized_df[column] = normalized_df[column] * weight

    # Sum the weighted values to get the composite score
    df['composite_score'] = normalized_df[list(weights.keys())].sum(axis=1)
    return df

def save_advanced_stats(data, conn):
    # Access the data inside the "off.table" property
    off_table_data = data.get("off.table", [])
    df = pd.DataFrame(off_table_data)

    # Filter the DataFrame for the 2024 season
    df_2024 = df[df['season'] == 2024].copy()

    # Replace team names
    df_2024.loc[:, 'team'] = df_2024['team'].replace({'CLE': 'CLV', 'ARI': 'ARZ'})

    df_2024['TEAM'] = df_2024['team']
    df_2024.drop(columns=['team'], inplace=True)

    # Calculate the composite score
    df_2024 = calculate_offensive_composite_score(df_2024, offensive_weights)

    # Create a type column to distinguish between offensive and defensive stats
    df_2024['type'] = 'offense'

    # Make the team and type columns the unique identifier
    df_2024['unique_id'] = df_2024['TEAM'] + df_2024['type']


    # Calculate the standard deviation of the composite scores
    df_2024['composite_score_std'] = df_2024['composite_score'].std()
    # Keep only the columns used in the calculations
    columns_to_keep = list(defensive_weights.keys()) + ['TEAM', 'season', 'composite_score', 'composite_score_std', 'type', 'unique_id']
    df_2024 = df_2024[columns_to_keep]

    # Sort by composite score from high to low
    df_2024 = df_2024.sort_values(by='composite_score', ascending=False)

    # Insert data into the SQLite database
    df_2024.to_sql('advanced_stats', conn, if_exists='replace', index=False)
    return df_2024

def save_defensive_stats(data, conn):
    # Access the data inside the "def.table" property
    def_table_data = data.get("def.table", [])
    df = pd.DataFrame(def_table_data)

    # Filter the DataFrame for the 2024 season
    df_2024 = df[df['season'] == 2024].copy()

    # Replace team names
    df_2024.loc[:, 'team'] = df_2024['team'].replace({'CLE': 'CLV', 'ARI': 'ARZ'})

    df_2024['TEAM'] = df_2024['team']
    df_2024.drop(columns=['team'], inplace=True)

    # Calculate the composite score
    df_2024 = calculate_defensive_composite_score(df_2024, defensive_weights)

    # Create a type column to distinguish between offensive and defensive stats
    df_2024['type'] = 'defense'


    # Make the team and type columns the unique identifier
    df_2024['unique_id'] = df_2024['TEAM'] + df_2024['type']

    # Calculate the standard deviation of the composite scores and add it to the existing dataframe
    df_2024['composite_score_std'] = df_2024['composite_score'].std()
    # Keep only the columns used in the calculations
    columns_to_keep = list(defensive_weights.keys()) + ['TEAM', 'season', 'composite_score', 'composite_score_std', 'type', 'unique_id']
    df_2024 = df_2024[columns_to_keep]

    # Sort by composite score from high to low
    df_2024 = df_2024.sort_values(by='composite_score', ascending=False)

    # Insert data into the SQLite database so it stores offense and defense stats. If there are 64 items in the table,
    df_2024.to_sql('advanced_stats', conn, if_exists='append', index=False)
    return df_2024

def main():
    off_url = "https://sumersports.com/wp-content/uploads/data/off_team.json"
    def_url = "https://sumersports.com/wp-content/uploads/data/def_team.json"

    # Connect to SQLite database
    conn = sqlite3.connect('db/nfl_data.db')

    off_data = fetch_advanced_stats(off_url)
    save_advanced_stats(off_data, conn)

    def_data = fetch_advanced_stats(def_url)
    save_defensive_stats(def_data, conn)

    # Commit and close the connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()