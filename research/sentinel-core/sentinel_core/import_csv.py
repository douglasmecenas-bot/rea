"""Importação OFFLINE de CSV autorizado para contornar dependência de rede.

É alternativa para dados já obtidos legalmente pelo usuário, não mecanismo para
evadir controles de acesso. Proveniência declarada NÃO autentica o fornecedor.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys

from .core import Candle
from .data import _symbol, VALID_INTERVALS
from .history import FundingEvent, MarketStore, validate_series

MAX_BYTES = 64_000_000
MAX_ROWS = 200_000
CANDLE_FIELDS = {
    "open_time", "close_time", "open", "high", "low", "close", "volume"
}
FUNDING_FIELDS = {"funding_time", "rate", "mark_price"}


def read_csv(path: str | Path, kind: str, symbol: str,
             interval: str | None = None) -> tuple[list, dict]:
    _symbol(symbol)
    src = Path(path)
    if kind not in ("candles", "funding"):
        raise ValueError("kind inválido")
    if kind == "candles" and interval not in VALID_INTERVALS:
        raise ValueError("Intervalo inválido")
    if not src.is_file() or src.stat().st_size > MAX_BYTES:
        raise ValueError("Arquivo não encontrado ou excede 64 MB")
    digest = sha256()
    with src.open("rb") as inp:
        while True:
            chunk = inp.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    records = []
    with src.open("r", newline="", encoding="utf-8-sig") as inp:
        reader = csv.DictReader(inp)
        required = CANDLE_FIELDS if kind == "candles" else FUNDING_FIELDS
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("Cabeçalhos CSV ausentes: " + ",".join(sorted(required)))
        for row in reader:
            if len(records) >= MAX_ROWS:
                raise ValueError("CSV excede limite de linhas")
            if None in row:
                raise ValueError("Linha com colunas extras")
            if row.get("symbol") and row["symbol"] != symbol:
                raise ValueError("CSV contém ativo diferente do selecionado")
            if kind == "candles":
                if row.get("interval") and row["interval"] != interval:
                    raise ValueError("CSV contém intervalo diferente")
                record = Candle(
                    open_time=int(row["open_time"]),
                    close_time=int(row["close_time"]),
                    open=float(row["open"]), high=float(row["high"]),
                    low=float(row["low"]), close=float(row["close"]),
                    volume=float(row["volume"]))
            else:
                record = FundingEvent(
                    funding_time=int(row["funding_time"]),
                    rate=float(row["rate"]),
                    mark_price=float(row["mark_price"]))
            records.append(record)
    if not records:
        raise ValueError("CSV sem dados")
    if kind == "candles":
        coverage = validate_series(records, interval, require_contiguous=True)
    else:
        for i in range(len(records)-1):
            if records[i].funding_time >= records[i+1].funding_time:
                raise ValueError("Funding duplicado/desordenado")
        coverage = {
            "events":len(records),
            "first_ms":records[0].funding_time,
            "last_ms":records[-1].funding_time,
            "funding_schedule_completeness":"unverified"
        }
    return records, {
        "mode":"read_only_csv_import",
        "symbol":symbol, "interval":interval if kind=="candles" else None,
        "kind":kind, "csv_sha256":digest.hexdigest(),
        "csv_bytes":src.stat().st_size,
        "source_authenticity":"NOT_VERIFIED_user_supplied_CSV",
        **coverage,
    }


def main() -> int:
    p=argparse.ArgumentParser(description="Importar CSV local com origem declarada")
    p.add_argument("kind",choices=("candles","funding"))
    p.add_argument("--file",required=True)
    p.add_argument("--symbol",required=True)
    p.add_argument("--interval",choices=sorted(VALID_INTERVALS))
    p.add_argument("--db",default="data/sentinel.sqlite")
    a=p.parse_args()
    try:
        data,report=read_csv(a.file,a.kind,a.symbol,a.interval)
        dest=Path(a.db).expanduser()
        dest.parent.mkdir(parents=True,exist_ok=True)
        with MarketStore(dest) as store:
            if a.kind=="candles":
                store.put_candles(a.symbol,a.interval,data)
                # Ler de volta para verificar persistência real.
                store.get_candles(a.symbol,a.interval,data[0].open_time,
                                  data[-1].close_time+1)
            else:
                store.put_funding(a.symbol,data)
                persisted=store.get_funding(a.symbol,data[0].funding_time,
                                             data[-1].funding_time+1)
                if persisted != data:
                    raise ValueError("Funding persistido não corresponde à entrada")
        print(json.dumps(report,indent=2,ensure_ascii=False))
        return 0
    except (ValueError,OSError,sqlite3.Error,TypeError,UnicodeError,csv.Error) as exc:
        print(json.dumps({"status":"error_no_fabricated_data",
                          "reason":str(exc)},ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
