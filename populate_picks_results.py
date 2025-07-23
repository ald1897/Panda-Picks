#!/usr/bin/env python3
"""
Standalone script to populate the picks_results table with simulated game results
based on the provided picks data.
"""

import sqlite3
import random
from typing import List, Dict, Any

# Set random seed for consistent results
random.seed(42)

# Database path
DATABASE_PATH = "database/nfl_data.db"

# Raw picks data
PICKS_DATA = [
    ("WEEK1", "PHI", "DAL", -7, 7, "PHI", 20.6, 17.4, 24, "home significant", "home significant", "home significant"),
    ("WEEK1", "DEN", "TEN", -7.5, 7.5, "DEN", 20.1, 6.6, 15.5, "home significant", "home significant", "home significant"),
    ("WEEK1", "IND", "MIA", -1, 1, "IND", 8.3, 6.5, 4.8, "home significant", "home significant", "home significant"),
    ("WEEK1", "CHI", "MIN", -1, 1, "MIN", -9.5, -2.3, -8.7, "away significant", "away significant", "away significant"),
    ("WEEK1", "NYJ", "PIT", 3, -3, "PIT", -10.9, -4.4, -10.3, "away significant", "away significant", "away significant"),
    ("WEEK1", "CLV", "CIN", 5.5, -5.5, "CIN", -13.1, -3.9, -4.1, "away significant", "away significant", "away significant"),
    ("WEEK2", "BLT", "CLV", -12.5, 12.5, "BLT", 22.6, 15.9, 13.6, "home significant", "home significant", "home significant"),
    ("WEEK2", "DET", "CHI", -4.5, 4.5, "DET", 17.1, 17.4, 8.6, "home significant", "home significant", "home significant"),
    ("WEEK2", "MIA", "NE", -2.5, 2.5, "MIA", 6.6, 5, 4.6, "home significant", "home significant", "home significant"),
    ("WEEK2", "PIT", "SEA", -2.5, 2.5, "PIT", 1.6, 4.5, 2.2, "home significant", "home significant", "home significant"),
    ("WEEK2", "KC", "PHI", -1.5, 1.5, "PHI", -4.3, -12.6, -0.8, "away significant", "away significant", "away significant"),
    ("WEEK2", "TEN", "LA", 5.5, -5.5, "LA", -17.7, -5.2, -12.3, "away significant", "away significant", "away significant"),
    ("WEEK2", "LV", "LAC", 2.5, -2.5, "LAC", -20.8, -7.2, -21.5, "away significant", "away significant", "away significant"),
    ("WEEK3", "PHI", "LA", -4.5, 4.5, "PHI", 8.7, 12.7, 10.8, "home significant", "home significant", "home significant"),
    ("WEEK3", "CHI", "DAL", -3, 3, "CHI", 4, 6.2, 4.4, "home significant", "home significant", "home significant"),
    ("WEEK3", "LAC", "DEN", -1.5, 1.5, "LAC", 3.2, 0.8, 2.6, "home significant", "home significant", "home significant"),
    ("WEEK3", "JAX", "HST", 1.5, -1.5, "HST", -8.9, -1, -12.1, "away significant", "away significant", "away significant"),
    ("WEEK3", "CLV", "GB", 5.5, -5.5, "GB", -14, -8.9, -5.2, "away significant", "away significant", "away significant"),
    ("WEEK3", "TEN", "IND", -1.5, 1.5, "IND", -16.3, -11.8, -6.9, "away significant", "away significant", "away significant"),
    ("WEEK3", "NE", "PIT", -1.5, 1.5, "PIT", -18.8, -15.8, -9.9, "away significant", "away significant", "away significant"),
    ("WEEK3", "NYG", "KC", 6.5, -6.5, "KC", -20.4, -15.1, -11, "away significant", "away significant", "away significant"),
    ("WEEK4", "DET", "CLV", -10.5, 10.5, "DET", 23.3, 13.8, 15.6, "home significant", "home significant", "home significant"),
    ("WEEK4", "HST", "TEN", -6.5, 6.5, "HST", 16.7, 7.8, 9, "home significant", "home significant", "home significant"),
    ("WEEK4", "TB", "PHI", 2.5, -2.5, "PHI", -7, -8.3, -14.4, "away significant", "away significant", "away significant"),
    ("WEEK4", "LV", "CHI", 1.5, -1.5, "CHI", -7.3, -1.5, -11.9, "away significant", "away significant", "away significant"),
    ("WEEK4", "DAL", "GB", 1.5, -1.5, "GB", -11.8, -4.5, -16.8, "away significant", "away significant", "away significant"),
    ("WEEK4", "NYG", "LAC", 3, -3, "LAC", -21.6, -12.2, -11.8, "away significant", "away significant", "away significant"),
    ("WEEK5", "ARZ", "TEN", -6, 6, "ARZ", 18, 13.6, 2.4, "home significant", "home significant", "home significant"),
    ("WEEK5", "IND", "LV", -2.5, 2.5, "IND", 13.8, 17.1, 4.8, "home significant", "home significant", "home significant"),
    ("WEEK5", "BLT", "HST", -7.5, 7.5, "BLT", 9.5, 19, 0.5, "home significant", "home significant", "home significant"),
    ("WEEK5", "PHI", "DEN", -4.5, 4.5, "PHI", 6.3, 2.4, 16.5, "home significant", "home significant", "home significant"),
    ("WEEK5", "JAX", "KC", 4.5, -4.5, "KC", -14.3, -9.1, -14.8, "away significant", "away significant", "away significant"),
    ("WEEK5", "CLV", "MIN", 7, -7, "MIN", -15.7, -9.3, -5.1, "away significant", "away significant", "away significant"),
    ("WEEK6", "NYJ", "DEN", 6.5, -6.5, "DEN", -10.8, -3.3, -10, "away significant", "away significant", "away significant"),
    ("WEEK6", "MIA", "LAC", 1, -1, "LAC", -15.3, -7.2, -10.9, "away significant", "away significant", "away significant"),
    ("WEEK6", "NYG", "PHI", 7, -7, "PHI", -24.7, -26.1, -13.4, "away significant", "away significant", "away significant"),
    ("WEEK7", "KC", "LV", -9.5, 9.5, "KC", 19.6, 20.7, 10.1, "home significant", "home significant", "home significant"),
    ("WEEK7", "DEN", "NYG", -7.5, 7.5, "DEN", 18.4, 7.1, 13.5, "home significant", "home significant", "home significant"),
    ("WEEK7", "LAC", "IND", -6.5, 6.5, "LAC", 7, 4.5, 2.3, "home significant", "home significant", "home significant"),
    ("WEEK7", "CIN", "PIT", -4.5, 4.5, "PIT", -3.5, -0.4, -8.3, "away significant", "away significant", "away significant"),
    ("WEEK7", "MIN", "PHI", 2.5, -2.5, "PHI", -7.1, -10.9, -8.9, "away significant", "away significant", "away significant"),
    ("WEEK8", "PHI", "NYG", -10.5, 10.5, "PHI", 24.7, 13.4, 26.1, "home significant", "home significant", "home significant"),
    ("WEEK8", "BLT", "CHI", -7, 7, "BLT", 16.4, 19.5, 6.6, "home significant", "home significant", "home significant"),
    ("WEEK8", "IND", "TEN", -3.5, 3.5, "IND", 16.3, 6.9, 11.8, "home significant", "home significant", "home significant"),
    ("WEEK8", "DEN", "DAL", -4.5, 4.5, "DEN", 14.3, 11.1, 11.4, "home significant", "home significant", "home significant"),
    ("WEEK8", "KC", "WAS", -3.5, 3.5, "KC", 10.8, 18.4, 1.8, "home significant", "home significant", "home significant"),
    ("WEEK9", "PIT", "IND", -3.5, 3.5, "PIT", 3.9, 0.1, 4.7, "home significant", "home significant", "home significant"),
    ("WEEK9", "HST", "DEN", 1.5, -1.5, "DEN", -3.4, -2.7, -2.6, "away significant", "away significant", "away significant"),
    ("WEEK9", "NYG", "SF", 3.5, -3.5, "SF", -17.6, -3.9, -15.4, "away significant", "away significant", "away significant"),
    ("WEEK9", "MIA", "BLT", 5.5, -5.5, "BLT", -18.2, -6.3, -22.6, "away significant", "away significant", "away significant"),
    ("WEEK9", "TEN", "LAC", 4.5, -4.5, "LAC", -23.3, -14.2, -11.3, "away significant", "away significant", "away significant"),
    ("WEEK9", "NE", "ATL", -3, 3, "ATL", -23.7, -4.8, -23.9, "away significant", "away significant", "away significant"),
    ("WEEK10", "TB", "NE", -5.5, 5.5, "TB", 18, 17.8, 2.7, "home significant", "home significant", "home significant"),
    ("WEEK10", "DEN", "LV", -6.5, 6.5, "DEN", 17.6, 16.8, 8.5, "home significant", "home significant", "home significant"),
    ("WEEK10", "HST", "JAX", -3.5, 3.5, "HST", 8.9, 12.1, 1, "home significant", "home significant", "home significant"),
    ("WEEK10", "CHI", "NYG", -6, 6, "CHI", 8.1, 2.2, 6.5, "home significant", "home significant", "home significant"),
    ("WEEK10", "NYJ", "CLV", -2.5, 2.5, "NYJ", 5.7, 0.1, 1.9, "home significant", "home significant", "home significant"),
    ("WEEK10", "GB", "PHI", 1.5, -1.5, "PHI", -8.8, -10.8, -9.3, "away significant", "away significant", "away significant"),
    ("WEEK11", "MIN", "CHI", -2.5, 2.5, "MIN", 9.5, 8.7, 2.3, "home significant", "home significant", "home significant"),
    ("WEEK11", "PIT", "CIN", 1.5, -1.5, "PIT", 3.5, 8.3, 0.4, "home significant", "home significant", "home significant"),
    ("WEEK11", "NE", "NYJ", -5.5, 5.5, "NYJ", -7.9, -0.8, -10.2, "away significant", "away significant", "away significant"),
    ("WEEK11", "JAX", "LAC", 1.5, -1.5, "LAC", -15.5, -6.2, -15.6, "away significant", "away significant", "away significant"),
    ("WEEK11", "NYG", "GB", 4.5, -4.5, "GB", -15.9, -6.6, -12.8, "away significant", "away significant", "away significant"),
    ("WEEK11", "TEN", "HST", 3, -3, "HST", -16.7, -9, -7.8, "away significant", "away significant", "away significant"),
    ("WEEK11", "CLV", "BLT", 8.5, -8.5, "BLT", -22.6, -13.6, -15.9, "away significant", "away significant", "away significant"),
    ("WEEK12", "DET", "NYG", -9.5, 9.5, "DET", 25.2, 21.4, 13.3, "home significant", "home significant", "home significant"),
    ("WEEK12", "BLT", "NYJ", -11.5, 11.5, "BLT", 16.9, 26.4, 1.1, "home significant", "home significant", "home significant"),
    ("WEEK12", "CIN", "NE", -5.5, 5.5, "CIN", 15.3, 14.2, 2.8, "home significant", "home significant", "home significant"),
    ("WEEK12", "KC", "IND", -9.5, 9.5, "KC", 5.8, 3.7, 5.2, "home significant", "home significant", "home significant"),
    ("WEEK12", "LV", "CLV", -3.5, 3.5, "CLV", -1.1, -5.1, -4.9, "away significant", "away significant", "away significant"),
    ("WEEK12", "CHI", "PIT", -2.5, 2.5, "PIT", -10.4, -9.9, -3.4, "away significant", "away significant", "away significant"),
    ("WEEK12", "TEN", "SEA", 1.5, -1.5, "SEA", -18.6, -7.4, -9.4, "away significant", "away significant", "away significant"),
    ("WEEK12", "DAL", "PHI", 4.5, -4.5, "PHI", -20.6, -24, -17.4, "away significant", "away significant", "away significant"),
    ("WEEK13", "LAC", "LV", -6.5, 6.5, "LAC", 20.8, 21.5, 7.2, "home significant", "home significant", "home significant"),
    ("WEEK13", "PHI", "CHI", -7, 7, "PHI", 16.6, 9.4, 21.4, "home significant", "home significant", "home significant"),
    ("WEEK13", "TEN", "JAX", 1, -1, "JAX", -7.8, -0.7, -3, "away significant", "away significant", "away significant"),
    ("WEEK13", "WAS", "DEN", -2.5, 2.5, "DEN", -8.8, -0.2, -14.5, "away significant", "away significant", "away significant"),
    ("WEEK13", "CLV", "SF", 5.5, -5.5, "SF", -15.7, -6.2, -7.8, "away significant", "away significant", "away significant"),
    ("WEEK13", "DAL", "KC", 6, -6, "KC", -16.3, -13, -15, "away significant", "away significant", "away significant"),
    ("WEEK14", "DET", "DAL", -6, 6, "DET", 21.1, 25.4, 11.2, "home significant", "home significant", "home significant"),
    ("WEEK14", "GB", "CHI", -3.5, 3.5, "GB", 7.8, 8.8, 1.9, "home significant", "home significant", "home significant"),
    ("WEEK14", "BLT", "PIT", -8.5, 8.5, "BLT", 6, 11.4, 1.4, "home significant", "home significant", "home significant"),
    ("WEEK14", "KC", "HST", -6.5, 6.5, "KC", 5.4, 6.5, 4.3, "home significant", "home significant", "home significant"),
    ("WEEK14", "LAC", "PHI", 2.5, -2.5, "PHI", -3.1, -11.8, -3.7, "away significant", "away significant", "away significant"),
    ("WEEK14", "JAX", "IND", -3, 3, "IND", -8.5, -3.8, -11.2, "away significant", "away significant", "away significant"),
    ("WEEK14", "LV", "DEN", 3.5, -3.5, "DEN", -17.6, -8.5, -16.8, "away significant", "away significant", "away significant"),
    ("WEEK15", "PHI", "LV", -10.5, 10.5, "PHI", 23.9, 23.1, 21.1, "home significant", "home significant", "home significant"),
    ("WEEK15", "SF", "TEN", -7.5, 7.5, "SF", 19.3, 14.9, 5.9, "home significant", "home significant", "home significant"),
    ("WEEK15", "PIT", "MIA", -3, 3, "PIT", 12.2, 6.5, 9.6, "home significant", "home significant", "home significant"),
    ("WEEK15", "DAL", "MIN", 1, -1, "MIN", -13.5, -4.9, -16.7, "away significant", "away significant", "away significant"),
    ("WEEK16", "BLT", "NE", -9, 9, "BLT", 24.8, 26, 12.5, "home significant", "home significant", "home significant"),
    ("WEEK16", "HST", "LV", -4.5, 4.5, "HST", 14.2, 18, 2, "home significant", "home significant", "home significant"),
    ("WEEK16", "DEN", "JAX", -6, 6, "DEN", 12.3, 10.9, 7.5, "home significant", "home significant", "home significant"),
    ("WEEK16", "DET", "PIT", -6.5, 6.5, "DET", 6.7, 9.3, 3.4, "home significant", "home significant", "home significant"),
    ("WEEK16", "CHI", "GB", 1.5, -1.5, "GB", -7.8, -1.9, -8.8, "away significant", "away significant", "away significant"),
    ("WEEK16", "CLV", "BUF", 8.5, -8.5, "BUF", -11.3, -1, -5.2, "away significant", "away significant", "away significant"),
    ("WEEK16", "WAS", "PHI", 1.5, -1.5, "PHI", -15.1, -12.8, -20.8, "away significant", "away significant", "away significant"),
    ("WEEK16", "DAL", "LAC", 1, -1, "LAC", -17.5, -10.1, -15.8, "away significant", "away significant", "away significant"),
    ("WEEK16", "NYG", "MIN", 2.5, -2.5, "MIN", -17.6, -7, -12.7, "away significant", "away significant", "away significant"),
    ("WEEK16", "TEN", "KC", 7, -7, "KC", -22.1, -17.1, -10.5, "away significant", "away significant", "away significant"),
    ("WEEK17", "IND", "JAX", -1.5, 1.5, "IND", 8.5, 11.2, 3.8, "home significant", "home significant", "home significant"),
    ("WEEK17", "NYJ", "NE", 1.5, -1.5, "NYJ", 7.9, 10.2, 0.8, "home significant", "home significant", "home significant"),
    ("WEEK17", "LAC", "HST", -3.5, 3.5, "LAC", 6.6, 7.3, 1.4, "home significant", "home significant", "home significant"),
    ("WEEK17", "BUF", "PHI", -1.5, 1.5, "PHI", -11.5, -10.8, -17.2, "away significant", "away significant", "away significant"),
    ("WEEK18", "PHI", "WAS", -4.5, 4.5, "PHI", 15.1, 20.8, 12.8, "home significant", "home significant", "home significant"),
    ("WEEK18", "CIN", "CLV", -8.5, 8.5, "CIN", 13.1, 4.1, 3.9, "home significant", "home significant", "home significant"),
    ("WEEK18", "JAX", "TEN", -4.5, 4.5, "JAX", 7.8, 3, 0.7, "home significant", "home significant", "home significant"),
    ("WEEK18", "DEN", "LAC", -2.5, 2.5, "LAC", -3.2, -2.6, -0.8, "away significant", "away significant", "away significant"),
    ("WEEK18", "PIT", "BLT", 4.5, -4.5, "BLT", -6, -1.4, -11.4, "away significant", "away significant", "away significant"),
    ("WEEK18", "NE", "MIA", -2.5, 2.5, "MIA", -6.6, -4.6, -5, "away significant", "away significant", "away significant"),
    ("WEEK18", "CHI", "DET", 1.5, -1.5, "DET", -17.1, -8.6, -17.4, "away significant", "away significant", "away significant"),
    ("WEEK18", "LV", "KC", 6, -6, "KC", -19.6, -10.1, -20.7, "away significant", "away significant", "away significant"),
]

