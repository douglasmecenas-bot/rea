"""Testes de duas etapas; valores de RSI simulados apenas em TESTES."""
import unittest
from unittest.mock import patch

from sentinel_core.core import Candle, Signal
from sentinel_core.alerts import SignalTracker, replay_events


HOUR=3600000
STEP=900000


def series(n, step, start=0, base=100, slope=0):
    return [Candle(start+i*step,start+(i+1)*step-1,
                   base+i*slope,base+i*slope+1,base+i*slope-1,
                   base+i*slope,25) for i in range(n)]


class AlertTests(unittest.TestCase):
    def setUp(self):
        self.start=260*HOUR
        self.f=series(70,STEP,self.start)
        self.up=series(330,HOUR,0,100,.2)
        self.btc=series(330,HOUR,0,250,.15)

    def patched_rsi(self,value):
        return patch("sentinel_core.alerts.wilder_rsi",
                     side_effect=lambda values,period:[value]*len(values))

    def test_preliminary_then_confirmed_with_setup_link(self):
        tracker=SignalTracker("ETHUSDT")
        with self.patched_rsi(48), patch("sentinel_core.alerts.decide",return_value=None):
            first=tracker.advance(self.f[:50],self.up,self.btc)
        self.assertEqual(len(first),1)
        self.assertEqual(first[0].event_type,"PRELIMINARY")
        self.assertEqual(first[0].side,"LONG")
        confirm=Signal("LONG",self.f[50].close_time,100,1,99,102,52,1,"test")
        with self.patched_rsi(52), patch("sentinel_core.alerts.decide",return_value=confirm):
            after=tracker.advance(self.f[:51],self.up,self.btc)
        self.assertEqual(len(after),1)
        self.assertEqual(after[0].event_type,"CONFIRMED")
        self.assertEqual(first[0].setup_id,after[0].setup_id)
        self.assertTrue(after[0].preliminary_seen)
        self.assertIsNone(tracker.pending)

    def test_expiry_after_eight_bars(self):
        tracker=SignalTracker("ETHUSDT")
        with self.patched_rsi(48), patch("sentinel_core.alerts.decide",return_value=None):
            first=tracker.advance(self.f[:50],self.up,self.btc)
            events=[]
            for end in range(51,59):
                events.extend(tracker.advance(self.f[:end],self.up,self.btc))
        self.assertEqual([e.event_type for e in events],["EXPIRED"])
        self.assertEqual(events[0].setup_id,first[0].setup_id)

    def test_invalidation_and_cooldown(self):
        tracker=SignalTracker("ETHUSDT")
        with self.patched_rsi(48), patch("sentinel_core.alerts.decide",return_value=None):
            tracker.advance(self.f[:50],self.up,self.btc)
        with self.patched_rsi(35), patch("sentinel_core.alerts.decide",return_value=None):
            events=tracker.advance(self.f[:51],self.up,self.btc)
        self.assertEqual([e.event_type for e in events],["INVALIDATED"])
        with self.patched_rsi(48),patch("sentinel_core.alerts.decide",return_value=None):
            self.assertEqual(tracker.advance(self.f[:52],self.up,self.btc),[])

    def test_direct_confirm_is_not_marked_as_paired(self):
        tracker=SignalTracker("ETHUSDT")
        signal=Signal("LONG",self.f[49].close_time,100,1,99,102,51,1,"test")
        with self.patched_rsi(51),patch("sentinel_core.alerts.decide",return_value=signal):
            events=tracker.advance(self.f[:50],self.up,self.btc)
        self.assertEqual(events[0].event_type,"CONFIRMED")
        self.assertFalse(events[0].preliminary_seen)

    def test_repeated_candle_rejected(self):
        tracker=SignalTracker("ETHUSDT")
        with self.patched_rsi(48),patch("sentinel_core.alerts.decide",return_value=None):
            tracker.advance(self.f[:50],self.up,self.btc)
            with self.assertRaises(ValueError):
                tracker.advance(self.f[:50],self.up,self.btc)

    def test_outdated_context_does_not_emit(self):
        tracker=SignalTracker("ETHUSDT")
        stale=series(201,HOUR,0,100,.2)
        with self.patched_rsi(48),patch("sentinel_core.alerts.decide",return_value=None):
            events=tracker.advance(self.f[:50],stale,stale)
        self.assertEqual(events,[])

    def test_replay_does_not_invent_events(self):
        f=series(110,STEP,260*HOUR)
        h=series(310,HOUR,0,100,0)
        with patch("sentinel_core.alerts.decide",return_value=None):
            output=replay_events("ETHUSDT",f,h,h)
        self.assertEqual(output["mode"],"offline_replay_no_trades")
        self.assertEqual(output["event_count"],0)


if __name__=="__main__":
    unittest.main()
