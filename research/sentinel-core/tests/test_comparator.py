"""Testes exclusivamente offline para comparadores de Freqtrade, Jesse e Sentinel."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

from sentinel_core.comparator import read_trades, trade_statistics, compare


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)

    def save(self,name,data):
        p=self.folder/name
        p.write_text(json.dumps(data),encoding="utf-8")
        return p

    def csv(self,name,rows):
        p=self.folder/name
        with p.open("w",encoding="utf-8",newline="") as out:
            writer=csv.DictWriter(out,fieldnames=list(rows[0]))
            writer.writeheader();writer.writerows(rows)
        return p

    def test_freqtrade_export_keeps_reported_net_pnl(self):
        doc={"strategy":{"RSI":{
          "trades":[
            {"pair":"ETH/USDT:USDT","is_short":False,
             "open_date":"2026-09-01T10:00:00+00:00",
             "close_date":"2026-09-01T10:45:00+00:00",
             "profit_abs":1.25},
            {"pair":"ETH/USDT:USDT","is_short":True,
             "open_date":"2026-09-02T10:00:00Z",
             "close_date":"2026-09-02T11:00:00Z",
             "profit_abs":-2.5},
           ]}}}
        path=self.save("freq.json",doc)
        trades,meta=read_trades(path,"freqtrade")
        self.assertEqual([t.side for t in trades],["LONG","SHORT"])
        self.assertAlmostEqual(trade_statistics(trades)["total_reported_pnl"],-1.25)
        self.assertEqual(meta["origin_verified"],False)

    def test_freqtrade_requires_explicit_strategy_if_multiple(self):
        path=self.save("multi.json",{"strategy":{"a":{"trades":[]},"b":{"trades":[]}}})
        with self.assertRaises(ValueError):
            read_trades(path,"freqtrade")
        trades,_=read_trades(path,"freqtrade","a")
        self.assertEqual(trades,[])

    def test_jesse_csv_explicit_net_pnl_and_timezone(self):
        path=self.csv("jesse.csv",[
          {"symbol":"BTC-USDT","side":"long","entry_time":"2026-08-01T10:00:00+00:00",
           "exit_time":"2026-08-01T10:15:00+00:00","pnl":"14.25"},
          {"symbol":"BTC-USDT","side":"short","entry_time":"2026-08-02T10:00:00+00:00",
           "exit_time":"2026-08-02T10:15:00+00:00","pnl":"-2.15"}])
        trades,_=read_trades(path,"jesse_csv")
        self.assertEqual(len(trades),2)
        self.assertAlmostEqual(trade_statistics(trades)["win_rate"],.5)
        self.assertAlmostEqual(trade_statistics(trades)["profit_factor"],14.25/2.15)

    def test_reject_naive_time_to_prevent_time_alignment_errors(self):
        path=self.csv("naive.csv",[{
          "symbol":"BTCUSDT","side":"long",
          "entry_time":"2026-08-01 10:00:00","exit_time":"2026-08-01 11:00:00",
          "pnl":"2"}])
        with self.assertRaises(ValueError):
            read_trades(path,"jesse_csv")

    def test_sent_v03_walkforward_uses_test_only(self):
        entry=1_780_000_000_000
        fake={"symbol":"BTCUSDT","walk_forward":{"results":[
          {"train":{"trade_log":[{"entry_at":entry,"exit_at":entry+900000,"side":"SHORT","pnl":100}]},
           "test":{"trade_log":[{"entry_at":entry+1800000,"exit_at":entry+3600000,"side":"LONG","pnl":-10}]}}
        ]}}
        path=self.save("wf.json",fake)
        trades,_=read_trades(path,"sentinel")
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0].pnl_quote,-10)

    def test_sent_v02_holdout_uses_only_test(self):
        entry=1_780_000_000_000
        x={"symbol":"ETHUSDT","evaluation":{
            "train":{"trade_log":[{"entry_at":entry,"exit_at":entry+900000,"side":"LONG","pnl":999}]},
            "test":{"trade_log":[{"entry_at":entry+1800000,"exit_at":entry+3600000,"side":"SHORT","pnl":-5}]}
        }}
        trades,_=read_trades(self.save("v02.json",x),"sentinel")
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0].pnl_quote,-5)

    def test_trade_metrics_and_empty(self):
        x=trade_statistics([])
        self.assertIsNone(x["win_rate"])
        self.assertIsNone(x["profit_factor"])
        self.assertEqual(x["trade_count"],0)

    def test_duplicate_trades_rejected(self):
        at=1_780_000_000_000
        row={"symbol":"BTCUSDT","side":"LONG","entry_time":at,
             "exit_time":at+900000,"pnl":1.25,"id":"a"}
        path=self.csv("dups.csv",[row,row])
        with self.assertRaises(ValueError):
            read_trades(path,"jesse_csv")

    def test_compared_results_show_caution(self):
        path=self.csv("report.csv",[{
            "symbol":"BTCUSDT","side":"LONG","entry_time":1_780_000_000_000,
            "exit_time":1_780_000_900_000,"pnl":2.0
        }])
        out=compare([("jesse_csv",str(path),None)])
        self.assertIn("NOT meaningful",out["comparability_warning"])
        self.assertEqual(out["reports"][0]["per_symbol"]["BTCUSDT"]["trade_count"],1)


if __name__=="__main__":
    unittest.main()
