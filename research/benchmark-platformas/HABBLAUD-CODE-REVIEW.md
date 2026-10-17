# Habblaud: leitura de código-fonte público (MIT)

**Data:** 15/10/2026  
**Método:** inspeção dos arquivos públicos do repositório `marmottajr/habblaud` via GitHub; **não é captura REA nem observação de produção**.

## Funcionamento observado no código

Fonte primária: https://github.com/marmottajr/habblaud/blob/main/server/README.md

1. O servidor é em **Node.js**, sem dependências de runtime, e representa sessões do Claude Code/Codex como `Office`, salas e agentes.
2. Para Claude Code, lê arquivos de sessão do computador local, incluindo registros por PID e transcripts JSONL; descobre subagentes e atividades de ferramentas.
3. O transporte para UI é **SSE (Server-Sent Events)**, não necessariamente WebSocket:
   - `GET /api/stream`: eventos `snapshot`, `feed`, `notice`; ping a cada 15 s.
   - `GET /api/snapshot`: estado corrente.
   - `GET /api/agents/:id`: histórico de até 200 atividades.
   - `GET /api/stats`: estatísticas por dia.
4. Módulos separados: `server/sources/`, `server/model/`, `server/http/`, `server/permissions/`, `server/codex/` e `server/messages/`; o `server/index.ts` cria o servidor, modelo e subsistemas.
5. Segurança de instância local: `server/http/guard.ts` é descrito como verificando Host e Origin e impondo JSON em POSTs; recursos de terminal/controle dependem de bind local. Revisar a implementação antes de reaproveitar a ideia.
6. Eventos GitHub são inferidos de transcripts e resultados de comandos/MCP, sem exigir token remoto como mecanismo principal (`server/sources/github.ts`).

Fonte secundária: https://github.com/marmottajr/habblaud/blob/main/server/index.ts

## O que aproveitamos de forma original

- Separação **conectores / modelo interno / feed SSE / frontend** é arquitetura útil.
- Para nosso painel de agentes, adapters poderiam ler telemetria autorizada de Codex, Claude Code ou outras ferramentas, com permissões granulares.
- Transmissão SSE é suficiente para estados e notificações unidirecionais, sem obrigatoriedade de WebSocket.
- Reuso de código MIT exige manter avisos de copyright e licença; preferimos construir nossa própria implementação baseada em conceitos, sem clonar UI/identidade da marca.

## O que não podemos inferir do repositório

- Como funciona a implantação comercial em `habblaud.com`.
- Compatibilidade de todas as versões futuras do Codex/Claude Code.
- Níveis de desempenho sem benchmarks próprios.

**Nota de produto:** monitor de agentes é módulo **separado** do MVP principal de inteligência de criptoativos.
