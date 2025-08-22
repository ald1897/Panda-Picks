from nicegui import ui
from ..data import calculate_win_rates, get_total_picks, get_upcoming_games, get_recent_picks, get_win_rate_trend, get_weekly_profit_and_balance, get_teaser_weekly_profit_and_balance, COLORS

def register(router):
    @router.add('/dashboard')
    def dashboard():
        ui.label('Dashboard').classes('text-h4 q-mb-lg')
        with ui.row().classes('w-full justify-center q-col-gutter-md'):
            with ui.card().style(f'background: linear-gradient(135deg, {COLORS["card1"]}, #42A312); color: white').classes('q-pa-md shadow-lg'):
                with ui.column().classes('items-center'):
                    ui.icon('analytics').classes('text-h2 q-mb-md')
                    ui.label('Overall Win Rate').classes('text-h6')
                    ui.label(calculate_win_rates()['overall']).classes('text-h3')
            with ui.card().style(f'background: linear-gradient(135deg, {COLORS["card2"]}, #e64a19); color: white').classes('q-pa-md shadow-lg'):
                with ui.column().classes('items-center'):
                    ui.icon('sports').classes('text-h2 q-mb-md')
                    ui.label('Total Picks').classes('text-h6')
                    ui.label(str(get_total_picks())).classes('text-h3')
            with ui.card().style(f'background: linear-gradient(135deg, {COLORS["card3"]}, #3949ab); color: white').classes('q-pa-md shadow-lg'):
                with ui.column().classes('items-center'):
                    ui.icon('event').classes('text-h2 q-mb-md')
                    ui.label('Upcoming Games').classes('text-h6')
                    ui.label(str(get_upcoming_games())).classes('text-h3')
        # Weekly Win Rate Trend chart
        trend = get_win_rate_trend()
        with ui.card().classes('w-full q-mt-lg shadow-lg'):
            ui.label('Weekly Win Rate Trend').classes('text-h6 q-pa-md')
            if trend['weeks']:
                opts = {
                    'tooltip': {'trigger': 'axis'},
                    'xAxis': {'type': 'category', 'data': trend['weeks']},
                    'yAxis': {'type': 'value', 'min': 0, 'max': 100, 'axisLabel': {'formatter': '{value}%'}},
                    'series': [{
                        'name': 'Win Rate', 'type': 'line', 'data': trend['win_rates'],
                        'smooth': True, 'lineStyle': {'width': 3, 'color': COLORS['primary']},
                        'areaStyle': {'color': 'rgba(72,135,43,0.15)'}
                    }]
                }
                ui.echart(options=opts).classes('w-full').style('height:300px;')
            else:
                ui.label('No historical picks to display.').classes('q-pa-md text-grey')
        # Single Picks Profit & Balance chart
        perf_single = get_weekly_profit_and_balance(start_balance=1000.0, stake=100.0)
        with ui.card().classes('w-full q-mt-lg shadow-lg'):
            ui.label('Weekly Profit, Wagered & Rolling Balance – Single Picks ($100 stake, start $1000)').classes('text-h6 q-pa-md')
            if perf_single['weeks']:
                opts_single = {
                    'tooltip': {'trigger': 'axis'},
                    'legend': {'data': ['Amount Wagered', 'Weekly Profit', 'Rolling Balance', 'Cumulative ROI %']},
                    'xAxis': {'type': 'category', 'data': perf_single['weeks']},
                    'yAxis': [
                        {'type': 'value', 'name': 'Profit / Wagered', 'position': 'left'},
                        {'type': 'value', 'name': 'Balance', 'position': 'right'},
                        {'type': 'value', 'name': 'ROI %', 'position': 'right', 'offset': 60, 'axisLabel': {'formatter': '{value}%'}}
                    ],
                    'series': [
                        {'name': 'Amount Wagered', 'type': 'bar', 'data': perf_single.get('weekly_wagered', []), 'itemStyle': {'color': COLORS['accent']}, 'barGap': '10%'},
                        {'name': 'Weekly Profit', 'type': 'bar', 'data': perf_single['weekly_profit'], 'itemStyle': {'color': COLORS['secondary']}},
                        {'name': 'Rolling Balance', 'type': 'line', 'yAxisIndex': 1, 'data': perf_single['rolling_balance'], 'smooth': True, 'lineStyle': {'width': 3, 'color': COLORS['primary']}},
                        {'name': 'Cumulative ROI %', 'type': 'line', 'yAxisIndex': 2, 'data': perf_single.get('cumulative_roi', []), 'smooth': True, 'lineStyle': {'width': 2, 'type': 'dashed', 'color': '#607d8b'}, 'areaStyle': {'opacity': 0.05}}
                    ]
                }
                ui.echart(options=opts_single).classes('w-full').style('height:360px;')
            else:
                ui.label('No completed single-pick results to compute profit.').classes('q-pa-md text-grey')
        # Teasers Profit & Balance chart
        perf_teaser = get_teaser_weekly_profit_and_balance(start_balance=1000.0, stake_per_combo=100.0, sizes=(2,3,4))
        with ui.card().classes('w-full q-mt-lg shadow-lg'):
            ui.label('Weekly Profit, Wagered & Rolling Balance – Teasers (2–4 leg, static odds, $100 per combo, start $1000)').classes('text-h6 q-pa-md')
            if perf_teaser['weeks']:
                opts_teaser = {
                    'tooltip': {'trigger': 'axis'},
                    'legend': {'data': ['Amount Wagered', 'Weekly Profit', 'Rolling Balance', 'Cumulative ROI %']},
                    'xAxis': {'type': 'category', 'data': perf_teaser['weeks']},
                    'yAxis': [
                        {'type': 'value', 'name': 'Profit / Wagered', 'position': 'left'},
                        {'type': 'value', 'name': 'Balance', 'position': 'right'},
                        {'type': 'value', 'name': 'ROI %', 'position': 'right', 'offset': 60, 'axisLabel': {'formatter': '{value}%'}}
                    ],
                    'series': [
                        {'name': 'Amount Wagered', 'type': 'bar', 'data': perf_teaser.get('weekly_wagered', []), 'itemStyle': {'color': COLORS['accent']}, 'barGap': '10%'},
                        {'name': 'Weekly Profit', 'type': 'bar', 'data': perf_teaser['weekly_profit'], 'itemStyle': {'color': COLORS['secondary']}},
                        {'name': 'Rolling Balance', 'type': 'line', 'yAxisIndex': 1, 'data': perf_teaser['rolling_balance'], 'smooth': True, 'lineStyle': {'width': 3, 'color': COLORS['primary']}},
                        {'name': 'Cumulative ROI %', 'type': 'line', 'yAxisIndex': 2, 'data': perf_teaser.get('cumulative_roi', []), 'smooth': True, 'lineStyle': {'width': 2, 'type': 'dashed', 'color': '#455a64'}, 'areaStyle': {'opacity': 0.05}}
                    ]
                }
                ui.echart(options=opts_teaser).classes('w-full').style('height:360px;')
                # Teaser combo summary table
                detail = perf_teaser.get('detail', {})
                summary_rows = []
                start_bankroll = 1000.0
                for idx, wk in enumerate(perf_teaser['weeks']):
                    wk_detail = detail.get(wk, {})
                    summ = wk_detail.get('summary', {})
                    weekly_profit = perf_teaser['weekly_profit'][idx]
                    rolling_balance = perf_teaser['rolling_balance'][idx]
                    weekly_return_pct = (weekly_profit / start_bankroll * 100.0) if start_bankroll else 0.0
                    amount_wagered = perf_teaser.get('weekly_wagered', [])[idx] if perf_teaser.get('weekly_wagered') else 0.0
                    summary_rows.append({
                        'Week': wk,
                        'Winning_Legs': summ.get('winning_legs',''),
                        'Total_Legs': summ.get('legs',''),
                        'Winning_Combos': summ.get('winning_combos',''),
                        'Total_Combos': summ.get('total_combos',''),
                        'Combo_Win_Ratio': summ.get('win_ratio',''),
                        'Amount_Wagered': f"${amount_wagered:,.2f}",
                        'Weekly_Profit': f"${weekly_profit:,.2f}",
                        'Rolling_Balance': f"${rolling_balance:,.2f}",
                        'Return_Percent': f"{weekly_return_pct:.2f}%"
                    })
                if summary_rows:
                    ui.label('Teaser Leg / Combo Summary').classes('text-subtitle2 q-mt-md q-mb-sm')
                    columns_summary = [
                        {'name': 'Week', 'label': 'Week', 'field': 'Week'},
                        {'name': 'Winning_Legs', 'label': 'Winning Legs', 'field': 'Winning_Legs'},
                        {'name': 'Total_Legs', 'label': 'Total Legs', 'field': 'Total_Legs'},
                        {'name': 'Winning_Combos', 'label': 'Winning Combos', 'field': 'Winning_Combos'},
                        {'name': 'Total_Combos', 'label': 'Total Combos', 'field': 'Total_Combos'},
                        {'name': 'Combo_Win_Ratio', 'label': 'Combo Win Ratio', 'field': 'Combo_Win_Ratio'},
                        {'name': 'Amount_Wagered', 'label': 'Amount Wagered', 'field': 'Amount_Wagered'},
                        {'name': 'Weekly_Profit', 'label': 'Weekly Profit', 'field': 'Weekly_Profit'},
                        {'name': 'Rolling_Balance', 'label': 'Rolling Balance', 'field': 'Rolling_Balance'},
                        {'name': 'Return_Percent', 'label': 'Return % (of $1000)', 'field': 'Return_Percent'},
                    ]
                    ui.table(columns=columns_summary, rows=summary_rows, row_key='Week').props('dense bordered').classes('w-full q-mb-md')
            else:
                ui.label('No completed teaser results to compute profit.').classes('q-pa-md text-grey')
    return dashboard
