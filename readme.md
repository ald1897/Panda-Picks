# Panda Picks - NFL Betting Analysis

## Overview
Panda Picks is an NFL betting analysis tool that predicts game outcomes and evaluates betting strategies. The application uses PFF (Pro Football Focus) team grades and spread data to make informed betting picks, and includes a comprehensive backtesting system to evaluate performance.

## Features
- Extracts and processes team grades from PFF data
- Fetches and analyzes NFL game spreads
- Generates game picks based on team advantages (offense, defense, overall)
- Creates teaser bet combinations (2-team, 3-team, 4-team)
- Backtests betting strategies across NFL season weeks
- Calculates win percentages and potential profits

## Project Structure
```
panda_picks/
├── analysis/
│   ├── backtest.py   # Evaluates betting performance
│   ├── bets.py       # Generates betting combinations
│   ├── picks.py      # Creates game predictions
│   └── spreads.py    # Processes spread information
├── data/
│   ├── advanced_stats.py  # (Optional) Advanced stats analysis
│   └── pdf_scraper.py     # Extracts team grades from PDFs
├── db/
│   └── database.py   # Database operations
├── config.py         # Project configuration
└── main.py           # Main execution script
```

## Getting Started

### Prerequisites
- Python 3.8+
- Required Python packages (install via pip):
    - pandas
    - numpy
    - tabula-py
    - requests
    - sqlite3

### Installation
1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Usage
Run the main script to execute the complete pipeline:
```
python -m panda_picks.main
```

This will:
1. Create/reset the database
2. Extract team grades from PDF data
3. Process NFL spreads
4. Generate game picks
5. Run the backtest on historical data

## How It Works
1. **Data Collection**: The system extracts team grades from PFF data and fetches NFL game spreads.
2. **Analysis**: It calculates advantages between teams based on various metrics.
3. **Picks Generation**: Teams are selected based on significant advantages in key areas.
4. **Bet Combinations**: Multiple bet combinations are generated for teaser bets.
5. **Backtesting**: Historical performance is evaluated to calculate profitability.

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.