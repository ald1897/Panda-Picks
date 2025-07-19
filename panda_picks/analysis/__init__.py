# Import modules from this subpackage
from . import picks, backtest, bets, spreads

# Expose specific functions if needed
from .picks import makePicks
from .backtest import backtest
from .bets import adjust_spread
from .spreads import main as create_spreads


__all__ = ['picks', 'backtest', 'bets', 'spreads', 'makePicks', 'spreads.py']