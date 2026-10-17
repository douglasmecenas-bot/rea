#!/usr/bin/env bash
# Ajudante REA: captura passiva de uma aba PUBLICA ja aberta em Chromium CDP.
# Nao inicia browser, nao navega, nao faz login e nao usa credenciais.
set -Eeuo pipefail

if [ "$#" -ne 2 ]; then
  echo "Uso: bash capture-public-site.sh <TARGET_ID> <mycryptopanel|habblaud|viverdeia>" >&2
  exit 2
fi

TARGET_ID="$1"
SITE="$2"
case "$SITE" in
  mycryptopanel|habblaud|viverdeia) ;;
  *) echo "Alvo nao autorizado neste roteiro. EAssets exige autorizacao antes de automacao." >&2; exit 2 ;;
esac
command -v rea >/dev/null || { echo "Instale a CLI rea-agents (versao oficial) antes." >&2; exit 1; }

ENDPOINT="${REA_CDP_ENDPOINT:-http://127.0.0.1:9222}"
OUTBASE="${REA_CAPTURE_BASE:-research/benchmark-platformas/_captures}"
OUTDIR="$OUTBASE/$SITE"
mkdir -p "$OUTDIR"

printf 'Confirme manualmente que TARGET_ID=%s corresponde a uma aba PUBLICA de %s.\n' "$TARGET_ID" "$SITE"
printf 'A coleta pode registrar caminhos e query strings. NAO envie nem comite os JSON brutos.\n'

rea list-browser-targets "$ENDPOINT" --json > "$OUTDIR/targets.json"
rea inspect-web-page "$ENDPOINT" "$TARGET_ID" \
  --observation-ms 1000 \
  --include-json-body-shapes \
  --include-websocket-shapes \
  --json > "$OUTDIR/page.json"
rea analyze-web-bundle "$ENDPOINT" "$TARGET_ID" --json > "$OUTDIR/bundle.json"
rea capture-web-screenshot "$ENDPOINT" "$TARGET_ID" --json > "$OUTDIR/screenshot.json"

echo "Capturas salvas em $OUTDIR. Revise dados sensiveis antes de compartilhar qualquer artifact."
