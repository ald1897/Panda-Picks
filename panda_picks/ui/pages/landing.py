from nicegui import ui

def register(router):
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
                for title, desc in [
                    ('Data-driven Predictions', 'Leverages historical data and team grades for informed picks.'),
                    ('Comprehensive Analysis', 'In-depth analysis of win rates, home/away performance, and trends.'),
                    ('Centralized Database', 'All data stored in a structured SQLite database for easy access.'),
                    ('User-Friendly Interface', 'A clean and interactive UI to view stats and analysis.'),
                ]:
                    with ui.item():
                        with ui.item_section():
                            ui.item_label(title).props('overline')
                            ui.item_label(desc)
        with ui.card().classes('w-full q-mt-lg q-pa-lg shadow-lg'):
            ui.label('Workflow').classes('text-h5 q-mb-md')
            ui.markdown('''
                1. **Data Ingestion**: Raw data is processed and stored.\n
                2. **Database Management**: Data is organized in an SQLite database.\n
                3. **Analysis**: Scripts analyze data to generate insights and picks.\n
                4. **Presentation**: Results are displayed in the dashboard and analysis pages.
            ''').classes('text-body1')
    return landing
