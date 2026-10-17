# Protocolo técnico: observação passiva de sites com REA

## Status e limites

Este documento é um roteiro para **executar** o REA. Os comandos abaixo foram conferidos contra `docs/browser-observation.md` do fork. **Não declarar execução antes de existirem artefatos REA datados.**

REA via GitHub é código versionado: o conector GitHub não é um servidor MCP do REA nem um browser. Para realizar a observação precisa de Node.js >=22.19 (ou 24.x >=24.11, ou 26+), REA instalado e navegador Chromium com porta CDP em loopback.

Uso apenas de páginas públicas e investigação autorizada. **EAssets** restringe bots/scripts de coleta sem autorização expressa; excluído de captura automatizada neste protocolo. Não abrir conteúdos autenticados, contornar paywalls, descobrir segredos ou testar falhas de segurança de terceiros.

## 1. Instalar REA localmente

No próprio fork, seguir `docs/installation.md` e preferir pacote oficial auditado:

```bash
node --version
npx rea-agents setup
rea --help
```

Revisar todas as alterações propostas pelo setup. A instalação não é realizada por este documento.

## 2. Iniciar Chromium separado para captura consentida

Exemplo no Linux:

```bash
chromium --remote-debugging-port=9222 \
  --user-data-dir=/tmp/rea-public-research \
  --no-first-run \
  https://mycryptopanel.com/terminal
```

Em sistemas diferentes, ajustar executável/caminho. Não expor 9222 à rede. Usar perfil limpo, sem sessões pessoais, sem chaves/API/contas.

## 3. Descobrir alvo

```bash
rea list-browser-targets http://127.0.0.1:9222 --json
```

Localizar na saída o ID do alvo de `https://mycryptopanel.com`. Confirmar origem e URL. Substituir `TARGET_ID` pelo identificador **real** retornado, não por um ID de exemplo.

## 4. Capturar evidências read-only

```bash
mkdir -p research/benchmark-platformas/_captures/mycryptopanel
rea inspect-web-page http://127.0.0.1:9222 TARGET_ID \
  --observation-ms 1000 --include-json-body-shapes \
  --include-websocket-shapes --json \
  > research/benchmark-platformas/_captures/mycryptopanel/page.json

rea analyze-web-bundle http://127.0.0.1:9222 TARGET_ID --json \
  > research/benchmark-platformas/_captures/mycryptopanel/bundle.json

rea capture-web-screenshot http://127.0.0.1:9222 TARGET_ID --json \
  > research/benchmark-platformas/_captures/mycryptopanel/screenshot.json
```

A inspeção CDP do REA é passiva: não navega nem aciona botões. Se houver interação necessária, realizá-la **manualmente** e capturar uma segunda sessão ou janela observada, documentando o gesto.

> Dados de rede podem conter URLs e query strings; considerar todo artifact sensível até revisão. **Nunca commitar bruto** sem auditoria de privacidade, tokens e dados de terceiros.

## 5. Transformar capturas em conclusões verificáveis

Relatório por plataforma:

- **Interface:** telas, filtros, ordenação, estados de loading/erro e UX responsiva.
- **Frontend:** chunks e framework observáveis, imports, SPA routing, formatos de dados.
- **Dados de rede:** somente métodos, origem, paths e formatos efetivamente observados; nunca tratar candidatos inferidos como API oficial.
- **Tempo real:** verificar se há eventos SSE/WebSocket e seus intervalos; distinguir claims de latências medidas.
- **Segurança/limites:** autenticação, CORS, cache e limites somente se observáveis de forma passiva.
- **Diferenciação:** o que implementar originalmente; o que evitar; dependências e licenças.

Cada conclusão aponta para artifact REA, Evidence ID e timestamp, ou fonte pública. Lacunas recebem status **não verificado**.

## 6. Resultado esperado por alvo

- **MyCryptoPanel:** relatório técnico de recursos, rotas e arquitetura frontend observada; comparativo da fonte Binance oficial.
- **Habblaud:** preferir leitura direta do repositório MIT em vez de REA em website.
- **Viver de IA:** catálogo e páginas públicas; não ingressar em áreas restritas.
- **EAssets:** análise apenas de material público até licença/autorização para técnicas adicionais.
- **binance-api.mycryptopanel.com:** não assumir API pública; aguardar documentação do responsável.

## Repositório e execução

As evidências brutas devem permanecer em `_captures/`, ignorado pelo Git. Um dossiê resumido e higienizado pode ser commitado após validação. Para o produto original, abrir um repositório separado; não misturar app comercial à árvore do REA.
