"""Advanced NFL stats collection & composite scoring (week-aware).
Minimal clean implementation supporting Phase 0-1.
"""
from __future__ import annotations
import requests, pandas as pd, numpy as np, sqlite3, logging, os, random, re, time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse

try:
    from panda_picks.db.database import get_connection
except ImportError:  # fallback
    def get_connection():
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'nfl_data.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return sqlite3.connect(db_path)

log_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'panda_picks.log')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s - %(message)s',
                    handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
logger = logging.getLogger('advanced_stats')

WEIGHTS = {
    'offense': {
        'epa_per_play': 30,
        'epa_per_pass': 20,
        'epa_per_rush': 10,
        'Success %': 15,
        'Comp %': 5,
        'YAC EPA/Att': 8,
        'ADoT': 3,
        'Eckel %': 10,
        'PROE': 3,
        'Sack %': -5,
        'Scramble %': 2,
        'Int %': -7
    },
    'defense': {
        'epa_per_play': -30,
        'epa_per_pass': -20,
        'epa_per_rush': -10,
        'Success %': -15,
        'Comp %': -5,
        'YAC EPA/Att': -8,
        'ADoT': 2,
        'Eckel %': -10,
        'Sack %': 7,
        'Int %': 7,
        'Pass Yards': -3,
        'Rush Yards': -2
    }
}

SCRAPE_URLS = {
    'offense': 'https://sumersports.com/teams/offensive/',
    'defense': 'https://sumersports.com/teams/defensive/'
}

TEAM_NAME_MAP = {'CLE':'CLV','ARI':'ARZ','LAR':'LA','JAC':'JAX','WSH':'WAS','LV':'LVR'}

TEAM_ABBR_MAP = {
    'arizona cardinals':'ARZ', 'atlanta falcons':'ATL', 'baltimore ravens':'BLT', 'buffalo bills':'BUF',
    'carolina panthers':'CAR', 'chicago bears':'CHI', 'cincinnati bengals':'CIN', 'cleveland browns':'CLV',
    'dallas cowboys':'DAL', 'denver broncos':'DEN', 'detroit lions':'DET', 'green bay packers':'GB',
    'houston texans':'HST', 'indianapolis colts':'IND', 'jacksonville jaguars':'JAX', 'kansas city chiefs':'KC',
    'las vegas raiders':'LVR', 'los angeles chargers':'LAC', 'los angeles rams':'LA', 'miami dolphins':'MIA',
    'minnesota vikings':'MIN', 'new england patriots':'NE', 'new orleans saints':'NO', 'new york giants':'NYG',
    'new york jets':'NYJ', 'philadelphia eagles':'PHI', 'pittsburgh steelers':'PIT', 'san francisco 49ers':'SF',
    'seattle seahawks':'SEA', 'tampa bay buccaneers':'TB', 'tennessee titans':'TEN', 'washington commanders':'WAS'
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0'
]

COLUMN_MAPPING = {  # only map what we expect; unknown cols retained
    'Team':'team', 'EPA/Play':'epa_per_play', 'EPA/Pass':'epa_per_pass', 'EPA/Rush':'epa_per_rush',
    'Comp%':'Comp %', 'INT%':'Int %', 'Sack%':'Sack %'
}

