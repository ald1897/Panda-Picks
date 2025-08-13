#!/usr/bin/env python3
from router import Router
from nicegui import ui
from panda_picks.db.database import get_connection

# Colors for consistency
COLORS = {
    'primary': '#48872B',    # Kelly Green
    'secondary': '#ff9800',  # Orange
    'accent': '#3f51b5',     # Deep blue (old primary)
    'card1': '#5DE224',      # Light Green
    'card2': '#ff7043',      # Deep orange
    'card3': '#5c6bc0',      # Light blue-purple (old card1)
}

# Data functions with database access
def get_total_picks():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM picks")
        result = cursor.fetchone()[0]
        conn.close()
        return result
    except Exception:
        # No placeholder value; only return 0 if query fails
        return 0

def get_win_rate():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM picks_results WHERE Pick_Covered_Spread = 1")
        correct = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM picks_results")
        total = cursor.fetchone()[0]
        conn.close()
        if total > 0:
            return f"{(correct / total) * 100:.1f}%"
        return "0%"  # Fallback value
    except:
        return "0%"  # Fallback value

def get_upcoming_games():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM spreads WHERE Home_Score IS NULL")
        result = cursor.fetchone()[0]
        conn.close()
        return result
    except:
        return 0  # Fallback value

def get_recent_picks():
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
            formatted_rows = []
            for week, home, away, pick, result in rows:
                formatted_rows.append({
                    'Week': week,
                    'Home': home,
                    'Away': away,
                    'Pick': pick,
                    'Result': result
                })
            return formatted_rows
        else:
            return []  # Return empty list if no rows found
    except:
        return []

def calculate_win_rates():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Overall win rate
        cursor.execute("SELECT COUNT(*) FROM picks_results WHERE Pick_Covered_Spread = 1")
        wins = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM picks_results WHERE Pick_Covered_Spread IS NOT NULL")
        total = cursor.fetchone()[0]
        overall = (wins / total) * 100 if total > 0 else 0

        # Home team win rate
        cursor.execute("SELECT COUNT(*) FROM picks_results WHERE Pick_Covered_Spread = 1 AND Game_Pick = Home_Team")
        home_wins = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM picks_results WHERE Pick_Covered_Spread IS NOT NULL AND Game_Pick = Home_Team")
        home_total = cursor.fetchone()[0]
        home = (home_wins / home_total) * 100 if home_total > 0 else 0

        # Away team win rate
        cursor.execute("SELECT COUNT(*) FROM picks_results WHERE Pick_Covered_Spread = 1 AND Game_Pick = Away_Team")
        away_wins = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM picks_results WHERE Pick_Covered_Spread IS NOT NULL AND Game_Pick = Away_Team")
        away_total = cursor.fetchone()[0]
        away = (away_wins / away_total) * 100 if away_total > 0 else 0

        conn.close()
        return {
            'overall': f"{overall:.1f}%",
            'home': f"{home:.1f}%",
            'away': f"{away:.1f}%"
        }
    except Exception:
        # Return zero win rates if database query fails (no placeholder sample data)
        return {
            'overall': '0.0%',
            'home': '0.0%',
            'away': '0.0%'
        }

def get_upcoming_picks():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Picks table has no date or explicit confidence; derive a confidence proxy from Overall_Adv
        cursor.execute("SELECT WEEK, Home_Team, Away_Team, Game_Pick, Overall_Adv FROM picks")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return []
        # Determine scaling for confidence (normalize absolute Overall_Adv to max)
        max_adv = max(abs(r[4]) for r in rows if r[4] is not None) or 1
        data = []
        for week, home, away, pick, overall_adv in rows:
            if overall_adv is None:
                confidence_pct = 'N/A'
            else:
                confidence = (abs(overall_adv) / max_adv) * 100
                confidence_pct = f"{confidence:.1f}%"
            data.append({
                'Week': week,
                'Home_Team': home,
                'Away_Team': away,
                'Predicted_Pick': pick,
                'Confidence_Score': confidence_pct
            })
        return data
    except Exception:
        return []

