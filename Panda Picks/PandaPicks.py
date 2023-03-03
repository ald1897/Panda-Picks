import logging
import time
import pdf_scraper
import matchups
import picks


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



if __name__ == '__main__':
    start()
