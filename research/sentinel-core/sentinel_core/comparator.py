"""Normalização OFFLINE de resultados Sentinel, Jesse e Freqtrade.

Nunca executa nem instala frameworks de terceiros. Somente lê arquivos de
resultados produzidos legalmente pelo usuário. Conserva P&L como reportado,
sem recontabilizar custos (dupla contagem seria um erro).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

MAX_FILE = 50_000_000
MAX_TRADES = 200_000


@dataclass(frozen=True)
class Trade:
    source: str
    symbol: str
    side: str
    entry_ms: int
    exit_ms: int
    pnl_quote: float
    original_id: str

    def __post_init__(self):
        if not self.source or not self.symbol or self.side not in ("LONG", "SHORT"):
            raise ValueError("Trades devem especificar origem, ativo e lado")
        if self.entry_ms < 0 or self.exit_ms <= self.entry_ms:
            raise ValueError("Entrada/saída inválida")
        if not isfinite(self.pnl_quote):
            raise ValueError("PnL inválido")


def _time(value) -> int:
    if isinstance(value, (int, float)):
        if not isfinite(value) or value < 0:
            raise ValueError("Timestamp inválido")
        if value >= 1e12:
            return int(value)
        if value >= 1e9:
            return int(value*1000)
        raise ValueError("Unix timestamps devem ser epoch seconds ou milliseconds")
    s = str(value).strip()
    if not s:
        raise ValueError("Timestamp ausente")
    # números explícitos em formato string
    try:
        return _time(float(s))
    except (ValueError, OverflowError):
        pass
    parsed = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Data sem fuso horário: normalize para UTC antes de importar")
    return int(parsed.timestamp()*1000)


def _number(obj: dict, *keys: str) -> float:
    for k in keys:
        if k in obj and obj[k] not in (None, ""):
            val = float(obj[k])
            if not isfinite(val):
                raise ValueError("Número não finito")
            return val
    raise ValueError("Campo numérico obrigatório ausente: "+", ".join(keys))


def _required(obj: dict, *keys: str):
    for k in keys:
        if obj.get(k) not in (None, ""):
            return obj[k]
    raise ValueError("Campo obrigatório ausente: "+", ".join(keys))


def _side(obj: dict):
    if "is_short" in obj:
        v = obj["is_short"]
        if isinstance(v, str):
            v = v.lower() in ("true", "1", "yes")
        return "SHORT" if v else "LONG"
    val = str(_required(obj, "side", "type", "position_type")).upper()
    if val in ("SHORT", "SELL"):
        return "SHORT"
    if val in ("LONG", "BUY"):
        return "LONG"
    raise ValueError("Lado LONG/SHORT não reconhecido")


def _sentinel(doc: dict) -> list[Trade]:
    src = doc.get("evaluation",doc)
    if "walk_forward" in src:
        segments = [f["test"] for f in src["walk_forward"]["results"]]
    elif "trade_log" in src:
        segments = [src]
    elif "trades" in src and isinstance(src["trades"], list):
        segments = [src]
    elif "result" in src:
        segments = [src["result"]]
    else:
        raise ValueError("Relatório Sentinel não reconhecido")
    sym = str(doc.get("symbol", "UNKNOWN"))
    out = []
    for part in segments:
        for i, t in enumerate(part.get("trade_log", part.get("trades", []))):
            out.append(Trade("sentinel",sym,_side(t),
                 _time(_required(t,"entry_at")),
                 _time(_required(t,"exit_at")),
                 _number(t,"pnl"),str(t.get("original_id",i))))
    return out


def _freqtrade(doc: dict, strategy: str | None) -> list[Trade]:
    if "strategy" not in doc or not isinstance(doc["strategy"],dict):
        raise ValueError("Formato Freqtrade exige objeto 'strategy' do JSON exportado")
    names = sorted(doc["strategy"])
    if strategy is None:
        if len(names) != 1:
            raise ValueError("Múltiplas estratégias: informe --strategy explicitamente")
        strategy = names[0]
    if strategy not in doc["strategy"]:
        raise ValueError("Estratégia não encontrada no JSON exportado")
    records = doc["strategy"][strategy].get("trades")
    if not isinstance(records,list):
        raise ValueError("Freqtrade não contém trades na estratégia selecionada")
    out = []
    for i,t in enumerate(records):
        out.append(Trade("freqtrade",str(_required(t,"pair")),
                         _side(t),
                         _time(_required(t,"open_date","open_timestamp")),
                         _time(_required(t,"close_date","close_timestamp")),
                         _number(t,"profit_abs"),
                         str(t.get("trade_id",i))))
    return out


def _jesse(rows: list[dict]) -> list[Trade]:
    """Adapter explícito para CSV; cabeçalhos podem variar entre versões Jesse.

    Exige PnL monetário, NÃO aceita apenas profit percentage.
    """
    out=[]
    for i,r in enumerate(rows):
        out.append(Trade("jesse",str(_required(r,"symbol","pair")),
                         _side(r),
                         _time(_required(r,"entry_time","opened_at","entry_date")),
                         _time(_required(r,"exit_time","closed_at","exit_date")),
                         _number(r,"pnl","PNL","profit_abs","pnl_quote"),
                         str(r.get("id",i))))
    return out


def read_trades(path: str | Path, kind: str,
                strategy: str | None = None) -> tuple[list[Trade], dict]:
    if kind not in ("sentinel","freqtrade","jesse_csv"):
        raise ValueError("Formatos aceitos: sentinel, freqtrade, jesse_csv")
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ValueError("Arquivo ausente ou maior que 50MB")
    contents = path.read_bytes()
    digest = sha256(contents).hexdigest()
    if kind == "jesse_csv":
        with path.open("r",encoding="utf-8-sig",newline="") as fd:
            records=list(csv.DictReader(fd))
        trades=_jesse(records)
    else:
        doc=json.loads(contents)
        if not isinstance(doc,dict):
            raise ValueError("Relatório JSON deve ser objeto")
        trades=_sentinel(doc) if kind=="sentinel" else _freqtrade(doc,strategy)
    if len(trades) > MAX_TRADES:
        raise ValueError("Trade count excede limite")
    trades=sorted(trades,key=lambda x:(x.exit_ms,x.entry_ms,x.original_id))
    seen=set()
    for t in trades:
        key=(t.source,t.symbol,t.entry_ms,t.exit_ms,t.original_id)
        if key in seen:
            raise ValueError("Trades duplicados; importação recusada")
        seen.add(key)
    return trades,{
        "kind":kind,"sha256":digest,"trade_count":len(trades),
        "origin_verified":False,
        "pnl_unit":"reported_quote_currency_not_normalized",
        "notice":"Fee/funding assumed included as reported; provenance and method not independently audited",
    }


def trade_statistics(trades: list[Trade]) -> dict:
    wins=[t.pnl_quote for t in trades if t.pnl_quote>0]
    losses=[t.pnl_quote for t in trades if t.pnl_quote<0]
    gross=sum(wins)
    loss_abs=-sum(losses)
    # P&L quote currencies may differ! Caller MUST partition by asset/market.
    return {
      "trade_count":len(trades),
      "total_reported_pnl":round(sum(t.pnl_quote for t in trades),6),
      "win_rate":len(wins)/len(trades) if trades else None,
      "profit_factor":gross/loss_abs if loss_abs else None,
      "expectancy_quote_per_trade":sum(t.pnl_quote for t in trades)/len(trades) if trades else None,
      "gross_profit":round(gross,6),"gross_loss_abs":round(loss_abs,6),
      "first_exit_ms":trades[0].exit_ms if trades else None,
      "last_exit_ms":trades[-1].exit_ms if trades else None,
      "risk_not_comparable_without_normalization":True,
    }


def compare(inputs: list[tuple[str,str,str|None]]) -> dict:
    if not inputs:
        raise ValueError("Nenhuma fonte")
    exports=[]
    for name,path,strategy in inputs:
        kind=name
        trades,metadata=read_trades(path,kind,strategy)
        groups={}
        for trade in trades:
            groups.setdefault(trade.symbol,[]).append(trade)
        exports.append({
          "source":kind,"file_sha256":metadata["sha256"],
          "meta":metadata,
          "per_symbol":{k:trade_statistics(v) for k,v in sorted(groups.items())},
          "trades":[asdict(t) for t in trades]
        })
    return {
      "version":"sentinel-v0.4-audit",
      "reports":exports,
      "comparability_warning":(
        "Absolute PnL and win rates are NOT meaningful cross-framework comparisons "
        "without matching timestamps, symbol, asset quote, strategy, notional, "
        "initial balance, fees, funding and fills. NO profitability inference."
      ),
    }
