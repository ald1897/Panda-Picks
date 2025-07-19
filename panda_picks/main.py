# panda_picks/main.py
import logging
import time
from panda_picks.data import pdf_scraper, advanced_stats
from panda_picks.analysis import picks
# With this:
from panda_picks.analysis.backtest import backtest
from panda_picks.analysis import spreads as create_spreads  # Alias to match existing code
from panda_picks.db import database as db
from panda_picks import config

def start():
    logging.basicConfig(filename=config.PROJECT_ROOT / 'panda_picks.log', level=logging.DEBUG)
    logging.info('Starting Panda Picks')
    logging.info('Dropping Tables')
    db.drop_tables()
    logging.info('Creating Tables')
    db.create_tables()
    time.sleep(0.1)
    logging.info('Starting PFF Grades')
    pdf_scraper.getGrades()
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
    time.sleep(0.1)
    logging.info("Backtesting")
    backtest()
    logging.info('Backtesting completed')



if __name__ == '__main__':
    start()
