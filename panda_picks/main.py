# panda_picks/main.py
import logging
import time
import os  # added for env flags
from panda_picks.data import get_pff_grades, advanced_stats
from panda_picks.analysis import picks
# With this:
from panda_picks.analysis.backtest import backtest
from panda_picks.analysis import spreads as create_spreads  # Alias to match existing code
from panda_picks.db import database as db
from panda_picks import config

# Optional import inside function to avoid requirement when not publishing

def start():
    logging.basicConfig(filename=config.PROJECT_ROOT / 'panda_picks.log', level=logging.DEBUG)
    logging.info('Starting Panda Picks')
    logging.info('Dropping Tables')
    db.drop_tables()
    logging.info('Creating Tables')
    db.create_tables()
    time.sleep(0.1)
    logging.info('Starting PFF Grades')
    get_pff_grades.getGrades()
    logging.info('PFF Grades Completed')
    time.sleep(0.1)
    logging.info('Storing PFF Grades Data')
    db.store_grades_data()
    logging.info('Done Storing PFF Grades')
    time.sleep(0.1)
    logging.info('Starting Advanced Stats')
    # get_advanced_stats.main()
    logging.info('Done Advanced Stats')
    time.sleep(0.1)
    logging.info("Creating Spread Info")
    create_spreads.main()
    logging.info("Spread Info Created")
    time.sleep(0.1)
    logging.info('Starting Picks')
    picks.makePicks()
    logging.info("Done Making Picks")

    # Optional: auto-publish picks to Twitter if enabled
    if os.getenv("TWITTER_AUTO_PUBLISH", "0") == "1":
        try:
            from panda_picks.publish.twitter import publish_latest_week, publish_week_picks
            week_env = os.getenv("TWITTER_WEEK")
            if week_env:
                try:
                    w = int(week_env)
                    logging.info(f"Auto publishing picks for explicit week {w}")
                    publish_week_picks(w)
                except ValueError:
                    logging.warning(f"Invalid TWITTER_WEEK value: {week_env}; falling back to latest week")
                    publish_latest_week()
            else:
                logging.info("Auto publishing picks for latest week")
                publish_latest_week()
        except Exception as e:
            logging.exception(f"Twitter auto-publish failed: {e}")

    time.sleep(0.1)
    logging.info("Backtesting")
    backtest()
    logging.info('Backtesting completed')


if __name__ == '__main__':
    try:
        start()
    except RuntimeError as e:
        print(f"\n[ERROR] {e}\n\nThe database file could not be reset because it is locked by another process.\nPlease close all applications or processes that may be using the file (such as other Python scripts, database viewers, or editors) and try again.\nOn Windows, you can use Task Manager or Process Explorer to find the locking process.\n")
        import sys
        sys.exit(1)
