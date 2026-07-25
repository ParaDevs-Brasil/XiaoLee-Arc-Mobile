# Roadmap de Integração Frontend ↔ Backend — pós c8bf280

**Para:** Jeiel & Mari · **De:** f0ntz · **Data:** 4 jul 2026 · **Deadline Lepton:** 6 jul

## O que mudou no backend (contexto em 1 minuto)

O commit `c8bf280` deixou o loop agêntico **multi-chain 100% live**: o agente (Claude via API, sem mock)
descobre creators, avalia, **decide o valor e o trilho sozinho**, e paga USDC real a partir do Arc:

| Wallet do creator | Trilho | Tool |
|---|---|---|
| Arc / EVM (`0x…`) | Arc direto | `pay_creator_nanopayment` |
| Solana (base58) | CCTP V2: burn no Arc → mint na Solana | `payout_cross_chain_nanopayment` |
| Stellar (`G…` strkey) | CCTP V2: burn no Arc → CctpForwarder → conta Stellar | `payout_cross_chain_nanopayment` |

Validado on-chain nas duas direções de cada rota. Orçamento único entre trilhos, recibo PQC (ML-DSA-87)
por pagamento, dedup por creator. 447 testes passando.

**O front da branch `feuture/frontend-fix` é a cara disso tudo — este doc mapeia o que falta ligar, em ordem de impacto.**

---

## Fase 0 — Solda mínima (bloqueia a demo, fazer primeiro)

### 0.1 Onboarding de creator: wallet + chain ⚠️ QUEBRADO HOJE
O onboarding novo conecta wallet EVM e manda o endereço `0x…` no campo `circle_wallet_id` do
`POST /v1/creator/register`. O backend valida esse campo contra a Circle API (`GET /v1/wallets/{id}`)
→ com `CIRCLE_API_KEY` setada, **todo registro via UI retorna 422**.

E agora com multi-chain o registro precisa saber **em qual chain** o creator recebe:

- **Backend (f0ntz):** aceitar endereço nativo + campo `chain` no register; pular validação Circle
  quando for endereço on-chain; nos payouts, endereço `0x…` registrado vai direto pro
  `arc_client.send_usdc` (hoje `get_wallet_info("0x…")` estoura RuntimeError em `creator_pay_tools.py`).
- **Front (Mari):** evoluir o onboarding para payload combinado:
  ```json
  { "twitter_handle": "@handle", "wallet_address": "<endereço>", "chain": "arc" | "solana" | "stellar" }
  ```
  Dica de UX: seletor de chain com auto-detect pelo formato — `0x…` (40 hex) → arc, base58 32-44 chars
  → solana, `G…` 56 chars → stellar. Validar formato **antes** de enviar e tratar 422 com mensagem amigável.
  O botão "Connect EVM wallet" preenche o caso arc; para Solana/Stellar o creator cola o endereço.

> Combinar o payload final juntos antes de codar — é a única mudança de contrato da Fase 0.

### 0.2 Participante de campanha com chain
`CampaignParticipant` agora tem `chain`, `solana_wallet`, `stellar_wallet` (ADR-006) — mas o
`POST /campaigns/join` ainda não recebe/persiste isso (hoje só os seeds de demo preenchem).
Quando o join enviar `wallet_public_key`, mandar também a chain detectada. Sem isso o
`discover_creators` do agente não sabe o trilho de quem entrou pela UI.

---

## Fase 1 — Vitrine agentic multi-chain (o ouro do Lepton, é isso que o juiz precisa VER)

### 1.1 Cockpit do agente: mostrar o trilho de cada pagamento
Vocês já consomem `GET /v1/agent/run-campaign/{id}/status` via `useAgentStatus`. Dois ajustes:

- **Bug atual:** o backend grava cada payment como `{creator_id, amount_usdc, tx, intent_id, step}`,
  mas a interface `AgentPayment` do front espera `to` → hoje `payment.to` é `undefined`.
  Vou normalizar para `to` + adicionar `destination_chain` no backend; enquanto isso dá para ler de `creator_id`.
- **Dica de ouro (zero backend):** o array `steps` já traz o `tool_result` completo. Quando
  `tool_name === "payout_cross_chain_nanopayment"`, o result tem:
  ```json
  { "tx": "…", "destination_chain": "solana", "receipt_pqc": "…", "status": "received",
    "latency": { "burn_attest_s": 12.3, "mint_s": 4.1, "total_s": 16.4 } }
  ```
  Dá para renderizar uma **timeline burn → attestation → mint com latência por etapa** só lendo os steps.
  Isso é a cena da demo: "o agente decidiu pagar esse creator na Solana e aqui está o burn no Arc e o mint lá".

**Links de explorer por chain** (o `tx` muda de formato conforme o trilho):

