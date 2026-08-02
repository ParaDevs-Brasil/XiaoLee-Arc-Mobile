#!/usr/bin/env bash
# Semeia os participantes que a Community Builder (campanha 3, tipo referral)
# exige para verificar.
#
# `verify_referral` (server/integrations/campaign_verifier.py) pede >= 3 OUTROS
# participantes inscritos na mesma campanha — é o proxy que impede alguém de
# resgatar um reward de indicação sozinho. Num banco recém-criado a campanha
# nasce do seed sem participante nenhum, então a verificação reprova e o fluxo
# join → verify → claim não fecha na demo.
#
# Só faz sentido em ambiente de demonstração. Não rodar contra um banco com
# usuários reais: estes três viram usuários de verdade na tabela `users`.
#
# Uso:
#   ./scripts/seed_referral_demo.sh https://xiaolee-mobile-api.up.railway.app
set -euo pipefail

API="${1:?uso: $0 <url-do-backend>}"
CAMPANHA="${2:-3}"

for amigo in demo_amiga_ana demo_amigo_bruno demo_amiga_carla; do
  resposta=$(curl -sS -X POST "$API/campaigns/join" \
    -H "Authorization: Bearer $amigo" \
    -H 'Content-Type: application/json' \
    -d "{\"campaign_identifier\":\"$CAMPANHA\"}")
  # 409 (já inscrito) é sucesso para o nosso propósito — o script é idempotente.
  printf '  %-18s %s\n' "$amigo" "$resposta"
done

echo
echo "Participantes agora inscritos na campanha $CAMPANHA:"
curl -sS "$API/campaigns" | python3 -c "
import sys, json
for c in json.load(sys.stdin)['campaigns']:
    if str(c['id']) == '${CAMPANHA}':
        print(f\"  {c['name']}: {c['completed_participants']} inscrito(s), \"
              f\"{c['reward_per_participant']} {c['reward_token']} por participante\")
"
