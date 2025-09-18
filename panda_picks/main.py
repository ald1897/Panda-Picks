# panda_picks/main.py
import logging
import time
import argparse
from panda_picks.data import get_pff_grades, advanced_stats
from panda_picks.analysis import picks
# With this:
from panda_picks.analysis.backtest import backtest
from panda_picks.analysis import spreads as create_spreads  # Alias to match existing code
from panda_picks.db import database as db
from panda_picks import config

def start(weeks: list[int] | None = None):
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
    logging.info('Done Advanced Stats')
    time.sleep(0.1)
    logging.info('Creating Spread Info')
    create_spreads.main()
    logging.info('Spread Info Created')
    time.sleep(0.1)
    logging.info('Starting Picks')
    picks.makePicks(weeks=weeks)
    logging.info('Done Making Picks')
    time.sleep(0.1)
    logging.info('Backtesting')
    backtest()
    logging.info('Backtesting completed')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Panda Picks pipeline')
    parser.add_argument('--weeks', help='Comma-separated week numbers to process (e.g. 2 or 2,3,4). If omitted, all weeks 1-18.', default=None)
    args = parser.parse_args()
    weeks_list = None
    if args.weeks:
        raw = [w.strip() for w in args.weeks.split(',') if w.strip()]
        parsed = []
        for r in raw:
            try:
                iv = int(r)
                if 1 <= iv <= 18:
                    parsed.append(iv)
            except ValueError:
                pass
        weeks_list = parsed or None
    start(weeks=weeks_list)
