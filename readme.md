### Panda Picks Project

#### Overview
The Panda Picks project is an NFL betting backtest application that predicts game outcomes and evaluates betting strategies. The application uses various data sources, including team grades, matchups, and spreads, to make informed betting picks. It also provides a Streamlit-based web interface for users to interact with the data and visualize results.

#### Project Structure
- `src/`
  - `app.py`: Main Streamlit application file that displays predictions, picks data, week stats, and summary stats.
  - `backtest.py`: Contains functions to backtest betting strategies and calculate winnings.
  - `create_spreads.py`: Fetches and processes NFL game data from an API to create spreads.
  - `main.py`: Orchestrates the execution of various modules to scrape data, make picks, and backtest strategies.
  - `matchups.py`: Scrapes NFL matchup data from a website and processes it.
  - `pdf_scraper.py`: Extracts team grades from a PDF file and processes them.
  - `picks.py`: Generates game picks based on team grades and matchups.
  - `spreads.py`: Processes and merges spread data with team abbreviations.

#### Key Features
- **Dynamic Bankroll and Bet Amount**: Users can set their starting bankroll and bet amount through the Streamlit sidebar.
- **Data Visualization**: The application uses Altair to create charts for visualizing predictions and summary statistics.
- **Comprehensive Data Processing**: Merges various data sources, including team grades, matchups, and spreads, to make informed game picks.
- **Backtesting**: Evaluates betting strategies by calculating winnings and win percentages over multiple weeks.

#### How to Run
1. **Install Dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```sh
   streamlit run src/app.py
   ```

3. **Generate Data**:
   - Run `main.py` to scrape data, make picks, and backtest strategies:
     ```sh
     python src/main.py
     ```

#### Deployment
To deploy the application on AWS using Elastic Beanstalk:
1. **Install AWS CLI and EB CLI**:
   ```sh
   pip install awscli awsebcli
   ```

2. **Configure AWS CLI**:
   ```sh
   aws configure
   ```

3. **Initialize Elastic Beanstalk**:
   ```sh
   eb init -p python-3.8 my-streamlit-app
   ```

4. **Create an Environment and Deploy**:
   ```sh
   eb create my-streamlit-env
   eb deploy
   ```

5. **Open Your Application**:
   ```sh
   eb open
   ```

#### Files Description
- **`app.py`**: Main application file for the Streamlit interface.
- **`backtest.py`**: Contains functions for backtesting betting strategies.
- **`create_spreads.py`**: Fetches and processes NFL game data to create spreads.
- **`main.py`**: Orchestrates the execution of data scraping, pick making, and backtesting.
- **`matchups.py`**: Scrapes and processes NFL matchup data.
- **`pdf_scraper.py`**: Extracts and processes team grades from a PDF file.
- **`picks.py`**: Generates game picks based on processed data.
- **`spreads.py`**: Processes and merges spread data with team abbreviations.

#### Data Sources
- **Team Grades**: Extracted from a PDF file using `pdf_scraper.py`.
- **Matchups**: Scraped from a website using `matchups.py`.
- **Spreads**: Fetched from an API and processed using `create_spreads.py`.

#### Contact
For any questions or issues, please contact the project maintainer.