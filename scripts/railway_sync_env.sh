#!/usr/bin/env bash
# Sincroniza as env vars do sprint Arc do .env local -> serviço backend no Railway.
# Rodar SOMENTE depois de rotacionar o CIRCLE_ENTITY_SECRET no console da Circle
# e atualizar o valor novo no .env local.
#
# Uso: ./scripts/railway_sync_env.sh [--dry-run]
set -euo pipefail

ENV_FILE="$(dirname "$0")/../.env"
SERVICE="xiaolee"
DRY_RUN="${1:-}"

# Vars do sprint Arc que a prod precisa (as demais têm default seguro no settings.py)
VARS=(
  LLM_PROVIDER
  ANTHROPIC_API_KEY
  ANTHROPIC_MODEL
  CIRCLE_API_KEY
  CIRCLE_ENTITY_SECRET
  CIRCLE_WALLET_ID
  CIRCLE_BLOCKCHAIN
  ARC_SANDBOX
  ARC_RPC_URL
  ARC_CHAIN_ID
  ARC_USDC_ADDRESS
  ARC_AGENT_PRIVATE_KEY
  ARC_PAYMENT_SECRET
  ARC_CCTP_USDC
  ARC_CCTP_TOKEN_MESSENGER
  ARC_CCTP_MSG_TRANSMITTER
  ARC_CCTP_DOMAIN
  PQC_ENABLED
  PQC_PUBLIC_KEY
  PQC_SECRET_KEY
)

SET_ARGS=()
MISSING=()
for key in "${VARS[@]}"; do
  value="$(grep -E "^${key}=" "$ENV_FILE" | head -1 | cut -d= -f2-)"
  if [ -z "$value" ]; then
    MISSING+=("$key")
  else
    SET_ARGS+=(--set "${key}=${value}")
  fi
done

# JWT_SECRET não existe no .env local — gera um forte só para prod
if ! railway variables --service "$SERVICE" --kv 2>/dev/null | grep -q '^JWT_SECRET='; then
  SET_ARGS+=(--set "JWT_SECRET=$(openssl rand -hex 32)")
  echo "[info] JWT_SECRET novo será gerado para prod"
fi

[ ${#MISSING[@]} -gt 0 ] && echo "[aviso] sem valor no .env (puladas): ${MISSING[*]}"

if [ "$DRY_RUN" = "--dry-run" ]; then
  printf '[dry-run] railway variables --service %s' "$SERVICE"
  for a in "${SET_ARGS[@]}"; do
    [ "$a" = "--set" ] && continue
    printf ' --set %s=<oculto>' "${a%%=*}"
  done
  echo
  exit 0
fi

railway variables --service "$SERVICE" "${SET_ARGS[@]}"
echo "[ok] Vars aplicadas no serviço $SERVICE — o Railway dispara um redeploy automático."
