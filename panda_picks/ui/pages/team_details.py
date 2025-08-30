from nicegui import ui
from ..data import get_all_team_names, get_team_details

def register(router):
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
    return team_details_page

