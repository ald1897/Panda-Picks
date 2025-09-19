import sqlite3
from panda_picks.db.database import drop_tables, create_tables, get_connection
from panda_picks.analysis.advanced_features import build_matchup_features, build_team_week_features


def setup_db():
    drop_tables()
    create_tables()
    return get_connection()


def insert_synthetic(conn, season:int, week:int):
    cur = conn.cursor()
    # spreads
    cur.executemany("INSERT INTO spreads (WEEK, Home_Team, Away_Team, Home_Score, Away_Score, Home_Odds_Close, Away_Odds_Close, Home_Line_Close, Away_Line_Close) VALUES (?,?,?,?,?,?,?,?,?)", [
        (f"WEEK{week}",'AAA','BBB',None,None,-110,100,-2,2),
        (f"WEEK{week}",'CCC','DDD',None,None,-120,105,-3,3)
    ])
    # advanced stats offense & defense composites
    rows=[
        (season, week,'offense','AAA',15, 1.0, 'ts'),
        (season, week,'defense','AAA',10, 0.5, 'ts'),
        (season, week,'offense','BBB',12, 0.2, 'ts'),
        (season, week,'defense','BBB',14, 0.8, 'ts'),
        (season, week,'offense','CCC',9, -0.2, 'ts'),
        (season, week,'defense','CCC',11, 0.1, 'ts'),
        (season, week,'offense','DDD',8, -0.4, 'ts'),
        (season, week,'defense','DDD',7, -0.6, 'ts'),
    ]
    cur.executemany("INSERT OR REPLACE INTO advanced_stats (season, week, type, TEAM, composite_score, z_score, last_updated) VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()


def test_build_team_and_matchup_features():
    season=2025; week=5
    conn = setup_db()
    try:
        insert_synthetic(conn, season, week)
        team_df = build_team_week_features(conn, season, week)
        assert not team_df.empty, 'Team features empty'
        assert {'AAA','BBB','CCC','DDD'}.issubset(set(team_df['TEAM'])), 'Missing teams'
        matchup_df = build_matchup_features(conn, season, week)
        assert not matchup_df.empty, 'Matchup features empty'
        row = matchup_df[(matchup_df.Home_Team=='AAA') & (matchup_df.Away_Team=='BBB')].iloc[0]
        # home_off_vs_away_def = AAA offense 15 - BBB defense 14 = 1
        assert abs(row.home_off_vs_away_def - 1.0) < 1e-6
        # home_def_vs_away_off = AAA defense 10 - BBB offense 12 = -2
        assert abs(row.home_def_vs_away_off + 2.0) < 1e-6
        # net_home_adv = 1 + (-2) = -1
        assert abs(row.net_home_adv + 1.0) < 1e-6
    finally:
        conn.close()

