"""Fantasy Football WAR (Wins Above Replacement) Calculator.

A modern Python implementation of Fantasy Football WAR calculations
with support for MPPR (Minus PPR) scoring and Individual Defense Players (IDP).
"""

__version__ = "0.1.0"
__author__ = "Christian Lohr"
__email__ = "your.email@example.com"

from fantasy_war.config.settings import Settings
from fantasy_war.config.leagues import LeagueConfig

__all__ = [
    "Settings", 
    "LeagueConfig",
    "__version__",
]