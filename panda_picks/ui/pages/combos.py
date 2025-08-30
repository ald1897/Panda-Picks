from nicegui import ui
import math
import pandas as pd
from ..data import get_week_picks_for_combos
from panda_picks.analysis.utils.combos import generate_bet_combinations
import json
from pathlib import Path
from typing import Dict, List, Any

OVERRIDES_FILE = Path(__file__).resolve().parent / 'manual_combo_overrides.json'

def _load_overrides() -> Dict[str, Any]:
    try:
        if OVERRIDES_FILE.exists():
            return json.loads(OVERRIDES_FILE.read_text())
    except Exception:
        pass
    return {}

def _save_overrides(data: Dict[str, Any]):
    try:
        OVERRIDES_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass

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
        # Overrides / manual picks UI container
        overrides_card = ui.card().classes('w-full shadow-sm q-pa-sm')
        table_container = ui.element('div').classes('w-full')
        summary_card = ui.card().classes('w-full shadow-sm q-pa-md')

        # Added 5-leg static odds (+333)
        TEASER_STATIC_AMERICAN = {2: -135, 3: 140, 4: 240, 5: 333}

        overrides_state = {
            'raw_picks': [],           # model picks for current week
            'manual_picks': {},        # week -> list of manual rows
            'selected_teams': {},      # week -> list of selected team names
        }
        overrides_state['manual_picks'] = _load_overrides().get('manual', {})
        overrides_state['selected_teams'] = _load_overrides().get('selected', {})

        # Will be initialized later
        team_multiselect = {'widget': None}
        manual_list_container = ui.column().classes('w-full')

        def persist_overrides():
            data = {
                'manual': overrides_state['manual_picks'],
                'selected': overrides_state['selected_teams'],
            }
            _save_overrides(data)

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

        def get_current_manual_picks(week_key: str) -> List[Dict[str, Any]]:
            return overrides_state['manual_picks'].get(week_key, [])

        def set_current_manual_picks(week_key: str, lst: List[Dict[str, Any]]):
            overrides_state['manual_picks'][week_key] = lst
            persist_overrides()
            refresh_manual_list()

        def refresh_manual_list():
            manual_list_container.clear()
            wk = week_select.value
            mpicks = get_current_manual_picks(wk)
            if not mpicks:
                with manual_list_container:
                    ui.label('No manual picks added.').classes('text-caption text-grey')
                return
            with manual_list_container:
                ui.label('Manual Picks:').classes('text-caption')
                for idx, mp in enumerate(mpicks):
                    with ui.row().classes('items-center q-gutter-xs'):
                        ui.label(f"{mp.get('Game_Pick')} (Odds: {mp.get('Home_Odds_Close')}, Prob: {mp.get('Home_Win_Prob'):.3f})").classes('text-caption')
                        ui.button(icon='delete', flat=True, dense=True, on_click=lambda i=idx: remove_manual_pick(i)).props('size=sm')

        def remove_manual_pick(index: int):
            wk = week_select.value
            mpicks = get_current_manual_picks(wk)
            if 0 <= index < len(mpicks):
                mpicks.pop(index)
                set_current_manual_picks(wk, mpicks)
                # also update selection widget options
                rebuild_team_selection()
                update_table()

        def rebuild_team_selection():
            # Build list of model picks + manual picks
            wk = week_select.value
            model_picks = overrides_state['raw_picks']
            manual_picks = get_current_manual_picks(wk)
            teams = sorted({p['Game_Pick'] for p in model_picks} | {m['Game_Pick'] for m in manual_picks})
            stored_sel = overrides_state['selected_teams'].get(wk)
            if stored_sel:
                # Preserve only those still present
                selected = [t for t in stored_sel if t in teams]
            else:
                selected = teams[:]  # default all
            overrides_state['selected_teams'][wk] = selected
            if team_multiselect['widget'] is None:
                team_multiselect['widget'] = ui.select(teams, value=selected, multiple=True, label='Include Teams (override)').classes('w-full')
                team_multiselect['widget'].on('update:model-value', lambda e: on_team_selection_change())
            else:
                team_multiselect['widget'].options = teams
                team_multiselect['widget'].value = selected
            persist_overrides()

        def on_team_selection_change():
            wk = week_select.value
            overrides_state['selected_teams'][wk] = list(team_multiselect['widget'].value or [])
            persist_overrides()
            update_table()

        def add_manual_pick(team: str, american_odds: float, win_prob: float, line: float | None):
            wk = week_select.value
            try:
                prob = float(win_prob)
                if prob <= 0 or prob >= 1:
                    return
            except Exception:
                return
            try:
                am = float(american_odds)
            except Exception:
                return
            ln = 0.0
            try:
                if line is not None:
                    ln = float(line)
            except Exception:
                ln = 0.0
            row = {
                'WEEK': wk,
                'Home_Team': team,  # treat as home for simplicity
                'Away_Team': 'MANUAL',
                'Game_Pick': team,
                'Home_Odds_Close': am,
                'Away_Odds_Close': +100,  # dummy
                'Home_Win_Prob': prob,
                'Away_Win_Prob': 1 - prob,
                'Pick_Prob': prob,
                'Pick_Edge': 0.0,
                'Home_Line_Close': ln,
                'Away_Line_Close': -ln,
            }
            mpicks = get_current_manual_picks(wk) + [row]
            set_current_manual_picks(wk, mpicks)
            rebuild_team_selection()
            update_table()

        # Build overrides UI (dynamic parts will be filled after week load)
        with overrides_card:
            ui.label('Overrides & Manual Picks').classes('text-subtitle2 q-mb-sm')
            with ui.expansion('Configure Picks', icon='tune', value=False).classes('w-full'):
                with ui.column().classes('w-full q-gutter-sm'):
                    ui.label('Select which teams/picks to include in combinations. Deselect to exclude. Add manual picks below to override the model.').classes('text-caption text-grey')
                    # team_multiselect inserted dynamically
                    # Manual add form
                    with ui.row().classes('q-col-gutter-sm items-end'):
                        manual_team_input = ui.input(label='Manual Team').classes('w-1/5')
                        manual_odds_input = ui.number(label='American Odds', value='+100').classes('w-1/5')
                        manual_prob_input = ui.number(label='Win Prob (0-1)', value=0.55, format='%.3f').classes('w-1/5')
                        manual_line_input = ui.number(label='Line (optional)', value=0, format='%.1f').classes('w-1/5')
                        ui.button('Add Manual Pick', icon='add', on_click=lambda: add_manual_pick(manual_team_input.value.strip().upper() if manual_team_input.value else '', manual_odds_input.value, manual_prob_input.value, manual_line_input.value)).classes('w-1/5')
                    manual_list_container  # placeholder for manual picks list
                    ui.button('Reset Week Selections', icon='restart_alt', color='warning', on_click=lambda: reset_week_selection()).props('outline size=sm')

        def reset_week_selection():
            wk = week_select.value
            overrides_state['selected_teams'][wk] = [p['Game_Pick'] for p in overrides_state['raw_picks']] + [m['Game_Pick'] for m in get_current_manual_picks(wk)]
            rebuild_team_selection()
            update_table()

        def load_week_picks():
            wk = week_select.value
            raw = get_week_picks_for_combos(wk)
            overrides_state['raw_picks'] = raw or []
            rebuild_team_selection()
            refresh_manual_list()

        def update_table():
            stake = float(stake_input.value or 0)
            summary_rows = []
            table_container.clear()
            wk = week_select.value
            raw_picks = overrides_state['raw_picks']
            manual_picks = get_current_manual_picks(wk)
            # Apply selection filter
            selected = set(overrides_state['selected_teams'].get(wk, []))
            effective_rows = [p for p in raw_picks if p.get('Game_Pick') in selected] + [m for m in manual_picks if m.get('Game_Pick') in selected]
            if not effective_rows or len(effective_rows) < 2:
                update_summary([], stake)
                with table_container:
                    ui.label('Not enough selected picks for combinations (need at least 2).').classes('q-pa-md')
                return
            picks_df = pd.DataFrame(effective_rows)
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

        def initialize_week():
            load_week_picks()
            update_table()

        # Initial load
        initialize_week()
        week_select.on('update:model-value', lambda e: initialize_week())
        size_multiselect.on('update:model-value', lambda e: update_table())
        stake_input.on('update:model-value', lambda e: update_table())
    return combos_page
