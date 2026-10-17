# Plano de migração do Sentinel para repositório PRIVADO

**Bloqueio de governança:** o atual \`douglasmecenas-bot/rea\` é fork público do REA. Ele serve apenas como laboratório de pesquisa. **Não faça merge dos PRs do Sentinel no \`main\` do REA como arquitetura final.** O proprietário deve criar \`douglasmecenas-bot/sentinel-atlas\` como repositório **privado**.

## Pré-requisitos

- Usuário autorizado cria repositório privado **vazio**, sem README inicial.
- Conceder ao conector GitHub usado no ChatGPT acesso a este novo repositório, se a instalação limita os repositórios acessíveis.
- Não migrar dados reais, capturas de sessão, APIs, secrets, arquivos .sqlite, logs privados ou qualquer \`_captures/\`.

## Extração limpa do histórico exclusivo Sentinel

Estes comandos são para rodar em um computador com Git e credenciais legítimas, usando a branch técnica que já possui v0.4, no clone do fork público:

    git clone https://github.com/douglasmecenas-bot/rea.git
    cd rea
    git fetch origin feat/sentinel-v04-audit-terminal-2026-10
    git switch -c sentinel-v04 origin/feat/sentinel-v04-audit-terminal-2026-10
    git subtree split --prefix=research/sentinel-core -b sentinel-only

A branch \`sentinel-only\` terá apenas o histórico do projeto Sentinel. **Confira** \`git log\` e \`git ls-tree -r\` antes de publicar no repositório privado. Não usar \`--force\` em \`main\` existente.

Após revisar o conteúdo local e confirmar que o repositório privado está vazio:

    git remote add sentinel https://github.com/douglasmecenas-bot/sentinel-atlas.git
    git push sentinel sentinel-only:main

O fluxo de CI precisa ser copiado/adaptado (após revisão) para
\`sentinel-atlas/.github/workflows/\`, pois os workflows deste projeto
estão hoje no **root do REA**, fora de \`research/sentinel-core/\`:
- \`.github/workflows/sentinel-core-tests.yml\`
- \`.github/workflows/sentinel-dashboard-smoke.yml\`

No repositório privado, remover \`working-directory: research/sentinel-core\` e executar na raiz do novo projeto. Não migrar o workflow \`sentinel-binance-public-probe.yml\` automaticamente: o HTTP 451 registrado exige revisão de conectividade/autorização.

## Depois da migração

- Não adicionar \`origin\` com tokens na URL. Usar autenticação GitHub normal.
- Definir branch protection, revisões obrigatórias, CI e verificação de segredos.
- Conferir que \`data/\` e \`runs/\` estão ignorados; evitar upload de bases e relatórios privados.
- Versões de bibliotecas e ações CI devem ser fixadas para release, inclusive checks de dependências e verificações de licença.
- REA permanece como ferramenta isolada de análise autorizada das interfaces públicas ou licenciadas.
- A execução de ordens continua inexistente e não deve ser ativada como parte da migração.

**Status nesta data:** o novo repositório privado não foi criado por esta ferramenta; a migração ainda NÃO ocorreu. Estes são comandos de execução futura quando houver o repositório autorizado.
