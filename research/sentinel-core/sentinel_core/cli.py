"""CLI: python -m sentinel_core.cli analyze|backtest --symbol ETHUSDT."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
import sys
import time
from .core import Strategy, decide, backtest
from .data import BinancePublic, MarketDataError


def main() -> int:
    parser = argparse.ArgumentParser(description="Sentinel read-only/paper backtest")
    parser.add_argument("mode", choices=("analyze", "backtest", "contracts"))
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--limit", type=int, default=1500)
    args = parser.parse_args()
    try:
        client = BinancePublic()
        if args.mode == "contracts":
            print(json.dumps({"contracts": client.contracts(),
                              "source": "Binance USD-M"}, ensure_ascii=False))
            return 0
        if args.symbol not in client.contracts():
            raise ValueError("Contrato não listado como perpétuo USDT em negociação")
        now_ms = int(time.time()*1000)
        fast = client.klines(args.symbol, "15m", args.limit, now_ms=now_ms)
        trend = client.klines(args.symbol, "1h", min(args.limit, 1500), now_ms=now_ms)
        btc = client.klines("BTCUSDT", "1h", min(args.limit, 1500), now_ms=now_ms)
        if args.mode == "analyze":
            ticker = client.ticker24(args.symbol)
            at = fast[-1].close_time if fast else now_ms
            signal = decide(fast, trend, btc, at, ticker["change_pct_24h"])
            output = {
                "mode": "read_only", "symbol": args.symbol,
                "source": "Binance USD-M Futures public REST",
                "last_closed_15m_ms": at if fast else None,
                "data_counts": {"15m": len(fast), "1h": len(trend), "btc_1h": len(btc)},
                "ticker": ticker, "signal": asdict(signal) if signal else None,
                "status": "signal" if signal else "no_signal_or_insufficient_data",
            }
        else:
            output = {
                "mode": "paper_backtest", "symbol": args.symbol,
                "source": "Binance USD-M Futures public historical klines",
                "window": {"bars_15m": len(fast), "bars_1h": len(trend),
                           "bars_btc_1h": len(btc)},
                "result": backtest(fast, trend, btc, Strategy()),
            }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (MarketDataError, ValueError, IndexError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc),
                          "data_fabricated": False}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
