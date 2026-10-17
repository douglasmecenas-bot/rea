# Fronteiras de pesquisa e produto

| Componente | Agora | Pronto para produção? |
| --- | --- | --- |
| Dados históricos | SQLite, CSV verificado estruturalmente, conector Binance público bloqueado HTTP 451 no runner | Não |
| Estratégia de tendência | RSI14, EMA20, regime EMA50/200 e BTC, filtro 24h | Não há evidência de edge |
| Backtest | next-bar open, fee/slippage estimadas, financiamento informado | Não; sem book/fills reais |
| Walk-forward | Folds fixos com OOS separados | Insuficiente para alegar robustez |
| Comparador Freqtrade/Jesse | Leitor de exportações locais | Versões/campos reais ainda precisam de testes |
| Alertas | PRELIMINARY, CONFIRMED, INVALIDATED, EXPIRED | Apenas replay offline |
| Painel visual | Navegação, série local, relatório e eventos offline | Somente desktop local |
| REA | Análise autorizada e documentação de pesquisa | Não executado no EAssets autenticado |
| Execução financeira | Não existe | Bloqueada por design |
| Serviços pagos | Nenhum | Não planejados nesta fase |

**Objetivo de produto:** Terminal Sentinel original, independente de ferramentas profissionais da LEC/Lovable, com código próprio e eventual comparação com open source sem violações de licença.

**Origem dos frameworks**: Freqtrade GPLv3, Jesse MIT, Hummingbot Apache-2.0, OctoBot GPLv3. Referências e interfaces externas somente; revisão técnica e jurídica antes de incorporar código. Não copiar código, imagens ou endpoints privados de EAssets/Pionex.
