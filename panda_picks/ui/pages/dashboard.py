from nicegui import ui
from ..data import calculate_win_rates, get_total_picks, get_upcoming_games, get_win_rate_trend, get_teaser_weekly_profit_and_balance, COLORS

def register(router):
    @router.add('/dashboard')
    def dashboard():
        ui.label('Dashboard').classes('text-h4 q-mb-lg')
        # Win Rate Trend (straight lines only now)
        trend = get_win_rate_trend()
        with ui.card().classes('w-full q-mt-lg shadow-lg'):
            ui.label('Weekly ATS Win Rate Trend (pushes excluded, straight lines)').classes('text-h6 q-pa-md')
            if trend['weeks']:
                opts = {
                    'tooltip': {'trigger': 'axis'},
                    'xAxis': {'type': 'category', 'data': trend['weeks']},
                    'yAxis': {'type': 'value', 'min': 0, 'max': 100, 'axisLabel': {'formatter': '{value}%'}},
                    'series': [{
                        'name': 'ATS Win Rate', 'type': 'line', 'data': trend['win_rates'],
                        'smooth': True, 'lineStyle': {'width': 3, 'color': COLORS['primary']},
                        'areaStyle': {'color': 'rgba(72,135,43,0.15)'}
                    }]
                }
                ui.echart(options=opts).classes('w-full').style('height:300px;')
            else:
                ui.label('No historical picks to display.').classes('q-pa-md text-grey')
        # Teaser profit chart & wins/losses remain unchanged below
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
            else:
                ui.label('No completed teaser results to compute profit.').classes('q-pa-md text-grey')
        if perf_teaser.get('weeks'):
            weeks = perf_teaser['weeks']
            detail = perf_teaser.get('detail', {})
            wins_series = []
            losses_series = []
            for wk in weeks:
                wk_detail = detail.get(wk, {})
                total_wins = 0
                total_losses = 0
                for size_key in (2,3,4):
                    size_stats = wk_detail.get(size_key)
                    if size_stats:
                        total_wins += size_stats.get('wins', 0)
                        total_losses += size_stats.get('losses', 0)
                wins_series.append(total_wins)
                losses_series.append(total_losses)
            with ui.card().classes('w-full q-mt-md shadow-lg'):
                ui.label('Weekly Teaser Combo Wins vs Losses (All Sizes Aggregated)').classes('text-h6 q-pa-md')
                bar_opts = {
                    'tooltip': {'trigger': 'axis'},
                    'legend': {'data': ['Wins', 'Losses']},
                    'xAxis': {'type': 'category', 'data': weeks},
                    'yAxis': {'type': 'value', 'name': 'Combos'},
                    'series': [
                        {'name': 'Wins', 'type': 'bar', 'data': wins_series, 'itemStyle': {'color': COLORS['primary']}},
                        {'name': 'Losses', 'type': 'bar', 'data': losses_series, 'itemStyle': {'color': '#d32f2f'}},
                    ]
                }
                ui.echart(options=bar_opts).classes('w-full').style('height:300px;')
    return dashboard
