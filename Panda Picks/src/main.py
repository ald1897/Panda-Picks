import logging
import time
import pdf_scraper
import matchups
import picks
import create_spreads
import backtest
import get_advanced_stats
import db


def start():
    logging.basicConfig(filename='panda_picks.log', level=logging.DEBUG)
    print('Starting PFF Grades')
    pdf_scraper.getGrades()
    print('Done PFF Grades')
    time.sleep(0.1)
    print('Starting Advanced Stats')
    get_advanced_stats.main()
    print('Done Advanced Stats')
    time.sleep(0.1)
    print('Starting Matchup Data')
    matchups.matchups()
    print("Done Matchup Data")
    time.sleep(0.1)
    print('Starting Picks')
    picks.makePicks()
    print("Done Making Picks")
    time.sleep(0.1)
    print("Creating Spread Info")
    create_spreads.main()
    print("Spread Info Created")
    time.sleep(0.1)
    print("Backtesting")
    backtest.backtest()
    print('Backtesting completed')


if __name__ == '__main__':
    start()
