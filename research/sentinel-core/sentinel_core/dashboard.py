"""Servidor local SOMENTE LEITURA do Sentinel.

É uma interface de auditoria de arquivo, não um terminal de negociação.
Não possui POST, WebSocket de ordens, tokens, chaves ou endpoints privados.
Bind fixo no loopback 127.0.0.1. NÃO publicar com proxy/rede externa.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qs
import sqlite3
import sys

from .data import VALID_INTERVALS, _symbol
from .webui import DOCUMENT

FILE_LIMIT = 10_000_000
REPORT = re.compile(r"^[A-Za-z0-9_.-]+\.json$")


def _json(obj):
    return json.dumps(obj,ensure_ascii=False,allow_nan=False).encode("utf-8")


def build_handler(db_path: str | Path, reports_dir: str | Path):
    db_path=Path(db_path)
    reports_dir=Path(reports_dir)

    def summarize_db() -> list[dict]:
        if not db_path.is_file():
            return []
        con=sqlite3.connect(f"file:{db_path.resolve()}?mode=ro",uri=True,timeout=2)
        try:
            rows=con.execute(
                "SELECT symbol,interval,COUNT(*),MIN(open_time),MAX(open_time) "
                "FROM candles GROUP BY symbol,interval ORDER BY symbol,interval"
            ).fetchall()
            return [
                {"symbol":s,"interval":i,"candles":n,
                 "first_open_ms":t0,"last_open_ms":t1,
                 "source":"locally_saved_unverified_input"}
                for s,i,n,t0,t1 in rows
            ]
        finally:
            con.close()

    def candles(symbol: str, interval: str, limit: int):
        _symbol(symbol)
        if interval not in VALID_INTERVALS or not 1<=limit<=2000:
            raise ValueError("Consulta inválida")
        if not db_path.is_file():
            return []
        con=sqlite3.connect(f"file:{db_path.resolve()}?mode=ro",uri=True,timeout=2)
        try:
            rows=con.execute(
              "SELECT open_time,close_time,open,high,low,close,volume "
              "FROM candles WHERE symbol=? AND interval=? "
              "ORDER BY open_time DESC LIMIT ?",(symbol,interval,limit)
            ).fetchall()
            return [dict(zip(("open_time","close_time","open","high","low","close","volume"),r))
                    for r in reversed(rows)]
        finally:
            con.close()

    def reports():
        if not reports_dir.exists():
            return []
        items=[]
        for path in sorted(reports_dir.iterdir(),key=lambda p:p.name):
            if (not path.is_file() or path.is_symlink()
                    or not REPORT.fullmatch(path.name)
                    or path.stat().st_size > FILE_LIMIT):
                continue
            items.append({"name":path.name,"bytes":path.stat().st_size})
        return items

    def get_report(name):
        if not REPORT.fullmatch(name):
            raise ValueError("Nome de relatório inválido")
        file=reports_dir/name
        if file.is_symlink() or not file.is_file() or file.stat().st_size>FILE_LIMIT:
            raise FileNotFoundError("Relatório não encontrado")
        return json.loads(file.read_text(encoding="utf-8"))

    class Handler(BaseHTTPRequestHandler):
        server_version="SentinelLocalResearch/0.4"
        def _send(self, payload: bytes, status=200, mime="application/json; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(len(payload)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Referrer-Policy","no-referrer")
            self.send_header("X-Frame-Options","DENY")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; script-src 'self' 'unsafe-inline';"
                             " style-src 'self' 'unsafe-inline'; connect-src 'self';"
                             " img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            split=urlsplit(self.path)
            params=parse_qs(split.query)
            try:
                if split.path in ("/","/index.html"):
                    return self._send(DOCUMENT.encode("utf-8"),mime="text/html; charset=utf-8")
                if split.path=="/api/health":
                    return self._send(_json({
                        "version":"0.4","mode":"offline_read_only","trading_enabled":False,
                        "market_data_live":False,"source_verified":False,
                        "reports_dir_configured":True,
                    }))
                if split.path=="/api/markets":
                    return self._send(_json({"markets":summarize_db()}))
                if split.path=="/api/candles":
                    return self._send(_json({
                      "candles":candles(params.get("symbol",["BTCUSDT"])[0],
                                        params.get("interval",["15m"])[0],
                                        int(params.get("limit",["350"])[0])),
                      "source":"local_SQLite_not_live",
                    }))
                if split.path=="/api/reports":
                    return self._send(_json({"reports":reports()}))
                if split.path=="/api/report":
                    return self._send(_json({
                        "report":get_report(params.get("name",[""])[0]),
                        "source":"local_report_user_supplied_not_verified",
                    }))
                return self._send(_json({"error":"not_found"}),404)
            except (ValueError,TypeError,sqlite3.Error) as exc:
                return self._send(_json({"error":"bad_request","details":str(exc)[:300]}),400)
            except (FileNotFoundError,PermissionError) as exc:
                return self._send(_json({"error":"not_found","details":str(exc)[:300]}),404)
            except (OSError,json.JSONDecodeError) as exc:
                return self._send(_json({"error":"file_unavailable","details":str(exc)[:300]}),500)

        def do_POST(self):
            return self._send(_json({"error":"read_only_no_mutations"}),405)

        def do_PUT(self):
            return self.do_POST()

        def do_DELETE(self):
            return self.do_POST()

    return Handler


def main() -> int:
    parser=argparse.ArgumentParser(description="Sentinel auditoria SOMENTE LOCAL e leitura")
    parser.add_argument("--db",default="data/sentinel.sqlite")
    parser.add_argument("--reports-dir",default="runs")
    parser.add_argument("--port",type=int,default=8765)
    args=parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise SystemExit("Porta precisa ser 1024..65535")
    try:
        with ThreadingHTTPServer(("127.0.0.1",args.port),
                                 build_handler(args.db,args.reports_dir)) as server:
            print(f"Sentinel offline audit: http://127.0.0.1:{args.port}")
            print("Apenas leitura; não compartilhar via rede pública.")
            server.serve_forever()
    except (KeyboardInterrupt, OSError) as exc:
        print(f"Encerrado: {exc}",file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
