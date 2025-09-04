from nicegui import ui
import json
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
                COMPARISON_MAP = [
                    {'home':'PASS','aways':['PRSH','COV'],'label':'Passing Offense vs Pass Rush & Coverage'},
                    {'home':'RUN','aways':['RDEF','TACK'],'label':'Rushing Offense vs Run Defense & Tackling'},
                    {'home':'OFF','aways':['DEF'],'label':'Overall Offense vs Overall Defense'},
                    {'home':'RECV','aways':['COV'],'label':'Receiving vs Coverage'},
                    {'home':'PBLK','aways':['PRSH'],'label':'Pass Blocking vs Pass Rush'},
                    {'home':'RBLK','aways':['RDEF'],'label':'Run Blocking vs Run Defense'},
                    {'home':'DEF','aways':['OFF'],'label':'Overall Defense vs Opponent Offense'},
                    {'home':'PRSH','aways':['PBLK','PASS'],'label':'Pass Rush vs Pass Blocking & Passing'},
                    {'home':'COV','aways':['RECV'],'label':'Coverage vs Receiving'},
                    {'home':'RDEF','aways':['RUN','RBLK'],'label':'Run Defense vs Rushing & Run Blocking'},
                    {'home':'TACK','aways':['RUN'],'label':'Tackling vs Rushing'},
                ]
                # Tooltip explanations for each aspect label
                TOOLTIP_MAP = {
                    'Passing Offense vs Pass Rush & Coverage': 'Home passing grade against the opponent\'s ability to generate pressure (PRSH) and defend routes (COV).',
                    'Rushing Offense vs Run Defense & Tackling': 'Home rushing efficiency versus opponent run defense gap integrity (RDEF) and tackling reliability (TACK).',
                    'Overall Offense vs Overall Defense': 'Aggregate offensive grade compared to opponent\'s composite defensive grade.',
                    'Receiving vs Coverage': 'Receiver separation/production versus opponent coverage ability (COV).',
                    'Pass Blocking vs Pass Rush': 'Protection quality (PBLK) versus opponent pass rush disruption rate (PRSH).',
                    'Run Blocking vs Run Defense': 'Line/run scheme blocking success versus opponent front run defense (RDEF).',
                    'Overall Defense vs Opponent Offense': 'Defense composite grade versus opponent overall offensive strength.',
                    'Pass Rush vs Pass Blocking & Passing': 'Ability to create pressure (PRSH) versus opponent pass protection (PBLK) and passing execution (PASS).',
                    'Coverage vs Receiving': 'Coverage unit performance versus opponent receiving corps.',
                    'Run Defense vs Rushing & Run Blocking': 'Front/seconday run stopping versus opponent rushing production (RUN) and run blocking (RBLK).',
                    'Tackling vs Rushing': 'Tackling efficiency versus opponent rushing attempts and yards creation.',
                }
                # Icon & color metadata for visual tags
                CATEGORY_META = {
                    'Passing Offense vs Pass Rush & Coverage': {'icon':'send','color':'#1976d2'},
                    'Rushing Offense vs Run Defense & Tackling': {'icon':'directions_run','color':'#388e3c'},
                    'Overall Offense vs Overall Defense': {'icon':'dashboard','color':'#00897b'},
                    'Receiving vs Coverage': {'icon':'groups','color':'#7b1fa2'},
                    'Pass Blocking vs Pass Rush': {'icon':'construction','color':'#5d4037'},
                    'Run Blocking vs Run Defense': {'icon':'build','color':'#6d4c41'},
                    'Overall Defense vs Opponent Offense': {'icon':'security','color':'#455a64'},
                    'Pass Rush vs Pass Blocking & Passing': {'icon':'bolt','color':'#f57c00'},
                    'Coverage vs Receiving': {'icon':'visibility','color':'#512da8'},
                    'Run Defense vs Rushing & Run Blocking': {'icon':'health_and_safety','color':'#2e7d32'},
                    'Tackling vs Rushing': {'icon':'sports_mma','color':'#c62828'},
                }
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
                    except Exception:
                        return None
                    return None
                advantage_columns = [
                    ('Overall_Adv','Overall Advantage'),
                    ('Offense_Adv','Offense Advantage'),
                    ('Defense_Adv','Defense Advantage')
                ]
                def render_table(rows, tooltip_map):
                    if not rows: return
                    cols = [
                        {'name':'Matchup','label':'Aspect','field':'Matchup','sortable':True},
                        {'name':'Home','label':'Home Grade','field':'Home','sortable':True},
                        {'name':'Away','label':'Opponent Counters','field':'Away','sortable':False},
                        {'name':'Diff','label':'Home Edge','field':'Diff','sortable':True},
                    ]
                    tbl = ui.table(columns=cols, rows=rows, row_key='Matchup').props('dense bordered flat square').classes('w-full')
                    tooltip_json = json.dumps(tooltip_map)
                    # Updated cell with icon & color
                    tbl.add_slot('body-cell-Matchup', r'''<q-td :props="props"><div style="display:flex;align-items:center;gap:6px;"> <q-icon :name="props.row._icon" :style="`color:${props.row._color}`" size="16px"/> <span>{{ props.row.Matchup }}</span> <q-icon name="info" size="14px" class="text-grey-5"><q-tooltip>{{ (function(){ const m = %s; return m[props.row.Matchup] || '' })() }}</q-tooltip></q-icon></div></q-td>''' % tooltip_json)
                    tbl.add_slot('header-cell-Matchup', r'''<q-th :props="props">Aspect <q-icon name="help_outline" size="14px" class="text-grey-6"><q-tooltip>Describes the home team aspect versus key opponent counters.</q-tooltip></q-icon></q-th>''')
                    tbl.add_slot('header-cell-Home', r'''<q-th :props="props">Home Grade <q-icon name="help_outline" size="14px" class="text-grey-6"><q-tooltip>Model grade for the home team aspect.</q-tooltip></q-icon></q-th>''')
                    tbl.add_slot('header-cell-Away', r'''<q-th :props="props">Opponent Counters <q-icon name="help_outline" size="14px" class="text-grey-6"><q-tooltip>Relevant opponent metrics; multiple separated by | .</q-tooltip></q-icon></q-th>''')
                    tbl.add_slot('header-cell-Diff', r'''<q-th :props="props">Home Edge <q-icon name="help_outline" size="14px" class="text-grey-6"><q-tooltip>Home Edge = Home Grade - average of listed opponent counter grades (positive favors home).</q-tooltip></q-icon></q-th>''')
                    tbl.add_slot('body-cell-Diff', r'''<q-td :props="props"><span :style="(() => {const d=props.row._diff_raw; if(d===0) return ''; const a=Math.min(Math.abs(d)/40,0.35); return `background-color:${d>0?`rgba(76,175,80,${a})`:`rgba(244,67,54,${a})`}; padding:2px 4px; border-radius:3px; display:inline-block;`; })()" :class="{'text-green': props.row._diff_raw>0, 'text-red': props.row._diff_raw<0}">{{ props.row.Diff }}</span></q-td>''')
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
                                ov = next((m['value'] for m in adv_metrics if m['label'].startswith('Overall')), None)
                                if isinstance(ov,(int,float)):
                                    adv_txt = f"Overall Adv: {ov:+.2f}"
                            pick_edge_txt = ''
                            if pick and isinstance(pick.get('Pick_Edge'), (int,float)):
                                pick_edge_txt = f"Pick Edge: {pick.get('Pick_Edge'):+.3f}"
                            header_parts = [t for t in [line_txt, odds_txt, adv_txt, pick_edge_txt] if t]
                            ui.label(' | '.join(header_parts)).classes('text-caption text-grey')
                        if adv_metrics:
                            labels = [m['label'] for m in adv_metrics]
                            values = [float(m['value']) for m in adv_metrics]
                            bar_colors = [COLORS['primary'] if v > 0 else '#f44336' for v in values]
                            max_abs = max(abs(v) for v in values) if values else 1.0
                            html_rows = ['<div style="display:flex;flex-direction:column;gap:8px;padding:6px 0;">']
                            for lbl, val, col in zip(labels, values, bar_colors):
                                pct = (abs(val) / max_abs) if max_abs else 0
                                bar_width = int(60 + pct * 340)
                                html_rows.append(
                                    "<div style='display:flex;align-items:center;gap:12px;'>"
                                    f"<div style='width:160px;font-size:13px;color:#333;'>{lbl}</div>"
                                    f"<div style='flex:0 0 {bar_width}px;height:20px;border-radius:6px;background:{col};box-shadow:inset 0 -2px 0 rgba(0,0,0,0.12);'></div>"
                                    f"<div style='width:90px;text-align:right;font-size:13px;color:#222'>{val:+.2f}</div>"
                                    "</div>"
                                )
                            html_rows.append('</div>')
                            ui.html(''.join(html_rows)).classes('w-full q-mb-sm')

                        with ui.row().classes('w-full q-col-gutter-md'):
                            with ui.card().classes('w-1/2 shadow'):
                                if pick and pick.get('Game_Pick') == home:
                                    ui.badge('Model Pick', color='green').classes('q-mt-sm')
                                elif pick and pick.get('Game_Pick') == away:
                                    ui.badge('Model Pick', color='green').classes('q-mt-sm')
                        # Build matchup-based rows then split into offense/defense groups
                        all_rows = []
                        for cfg in COMPARISON_MAP:
                            home_metric = cfg['home']
                            home_val = home_gr.get(home_metric)
                            away_values = []
                            numeric_aways = []
                            for am in cfg['aways']:
                                v = away_gr.get(am)
                                away_values.append((am, v))
                                if isinstance(v,(int,float)):
                                    numeric_aways.append(v)
                            if home_val is None and not any(v is not None for _,v in away_values):
                                continue
                            diff = None
                            if isinstance(home_val,(int,float)) and numeric_aways:
                                base = numeric_aways[0] if len(numeric_aways)==1 else sum(numeric_aways)/len(numeric_aways)
                                diff = home_val - base
                            if len(away_values) == 1:
                                away_display = fmt(away_values[0][1])
                            else:
                                parts = []
                                for mn, mv in away_values:
                                    parts.append(f"{mn}: {fmt(mv)}" if mv is not None else f"{mn}: N/A")
                                away_display = ' | '.join(parts)
                            label_txt = cfg['label']
                            meta = CATEGORY_META.get(label_txt, {'icon':'info','color':'#607d8b'})
                            all_rows.append({
                                'Matchup': label_txt,
                                'Home': fmt(home_val),
                                'Away': away_display,
                                'Diff': (f"{diff:+.1f}" if isinstance(diff,(int,float)) else 'N/A'),
                                '_diff_raw': diff if isinstance(diff,(int,float)) else 0,
                                '_icon': meta['icon'],
                                '_color': meta['color']
                            })
                        offense_set = {
                            'Passing Offense vs Pass Rush & Coverage',
                            'Rushing Offense vs Run Defense & Tackling',
                            'Overall Offense vs Overall Defense',
                            'Receiving vs Coverage',
                            'Pass Blocking vs Pass Rush',
                            'Run Blocking vs Run Defense'
                        }
                        offense_rows = [r for r in all_rows if r['Matchup'] in offense_set]
                        defense_rows = [r for r in all_rows if r['Matchup'] not in offense_set]
                        if offense_rows:
                            ui.label('Home Offense Matchups').classes('text-subtitle2 q-mt-md')
                            render_table(offense_rows, TOOLTIP_MAP)
                        if defense_rows:
                            ui.label('Home Defense Matchups').classes('text-subtitle2 q-mt-lg')
                            render_table(defense_rows, TOOLTIP_MAP)
                week_select.on('update:model-value', lambda e: refresh_matchups())
                matchup_select.on('update:model-value', lambda e: update_comparison())
                refresh_matchups()
            else:
                ui.label('No spreads data found to populate matchups.').classes('q-pa-md')
    return analysis
