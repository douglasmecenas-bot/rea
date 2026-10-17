"""Replay de alertas em duas etapas com SQLite local, SEM mensagens externas."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

from .data import _symbol
from .history import MarketStore
from .alerts import replay_events


def _date(s):
    parsed=datetime.fromisoformat(s)
    if parsed.tzinfo is None:
        parsed=parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp()*1000)


def main():
    p=argparse.ArgumentParser(description="Sentinel offline signal events replay")
    p.add_argument("--symbol",required=True)
    p.add_argument("--start",required=True,help="YYYY-MM-DD UTC")
    p.add_argument("--end",required=True,help="YYYY-MM-DD UTC (exclusivo)")
    p.add_argument("--db",default="data/sentinel.sqlite")
    p.add_argument("--out",help="Salvar JSON novo em runs/ (sem credenciais)")
    a=p.parse_args()
    try:
        symbol=_symbol(a.symbol)
        start,end=_date(a.start),_date(a.end)
        if start>=end:
            raise ValueError("Intervalo inválido")
        with MarketStore(a.db) as store:
            f=store.get_candles(symbol,"15m",start,end)
            h=store.get_candles(symbol,"1h",start,end)
            b=store.get_candles("BTCUSDT","1h",start,end)
        report=replay_events(symbol,f,h,b)
        if a.out:
            target=Path(a.out)
            if target.exists():
                raise ValueError("Arquivo já existe")
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(report,ensure_ascii=False,indent=2),
                              encoding="utf-8")
        # Saída resumida; eventos completos apenas no arquivo opcional.
        print(json.dumps({
          "mode":report["mode"],"symbol":symbol,
          "count":report["event_count"],
          "by_type":{k:sum(e["event_type"]==k for e in report["events"])
                     for k in ("PRELIMINARY","CONFIRMED","INVALIDATED","EXPIRED")},
          "pending_at_end":report["pending_at_end"],
          "trading_enabled":False,
        },ensure_ascii=False,indent=2))
        return 0
    except (ValueError,TypeError,OSError,sqlite3.Error) as exc:
        print(json.dumps({"error":str(exc),"fabricated_signals":False},
                         ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
