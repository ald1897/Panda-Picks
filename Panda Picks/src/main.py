import logging
import time
import pdf_scraper
import picks
import create_spreads
import backtest
import get_advanced_stats
import db.db as db


def start():
    logging.basicConfig(filename='panda_picks.log', level=logging.DEBUG)
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
    backtest.backtest()
    logging.info('Backtesting completed')


if __name__ == '__main__':
    start()
