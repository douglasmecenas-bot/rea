"""Sentinel v0.4: comparar resultados OFFLINE já exportados.

Os arquivos precisam ser de fontes autorizadas e conter P&L líquido em
mesma moeda para comparação quantitativa. Nunca executa frameworks.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .comparator import compare


def main():
    p=argparse.ArgumentParser(description="Sentinel offline export comparator")
    p.add_argument("--sentinel", help="JSON produzido por Sentinel")
    p.add_argument("--freqtrade", help="JSON oficial de Freqtrade backtesting")
    p.add_argument("--freqtrade-strategy", help="Se export contém mais de uma estratégia")
    p.add_argument("--jesse", help="CSV exportado de Jesse com P&L monetário")
    p.add_argument("--output",help="Arquivo JSON novo para persistir resultado")
    args=p.parse_args()
    files=[]
    if args.sentinel:
        files.append(("sentinel",args.sentinel,None))
    if args.freqtrade:
        files.append(("freqtrade",args.freqtrade,args.freqtrade_strategy))
    if args.jesse:
        files.append(("jesse_csv",args.jesse,None))
    try:
        result=compare(files)
        if args.output:
            path=Path(args.output)
            if path.exists():
                raise ValueError("Saída já existe")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        # Não despejar trades privados no terminal por padrão.
        summary={
            "version":result["version"],"sources":[
                {"source":x["source"],"sha256":x["file_sha256"],
                 "per_symbol":x["per_symbol"]} for x in result["reports"]
            ],"warning":result["comparability_warning"],
        }
        print(json.dumps(summary,ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({"status":"invalid_input","reason":str(exc),
                          "fake_results":False},ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
