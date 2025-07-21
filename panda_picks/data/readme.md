# Data Package Documentation

This package contains scripts for processing and extracting raw NFL data, transforming it into structured formats for analysis and database storage. Below is a summary of each file and its main functions:

## advanced_stats.py
- **Purpose:** Fetches, normalizes, and processes advanced team statistics from external sources, calculates composite scores using weighted metrics, and stores the results in the database.
- **Key Functions:**
  - `fetch_advanced_stats(url)`: Downloads advanced stats JSON data from a given URL.
  - `normalize(df, columns)`: Normalizes specified columns in a DataFrame.
  - `calculate_offensive_composite_score(df, weights)`: Calculates a weighted composite score for offensive stats.
  - `calculate_defensive_composite_score(df, weights)`: Calculates a weighted composite score for defensive stats.
  - `save_advanced_stats(data, conn)`: Processes and saves offensive stats to the database.
  - `save_defensive_stats(data, conn)`: Processes and saves defensive stats to the database.
  - `main()`: Orchestrates the fetching, processing, and saving of both offensive and defensive stats.

## pdf_scraper.py
- **Purpose:** Extracts team grades and statistics from PDF files, merges them with team abbreviations, and outputs the results as CSV files for further analysis or database insertion.
- **Key Functions:**
  - `extract_team_grades(pdf_path)`: Reads a PDF and extracts team grades into a DataFrame.
  - `merge_with_abbreviations(grades_df, abbrev_path)`: Merges extracted grades with team abbreviations for consistency.
  - `getGrades()`: Main function to process the PDF, merge with abbreviations, and save the result as a CSV file.

---

These scripts are typically run before any analysis to ensure the database is populated with up-to-date and accurate data.

