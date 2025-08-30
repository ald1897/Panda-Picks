from nicegui import ui
import math
import pandas as pd
from ..data import get_week_picks_for_combos
from panda_picks.analysis.utils.combos import generate_bet_combinations

def register(router):
    @router.add('/combos')
    def combos_page():
        ui.label('Bet Combinations (Parlays)').classes('text-h4 q-mb-md')
        with ui.card().classes('w-full shadow-lg q-pa-md'):
            with ui.row().classes('items-center q-col-gutter-md'):
                week_select = ui.select([f"WEEK{i}" for i in range(1,19)], value='WEEK1', label='Select Week').classes('w-1/6')
                size_multiselect = ui.select(['2','3','4','5'], value=['2','3','4','5'], label='Sizes', multiple=True).classes('w-1/6')
                stake_input = ui.number(label='Stake per Combo', value=100, format='%.0f').classes('w-1/6')
                ui.button('Refresh', icon='refresh', on_click=lambda: update_table()).classes('q-ml-md')
                export_btn = ui.button('Export CSV', icon='download').props('outline')
        summary_card = ui.card().classes('w-full shadow-sm q-pa-md')
        table_container = ui.element('div').classes('w-full')

        # Added 5-leg static odds (+333)
        TEASER_STATIC_AMERICAN = {2: -135, 3: 140, 4: 240, 5: 333}

        def format_american(val):
            try:
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    return 'N/A'
                v = float(val)
                sign = '+' if v > 0 else ''
                return f"{sign}{int(round(v))}"
            except Exception:
                return 'N/A'

        def teaser_profit_from_american(odds: float, stake: float) -> float:
            try:
                o = float(odds)
                if o > 0:  # positive odds
                    return stake * (o / 100.0)
                else:     # negative odds
                    return stake * (100.0 / abs(o))
            except Exception:
                return math.nan

        def update_summary(rows, stake):
            summary_card.clear()
            with summary_card:
                if not rows:
                    ui.label('No combos to summarize.').classes('text-grey')
                    return
                total_combos = len(rows)
                total_wagered = total_combos * stake
                total_profit = sum(r.get('_profit', 0) for r in rows if isinstance(r.get('_profit'), (int,float)))
                total_return = total_wagered + total_profit
                with ui.row().classes('w-full justify-around'):
                    with ui.column().classes('items-center'):
                        ui.label('Combos').classes('text-caption')
                        ui.label(str(total_combos)).classes('text-h6')
                    with ui.column().classes('items-center'):
                        ui.label('Total Wagered').classes('text-caption')
                        ui.label(f"${total_wagered:,.2f}").classes('text-h6')
                    with ui.column().classes('items-center'):
                        ui.label('Total Profit').classes('text-caption')
                        ui.label(f"${total_profit:,.2f}").classes('text-h6')
                    with ui.column().classes('items-center'):
                        ui.label('Total Return').classes('text-caption')
                        ui.label(f"${total_return:,.2f}").classes('text-h6')

        def update_table():
            stake = float(stake_input.value or 0)
            summary_rows = []
            table_container.clear()
            raw_picks = get_week_picks_for_combos(week_select.value)
            if not raw_picks or len(raw_picks) < 2:
                update_summary([], stake)
                with table_container:
                    ui.label('Not enough picks for combinations (need at least 2).').classes('q-pa-md')
                return
            picks_df = pd.DataFrame(raw_picks)
            combos = generate_bet_combinations(picks_df, 2, 5)
            selected_sizes = set(int(s) for s in (size_multiselect.value or []))
            combos = [c for c in combos if c['Size'] in selected_sizes]
            if not combos:
                update_summary([], stake)
                with table_container:
                    ui.label('No combinations for selected sizes.').classes('q-pa-md')
                return
            rows = []
            for c in combos:
                size = c['Size']
                leg_lines = c.get('Leg_Lines', [])
                bet_lines = []
                for ll in leg_lines:
                    cur_disp = ll.get('Current_Line_Display','N/A')
                    teas_disp = ll.get('Teaser_Line_Display','N/A')
                    team = ll.get('Team','?')
                    if cur_disp == 'N/A' and teas_disp == 'N/A':
                        continue
                    bet_lines.append(f"{team} {cur_disp} -> {teas_disp} ")
                bet_info = '<br>'.join(bet_lines) if bet_lines else 'N/A'
                if size in TEASER_STATIC_AMERICAN:
                    am_odds = TEASER_STATIC_AMERICAN[size]
                    profit = teaser_profit_from_american(am_odds, stake)
                else:
                    am_odds = c.get('Book_American_Odds')
                    dec = c.get('Book_Dec_Odds')
                    profit = stake * (dec - 1) if isinstance(dec,(int,float)) and not math.isnan(dec or math.nan) else math.nan
                rows.append({
                    'Size': size,
                    'Teams': c['Teams'],
                    'Bet_Info': bet_info,
                    'Book_American': format_american(am_odds),
                    'Est_Payout_$100': f"${profit:,.2f}" if profit == profit else 'N/A',
                    '_profit': profit
                })
            update_summary(rows, stake)
            columns = [
                {'name': 'Size', 'label': 'Legs', 'field': 'Size', 'sortable': True},
                {'name': 'Teams', 'label': 'Teams', 'field': 'Teams'},
                {'name': 'Bet_Info', 'label': 'Bet Info', 'field': 'Bet_Info'},
                {'name': 'Book_American', 'label': 'Teaser Odds (Am)', 'field': 'Book_American', 'sortable': True},
                {'name': 'Est_Payout_$100', 'label': f'Profit on ${int(stake)} Stake', 'field': 'Est_Payout_$100', 'sortable': True},
            ]
            with table_container:
                tbl = ui.table(columns=columns, rows=rows, row_key='Teams').props('dense bordered').classes('w-full')
                tbl.add_slot('body-cell-Bet_Info', r'''<q-td :props="props"><div v-html="props.row.Bet_Info"></div></q-td>''')
                tbl.add_slot('top-right', r'''
                    <q-input borderless dense debounce="300" v-model="props.filter" placeholder="Filter">
                      <template v-slot:append><q-icon name="search" /></template>
                    </q-input>
                ''')
            def do_export():
                import csv, io
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=[c['name'] for c in columns])
                writer.writeheader()
                for r in rows:
                    writer.writerow({k: r.get(k) for k in writer.fieldnames})
                ui.download(output.getvalue(), filename=f"combos_{week_select.value}.csv")
            export_btn.on('click', lambda e: do_export())
        update_table()
        week_select.on('update:model-value', lambda e: update_table())
        size_multiselect.on('update:model-value', lambda e: update_table())
        stake_input.on('update:model-value', lambda e: update_table())
    return combos_page
