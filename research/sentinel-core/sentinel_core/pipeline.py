"""CLI histórico e avaliação auditável, executada LOCALMENTE, sem ordens.

Uso:
 python -m sentinel_core.pipeline collect --symbol ETHUSDT --start 2026-09-01 --end 2026-10-01
 python -m sentinel_core.pipeline evaluate --symbol ETHUSDT --start 2026-09-01 --end 2026-10-01
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone
import json
from pathlib import Path
import sqlite3
import sys

from .data import BinancePublic, MarketDataError, _symbol
from .history import (MarketStore, INTERVAL_MS, backfill_candles,
                      backfill_funding, validate_series)
from .simulator import simulate, chronological_holdout


def _timestamp(value: str) -> int:
    day=date.fromisoformat(value)
    return int(datetime.combine(day,time.min,tzinfo=timezone.utc).timestamp()*1000)


def main() -> int:
    parser=argparse.ArgumentParser(description="Sentinel v0.2: somente dados públicos/paper")
    sub=parser.add_subparsers(dest="mode",required=True)
    for mode in ("collect","evaluate"):
        p=sub.add_parser(mode)
        p.add_argument("--symbol",required=True,help="Ex.: ETHUSDT")
        p.add_argument("--start",required=True,help="AAAA-MM-DD UTC inclusivo")
        p.add_argument("--end",required=True,help="AAAA-MM-DD UTC EXCLUSIVO")
        p.add_argument("--db",default="data/sentinel.sqlite")
        if mode=="collect":
            p.add_argument("--max-pages",type=int,default=40)
        if mode=="evaluate":
            p.add_argument("--train-fraction",type=float,default=.7)
            p.add_argument("--omit-funding",action="store_true",
                           help="Não usar funding; resultado SEM financiamento")
            p.add_argument("--output",help="Caminho JSON privado/local (não commitar)")
    args=parser.parse_args()
    try:
        symbol=_symbol(args.symbol)
        start=_timestamp(args.start)
        end=_timestamp(args.end)
        if start >= end:
            raise ValueError("End deve ser posterior ao start")
        path=Path(args.db).expanduser()
        path.parent.mkdir(parents=True,exist_ok=True)
        with MarketStore(path) as store:
            if args.mode=="collect":
                client=BinancePublic()
                if symbol not in client.contracts():
                    raise ValueError("Símbolo não está disponível como contrato perpétuo USDT")
                series=[(symbol,"15m"),(symbol,"1h")]
                if symbol!="BTCUSDT":
                    series.append(("BTCUSDT","1h"))
                summaries=[]
                for sym,interval in series:
                    bars=backfill_candles(client,sym,interval,start,end,
                                          max_pages=args.max_pages)
                    store.put_candles(sym,interval,bars)
                    verify=store.get_candles(sym,interval,start,end)
                    summary=validate_series(verify,interval)
                    summaries.append({"symbol":sym,"interval":interval,**summary})
                fund=backfill_funding(client,symbol,start,end)
                store.put_funding(symbol,fund)
                result={
                    "mode":"historical_public_collection",
                    "source":"Binance public USD-M Futures REST",
                    "range_start_inclusive_ms":start,"range_end_exclusive_ms":end,
                    "database":str(path),"series":summaries,
                    "funding_events":len(fund),
                    "funding_completeness":"not_verified_from_schedule",
                    "trading_enabled":False,
                }
            else:
                fast=store.get_candles(symbol,"15m",start,end)
                hour=store.get_candles(symbol,"1h",start,end)
                btc=store.get_candles("BTCUSDT","1h",start,end)
                funding=(None if args.omit_funding
                         else store.get_funding(symbol,start,end))
                summary=chronological_holdout(
                    fast,hour,btc,funding_events=funding,
                    train_fraction=args.train_fraction)
                result={
                    "mode":"offline_holdout", "symbol":symbol,
                    "range_start_inclusive_ms":start,
                    "range_end_exclusive_ms":end,
                    "series_hashes":{
                        "15m":validate_series(fast,"15m")["sha256"],
                        "1h":validate_series(hour,"1h")["sha256"],
                        "btc_1h":validate_series(btc,"1h")["sha256"],
                    },
                    "trading_enabled":False,
                    "funding_notice":(
                       "Excluded by explicit --omit-funding"
                       if args.omit_funding else
                       "Events read from local DB; full funding coverage NOT independently verified"),
                    "evaluation":summary,
                }
                if args.output:
                    dest=Path(args.output).expanduser()
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    if dest.exists():
                        raise ValueError("Arquivo de saída existente; escolha outro nome")
                    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),
                                    encoding="utf-8")
            print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,MarketDataError,sqlite3.Error,OSError,KeyError,TypeError) as exc:
        print(json.dumps({"status":"error","reason":str(exc),"fabricated_data":False},
                         ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
