from panda_picks.db.database import get_connection
import math
from typing import List, Dict, Any

# Centralized color palette
COLORS = {
    'primary': '#48872B',    # Kelly Green
    'secondary': '#ff9800',  # Orange
    'accent': '#3f51b5',     # Deep blue (old primary)
    'card1': '#5DE224',      # Light Green
    'card2': '#ff7043',      # Deep orange
    'card3': '#5c6bc0',      # Light blue-purple (old card1),
}

# --- Data Access & Computation Helpers --- #

def _resolve_home_line(home_line, away_line):
    """Return the spread line relative to the home team if available, otherwise infer from away line.
    If both missing returns None."""
    if home_line is not None:
        return home_line
    if away_line is not None:
        return -away_line
    return None


def _grade_pick_row(home_team, away_team, pick_side, home_score, away_score, home_line, away_line):
    """Determine outcome for a single pick.
    Returns: (is_push: bool, is_win: bool or None if pending)
    Push = (home_score + line) == away_score.
    Win if picked side covers after excluding pushes.
    """
    if home_score is None or away_score is None:
        return (False, None)
    line = _resolve_home_line(home_line, away_line)
    if line is None:
        return (False, None)
    adjusted = home_score + line
    if adjusted == away_score:  # push
        return (True, None)
    home_covers = adjusted > away_score
    if pick_side == home_team:
        return (False, home_covers)
    if pick_side == away_team:
        return (False, not home_covers)
    return (False, None)


def get_total_picks() -> int:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM picks")
        result = cursor.fetchone()[0]
        conn.close()
        return result
    except Exception:
        return 0


def get_win_rate() -> str:
    # Recompute dynamically ignoring pushes (do not trust Pick_Covered_Spread if pushes misclassified)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT Home_Team, Away_Team, Game_Pick, Home_Score, Away_Score, Home_Line_Close, Away_Line_Close
            FROM picks_results
            WHERE Home_Score IS NOT NULL AND Away_Score IS NOT NULL
        """)
        rows = cur.fetchall()
        conn.close()
        wins = 0
        graded = 0
        for home, away, pick_side, hs, ascore, hline, aline in rows:
            is_push, is_win = _grade_pick_row(home, away, pick_side, hs, ascore, hline, aline)
            if is_win is None:  # push or pending
                continue
            graded += 1
            if is_win:
                wins += 1
        return f"{(wins/graded)*100:.1f}%" if graded else "0%"
    except Exception:
        return "0%"


def get_upcoming_games() -> int:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM spreads WHERE Home_Score IS NULL")
        result = cursor.fetchone()[0]
        conn.close()
        return result
    except Exception:
        return 0


def get_recent_picks() -> List[Dict[str, Any]]:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
        SELECT WEEK, Home_Team, Away_Team, Game_Pick, 
        CASE WHEN Pick_Covered_Spread = 1 THEN 'WIN' WHEN Pick_Covered_Spread = 0 THEN 'LOSS' ELSE 'PENDING' END as Result
        FROM picks_results 
        ORDER BY WEEK LIMIT 15
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [
                {'Week': week, 'Home': home, 'Away': away, 'Pick': pick, 'Result': result}
                for week, home, away, pick, result in rows
            ]
        return []
    except Exception:
        return []


def calculate_win_rates() -> Dict[str, str]:
    # Recompute home/away and overall excluding pushes
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT WEEK, Home_Team, Away_Team, Game_Pick, Home_Score, Away_Score, Home_Line_Close, Away_Line_Close
            FROM picks_results
            WHERE Home_Score IS NOT NULL AND Away_Score IS NOT NULL
        """)
        rows = cur.fetchall()
        conn.close()
        overall_wins = overall_total = home_wins = home_total = away_wins = away_total = 0
        for wk, home, away, pick_side, hs, ascore, hline, aline in rows:
            is_push, is_win = _grade_pick_row(home, away, pick_side, hs, ascore, hline, aline)
            if is_win is None:
                continue
            overall_total += 1
            if pick_side == home:
                home_total += 1
            elif pick_side == away:
                away_total += 1
            if is_win:
                overall_wins += 1
                if pick_side == home:
                    home_wins += 1
                elif pick_side == away:
                    away_wins += 1
        def pct(w, t):
            return f"{(w/t)*100:.1f}%" if t else "0.0%"
        return {'overall': pct(overall_wins, overall_total), 'home': pct(home_wins, home_total), 'away': pct(away_wins, away_total)}
    except Exception:
        return {'overall': '0.0%', 'home': '0.0%', 'away': '0.0%'}

