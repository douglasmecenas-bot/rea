import csv
from pathlib import Path
import tempfile
import unittest

from sentinel_core.history import MarketStore
from sentinel_core.import_csv import read_csv


def write_csv(path, fields, rows):
    with open(path,"w",newline="",encoding="utf-8") as out:
        writer=csv.DictWriter(out,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def candle_rows(count, symbol="BTCUSDT", interval="15m"):
    rows=[]
    for i in range(count):
        rows.append({
            "symbol":symbol,"interval":interval,
            "open_time":i*900000,"close_time":(i+1)*900000-1,
            "open":"100","high":"103","low":"99",
            "close":"101","volume":"500"})
    return rows


class CsvImportTests(unittest.TestCase):
    def test_candles_roundtrip_with_provenance(self):
        with tempfile.TemporaryDirectory() as root:
            f=Path(root)/"data.csv"
            rows=candle_rows(5)
            write_csv(f,list(rows[0]),rows)
            data,meta=read_csv(f,"candles","BTCUSDT","15m")
            self.assertEqual(len(data),5)
            self.assertEqual(len(meta["csv_sha256"]),64)
            self.assertEqual(meta["source_authenticity"],
                             "NOT_VERIFIED_user_supplied_CSV")
            with MarketStore(Path(root)/"db.sqlite") as store:
                store.put_candles("BTCUSDT","15m",data)
                actual=store.get_candles("BTCUSDT","15m",0,5*900000)
                self.assertEqual(data,actual)

    def test_refuse_csv_with_gap(self):
        with tempfile.TemporaryDirectory() as root:
            f=Path(root)/"gap.csv"
            rows=candle_rows(5)
            rows.pop(2)
            write_csv(f,list(rows[0]),rows)
            with self.assertRaises(ValueError):
                read_csv(f,"candles","BTCUSDT","15m")

    def test_refuse_other_symbol(self):
        with tempfile.TemporaryDirectory() as root:
            f=Path(root)/"mixed.csv"
            rows=candle_rows(4)
            rows[1]["symbol"]="ETHUSDT"
            write_csv(f,list(rows[0]),rows)
            with self.assertRaises(ValueError):
                read_csv(f,"candles","BTCUSDT","15m")

    def test_refuse_funding_duplicate(self):
        with tempfile.TemporaryDirectory() as root:
            f=Path(root)/"fund.csv"
            rows=[
                {"symbol":"ETHUSDT","funding_time":1000,"rate":.001,"mark_price":100},
                {"symbol":"ETHUSDT","funding_time":1000,"rate":.002,"mark_price":101},
            ]
            write_csv(f,list(rows[0]),rows)
            with self.assertRaises(ValueError):
                read_csv(f,"funding","ETHUSDT")

    def test_funding_csv_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            f=Path(root)/"fund.csv"
            rows=[
                {"symbol":"ETHUSDT","funding_time":1000,"rate":.001,"mark_price":100},
                {"symbol":"ETHUSDT","funding_time":2000,"rate":-.002,"mark_price":101},
            ]
            write_csv(f,list(rows[0]),rows)
            data,meta=read_csv(f,"funding","ETHUSDT")
            self.assertEqual(meta["funding_schedule_completeness"],"unverified")
            with MarketStore(":memory:") as store:
                store.put_funding("ETHUSDT",data)
                self.assertEqual(store.get_funding("ETHUSDT",0,3000),data)


if __name__=="__main__":
    unittest.main()
