"""Núcleo Sentinel: indicadores, decisões e backtest sem alavancagem.

Versão experimental. O sistema NÃO envia ordens nem recomenda investimentos.
Todas as decisões em t usam somente candles fechados até t.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Literal

Side = Literal["LONG", "SHORT"]


@dataclass(frozen=True)
class Candle:
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        prices = (self.open, self.high, self.low, self.close, self.volume)
        if (self.close_time <= self.open_time or not all(isfinite(v) for v in prices)
                or min(self.open, self.high, self.low, self.close) <= 0 or self.volume < 0
                or self.high < max(self.open, self.close, self.low)
                or self.low > min(self.open, self.close, self.high)):
            raise ValueError("Candle inválido")


@dataclass(frozen=True)
class Strategy:
    rsi_period: int = 14
    ema_fast: int = 20
    ema_trend: int = 50
    ema_regime: int = 200
    atr_period: int = 14
    atr_mult: float = 1.5
    reward_risk: float = 2.0
    risk_fraction: float = 0.01
    one_way_fee_bps: float = 9.0      # 0,18% ida + volta
    slippage_bps: float = 2.0
    max_notional_to_equity: float = 1.0  # simulação SEM alavancagem
    max_holding_bars: int = 96

    def __post_init__(self):
        if any(int(v) < 1 for v in (self.rsi_period, self.ema_fast, self.ema_trend,
                                    self.ema_regime, self.atr_period, self.max_holding_bars)):
            raise ValueError("Janelas inválidas")
        if not (self.atr_mult > 0 and self.reward_risk > 0 and 0 < self.risk_fraction <= 0.05
                and self.one_way_fee_bps >= 0 and self.slippage_bps >= 0
                and 0 < self.max_notional_to_equity <= 1):
            raise ValueError("Parâmetros de risco inválidos")


@dataclass(frozen=True)
class Signal:
    side: Side
    at: int
    price: float
    stop_distance: float
    stop: float
    target: float
    rsi: float
    atr: float
    reason: str


def sma_seeded_ema(values: list[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("period precisa ser >= 1")
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    avg = sum(values[:period]) / period
    out[period - 1] = avg
    a = 2.0 / (period + 1.0)
    for i in range(period, len(values)):
        avg = values[i] * a + avg * (1 - a)
        out[i] = avg
    return out


def wilder_rsi(prices: list[float], period: int = 14) -> list[float | None]:
    if period < 1:
        raise ValueError("period precisa ser >= 1")
    out: list[float | None] = [None] * len(prices)
    if len(prices) <= period:
        return out
    gains = [max(prices[i] - prices[i-1], 0) for i in range(1, period+1)]
    losses = [max(prices[i-1] - prices[i], 0) for i in range(1, period+1)]
    g, l = sum(gains)/period, sum(losses)/period
    def value(ag: float, al: float) -> float:
        if ag == 0 and al == 0:
            return 50.0
        if al == 0:
            return 100.0
        if ag == 0:
            return 0.0
        return 100.0 - 100.0 / (1.0 + ag/al)
    out[period] = value(g, l)
    for i in range(period+1, len(prices)):
        diff = prices[i] - prices[i-1]
        g = (g * (period-1) + max(diff, 0)) / period
        l = (l * (period-1) + max(-diff, 0)) / period
        out[i] = value(g, l)
    return out


def wilder_atr(candles: list[Candle], period: int = 14) -> list[float | None]:
    if period < 1:
        raise ValueError("period precisa ser >= 1")
    out: list[float | None] = [None] * len(candles)
    if len(candles) <= period:
        return out
    tr = [0.0] * len(candles)
    for i in range(1, len(candles)):
        c, p = candles[i], candles[i-1]
        tr[i] = max(c.high - c.low, abs(c.high - p.close), abs(c.low - p.close))
    avg = sum(tr[1:period+1]) / period
    out[period] = avg
    for i in range(period+1, len(candles)):
        avg = (avg * (period-1) + tr[i]) / period
        out[i] = avg
    return out


def indicators(candles: list[Candle], strategy: Strategy = Strategy()) -> dict:
    closes = [c.close for c in candles]
    return {
        "ema20": sma_seeded_ema(closes, strategy.ema_fast),
        "ema50": sma_seeded_ema(closes, strategy.ema_trend),
        "ema200": sma_seeded_ema(closes, strategy.ema_regime),
        "rsi14": wilder_rsi(closes, strategy.rsi_period),
        "atr14": wilder_atr(candles, strategy.atr_period),
    }


def _closed(candles: list[Candle], at: int) -> list[Candle]:
    valid = [c for c in candles if c.close_time <= at]
    if any(valid[i].close_time >= valid[i+1].close_time for i in range(len(valid)-1)):
        raise ValueError("Candles não ordenados ou duplicados")
    return valid


def decide(
    fast_15m: list[Candle], trend_1h: list[Candle], btc_1h: list[Candle],
    at: int, pct_change_24h: float | None = None, strategy: Strategy = Strategy()
) -> Signal | None:
    """RSI cruzando 50 + EMA20, EMA50/200 1h e regime BTC EMA200 1h.

    Retorna None sem dados suficientes, sem confluência ou fora do regime.
    Não usa 1h incompleto nem candle com fechamento futuro.
    """
    f, h, b = (_closed(x, at) for x in (fast_15m, trend_1h, btc_1h))
    if len(f) < max(strategy.ema_fast, strategy.rsi_period + 2, strategy.atr_period+1) \
       or len(h) < strategy.ema_regime or len(b) < strategy.ema_regime:
        return None
    c = f[-1]
    rsi = wilder_rsi([x.close for x in f], strategy.rsi_period)
    atr = wilder_atr(f, strategy.atr_period)[-1]
    ema20 = sma_seeded_ema([x.close for x in f], strategy.ema_fast)[-1]
    trend_ema50 = sma_seeded_ema([x.close for x in h], strategy.ema_trend)[-1]
    trend_ema200 = sma_seeded_ema([x.close for x in h], strategy.ema_regime)[-1]
    btc_ema200 = sma_seeded_ema([x.close for x in b], strategy.ema_regime)[-1]
    if any(v is None for v in (rsi[-1], rsi[-2], atr, ema20, trend_ema50,
                                trend_ema200, btc_ema200)):
        return None
    if atr <= 0:
        return None
    long_ok = (rsi[-2] <= 50 < rsi[-1] and c.close > ema20
               and trend_ema50 > trend_ema200 and b[-1].close > btc_ema200
               and (pct_change_24h is None or pct_change_24h >= -10))
    short_ok = (rsi[-2] >= 50 > rsi[-1] and c.close < ema20
                and trend_ema50 < trend_ema200 and b[-1].close < btc_ema200
                and (pct_change_24h is None or pct_change_24h <= 15))
    if not (long_ok or short_ok):
        return None
    side: Side = "LONG" if long_ok else "SHORT"
    dist = float(atr) * strategy.atr_mult
    sign = 1 if side == "LONG" else -1
    return Signal(side=side, at=c.close_time, price=c.close, stop_distance=dist,
                  stop=c.close - sign*dist, target=c.close + sign*dist*strategy.reward_risk,
                  rsi=float(rsi[-1]), atr=float(atr),
                  reason="RSI50+EMA20 15m / EMA50-200 1h / BTC EMA200 1h")


def backtest(
    fast_15m: list[Candle], trend_1h: list[Candle], btc_1h: list[Candle],
    strategy: Strategy = Strategy(), initial_equity: float = 10000.0
) -> dict:
    """Simulador 15m com execução na próxima abertura e stop prioritário.

    Uma posição por vez. Stop e alvo intrabar simultâneos => STOP.
    Não modela book, gaps externos, funding, liquidação ou impacto de mercado;
    essas limitações tornam os resultados NÃO aptos para operações reais.
    """
    if not isfinite(initial_equity) or initial_equity <= 0:
        raise ValueError("initial_equity inválido")
    if any(fast_15m[i].close_time >= fast_15m[i+1].close_time
           for i in range(len(fast_15m)-1)):
        raise ValueError("Candles 15m fora de ordem")
    fee = strategy.one_way_fee_bps / 10000
    slip = strategy.slippage_bps / 10000
    equity = initial_equity
    trades = []
    i = max(20, strategy.rsi_period+2, strategy.ema_fast)
    while i < len(fast_15m)-1:
        current = fast_15m[i]
        # Simulação de variação 24h com 96 velas 15m fechadas:
        change = 100*(current.close / fast_15m[i-96].close - 1) if i >= 96 else None
        signal = decide(fast_15m[:i+1], trend_1h, btc_1h,
                        current.close_time, change, strategy)
        if signal is None:
            i += 1
            continue
        entry_i = i+1
        entry_bar = fast_15m[entry_i]
        sign = 1 if signal.side == "LONG" else -1
        entry = entry_bar.open * (1 + sign*slip)
        dist = signal.stop_distance
        stop = entry - sign*dist
        target = entry + sign*dist*strategy.reward_risk
        # sizing conservador que considera stop + taxas + slippage de saída
        loss_per_unit = dist + entry*(2*fee + slip)
        quantity = min(equity*strategy.risk_fraction/loss_per_unit,
                       equity*strategy.max_notional_to_equity/entry)
        if quantity <= 0:
            break
        exit_i = min(entry_i+strategy.max_holding_bars-1, len(fast_15m)-1)
        reason = "TIME"
        raw_exit = fast_15m[exit_i].close
        for j in range(entry_i, exit_i+1):
            bar = fast_15m[j]
            stopped = bar.low <= stop if sign == 1 else bar.high >= stop
            targeted = bar.high >= target if sign == 1 else bar.low <= target
            if stopped:
                # se abertura passou do stop, assumir pior abertura
                raw_exit = min(bar.open, stop) if sign == 1 else max(bar.open, stop)
                reason, exit_i = "STOP", j
                break
            if targeted:
                raw_exit = target  # não presumir melhoria de preço em gap favorável
                reason, exit_i = "TARGET", j
                break
        exit_price = raw_exit * (1 - sign*slip)
        gross = (exit_price-entry)*quantity*sign
        fees = (entry+exit_price)*quantity*fee
        pnl = gross - fees
        equity += pnl
        trades.append({
            "side": signal.side, "entry_at": entry_bar.open_time,
            "signal_at": signal.at, "exit_at": fast_15m[exit_i].close_time,
            "entry": round(entry, 8), "exit": round(exit_price, 8),
            "qty": round(quantity, 8), "pnl": round(pnl, 4),
            "equity_after": round(equity, 4), "exit_reason": reason,
            "estimated_fee": round(fees, 4), "signal": asdict(signal),
        })
        i = exit_i+1   # sem sobrepor posições, próximo fechamento após saída

    peak = initial_equity
    max_dd = 0.0
    for equity_after in (t["equity_after"] for t in trades):
        peak = max(peak, equity_after)
        max_dd = max(max_dd, (peak-equity_after)/peak)
    wins = [x for x in trades if x["pnl"] > 0]
    gains = sum(x["pnl"] for x in trades if x["pnl"] > 0)
    losses = -sum(x["pnl"] for x in trades if x["pnl"] < 0)
    return {
        "engine": "sentinel-core-exp-v1", "initial_equity": initial_equity,
        "final_equity": round(equity, 4), "net_pnl": round(equity-initial_equity, 4),
        "trade_count": len(trades), "win_rate": len(wins)/len(trades) if trades else None,
        "profit_factor": gains/losses if losses else None,
        "max_closed_trade_drawdown_pct": round(max_dd*100, 4),
        "fee_rate_one_way_bps": strategy.one_way_fee_bps,
        "slippage_bps": strategy.slippage_bps, "leverage": 1,
        "limitations": [
            "Somente P&L de operações fechadas; drawdown intraposição não medido",
            "Sem funding, impacto no book, liquidação ou taxas variáveis",
            "Intrabar stop e alvo simultâneos: stop primeiro",
            "Nenhum trade com dinheiro é executado",
        ],
        "trades": trades,
    }
