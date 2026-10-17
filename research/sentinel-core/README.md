# Sentinel Atlas — v0.4: auditoria e sinais históricos

**Novo:** painel web em `127.0.0.1`, comparador de exportações Sentinel/Freqtrade/Jesse, replay offline de sinais PRELIMINARY/CONFIRMED/INVALIDATED/EXPIRED, documentação de escopo e testes Chromium. [Manual completo](V04-GUIDE.md) · [Fronteiras do produto](PRODUCT-BOUNDARIES.md).

**Não há dinheiro real nem alertas live.** A Binance Futures pública retornou HTTP 451 no runner do GitHub; nada aqui contorna acesso bloqueado.

Iniciar interface local, na pasta `research/sentinel-core/`:

    python -m sentinel_core.dashboard --db data/sentinel.sqlite --reports-dir runs --port 8765

---

# Sentinel Core — v0.3 laboratório quantitativo independente

**Atualização v0.3:** walk-forward com múltiplas janelas OOS sequenciais, benchmarks simples, sonda de disponibilidade de dados Binance e importação OFFLINE de CSV autorizado, para evitar dependência de endpoints inacessíveis. Detalhes: [V03-GUIDE.md](V03-GUIDE.md).

**Verificação externa:** O GitHub Actions recebeu HTTP 451 da API Binance Futures em 17/10/2026; portanto nenhum backtest real foi executado neste ambiente. Não contornaremos o bloqueio. A suíte offline é executada com dados sintéticos e é verificada pela CI. Nenhuma ordem real, credencial ou serviço pago é utilizado.

---

# Sentinel Core — v0.2 em desenvolvimento

**Atualização:** implementada coleta histórica paginada, SQLite com validação de cobertura, funding histórico e simulador com holdout cronológico. A v0.1 continua preservada como baseline. **Sem ordens reais e sem uso de dinheiro.**

Para a versão nova, instruções de coleta e avaliação: [V02-GUIDE.md](V02-GUIDE.md). Os testes sintéticos são executados pelo GitHub Actions. Nenhuma estratégia foi comprovada lucrativa nem executada com históricos reais neste CI.

---

## Versão inicial v0.1 — referência
**Status:** experimental v0.1 | **Ordens reais:** NÃO IMPLEMENTADAS | **Modo:** análise e backtest offline.

Implementação nova e original em Python, apenas biblioteca padrão. Usa endpoints **públicos da Binance USD-M Futures**, sem chaves API e sem depender de EAssets, Pionex ou grupos de sinais pagos.

Este módulo foi instalado provisoriamente sob research/sentinel-core do fork REA, para facilitar o trabalho com GitHub. A aplicação comercial deve morar em repositório independente; manter REA como ferramenta de pesquisa. Nenhum código de terceiros foi copiado.

## Execução

No diretório research/sentinel-core com Python >=3.10:

    python -m unittest discover -s tests -v
    python -m sentinel_core.cli contracts
    python -m sentinel_core.cli analyze --symbol ETHUSDT
    python -m sentinel_core.cli backtest --symbol ETHUSDT

Os testes rodam offline. Os comandos de consulta só funcionam quando a Binance está acessível do ambiente e seus limites de uso permitem. Não usar VPN/bypass para contornar regras ou restrições de serviço. Erro de rede não gera preços fictícios.

## Estratégia demonstrativa

1. Candle 15m fechado: RSI14 cruzando a linha de 50; fechamento acima/abaixo de EMA20.
2. Candles 1h fechados: EMA50 acima/abaixo EMA200, e BTC acima/abaixo de sua EMA200.
3. Bloqueio LONG se variação 24h inferior a -10%; SHORT se superior a +15%. No backtest, a variação é aproximada com 96 velas 15m, e não o ticker contínuo da Binance.
4. Stop ATR14*1.5, alvo 2x o risco, uma posição por vez.
5. Simulação de execução na abertura da vela SEGUINTE ao sinal; sem lookahead; stop prioritário quando stop e target alcançados dentro da mesma vela.
6. Limite de sizing: orçamento de perda estimada de 1% da equity, com taxa 0,09% por lado, slippage hipotético de 2 bps por lado e teto de notional igual à equity (SEM alavancagem).

Nenhum destes parâmetros produz garantia de lucro. A estratégia não foi otimizada nem validada fora da amostra.

## Limites da simulação

- OHLCV não modela bid/ask, fila, liquidez, impacto no mercado ou fills reais.
- Não calcula funding, liquidação, impostos, precisão de contrato ou taxas específicas de ativo/cliente.
- Drawdown informado é só após fechamento de posições, não inclui drawdown intraposição.
- Consultas de até 1500 candles tornam períodos históricos curtos; necessitamos backfill e testes walk-forward.
- A função decide filtra candles com timestamps futuros e rejeita séries duplicadas/desordenadas. Não inferir causalidade de resultados da simulação.
- A ferramenta BinancePublic só lê exchangeInfo, klines, ticker24, premiumIndex, openInterest. NÃO assina requests ou envia ordens.

## Componentes open source avaliados para integração

| Projeto | Módulo visado | Licença da origem |
|---|---|---|
| freqtrade/freqtrade | laboratório/backtesting, FreqAI | GPL-3.0 |
| jesse-ai/jesse | replay e estratégia | MIT |
| hummingbot/hummingbot | arquitetura de conectores e execução | Apache-2.0 |
| Drakkar-Software/OctoBot | UX, templates de Grid e DCA | GPL-3.0 |
| nautechsystems/nautilus_trader | engine orientado a eventos | LGPL-3.0 |

**Ainda não instalados nem integrados.** Usar código GPL/LGPL em produto comercial exige cumprir obrigações de licença; não combinar projetos indiscriminadamente. Preferir comparação de resultados e adapters externos sobre copiar bases de código.

## Próximos critérios de aceite

- Testes CI concluídos, incluindo casos positivos de LONG e SHORT com fixtures artificiais e prova de ausência de lookahead.
- Backtest com candles históricos persistidos, walk-forward, múltiplos regimes de mercado e histórico de taxas reais.
- Replay auditável para sinais de canais, com latência, edições e cancelamentos, quando o dono do conteúdo autorizar.
- Comparações quantitativas entre as implementações do nosso motor e frameworks Freqtrade/Jesse por interface explícita.
- Adapter opcional Hummingbot apenas após security review, setup isolado e paper trading.
- Dashboard e alertas integrados somente depois da qualidade de dados.

## Fontes

- Binance REST oficial: https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data
- REA e limitações de observação: https://github.com/morluto/rea/blob/main/docs/browser-observation.md
- Repositórios: https://github.com/freqtrade/freqtrade ; https://github.com/jesse-ai/jesse ; https://github.com/hummingbot/hummingbot

REA não concede acesso ao backend proprietário, e acesso a um site não autoriza extração irrestrita. Recursos de terceiros devem ser documentados por licença, documentação ou uso autorizado.
