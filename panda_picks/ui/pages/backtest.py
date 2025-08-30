from nicegui import ui
from ..data import run_backtest, COLORS

def register(router):
    @router.add('/backtest')
    def backtest_page():
        ui.label('Backtest Betting Strategies').classes('text-h4 q-mb-lg')
        results_card = ui.card().classes('w-full shadow-lg q-mb-lg')
        chart_card = ui.card().classes('w-full shadow-lg')
        def update_backtest_results(strategy: str):
            data = run_backtest(strategy)
            results_card.clear()
            with results_card:
                ui.label('Backtest Results').classes('text-h6 q-pa-md')
                with ui.row().classes('q-pa-md w-full justify-around'):
                    for metric, value in data['metrics'].items():
                        with ui.column().classes('items-center'):
                            ui.label(metric.replace('_',' ').title()).classes('text-subtitle1')
                            ui.label(value).classes('text-h5 text-weight-bold')
            chart_card.clear()
            with chart_card:
                ui.label('Profit Over Time').classes('text-h6 q-pa-md')
                if data['chart_data']:
                    with ui.matplotlib(figsize=(8, 4)).classes('w-full') as profit_chart:
                        fig = profit_chart.figure
                        ax = fig.add_subplot(111)
                        games = [d['game'] for d in data['chart_data']]
                        profits = [d['profit'] for d in data['chart_data']]
                        ax.plot(games, profits, marker='o', linewidth=2, color=COLORS['primary'])
                        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.7)
                        ax.set_xlabel('Game Number')
                        ax.set_ylabel('Profit ($)')
                        ax.set_title('Profit Over Time')
                        ax.grid(True, linestyle='--', alpha=0.7)
                        fig.tight_layout()
                else:
                    ui.html('<div style="width: 100%; height: 200px; display: flex; align-items: center; justify-content: center; color: #9e9e9e;">No data for chart.</div>').classes('w-full')
        with ui.card().classes('w-full shadow-lg q-mb-lg'):
            with ui.row().classes('w-full items-center q-pa-md'):
                strategy_select = ui.select(['Favorites', 'Underdogs', 'Home Teams'], value='Favorites', label='Select Strategy')
                ui.button('Run Backtest', on_click=lambda: update_backtest_results(strategy_select.value))
        return backtest_page
    return backtest_page

