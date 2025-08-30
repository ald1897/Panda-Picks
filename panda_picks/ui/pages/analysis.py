from nicegui import ui
from ..data import get_available_weeks, get_week_matchups, get_matchup_details, COLORS

def register(router):
    @router.add('/analysis')
    def analysis():
        ui.label('Analysis').classes('text-h4 q-mb-lg')
        with ui.card().classes('w-full shadow-lg q-mb-lg'):
            ui.label('Matchup Explorer').classes('text-h6 q-pa-md')
            weeks = get_available_weeks()
            if weeks:
                with ui.row().classes('q-pa-sm items-center q-col-gutter-md'):
                    week_select = ui.select(weeks, value=weeks[0], label='Week').classes('w-1/6')
                    matchup_select = ui.select([], label='Matchup').classes('w-1/3')
                comparison_container = ui.column().classes('w-full q-pa-sm gap-4')
                metrics = ['OVR','OFF','DEF','PASS','RUN','RECV','PBLK','RBLK','PRSH','COV','RDEF','TACK']
                def fmt(val):
                    try:
                        if val is None: return 'N/A'
                        if isinstance(val,(int,float)):
                            return f"{val:.1f}" if abs(val) % 1 else f"{int(val)}"
                        return str(val)
                    except Exception:
                        return 'N/A'
                def refresh_matchups():
                    m_list = get_week_matchups(week_select.value)
                    matchup_select.options = [m['Label'] for m in m_list]
                    matchup_select.value = m_list[0]['Label'] if m_list else None
                    update_comparison()
                def compute_adv(home_gr, away_gr, col):
                    try:
                        if not home_gr or not away_gr:
                            return None
                        if col == 'Overall_Adv':
                            return (home_gr.get('OVR') - away_gr.get('OVR')) if home_gr.get('OVR') is not None and away_gr.get('OVR') is not None else None
                        if col == 'Offense_Adv':
                            return (home_gr.get('OFF') - away_gr.get('DEF')) if home_gr.get('OFF') is not None and away_gr.get('DEF') is not None else None
                        if col == 'Defense_Adv':
                            return (home_gr.get('DEF') - away_gr.get('OFF')) if home_gr.get('DEF') is not None and away_gr.get('OFF') is not None else None
                        if col == 'Off_Comp_Adv':
                            # Composite offense vs composite defense (fallback heuristic)
                            offensive_parts = [home_gr.get(k) for k in ['OFF','PASS','RUN','RECV','PBLK','RBLK'] if home_gr.get(k) is not None]
                            defensive_parts = [away_gr.get(k) for k in ['DEF','COV','RDEF','PRSH','TACK'] if away_gr.get(k) is not None]
                            if offensive_parts and defensive_parts:
                                return (sum(offensive_parts)/len(offensive_parts)) - (sum(defensive_parts)/len(defensive_parts))
                            return None
                        if col == 'Def_Comp_Adv':
                            defensive_parts_home = [home_gr.get(k) for k in ['DEF','COV','RDEF','PRSH','TACK'] if home_gr.get(k) is not None]
                            offensive_parts_away = [away_gr.get(k) for k in ['OFF','PASS','RUN','RECV','PBLK','RBLK'] if away_gr.get(k) is not None]
                            if defensive_parts_home and offensive_parts_away:
                                return (sum(defensive_parts_home)/len(defensive_parts_home)) - (sum(offensive_parts_away)/len(offensive_parts_away))
                            return None
                    except Exception:
                        return None
                    return None
                advantage_columns = [
                    ('Overall_Adv','Overall Advantage'),
                    ('Offense_Adv','Offense Advantage'),
                    ('Defense_Adv','Defense Advantage'),
                    ('Off_Comp_Adv','Off Comp Adv'),
                    ('Def_Comp_Adv','Def Comp Adv'),
                ]
                def update_comparison():
                    comparison_container.clear()
                    label = matchup_select.value
                    if not label: return
                    try:
                        parts = label.split('@')
                        away = parts[0].strip()
                        home = parts[1].strip()
                    except Exception:
                        return
                    details = get_matchup_details(week_select.value, home, away)
                    spread = details['spread']
                    pick = details['pick']
                    home_gr = details['home_grades']
                    away_gr = details['away_grades']
                    adv_metrics = []
                    for adv_col,label_txt in advantage_columns:
                        val = pick.get(adv_col) if pick else None
                        if not isinstance(val,(int,float)):
                            val = compute_adv(home_gr, away_gr, adv_col)
                        if isinstance(val,(int,float)):
                            adv_metrics.append({'label':label_txt,'value':val})
                    with comparison_container:
                        with ui.row().classes('items-center justify-between w-full'):
                            ui.label(f"{away} @ {home}").classes('text-h6')
                            line_txt = ''
                            if spread:
                                hl = spread.get('Home_Line_Close')
                                if hl is not None:
                                    line_txt = f"Line: {home} {hl:+}" if isinstance(hl,(int,float)) else f"Line: {hl}"
                            odds_txt = ''
                            if spread:
                                ho = spread.get('Home_Odds_Close')
                                ao = spread.get('Away_Odds_Close')
                                if ho is not None and ao is not None:
                                    odds_txt = f"Odds (H/A): {ho} / {ao}"
                            adv_txt = ''
                            if adv_metrics:
                                # show overall adv (home perspective) first metric
                                ov = next((m['value'] for m in adv_metrics if m['label'].startswith('Overall')), None)
                                if isinstance(ov,(int,float)):
                                    adv_txt = f"Overall Adv: {ov:+.2f}"
                            pick_edge_txt = ''
                            if pick and isinstance(pick.get('Pick_Edge'), (int,float)):
                                pick_edge_txt = f"Pick Edge: {pick.get('Pick_Edge'):+.3f}"
                            header_parts = [t for t in [line_txt, odds_txt, adv_txt, pick_edge_txt] if t]
                            ui.label(' | '.join(header_parts)).classes('text-caption text-grey')
                        if adv_metrics:
                            max_abs = max(abs(m['value']) for m in adv_metrics) or 1
                            with ui.column().classes('w-full q-mt-xs'):
                                for m in adv_metrics:
                                    pct = (abs(m['value'])/max_abs)
                                    with ui.row().classes('items-center w-full'):
                                        ui.label(m['label']).classes('text-caption w-1/4')
                                        color = 'green' if m['value'] > 0 else 'red'
                                        ui.linear_progress(value=pct, show_value=False).props(f'color={color}').classes('w-2/4')
                                        ui.label(f"{m['value']:+.2f}").classes('text-caption w-1/4 text-right')
                        with ui.row().classes('w-full q-col-gutter-md'):
                            with ui.card().classes('w-1/2 shadow'):
                                ui.label(f"Home: {home}").classes('text-subtitle1 q-mb-xs')
                                with ui.row().classes('text-caption wrap'):
                                    for m in metrics:
                                        if m in home_gr:
                                            ui.label(f"{m}: {fmt(home_gr.get(m))}").classes('q-mr-md q-mb-xs')
                                if pick and pick.get('Game_Pick') == home:
                                    ui.badge('Model Pick', color='green').classes('q-mt-sm')
                            with ui.card().classes('w-1/2 shadow'):
                                ui.label(f"Away: {away}").classes('text-subtitle1 q-mb-xs')
                                with ui.row().classes('text-caption wrap'):
                                    for m in metrics:
                                        if m in away_gr:
                                            ui.label(f"{m}: {fmt(away_gr.get(m))}").classes('q-mr-md q-mb-xs')
                                if pick and pick.get('Game_Pick') == away:
                                    ui.badge('Model Pick', color='green').classes('q-mt-sm')
                        rows = []
                        for m in metrics:
                            hv = home_gr.get(m)
                            av = away_gr.get(m)
                            if hv is None and av is None: continue
                            diff = hv - av if isinstance(hv,(int,float)) and isinstance(av,(int,float)) else None
                            rows.append({'Metric': m,'Home': fmt(hv),'Away': fmt(av),'Diff': (f"{diff:+.1f}" if diff is not None else 'N/A'),'_diff_raw': diff if diff is not None else 0})
                        if rows:
                            cols = [
                                {'name':'Metric','label':'Metric','field':'Metric','sortable':True},
                                {'name':'Home','label':home,'field':'Home','sortable':True},
                                {'name':'Away','label':away,'field':'Away','sortable':True},
                                {'name':'Diff','label':'Diff (H-A)','field':'Diff','sortable':True},
                            ]
                            tbl = ui.table(columns=cols, rows=rows, row_key='Metric').props('dense bordered flat square').classes('w-full')
                            tbl.add_slot('body-cell-Diff', r'''<q-td :props="props"><span :style="(() => {const d=props.row._diff_raw; if(d===0) return ''; const a=Math.min(Math.abs(d)/40,0.35); return `background-color:${d>0?`rgba(76,175,80,${a})`:`rgba(244,67,54,${a})`}; padding:2px 4px; border-radius:3px; display:inline-block;`; })()" :class="{'text-green': props.row._diff_raw>0, 'text-red': props.row._diff_raw<0}">{{ props.row.Diff }}</span></q-td>''')
                week_select.on('update:model-value', lambda e: refresh_matchups())
                matchup_select.on('update:model-value', lambda e: update_comparison())
                refresh_matchups()
            else:
                ui.label('No spreads data found to populate matchups.').classes('q-pa-md')
    return analysis
