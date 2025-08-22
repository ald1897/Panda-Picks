from nicegui import ui
from ..data import get_upcoming_picks

def register(router):
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
                    {'name': 'Spread', 'label': 'Spread (Home)', 'field': 'Spread', 'sortable': True},
                    {'name': 'Home_Score', 'label': 'Home Score', 'field': 'Home_Score', 'sortable': True},
                    {'name': 'Away_Score', 'label': 'Away Score', 'field': 'Away_Score', 'sortable': True},
                    {'name': 'Predicted_Pick', 'label': 'Predicted Pick', 'field': 'Predicted_Pick', 'sortable': True},
                    {'name': 'Confidence_Score', 'label': 'Confidence Score', 'field': 'Confidence_Score', 'sortable': True},
                ]
                ui.table(columns=columns, rows=picks_data, row_key='Row_ID').classes('w-full')
            else:
                ui.label('No upcoming picks found.').classes('q-pa-md')
    return picks
