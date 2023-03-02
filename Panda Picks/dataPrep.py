import time
import pdf_scraper
import matchups


def start():
    print('Starting PFF Grades')
    pdf_scraper.getGrades()
    time.sleep(5)
    print('Starting Matchups')
    matchups.matchups()
    time.sleep(5)
    print("Done!")


if __name__ == '__main__':
    start()
