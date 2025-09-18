"""Utilities for initializing prior season grades and capturing weekly snapshots.

Functions:
    populate_grades_prior(from_table='grades', csv_path=None, source_label='import')
        Populate grades_prior table from existing grades table or a CSV file.
    snapshot_current_grades(season: int, week: str)
        Snapshot current grades into grades_snapshots for auditing.

Design:
 - grades_prior holds one definitive prior-season row per team.
 - grades_snapshots holds per-week snapshots of evolving current season grades.

Safe to call repeatedly (idempotent for same data). Re-running populate_grades_prior
will overwrite existing rows for teams provided (using INSERT OR REPLACE).
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path
import logging
from typing import Optional

from panda_picks.db.database import get_connection, create_tables
from panda_picks import config

GRADE_COLUMNS = [
    'TEAM','OVR','OFF','PASS','RUN','RECV','PBLK','RBLK','DEF','RDEF','TACK','PRSH','COV',
    'WINS','LOSSES','TIES','PTS_SCORED','PTS_ALLOWED'
]

PRIOR_TABLE = 'grades_prior'
GRADES_TABLE = 'grades'
SNAP_TABLE = 'grades_snapshots'
SNAP_ALLOWED_COLS = {
    'Season','Week','TEAM','OVR','OFF','PASS','RUN','RECV','PBLK','RBLK','DEF','RDEF','TACK','PRSH','COV',
    'WINS','LOSSES','TIES','PTS_SCORED','PTS_ALLOWED','SNAPSHOT_TS'
}


def _table_exists(conn, name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def populate_grades_prior(from_table: str = GRADES_TABLE, csv_path: Optional[Path] = None, source_label: str = 'import') -> int:
    """Populate grades_prior from an existing grades table or a CSV file.

    Args:
        from_table: table name containing source grades (default 'grades'). Ignored if csv_path provided.
        csv_path: optional path to CSV file containing prior season final grades.
        source_label: metadata label stored in SOURCE column.
    Returns:
        number of rows written.
    """
    conn = get_connection()
    try:
        create_tables()  # ensure schema
        if csv_path:
            df = pd.read_csv(csv_path)
        else:
            if not _table_exists(conn, from_table):
                logging.warning(f"populate_grades_prior: source table {from_table} missing")
                return 0
            df = pd.read_sql_query(f"SELECT * FROM {from_table}", conn)
        if df.empty:
            logging.warning("populate_grades_prior: source data empty")
            return 0
        # Normalize columns (add missing)
        for col in GRADE_COLUMNS:
            if col not in df.columns:
                df[col] = None
        prior_df = df[GRADE_COLUMNS].copy()
        prior_df['SOURCE'] = source_label
        # Replace existing rows (primary key on TEAM) using to_sql replace semantics through temp table then upsert
        cur = conn.cursor()
        # Write to temporary table in memory for deterministic columns
        prior_df.to_sql('_temp_prior', conn, if_exists='replace', index=False)
        # Upsert into grades_prior
        insert_cols = [c for c in prior_df.columns if c != 'SOURCE']
        col_list = ','.join(['TEAM'] + [c for c in GRADE_COLUMNS if c != 'TEAM'])
        # Use INSERT OR REPLACE to fully overwrite
        cur.execute("PRAGMA foreign_keys = OFF")
        cur.execute("BEGIN")
        cur.execute(f"DELETE FROM {PRIOR_TABLE} WHERE TEAM IN (SELECT TEAM FROM _temp_prior)")
        prior_df[['TEAM','OVR','OFF','PASS','RUN','RECV','PBLK','RBLK','DEF','RDEF','TACK','PRSH','COV','WINS','LOSSES','TIES','PTS_SCORED','PTS_ALLOWED','SOURCE']].to_sql(PRIOR_TABLE, conn, if_exists='append', index=False)
        conn.commit()
        return len(prior_df)
    finally:
        conn.close()


def snapshot_current_grades(season: int, week: str) -> int:
    """Snapshot current grades into grades_snapshots.

    Args:
        season: four-digit season year.
        week: week label (e.g. 'WEEK1').
    Returns:
        number of rows written (inserted or replaced).
    """
    conn = get_connection()
    try:
        if not _table_exists(conn, GRADES_TABLE):
            logging.warning("snapshot_current_grades: grades table missing")
            return 0
        df = pd.read_sql_query(f"SELECT * FROM {GRADES_TABLE}", conn)
        if df.empty:
            return 0
        if 'TEAM' not in df.columns:
            logging.warning("snapshot_current_grades: TEAM column missing")
            return 0
        df['Season'] = season
        df['Week'] = week
        # Restrict to allowed snapshot schema columns (ignore extras like LAST_UPDATED)
        keep_cols = [c for c in df.columns if c in SNAP_ALLOWED_COLS]
        # Ensure Season & Week first for readability
        ordered = ['Season','Week'] + [c for c in keep_cols if c not in ('Season','Week')]
        cur = conn.cursor()
        cur.execute("BEGIN")
        cur.execute(f"DELETE FROM {SNAP_TABLE} WHERE Season=? AND Week=?", (season, week))
        df[ordered].to_sql(SNAP_TABLE, conn, if_exists='append', index=False)
        conn.commit()
        return len(df)
    finally:
        conn.close()


def ensure_prior_populated(source_label: str = 'initial_snapshot') -> int:
    """Populate grades_prior from grades table if grades_prior is empty.
    Returns existing row count (if already populated) or number inserted.
    """
    conn = get_connection()
    try:
        if not _table_exists(conn, PRIOR_TABLE):
            create_tables()
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(1) FROM {PRIOR_TABLE}")
        existing = cur.fetchone()[0]
        if existing and existing > 0:
            return existing
        # populate
        conn.close()  # reuse existing function which opens its own connection
        inserted = populate_grades_prior(source_label=source_label)
        return inserted
    finally:
        try: conn.close()
        except Exception: pass


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Grades migration utilities')
    sub = parser.add_subparsers(dest='cmd')

    p_prior = sub.add_parser('prior', help='Populate grades_prior')
    p_prior.add_argument('--csv', type=str, help='CSV path for prior grades (if omitted, uses grades table)')
    p_prior.add_argument('--source', type=str, default='import', help='Source label metadata')
    p_prior.add_argument('--ensure', action='store_true', help='Only populate if empty (idempotent)')

    p_snap = sub.add_parser('snapshot', help='Snapshot current grades')
    p_snap.add_argument('--season', type=int, required=True)
    p_snap.add_argument('--week', type=str, required=True)

    args = parser.parse_args()
    if args.cmd == 'prior':
        if getattr(args, 'ensure', False):
            count = ensure_prior_populated(source_label=args.source)
            print(f"grades_prior rows after ensure: {count}")
        else:
            count = populate_grades_prior(csv_path=Path(args.csv) if args.csv else None, source_label=args.source)
            print(f"Populated {count} prior grade rows")
    elif args.cmd == 'snapshot':
        count = snapshot_current_grades(season=args.season, week=args.week)
        print(f"Snapshot {count} current grade rows for {args.season} {args.week}")
    else:
        parser.print_help()
