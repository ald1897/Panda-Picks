# DB Package Documentation

This package manages all database-related operations for the project, providing utilities for creating, dropping, and populating tables in the SQLite database, as well as functions for storing and retrieving data.

## database.py
- **Purpose:** Handles all database schema definitions, connections, and data storage/retrieval for grades, advanced stats, spreads, picks, and results tables.
- **Key Functions:**
  - `get_connection()`: Returns a connection to the SQLite database using the path from config.py.
  - `store_grades_data()`: Loads team grades from a CSV and stores them in the grades table.
  - `drop_tables()`: Drops all relevant tables (grades, advanced_stats, spreads, picks, backtest_results, picks_results, teaser_results) to reset the database.
  - `create_tables()`: Creates all necessary tables for the project, including schema for grades, advanced stats, spreads, picks, backtest results, picks results, and teaser results.

---

This module is used by both data processing and analysis scripts to ensure all data is structured and accessible for further analysis. It should be run before analysis scripts to set up or reset the database structure.

