"""Sentinel v0.2: backtester OHLCV com auditoria, funding e holdout.

NUNCA executa ordens; intervalos intrabar são desconhecidos:
stop e alvo simultâneos => stop; funding no bar de saída é aproximado.
"""
from __future__ import annotations

from dataclasses import asdict
from math import isfinite

from .core import Candle, Strategy, decide
from .history import FundingEvent, validate_series

FIFTEEN = 900_000
HOUR = 3_600_000


def _metrics(trades: list[dict], equity: float, initial: float,
             max_drawdown: float, strategy: Strategy, funding_status: str) -> dict:
    gross_pos = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_neg = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    return {
        "engine": "sentinel-v0.2-experimental",
        "initial_equity": round(initial, 6),
        "final_equity": round(equity, 6),
        "net_pnl": round(equity-initial, 6),
        "return_pct": round(100*(equity/initial-1), 5),
        "trades": len(trades),
        "win_rate": (sum(t["pnl"] > 0 for t in trades)/len(trades)) if trades else None,
        "profit_factor": (gross_pos/gross_neg) if gross_neg > 0 else None,
        "max_conservative_intrabar_drawdown_pct": round(100*max_drawdown, 5),
        "estimated_total_fees": round(sum(t["fees"] for t in trades), 6),
        "total_funding_pnl": round(sum(t["funding_pnl"] for t in trades), 6),
        "funding_status": funding_status,
        "assumptions": {
            "fee_bps_each_side": strategy.one_way_fee_bps,
            "slippage_bps_each_side": strategy.slippage_bps,
            "max_notional_to_equity": strategy.max_notional_to_equity,
            "risk_fraction": strategy.risk_fraction,
        },
        "limitations": [
            "Modelo OHLCV, sem book, partial fills, impostos, lot size ou impacto de mercado",
            "Funding intrabar contabilizado inclusive no candle de saída; sequência exata intrabar desconhecida",
            "Sem eventos funding ≠ financiamento zero: ver funding_status",
            "Drawdown pessimista baseado no extremo intrabar; ordem real dos extremos é desconhecida",
            "Uma posição por vez, sem alavancagem e sem execução de ordens",
            "Separação temporal não substitui validação walk-forward múltipla e fora da amostra",
        ],
        "trade_log": trades,
    }


