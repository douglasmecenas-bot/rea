# Sentinel v0.2 — histórico reproduzível e simulação auditável

**Status:** experimental, sem ordens e sem operação de dinheiro real.

Módulos originais em Python:
- \`sentinel_core/data.py\`: cliente Binance USD-M público, sem credenciais; caminho e host fixos.
- \`sentinel_core/history.py\`: paginação por janelas UTC fechadas, integridade, hash SHA-256 e persistência SQLite de OHLCV/funding.
- \`sentinel_core/simulator.py\`: simulação com sinal na vela fechada e execução na abertura seguinte, taxas, slippage, funding (se informado), worst-case intrabar estimado e holdout cronológico.
- \`sentinel_core/pipeline.py\`: CLI de coleta e avaliação **offline**.
- \`tests/\`: testes sintéticos offline (não demonstram lucro).

## Requisitos

Python >=3.10, somente biblioteca padrão. Não há API keys nem conectores a EAssets/Pionex. Rede requerida apenas para \`collect\`.

### 1. Executar testes

Dentro de \`research/sentinel-core\`:

    python -m unittest discover -s tests -v

### 2. Coletar dados públicos oficiais

As datas são **UTC**, começo incluso e final **exclusivo** (00:00 UTC). Exemplo de 30 dias:

    python -m sentinel_core.pipeline collect --symbol ETHUSDT --start 2026-09-01 --end 2026-10-01 --db data/sentinel.sqlite --max-pages 50

Essa operação baixa candles de 15m/1h do ativo, 1h de BTC como referência, e eventos históricos de funding (markPrice conforme fornecido pela API). Ela utiliza páginas limitadas, rejeita gaps, exige candles já fechados, confere cobertura e grava SHA-256 de cada série. Em falha, não fabrica cotações.

**Não execute coleta em CI público**. O acesso pode ser indisponível conforme rede, regras regionais e rate limits. Respeitar os termos da Binance.

### 3. Avaliar localmente sem rede

    python -m sentinel_core.pipeline evaluate --symbol ETHUSDT --start 2026-09-01 --end 2026-10-01 --db data/sentinel.sqlite --output runs/eth-sep2026.json

Usa SQLite já populado. O relatório contém holdout cronológico fixo 70/30, o mesmo saldo inicial para as duas janelas, fees/funding parametrizados, histórico dos trades, SHA da série e riscos. Se o histórico estiver incompleto, para com erro.

    python -m sentinel_core.pipeline evaluate --symbol ETHUSDT --start 2026-09-01 --end 2026-10-01 --db data/sentinel.sqlite --omit-funding

O segundo comando desliga funding **explicitamente** e deve ser rotulado como cenário incompleto. Mesmo com eventos no SQLite, a cobertura histórica de funding é marcada como **não auditada independentemente**.

## Como interpretar resultados

- Valores com fees/slippage são **estimativas**. 9 bps por lado de fee + 2 bps/slippage por lado por padrão; diferenças por VIP/maker/taker, funding e impacto real precisam ser medidas.
- Sinais apenas no fechamento; entradas apenas na próxima abertura; referências BTC/ativo 1h exigem candles fechados e recentes.
- Estratégia: RSI14 cruza 50 no 15m, EMA20 no 15m, EMA50/200 no 1h, filtro BTC EMA200 no 1h, 24h via 96 candles de 15m; stop 1,5 ATR14 e alvo 2R.
- O cálculo de worst-case intrabar considera low/high inteiro da vela mesmo que preço tivesse atingido alvo antes do extremo. Por isso é pessimista, **não prova ordem intrabar**.
- Stop e alvo simultâneos no mesmo candle => stop. Funding na barra de saída é aproximado; a sequência temporal da liquidação de funding e stop não é conhecida a partir de OHLCV.
- Posição fechada por tempo máximo ou fim do conjunto; cálculos de abertura em gap penalizam stop.
- O holdout cronológico é **um único split**, sem tuning ou validação walk-forward repetida. Não usar como prova de rentabilidade; requer períodos mais longos, regimes diferentes, tamanhos mínimos amostrais e comparação com benchmarks.
- Os primeiros 200 candles 1h do intervalo são warmup da EMA200; candles anteriores ao primeiro dia podem ser necessários para não perder sinais no início da janela. O backfill v0.2 coleta no próprio início e exclui as primeiras horas por warmup, **não atribui histórico anterior fictício**.
- Proibir operações reais até auditoria externa, teste de reconexão, tratamento de exchange precision e longos períodos de forward/paper trading.

## Evidências e limite

Fonte oficial: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data
Funding: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
Projeto REA: https://github.com/morluto/rea
Projetos de comparação: Freqtrade (GPLv3), Jesse (MIT), Hummingbot (Apache-2.0).

**Nenhum destes projetos externos foi incorporado ao módulo.** Trabalhar em separado até análise de licenças e arquitetura. **Não foi executado REA contra EAssets.**

## Critérios da próxima etapa v0.3

1. Reavaliar marcação intrabar usando datasets de granularidade menor e/ou trades tick-by-tick.
2. Funding com cobertura auditada por cronograma histórico e mudanças de intervalos de cada contrato.
3. Walk-forward com várias janelas, bootstrap de confiança, comparador Freqtrade/Jesse via formato neutro de resultados.
4. Stop/limit com liquidez, regras de precisão, maker/taker, ordens parciais e drawdown correto com markPrice minuto a minuto.
5. UI de auditoria, sinais pré-confirmados, notificações Telegram/Discord e paper trading isolado.
