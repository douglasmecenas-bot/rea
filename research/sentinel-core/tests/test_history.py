import tempfile
import unittest
from pathlib import Path

from sentinel_core.core import Candle
from sentinel_core.data import MarketDataError
from sentinel_core.history import (
    FundingEvent, MarketStore, backfill_candles, backfill_funding, validate_series)


STEP = 900_000


def candle(i):
    start = i*STEP
    price = 100+i
    return Candle(start,start+STEP-1,price,price+1,price-1,price,12)


class FakeClient:
    def __init__(self, candles):
        self.candles=candles
        self.requests=[]

    def klines(self,symbol,interval,limit,now_ms,start_ms,end_ms):
        self.requests.append((start_ms,end_ms,limit))
        return [c for c in self.candles
                if start_ms <= c.open_time <= end_ms][:limit]


class HistoryTests(unittest.TestCase):
    def test_backfill_uses_bounded_pages_and_proves_full_coverage(self):
        client=FakeClient([candle(i) for i in range(7)])
        items=backfill_candles(client,"BTCUSDT","15m",0,7*STEP,
                               page_size=3,max_pages=3,now_ms=8*STEP)
        self.assertEqual(len(items),7)
        self.assertEqual(client.requests,[(0,3*STEP-1,3),
                                           (3*STEP,6*STEP-1,3),
                                           (6*STEP,7*STEP-1,3)])
        self.assertEqual(validate_series(items,"15m")["gaps"],[])

    def test_reject_missing_candle(self):
        client=FakeClient([candle(i) for i in [0,1,3,4]])
        with self.assertRaises(MarketDataError):
            backfill_candles(client,"BTCUSDT","15m",0,5*STEP,
                             page_size=5,now_ms=6*STEP)

    def test_refuse_incomplete_current_window(self):
        with self.assertRaises(ValueError):
            backfill_candles(FakeClient([]),"BTCUSDT","15m",0,5*STEP,
                             now_ms=4*STEP)
        with self.assertRaises(ValueError):
            backfill_candles(FakeClient([]),"BTCUSDT","15m",1,2*STEP,
                             now_ms=4*STEP)

    def test_sqlite_idempotency_conflict_and_complete_range(self):
        with tempfile.TemporaryDirectory() as root:
            with MarketStore(Path(root)/"market.sqlite") as store:
                items=[candle(i) for i in range(4)]
                store.put_candles("BTCUSDT","15m",items)
                store.put_candles("BTCUSDT","15m",items)
                again=store.get_candles("BTCUSDT","15m",0,4*STEP)
                self.assertEqual(items,again)
                with self.assertRaises(ValueError):
                    store.get_candles("BTCUSDT","15m",0,5*STEP)
                modified=Candle(0,STEP-1,100,101,99,100.5,12)
                with self.assertRaises(ValueError):
                    store.put_candles("BTCUSDT","15m",[modified])
                self.assertEqual(items,store.get_candles("BTCUSDT","15m",0,4*STEP))

    def test_funding_pagination_store_roundtrip(self):
        events=[FundingEvent(1000,.001,100),FundingEvent(2000,-.002,110),
                FundingEvent(3000,.003,120)]
        class FakeFunding:
            def funding_rates(self,symbol,start_ms,end_ms,limit):
                return [{"symbol":symbol,"fundingTime":e.funding_time,
                         "fundingRate":str(e.rate),"markPrice":str(e.mark_price)}
                        for e in events if start_ms <= e.funding_time <= end_ms][:limit]
        result=backfill_funding(FakeFunding(),"BTCUSDT",500,4000,page_size=2)
        self.assertEqual(result,events)
        with MarketStore(":memory:") as db:
            db.put_funding("BTCUSDT",result)
            db.put_funding("BTCUSDT",result)
            self.assertEqual(db.get_funding("BTCUSDT",500,4000),events)

    def test_series_checksum_detects_rewritten_candle(self):
        original=[candle(i) for i in range(4)]
        changed=original[:]
        changed[2]=Candle(2*STEP,3*STEP-1,102,103,101,102.5,12)
        self.assertNotEqual(validate_series(original,"15m")["sha256"],
                            validate_series(changed,"15m")["sha256"])


if __name__=="__main__":
    unittest.main()
