"""Sentinel Research Alerts: antecipação -> confirmação/invalidação.

Usa apenas candles fechados e condições públicas. Nunca envia mensagens,
não executa ordens e não fornece recomendação financeira.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from math import isfinite

from .core import (Candle, Strategy, Signal, decide, sma_seeded_ema,
                   wilder_atr, wilder_rsi)
from .history import validate_series

HOUR = 3_600_000
STEP = 900_000


@dataclass(frozen=True)
class Event:
    event_id: str
    setup_id: str
    symbol: str
    at_ms: int
    event_type: str
    side: str
    observed_price: float
    rsi14: float
    stop: float | None
    target: float | None
    reason: str
    preliminary_seen: bool


@dataclass
class Pending:
    setup_id: str
    side: str
    at_ms: int
    index: int
    initial_price: float
    initial_atr: float


class SignalTracker:
    """Uma única oportunidade observada por ativo, TTL e cooldown declarados."""

    def __init__(self, symbol: str, *, strategy: Strategy = Strategy(),
                 ttl_bars: int = 8, cooldown_bars: int = 8):
        if not symbol or not symbol.isalnum() or symbol != symbol.upper():
            raise ValueError("Ativo inválido")
        if not (1 <= ttl_bars <= 96 and 0 <= cooldown_bars <= 96):
            raise ValueError("TTL/cooldown inválidos")
        self.symbol=symbol
        self.strategy=strategy
        self.ttl_bars=ttl_bars
        self.cooldown_bars=cooldown_bars
        self.pending: Pending | None=None
        self.last_at=-1
        self.cooldown_until_idx=-1
        self.emitted_ids=set()

    def _emit(self, kind, side, at, price, rsi, stop, target, reason,
              setup_id, paired):
        eid=sha256(f"{setup_id}:{kind}:{at}".encode()).hexdigest()[:20]
        if eid in self.emitted_ids:
            raise AssertionError("Alerta duplicado")
        self.emitted_ids.add(eid)
        return Event(eid,setup_id,self.symbol,at,kind,side,price,
                     rsi,stop,target,reason,paired)

    def advance(self, fast: list[Candle], hourly: list[Candle],
                btc: list[Candle]) -> list[Event]:
        """Recebe série ATÉ a vela 15m recém-fechada, uma vez por timestamp.

        Dados 1h posteriores ao candle são ignorados na função de sinal. Sem
        referência BTC recente o tracker não cria novas oportunidades.
        """
        if not fast:
            return []
        c=fast[-1]
        if c.close_time <= self.last_at:
            raise ValueError("Replay fora de ordem ou vela repetida")
        self.last_at=c.close_time
        i=(c.open_time//STEP)
        if len(fast)<max(self.strategy.ema_fast+1,self.strategy.rsi_period+2,
                         self.strategy.atr_period+1):
            return []
        rsi=wilder_rsi([x.close for x in fast],self.strategy.rsi_period)[-1]
        atr=wilder_atr(fast,self.strategy.atr_period)[-1]
        ema20=sma_seeded_ema([x.close for x in fast],self.strategy.ema_fast)[-1]
        if any(x is None for x in (rsi,atr,ema20)) or atr<=0:
            return []
        h=[x for x in hourly if x.close_time<=c.close_time]
        b=[x for x in btc if x.close_time<=c.close_time]
        # Se faltar EMA200 contextual, nenhum estágio será confirmado.
        if len(h)<self.strategy.ema_regime or len(b)<self.strategy.ema_regime:
            return []
        if c.close_time-h[-1].close_time>HOUR or c.close_time-b[-1].close_time>HOUR:
            return []
        h50=sma_seeded_ema([x.close for x in h],self.strategy.ema_trend)[-1]
        h200=sma_seeded_ema([x.close for x in h],self.strategy.ema_regime)[-1]
        btc200=sma_seeded_ema([x.close for x in b],self.strategy.ema_regime)[-1]
        long_regime=h50>h200 and b[-1].close>btc200
        short_regime=h50<h200 and b[-1].close<btc200
        change24=100*(c.close/fast[-97].close-1) if len(fast)>=97 else None
        valid_long=long_regime and (change24 is None or change24>=-10)
        valid_short=short_regime and (change24 is None or change24<=15)
        events=[]
        confirmation=decide(fast,hourly,btc,c.close_time,change24,self.strategy)
        pending=self.pending

        if pending is not None:
            lifetime=i-pending.index
            broken_regime=(pending.side=="LONG" and not valid_long or
                           pending.side=="SHORT" and not valid_short)
            against=(pending.side=="LONG" and
                     (c.close<pending.initial_price-2*pending.initial_atr or rsi<40) or
                     pending.side=="SHORT" and
                     (c.close>pending.initial_price+2*pending.initial_atr or rsi>60))
            if broken_regime or against:
                events.append(self._emit(
                    "INVALIDATED",pending.side,c.close_time,c.close,rsi,None,None,
                    "Mudança de regime ou perda do limite de invalidação",
                    pending.setup_id,True))
                self.pending=None
                self.cooldown_until_idx=i+self.cooldown_bars
            elif lifetime>=self.ttl_bars:
                events.append(self._emit(
                    "EXPIRED",pending.side,c.close_time,c.close,rsi,None,None,
                    "Janela de confirmação expirou sem cruzamento",pending.setup_id,True))
                self.pending=None
                self.cooldown_until_idx=i+self.cooldown_bars
            elif confirmation is not None and confirmation.side==pending.side:
                events.append(self._emit(
                    "CONFIRMED",pending.side,c.close_time,c.close,rsi,
                    confirmation.stop,confirmation.target,
                    "Confirmação multitempo observada; não implica ordem",
                    pending.setup_id,True))
                self.pending=None
                self.cooldown_until_idx=i+self.cooldown_bars

        if self.pending is None and i>=self.cooldown_until_idx:
            if confirmation is not None:
                # Crossover muito rápido pode não gerar antecipação anterior;
                # registrar como confirmação NÃO PAREADA, sem inventar evento antigo.
                new_id=sha256(f"{self.symbol}:{confirmation.side}:{c.close_time}".encode()).hexdigest()[:18]
                events.append(self._emit(
                    "CONFIRMED",confirmation.side,c.close_time,c.close,rsi,
                    confirmation.stop,confirmation.target,
                    "Cruzamento direto sem alerta preliminar anterior",
                    new_id,False))
                self.cooldown_until_idx=i+self.cooldown_bars
            elif valid_long and 45<=rsi<50 and c.close>=ema20*.995:
                setup_id=sha256(f"{self.symbol}:LONG:{c.close_time}".encode()).hexdigest()[:18]
                self.pending=Pending(setup_id,"LONG",c.close_time,i,c.close,atr)
                events.append(self._emit(
                    "PRELIMINARY","LONG",c.close_time,c.close,rsi,None,None,
                    "RSI próximo de 50, preço perto da EMA20 e tendência de alta",
                    setup_id,False))
            elif valid_short and 50<rsi<=55 and c.close<=ema20*1.005:
                setup_id=sha256(f"{self.symbol}:SHORT:{c.close_time}".encode()).hexdigest()[:18]
                self.pending=Pending(setup_id,"SHORT",c.close_time,i,c.close,atr)
                events.append(self._emit(
                    "PRELIMINARY","SHORT",c.close_time,c.close,rsi,None,None,
                    "RSI próximo de 50, preço perto da EMA20 e tendência de baixa",
                    setup_id,False))
        return events


def replay_events(symbol: str, fast: list[Candle], hourly: list[Candle],
                  btc: list[Candle], *,
                  strategy: Strategy = Strategy()) -> dict:
    quality={
        "15m":validate_series(fast,"15m"),
        "hourly":validate_series(hourly,"1h"),
        "btc_hourly":validate_series(btc,"1h"),
    }
    tracker=SignalTracker(symbol,strategy=strategy)
    events=[]
    for i in range(len(fast)):
        # A construção da série de replay nunca injeta o candle do futuro
        # na análise de indicadores da vela corrente.
        events.extend(tracker.advance(fast[:i+1],hourly,btc))
    return {
        "mode":"offline_replay_no_trades",
        "symbol":symbol,"source":"validated_user_data",
        "quality":quality,"event_count":len(events),
        "events":[asdict(e) for e in events],
        "pending_at_end":asdict(tracker.pending) if tracker.pending else None,
        "important":"PRELIMINARY não prediz confirmação. CONFIRMED não é recomendação de trade.",
    }
