from nicegui import ui
from ..data import get_team_grades

def register(router):
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
                table.add_slot('top-right', r'''\n                    <q-input borderless dense debounce="300" v-model="props.filter" placeholder="Search">\n                    <template v-slot:append>\n                        <q-icon name="search" />\n                    </template>\n                    </q-input>\n                ''')
            else:
                ui.label('No team grades found.').classes('q-pa-md')
    return grades