def get_team_grades():
    """Fetch team grades using actual schema columns (OVR, OFF, DEF)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT TEAM, OVR, OFF, DEF FROM grades")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [
                {'Team': r[0], 'Overall_Grade': r[1], 'Offense_Grade': r[2], 'Defense_Grade': r[3]}
                for r in rows
            ]
        return []
    except Exception:
        return []

def get_spreads_data():
    """Return spreads data using Home_Line_Close as the line (spread)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT WEEK, Home_Team, Away_Team, Home_Line_Close FROM spreads")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [
                {'Week': r[0], 'Home_Team': r[1], 'Away_Team': r[2], 'Line': r[3]}
                for r in rows
            ]
        return []
    except Exception:
        return []

def run_backtest(strategy: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Use Home_Line_Close as the spread (negative => home favorite)
        query = "SELECT Home_Team, Away_Team, Home_Score, Away_Score, Home_Line_Close FROM spreads WHERE Home_Score IS NOT NULL"
        cursor.execute(query)
        games = cursor.fetchall()
        conn.close()

        if not games:
            raise ValueError("No historical game data with scores found.")

        profit = 0
        wins = 0
        total_bets = 0
        chart_data = [{'game': 0, 'profit': 0}]

        for i, (home_team, away_team, home_score, away_score, home_line) in enumerate(games):
            if home_line is None:
                continue
            favorite = home_team if home_line < 0 else away_team
            underdog = away_team if home_line < 0 else home_team

            bet_on = None
            if strategy == 'Favorites':
                bet_on = favorite
            elif strategy == 'Underdogs':
                bet_on = underdog
            elif strategy == 'Home Teams':
                bet_on = home_team

            if bet_on is None:
                continue

            # Determine which side covered
            # Home covers if home_score + spread > away_score
            if home_score is None or away_score is None:
                continue
            home_covers = (home_score + home_line) > away_score
            if (home_score + home_line) == away_score:  # push
                continue

            total_bets += 1
            won = (bet_on == home_team and home_covers) or (bet_on == away_team and not home_covers)

            if won:
                wins += 1
                profit += 91  # assuming -110 odds payout net +91 on 100 stake
            else:
                profit -= 100

            chart_data.append({'game': i + 1, 'profit': profit})

        if total_bets == 0:
            return {'metrics': {'roi': '0.0%', 'win_rate': '0.0%', 'profit_loss': '$0'}, 'chart_data': []}

        roi = (profit / (total_bets * 100)) * 100
        win_rate = (wins / total_bets) * 100

        return {
            'metrics': {
                'roi': f"{roi:.1f}%",
                'win_rate': f"{win_rate:.1f}%",
                'profit_loss': f"${profit}",
            },
            'chart_data': chart_data,
        }
    except Exception:
        # On failure return neutral metrics (remove placeholder profitable series)
        return {
            'metrics': {'roi': '0.0%', 'win_rate': '0.0%', 'profit_loss': '$0'},
            'chart_data': []
        }

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
            if home_score is None or away_score is None or home_line is None:
                continue
            # Determine cover: home covers if home_score + home_line > away_score
            if (home_score + home_line) == away_score:  # push
                continue
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
                {'Week': r[0], 'Matchup': f"{r[2]} @ {r[1]}", 'Score': f"{r[4]}-{r[3]}"}
                for r in recent_results
            ],
            'upcoming_schedule': [
                {'Week': r[0], 'Matchup': f"{r[2]} @ {r[1]}"}
                for r in upcoming_schedule
            ],
            'ats_record': f"{ats_wins}-{ats_losses}"
        }
    except Exception:
        return {
            'grades': {},
            'recent_results': [],
            'upcoming_schedule': [],
            'ats_record': '0-0'
        }

