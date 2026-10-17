import http.client
import json
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from http.server import ThreadingHTTPServer

from sentinel_core.core import Candle
from sentinel_core.history import MarketStore
from sentinel_core.dashboard import build_handler
from sentinel_core.webui import DOCUMENT


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.root=tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.base=Path(self.root.name)
        self.db=self.base/"test.sqlite"
        self.reports=self.base/"runs"
        self.reports.mkdir()
        with MarketStore(self.db) as store:
            store.put_candles("BTCUSDT","15m",[
                Candle(i*900000,(i+1)*900000-1,100+i,101+i,99+i,100+i,100)
                for i in range(5)
            ])
        self.http=ThreadingHTTPServer(("127.0.0.1",0),
            build_handler(self.db,self.reports))
        self.thread=Thread(target=self.http.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.shutdown)

    def shutdown(self):
        self.http.shutdown();self.http.server_close();self.thread.join(timeout=4)

    def request(self,path,method="GET",host=None):
        c=http.client.HTTPConnection("127.0.0.1",self.http.server_port,timeout=5)
        headers={} if host is None else {"Host":host}
        c.request(method,path,headers=headers)
        r=c.getresponse()
        content=r.read().decode("utf-8")
        result=r.status,r.getheader("Content-Type"),content
        c.close()
        return result

    def test_home_is_app_with_no_external_js(self):
        status,mime,text=self.request("/")
        self.assertEqual(status,200)
        self.assertIn("Sentinel Atlas",text)
        self.assertIn("PAPER ONLY",text)
        self.assertNotIn("<script src=",text)
        self.assertIn("127.0.0.1",text)

    def test_health_has_no_trading(self):
        status,_,text=self.request("/api/health")
        self.assertEqual(status,200)
        obj=json.loads(text)
        self.assertFalse(obj["trading_enabled"])
        self.assertFalse(obj["market_data_live"])

    def test_market_data_real_from_temp_db(self):
        s,_,text=self.request("/api/markets")
        self.assertEqual(s,200)
        self.assertEqual(json.loads(text)["markets"][0]["candles"],5)
        s,_,text=self.request("/api/candles?symbol=BTCUSDT&interval=15m")
        self.assertEqual(s,200)
        series=json.loads(text)["candles"]
        self.assertEqual(len(series),5)
        self.assertEqual(series[4]["close"],104)
        self.assertEqual(json.loads(text)["source"],"local_SQLite_not_live")

    def test_report_list_and_safe_file_open(self):
        (self.reports/"sample.json").write_text('{"evaluation":{"test":{"return_pct":-5}}}',
                                                encoding="utf-8")
        s,_,raw=self.request("/api/reports")
        self.assertEqual(s,200)
        self.assertEqual(json.loads(raw)["reports"][0]["name"],"sample.json")
        s,_,raw=self.request("/api/report?name=sample.json")
        self.assertEqual(s,200)
        self.assertEqual(json.loads(raw)["report"]["evaluation"]["test"]["return_pct"],-5)
        s,_,_=self.request("/api/report?name=..%2Fsecret.json")
        self.assertEqual(s,400)

    def test_remote_host_denied_even_on_loopback(self):
        s,_,raw=self.request("/api/reports",host="bad.example.com")
        self.assertEqual(s,403)
        self.assertEqual(json.loads(raw)["error"],"untrusted_host")

    def test_no_trade_mutations(self):
        for meth in ("POST","PUT","DELETE"):
            s,_,raw=self.request("/api/health",method=meth)
            self.assertEqual(s,405)
            self.assertEqual(json.loads(raw)["error"],"read_only_no_mutations")

    def test_invalid_symbol_and_interval_denied(self):
        for arg in ("symbol=../../../api","interval=99m","limit=999999"):
            s,_,raw=self.request("/api/candles?"+arg)
            self.assertEqual(s,400)

    def test_static_markup_contains_all_views(self):
        for word in ('id="overview"','id="research"','id="reports"',
                     'id="method"','id="chart"','id="reportList"'):
            self.assertIn(word,DOCUMENT)


if __name__=="__main__":
    unittest.main()
