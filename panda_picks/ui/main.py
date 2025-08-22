#!/usr/bin/env python3
import sys, pathlib, os
# Detect script execution (no package context) and fix sys.path so absolute imports work
if __package__ is None or __package__ == '':
    current_dir = pathlib.Path(__file__).resolve().parent  # .../panda_picks/ui
    pkg_dir = current_dir.parent  # .../panda_picks
    root_dir = pkg_dir.parent     # project root
    root_str = str(root_dir)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    # After path fix, use absolute imports
    from panda_picks.ui.router import Router  # type: ignore
    from panda_picks.ui.data import COLORS  # type: ignore
    from panda_picks.ui.pages import landing as landing_page  # type: ignore
    from panda_picks.ui.pages import dashboard as dashboard_page  # type: ignore
    from panda_picks.ui.pages import analysis as analysis_page  # type: ignore
    from panda_picks.ui.pages import picks as picks_page  # type: ignore
    from panda_picks.ui.pages import grades as grades_page  # type: ignore
    from panda_picks.ui.pages import spreads as spreads_page  # type: ignore
    from panda_picks.ui.pages import settings as settings_page  # type: ignore
    from panda_picks.ui.pages import backtest as backtest_page  # type: ignore
    from panda_picks.ui.pages import team_details as team_details_page  # type: ignore
    from panda_picks.ui.pages import combos as combos_page  # type: ignore
else:
    from .router import Router
    from nicegui import ui
    from .data import COLORS
    from .pages import landing as landing_page
    from .pages import dashboard as dashboard_page
    from .pages import analysis as analysis_page
    from .pages import picks as picks_page
    from .pages import grades as grades_page
    from .pages import spreads as spreads_page
    from .pages import settings as settings_page
    from .pages import backtest as backtest_page
    from .pages import team_details as team_details_page
    from .pages import combos as combos_page

# When running as script, nicegui still needed (import after path setup)
if 'ui' not in globals():
    from nicegui import ui

@ui.page('/')  # SPA entry
@ui.page('/{_:path}')
def main():
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
        .shadow-lg { box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05); }
    </style>
    ''')
    router = Router()
    ui.colors(primary=COLORS['primary'], secondary=COLORS['secondary'], accent=COLORS['accent'])
    # Header
    with ui.header().classes('bg-primary text-white'):
        with ui.row().classes('w-full items-center justify-between q-px-lg'):
            ui.label('Panda Picks').classes('text-h4')
            with ui.row().classes('items-center'):
                ui.icon('sports_football').classes('text-h4')
                ui.button('NFL 2025').props('flat')
            dark_mode = ui.dark_mode()
            ui.button(on_click=lambda: dark_mode.toggle(), icon='dark_mode').props('flat')

    # Register routes from modules (capture functions for navigation)
    landing = landing_page.register(router)
    dashboard = dashboard_page.register(router)
    analysis = analysis_page.register(router)
    picks = picks_page.register(router)
    grades = grades_page.register(router)
    spreads = spreads_page.register(router)
    settings = settings_page.register(router)
    backtest = backtest_page.register(router)
    team_details = team_details_page.register(router)
    combos = combos_page.register(router)

    # Navigation bar
    with ui.row().classes('q-pa-md w-full bg-white shadow-sm'):
        ui.button('Home', on_click=lambda: router.open(landing), icon='home').classes('q-mr-sm')
        ui.button('Dashboard', on_click=lambda: router.open(dashboard), icon='dashboard').classes('q-mr-sm')
        ui.button('Analysis', on_click=lambda: router.open(analysis), icon='bar_chart').classes('q-mr-sm')
        ui.button('Picks', on_click=lambda: router.open(picks), icon='style').classes('q-mr-sm')
        ui.button('Grades', on_click=lambda: router.open(grades), icon='grade').classes('q-mr-sm')
        ui.button('Spreads', on_click=lambda: router.open(spreads), icon='timeline').classes('q-mr-sm')
        ui.button('Backtest', on_click=lambda: router.open(backtest), icon='science').classes('q-mr-sm')
        ui.button('Teams', on_click=lambda: router.open(team_details), icon='groups').classes('q-mr-sm')
        ui.button('Combos', on_click=lambda: router.open(combos), icon='functions').classes('q-mr-sm')
        ui.button('Settings', on_click=lambda: router.open(settings), icon='settings')

    # Content frame
    router.frame().classes('w-full p-4')

if __name__ in {'__main__','__mp_main__'}:
    if os.getenv('PANDA_PICKS_NO_UI') == '1':
        print('Panda Picks UI loaded (server not started due to PANDA_PICKS_NO_UI=1).')
    else:
        ui.run(port=8001)
