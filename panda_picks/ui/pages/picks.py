from nicegui import ui
from ..data import get_upcoming_picks


def register(router):
    @router.add('/picks')
    def picks():
        ui.label('Upcoming Picks').classes('text-h4 q-mb-lg')
        picks_data = get_upcoming_picks()

        with ui.row().classes('w-full items-center q-mb-md'):
            ui.button('Export to CSV', icon='download', on_click=lambda: ui.notify('Exporting... (placeholder)')).classes('q-mr-md')
            ui.switch('Show Past Picks')  # placeholder (existing)
            show_teasers = ui.switch('Show Teaser Columns', value=True)

        COLOR_MAP = {'WIN': 'green', 'LOSS': 'red', 'PUSH': 'grey', 'PENDING': 'orange', 'NA': 'grey'}
        if picks_data:
            for r in picks_data:
                res = (r.get('Result') or '').strip() or 'PENDING'
                r['Result'] = res  # normalize empty to PENDING
                r['Result_Color'] = COLOR_MAP.get(res, 'grey')
                r['Result_Display'] = res
                tres = (r.get('Teaser_Result') or '').strip() or 'PENDING'
                r['Teaser_Result'] = tres
                r['Teaser_Result_Color'] = COLOR_MAP.get(tres, 'grey')
                r['Teaser_Result_Display'] = tres

        def build_columns(include_teasers: bool):
            base = [
                {'name': 'Week', 'label': 'Week', 'field': 'Week', 'sortable': True},
                {'name': 'Home_Team', 'label': 'Home Team', 'field': 'Home_Team', 'sortable': True},
                {'name': 'Away_Team', 'label': 'Away Team', 'field': 'Away_Team', 'sortable': True},
                {'name': 'Spread', 'label': 'Spread (Home)', 'field': 'Spread', 'sortable': True},
                {'name': 'Predicted_Pick', 'label': 'Predicted Pick', 'field': 'Predicted_Pick', 'sortable': True},
                {'name': 'Result', 'label': 'Result', 'field': 'Result', 'sortable': True},
                {'name': 'Confidence_Score', 'label': 'Confidence', 'field': 'Confidence_Score', 'sortable': True},
            ]
            teaser_cols = [
                {'name': 'Teaser_Pick', 'label': 'Teaser Pick (6pt)', 'field': 'Teaser_Pick', 'sortable': True},
                {'name': 'Teaser_Result', 'label': 'Teaser Result', 'field': 'Teaser_Result', 'sortable': True},
            ] if include_teasers else []
            tail = [
                {'name': 'Home_Score', 'label': 'Home Score', 'field': 'Home_Score', 'sortable': True},
                {'name': 'Away_Score', 'label': 'Away Score', 'field': 'Away_Score', 'sortable': True},
            ]
            return base + teaser_cols + tail

        with ui.card().classes('w-full shadow-lg'):
            if picks_data:
                columns = build_columns(include_teasers=True)
                table = ui.table(columns=columns, rows=picks_data, row_key='Row_ID').classes('w-full')

                table.add_slot('body-cell-Result', r'''<q-td :props="props">
                    <q-badge :color="props.row.Result_Color" text-color="white" class="q-pa-xs" style="min-width:52px;display:inline-block;text-align:center;">{{ props.row.Result_Display }}</q-badge>
                </q-td>''')
                table.add_slot('body-cell-Teaser_Result', r'''<q-td :props="props">
                    <q-badge :color="props.row.Teaser_Result_Color" text-color="white" class="q-pa-xs" style="min-width:52px;display:inline-block;text-align:center;">{{ props.row.Teaser_Result_Display }}</q-badge>
                </q-td>''')

                def on_toggle_teasers():
                    include = show_teasers.value
                    table.columns = build_columns(include_teasers=include)
                    table.update()
                if hasattr(show_teasers, 'on_value_change'):
                    show_teasers.on_value_change(lambda _: on_toggle_teasers())
                else:
                    show_teasers.on('update:model-value', lambda e: on_toggle_teasers())
            else:
                ui.label('No upcoming picks found.').classes('q-pa-md')
    return picks
