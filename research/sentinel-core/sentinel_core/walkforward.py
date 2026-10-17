"""Sentinel v0.3 — walk-forward sequencial com parâmetros FIXOS.

Cada teste usa um bloco futuro não sobreposto. O motor de decisão vê apenas
velas fechadas naquele instante, mesmo com contextos de warmup.
Não faz otimização, live trading ou garantias de performance.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from math import prod

from .core import Candle, Strategy
from .history import FundingEvent, validate_series
from .simulator import simulate

HOUR = 3_600_000


def _bounds(candles: list[Candle], start: int, end: int) -> list[Candle]:
    return [c for c in candles if c.open_time < end and c.close_time < end
            and c.close_time >= start - 240 * HOUR]


def _funding_events(events: list[FundingEvent] | None,
                    start: int, end: int) -> list[FundingEvent] | None:
    return None if events is None else [
        x for x in events if start <= x.funding_time < end
    ]


def hold_benchmarks(test: list[Candle], strategy: Strategy) -> dict:
    """Retornos comparativos hipotéticos, excluem funding e impacto do book.

    Não confundir com execução futura real; stop e sizing diferentes.
    """
    if len(test) < 2:
        raise ValueError("Benchmarks exigem ao menos duas velas")
    first = test[0].open
    last = test[-1].close
    slip = strategy.slippage_bps / 10_000
    fee = strategy.one_way_fee_bps / 10_000
    returns = {}
    for direction, label in ((1, "buy_hold"), (-1, "short_hold")):
        entry = first * (1 + direction * slip)
        exit_ = last * (1 - direction * slip)
        pnl = direction * (exit_ - entry) / entry
        costs = fee * (entry + exit_) / entry
        returns[label] = round(100 * (pnl - costs), 6)
    return {
        **returns,
        "cash_pct": 0.0,
        "assumption": "100% notional, uma operação em todo o teste; sem funding",
    }


def evaluate_walk_forward(
    fast_15m: list[Candle],
    trend_1h: list[Candle],
    btc_1h: list[Candle],
    *,
    strategy: Strategy = Strategy(),
    funding_events: list[FundingEvent] | None = None,
    train_bars: int = 1152,
    test_bars: int = 288,
    warmup_bars: int = 960,
    folds: int = 3,
    initial_equity: float = 10_000.0,
) -> dict:
    """Não otimiza parâmetros; estratégia fixa é verificada nos períodos seguintes.

    Para uma avaliação fora da amostra verdadeira, quaisquer ajustes após
    inspeção dos resultados exigem NOVOS períodos não utilizados no tuning.
    """
    quality = {
        "15m": validate_series(fast_15m, "15m"),
        "1h": validate_series(trend_1h, "1h"),
        "btc_1h": validate_series(btc_1h, "1h"),
    }
    if (not isinstance(train_bars, int) or not isinstance(test_bars, int)
            or not isinstance(warmup_bars, int) or not isinstance(folds, int)
            or train_bars < 200 or test_bars < 24 or warmup_bars < 800
            or not (1 <= folds <= 24)):
        raise ValueError("Folds ou janelas inválidas; warmup >= 800 candles 15m")
    first_test = train_bars + warmup_bars
    required = first_test + folds * test_bars
    if len(fast_15m) < required:
        raise ValueError(
            f"Histórico insuficiente: mínimo {required} candles 15m; "
            f"encontrados {len(fast_15m)}"
        )
    if not trend_1h or not btc_1h:
        raise ValueError("Contexto de regime 1h ausente")

    all_folds = []
    for n in range(folds):
        test_start_idx = first_test + n * test_bars
        test_end_idx = test_start_idx + test_bars
        train_start_idx = test_start_idx - train_bars
        context_idx = train_start_idx - warmup_bars
        train_at = fast_15m[train_start_idx].open_time
        test_at = fast_15m[test_start_idx].open_time
        test_end_at = fast_15m[test_end_idx - 1].close_time + 1

        train_15m = fast_15m[context_idx:test_start_idx]
        test_15m = fast_15m[context_idx:test_end_idx]
        train_hour = _bounds(trend_1h, train_15m[0].open_time, test_at)
        train_btc = _bounds(btc_1h, train_15m[0].open_time, test_at)
        test_hour = _bounds(trend_1h, test_15m[0].open_time, test_end_at)
        test_btc = _bounds(btc_1h, test_15m[0].open_time, test_end_at)

        # Recusa lacunas nas janelas e ausência de referência 1h relevante.
        # simulate() recusa também dados 1h obsoletos durante os sinais.
        train = simulate(
            train_15m, train_hour, train_btc,
            funding_events=_funding_events(funding_events, train_at, test_at),
            strategy=strategy, initial_equity=initial_equity,
            first_entry_ms=train_at,
        )
        test = simulate(
            test_15m, test_hour, test_btc,
            funding_events=_funding_events(funding_events, test_at, test_end_at),
            strategy=strategy, initial_equity=initial_equity,
            first_entry_ms=test_at,
        )
        # Rejeitar atribuição indevida a OOS de operações anteriores.
        for trade in test["trade_log"]:
            if not (test_at <= trade["entry_at"] < test_end_at):
                raise AssertionError("Trade fora do período de teste")
        all_folds.append({
            "fold": n+1,
            "train_start_ms": train_at, "train_end_exclusive_ms": test_at,
            "test_start_ms": test_at, "test_end_exclusive_ms": test_end_at,
            "train": train, "test": test,
            "test_benchmarks": hold_benchmarks(
                fast_15m[test_start_idx:test_end_idx], strategy
            ),
            "test_dataset_sha256": validate_series(
                fast_15m[test_start_idx:test_end_idx], "15m"
            )["sha256"],
        })

    total_trades = sum(f["test"]["trades"] for f in all_folds)
    compounded = prod(1 + f["test"]["return_pct"]/100 for f in all_folds)
    returns = [f["test"]["return_pct"] for f in all_folds]
    config = asdict(strategy)
    signature = sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    return {
        "engine": "sentinel-v0.3-fixed-sequential-walk-forward",
        "purpose": "research_paper_only",
        "parameters_fixed_before_all_tests": True,
        "strategy_sha256": signature, "strategy": config,
        "source_quality": quality,
        "funding_coverage": ("not_provided" if funding_events is None
                             else "events_present_but_completeness_unverified"),
        "walk_forward": {
            "folds": folds, "train_bars_15m": train_bars,
            "test_bars_15m": test_bars, "warmup_bars_15m": warmup_bars,
            "out_of_sample_total_trades": total_trades,
            "out_of_sample_positive_folds": sum(x > 0 for x in returns),
            "out_of_sample_compounded_return_pct": round(
                100*(compounded-1), 6
            ),
            "out_of_sample_trades_enough_for_statistical_claim": total_trades >= 30,
            "disclaimer": (
                "Compounded OOS return is hypothetical and excludes strategy "
                "selection bias. Benchmarks omit funding, so not fully comparable. "
                "No guaranteed profit, no live execution."
            ),
            "results": all_folds,
        },
    }