class AdvancedStatsCollector:
    def __init__(self, season: int, week: Optional[int] = None):
        self.season = season
        self.week = week if week is not None else 1
        self.conn = get_connection()
        self.session = self._create_session()

    def __enter__(self): return self
    def __exit__(self, *exc):
        try: self.conn.close()
        except: pass

    def _create_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({'User-Agent': random.choice(USER_AGENTS), 'Accept':'text/html'})
        return s

    def _referrer(self, url: str) -> str:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}/"

    def scrape_team_data(self, kind: str, retries: int = 3) -> Optional[pd.DataFrame]:
        url = SCRAPE_URLS.get(kind)
        if not url:
            return None
        for attempt in range(retries):
            try:
                self.session.headers['Referer'] = self._referrer(url)
                time.sleep(0.5 + random.random())
                r = self.session.get(url, timeout=15)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, 'html.parser')
                table = soup.find('table')
                if not table: continue
                headers = [th.get_text(strip=True) for th in table.find_all('th')]
                if not headers:  # fallback first row
                    first_tr = table.find('tr')
                    if first_tr:
                        headers = [td.get_text(strip=True) for td in first_tr.find_all('td')]
                rows = []
                for tr in table.find_all('tr'):
                    tds = tr.find_all('td')
                    if len(tds) == len(headers) and len(headers) > 2:
                        rows.append([td.get_text(strip=True) for td in tds])
                if not rows:
                    continue
                df = pd.DataFrame(rows, columns=headers)
                return self._clean(df, kind)
            except Exception as e:
                logger.warning(f"{kind} scrape attempt {attempt+1} failed: {e}")
        logger.error(f"Failed to scrape {kind} stats")
        return None

    def _clean(self, df: pd.DataFrame, kind: str) -> pd.DataFrame:
        if df.empty: return df
        out = df.copy()
        for src,dst in COLUMN_MAPPING.items():
            if src in out.columns:
                out.rename(columns={src: dst}, inplace=True)
        team_col = None
        for c in out.columns:
            if c.lower() in ('team','team name','name'): team_col = c; break
        if not team_col: return pd.DataFrame()
        out['team'] = out[team_col].astype(str).apply(lambda x: re.sub(r'^\d+\.\s*','', x.strip()))
        # Map full names to abbreviations
        lower_vals = out['team'].str.lower()
        mapped = []
        for lv, original in zip(lower_vals, out['team']):
            abbr = TEAM_ABBR_MAP.get(lv)
            if not abbr:
                # Try partial match on first word if full not found
                first = lv.split()[0]
                candidates = [v for k,v in TEAM_ABBR_MAP.items() if k.startswith(first)]
                abbr = candidates[0] if candidates else original.upper()[:3]
            mapped.append(abbr)
        out['TEAM'] = mapped
        out.drop(columns=[team_col, 'team'], errors='ignore', inplace=True)
        # numeric conversions (% handling)
        for c in list(out.columns):
            if c == 'TEAM': continue
            if out[c].astype(str).str.contains('%').any():
                out[c] = out[c].astype(str).str.replace('%','', regex=False)
            out[c] = pd.to_numeric(out[c], errors='ignore')
        out['season'] = self.season
        out['week'] = self.week
        out['type'] = kind
        return out

    def normalize_dataframe(self, df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
        norm = df.copy()
        for c in cols:
            if c in df.columns:
                mx, mn = df[c].max(), df[c].min()
                norm[c] = 0.5 if mx == mn else (df[c]-mn)/(mx-mn)
        return norm

    def calculate_composite_scores(self, stats_df: pd.DataFrame, kind: str) -> pd.DataFrame:
        if stats_df.empty: return stats_df
        weights = WEIGHTS.get(kind, {})
        cols = [c for c in weights if c in stats_df.columns]
        if not cols:
            stats_df['composite_score']=0; stats_df['z_score']=0; return stats_df
        norm = self.normalize_dataframe(stats_df, cols)
        inverse = {'int_rate','sack_rate','Int %','Sack %'}
        for c in cols:
            if kind=='offense' and c in inverse:
                norm[c] = 1 - norm[c]
            elif kind=='defense' and c not in inverse:
                norm[c] = 1 - norm[c]
        comp_cols=[]
        for c in cols:
            wc = f"{c}_w"; norm[wc]=norm[c]*weights[c]; comp_cols.append(wc)
        out = stats_df.copy()
        out['composite_score'] = norm[comp_cols].sum(axis=1)
        mu = out['composite_score'].mean(); sd = out['composite_score'].std()
        out['z_score'] = (out['composite_score']-mu)/sd if sd>0 else 0
        out['last_updated'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        return out

    def save_composite_scores(self, df: pd.DataFrame) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS advanced_stats (season INTEGER, week INTEGER, type TEXT, TEAM TEXT, composite_score REAL, z_score REAL, last_updated TEXT, PRIMARY KEY (season, week, type, TEAM))")
            base = {'season','week','type','TEAM','composite_score','z_score','last_updated'}
            df_db = df.copy()
            # Sanitize additional column names (only letters, numbers, underscore)
            import re
            name_map = {}
            existing_safe = set(base)
            def make_safe(c: str) -> str:
                safe = re.sub(r'[^A-Za-z0-9_]', '_', c)
                safe = re.sub(r'_+', '_', safe).strip('_')
                if not safe:
                    safe = 'col'
                orig = safe
                i = 1
                while safe in existing_safe:
                    safe = f"{orig}_{i}"; i += 1
                existing_safe.add(safe)
                return safe
            for col in list(df_db.columns):
                if col in base: continue
                safe = make_safe(col)
                name_map[col] = safe
                if safe != col:
                    df_db[safe] = df_db[col]
            # Add new columns to table if needed
            cur.execute("PRAGMA table_info(advanced_stats)")
            existing_cols = {r[1] for r in cur.fetchall()}
            for col, safe in name_map.items():
                if safe not in existing_cols:
                    series = df_db[col] if col in df_db.columns else df_db[safe]
                    if pd.api.types.is_float_dtype(series) or pd.api.types.is_integer_dtype(series):
                        col_type = 'REAL'
                    else:
                        col_type = 'TEXT'
                    try:
                        cur.execute(f'ALTER TABLE advanced_stats ADD COLUMN "{safe}" {col_type}')
                    except Exception:
                        pass
            self.conn.commit()
            # Refresh columns
            cur.execute("PRAGMA table_info(advanced_stats)")
            existing_cols = {r[1] for r in cur.fetchall()}
            insert_cols = [c for c in base] + [safe for safe in name_map.values() if safe in existing_cols]
            placeholders = ','.join(['?']*len(insert_cols))
            stmt = f"INSERT OR REPLACE INTO advanced_stats ({','.join(insert_cols)}) VALUES ({placeholders})"
            rows = []
            for _, r in df_db.iterrows():
                vals = []
                for c in insert_cols:
                    v = r.get(c)
                    if pd.isna(v):
                        vals.append(None)
                    else:
                        if isinstance(v,(np.floating,np.integer)):
                            vals.append(float(v))
                        else:
                            vals.append(v)
                rows.append(tuple(vals))
            cur.executemany(stmt, rows)
            self.conn.commit()
            logger.info(f"Saved {len(rows)} {df['type'].iloc[0] if len(df)>0 else ''} composite rows (week={self.week})")
            return True
        except Exception as e:
            logger.error(f"save_composite_scores error: {e}")
            return False

    def process_all_stats(self) -> Tuple[Dict[str,pd.DataFrame], Dict[str,pd.DataFrame]]:
        raw: Dict[str,pd.DataFrame] = {}
        comp: Dict[str,pd.DataFrame] = {}
        for kind in ('offense','defense'):
            df = self.scrape_team_data(kind)
            if df is None or df.empty: continue
            raw[kind]=df
            cdf = self.calculate_composite_scores(df, kind)
            comp[kind]=cdf
            self.save_composite_scores(cdf)
        return raw, comp

def main(season: Optional[int]=None, week: Optional[int]=None):
    season_v = season if season is not None else datetime.now().year
    week_v = week if week is not None else 1
    logger.info(f"Advanced stats run season={season_v} week={week_v}")
    try:
        with AdvancedStatsCollector(season_v, week_v) as c:
            raw, comp = c.process_all_stats()
            if not raw:
                logger.warning("No advanced stats collected")
    except Exception as e:
        logger.exception(f"advanced stats main error: {e}")

if __name__ == '__main__':
    main()
