import os
from typing import List, Optional
from datetime import datetime
import math

try:
    import tweepy  # type: ignore
except ImportError:  # Tweepy optional at runtime
    tweepy = None  # fallback for environments without tweepy installed yet

from dotenv import load_dotenv
from panda_picks.db.database import get_connection

# Load environment variables (fallback to project root .env if present)
load_dotenv()

# Runtime flags (environment driven)
TWITTER_ENABLED = os.getenv("TWITTER_ENABLED", "0") == "1"
TWITTER_DRY_RUN = os.getenv("TWITTER_DRY_RUN", "1") == "1"  # default dry run ON
TWITTER_HASHTAGS = os.getenv("TWITTER_HASHTAGS", "#NFL #SportsBetting #Picks")
MAX_TWEET_CHARS = 280

# Credentials
consumer_key = os.getenv("TWITTER_CONSUMER_KEY")
consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET")
access_token = os.getenv("TWITTER_ACCESS_TOKEN")
access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")


def _can_post() -> bool:
    if not TWITTER_ENABLED:
        return False
    missing = [k for k, v in {
        'TWITTER_CONSUMER_KEY': consumer_key,
        'TWITTER_CONSUMER_SECRET': consumer_secret,
        'TWITTER_ACCESS_TOKEN': access_token,
        'TWITTER_ACCESS_TOKEN_SECRET': access_token_secret,
    }.items() if not v]
    return len(missing) == 0


def authenticate_twitter():
    """Authenticate with Twitter API (OAuth 1.0a)."""
    if not tweepy:
        raise RuntimeError("tweepy not installed. Install requirements first.")
    auth = tweepy.OAuth1UserHandler(
        consumer_key, consumer_secret,
        access_token, access_token_secret
    )
    api = tweepy.API(auth)
    try:
        api.verify_credentials()
    except Exception as e:
        raise RuntimeError(f"Twitter authentication failed: {e}")
    return api


def _format_pick_row(row) -> str:
    """Format a single pick summary line within a thread."""
    pick_team = row['Game_Pick']
    home = row['Home_Team']
    away = row['Away_Team']
    # Determine opponent for phrasing
    opponent = away if pick_team == home else home
    edge_pct = row.get('Pick_Edge')
    prob = row.get('Pick_Prob')
    implied = row.get('Pick_Implied_Prob')
    cover = row.get('Pick_Cover_Prob')
    def fmt(p):
        return f"{p*100:.1f}%" if p is not None and not math.isnan(p) else "--"
    edge_str = f"{edge_pct*100:+.1f}%" if edge_pct is not None and not math.isnan(edge_pct) else "--"
    prob_str = fmt(prob)
    implied_str = fmt(implied)
    cover_str = fmt(cover)
    return (
        f"{pick_team} over {opponent} | Edge {edge_str} | Win {prob_str} vs {implied_str} | Cover {cover_str}"
    )


def _chunk_lines_to_tweets(lines: List[str], header: str, footer: Optional[str]=None) -> List[str]:
    tweets: List[str] = []
    current = header.strip()
    if len(current) > MAX_TWEET_CHARS:
        # Truncate header if somehow too long (shouldn't normally happen)
        current = current[:MAX_TWEET_CHARS - 3] + '...'
    for line in lines:
        candidate = current + ('\n' if current else '') + line
        if len(candidate) <= MAX_TWEET_CHARS:
            current = candidate
        else:
            tweets.append(current)
            current = line
    if footer:
        # Try to append footer to last tweet or create new
        if len(current + '\n' + footer) <= MAX_TWEET_CHARS:
            current = current + ('\n' if current else '') + footer
        else:
            tweets.append(current)
            # If footer itself is too long, truncate
            if len(footer) > MAX_TWEET_CHARS:
                footer = footer[:MAX_TWEET_CHARS - 3] + '...'
            current = footer
    if current:
        tweets.append(current)
    return tweets


def format_week_picks_thread(week: int, df) -> List[str]:
    """Create a list of tweet texts (thread) summarizing picks for a week."""
    if df is None or df.empty:
        return [f"Week {week} - No qualifying picks this week. {TWITTER_HASHTAGS}"]
    header = f"Week {week} Picks (n={len(df)})"  # hashtags added in footer
    lines = []
    for idx, row in df.iterrows():
        lines.append(f"{len(lines)+1}) {_format_pick_row(row)}")
    footer = TWITTER_HASHTAGS.strip()
    return _chunk_lines_to_tweets(lines, header, footer)


def post_thread(texts: List[str]) -> List[str]:
    """Post a list of tweets as a thread; returns posted tweet IDs or previews when dry-run.
    Honors TWITTER_ENABLED and TWITTER_DRY_RUN flags.
    """
    posted_refs: List[str] = []
    if not _can_post():
        # Just preview; not enabled
        for t in texts:
            print(f"[TWITTER PREVIEW - DISABLED]\n{t}\n{'-'*40}")
        return posted_refs
    if TWITTER_DRY_RUN:
        for t in texts:
            print(f"[TWITTER DRY RUN]\n{t}\n{'-'*40}")
        return posted_refs
    api = authenticate_twitter()
    in_reply_to_id = None
    for t in texts:
        try:
            status = api.update_status(status=t, in_reply_to_status_id=in_reply_to_id, auto_populate_reply_metadata=True)
            in_reply_to_id = status.id
            posted_refs.append(str(status.id))
            print(f"[TWITTER POSTED] id={status.id} chars={len(t)}")
        except Exception as e:
            print(f"Error posting tweet chunk: {e}\nContent: {t}")
            break
    return posted_refs


def publish_week_picks(week: int, picks_df=None) -> List[str]:
    """Fetch (or use provided) week picks and publish (or preview) them as a thread.
    Returns list of posted tweet IDs (or empty if dry run / disabled).
    """
    if picks_df is None:
        conn = get_connection()
        try:
            picks_df = None
            try:
                import pandas as pd  # local import to avoid global dependency issues
                picks_df = pd.read_sql_query("SELECT * FROM picks WHERE WEEK = ? ORDER BY Pick_Edge DESC", conn, params=[f"WEEK{week}"])
            except Exception as e:
                print(f"Could not load picks for week {week}: {e}")
                picks_df = None
        finally:
            conn.close()
    tweets = format_week_picks_thread(week, picks_df)
    return post_thread(tweets)


def publish_latest_week():
    """Determine the latest week present in picks table and publish its picks."""
    conn = get_connection()
    week_num = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT WEEK FROM picks")
        weeks = [row[0] for row in cur.fetchall() if row and row[0]]
        if weeks:
            # WEEK format = 'WEEK3'
            numeric = []
            for w in weeks:
                try:
                    numeric.append(int(str(w).replace('WEEK','')))
                except ValueError:
                    continue
            if numeric:
                week_num = max(numeric)
    except Exception as e:
        print(f"Error determining latest week: {e}")
    finally:
        conn.close()
    if week_num is None:
        print("No weeks found to publish.")
        return []
    return publish_week_picks(week_num)


if __name__ == "__main__":
    # Manual quick test / preview; respects env flags
    target_week = int(os.getenv("PUBLISH_WEEK", "1"))
    ids = publish_week_picks(target_week)
    print(f"Publish result IDs: {ids}")
