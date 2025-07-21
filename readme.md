# Panda Picks

Panda Picks is a Python-based project designed to analyze NFL data, generate predictions, and store results in a structured database. The project integrates data processing, database management, and analysis to provide insights into NFL matchups, team performance, and betting strategies.

## Project Structure

### Root Directory
- **`panda_picks.log`**: Log file for tracking application events and errors.
- **`readme.md`**: Documentation for the project.
- **`data/`**: Contains raw data files for grades, matchups, picks, and spreads.
- **`database/`**: Stores the SQLite database file (`nfl_data.db`).
- **`panda_picks/`**: Main Python package containing core scripts and configurations.
- **`analysis/`**: Contains scripts for analyzing data and generating predictions.
- **`db/`**: Contains database-related scripts for managing and interacting with the SQLite database.
- **`utils/`**: Utility scripts for handling paths and other helper functions.

---

## Components and Their Interconnections

### 1. **`panda_picks/config.py`**
- Centralized configuration file for the project.
- Defines constants like `DATABASE_PATH` (path to the SQLite database) and `TEAM_GRADES_CSV` (path to the team grades CSV file).
- Used across all scripts to ensure consistent configuration.

### 2. **Database Management (`panda_picks/db/database.py`)**
- Handles all database-related operations, including creating, dropping, and populating tables.
- **Key Functions**:
  - `get_connection()`: Establishes a connection to the SQLite database.
  - `store_grades_data()`: Reads team grades from a CSV file and stores them in the `grades` table.
  - `drop_tables()`: Drops all existing tables in the database.
  - `create_tables()`: Creates tables for grades, advanced stats, spreads, picks, and results.
- **Interconnection**:
  - Relies on `config.py` for database and file paths.
  - Processes data from the `data/` directory and stores it in the database.

### 3. **Data Analysis (`analysis/`)**
- Scripts for analyzing NFL data and generating predictions.
- **Key Scripts**:
  - `backtest.py`: Performs backtesting on historical data to evaluate betting strategies.
  - `bets.py`: Generates betting recommendations based on analysis.
  - `picks.py`: Processes matchup data and generates game picks.
  - `spreads.py`: Analyzes spreads data to identify trends.
- **Interconnection**:
  - Fetches data from the database using `db/database.py`.
  - Outputs results to the database or generates CSV files in the `data/picks/` directory.

### 4. **Data Processing (`data/`)**
- Scripts for processing raw data and preparing it for analysis.
- **Key Scripts**:
  - `advanced_stats.py`: Extracts and processes advanced statistics from raw data.
  - `pdf_scraper.py`: Scrapes data from PDF files (e.g., team grades).
- **Interconnection**:
  - Reads raw data from the `data/grades/` directory.
  - Outputs processed data to the database or as CSV files.

### 5. **Utilities (`utils/`)**
- Contains helper functions for common tasks.
- **Key Script**:
  - `paths.py`: Provides utility functions for handling file paths.
- **Interconnection**:
  - Used across the project to ensure consistent path handling.

---

## Workflow

1. **Data Ingestion**:
  - Raw data (e.g., team grades, matchups, spreads) is stored in the `data/` directory.
  - Scripts like `pdf_scraper.py` and `advanced_stats.py` process this data.

2. **Database Management**:
  - The processed data is stored in the SQLite database (`nfl_data.db`) using `db/database.py`.
  - Tables are created, updated, or cleared as needed.

3. **Analysis**:
  - Scripts in the `analysis/` package fetch data from the database and perform analysis.
  - Results (e.g., game picks, betting strategies) are stored back in the database or exported as CSV files.

4. **Output**:
  - Final results are available in the `data/picks/` directory or directly in the database.

---

## How to Run the Project

1. **Set Up the Environment**:
  - Create a virtual environment:
    ```bash
    python -m venv venv
    ```
  - Activate the virtual environment:
    ```bash
    venv\Scripts\activate
    ```
  - Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2. **Prepare the Database**:
  - Run the `database.py` script to create tables:
    ```bash
    python panda_picks/db/database.py
    ```

3. **Process Data**:
  - Use scripts in the `data/` package to process raw data.

4. **Run Analysis**:
  - Execute scripts in the `analysis/` package to generate predictions and insights.

5. **View Results**:
  - Check the `data/picks/` directory or query the database for results.

---

## Dependencies

- Python 3.11+
- Pandas
- SQLite3

---

## Future Enhancements

- Add automated data scraping for real-time updates.
- Implement a web interface for easier interaction with the database and analysis results.
- Expand analysis capabilities with machine learning models.