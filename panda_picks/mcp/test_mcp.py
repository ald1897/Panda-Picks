# Simple script to test if GitHub Copilot can use MCP servers
# If the MCP server is working, Copilot should be able to complete this code with context from your project

import os
import sys
import sqlite3

# Try to print information that would require project knowledge
print("Testing if MCP servers are providing context to Copilot...")

# Test direct database connection (not through MCP, just to verify database exists)
try:
    conn = sqlite3.connect("../../database/nfl_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Database tables found through direct connection:")
    for table in tables:
        print(f"- {table[0]}")
    conn.close()
    print("Direct database connection successful!")
except Exception as e:
    print(f"Error connecting directly to database: {e}")

# If you have an SQLite MCP server connected properly, Copilot should be able to
# suggest table names from your nfl_data.db after typing:
# List every table in the nfl_Data.db database
# "picks", "grades", "matchups", "teams", "spreads", # "advanced_stats", "backtest_results", picks_results = []

#Write a query that gets all the data from the "picks" table
# and prints it out
try:
    conn = sqlite3.connect("../../database/nfl_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM picks")
    picks_data = cursor.fetchall()
    print("Picks data retrieved successfully:")
    for row in picks_data:
        print(row)
    conn.close()

# If you have a Git MCP server connected, Copilot should know your repo structure
# Try asking it about files in your project after running this
