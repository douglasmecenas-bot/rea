# Sentinel Atlas v0.4 — terminal independente de pesquisa

**Estado real da entrega:** aplicação local funcional com leitura SQLite, gráficos e relatórios; comparador de exportações, rastreabilidade e replay de alertas. **Não é serviço de sinais em tempo real, corretora ou sistema lucrativo validado.** Nenhum código de EAssets, Pionex, Freqtrade ou Jesse foi copiado para este motor.

## Execução inicial

Clonar sua branch REA de pesquisa. Usar Python 3.12+:

    cd research/sentinel-core
    python -m unittest discover -s tests -v
    python -m sentinel_core.dashboard --db data/sentinel.sqlite --reports-dir runs --port 8765

Abrir **somente no próprio PC**: http://127.0.0.1:8765.

A interface funciona com base vazia (exibe "SEM DADOS", não inventa cotações). Com SQLite preenchido, mostrará símbolos/timeframes, gráficos de fechamento dos candles registrados, tamanho do histórico e relatórios JSON em runs/. A interface é original, responsiva e totalmente local; a execução no Chrome é exercitada em GitHub Actions sem chamadas de mercado.

O servidor é **read-only** e atende exclusivamente na interface loopback; não configure reverse proxy nem publique a porta. Possui validação do cabeçalho Host, sem POST/PUT/DELETE permitidos, tamanho limitado para leitura dos relatórios e nomes de arquivo sem caminhos arbitrários.

## Dados históricos

A alternativa preferida é usar datasets com licença adequada e origem verificável. Leia [V03-GUIDE.md](V03-GUIDE.md) para duas rotas: a coleta de endpoint público da Binance quando permitido/possível, e importação de CSV fornecido pelo usuário.

Em 17/10/2026, a verificação automática da Binance Futures no GitHub Actions encontrou **HTTP 451**. Não será contornada, e a sonda foi alterada para execução manual. Não há dataset de mercado real incluído aqui, nem evidências de performance com dados reais.

Arquivos devem ficar **fora do Git público**: data/ para SQLite; runs/ para relatórios. Nunca subir chaves API, CSV proprietário, sessões autenticadas ou capturas com cookies.

## Comparador de motores

Use exportações **já produzidas fora deste projeto**, obtidas legitimamente por você. Adaptadores de leitura são originais; não executam nem dependem de frameworks externos.

    python -m sentinel_core.compare_cli \
      --sentinel runs/eth-walkforward.json \
      --freqtrade /caminho/export-freqtrade.json \
      --freqtrade-strategy NomeExato \
      --jesse /caminho/export-jesse.csv \
      --output runs/comparacao.json

Cada argumento é opcional, mas deve haver ao menos uma fonte. Freqtrade aceita JSON de backtest com objeto "strategy" e registros "trades"; se múltiplas estratégias, informe a estratégia. Jesse usa CSV com cabeçalhos \`symbol\` ou \`pair\`, \`side\` ou \`type\`, \`entry_time\`, \`exit_time\` e **PNL monetário** \`pnl\` / \`PNL\` / \`profit_abs\` / \`pnl_quote\`. Os nomes reais podem variar entre versões; ajuste o mapeamento conforme o arquivo e teste novamente, sem adivinhar o significado de colunas.

Datas devem ter timezone explícito, por exemplo "2026-09-01T12:30:00+00:00"; Unix seconds ou milliseconds também são aceitos. Na saída, a unidade dos valores PNL é **a unidade reportada pela origem**, e taxas/funding são entendidos como já incluídos. Não somar PNL de moedas quote diferentes nem comparar métricas quando notional, custos, janelas ou instrumentos divergem. O relatório exige inspeção humana antes de qualquer alegação de superioridade.

Documentação original: https://docs.freqtrade.io/en/stable/backtesting/ e https://docs.jesse.trade/docs/backtest/exports

## Motor de alertas em duas etapas

A ferramenta **não envia alertas a Telegram/Discord**. Produz eventos para auditoria local com um replay histórico:

    python -m sentinel_core.replay_cli \
      --symbol ETHUSDT --start 2026-09-01 --end 2026-10-15 \
      --db data/sentinel.sqlite --out runs/alerts.json

Abra/atualize a aba "Alertas simulados" do painel. O navegador carregará no máximo os 500 eventos recentes do arquivo \`runs/alerts.json\` e indicará que são históricos, não live.

Estados possíveis:
- PRELIMINARY: RSI14 perto da linha 50, preço próximo EMA20, confirmação prévia de contexto EMA50/EMA200 no 1h e regime BTC EMA200 no 1h.
- CONFIRMED: cruzamento RSI50 em candle fechado com regras do núcleo e possível vínculo a uma antecipação anterior (ou \`preliminary_seen=false\` em cruzamentos rápidos).
- INVALIDATED: rompimento de limites contrários ao setup ou mudança de regime.
- EXPIRED: ausência de confirmação dentro de oito candles 15m.
- Cooldown: oito candles depois de encerrado o ciclo; sem múltiplos alertas por candle.

Essas regras são experimentais; não foram otimizadas nem validadas estatisticamente. **Nenhum evento representa recomendação financeira ou execução.** O motor é determinístico para o mesmo conjunto de candles e estratégia.

## Segurança / impedimentos atuais

1. **GitHub Actions passou testes sintéticos offline, não backtest de dados Binance.** Nenhuma afirmação de retorno lucrativo foi produzida.
2. **Binance USD-M HTTP 451** no runner da plataforma. Precisa de fonte legítima de dados históricos para avaliar a estratégia.
3. **REA autenticado no EAssets pendente**. Só observar interfaces autorizadas; nunca extrair secrets ou contornar proibições de automação.
4. **Freqtrade / Jesse / Hummingbot não instalados**. O comparador lê arquivos exportados; isso não equivale à integração operacional com esses motores.
5. **GitHub atualmente é fork público de REA**. Para separar comercialmente o Sentinel, crie um repositório **privado** próprio, migre com revisão e preserve o REA como laboratório.
6. Não implantar execução de trades nem adquirir produtos de sinais até conclusão de backtests, paper trading e auditoria de segurança/contratos.

## Próximas entregas requerendo ambiente e decisões

- Repositório privado independente Sentinel.
- Arquivos históricos autorizados com séries 15m/1h suficientes e funding auditado, caso Binance pública permaneça bloqueada.
- Backtest walk-forward prolongado, igualdade de timestamps/instrumento com comparador Freqtrade e Jesse; métricas de exposição, Sharpe, Calmar, amostra e confiança.
- Integração de alertas em sandbox Telegram/Discord sem permissão de trade, com credenciais mantidas fora do Git.
- Paper trading conectado a fonte autorizada, respeitando jurisdição e políticas de corretora.
- Segurança e aprovação explícita antes de ordens reais; limite de perdas diário e kill switch para operação real.
