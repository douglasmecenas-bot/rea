import unittest
from sentinel_core.core import (Candle, Strategy, wilder_rsi, sma_seeded_ema,
                                wilder_atr, decide, backtest)


def bars(n, unit=900000, start=0, base=100, drift=0.1):
    result = []
    for i in range(n):
        close = base + i * drift
        op = close - drift/2
        result.append(Candle(start+i*unit, start+(i+1)*unit-1, op,
                             max(op,close)+1, min(op,close)-1, close, 50))
    return result


class CoreTests(unittest.TestCase):
    def test_ema_seed_exact(self):
        self.assertEqual(sma_seeded_ema([1,2,3,4,5],3),
                         [None,None,2,3,4])

    def test_rsi_bounds(self):
        self.assertEqual(wilder_rsi([100]*40)[-1],50)
        self.assertEqual(wilder_rsi(list(range(40)))[-1],100)
        self.assertEqual(wilder_rsi(list(range(40,0,-1)))[-1],0)

    def test_atr_constant(self):
        self.assertAlmostEqual(wilder_atr(bars(100,drift=0))[-1],2)

    def test_incomplete_context_no_signal(self):
        fast=bars(40)
        self.assertIsNone(decide(fast,bars(50,3600000),
                                 bars(50,3600000),fast[-1].close_time))

    def test_future_candles_do_not_change_past(self):
        fast=bars(100)
        trend=bars(300,unit=3600000)
        btc=bars(300,unit=3600000)
        t=fast[-1].close_time
        expected=decide(fast,trend,btc,t)
        later=bars(10,start=t+1,drift=-1)
        actual=decide(fast+later,trend+later,btc+later,t)
        self.assertEqual(expected,actual)

    def test_reject_invalid_candle(self):
        with self.assertRaises(ValueError):
            Candle(0,1,10,8,9,10,12)

    def test_reject_duplicate(self):
        fast=bars(60)
        with self.assertRaises(ValueError):
            decide(fast+[fast[-1]],bars(240,3600000),
                   bars(240,3600000),fast[-1].close_time)

    def test_risk_validation(self):
        with self.assertRaises(ValueError):
            Strategy(risk_fraction=0.9)
        with self.assertRaises(ValueError):
            Strategy(max_notional_to_equity=3)

    def test_no_trade_backtest_and_no_leverage(self):
        r=backtest(bars(300),bars(300,3600000),bars(300,3600000))
        self.assertEqual(r["trade_count"],0)
        self.assertEqual(r["final_equity"],10000)
        self.assertEqual(r["leverage"],1)

    def test_invalid_equity(self):
        with self.assertRaises(ValueError):
            backtest([],[],[],initial_equity=-100)


if __name__ == "__main__":
    unittest.main()
