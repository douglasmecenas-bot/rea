# Estudo de plataformas: REA + produto próprio

**Data:** 15/10/2026  
**Status:** reconhecimento público documentado; captura técnica com REA preparada, **ainda não executada**.  
**Objetivo:** observar recursos acessíveis publicamente, separar fatos de hipóteses, e projetar software original.

## Alvos e limites

| Referência | Evidência pública confirmada | Ainda não verificado | Ação permitida e prioridade |
| --- | --- | --- | --- |
| MyCryptoPanel — https://mycryptopanel.com/ e /terminal | Site anuncia futuros Binance, preço, variação, OI, LSR, RSI 1m/5m/15m/1h/4h/1d, ordenação e radar gratuito; HTML da página /terminal só mostrou estado inicial de carregamento. | Fluxos concretos de WebSocket, scripts, periodicidade, tratamento de erros e fórmula de Power RSI. | **P1**: captura passiva do navegador com REA, sem login, bypass ou dados privados. |
| EAssets — https://eassets.ai/en | Marketing público anuncia screener de >500 ativos, indicadores de derivativos, watchlist, filtros, setups, timeline, exportação JSON para IA, mapa e comparação por sessão. | Fórmulas proprietárias, estrutura real de backend, contrato de API e latência mensurada. | **P2**: benchmarking funcional baseado em material público; **não automatizar coleta sem permissão expressa** (Termos vedam scripts/bots não autorizados). |
| Binance-API MyCryptoPanel — https://binance-api.mycryptopanel.com/ | Nenhuma documentação pública confirmada nesta investigação. | Autoria, função, política de acesso e segurança. | **P2 bloqueado**: não submeter chaves, não presumir API pública, não sondar endpoints ocultos. |
| Habblaud — https://habblaud.com/ ; https://github.com/marmottajr/habblaud | Repositório de código aberto MIT; visualização de sessões de Claude Code/Codex, salas, atividade e pedidos de aprovação. | Infra de implantação e comportamento em produção. | **P3**: ler código aberto e licença antes de qualquer REA; melhor como ferramenta de desenvolvimento. |
| Viver de IA — https://viverdeia.ai/paid | Site público divulga ecossistema B2B com soluções de IA, conteúdo de formação, mentoria e cases. | Plataforma após autenticação, pagamentos, templates completos e funcionamento interno. | **P3**: pesquisa de fluxos públicos de catálogo e páginas institucionais, sem ingressar em área privada. |

### Evidências públicas utilizadas

- MyCryptoPanel: https://mycryptopanel.com/ e https://mycryptopanel.com/terminal
- EAssets: https://eassets.ai/en e **Termos** https://eassets.ai/en/terms
- Habblaud: https://github.com/marmottajr/habblaud e https://habblaud.com/
- Viver de IA: https://viverdeia.ai/ e https://viverdeia.ai/treinamento-de-ia-para-empresas
- Documentação oficial do REA: docs/browser-observation.md, docs/website-script-export.md e docs/web-network-captures.md (neste próprio repositório)
- Documentação oficial Binance: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api

**Convenção de evidência:** 'observado' = página pública ou código-fonte aberto efetivamente lidos; 'divulgado' = alegação do fornecedor; 'hipótese' = não confirmado; 'capturado pelo REA' = somente com artifact e timestamp do REA, que ainda não existem.

## Produto proposto: núcleo de inteligência de criptoativos

O escopo viável do primeiro produto é um **Radar de Futuros + Sentinel**, não clonar todos os cinco negócios. Recursos de educação corporativa e escritório de agentes pertencem a outro produto/módulo e não devem inflar o MVP.

### MVP 1

1. **Ingestão autorizada:** Binance USDⓈ-M REST e WebSocket oficiais, com limites de taxa, reconexão e indicação de atraso.
2. **Normalização:** símbolos, intervalos, velas, volume, funding, OI e LSR. Distinguir razão por *contas* de razão por *posições*.
3. **Indicadores próprios:** RSI multi-tempo, EMA, ATR, variação 24h, força relativa ao BTC; exibir fórmula e versão.
4. **Radar e filtros:** busca por ativo, ordenação, confluência entre períodos, watchlist e registro do timestamp.
5. **Motor Sentinel:** pré-sinal, confirmação, invalidação e filtros de volatilidade; nenhuma ordem real por padrão.
6. **Auditoria:** reproduzir cada sinal em histórico e reter fonte, configuração, custos e momento da decisão.
7. **Backtest e simulação:** taxas, slippage, liquidez, períodos fora da amostra e paper trading antes de execuções reais.

### Arquitetura inicial (proposta, não descoberta sobre terceiros)

```
Binance REST / WebSocket
  -> market-data gateway (ratelimit, retries, reconnect, health)
  -> data normalization + candles/derivatives storage
  -> indicator engine (versioned)
  -> signal/risk/backtest engine
  -> REST + event stream -> web radar / alert manager
```

Sugestão de stack: **TypeScript/Node.js**, PostgreSQL + TimescaleDB (se necessário), Redis para cache e pub/sub, frontend React/Next.js, testes automatizados. Escolha definitiva depende de requisitos de carga e orçamento.

### Critérios de aceite do primeiro protótipo

- Feeds Binance documentados; nenhuma credencial de trade para modo somente leitura.
- Indicadores comparados com casos de referência e testes determinísticos, inclusive bordas de janela.
- Dados com timestamp de origem, delay visível e detecção de stale feeds.
- Decisões de entrada/saída auditáveis; custos e risco explícitos; sem promessas de lucro.
- Separação de dados de fontes terceiras; nenhuma redistribuição incompatível com licenças.
- Observabilidade: erros por ativo, desconexões e data gaps.

## Próxima execução do REA

Veja [REA-RUNBOOK.md](REA-RUNBOOK.md) e [capture-public-site.sh](capture-public-site.sh).

**Importante:** possuir o repositório no GitHub não significa que o REA esteja instalado/conectado a um navegador. Esta investigação inicial não inspecionou bundles privados, não interceptou tráfego autenticado e não executou o MCP REA. Conectar e rodar uma sessão local ou num runner compatível é o próximo passo de coleta de evidências.
