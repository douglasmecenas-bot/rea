"""Histórico auditável SQLite + paginação limitada para Binance USD-M pública.

Nenhuma chave API, ordens, scraping de terceiros ou geração de preços sintéticos.
Exige candles consecutivos para evitar resultados enganosos com gaps.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from math import isfinite
import json
import sqlite3
import time
from pathlib import Path

from .core import Candle
from .data import BinancePublic, MarketDataError, _symbol, VALID_INTERVALS

INTERVAL_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000,
               "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}


@dataclass(frozen=True)
class FundingEvent:
    funding_time: int
    rate: float
    mark_price: float

    def __post_init__(self):
        if (not isinstance(self.funding_time, int) or self.funding_time < 0
                or not isfinite(self.rate) or not isfinite(self.mark_price)
                or self.mark_price <= 0):
            raise ValueError("Funding rate/markPrice inválidos")


def validate_series(candles: list[Candle], interval: str,
                    require_contiguous: bool = True) -> dict:
    if interval not in INTERVAL_MS:
        raise ValueError("Intervalo não suportado")
    step = INTERVAL_MS[interval]
    gaps = []
    for i, c in enumerate(candles):
        if c.open_time % step or c.close_time != c.open_time + step - 1:
            raise ValueError("Timestamp de candle não corresponde ao intervalo UTC")
        if i > 0:
            delta = c.open_time - candles[i-1].open_time
            if delta <= 0 or delta % step:
                raise ValueError("Timestamp duplicado/desordenado")
            if delta > step:
                gaps.append({"after": candles[i-1].open_time,
                             "before": c.open_time, "missing": delta//step-1})
    if gaps and require_contiguous:
        raise ValueError(f"Dataset contém {len(gaps)} gaps; backtest recusado")
    packed = json.dumps([asdict(c) for c in candles],
                        separators=(",", ":"), sort_keys=True)
    return {"candles": len(candles),
            "first_open_ms": candles[0].open_time if candles else None,
            "last_open_ms": candles[-1].open_time if candles else None,
            "gaps": gaps, "sha256": sha256(packed.encode()).hexdigest()}


def backfill_candles(client: BinancePublic, symbol: str, interval: str,
                     start_ms: int, end_ms: int, *,
                     page_size: int = 500, max_pages: int = 100,
                     now_ms: int | None = None) -> list[Candle]:
    """[start_ms,end_ms), exige intervalo alinhado e cobertura 100%.

    Janela explícita em cada página evita perder o começo se o servidor
    priorizar as velas mais recentes ao receber startTime+endTime.
    """
    _symbol(symbol)
    if interval not in VALID_INTERVALS:
        raise ValueError("Intervalo inválido")
    step = INTERVAL_MS[interval]
    now = int(time.time()*1000) if now_ms is None else now_ms
    if (not isinstance(start_ms, int) or not isinstance(end_ms, int)
            or start_ms < 0 or end_ms <= start_ms or end_ms > now
            or start_ms % step or end_ms % step):
        raise ValueError("Janela inválida: use timestamps UTC alinhados de velas FECHADAS")
    if not (1 <= page_size <= 1500 and 1 <= max_pages <= 500):
        raise ValueError("Limites de paginação inválidos")
    expected_pages = (end_ms-start_ms + page_size*step - 1)//(page_size*step)
    if expected_pages > max_pages:
        raise ValueError("Janela maior que max_pages; divida a coleta")
    output: list[Candle] = []
    cursor = start_ms
    for _ in range(max_pages):
        if cursor >= end_ms:
            break
        page_end_exclusive = min(end_ms, cursor + page_size*step)
        rows = client.klines(symbol, interval, limit=page_size,
                             start_ms=cursor, end_ms=page_end_exclusive-1,
                             now_ms=now)
        if not rows:
            raise MarketDataError(f"Sem candles em {cursor}; cobertura incompleta")
        expected_count = (page_end_exclusive-cursor)//step
        if len(rows) != expected_count or rows[0].open_time != cursor:
            raise MarketDataError(f"Página incompleta em {cursor}; esperado {expected_count}, recebido {len(rows)}")
        validate_series(rows, interval)
        output.extend(rows)
        cursor = page_end_exclusive
    if cursor != end_ms:
        raise MarketDataError("Paginação terminou sem cobrir a janela")
    validate_series(output, interval)
    return output


def backfill_funding(client: BinancePublic, symbol: str,
                     start_ms: int, end_ms: int, *,
                     max_pages: int = 30, page_size: int = 500) -> list[FundingEvent]:
    """Funding timestamp inclusivo/exclusivo. Ausência de evento ≠ prova de zero."""
    _symbol(symbol)
    if not (isinstance(start_ms, int) and isinstance(end_ms, int)
            and 0 <= start_ms < end_ms):
        raise ValueError("Janela funding inválida")
    if not (1 <= page_size <= 1000 and 1 <= max_pages <= 100):
        raise ValueError("Paginação funding inválida")
    output: list[FundingEvent] = []
    cursor = start_ms
    for _ in range(max_pages):
        raw = client.funding_rates(symbol, cursor, end_ms-1, limit=page_size)
        if not raw:
            return output
        page = []
        for record in raw:
            if record.get("symbol") != symbol:
                raise MarketDataError("Símbolo funding inconsistente")
            event = FundingEvent(int(record["fundingTime"]),
                                 float(record["fundingRate"]),
                                 float(record["markPrice"]))
            if not (cursor <= event.funding_time < end_ms):
                raise MarketDataError("Funding fora da janela solicitada")
            page.append(event)
        if any(page[i].funding_time >= page[i+1].funding_time
               for i in range(len(page)-1)):
            raise MarketDataError("Funding duplicado ou desordenado")
        output.extend(page)
        cursor = page[-1].funding_time+1
        if len(page) < page_size:
            return output
    raise MarketDataError("Funding excedeu max_pages; dados incompletos")


class MarketStore:
    """SQLite local; conflito de bytes numéricos não é sobrescrito silenciosamente."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS candles(
             symbol TEXT NOT NULL, interval TEXT NOT NULL,
             open_time INTEGER NOT NULL, close_time INTEGER NOT NULL,
             open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL,
             close REAL NOT NULL, volume REAL NOT NULL,
             PRIMARY KEY(symbol, interval, open_time))
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS funding(
             symbol TEXT NOT NULL, funding_time INTEGER NOT NULL,
             rate REAL NOT NULL, mark_price REAL NOT NULL,
             PRIMARY KEY(symbol, funding_time))
        """)

    def __enter__(self):
        return self

    def __exit__(self, typ, val, tb):
        self.db.close()

    def put_candles(self, symbol: str, interval: str, candles: list[Candle]):
        _symbol(symbol)
        validate_series(candles, interval)
        with self.db:
            for c in candles:
                prior = self.db.execute(
                    "SELECT close_time,open,high,low,close,volume FROM candles "
                    "WHERE symbol=? AND interval=? AND open_time=?",
                    (symbol, interval, c.open_time)).fetchone()
                record = (c.close_time,c.open,c.high,c.low,c.close,c.volume)
                if prior is not None:
                    if tuple(prior) != record:
                        raise ValueError(f"Conflito histórico: {symbol} {interval} {c.open_time}")
                    continue
                self.db.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?)",
                                (symbol,interval,c.open_time,*record))

    def get_candles(self, symbol: str, interval: str, start_ms: int, end_ms: int,
                    require_complete: bool = True) -> list[Candle]:
        _symbol(symbol)
        if interval not in INTERVAL_MS or end_ms <= start_ms:
            raise ValueError("Seleção inválida")
        rows = self.db.execute(
            "SELECT open_time,close_time,open,high,low,close,volume FROM candles "
            "WHERE symbol=? AND interval=? AND open_time>=? AND open_time<? "
            "ORDER BY open_time", (symbol,interval,start_ms,end_ms)).fetchall()
        candles = [Candle(*row) for row in rows]
        validate_series(candles, interval)
        if require_complete:
            expected = (end_ms-start_ms)//INTERVAL_MS[interval]
            if (start_ms%INTERVAL_MS[interval] or end_ms%INTERVAL_MS[interval]
                    or len(candles) != expected or not candles
                    or candles[0].open_time != start_ms
                    or candles[-1].open_time != end_ms-INTERVAL_MS[interval]):
                raise ValueError("Janela SQLite não possui cobertura contínua integral")
        return candles

    def put_funding(self, symbol: str, events: list[FundingEvent]):
        _symbol(symbol)
        if any(events[i].funding_time >= events[i+1].funding_time
               for i in range(len(events)-1)):
            raise ValueError("Eventos funding desordenados")
        with self.db:
            for event in events:
                record = (event.rate,event.mark_price)
                prior = self.db.execute(
                    "SELECT rate,mark_price FROM funding WHERE symbol=? AND funding_time=?",
                    (symbol,event.funding_time)).fetchone()
                if prior is not None:
                    if tuple(prior) != record:
                        raise ValueError("Conflito de funding registrado")
                    continue
                self.db.execute("INSERT INTO funding VALUES (?,?,?,?)",
                                (symbol,event.funding_time,*record))

    def get_funding(self, symbol: str, start_ms: int, end_ms: int) -> list[FundingEvent]:
        _symbol(symbol)
        rows = self.db.execute(
            "SELECT funding_time,rate,mark_price FROM funding "
            "WHERE symbol=? AND funding_time>=? AND funding_time<? ORDER BY funding_time",
            (symbol,start_ms,end_ms)).fetchall()
        return [FundingEvent(*row) for row in rows]
