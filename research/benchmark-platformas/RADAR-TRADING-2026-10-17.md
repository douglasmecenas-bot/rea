# Radar de ferramentas de cripto, sinais e bots — 17/10/2026

## Evidências verificadas

Este documento é uma **pesquisa de mercado**; não é backtest e não demonstra rentabilidade de produto algum. O objetivo é subsidiar produto próprio Sentinel Atlas, mantendo a plataforma comercial separada do repositório REA.

| Referência | Capacidades comprovadas em documentação ou código aberto | Possível uso | Ressalvas |
|---|---|---|---|
| Pionex | Bots integrados Spot Grid, Futures Grid, DCA e gerenciamento de ordens; sem mensalidade separada nos bots nativos (segundo a empresa); custos de ordens e funding | Benchmark de automação e UX | Lucro de grades pode coexistir com prejuízo total; futuros podem liquidar; conferir taxas, disponibilidade regional e KYC |
| SuperTradingAIbot no Telegram | Perfil público de bot @supertradingaibot que se apresenta como assistente IA para gráficos e setups | Estudar apresentação de sinal e explicação | **Sem retorno auditado independente localizado**, preço e metodologia do grupo pago não confirmados; número de usuários não comprova acerto |
| TradingView | Estratégias Pine Script, alertas dinâmicos e webhooks | Editor de setups e alerta para Discord/Telegram | Simulação histórica não equivale a execução real |
| Cornix | Sinais Telegram/Discord, autoexecução, integração com exchange, stop e take-profit | Pipeline de ingestão/normalização de sinais | Executor não garante qualidade do provedor |
| 3Commas | DCA e Signal Bots por TradingView e JSON | Automação baseada em regras | Chaves API, custos, segurança de terceiros |
| CoinGlass | Open Interest, funding, mapas de liquidação estimada, APIs com planos específicos | Filtro de liquidez e contexto do mercado | Heatmap é estimativa, não preço alvo garantido; API do mapa requer Professional ou Enterprise |
| CryptoQuant | Métricas on-chain, exchange inflow e reserves | Filtro macro e contexto on-chain | Métrica isolada não é sinal determinístico |
| LuxAlgo | Indicadores, estratégias e alertas com IA em TradingView; comunidade Discord | Benchmark de UX para criador de regras | Métricas comerciais exigem auditoria |
| Freqtrade | Código GPL-3.0, backtest, otimização e dry-run, FreqAI | Prototipar e validar estratégias | Copiar código GPL para produto proprietário requer análise jurídica de obrigações |
| Hummingbot | Apache-2.0, controllers, executors, market making, grid e conectores CEX/DEX | Arquitetura de execução com conectores | Complexidade; cada estratégia exige gestão de risco |
| OctoBot | GPL-3.0, Web UI, Grid/DCA, TradingView, paper trading, bots IA | Referência de aplicação completa | GPL-3.0 e partes beta |
| Jesse | MIT, pesquisa quantitativa/backtesting, múltiplos timeframes e paper/live | Motor de estratégias | Verificar diferenças por edição/licenciamento comercial |
| NautilusTrader | LGPL-3.0, engine orientado a eventos Rust | Arquitetura de execução resiliente | Revisar obrigações de linking/distribuição; implementação complexa |
| FinRL | MIT, pesquisa de RL para finanças | Laboratório de IA e pesquisa | IA não demonstra retorno positivo por si só |

## Fontes oficiais / primárias

Pionex:
- https://www.pionex.com/blog/is-there-any-fees-for-starting-a-bot-or-only-transaction-fees/
- https://www.pionex.com/blog/futures-grid/
- https://www.pionex.com/blog/pt/pionex-blog-crypto-trading-bot-2/
- https://www.pionex.com/blog/pionex-fee-trx-grid-is-0-05-buy-0-05-sell-or-0-05-fee-buy-sell/

Telegram:
- https://t.me/supertradingaibot
- https://www.telegramstats.org/advertisers/tg-supertradingaibot (terceiro, atividade publicitária; não auditoria de resultados)

Automação e sinais:
- https://help.cornix.io/en/articles/8800202-what-is-the-cornix-signals-bot
- https://help.3commas.io/en/articles/16300161-moving-from-3commas-v1-to-3commas-v2-feature-bot-migration-guide
- https://br.tradingview.com/pine-script-docs/faq/alerts/

Derivativos / análise:
- https://docs.coinglass.com/reference/liquidation-heatmap
- https://www.coinglass.com/pt/learn/coinglass-intro-en
- https://cryptoquant.com/asset/qnt/chart/exchange-flows
- https://discord.com/servers/luxalgo-641770286638694402

GitHub:
- https://github.com/freqtrade/freqtrade — GPL-3.0
- https://github.com/hummingbot/hummingbot — Apache-2.0
- https://github.com/Drakkar-Software/OctoBot — GPL-3.0
- https://github.com/jesse-ai/jesse — MIT
- https://github.com/nautechsystems/nautilus_trader — LGPL-3.0
- https://github.com/AI4Finance-Foundation/FinRL — MIT
- https://github.com/enarjord/passivbot

Comunidades oficiais:
- Freqtrade Discord https://discord.gg/p7nuUNVfP7 (referenciado no README oficial)
- Hummingbot Discord https://discord.com/servers/hummingbot-530578568154054663 (ficha da comunidade)
- LuxAlgo Discord https://discord.com/servers/luxalgo-641770286638694402

## Plano de auditoria comparável dos sinais e bots

1. Para um canal de sinais: catalogar **todos** os sinais consecutivos emitidos antes dos eventos, com UTC, símbolo, corretora, sentido, faixa, invalidade, stop, alvos, cancelamento e edições. Não confiar em prints retroativos.
2. Reproduzir cada sinal a partir de preços negociáveis (bid/ask), latência realista, spread, slippage, fees, funding, liquidação e alavancagem.
3. Relatar taxa de acerto + payoff médio + expectativa líquida + drawdown + profit factor + exposição simultânea; separar estratégias, moedas e períodos de mercado.
4. Fazer shadow trading sem dinheiro por 30 dias para qualidade operacional; depois uma amostra suficientemente ampla em múltiplos regimes, com teste fora da amostra. A janela de 30 dias é **triagem**, não comprovação estatística de edge.
5. Para Pionex: demonstrativo integral de bot, capital inicial e aportes/saques, histórico de trades, P&L realizado e não realizado, fees/funding, drawdown, data de início; não usar apenas "grid profit" ou APY anualizado.

## Proposta de arquitetura (produto original, não cópia)

Binance dados oficiais -> normalização/timeframes -> features RSI/EMA/ATR/OI/long-short/funding -> classificadores de regime -> motor de sinais e risco -> simulador/backtest/forward -> alertas (Telegram/Discord) -> UI auditável.

Complementos: market making/grids orientados ao regime (ideias Hummingbot e Pionex), adaptador de sinais externos como Cornix, editor de estratégias como TradingView/LuxAlgo, análise de liquidações como CoinGlass (licença/API adequada), explicações IA e diário de evidências.

**Priorização:** primeiro Freqtrade ou Jesse para pesquisa + Hummingbot para arquitetura de execução + Pionex para benchmark Grid + Cornix para pipeline de sinais. Após validar dados e custos, integrar ao Sentinel. **Nunca habilitar operações com dinheiro automaticamente.**

Licenças devem ser analisadas antes de reutilizar qualquer componente no software comercial. Estudar ideias/funcionalidades não concede direito de copiar software proprietário.
