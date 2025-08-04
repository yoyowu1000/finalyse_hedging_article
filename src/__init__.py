"""Liability Hedging Library

A professional implementation for hedging liability cashflows using fixed-income portfolios.
"""

from .models import Liability, Bond, YieldCurve
from .optimizer import HedgingOptimizer
from .analyzer import HedgingAnalyzer

__version__ = "1.0.0"
__all__ = ["Liability", "Bond", "YieldCurve", "HedgingOptimizer", "HedgingAnalyzer"]