import unittest
from unittest.mock import patch
from sentinel_core.data import BinancePublic, MarketDataError


class DataTests(unittest.TestCase):
    def test_input_guard(self):
        c=BinancePublic()
        with self.assertRaises(ValueError):
            c.klines("../orders","15m")
        with self.assertRaises(ValueError):
            c.klines("BTCUSDT","3m")
        with self.assertRaises(ValueError):
            c.klines("BTCUSDT","15m",1600)

    def test_ignore_open_candle(self):
        c=BinancePublic()
        raw=[
            [0,"100","103","99","101","10",899999],
            [900000,"101","105","100","102","11",1799999],
        ]
        with patch.object(c,"_get",return_value=raw):
            candles=c.klines("BTCUSDT","15m",2,now_ms=1000000)
            self.assertEqual(len(candles),1)
            self.assertEqual(candles[0].close,101)

    def test_ticker_validation(self):
        c=BinancePublic()
        with patch.object(c,"_get",return_value={"symbol":"BADUSDT"}):
            with self.assertRaises(MarketDataError):
                c.ticker24("BTCUSDT")


if __name__ == "__main__":
    unittest.main()
