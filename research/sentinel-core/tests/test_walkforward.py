"""Testes offline: separação temporal, benchmarks e sonda sem ordens."""
import unittest
from unittest.mock import patch

from sentinel_core.core import Candle, Strategy
from sentinel_core.walkforward import evaluate_walk_forward, hold_benchmarks
from sentinel_core.exchange_probe import probe
from sentinel_core.data import MarketDataError

MINUTE15 = 900_000
HOUR = 3_600_000


def bars(n, step, first=0, price=100):
    return [
        Candle(first+i*step, first+(i+1)*step-1,
               price,price+1,price-1,price,100)
        for i in range(n)
    ]


class WalkForwardTests(unittest.TestCase):
    def setUp(self):
        self.fast = bars(1060, MINUTE15)
        self.h = bars(300, HOUR)

    @patch("sentinel_core.simulator.decide", return_value=None)
    def test_fold_disjointness_and_paper_returns(self, _decision):
        x = evaluate_walk_forward(
            self.fast,self.h,self.h,
            warmup_bars=800,train_bars=200,test_bars=24,folds=2)
        folds = x["walk_forward"]["results"]
        self.assertEqual(len(folds),2)
        self.assertEqual(folds[0]["test_end_exclusive_ms"],
                         folds[1]["test_start_ms"])
        self.assertEqual(x["walk_forward"]["out_of_sample_total_trades"],0)
        self.assertEqual(x["walk_forward"]["out_of_sample_compounded_return_pct"],0)
        self.assertFalse(x["walk_forward"]["out_of_sample_trades_enough_for_statistical_claim"])
        for fold in folds:
            self.assertEqual(fold["test"]["trades"],0)
            self.assertEqual(fold["test"]["engine"],"sentinel-v0.2-experimental")

    @patch("sentinel_core.simulator.decide", return_value=None)
    def test_future_change_does_not_affect_past_fold(self, _decision):
        x = evaluate_walk_forward(
            self.fast,self.h,self.h,
            warmup_bars=800,train_bars=200,test_bars=24,folds=2)
        changed = list(self.fast)
        p = changed[1055]
        changed[1055] = Candle(p.open_time,p.close_time,100,102,99,101,100)
        y = evaluate_walk_forward(
            changed,self.h,self.h,
            warmup_bars=800,train_bars=200,test_bars=24,folds=2)
        self.assertEqual(
            x["walk_forward"]["results"][0],
            y["walk_forward"]["results"][0])
        self.assertNotEqual(x["source_quality"]["15m"]["sha256"],
                            y["source_quality"]["15m"]["sha256"])

    def test_gap_and_insufficient_data_fail_closed(self):
        with self.assertRaises(ValueError):
            evaluate_walk_forward(self.fast[:900],self.h,self.h,
                                  warmup_bars=800,train_bars=200,test_bars=24,folds=2)
        with self.assertRaises(ValueError):
            evaluate_walk_forward(self.fast[:500]+self.fast[501:],
                                  self.h,self.h,warmup_bars=800,
                                  train_bars=200,test_bars=24,folds=2)

    def test_benchmarks_account_for_fees_and_slip(self):
        xx = [Candle(0,MINUTE15-1,100,102,99,101,1),
              Candle(MINUTE15,2*MINUTE15-1,101,105,100,104,1)]
        zero_cost = Strategy(one_way_fee_bps=0,slippage_bps=0)
        bench = hold_benchmarks(xx,zero_cost)
        self.assertAlmostEqual(bench["buy_hold"],4.0)
        self.assertAlmostEqual(bench["short_hold"],-4.0)
        cost = hold_benchmarks(xx,Strategy())
        self.assertLess(cost["buy_hold"],bench["buy_hold"])
        self.assertLess(cost["short_hold"],bench["short_hold"])

    def test_bad_fold_params(self):
        with self.assertRaises(ValueError):
            evaluate_walk_forward(self.fast,self.h,self.h,
                                  warmup_bars=799,train_bars=200,
                                  test_bars=24,folds=2)

    @patch("sentinel_core.exchange_probe.BinancePublic")
    def test_exchange_probe_network_error_is_explicit(self, mock):
        mock.return_value.klines.side_effect = MarketDataError("blocked")
        result = probe()
        self.assertEqual(result["status"],"unavailable_not_verified")
        self.assertEqual(result["executed_orders"],0)
        self.assertNotIn("sha256",result)

    @patch("sentinel_core.exchange_probe.BinancePublic")
    def test_exchange_probe_never_fabricates_partial_response(self, mock):
        mock.return_value.klines.return_value = []
        result = probe()
        self.assertEqual(result["status"],"unavailable_not_verified")


if __name__ == "__main__":
    unittest.main()
