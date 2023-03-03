import logging
import time
import pdf_scraper
import matchups
import picks
import spreads
import backtest


def start():
    print('Starting PFF Grades')
    pdf_scraper.getGrades()
    print('Done PFF Grades')
    time.sleep(1)
    print('Starting Matchup Data')
    matchups.matchups()
    print("Done Matchup Data")
    time.sleep(1)
    print('Starting Picks')
    picks.makePicks()
    print("Done Making Picks")
    time.sleep(1)
    print("Getting Spread Info")
    spreads.getSpreads()
    print("Spread Info Consumed")
    time.sleep(1)
    print("Backtesting")
    backtest.runTests()
    print('Backtesting completed')


if __name__ == '__main__':
    start()
