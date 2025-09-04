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
    from panda_picks.ui.pages import settings as settings_page  # type: ignore
    from panda_picks.ui.pages import combos as combos_page  # type: ignore
else:
    from .router import Router
    from nicegui import ui
    from .data import COLORS
    from .pages import landing as landing_page
    from .pages import dashboard as dashboard_page
    from .pages import analysis as analysis_page
    from .pages import picks as picks_page
    from .pages import settings as settings_page
    from .pages import combos as combos_page

# When running as script, nicegui still needed (import after path setup)
if 'ui' not in globals():
    from nicegui import ui

# Add static files route for docs (banner image expected at docs/banner.png)
try:
    from nicegui import app as _app
    _root = pathlib.Path(__file__).resolve().parent.parent.parent  # project root
    _docs = _root / 'docs'
    if _docs.exists():
        _app.add_static_files('/assets', str(_docs))
except Exception:
    pass

@ui.page('/')  # SPA entry
@ui.page('/{_:path}')
def main():
    ui.add_head_html('''
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Roboto', sans-serif; 
            background-color: #0B1424; /* deep navy */
            margin: 0; padding: 0; color: #FFFFFF;
        }
        .text-red { color: #ff6a1a; }
        .text-green { color: #48B553; }
        .shadow-lg { box-shadow: 0 10px 20px -5px rgba(0,0,0,0.55), 0 6px 8px -4px rgba(0,0,0,0.35); }
        .hero-banner { background: linear-gradient(90deg, rgba(11,20,36,0.9) 0%, rgba(11,20,36,0.55) 35%, rgba(11,20,36,0.25) 70%), url('/assets/banner.png') center/cover no-repeat; height: 220px; width:100%; position: relative; display:flex; flex-direction:column; justify-content:flex-end; }
        .hero-inner { padding: 18px 48px; }
        .brand-title { font-size: 48px; font-weight: 600; letter-spacing: 1px; margin:0; color:#FFFFFF; text-shadow:0 3px 10px rgba(0,0,0,0.6); }
        .brand-sub { font-size: 16px; font-weight:400; margin-top:6px; color:#FF6A1A; letter-spacing:0.5px; }
        .nav-bar { backdrop-filter: blur(6px); background: rgba(20,33,50,0.85); }
        .q-btn.flat-btn { --q-primary: #FF6A1A; }
    </style>
    ''')
    from panda_picks.ui.data import COLORS  # ensure updated palette
    router = Router()
    ui.colors(primary=COLORS['primary'], secondary=COLORS['secondary'], accent=COLORS['accent'])
    # Compact top header (controls only)
    with ui.header().classes('bg-transparent text-white shadow-none'):  # minimal header
        with ui.row().classes('w-full items-center justify-end q-px-md'):
            dark_mode = ui.dark_mode()
            ui.button(on_click=lambda: dark_mode.toggle(), icon='dark_mode').props('flat dense').classes('text-white')
    # Hero banner
    with ui.element('div').classes('hero-banner'):
        with ui.element('div').classes('hero-inner'):
            ui.html('<h1 class="brand-title">Panda Picks</h1>')
            ui.html('<div class="brand-sub">Model-Driven Football Edges & Teaser Optimization</div>')
    # Navigation bar (overlay style)
    with ui.row().classes('q-px-lg q-py-sm w-full nav-bar items-center'):
        ui.button('Home', on_click=lambda: router.open('/'), icon='home').props('flat').classes('text-white q-mr-sm')
        # Resolve function targets
        landing = landing_page.register(router)
        dashboard = dashboard_page.register(router)
        analysis = analysis_page.register(router)
        picks = picks_page.register(router)
        settings = settings_page.register(router)
        combos = combos_page.register(router)
        ui.button('Dashboard', on_click=lambda: router.open(dashboard), icon='dashboard').props('flat').classes('text-white q-mr-sm')
        ui.button('Analysis', on_click=lambda: router.open(analysis), icon='bar_chart').props('flat').classes('text-white q-mr-sm')
        ui.button('Picks', on_click=lambda: router.open(picks), icon='style').props('flat').classes('text-white q-mr-sm')
        ui.button('Combos', on_click=lambda: router.open(combos), icon='functions').props('flat').classes('text-white q-mr-sm')
        ui.button('Settings', on_click=lambda: router.open(settings), icon='settings').props('flat').classes('text-white')
    # Content frame
    router.frame().classes('w-full p-4')

if __name__ in {'__main__','__mp_main__'}:
    if os.getenv('PANDA_PICKS_NO_UI') == '1':
        print('Panda Picks UI loaded (server not started due to PANDA_PICKS_NO_UI=1).')
    else:
        ui.run(port=8001)