def get_win_rate_trend():
    """Return weekly win rates (percentage) based on picks_results or fallback join."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Primary: picks_results (trim week values)
        cursor.execute("""
            SELECT TRIM(WEEK) as WK,
                   SUM(CASE WHEN Pick_Covered_Spread IS NOT NULL THEN 1 ELSE 0 END) AS total_picks,
                   SUM(CASE WHEN Pick_Covered_Spread = 1 THEN 1 ELSE 0 END) AS wins
            FROM picks_results
            GROUP BY TRIM(WEEK)
            HAVING total_picks > 0
            ORDER BY CAST(REPLACE(UPPER(WK),'WEEK','') AS INTEGER)
        """)
        rows = cursor.fetchall()
        if not rows:
            cursor.execute("""
                SELECT TRIM(p.WEEK) as WK,
                       SUM(CASE WHEN s.Home_Score IS NOT NULL AND s.Away_Score IS NOT NULL AND s.Home_Line_Close IS NOT NULL THEN 1 ELSE 0 END) AS total_games,
                       SUM(CASE WHEN s.Home_Score IS NOT NULL AND s.Away_Score IS NOT NULL AND s.Home_Line_Close IS NOT NULL AND 
                                (
                                   (p.Game_Pick = p.Home_Team AND (s.Home_Score + s.Home_Line_Close) > s.Away_Score AND (s.Home_Score + s.Home_Line_Close) != s.Away_Score) OR
                                   (p.Game_Pick = p.Away_Team AND NOT ((s.Home_Score + s.Home_Line_Close) > s.Away_Score) AND (s.Home_Score + s.Home_Line_Close) != s.Away_Score)
                                )
                           THEN 1 ELSE 0 END) AS wins
                FROM picks p
                JOIN spreads s ON TRIM(p.WEEK) = TRIM(s.WEEK) AND p.Home_Team = s.Home_Team AND p.Away_Team = s.Away_Team
                GROUP BY TRIM(p.WEEK)
                HAVING total_games > 0
                ORDER BY CAST(REPLACE(UPPER(WK),'WEEK','') AS INTEGER)
            """)
            rows = cursor.fetchall()
        conn.close()
        if not rows:
            return {'weeks': [], 'win_rates': []}
        weeks = []
        win_rates = []
        for week, total_picks, wins in rows:
            if total_picks and total_picks > 0:
                weeks.append(week)
                pct = round((wins / total_picks) * 100, 1)
                win_rates.append(pct)
        return {'weeks': weeks, 'win_rates': win_rates}
    except Exception:
        return {'weeks': [], 'win_rates': []}

def get_weekly_win_rate_rows():
    """Return list of dicts: Week, Total_Picks, Wins, Losses, Win_Rate (str).
    Week is zero-padded (WEEK01) for proper lexical sorting in UI."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Primary: picks_results with Pick_Covered_Spread
        cursor.execute("""
            SELECT TRIM(WEEK) as WK,
                   SUM(CASE WHEN Pick_Covered_Spread IS NOT NULL THEN 1 ELSE 0 END) AS total_picks,
                   SUM(CASE WHEN Pick_Covered_Spread = 1 THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN Pick_Covered_Spread = 0 THEN 1 ELSE 0 END) AS losses
            FROM picks_results
            GROUP BY TRIM(WEEK)
            HAVING total_picks > 0
            ORDER BY CAST(REPLACE(UPPER(WK),'WEEK','') AS INTEGER)
        """)
        rows = cursor.fetchall()
        if not rows:
            # Fallback join (derive wins)
            cursor.execute("""
                SELECT TRIM(p.WEEK) as WK,
                       SUM(CASE WHEN s.Home_Score IS NOT NULL AND s.Away_Score IS NOT NULL AND s.Home_Line_Close IS NOT NULL THEN 1 ELSE 0 END) AS total_picks,
                       SUM(CASE WHEN s.Home_Score IS NOT NULL AND s.Away_Score IS NOT NULL AND s.Home_Line_Close IS NOT NULL AND 
                                ( (p.Game_Pick = p.Home_Team AND (s.Home_Score + s.Home_Line_Close) > s.Away_Score AND (s.Home_Score + s.Home_Line_Close) != s.Away_Score)
                                  OR
                                  (p.Game_Pick = p.Away_Team AND NOT ((s.Home_Score + s.Home_Line_Close) > s.Away_Score) AND (s.Home_Score + s.Home_Line_Close) != s.Away_Score) )
                           THEN 1 ELSE 0 END) AS wins
                FROM picks p
                JOIN spreads s ON TRIM(p.WEEK)=TRIM(s.WEEK) AND p.Home_Team=s.Home_Team AND p.Away_Team=s.Away_Team
                GROUP BY TRIM(p.WEEK)
                HAVING total_picks > 0
                ORDER BY CAST(REPLACE(UPPER(WK),'WEEK','') AS INTEGER)
            """)
            derived = cursor.fetchall()
            conn.close()
            data = []
            for wk, total_picks, wins in derived:
                number_part = wk.upper().replace('WEEK','')
                try:
                    num = int(number_part)
                except ValueError:
                    num = 0
                padded_week = f"WEEK{num:02d}" if num else wk
                losses = total_picks - wins if total_picks is not None else 0
                rate = f"{(wins/total_picks)*100:.1f}%" if total_picks else '0.0%'
                data.append({'Week': padded_week, 'Total_Picks': total_picks, 'Wins': wins, 'Losses': losses, 'Win_Rate': rate})
            return data
        conn.close()
        data = []
        for wk, total_picks, wins, losses in rows:
            number_part = wk.upper().replace('WEEK','')
            try:
                num = int(number_part)
            except ValueError:
                num = 0
            padded_week = f"WEEK{num:02d}" if num else wk
            rate = f"{(wins/total_picks)*100:.1f}%" if total_picks else '0.0%'
            data.append({'Week': padded_week, 'Total_Picks': total_picks, 'Wins': wins, 'Losses': losses, 'Win_Rate': rate})
        return data
    except Exception:
        return []