def convert_odds_to_decimal(line: float) -> float:
    """Convert point spread to rough decimal odds (simplified)"""
    if line < 0:
        return 1.0 + (100 / abs(line * 10))
    else:
        return 1.0 + (abs(line * 10) / 100)

def simulate_game_score(home_team: str, away_team: str, spread: float, pick: str, overall_adv: float) -> tuple:
    """
    Simulate realistic game scores based on spread and pick confidence.
    Returns (home_score, away_score, winner, correct_pick, pick_covered_spread)
    """

    # Base scores (realistic NFL range)
    base_home = random.randint(14, 31)
    base_away = random.randint(14, 31)

    # Adjust based on spread and advantage
    spread_factor = abs(spread) / 2
    advantage_factor = abs(overall_adv) / 10

    # Apply spread influence
    if spread < 0:  # Home team favored
        home_score = base_home + int(spread_factor) + random.randint(-3, 7)
        away_score = base_away + random.randint(-3, 3)
    else:  # Away team favored
        away_score = base_away + int(spread_factor) + random.randint(-3, 7)
        home_score = base_home + random.randint(-3, 3)

    # Apply advantage influence (stronger picks tend to win more)
    if "significant" in str(overall_adv).lower():
        if pick == home_team:
            home_score += random.randint(0, 4)
        else:
            away_score += random.randint(0, 4)

    # Ensure reasonable scores
    home_score = max(7, min(45, home_score))
    away_score = max(7, min(45, away_score))

    # Determine winner
    winner = home_team if home_score > away_score else away_team

    # Check if pick was correct
    correct_pick = 1 if pick == winner else 0

    # Check if pick covered the spread
    actual_spread = away_score - home_score  # Negative if home wins by more
    adjusted_spread = actual_spread + spread  # Add the betting line

    pick_covered = 0
    if adjusted_spread == 0:  # Push
        pick_covered = 0
    elif pick == home_team and adjusted_spread > 0:  # Home pick covers
        pick_covered = 1
    elif pick == away_team and adjusted_spread < 0:  # Away pick covers
        pick_covered = 1

    return home_score, away_score, winner, correct_pick, pick_covered

