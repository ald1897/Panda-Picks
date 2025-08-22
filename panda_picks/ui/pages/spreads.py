from nicegui import ui
from ..data import get_spreads_data

def register(router):
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
    return spreads