def get_upcoming_picks():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Include any available final scores from picks_results (may be NULL for upcoming games)
        cursor.execute("""
            SELECT p.WEEK, p.Home_Team, p.Away_Team, p.Game_Pick, p.Overall_Adv,
                   pr.Home_Score, pr.Away_Score,
                   p.Home_Line_Close, p.Away_Line_Close
            FROM picks p
            LEFT JOIN picks_results pr
              ON pr.WEEK = p.WEEK AND pr.Home_Team = p.Home_Team AND pr.Away_Team = p.Away_Team
        """)
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return []
        # Determine max absolute overall advantage for confidence normalization (ignore NULLs)
        max_adv = max((abs(r[4]) for r in rows if r[4] is not None), default=1) or 1
        data = []
        for week, home, away, pick, overall_adv, home_score, away_score, home_line, away_line in rows:
            if overall_adv is None:
                confidence_pct = 'N/A'
            else:
                confidence = (abs(overall_adv) / max_adv) * 100
                confidence_pct = f"{confidence:.1f}%"
            # Determine spread relative to home team (home line). If missing, infer from away line.
            spread_val = None
            if home_line is not None:
                spread_val = home_line
            elif away_line is not None:
                spread_val = -away_line
            if spread_val is None:
                spread_str = ''
            else:
                spread_str = 'PK' if abs(spread_val) < 0.0001 else f"{spread_val:+g}"
            data.append({
                'Row_ID': f"{week}-{home}-{away}",
                'Week': week,
                'Home_Team': home,
                'Away_Team': away,
                'Spread': spread_str,
                'Predicted_Pick': pick,
                'Confidence_Score': confidence_pct,
                'Home_Score': '' if home_score is None else home_score,
                'Away_Score': '' if away_score is None else away_score,
            })
        return data
    except Exception:
        return []

def get_team_grades():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT TEAM, OVR, OFF, DEF FROM grades")
        rows = cursor.fetchall()
        conn.close()
        return [
            {'Team': r[0], 'Overall_Grade': r[1], 'Offense_Grade': r[2], 'Defense_Grade': r[3]}
            for r in rows
        ] if rows else []
    except Exception:
        return []

def get_spreads_data():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT WEEK, Home_Team, Away_Team, Home_Line_Close FROM spreads")
        rows = cursor.fetchall()
        conn.close()
        return [
            {'Week': r[0], 'Home_Team': r[1], 'Away_Team': r[2], 'Line': r[3]} for r in rows
        ] if rows else []
    except Exception:
        return []

