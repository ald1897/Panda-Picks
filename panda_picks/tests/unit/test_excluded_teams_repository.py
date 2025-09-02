import os
import tempfile
import sqlite3
import time
import pytest

from panda_picks.data.repositories.excluded_teams_repository import ExcludedTeamsRepository

@pytest.fixture()
def temp_db(monkeypatch):
    from panda_picks import config
    from panda_picks.db.database import get_connection
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    monkeypatch.setattr(config, 'DATABASE_PATH', path)
    # create blank DB (table will be created lazily)
    conn = get_connection()
    yield conn
    conn.close()
    # Retry delete a few times for Windows file lock release
    for _ in range(5):
        try:
            if os.path.exists(path):
                os.remove(path)
            break
        except PermissionError:
            time.sleep(0.1)


def test_set_and_get_exclusions(temp_db):
    repo = ExcludedTeamsRepository()
    week = 'WEEK1'
    # Initially empty
    assert repo.get_exclusions(week) == []
    # Add exclusions
    repo.set_exclusions(week, ['EAGLES', 'COWBOYS', 'EAGLES'])  # duplicate EAGLES
    got = repo.get_exclusions(week)
    assert got == sorted(['EAGLES', 'COWBOYS'])  # sorted uniqueness guaranteed
    # Replace with different list
    repo.set_exclusions(week, ['BILLS'])
    assert repo.get_exclusions(week) == ['BILLS']
    # Clear by setting empty list
    repo.set_exclusions(week, [])
    assert repo.get_exclusions(week) == []


def test_isolated_weeks(temp_db):
    repo = ExcludedTeamsRepository()
    repo.set_exclusions('WEEK1', ['A', 'B'])
    repo.set_exclusions('WEEK2', ['C'])
    assert repo.get_exclusions('WEEK1') == ['A', 'B']
    assert repo.get_exclusions('WEEK2') == ['C']
