"""Avaliação walk-forward, sem rede e sem ordens.

Exemplo:
  python -m sentinel_core.walkforward_cli --symbol ETHUSDT \
    --start 2026-09-01 --end 2026-10-15 --db data/sentinel.sqlite
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

from .data import _symbol
from .history import MarketStore
from .walkforward import evaluate_walk_forward


def _day(s: str) -> int:
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()*1000)


def main() -> int:
    p = argparse.ArgumentParser(description="Sentinel v0.3 walk-forward sem trades reais")
    p.add_argument("--symbol", required=True)
    p.add_argument("--start", required=True, help="YYYY-MM-DD UTC incluído")
    p.add_argument("--end", required=True, help="YYYY-MM-DD UTC excluído")
    p.add_argument("--db", default="data/sentinel.sqlite")
    p.add_argument("--train-days", type=int, default=10)
    p.add_argument("--warmup-days", type=int, default=9)
    p.add_argument("--test-days", type=int, default=3)
    p.add_argument("--folds", type=int, default=3)
    p.add_argument("--omit-funding", action="store_true")
    p.add_argument("--report", help="Exportar JSON completo local (não commitar)")
    a = p.parse_args()
    try:
        symbol = _symbol(a.symbol)
        start, end = _day(a.start), _day(a.end)
        if start >= end:
            raise ValueError("Período inválido")
        for val in (a.train_days,a.warmup_days,a.test_days):
            if not (1 <= val <= 120):
                raise ValueError("Parâmetros de dias devem ser 1..120")
        if not (1 <= a.folds <= 24):
            raise ValueError("Número de folds inválido")
        with MarketStore(a.db) as store:
            fast = store.get_candles(symbol,"15m",start,end)
            h = store.get_candles(symbol,"1h",start,end)
            btc = store.get_candles("BTCUSDT","1h",start,end)
            funding = (None if a.omit_funding
                       else store.get_funding(symbol,start,end))
            result = evaluate_walk_forward(
                fast,h,btc,funding_events=funding,
                train_bars=a.train_days*96,
                warmup_bars=a.warmup_days*96,
                test_bars=a.test_days*96,
                folds=a.folds,
            )
        overall = result["walk_forward"]
        brief = {
            "status":"evaluated_simulation_not_live",
            "symbol":symbol, "source":"locally validated SQLite public Binance OHLCV",
            "strategy_sha256":result["strategy_sha256"],
            "funding_coverage":result["funding_coverage"],
            "fold_count":overall["folds"],
            "total_oos_trades":overall["out_of_sample_total_trades"],
            "oos_compounded_return_pct":overall["out_of_sample_compounded_return_pct"],
            "positive_folds":overall["out_of_sample_positive_folds"],
            "too_few_trades":not overall["out_of_sample_trades_enough_for_statistical_claim"],
            "folds":[{"fold":f["fold"],
                      "start_ms":f["test_start_ms"],
                      "end_exclusive_ms":f["test_end_exclusive_ms"],
                      "trades":f["test"]["trades"],
                      "return_pct":f["test"]["return_pct"],
                      "drawdown_bound_pct":f["test"]["max_conservative_intrabar_drawdown_pct"],
                      "buy_hold_pct_no_funding":f["test_benchmarks"]["buy_hold"],
                      "short_hold_pct_no_funding":f["test_benchmarks"]["short_hold"]}
                     for f in overall["results"]],
            "warning":"Pesquisa quantitativa; NÃO demonstra lucro futuro. Nenhuma ordem real.",
        }
        if a.report:
            target = Path(a.report).expanduser()
            if target.exists():
                raise ValueError("O relatório de destino já existe")
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(result,ensure_ascii=False,indent=2),
                              encoding="utf-8")
            brief["full_report_path"]=str(target)
        print(json.dumps(brief,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,TypeError,sqlite3.Error,OSError) as exc:
        print(json.dumps({"status":"error_no_fabricated_results",
                          "error":str(exc)},ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