def run_backtest(strategy: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "SELECT Home_Team, Away_Team, Home_Score, Away_Score, Home_Line_Close FROM spreads WHERE Home_Score IS NOT NULL"
        cursor.execute(query)
        games = cursor.fetchall()
        # Fallback: use picks_results if spreads has no scored games (allow NULL line, will filter later)
        if not games:
            cursor.execute("SELECT Home_Team, Away_Team, Home_Score, Away_Score, Home_Line_Close FROM picks_results WHERE Home_Score IS NOT NULL")
            games = cursor.fetchall()
        conn.close()
        if not games:
            return {'metrics': {'roi': '0.0%', 'win_rate': '0.0%', 'profit_loss': '$0'}, 'chart_data': []}
        profit = 0
        wins = 0
        total_bets = 0
        chart_data = []
        processed = 0
        for (home_team, away_team, home_score, away_score, home_line) in games:
            if home_line is None or home_score is None or away_score is None:
                continue
            favorite = home_team if home_line < 0 else away_team
            underdog = away_team if home_line < 0 else home_team
            if strategy == 'Favorites':
                bet_on = favorite
            elif strategy == 'Underdogs':
                bet_on = underdog
            elif strategy == 'Home Teams':
                bet_on = home_team
            else:
                bet_on = favorite  # default fallback
            home_covers = (home_score + home_line) > away_score
            if (home_score + home_line) == away_score:
                continue  # push
            total_bets += 1
            processed += 1
            won = (bet_on == home_team and home_covers) or (bet_on == away_team and not home_covers)
            if won:
                wins += 1
                profit += 91
            else:
                profit -= 100
            chart_data.append({'game': processed, 'profit': profit})
        if total_bets == 0:
            return {'metrics': {'roi': '0.0%', 'win_rate': '0.0%', 'profit_loss': '$0'}, 'chart_data': []}
        roi = (profit / (total_bets * 100)) * 100
        win_rate = (wins / total_bets) * 100
        return {
            'metrics': {'roi': f"{roi:.1f}%", 'win_rate': f"{win_rate:.1f}%", 'profit_loss': f"${profit}"},
            'chart_data': chart_data,
        }
    except Exception:
        return {'metrics': {'roi': '0.0%', 'win_rate': '0.0%', 'profit_loss': '$0'}, 'chart_data': []}

def get_all_team_names():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT TEAM FROM grades ORDER BY TEAM")
        teams = [row[0] for row in cursor.fetchall()]
        conn.close()
        return teams if teams else []
    except Exception:
        return []

def get_team_details(team_name: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT OVR, OFF, DEF FROM grades WHERE TEAM = ?", (team_name,))
        grades = cursor.fetchone()
        cursor.execute("""
            SELECT WEEK, Home_Team, Away_Team, Home_Score, Away_Score
            FROM spreads
            WHERE (Home_Team = ? OR Away_Team = ?) AND Home_Score IS NOT NULL
            ORDER BY WEEK DESC LIMIT 5
        """, (team_name, team_name))
        recent_results = cursor.fetchall()
        cursor.execute("""
            SELECT WEEK, Home_Team, Away_Team
            FROM spreads
            WHERE (Home_Team = ? OR Away_Team = ?) AND Home_Score IS NULL
            ORDER BY WEEK ASC LIMIT 5
        """, (team_name, team_name))
        upcoming_schedule = cursor.fetchall()
        cursor.execute("SELECT Home_Team, Away_Team, Home_Score, Away_Score, Home_Line_Close, Away_Line_Close FROM spreads WHERE Home_Score IS NOT NULL AND (Home_Team = ? OR Away_Team = ?)", (team_name, team_name))
        all_games = cursor.fetchall()
        ats_wins = 0
        ats_losses = 0
        for home_team, away_team, home_score, away_score, home_line, away_line in all_games:
            if home_score is None or away_score is None or home_line is None: continue
            if (home_score + home_line) == away_score: continue
            home_covers = (home_score + home_line) > away_score
            team_is_home = (team_name == home_team)
            if (team_is_home and home_covers) or ((not team_is_home) and (not home_covers)):
                ats_wins += 1
            else:
                ats_losses += 1
        conn.close()
        return {
            'grades': {'Overall': grades[0], 'Offense': grades[1], 'Defense': grades[2]} if grades else {},
            'recent_results': [
                {'Week': r[0], 'Matchup': f"{r[2]} @ {r[1]}", 'Score': f"{r[4]}-{r[3]}"} for r in recent_results
            ],
            'upcoming_schedule': [
                {'Week': r[0], 'Matchup': f"{r[2]} @ {r[1]}"} for r in upcoming_schedule
            ],
            'ats_record': f"{ats_wins}-{ats_losses}"
        }
    except Exception:
        return {'grades': {}, 'recent_results': [], 'upcoming_schedule': [], 'ats_record': '0-0'}

def get_win_rate_trend():
    # Compute weekly win rate excluding pushes using raw scores/lines instead of Pick_Covered_Spread
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT TRIM(WEEK) as WK, Home_Team, Away_Team, Game_Pick, Home_Score, Away_Score, Home_Line_Close, Away_Line_Close
            FROM picks_results
            WHERE Home_Score IS NOT NULL AND Away_Score IS NOT NULL
            ORDER BY CAST(REPLACE(UPPER(WK),'WEEK','') AS INTEGER)
        """)
        rows = cur.fetchall()
        conn.close()
        if not rows:
            # Fallback to original join logic if picks_results empty
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT TRIM(p.WEEK) as WK,
                       p.Home_Team, p.Away_Team, p.Game_Pick,
                       s.Home_Score, s.Away_Score, s.Home_Line_Close, s.Away_Line_Close
                FROM picks p
                JOIN spreads s ON TRIM(p.WEEK)=TRIM(s.WEEK) AND p.Home_Team=s.Home_Team AND p.Away_Team=s.Away_Team
                WHERE s.Home_Score IS NOT NULL AND s.Away_Score IS NOT NULL
                ORDER BY CAST(REPLACE(UPPER(WK),'WEEK','') AS INTEGER)
            """)
            rows = cur.fetchall()
            conn.close()
        if not rows:
            return {'weeks': [], 'win_rates': []}
        from collections import defaultdict
        week_stats = defaultdict(lambda: {'wins': 0, 'graded': 0})
        for wk, home, away, pick_side, hs, ascore, hline, aline in rows:
            is_push, is_win = _grade_pick_row(home, away, pick_side, hs, ascore, hline, aline)
            if is_win is None:
                continue
            week_stats[wk]['graded'] += 1
            if is_win:
                week_stats[wk]['wins'] += 1
        weeks_sorted = sorted(week_stats.keys(), key=lambda w: int(str(w).upper().replace('WEEK','') or 0))
        weeks=[]; win_rates=[]
        for wk in weeks_sorted:
            g = week_stats[wk]['graded']
            if g>0:
                weeks.append(wk)
                win_rates.append(round((week_stats[wk]['wins']/g)*100,1))
        return {'weeks': weeks, 'win_rates': win_rates}
    except Exception:
        return {'weeks': [], 'win_rates': []}

def get_weekly_win_rate_rows():
    # Build rows with wins/losses excluding pushes
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT TRIM(WEEK) as WK, Home_Team, Away_Team, Game_Pick, Home_Score, Away_Score, Home_Line_Close, Away_Line_Close
            FROM picks_results
            WHERE Home_Score IS NOT NULL AND Away_Score IS NOT NULL
            ORDER BY CAST(REPLACE(UPPER(WK),'WEEK','') AS INTEGER)
        """)
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return []
        from collections import defaultdict
        agg = defaultdict(lambda: {'wins':0,'losses':0})
        for wk, home, away, pick_side, hs, ascore, hline, aline in rows:
            is_push, is_win = _grade_pick_row(home, away, pick_side, hs, ascore, hline, aline)
            if is_win is None:
                continue
            if is_win:
                agg[wk]['wins'] += 1
            else:
                agg[wk]['losses'] += 1
        data=[]
        for wk in sorted(agg.keys(), key=lambda w: int(str(w).upper().replace('WEEK','') or 0)):
            wins=agg[wk]['wins']; losses=agg[wk]['losses']; total=wins+losses
            number_part = wk.upper().replace('WEEK','')
            try:
                num = int(number_part)
            except ValueError:
                num = 0
            padded_week = f"WEEK{num:02d}" if num else wk
            rate = f"{(wins/total)*100:.1f}%" if total else '0.0%'
            data.append({'Week': padded_week, 'Total_Picks': total, 'Wins': wins, 'Losses': losses, 'Win_Rate': rate})
        return data
    except Exception:
        return []

def get_week_picks_for_combos(week: str):
    try:
        wk = str(week).upper().replace('WEEK','')
        try:
            wk_int = int(wk)
        except ValueError:
            return []
        week_key = f"WEEK{wk_int}"
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
             SELECT p.WEEK, p.Home_Team, p.Away_Team, p.Game_Pick,
                    s.Home_Odds_Close, s.Away_Odds_Close,
                    p.Home_Line_Close, p.Away_Line_Close,
                    p.Overall_Adv, p.Offense_Adv, p.Defense_Adv,
                    p.Off_Comp_Adv, p.Def_Comp_Adv
             FROM picks p
             LEFT JOIN spreads s
               ON p.WEEK = s.WEEK AND p.Home_Team = s.Home_Team AND p.Away_Team = s.Away_Team
             WHERE p.WEEK = ?
         """, (week_key,))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return []
        def american_to_prob(odds):
            try:
                o = float(odds)
                if o > 0:
                    return 100.0 / (o + 100.0)
                else:
                    return (-o) / ((-o) + 100.0)
            except Exception:
                return math.nan
        data = []
        for r in rows:
            (wk, home, away, pick_side, home_odds, away_odds, home_line, away_line,
             overall_adv, off_adv, def_adv, off_comp_adv, def_comp_Adv) = r
            home_prob = american_to_prob(home_odds)
            away_prob = american_to_prob(away_odds)
            if not (isinstance(home_prob, float) and math.isnan(home_prob)) and not (isinstance(away_prob, float) and math.isnan(away_prob)):
                total = home_prob + away_prob
                if total > 0:
                    home_prob /= total
                    away_prob /= total
            data.append({
                'WEEK': wk,
                'Home_Team': home,
                'Away_Team': away,
                'Game_Pick': pick_side,
                'Home_Odds_Close': home_odds,
                'Away_Odds_Close': away_odds,
                'Home_Win_Prob': home_prob,
                'Away_Win_Prob': away_prob,
                'Pick_Prob': home_prob if pick_side == home else (away_prob if pick_side == away else math.nan),
                'Pick_Edge': overall_adv,
                'Home_Line_Close': home_line,
                'Away_Line_Close': away_line
            })
        return data
    except Exception:
        return []

