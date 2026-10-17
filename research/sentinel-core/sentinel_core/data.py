"""Cliente somente leitura para endpoints públicos da Binance USD-M Futures."""
from __future__ import annotations
import json
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .core import Candle

BASE = "https://fapi.binance.com"
VALID_INTERVALS = {"1m", "5m", "15m", "1h", "4h", "1d"}
SYMBOL = re.compile(r"^[A-Z0-9]{4,24}$")


class MarketDataError(RuntimeError):
    pass


def _symbol(value: str) -> str:
    if not SYMBOL.fullmatch(value):
        raise ValueError("Symbol inválido (ex.: BTCUSDT)")
    return value


class BinancePublic:
    """Somente GET público em caminhos autorizados; nenhuma chave, assinatura ou ordem."""
    def __init__(self, timeout: int = 10):
        if timeout < 1 or timeout > 60:
            raise ValueError("timeout deve ser 1..60")
        self.timeout = timeout

    def _get(self, path: str, **params):
        if path not in ("/fapi/v1/klines", "/fapi/v1/ticker/24hr",
                        "/fapi/v1/exchangeInfo", "/fapi/v1/premiumIndex",
                        "/fapi/v1/openInterest"):
            raise ValueError("Endpoint não autorizado")
        url = BASE + path + ("?" + urlencode(params) if params else "")
        req = Request(url, headers={"User-Agent": "SentinelResearch/0.1",
                                    "Accept": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                if response.status != 200:
                    raise MarketDataError(f"HTTP {response.status}")
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise MarketDataError("Resposta maior que limite")
                return json.loads(raw)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise MarketDataError(f"Binance indisponível: {type(exc).__name__}") from exc

    def klines(self, symbol: str, interval: str, limit: int = 500,
               now_ms: int | None = None) -> list[Candle]:
        symbol = _symbol(symbol)
        if interval not in VALID_INTERVALS:
            raise ValueError("Intervalo inválido")
        if not (1 <= limit <= 1500):
            raise ValueError("limit deve ser 1..1500")
        payload = self._get("/fapi/v1/klines", symbol=symbol,
                            interval=interval, limit=limit)
        if not isinstance(payload, list):
            raise MarketDataError("Klines inválidas")
        now_ms = int(time.time()*1000) if now_ms is None else now_ms
        candles = []
        for row in payload:
            if not isinstance(row, list) or len(row) < 7:
                raise MarketDataError("Registro de kline malformado")
            item = Candle(open_time=int(row[0]), close_time=int(row[6]),
                          open=float(row[1]), high=float(row[2]),
                          low=float(row[3]), close=float(row[4]),
                          volume=float(row[5]))
            if item.close_time < now_ms:
                candles.append(item)
        if any(candles[i].close_time >= candles[i+1].close_time
               for i in range(len(candles)-1)):
            raise MarketDataError("Candles duplicados ou desordenados")
        return candles

    def ticker24(self, symbol: str) -> dict:
        symbol = _symbol(symbol)
        payload = self._get("/fapi/v1/ticker/24hr", symbol=symbol)
        if not isinstance(payload, dict) or payload.get("symbol") != symbol:
            raise MarketDataError("Ticker inconsistente")
        return {
            "symbol": symbol, "price": float(payload["lastPrice"]),
            "change_pct_24h": float(payload["priceChangePercent"]),
            "quote_volume_24h": float(payload["quoteVolume"]),
            "close_time_ms": int(payload["closeTime"]),
            "source": "Binance USD-M public ticker24",
        }

    def contracts(self) -> list[str]:
        payload = self._get("/fapi/v1/exchangeInfo")
        if not isinstance(payload, dict):
            raise MarketDataError("exchangeInfo inválido")
        return sorted(s["symbol"] for s in payload.get("symbols", [])
                      if s.get("quoteAsset") == "USDT"
                      and s.get("contractType") == "PERPETUAL"
                      and s.get("status") == "TRADING")

    def derivatives(self, symbol: str) -> dict:
        symbol = _symbol(symbol)
        premium = self._get("/fapi/v1/premiumIndex", symbol=symbol)
        oi = self._get("/fapi/v1/openInterest", symbol=symbol)
        if premium.get("symbol") != symbol or oi.get("symbol") != symbol:
            raise MarketDataError("Derivativos inconsistentes")
        return {
            "symbol": symbol, "mark_price": float(premium["markPrice"]),
            "funding_rate": float(premium["lastFundingRate"]),
            "next_funding_time_ms": int(premium["nextFundingTime"]),
            "open_interest_contracts": float(oi["openInterest"]),
            "open_interest_time_ms": int(oi["time"]),
            "source": "Binance USD-M public derivatives",
        }
