import requests
import pandas as pd

# Define the weights for each statistic
offensive_weights = {
    'epa_per_play': 32,
    'epa_per_pass': 15,
    'pass_td': 10,
    'air_epa_per_att': 8,
    'avg_depth_targ': 8,
    'yac_epa_per_att': 6,
    'epa_per_rush': 5,
    'rush_td': 4,
    'comp_perc': 4,
    'scramble_rate': 3,
    'int_rate': 3,
    'sack_rate': 2
}

defensive_weights = {
    'epa_per_play': 32,
    'epa_per_pass': 15,
    'pass_td': 10,
    'air_epa_per_att': 8,
    'avg_depth_targ': 8,
    'yac_epa_per_att': 6,
    'epa_per_rush': 5,
    'rush_td': 4,
    'comp_perc': 4,
    'scramble_rate': 3,
    'int_rate': 3,
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

def save_advanced_stats(data, file_path):
    # Access the data inside the "off.table" property
    off_table_data = data.get("off.table", [])
    df = pd.DataFrame(off_table_data)

    # Filter the DataFrame for the 2024 season
    df_2024 = df[df['season'] == 2024].copy()

    # Replace team names
    df_2024.loc[:, 'team'] = df_2024['team'].replace({'CLE': 'CLV', 'ARI': 'ARZ'})

    # Calculate the composite score
    df_2024 = calculate_offensive_composite_score(df_2024, offensive_weights)

    # Calculate the standard deviation of the composite scores
    composite_score_std = df_2024['composite_score'].std()
    print(f"Offensive Composite Score Standard Deviation: {composite_score_std}")

    # Keep only the columns used in the calculations
    columns_to_keep = list(offensive_weights.keys()) + ['team', 'season', 'composite_score']
    df_2024 = df_2024[columns_to_keep]

    # Sort by composite score from high to low
    df_2024 = df_2024.sort_values(by='composite_score', ascending=False)

    df_2024.to_csv(file_path, index=False)
    return df_2024

def save_defensive_stats(data, file_path):
    # Access the data inside the "def.table" property
    def_table_data = data.get("def.table", [])
    df = pd.DataFrame(def_table_data)

    # Filter the DataFrame for the 2024 season
    df_2024 = df[df['season'] == 2024].copy()

    # Replace team names
    df_2024.loc[:, 'team'] = df_2024['team'].replace({'CLE': 'CLV', 'ARI': 'ARZ'})

    # Calculate the composite score
    df_2024 = calculate_defensive_composite_score(df_2024, defensive_weights)

    # Calculate the standard deviation of the composite scores
    composite_score_std = df_2024['composite_score'].std()
    print(f"Defensive Composite Score Standard Deviation: {composite_score_std}")

    # Keep only the columns used in the calculations
    columns_to_keep = list(defensive_weights.keys()) + ['team', 'season', 'composite_score']
    df_2024 = df_2024[columns_to_keep]

    # Sort by composite score from high to low
    df_2024 = df_2024.sort_values(by='composite_score', ascending=False)

    df_2024.to_csv(file_path, index=False)
    return df_2024

def main():
    off_url = "https://sumersports.com/wp-content/uploads/data/off_team.json"
    def_url = "https://sumersports.com/wp-content/uploads/data/def_team.json"
    off_file_path = "../Data/AdvancedStats/off_team.csv"
    def_file_path = "../Data/AdvancedStats/def_team.csv"

    off_data = fetch_advanced_stats(off_url)
    save_advanced_stats(off_data, off_file_path)
    print(f"Offensive data saved to {off_file_path}")

    def_data = fetch_advanced_stats(def_url)
    save_defensive_stats(def_data, def_file_path)
    print(f"Defensive data saved to {def_file_path}")

if __name__ == "__main__":
    main()