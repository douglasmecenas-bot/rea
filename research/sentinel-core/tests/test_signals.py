import unittest
from unittest.mock import patch
from sentinel_core.core import Candle, Strategy, Signal, decide, backtest


def candles(values, start, interval):
    out = []
    for i, close in enumerate(values):
        opening = close
        out.append(Candle(start+i*interval, start+(i+1)*interval-1,
                          opening, close+1, close-1, close, 100))
    return out


class PositiveSignalTests(unittest.TestCase):
    def setUp(self):
        self.start = 250*3600000
        self.trend_up = candles([200+i*.25 for i in range(250)], 0, 3600000)
        self.btc_up = candles([350+i*.25 for i in range(250)], 0, 3600000)
        self.trend_down = candles([500-i*.25 for i in range(250)], 0, 3600000)
        self.btc_down = candles([300-i*.1 for i in range(250)], 0, 3600000)

    def test_long_signal_with_confirmed_trend(self):
        fast = candles([100]*54+[99]*5+[103], self.start, 900000)
        s = decide(fast, self.trend_up, self.btc_up, fast[-1].close_time, 0)
        self.assertIsNotNone(s)
        self.assertEqual(s.side, "LONG")
        self.assertLess(s.stop, s.price)
        self.assertGreater(s.target, s.price)
        self.assertAlmostEqual((s.target-s.price)/(s.price-s.stop), 2)

    def test_short_signal_with_confirmed_trend(self):
        fast = candles([100]*54+[101]*5+[97], self.start, 900000)
        s = decide(fast, self.trend_down, self.btc_down, fast[-1].close_time, 0)
        self.assertIsNotNone(s)
        self.assertEqual(s.side, "SHORT")
        self.assertGreater(s.stop, s.price)
        self.assertLess(s.target, s.price)

    def test_long_24h_circuit_breaker(self):
        fast = candles([100]*54+[99]*5+[103], self.start, 900000)
        s = decide(fast, self.trend_up, self.btc_up, fast[-1].close_time, -11)
        self.assertIsNone(s)

    def test_short_24h_circuit_breaker(self):
        fast = candles([100]*54+[101]*5+[97], self.start, 900000)
        s = decide(fast, self.trend_down, self.btc_down, fast[-1].close_time, 16)
        self.assertIsNone(s)


class ExecutionTests(unittest.TestCase):
    def _check_stop_first(self, side):
        f = candles([100]*50, 0, 900000)
        signal = Signal(side, f[20].close_time, 100, .5,
                        99.5 if side == "LONG" else 100.5,
                        101 if side == "LONG" else 99,
                        51, 1, "synthetic unit test")
        def synthetic_decision(fast, *args, **kwargs):
            return signal if len(fast) == 21 else None
        with patch("sentinel_core.core.decide", side_effect=synthetic_decision):
            report = backtest(f, [], [], Strategy())
        self.assertEqual(report["trade_count"], 1)
        trade = report["trades"][0]
        self.assertEqual(trade["entry_at"], f[21].open_time)
        self.assertEqual(trade["exit_reason"], "STOP")
        self.assertLess(trade["pnl"], 0)
        self.assertLessEqual(trade["entry"]*trade["qty"], 10000.05)

    def test_long_stop_first(self):
        self._check_stop_first("LONG")

    def test_short_stop_first(self):
        self._check_stop_first("SHORT")


if __name__ == "__main__":
    unittest.main()
