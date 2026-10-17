# Sentinel v0.3 — Walk-forward e proveniência dos dados

**Status:** pesquisa quantitativa experimental. **Sem ordens reais e sem chaves de exchange.** O GitHub Actions validou o núcleo apenas com testes offline sintéticos. Não há evidência de rentabilidade ou edge em mercado real.

## 1. Por que não rodamos backtest real no CI?

A sonda de conectividade pública acessou exclusivamente https://fapi.binance.com e recebeu **HTTP 451** no GitHub-hosted runner, em 17/10/2026. Não devemos contornar essa restrição. O log registra HTTP 451, e o artifact com pequeno JSON de diagnóstico foi salvo para análise.

https://github.com/douglasmecenas-bot/rea/actions/runs/39072032035

A sonda passou a ser **manual (workflow_dispatch)** para evitar requisições repetidas; exige que o workflow já esteja na branch padrão para disparo pelo GitHub web.

## 2. Trabalhar com histórico autorizado no seu próprio PC

Duas rotas alternativas, conforme acesso legítimo ao mercado:

**A) Binance Futures pública disponível e permitida no ambiente local:**

Na pasta research/sentinel-core:

    python -m sentinel_core.pipeline collect \
      --symbol ETHUSDT --start 2026-09-01 --end 2026-10-15 \
      --db data/sentinel.sqlite --max-pages 40

O programa rejeita gaps de candles e armazena SHA-256 da série. Eventos de funding são baixados com paginação, porém **a completude segundo o calendário oficial não está verificada**.

**B) CSV histórico obtido de fonte autorizada pelo usuário** (nenhuma conexão com exchange):

    python -m sentinel_core.import_csv candles --symbol ETHUSDT --interval 15m \
      --file /caminho/ETHUSDT-15m.csv --db data/sentinel.sqlite

    python -m sentinel_core.import_csv candles --symbol ETHUSDT --interval 1h \
      --file /caminho/ETHUSDT-1h.csv --db data/sentinel.sqlite

    python -m sentinel_core.import_csv candles --symbol BTCUSDT --interval 1h \
      --file /caminho/BTCUSDT-1h.csv --db data/sentinel.sqlite

    python -m sentinel_core.import_csv funding --symbol ETHUSDT \
      --file /caminho/ETHUSDT-funding.csv --db data/sentinel.sqlite

Os CSVs de candles devem conter **open_time,close_time,open,high,low,close,volume** com timestamps Unix em **milissegundos UTC**. Podem conter colunas opcionais **symbol** e **interval**, que serão verificadas. A série deve ser cronológica e sem gaps, ou a importação falha. Funding: **funding_time,rate,mark_price**, com coluna symbol opcional.

O hash SHA-256 protege a rastreabilidade do arquivo e da série depois da importação, **mas não comprova que a origem fornecida pelo usuário é autêntica**. Valide fornecedor, fuso, intervalos, períodos sem negociação e licenças.

Não publique CSVs comerciais ou privados no repositório público; os bancos locais e relatórios ficam em data/ e runs/ ignorados pelo Git.

## 3. Avaliação walk-forward

Com pelo menos 28 dias de histórico de candles 15m (10 dias treino, 9 dias aquecimento e 3 folds de 3 dias):

    python -m sentinel_core.walkforward_cli \
      --symbol ETHUSDT --start 2026-09-01 --end 2026-10-15 \
      --train-days 10 --warmup-days 9 --test-days 3 --folds 3 \
      --db data/sentinel.sqlite --report runs/eth-walkforward.json

O relatório inclui:
- Estratégia explicitada e hash da configuração; dados identificados por SHA-256.
- 3 janelas OOS sequenciais, sem sobreposição, **ancoradas no fim** dos dados disponíveis, cada qual com contexto histórico de warmup.
- Para cada fold: período treino, período teste, número de trades, retorno líquido estimado, drawdown pessimista baseado em barras e comparações hipotéticas buy-and-hold, short-and-hold e ficar em caixa.
- Agregado hipotético dos retornos OOS compostos, indicação de baixa amostragem quando são menos de 30 trades OOS.
- Funding: se dados presentes, eventos usados com **cobertura não confirmada**, se ausentes use --omit-funding e rotule resultado sem funding.

**Importante:** Folds sequenciais com parâmetros fixos são avaliação de robustez; esta implementação não seleciona nem otimiza parâmetros em cada janela. Não é um processo completo de otimização walk-forward. Qualquer ajuste motivado por resultados OOS torna esses períodos parte da pesquisa, e exige novo holdout verdadeiramente intocado.

**Não comparar diretamente o retorno do Sentinel ao benchmark sem ajustar tempo de exposição, risco e funding; buy/short hold assume 100% notional e sem funding.**

## 4. Segurança e limitações

- Não possui módulo de envio de ordens, credenciais Binance ou alavancagem.
- DataStore SQLite local, fecha em erro de conflito histórico, rejeita candles faltando ou duplicados.
- Stop e alvo atingidos na mesma vela => stop primeiro; fills e pior extremo intrabar são aproximações pessimistas.
- Slippage e fee são hipóteses parametrizadas; não medem spread e liquidez reais.
- Funding aplicado por evento com markPrice informado e timestamp, sem cronologia intrabar comprovada.
- Os relatórios OOS não devem virar afirmações de rentabilidade futura.
- **Freqtrade, Jesse e Hummingbot ainda não foram incorporados.** A próxima fase é criar comparador de resultados por schema comum, preservando licenças.

## 5. Execução dos testes (offline)

    python -m unittest discover -s tests -v

GitHub Actions: .github/workflows/sentinel-core-tests.yml. A suíte não acessa rede nem executa trades.

Documentação oficial: https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data