| Chain | Formato do tx | Explorer |
|---|---|---|
| Arc (testnet) | `0x…` | explorer do Arc testnet |
| Solana (devnet) | assinatura base58 | `https://solscan.io/tx/{tx}?cluster=devnet` |
| Stellar (testnet) | hash hex | `https://stellar.expert/explorer/testnet/tx/{tx}` |

### 1.2 Reward dinâmico — a UI não deve assumir valor fixo
O agente agora **decide o valor** por creator (score 50-69 → ~0.7x baseline, 70-89 → 1x, 90-100 → ~1.4x).
Não renderizem "reward por creator" como constante nos payments do run; mostrem o valor real de cada um
e, se quiserem brilhar, um tooltip "valor decidido pelo agente com base no score" — o `final_message`
do run traz a explicação das decisões de scaling, vale exibir.

### 1.3 Traction feed: payouts do agente NÃO caem sozinhos no dashboard
O feed (`/v1/traction/stats` + SSE `/v1/traction/feed` — contrato de vocês já bate ✅) é alimentado por
`POST /v1/payments/settled`, que hoje é chamado por operador/script, não automaticamente pelos payout tools.
Para a demo: eu garanto o post após cada run. Se sobrar tempo eu ligo isso no backend. No front, o `tx`
do feed pode ser de qualquer uma das 3 chains — usem a mesma detecção de formato do 1.1 para o link.

### 1.4 Painel Treasury multi-chain (novo, fácil, bonito)
Três endpoints prontos que ninguém consome ainda:

- `GET /v1/arc/wallet/balance` — saldo USDC da treasury no Arc
- `GET /v1/cctp/treasury/solana/balance` → `{ chain, address, usdc_balance, sandbox }`
- `GET /v1/cctp/treasury/stellar/balance` e `GET /v1/cctp/healthcheck` (status agregado)

Card "Treasury" no dashboard com saldo por chain fecha a narrativa "Arc como hub".
**Atenção:** retornam **503 quando a flag da chain está off** (`SOLANA_CCTP_ENABLED` /
`STELLAR_CCTP_ENABLED` / `CCTP_ENABLED`) — tratar graceful (badge "disabled"), não é erro.

---

## Fase 2 — Narrativa Arc completa (depois da demo funcionar)

### 2.1 Chat: migrar x402 de Stellar para Arc
O chat ainda paga via `/v1/ai/query` (variante Stellar/XLM). A variante Arc já existe em `/v1/arc/ai/*`:

1. `POST /v1/arc/ai/query` sem header → **402** com `X-Payment-Required` (JSON: `pay_to`, `amount`, `asset: USDC`)
2. Paga USDC no Arc para `pay_to`, obtém `circle_id`
3. Repete o POST com header `X-Payment: {"circle_id": "…"}` → **200** com a resposta da AI

Anti-replay no backend (circle_id de uso único). Com isso o `utils/stellar.ts` sai do fluxo do chat
(swap Freighter, anchor, SEP-10 — aposentar junto com `StellarWallet.tsx`, que já está órfão).

### 2.2 Claim de campanha com assinatura EVM
`useCampaignActions.tsx` ainda exige Phantom `signMessage`, e o backend só verifica Ed25519/base58.
Com a identidade agora EVM: front assina com `personal_sign` (adicionar helper no `lib/evmWallet.ts`),
backend verifica EIP-191 (recover secp256k1 → comparar endereço). Enquanto não sair, claim funciona
só para sessões custodiais (Google/Telegram) — ok para a demo.

### 2.3 Badge de recibo PQC
Cada pagamento sai com `receipt_pqc` (ML-DSA-87, pós-quântico). Endpoints prontos:
`GET /v1/trust/public-key` e `POST /v1/trust/verify-receipt`. Um badge "🔐 recibo pós-quântico
verificado" ao lado de cada payment no cockpit é diferencial de apresentação barato — nenhum
outro time do hackathon vai ter isso.

---

## Gotchas gerais

- **Runs do agente são in-memory** — restart do server apaga; o status retorna 404 com mensagem explicando. Tratar no polling.
- **`GET /v1/agent/runs`** lista todos os runs (útil para um histórico simples no cockpit).
- **SSE só existe no traction feed**; status do agente é polling (já fazem certo).
- **`BRIDGE_SANDBOX=true`** faz os endpoints CCTP responderem com dados fake — bom para desenvolver o front sem gastar testnet.
- **Base URL:** tudo em `NEXT_PUBLIC_CORE_API_URL`, sem host novo.

## Ordem sugerida com o deadline dia 6

1. **Hoje:** Fase 0.1 (combinar payload do register comigo) + 1.1 (timeline cross-chain nos steps — zero backend)
2. **Amanhã:** 1.4 (treasury) + 1.2 (reward dinâmico) + 1.3 (validar feed na demo ensaiada)
3. **Se sobrar:** 2.3 (badge PQC) > 2.1 (chat na Arc) > 2.2 (claim EVM)

Qualquer contrato que precisar mudar no backend, me chamem que eu ajusto na hora — não travem no front por causa de payload.