@ui.page('/')  # normal index page (e.g. the entry point of the app)
@ui.page('/{_:path}')  # all other pages will be handled by the router but must be registered to also show the SPA index page
def main():
    # Set up the page
    ui.add_head_html('''
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Roboto', sans-serif; 
            background-color: #f5f5f5;
            margin: 0;
            padding: 0;
        }
        .text-red { color: #f44336; }
        .text-green { color: #4caf50; }
        .shadow-lg {
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
        }
    </style>
    ''')

    # Initialize the router
    router = Router()

    # Set the colors for the UI
    ui.colors(primary=COLORS['primary'], secondary=COLORS['secondary'], accent=COLORS['accent'])

    # Header area
    with ui.header().classes('bg-primary text-white'):
        with ui.row().classes('w-full items-center justify-between q-px-lg'):
            ui.label('Panda Picks').classes('text-h4')

            with ui.row().classes('items-center'):
                ui.icon('sports_football').classes('text-h4')
                ui.button('NFL 2025').props('flat')

            dark_mode = ui.dark_mode()
            ui.button(on_click=lambda: dark_mode.toggle(), icon='dark_mode').props('flat')

    @router.add('/')
    def landing():
        ui.label('Welcome to Panda Picks').classes('text-h3 q-mb-md')
        ui.label('Your one-stop solution for NFL data analysis and predictions.').classes('text-subtitle1 q-mb-lg')

        with ui.card().classes('w-full q-pa-lg shadow-lg'):
            ui.label('About Panda Picks').classes('text-h5 q-mb-md')
            ui.markdown('''
                Panda Picks is a Python-based project designed to analyze NFL data, generate predictions, and store results in a structured database. The project integrates data processing, database management, and analysis to provide insights into NFL matchups, team performance, and betting strategies.
            ''').classes('text-body1')

        with ui.card().classes('w-full q-mt-lg q-pa-lg shadow-lg'):
            ui.label('Key Features').classes('text-h5 q-mb-md')
            with ui.list().props('bordered separator'):
                with ui.item():
                    with ui.item_section():
                        ui.item_label('Data-driven Predictions').props('overline')
                        ui.item_label('Leverages historical data and team grades for informed picks.')
                with ui.item():
                    with ui.item_section():
                        ui.item_label('Comprehensive Analysis').props('overline')
                        ui.item_label('In-depth analysis of win rates, home/away performance, and trends.')
                with ui.item():
                    with ui.item_section():
                        ui.item_label('Centralized Database').props('overline')
                        ui.item_label('All data stored in a structured SQLite database for easy access.')
                with ui.item():
                    with ui.item_section():
                        ui.item_label('User-Friendly Interface').props('overline')
                        ui.item_label('A clean and interactive UI to view stats and analysis.')

        with ui.card().classes('w-full q-mt-lg q-pa-lg shadow-lg'):
            ui.label('Workflow').classes('text-h5 q-mb-md')
            ui.markdown('''
                1.  **Data Ingestion**: Raw data is processed and stored.
                2.  **Database Management**: Data is organized in an SQLite database.
                3.  **Analysis**: Scripts analyze data to generate insights and picks.
                4.  **Presentation**: Results are displayed in the dashboard and analysis pages.
            ''').classes('text-body1')

    @router.add('/dashboard')
    def dashboard():
        ui.label('Dashboard').classes('text-h4 q-mb-lg')

        # Stats Cards
        with ui.row().classes('w-full justify-center q-col-gutter-md'):
            with ui.card().style(f'background: linear-gradient(135deg, {COLORS["card1"]}, #42A312); color: white').classes('q-pa-md shadow-lg'):
                with ui.column().classes('items-center'):
                    ui.icon('analytics').classes('text-h2 q-mb-md')
                    ui.label('Overall Win Rate').classes('text-h6')
                    ui.label(calculate_win_rates()['overall']).classes('text-h3')

            with ui.card().style(f'background: linear-gradient(135deg, {COLORS["card2"]}, #e64a19); color: white').classes('q-pa-md shadow-lg'):
                with ui.column().classes('items-center'):
                    ui.icon('sports').classes('text-h2 q-mb-md')
                    ui.label('Total Picks').classes('text-h6')
                    ui.label(str(get_total_picks())).classes('text-h3')

            with ui.card().style(f'background: linear-gradient(135deg, {COLORS["card3"]}, #3949ab); color: white').classes('q-pa-md shadow-lg'):
                with ui.column().classes('items-center'):
                    ui.icon('event').classes('text-h2 q-mb-md')
                    ui.label('Upcoming Games').classes('text-h6')
                    ui.label(str(get_upcoming_games())).classes('text-h3')

        # Recent picks table
        with ui.card().classes('w-full q-mt-lg shadow-lg'):
            ui.label('Recent Picks').classes('text-h6 q-pa-md')

            rows = get_recent_picks()

            # Create table with rows - modify the 'classes' field to use a string instead of a lambda
            columns = [
                {'name': 'Week', 'label': 'Week', 'field': 'Week'},
                {'name': 'Home', 'label': 'Home Team', 'field': 'Home'},
                {'name': 'Away', 'label': 'Away Team', 'field': 'Away'},
                {'name': 'Pick', 'label': 'Pick', 'field': 'Pick'},
                {'name': 'Result', 'label': 'Result', 'field': 'Result'}
            ]

            # Process the rows to add the class directly
            for row in rows:
                if row['Result'] == 'WIN':
                    row['Result'] = f'<span class="text-green text-weight-bold">{row["Result"]}</span>'
                elif row['Result'] == 'LOSS':
                    row['Result'] = f'<span class="text-red text-weight-bold">{row["Result"]}</span>'

            ui.table(columns=columns, rows=rows, row_key='Week').props('dense bordered').classes('w-full')

    @router.add('/analysis')
    def analysis():
        ui.label('Analysis').classes('text-h4 q-mb-lg')

        # Win Rate Stats
        win_rates = calculate_win_rates()

        # Home vs Away Stats
        with ui.card().classes('shadow-lg w-full'):
            ui.label('Home vs Away Win Rate').classes('text-h6 q-pa-md')

            with ui.row().classes('q-pa-md w-full justify-around'):
                with ui.column().classes('items-center'):
                    ui.icon('home').classes('text-h3 text-primary')
                    ui.label('Home Team Picks').classes('text-subtitle1')
                    ui.label(win_rates['home']).classes('text-h5 text-weight-bold')

                ui.separator().props('vertical')

                with ui.column().classes('items-center'):
                    ui.icon('flight_takeoff').classes('text-h3 text-secondary')
                    ui.label('Away Team Picks').classes('text-subtitle1')
                    ui.label(win_rates['away']).classes('text-h5 text-weight-bold')

        # Weekly win rate table
        with ui.card().classes('w-full q-mt-lg shadow-lg'):
            ui.label('Weekly Win Rates').classes('text-h6 q-pa-md')
            rows = get_weekly_win_rate_rows()
            if rows:
                columns = [
                    {'name': 'Week', 'label': 'Week', 'field': 'Week', 'sortable': True},
                    {'name': 'Total_Picks', 'label': 'Total Picks', 'field': 'Total_Picks', 'sortable': True},
                    {'name': 'Wins', 'label': 'Wins', 'field': 'Wins', 'sortable': True},
                    {'name': 'Losses', 'label': 'Losses', 'field': 'Losses', 'sortable': True},
                    {'name': 'Win_Rate', 'label': 'Win Rate', 'field': 'Win_Rate', 'sortable': True},
                ]
                table = ui.table(columns=columns, rows=rows, row_key='Week').props('dense bordered').classes('w-full')
                table.add_slot('top-right', r'''
                    <q-input borderless dense debounce="300" v-model="props.filter" placeholder="Search Week">
                      <template v-slot:append><q-icon name="search" /></template>
                    </q-input>
                ''')
            else:
                ui.label('No weekly win rate data available.').classes('q-pa-md')

    @router.add('/picks')
    def picks():
        ui.label('Upcoming Picks').classes('text-h4 q-mb-lg')
        with ui.row().classes('w-full items-center q-mb-md'):
            ui.button('Export to CSV', icon='download', on_click=lambda: ui.notify('Exporting... (placeholder)')).classes('q-mr-md')
            ui.switch('Show Past Picks')

        with ui.card().classes('w-full shadow-lg'):
            picks_data = get_upcoming_picks()
            if picks_data:
                columns = [
                    {'name': 'Week', 'label': 'Week', 'field': 'Week', 'sortable': True},
                    {'name': 'Home_Team', 'label': 'Home Team', 'field': 'Home_Team', 'sortable': True},
                    {'name': 'Away_Team', 'label': 'Away Team', 'field': 'Away_Team', 'sortable': True},
                    {'name': 'Predicted_Pick', 'label': 'Predicted Pick', 'field': 'Predicted_Pick', 'sortable': True},
                    {'name': 'Confidence_Score', 'label': 'Confidence Score', 'field': 'Confidence_Score', 'sortable': True},
                ]
                ui.table(columns=columns, rows=picks_data, row_key='Week').classes('w-full')
            else:
                ui.label('No upcoming picks found.').classes('q-pa-md')

    @router.add('/grades')
    def grades():
        ui.label('Team Grades').classes('text-h4 q-mb-lg')

        def handle_upload(e):
            ui.notify(f'Uploaded {e.name} (placeholder)')

        with ui.card().classes('w-full shadow-lg q-pa-md'):
            ui.label('Update Grades').classes('text-h6')
            ui.upload(on_upload=handle_upload, label='Upload new grades (CSV/PDF)').classes('w-full q-mb-md')

            grades_data = get_team_grades()
            if grades_data:
                columns = [
                    {'name': 'Team', 'label': 'Team', 'field': 'Team', 'sortable': True, 'align': 'left'},
                    {'name': 'Overall_Grade', 'label': 'Overall', 'field': 'Overall_Grade', 'sortable': True},
                    {'name': 'Offense_Grade', 'label': 'Offense', 'field': 'Offense_Grade', 'sortable': True},
                    {'name': 'Defense_Grade', 'label': 'Defense', 'field': 'Defense_Grade', 'sortable': True},
                ]
                table = ui.table(columns=columns, rows=grades_data, row_key='Team').classes('w-full')
                table.add_slot('top-right', r'''
                    <q-input borderless dense debounce="300" v-model="props.filter" placeholder="Search">
                    <template v-slot:append>
                        <q-icon name="search" />
                    </template>
                    </q-input>
                ''')
            else:
                ui.label('No team grades found.').classes('q-pa-md')

    @router.add('/spreads')
    def spreads():
        ui.label('Spreads Analysis').classes('text-h4 q-mb-lg')

        with ui.card().classes('w-full q-mt-lg shadow-lg'):
            ui.label('Spreads Chart').classes('text-h6 q-pa-md')
            ui.html('<div style="width: 100%; height: 200px; display: flex; align-items: center; justify-content: center; color: #9e9e9e;">Interactive chart of spreads would appear here.</div>').classes('w-full')

        with ui.card().classes('w-full q-mt-lg shadow-lg'):
            ui.label('Raw Spread Data').classes('text-h6 q-pa-md')
            spreads_data = get_spreads_data()
            if spreads_data:
                columns = [
                    {'name': 'Week', 'label': 'Week', 'field': 'Week', 'sortable': True},
                    {'name': 'Home_Team', 'label': 'Home Team', 'field': 'Home_Team', 'sortable': True},
                    {'name': 'Away_Team', 'label': 'Away Team', 'field': 'Away_Team', 'sortable': True},
                    {'name': 'Line', 'label': 'Home Line Close', 'field': 'Line', 'sortable': True},
                ]
                ui.table(columns=columns, rows=spreads_data, row_key='Week').classes('w-full')
            else:
                ui.label('No spread data found.').classes('q-pa-md')

    @router.add('/settings')
    def settings():
        ui.label('Settings').classes('text-h4 q-mb-lg')

        with ui.card().classes('w-full shadow-lg q-mb-lg'):
            ui.label('Database Management').classes('text-h6 q-pa-md')
            with ui.row().classes('q-pa-md'):
                ui.button('Reset Database', color='negative', on_click=lambda: ui.notify('Database reset! (placeholder)', type='warning')).classes('q-mr-md')
                ui.button('Backup Database', on_click=lambda: ui.notify('Database backed up! (placeholder)', type='positive'))

        with ui.card().classes('w-full shadow-lg q-mb-lg'):
            ui.label('Data Management').classes('text-h6 q-pa-md')
            with ui.column().classes('q-pa-md'):
                ui.upload(label='Import Data', on_upload=lambda e: ui.notify(f'Importing {e.name}... (placeholder)')).classes('w-full')
                ui.button('Export All Data', on_click=lambda: ui.notify('Exporting data... (placeholder)')).classes('q-mt-md')

        with ui.card().classes('w-full shadow-lg'):
            ui.label('User Authentication').classes('text-h6 q-pa-md')
            with ui.column().classes('q-pa-md'):
                ui.label('Authentication settings would go here.').classes('text-grey')

    @router.add('/backtest')
    def backtest_page():
        ui.label('Backtest Betting Strategies').classes('text-h4 q-mb-lg')

        results_card = ui.card().classes('w-full shadow-lg q-mb-lg')
        chart_card = ui.card().classes('w-full shadow-lg')

        def update_backtest_results(strategy: str):
            data = run_backtest(strategy)
            results_card.clear()
            with results_card:
                ui.label('Backtest Results').classes('text-h6 q-pa-md')
                with ui.row().classes('q-pa-md w-full justify-around'):
                    for metric, value in data['metrics'].items():
                        with ui.column().classes('items-center'):
                            ui.label(metric.replace("_", " ").title()).classes('text-subtitle1')
                            ui.label(value).classes('text-h5 text-weight-bold')

            chart_card.clear()
            with chart_card:
                ui.label('Profit Over Time').classes('text-h6 q-pa-md')
                if data['chart_data']:
                    # Create profit chart with matplotlib
                    with ui.matplotlib(figsize=(8, 4)).classes('w-full') as profit_chart:
                        fig = profit_chart.figure
                        ax = fig.add_subplot(111)

                        # Extract game numbers and profit values
                        games = [d['game'] for d in data['chart_data']]
                        profits = [d['profit'] for d in data['chart_data']]

                        # Plot profit line
                        ax.plot(games, profits, marker='o', linewidth=2, color=COLORS['primary'])

                        # Add a horizontal line at zero
                        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.7)

                        # Labels and title
                        ax.set_xlabel('Game Number')
                        ax.set_ylabel('Profit ($)')
                        ax.set_title('Profit Over Time')

                        # Add grid
                        ax.grid(True, linestyle='--', alpha=0.7)

                        # Ensure layout looks good
                        fig.tight_layout()
                else:
                    ui.html('<div style="width: 100%; height: 200px; display: flex; align-items: center; justify-content: center; color: #9e9e9e;">No data for chart.</div>').classes('w-full')

        with ui.card().classes('w-full shadow-lg q-mb-lg'):
            with ui.row().classes('w-full items-center q-pa-md'):
                strategy_select = ui.select(['Favorites', 'Underdogs', 'Home Teams'], value='Favorites', label='Select Strategy')
                ui.button('Run Backtest', on_click=lambda: update_backtest_results(strategy_select.value))

    @router.add('/team-details')
    def team_details_page():
        ui.label('Team Details').classes('text-h4 q-mb-lg')

        details_container = ui.column().classes('w-full gap-4')

        def update_team_details(team_name: str):
            details = get_team_details(team_name)
            details_container.clear()
            with details_container:
                with ui.card().classes('w-full shadow-lg'):
                    ui.label('Team Grades & Record').classes('text-h6 q-pa-md')
                    with ui.row().classes('q-pa-md w-full justify-around'):
                        for grade, value in details['grades'].items():
                            with ui.column().classes('items-center'):
                                ui.label(grade).classes('text-subtitle1')
                                ui.label(value).classes('text-h5 text-weight-bold')
                        with ui.column().classes('items-center'):
                            ui.label('ATS Record').classes('text-subtitle1')
                            ui.label(details['ats_record']).classes('text-h5 text-weight-bold')

                with ui.row().classes('w-full gap-4'):
                    with ui.card().classes('w-1/2 shadow-lg'):
                        ui.label('Recent Results').classes('text-h6 q-pa-md')
                        ui.table(columns=[{'name': 'Matchup', 'label': 'Matchup', 'field': 'Matchup'}, {'name': 'Score', 'label': 'Score', 'field': 'Score'}], rows=details['recent_results'], row_key='Matchup').classes('w-full')

                    with ui.card().classes('w-1/2 shadow-lg'):
                        ui.label('Upcoming Schedule').classes('text-h6 q-pa-md')
                        ui.table(columns=[{'name': 'Matchup', 'label': 'Matchup', 'field': 'Matchup'}], rows=details['upcoming_schedule'], row_key='Matchup').classes('w-full')

        team_list = get_all_team_names()
        if team_list:
            ui.select(team_list, label='Select a Team', on_change=lambda e: update_team_details(e.value)).classes('w-1/3 q-mb-md')
            update_team_details(team_list[0])
        else:
            ui.label('No teams found.')

    # Navigation buttons
    with ui.row().classes('q-pa-md w-full bg-white shadow-sm'):
        ui.button('Home', on_click=lambda: router.open(landing), icon='home').classes('q-mr-sm')
        ui.button('Dashboard', on_click=lambda: router.open(dashboard), icon='dashboard').classes('q-mr-sm')
        ui.button('Analysis', on_click=lambda: router.open(analysis), icon='bar_chart').classes('q-mr-sm')
        ui.button('Picks', on_click=lambda: router.open(picks), icon='style').classes('q-mr-sm')
        ui.button('Grades', on_click=lambda: router.open(grades), icon='grade').classes('q-mr-sm')
        ui.button('Spreads', on_click=lambda: router.open(spreads), icon='timeline').classes('q-mr-sm')
        ui.button('Backtest', on_click=lambda: router.open(backtest_page), icon='science').classes('q-mr-sm')
        ui.button('Teams', on_click=lambda: router.open(team_details_page), icon='groups').classes('q-mr-sm')
        ui.button('Settings', on_click=lambda: router.open(settings), icon='settings')

    # Router frame - this is where the content will be displayed
    router.frame().classes('w-full p-4')


ui.run(port=8001)