def get_available_weeks():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT WEEK FROM spreads ORDER BY CAST(REPLACE(UPPER(WEEK),'WEEK','') AS INTEGER)")
        weeks = [row[0] for row in cur.fetchall()]
        conn.close()
        return weeks
    except Exception:
        return []

def get_week_matchups(week: str):
    try:
        if not week:
            return []
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT WEEK, Home_Team, Away_Team, Home_Line_Close, Home_Odds_Close, Away_Odds_Close
            FROM spreads WHERE WEEK = ? ORDER BY Home_Team
        """, (week,))
        rows = cur.fetchall()
        conn.close()
        return [
            {
                'Week': r[0],
                'Home_Team': r[1],
                'Away_Team': r[2],
                'Home_Line_Close': r[3],
                'Home_Odds_Close': r[4],
                'Away_Odds_Close': r[5],
                'Label': f"{r[2]} @ {r[1]}"
            } for r in rows
        ]
    except Exception:
        return []

def get_matchup_details(week: str, home: str, away: str):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM spreads WHERE WEEK=? AND Home_Team=? AND Away_Team=?", (week, home, away))
        spread = cur.fetchone()
        spread_cols = [d[0] for d in cur.description] if spread else []
        spread_data = dict(zip(spread_cols, spread)) if spread else {}
        cur.execute("SELECT * FROM picks WHERE WEEK=? AND Home_Team=? AND Away_Team=?", (week, home, away))
        pick = cur.fetchone()
        pick_cols = [d[0] for d in cur.description] if pick else []
        pick_data = dict(zip(pick_cols, pick)) if pick else {}
        cur.execute("SELECT * FROM grades WHERE TEAM=?", (home,))
        home_grade = cur.fetchone()
        home_cols = [d[0] for d in cur.description] if home_grade else []
        home_grade_data = dict(zip(home_cols, home_grade)) if home_grade else {}
        cur.execute("SELECT * FROM grades WHERE TEAM=?", (away,))
        away_grade = cur.fetchone()
        away_cols = [d[0] for d in away_grade] if away_grade else []
        away_grade_data = dict(zip(away_cols, away_grade)) if away_grade else {}
        conn.close()
        return {'spread': spread_data, 'pick': pick_data, 'home_grades': home_grade_data, 'away_grades': away_grade_data}
    except Exception:
        return {'spread': {}, 'pick': {}, 'home_grades': {}, 'away_grades': {}}

def get_weekly_profit_and_balance(start_balance: float = 1000.0, stake: float = 100.0):
    """Return dict with weeks, weekly_profit, rolling_balance based on picks_results.
    Win assumed +91 net (standard -110) on $100 stake, loss -100. Pending (NULL) ignored.
    start_balance: starting bankroll.
    stake: stake per pick.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT TRIM(WEEK) as WK,
                   SUM(CASE WHEN Pick_Covered_Spread = 1 THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN Pick_Covered_Spread = 0 THEN 1 ELSE 0 END) AS losses
            FROM picks_results
            WHERE Pick_Covered_Spread IS NOT NULL
            GROUP BY TRIM(WEEK)
            ORDER BY CAST(REPLACE(UPPER(WK),'WEEK','') AS INTEGER)
        """)
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return {'weeks': [], 'weekly_profit': [], 'rolling_balance': [], 'weekly_wagered': [], 'cumulative_roi': []}
        weeks = []
        weekly_profit = []
        rolling_balance = []
        weekly_wagered = []
        cumulative_roi = []
        balance = start_balance
        for wk, wins, losses in rows:
            wins = wins or 0
            losses = losses or 0
            total_graded = wins + losses
            profit = wins * (stake * 0.91) - losses * stake
            amount_wagered = total_graded * stake
            balance += profit
            roi_pct = ((balance - start_balance) / start_balance) * 100 if start_balance else 0.0
            weeks.append(wk)
            weekly_profit.append(round(profit, 2))
            weekly_wagered.append(round(amount_wagered, 2))
            rolling_balance.append(round(balance, 2))
            cumulative_roi.append(round(roi_pct, 2))
        return {'weeks': weeks, 'weekly_profit': weekly_profit, 'rolling_balance': rolling_balance, 'weekly_wagered': weekly_wagered, 'cumulative_roi': cumulative_roi}
    except Exception:
        return {'weeks': [], 'weekly_profit': [], 'rolling_balance': [], 'weekly_wagered': [], 'cumulative_roi': []}

def get_teaser_weekly_profit_and_balance(start_balance: float = 1000.0, stake_per_combo: float = 100.0, sizes=(2,3,4)):
    """Compute weekly profit and rolling balance using teaser combo strategy with 6-point adjustment.
    Assumptions / Rules:
      - Apply a 6-point teaser adjustment to the spread in favor of the picked team: adjusted_line = original_line + 6 (line is relative to picked side).
        * If the picked team is Home, original_line = Home_Line_Close. If Away, use Away_Line_Close if present else -Home_Line_Close.
      - Leg wins if (picked_score + adjusted_line) > opponent_score (strict; pushes treated as losses for simplicity).
      - Any leg loss causes every combo containing it to lose the full stake; all legs in combo must win to cash.
      - Static teaser odds mapping: 2:-135, 3:+140, 4:+240 per winning combo.
      - Profit per winning combo: positive odds o => stake * (o/100); negative odds -x => stake * (100/x).
      - Weekly profit = sum(win profits) - (stake_per_combo * losing_combos).
      - Rolling balance accumulates from start_balance.
      - Sizes with insufficient legs skipped.
    Returns dict: {weeks, weekly_profit, rolling_balance, detail: {week: {size: {wins, losses, profit}}}}
    """
    import itertools
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT TRIM(WEEK) as WK,
                   Home_Team, Away_Team, Game_Pick,
                   Home_Score, Away_Score,
                   Home_Line_Close, Away_Line_Close,
                   Pick_Covered_Spread, Correct_Pick
            FROM picks_results
            WHERE Home_Score IS NOT NULL AND Away_Score IS NOT NULL
            ORDER BY CAST(REPLACE(UPPER(WK),'WEEK','') AS INTEGER)
        """)
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return {'weeks': [], 'weekly_profit': [], 'rolling_balance': [], 'detail': {}, 'weekly_wagered': [], 'cumulative_roi': []}
        from collections import defaultdict
        by_week = defaultdict(list)
        for wk, home, away, pick, h_score, a_score, h_line, a_line, pick_cov, correct_pick in rows:
            by_week[wk].append((home, away, pick, h_score, a_score, h_line, a_line, pick_cov, correct_pick))
        static_odds = {2: -135, 3: 140, 4: 240}
        weeks_sorted = sorted(by_week.keys(), key=lambda w: int(str(w).upper().replace('WEEK','') or 0))
        weeks=[]; weekly_profit=[]; rolling=[]; balance=start_balance; detail={}; weekly_wagered_list=[]; cumulative_roi=[]
        for wk in weeks_sorted:
            games = by_week[wk]
            legs = []
            leg_summary = []
            for idx,(home,away,pick,h_score,a_score,h_line,a_line,pick_cov,correct_pick) in enumerate(games):
                if pick == home:
                    base_line = h_line if h_line is not None else (-a_line if a_line is not None else None)
                    picked_score = h_score; opp_score = a_score
                else:
                    base_line = a_line if a_line is not None else (-h_line if h_line is not None else None)
                    picked_score = a_score; opp_score = h_score
                teaser_line = None; teaser_win = None
                if base_line is not None:
                    teaser_line = base_line + 6
                    teaser_win = (picked_score + teaser_line) > opp_score
                leg_won = bool(correct_pick == 1)
                legs.append({'team': pick, 'won': leg_won, 'idx': idx})
                leg_summary.append({'team': pick,'result': 'WIN' if leg_won else 'LOSS','correct_pick': correct_pick,'teaser_line': teaser_line,'teaser_win': teaser_win,'picked_score': picked_score,'opp_score': opp_score})
            week_profit = 0.0
            detail[wk] = {'legs': leg_summary}
            if not legs:
                weeks.append(wk); weekly_profit.append(0.0); balance += 0.0; rolling.append(round(balance,2)); weekly_wagered_list.append(0.0); cumulative_roi.append(round(((balance-start_balance)/start_balance)*100,2)); continue
            try:
                import math as _math
                M = len(legs)
                N = sum(1 for l in legs if l['won'])
                active_sizes = [k for k in sizes if k <= M and k in static_odds]
                total_combos_cnt = sum(_math.comb(M,k) for k in active_sizes)
                winning_combos_cnt = sum(_math.comb(N,k) for k in active_sizes if N >= k)
            except Exception:
                total_combos_cnt = 0; winning_combos_cnt = 0; M=len(legs); N=sum(1 for l in legs if l['won']); active_sizes=[]
            weekly_amount_wagered_for_week = 0.0
            from itertools import combinations as _comb
            for size in sizes:
                if size not in static_odds or len(legs) < size:
                    continue
                wins_count=0; loss_count=0; size_profit=0.0
                all_combos = list(_comb(legs, size))
                weekly_amount_wagered_for_week += len(all_combos) * stake_per_combo
                for combo in all_combos:
                    if all(l['won'] for l in combo):
                        am = static_odds[size]
                        profit = stake_per_combo * (am/100.0) if am > 0 else stake_per_combo * (100.0/abs(am))
                        size_profit += profit
                        wins_count += 1
                    else:
                        size_profit -= stake_per_combo
                        loss_count += 1
                if wins_count or loss_count:
                    week_profit += size_profit
                    detail[wk][size] = {'wins': wins_count, 'losses': loss_count, 'profit': round(size_profit,2)}
            detail[wk]['summary'] = {
                'legs': M,
                'winning_legs': N,
                'active_sizes': active_sizes,
                'winning_combos': winning_combos_cnt,
                'total_combos': total_combos_cnt,
                'win_ratio': f"{winning_combos_cnt}/{total_combos_cnt}" if total_combos_cnt else '0/0',
                'amount_wagered': weekly_amount_wagered_for_week
            }
            weeks.append(wk)
            weekly_profit.append(round(week_profit,2))
            weekly_wagered_list.append(round(weekly_amount_wagered_for_week,2))
            balance += week_profit
            rolling.append(round(balance,2))
            cumulative_roi.append(round(((balance-start_balance)/start_balance)*100,2))
        return {'weeks': weeks, 'weekly_profit': weekly_profit, 'rolling_balance': rolling, 'detail': detail, 'weekly_wagered': weekly_wagered_list, 'cumulative_roi': cumulative_roi}
    except Exception:
        return {'weeks': [], 'weekly_profit': [], 'rolling_balance': [], 'detail': {}, 'weekly_wagered': [], 'cumulative_roi': []}
