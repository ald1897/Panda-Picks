#!/usr/bin/env python3
from router import Router
from nicegui import ui
from panda_picks.db.database import get_connection

# Colors for consistency
COLORS = {
    'primary': '#3f51b5',    # Deep blue
    'secondary': '#ff9800',  # Orange
    'accent': '#4caf50',     # Green
    'card1': '#5c6bc0',      # Light blue-purple
    'card2': '#ff7043',      # Deep orange
    'card3': '#66bb6a',      # Medium green
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
    except:
        return 128  # Fallback value

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
        return "62.5%"  # Fallback value
    except:
        return "62.5%"  # Fallback value

def get_upcoming_games():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM spreads WHERE Home_Score IS NULL")
        result = cursor.fetchone()[0]
        conn.close()
        return result
    except:
        return 5  # Fallback value

def get_recent_picks():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
        SELECT WEEK, Home_Team, Away_Team, Game_Pick, 
        CASE WHEN Pick_Covered_Spread = 1 THEN 'WIN' WHEN Pick_Covered_Spread = 0 THEN 'LOSS' ELSE 'PENDING' END as Result
        FROM picks_results 
        ORDER BY WEEK DESC LIMIT 5
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
            return [
                {'Week': 'WEEK1', 'Home': 'KC', 'Away': 'BAL', 'Pick': 'KC', 'Result': 'WIN'},
                {'Week': 'WEEK1', 'Home': 'SF', 'Away': 'LA', 'Pick': 'SF', 'Result': 'LOSS'},
                {'Week': 'WEEK1', 'Home': 'MIA', 'Away': 'NE', 'Pick': 'MIA', 'Result': 'WIN'}
            ]
    except:
        return [
            {'Week': 'WEEK1', 'Home': 'KC', 'Away': 'BAL', 'Pick': 'KC', 'Result': 'WIN'},
            {'Week': 'WEEK1', 'Home': 'SF', 'Away': 'LA', 'Pick': 'SF', 'Result': 'LOSS'},
            {'Week': 'WEEK1', 'Home': 'MIA', 'Away': 'NE', 'Pick': 'MIA', 'Result': 'WIN'}
        ]

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
    except:
        # Return placeholder win rates if database query fails
        return {
            'overall': '62.5%',
            'home': '67.8%',
            'away': '55.2%'
        }

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

    @router.add('/dashboard')
    def dashboard():
        ui.label('Dashboard').classes('text-h4 q-mb-lg')

        # Stats Cards
        with ui.row().classes('w-full justify-center q-col-gutter-md'):
            with ui.card().style(f'background: linear-gradient(135deg, {COLORS["card1"]}, #3949ab); color: white').classes('q-pa-md shadow-lg'):
                with ui.column().classes('items-center'):
                    ui.icon('analytics').classes('text-h2 q-mb-md')
                    ui.label('Overall Win Rate').classes('text-h6')
                    ui.label(calculate_win_rates()['overall']).classes('text-h3')

            with ui.card().style(f'background: linear-gradient(135deg, {COLORS["card2"]}, #e64a19); color: white').classes('q-pa-md shadow-lg'):
                with ui.column().classes('items-center'):
                    ui.icon('sports').classes('text-h2 q-mb-md')
                    ui.label('Total Picks').classes('text-h6')
                    ui.label(str(get_total_picks())).classes('text-h3')

            with ui.card().style(f'background: linear-gradient(135deg, {COLORS["card3"]}, #388e3c); color: white').classes('q-pa-md shadow-lg'):
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

        # Placeholder chart
        with ui.card().classes('w-full q-mt-lg shadow-lg'):
            ui.label('Win Rate Trend').classes('text-h6 q-pa-md')
            with ui.row().classes('q-pa-md w-full'):
                ui.html('''
                <div style="width: 100%; height: 300px; display: flex; align-items: center; justify-content: center; color: #9e9e9e;">
                    <div style="text-align: center;">
                        <div style="font-size: 48px; margin-bottom: 10px;">📈</div>
                        <div>Trend chart would appear here with actual data</div>
                    </div>
                </div>
                ''')

    # Navigation buttons
    with ui.row().classes('q-pa-md w-full bg-white shadow-sm'):
        ui.button('Dashboard', on_click=lambda: router.open(dashboard), icon='dashboard').classes('q-mr-sm')
        ui.button('Analysis', on_click=lambda: router.open(analysis), icon='bar_chart')

    # Router frame - this is where the content will be displayed
    router.frame().classes('w-full p-4')


ui.run(port=8001)