def create_picks_results_table(conn: sqlite3.Connection):
    """Create the picks_results table with all required columns"""
    cursor = conn.cursor()

    # Drop table if exists
    cursor.execute("DROP TABLE IF EXISTS picks_results")

    # Create table with all columns
    cursor.execute("""
        CREATE TABLE picks_results (
            WEEK TEXT,
            Home_Team TEXT,
            Away_Team TEXT,
            Home_Score INTEGER,
            Away_Score INTEGER,
            Home_Odds_Close REAL,
            Away_Odds_Close REAL,
            Home_Line_Close REAL,
            Away_Line_Close REAL,
            Game_Pick TEXT,
            Winner TEXT,
            Correct_Pick INTEGER,
            Pick_Covered_Spread INTEGER,
            Overall_Adv REAL,
            Offense_Adv REAL,
            Defense_Adv REAL,
            Off_Comp_Adv REAL,
            Def_Comp_Adv REAL,
            Overall_Adv_Sig TEXT,
            Offense_Adv_Sig TEXT,
            Defense_Adv_Sig TEXT,
            Off_Comp_Adv_Sig TEXT,
            Def_Comp_Adv_Sig TEXT
        )
    """)

    conn.commit()

def populate_picks_results():
    """Main function to populate the picks_results table"""
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)

        # Create table
        create_picks_results_table(conn)

        cursor = conn.cursor()

        print(f"Processing {len(PICKS_DATA)} games...")

        successful_inserts = 0

        for pick_data in PICKS_DATA:
            week, home_team, away_team, home_line, away_line, game_pick, overall_adv, offense_adv, defense_adv, overall_sig, offense_sig, defense_sig = pick_data

            # Simulate game
            home_score, away_score, winner, correct_pick, pick_covered = simulate_game_score(
                home_team, away_team, home_line, game_pick, overall_adv
            )

            # Convert lines to odds (simplified)
            home_odds = convert_odds_to_decimal(home_line)
            away_odds = convert_odds_to_decimal(away_line)

            # Insert into database
            cursor.execute("""
                INSERT INTO picks_results (
                    WEEK, Home_Team, Away_Team, Home_Score, Away_Score,
                    Home_Odds_Close, Away_Odds_Close, Home_Line_Close, Away_Line_Close,
                    Game_Pick, Winner, Correct_Pick, Pick_Covered_Spread,
                    Overall_Adv, Offense_Adv, Defense_Adv,
                    Off_Comp_Adv, Def_Comp_Adv,
                    Overall_Adv_Sig, Offense_Adv_Sig, Defense_Adv_Sig,
                    Off_Comp_Adv_Sig, Def_Comp_Adv_Sig
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                week, home_team, away_team, home_score, away_score,
                home_odds, away_odds, home_line, away_line,
                game_pick, winner, correct_pick, pick_covered,
                overall_adv, offense_adv, defense_adv,
                None, None,  # Off_Comp_Adv and Def_Comp_Adv (not provided in data)
                overall_sig, offense_sig, defense_sig,
                None, None   # Off_Comp_Adv_Sig and Def_Comp_Adv_Sig (not provided)
            ))

            successful_inserts += 1

            # Print progress every 10 games
            if successful_inserts % 10 == 0:
                print(f"Processed {successful_inserts} games...")

        # Commit all changes
        conn.commit()

        # Print summary statistics
        cursor.execute("SELECT COUNT(*) FROM picks_results")
        total_games = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM picks_results WHERE Correct_Pick = 1")
        correct_picks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM picks_results WHERE Pick_Covered_Spread = 1")
        spread_covers = cursor.fetchone()[0]

        overall_accuracy = (correct_picks / total_games) * 100 if total_games > 0 else 0
        spread_accuracy = (spread_covers / total_games) * 100 if total_games > 0 else 0

        print(f"\n=== SUMMARY ===")
        print(f"Total games processed: {total_games}")
        print(f"Correct winner picks: {correct_picks} ({overall_accuracy:.1f}%)")
        print(f"Spread covers: {spread_covers} ({spread_accuracy:.1f}%)")
        print(f"Database updated successfully!")

        # Show sample of results
        print(f"\n=== SAMPLE RESULTS ===")
        cursor.execute("""
            SELECT WEEK, Home_Team, Away_Team, Home_Score, Away_Score, 
                   Game_Pick, Winner, Correct_Pick, Pick_Covered_Spread
            FROM picks_results 
            LIMIT 5
        """)

        results = cursor.fetchall()
        for result in results:
            week, home, away, h_score, a_score, pick, winner, correct, covered = result
            print(f"{week}: {away} @ {home} ({a_score}-{h_score}) | Pick: {pick} | Winner: {winner} | Correct: {'✓' if correct else '✗'} | Covered: {'✓' if covered else '✗'}")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("Populating picks_results table with simulated data...")
    populate_picks_results()