def simulate(
    fast_15m: list[Candle], trend_1h: list[Candle], btc_1h: list[Candle],
    *, funding_events: list[FundingEvent] | None = None,
    strategy: Strategy = Strategy(), initial_equity: float = 10_000.0,
    first_entry_ms: int | None = None,
) -> dict:
    """Somente candles fechados, com execução na abertura seguinte ao sinal.

    funding_events=None deixa funding explicitamente fora do P&L.
    Lista de eventos é considerada informada, mas sua cobertura não é presumida.
    """
    if not isfinite(initial_equity) or initial_equity <= 0:
        raise ValueError("Saldo inicial inválido")
    validate_series(fast_15m, "15m")
    validate_series(trend_1h, "1h")
    validate_series(btc_1h, "1h")
    events = sorted(funding_events or [], key=lambda x: x.funding_time)
    if any(events[i].funding_time >= events[i+1].funding_time
           for i in range(len(events)-1)):
        raise ValueError("Funding duplicado")
    funding_status = ("not_provided" if funding_events is None
                      else "provided_completeness_not_verified")
    fee = strategy.one_way_fee_bps / 10_000
    slip = strategy.slippage_bps / 10_000
    equity = initial_equity
    peak = initial_equity
    max_dd = 0.0
    trades: list[dict] = []
    i = max(96, strategy.ema_fast, strategy.rsi_period+2, strategy.atr_period+1)

    def observe(value: float):
        nonlocal peak, max_dd
        peak = max(peak, value)
        if peak > 0:
            max_dd = max(max_dd, max(0.0, (peak-value)/peak))

    while i < len(fast_15m)-1:
        bar = fast_15m[i]
        if first_entry_ms is not None and fast_15m[i+1].open_time < first_entry_ms:
            i += 1
            continue
        # Não operar com séries 1h desatualizadas, mesmo quando registros já
        # estão ordenados e sem lacunas internas.
        recent_trend = next((x for x in reversed(trend_1h) if x.close_time <= bar.close_time), None)
        recent_btc = next((x for x in reversed(btc_1h) if x.close_time <= bar.close_time), None)
        if (recent_trend is None or recent_btc is None
                or bar.close_time-recent_trend.close_time > HOUR
                or bar.close_time-recent_btc.close_time > HOUR):
            i += 1
            continue
        change_24h = 100*(bar.close/fast_15m[i-96].close-1)
        signal = decide(fast_15m[:i+1], trend_1h, btc_1h,
                        bar.close_time, change_24h, strategy)
        if signal is None:
            i += 1
            continue
        entry_i = i+1
        entry_bar = fast_15m[entry_i]
        direction = 1 if signal.side == "LONG" else -1
        entry = entry_bar.open*(1+direction*slip)
        distance = signal.stop_distance
        stop = entry-direction*distance
        target = entry+direction*distance*strategy.reward_risk
        if stop <= 0 or target <= 0:
            i += 1
            continue
        est_loss_per_unit = distance+entry*(2*fee+slip)
        quantity = min(equity*strategy.risk_fraction/est_loss_per_unit,
                       equity*strategy.max_notional_to_equity/entry)
        if quantity <= 0:
            break
        initial_fee = entry*quantity*fee
        holding_funding = 0.0
        included_funding = []
        end_i = min(entry_i+strategy.max_holding_bars-1, len(fast_15m)-1)
        exit_reason = "TIME"
        exit_raw = fast_15m[end_i].close
        funding_cursor = 0
        while funding_cursor < len(events) and events[funding_cursor].funding_time < entry_bar.open_time:
            funding_cursor += 1

        for j in range(entry_i, end_i+1):
            observed = fast_15m[j]
            # Custo de funding aproximado pelo markPrice informado no evento.
            # Conservador no sentido de não tentar reconstruir ordem intrabar.
            while (funding_cursor < len(events)
                   and events[funding_cursor].funding_time <= observed.close_time):
                ev = events[funding_cursor]
                delta = -direction * ev.rate * ev.mark_price * quantity
                holding_funding += delta
                included_funding.append(ev.funding_time)
                funding_cursor += 1
            # Bound conservador de perda intrabar, não a sequência real.
            extreme = observed.low if direction == 1 else observed.high
            marked = (equity-initial_fee + holding_funding
                      + direction*(extreme-entry)*quantity-extreme*quantity*fee)
            observe(marked)
            stopped = observed.low <= stop if direction == 1 else observed.high >= stop
            targeted = observed.high >= target if direction == 1 else observed.low <= target
            if stopped:
                exit_raw = min(observed.open,stop) if direction == 1 else max(observed.open,stop)
                exit_reason, end_i = "STOP", j
                break
            if targeted:
                exit_raw = target
                exit_reason, end_i = "TARGET", j
                break

        exit_price = exit_raw*(1-direction*slip)
        exit_fee = exit_price*quantity*fee
        pnl_before_funding = direction*(exit_price-entry)*quantity-initial_fee-exit_fee
        pnl = pnl_before_funding+holding_funding
        equity += pnl
        observe(equity)
        trades.append({
            "side": signal.side, "signal_at": signal.at,
            "entry_at": entry_bar.open_time, "exit_at": fast_15m[end_i].close_time,
            "entry": round(entry, 9), "exit": round(exit_price, 9),
            "stop": round(stop, 9), "target": round(target, 9),
            "quantity": round(quantity, 9),
            "pnl": round(pnl, 6), "pnl_before_funding": round(pnl_before_funding, 6),
            "funding_pnl": round(holding_funding, 6),
            "funding_events_applied": included_funding,
            "fees": round(initial_fee+exit_fee, 6),
            "equity_after": round(equity, 6),
            "exit_reason": exit_reason,
            "signal": asdict(signal),
        })
        i = end_i+1

    return _metrics(trades,equity,initial_equity,max_dd,strategy,funding_status)


def chronological_holdout(
    fast_15m: list[Candle], trend_1h: list[Candle], btc_1h: list[Candle],
    *, funding_events: list[FundingEvent] | None = None,
    strategy: Strategy = Strategy(), initial_equity: float = 10_000.0,
    train_fraction: float = .7,
) -> dict:
    """Divisão temporal fixa; treino NÃO contém candles do período de teste.

    O período de teste recebe contexto anterior apenas para warmup de indicadores.
    Não há ajuste automático de parâmetros, otimização nem promessa de outperformance.
    """
    if not (.5 <= train_fraction <= .9):
        raise ValueError("train_fraction deve ser 0.5..0.9")
    validate_series(fast_15m,"15m")
    split = int(len(fast_15m)*train_fraction)
    if split < 150 or len(fast_15m)-split < 100:
        raise ValueError("Dados insuficientes para holdout com warmup")
    cutoff = fast_15m[split].open_time
    train = simulate(fast_15m[:split],trend_1h,btc_1h,
                     funding_events=([x for x in funding_events if x.funding_time < cutoff]
                                     if funding_events is not None else None),
                     strategy=strategy,initial_equity=initial_equity)
    test = simulate(fast_15m,trend_1h,btc_1h, funding_events=funding_events,
                    strategy=strategy,initial_equity=initial_equity,
                    first_entry_ms=cutoff)
    return {"split_time_ms":cutoff,"train_bars":split,
            "test_bars":len(fast_15m)-split,
            "method":"single_chronological_holdout_not_walk_forward",
            "train":train,"test":test}
