"""Sonda mínima SOMENTE LEITURA da Binance: uso manual ou em runner GitHub.

Emite um JSON pequeno de evidência. Não persiste dados de trades nem credenciais.
Falha de acesso por rede/jurisdição = "unavailable", nunca dados inventados.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import sys
import time

from .data import BinancePublic, MarketDataError
from .history import validate_series


def probe(symbol: str = "BTCUSDT") -> dict:
    client = BinancePublic(timeout=10)
    observed_at = int(time.time() * 1000)
    try:
        candles = client.klines(symbol, "15m", limit=101, now_ms=observed_at)
        if len(candles) != 100:
            raise MarketDataError(
                f"Cobertura insuficiente: {len(candles)}/100 velas fechadas")
        meta = validate_series(candles, "15m")
        ticker = client.ticker24(symbol)
        if ticker["price"] <= 0:
            raise MarketDataError("Ticker contém preço não positivo")
        # Dado fechado mais recente não pode estar muito antigo em uma sonda live.
        age_ms = observed_at - candles[-1].close_time
        if not (0 <= age_ms <= 60 * 60 * 1000):
            raise MarketDataError("Dataset retornado está defasado")
        return {
            "status": "live_public_market_verified",
            "mode": "read_only_no_credentials",
            "source": "https://fapi.binance.com",
            "checked_at_utc": datetime.fromtimestamp(
                observed_at/1000, timezone.utc).isoformat(),
            "symbol": symbol,
            "interval": "15m",
            "count": meta["candles"],
            "first_open_ms": meta["first_open_ms"],
            "last_open_ms": meta["last_open_ms"],
            "last_close_ms": candles[-1].close_time,
            "age_ms": age_ms,
            "sha256": meta["sha256"],
            "gaps": meta["gaps"],
            "ticker_timestamp_ms": ticker["close_time_ms"],
            "executed_orders": 0,
        }
    except (MarketDataError, OSError, ValueError, KeyError, TypeError) as exc:
        return {
            "status": "unavailable_not_verified",
            "mode": "read_only_no_credentials",
            "source": "https://fapi.binance.com",
            "symbol": symbol,
            "checked_at_utc": datetime.fromtimestamp(
                observed_at/1000, timezone.utc).isoformat(),
            "reason": type(exc).__name__,
            "details": str(exc)[:400],
            "executed_orders": 0,
        }


def main() -> int:
    result = probe()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "live_public_market_verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
