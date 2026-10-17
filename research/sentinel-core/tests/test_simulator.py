import unittest
from unittest.mock import patch

from sentinel_core.core import Candle, Signal, Strategy
from sentinel_core.history import FundingEvent
from sentinel_core.simulator import simulate, chronological_holdout

FIFTEEN=900000
HOUR=3600000


def bars(n,start,step,base=100):
    return [Candle(start+i*step,start+(i+1)*step-1,
                   base,base+.2,base-.2,base,20) for i in range(n)]


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.fast=bars(540,200*HOUR,FIFTEEN)
        self.hour=bars(400,0,HOUR)

    def _signal(self, side="LONG", at=None):
        return Signal(side,at if at is not None else self.fast[100].close_time,
                      100,1,99 if side=="LONG" else 101,
                      102 if side=="LONG" else 98,51,1,"synthetic")

    def _trigger(self, side="LONG", start=100):
        sig=self._signal(side,self.fast[start].close_time)
        def synthetic(fast,*args,**kwargs):
            return sig if fast[-1].close_time==sig.at else None
        return synthetic

    def test_no_trades_with_no_signals(self):
        with patch("sentinel_core.simulator.decide",return_value=None):
            out=simulate(self.fast,self.hour,self.hour)
        self.assertEqual(out["trades"],0)
        self.assertEqual(out["funding_status"],"not_provided")
        self.assertEqual(out["final_equity"],10000)

    def test_stop_is_prioritized_and_downside_marked(self):
        fast=self.fast[:]
        # Stop e alvo são tocados na mesma vela após o sinal.
        idx=101
        orig=fast[idx]
        fast[idx]=Candle(orig.open_time,orig.close_time,100,103,97,100,20)
        with patch("sentinel_core.simulator.decide",side_effect=self._trigger()):
            out=simulate(fast,self.hour,self.hour,strategy=Strategy())
        self.assertEqual(out["trades"],1)
        trade=out["trade_log"][0]
        self.assertEqual(trade["exit_reason"],"STOP")
        self.assertEqual(trade["entry_at"],fast[idx].open_time)
        self.assertLess(trade["pnl"],0)
        self.assertGreater(out["max_conservative_intrabar_drawdown_pct"],0)

    def test_funding_subtracted_from_long_pnl(self):
        timestamp=self.fast[104].open_time+5
        event=FundingEvent(timestamp,.002,100)
        with patch("sentinel_core.simulator.decide",side_effect=self._trigger()):
            baseline=simulate(self.fast,self.hour,self.hour,funding_events=[])
        with patch("sentinel_core.simulator.decide",side_effect=self._trigger()):
            funded=simulate(self.fast,self.hour,self.hour,funding_events=[event])
        t0,t1=baseline["trade_log"][0],funded["trade_log"][0]
        self.assertLess(t1["funding_pnl"],0)
        self.assertAlmostEqual(t1["pnl"]-t0["pnl"],t1["funding_pnl"],places=4)
        self.assertEqual(t1["funding_events_applied"],[timestamp])

    def test_holdout_training_unchanged_by_future_data(self):
        def no_signal(*args,**kwargs):
            return None
        with patch("sentinel_core.simulator.decide",side_effect=no_signal):
            original=chronological_holdout(self.fast,self.hour,self.hour,train_fraction=.7)
        fast=self.fast[:]
        at=530
        previous=fast[at]
        fast[at]=Candle(previous.open_time,previous.close_time,
                        100,101,99,100.5,20)
        with patch("sentinel_core.simulator.decide",side_effect=no_signal):
            modified=chronological_holdout(fast,self.hour,self.hour,train_fraction=.7)
        self.assertEqual(original["train"],modified["train"])
        self.assertEqual(original["split_time_ms"],modified["split_time_ms"])

    def test_funding_duplicate_rejected(self):
        ev=FundingEvent(self.fast[101].open_time,.001,100)
        with self.assertRaises(ValueError):
            simulate(self.fast,self.hour,self.hour,funding_events=[ev,ev])

    def test_gap_rejected(self):
        with self.assertRaises(ValueError):
            simulate(self.fast[:120]+self.fast[121:],self.hour,self.hour)

    def test_stale_reference_stream_skips_signal(self):
        old=bars(210,0,HOUR)
        with patch("sentinel_core.simulator.decide",side_effect=self._trigger()):
            out=simulate(self.fast,old,old)
        self.assertEqual(out["trades"],0)

    def test_entry_date_holdout(self):
        start_time=self.fast[300].open_time
        with patch("sentinel_core.simulator.decide",side_effect=self._trigger(start=100)):
            out=simulate(self.fast,self.hour,self.hour,first_entry_ms=start_time)
        self.assertEqual(out["trades"],0)


if __name__=="__main__":
    unittest.main()
