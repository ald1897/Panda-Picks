import logging
import time
from pathlib import Path
import pdf_scraper
import matchups
import picks
import spreads
import backtest


def setup_logging():
    """Configure logging for the application."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "panda_picks.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("PandaPicks")


def run_process(logger, name, function, *args, **kwargs):
    """Run a process with timing and error handling."""
    logger.info(f"Starting {name}...")

    start_time = time.time()
    try:
        function(*args, **kwargs)
        elapsed = time.time() - start_time
        logger.info(f"Completed {name} in {elapsed:.2f} seconds")
        return True
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return False


def start(season="2022", start_week=1, end_week=18):
    """
    Run the complete Panda Picks NFL prediction pipeline.

    Args:
        season (str): NFL season year
        start_week (int): First week to process
        end_week (int): Last week to process

    Returns:
        bool: True if pipeline completed successfully, False otherwise
    """
    try:
        # Set up logging
        logger = setup_logging()
        logger.info(f"Starting Panda Picks pipeline for {season} season, weeks {start_week}-{end_week}")

        # Step 1: Extract team grades
        if not run_process(logger, "Team Grades Extraction", pdf_scraper.getGrades):
            logger.error("Failed to extract team grades. Stopping pipeline.")
            return False

        # Step 2: Scrape matchup data
        if not run_process(logger, "Matchup Data Scraping",
                           matchups.scrape_matchups,
                           season=season,
                           start_week=start_week,
                           end_week=end_week):
            logger.error("Failed to scrape matchup data. Stopping pipeline.")
            return False

        # Step 3: Generate picks
        if not run_process(logger, "Game Picks Generation", picks.makePicks):
            logger.error("Failed to generate picks. Stopping pipeline.")
            return False

        # Step 4: Process spread data
        if not run_process(logger, "Spread Data Processing", spreads.getSpreads):
            logger.error("Failed to process spread data. Stopping pipeline.")
            return False

        # Step 5: Run backtests
        if not run_process(logger, "Backtesting", backtest.run_tests):
            logger.error("Failed to run backtests. Pipeline incomplete.")
            return False

        logger.info("Panda Picks pipeline completed successfully")
        return True

    except Exception as e:
        logger.critical(f"Critical error in pipeline: {e}")
        return False


if __name__ == '__main__':
    # You can modify these parameters as needed
    start(season="2022", start_week=1, end_week=18)