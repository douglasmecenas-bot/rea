"""Sentinel Core: pesquisa quantitativa somente leitura; nunca executa ordens."""
from .core import Candle, Strategy, Signal, indicators, decide, backtest

__all__ = ["Candle", "Strategy", "Signal", "indicators", "decide", "backtest"]
