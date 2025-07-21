# Analysis Package Documentation

This package contains scripts for analyzing NFL data, generating predictions, and evaluating betting strategies. Below is a summary of each file and its main functions:

## backtest.py
- **Purpose:** Performs backtesting on historical NFL data to evaluate betting strategies and track performance over time.
- **Key Functions:**
  - `backtest()`: Main function that simulates betting scenarios, calculates profits, and stores results in the database. It iterates through each week, merges picks and spreads, simulates teaser bets, and tracks cumulative profit and win percentage.
  - `calculate_winnings(bet_amount, odds)`: Calculates the payout for a given bet and odds.
  - `adjust_spread(row, teaser_points)`: Adjusts the spread for teaser bets.
  - `check_teaser_pick(row, team)`: Checks if a teaser pick is successful based on the adjusted spread and final scores.

## bets.py
- **Purpose:** Generates all possible team combinations for betting analysis for each week and simulates bet placements.
- **Key Functions:**
  - `generate_combos(weeks)`: For each week, fetches picks, generates 2-, 3-, and 4-team combinations, adjusts spreads, and saves combinations to CSV files.
  - `adjust_spread(row, teaser_points)`: Adjusts the spread for each team in the combination.

## picks.py
- **Purpose:** Processes matchup and grades data to generate game picks based on statistical advantages.
- **Key Functions:**
  - `makePicks()`: For each week, merges grades and spreads, calculates various advantage metrics (overall, offense, defense), determines significant edges, and stores the picks in the database.

## spreads.py
- **Purpose:** Fetches and processes NFL spreads and results data from an external API, processes it into a structured format, and stores it in the database for further analysis.
- **Key Functions:**
  - `fetch_data(week)`: Fetches spread and result data for a given week from the API.
  - `process_data(data, week)`: Processes the API response into a DataFrame with relevant columns.
  - `main()`: Loops through all weeks, fetches and processes data, and saves it to the database.

---

Each script connects to the SQLite database using a shared connection utility and is typically run after the data and database have been prepared. Results are stored in the database or exported as CSV files for further review.

