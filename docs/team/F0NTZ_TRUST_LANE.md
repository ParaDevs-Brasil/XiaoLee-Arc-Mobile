# Faixa f0ntz — Chain & Trust Lead (cockpit Lepton)

> **Dono:** f0ntz · **Carrega:** Circle Tools 20% + metade do Innovation 20%
> **Janela:** 15–29 jun · **Hoje:** 23 jun (D4) · **PQC + ERC-8004:** D5 (24 jun) + integration freeze
> **Foco deste doc:** shipar o que só o f0ntz faz (PQC, ERC-8004, rail) **na demo** e
> **colocar isso no mercado** — virar nota de Innovation no vídeo/repo.
> **Relacionados:** `ARC_LEPTON_ARCHITECTURE.md` (L0–L4), `WORKFLOW_SEMANA.md` (costuras), `SPRINT_STATUS.md` (na branch do Jeiel).

---

## 0. Onde estamos DE VERDADE (reconciliação repo × plano)

O plano em `ARC_LEPTON_ARCHITECTURE.md` está correto, mas o estado real está espalhado:

| Camada | Plano dizia | Realidade no código (24 jun) |
|---|---|---|
| L1 rail (ArcClient, x402, intent log) | f0ntz D2 | **Pronto, mas na branch `origin/feature/agent-brain-lead`** — não no `develop`. `arc_client.py`, `PaymentIntent`, migração `20260622`, 4 tools, `run-campaign`. 91/91 testes. |
| L2 loop agêntico | Jeiel | Pronto, mesma branch. E2E em **sandbox** (`ARC_SANDBOX=true`). |
| L1 pagamento REAL | — | 🔴 **Bloqueado** — vars Circle não configuradas. Pagamentos são `sandbox_tx_*` fake. |
| L3 PQC (recibo ML-DSA) | f0ntz D5 | ❌ **Não existe em código.** Só em docs. |
| L3 ERC-8004 | f0ntz D5 | ❌ Não existe. |

**Verdade incômoda:** o campo `receipt_pqc` **já é retornado** pela tool de pagamento
(`creator_pay_tools.py:280` e `:318`), mas hoje é `"receipt_pqc": intent_id` — **um placeholder
que só ecoa o UUID, zero criptografia**. O Jeiel e o frontend já consomem esse campo. Ou seja:

> A faixa f0ntz não precisa criar contrato novo. O encaixe já está aberto e congelado.
> Trocar a string falsa por uma assinatura ML-DSA real **é** a entrega de Innovation.

**Scorecard atual (do SPRINT_STATUS): ~30/100.** Innovation 0/20. Com PQC + ERC-8004 + Circle
real, a faixa f0ntz sozinha move ~35 pontos (20 Circle + 10 PQC + 5 ERC-8004 da metade Innovation).

---

## 1. Pré-requisito de tudo (D5 manhã, antes do PQC)

Sem isso o PQC assina recibo de pagamento fake — narrativa morre na demo.

1. **Mergear `feature/agent-brain-lead` no `develop`.** O rail e o ponto de encaixe vivem lá.
   Sem merge, todo trabalho de PQC fica órfão.
2. **Desbloquear Circle (vars reais)** — passo a passo já documentado no `SPRINT_STATUS.md` §"Como
   desbloquear". Resumo: setar entity secret no console → criar wallet → `ARC_SANDBOX=false` →
   fondar na Sepolia → 1 pagamento real com tx hash verificável no Etherscan.
3. **🔴 SEGURANÇA (alçada Chain & Trust — fazer hoje):** o `SPRINT_STATUS.md` commitado **expõe
   `CIRCLE_ENTITY_SECRET`, `CIRCLE_API_KEY` e o ciphertext do entity secret em texto claro no git.**
   Mesmo sendo `TEST_API_KEY`, o entity secret é a chave que assina requests de movimentação.
   Ação: **rotacionar o entity secret e a API key**, mover para `.env` (não versionado),
   e substituir no doc por placeholders. Recibo PQC não vale nada se a chave da wallet vazou.

---

## 2. PQC — recibo pós-quântico ML-DSA (o diferencial do f0ntz)

### 2.1 Tese de mercado (por que isso é Innovation, não vaidade)
Pagamento agêntico autônomo cria um problema novo: **quem prova que o agente pagou o que disse que
pagou, e que o recibo não foi forjado** — num mundo onde a assinatura precisa sobreviver a um
adversário com computador quântico (colheita-agora-decifra-depois)? A resposta da XiaoLee:
**todo pagamento confirmado vira um recibo assinado com ML-DSA (FIPS 204)** — assinatura
pós-quântica padronizada pelo NIST. Terceiro verifica offline, sem confiar no nosso servidor.

Frase de venda (vídeo/repo): *"Cada nanopagamento USDC do agente emite um recibo verificável e
quantum-safe. O trilho é Circle; a prova é pós-quântica."*

### 2.2 Escopo cirúrgico (NÃO reescrever protocolo)
Só assinar o **recibo do pagamento confirmado**. Não toca consenso, não toca x402, não toca chave
da wallet Circle. Entrega = 1 módulo + 1 campo + 1 endpoint de verificação.

### 2.3 Plano de implementação (D5)

**Lib:** `dilithium-py` (pip, ML-DSA-87 puro Python, FIPS 204 final, **zero dependência nativa** —
seguro no Docker em 1 dia). Alternativa se latência incomodar: `quantcrypt` (PQClean, mais rápido,
build nativo). ML-DSA-87 = nível de segurança máximo (NIST level 5).

1. **`backend/services/pqc_receipt.py`**
   - `generate_keypair()` → carrega/gera par ML-DSA-87; chave pública publicada no repo + endpoint.
   - `sign_receipt(intent_id, to, amount_usdc, arc_tx_hash, ts) -> str`
     - canonicaliza o payload (JSON ordenado), assina, retorna `base64(signature)`.
   - `verify_receipt(payload, signature_b64) -> bool` — verificação independente.
   - `public_key_b64()` — expõe a pública para o verificador externo.
2. **Migração `20260624_add_receipt_pqc.py`** — adiciona coluna `receipt_pqc Text NULL` em
   `payment_intents` (hoje só existe o campo no retorno da tool, não na tabela).
3. **Wire no encaixe já aberto** — em `creator_pay_tools.py`, após `status="submitted"`:
   troca `"receipt_pqc": intent_id` por `sign_receipt(...)` real e persiste na coluna.
   Contrato `{tx, receipt_pqc}` **não muda de forma** → Jeiel e frontend não quebram.
4. **Endpoint `GET /v1/trust/verify-receipt`** — recebe `{payload, signature}`, devolve
   `{valid: bool, algorithm: "ML-DSA-87", public_key}`. É a peça demonstrável pro júri:
   *qualquer um verifica, sem confiar na gente.*
5. **Feature flag `PQC_ENABLED`** — se a lib falhar no staging, cai pro placeholder e a demo
   do core não trava (regra do sprint: core sempre verde).

### 2.4 Definição de pronto (PQC)
- [ ] `pay_creator_nanopayment` real grava `receipt_pqc` assinado na tabela.
- [ ] `GET /v1/trust/verify-receipt` valida um recibo real da Canteen/Sepolia → `valid: true`.
- [ ] Adulterar 1 byte do payload → `valid: false` (mostrar isso no vídeo).
- [ ] Chave pública publicada no repo (`docs/pqc_public_key.txt`).
- [ ] Passa na integração e2e do fim do dia.

---

## 3. ERC-8004 — identidade on-chain do agente (outra metade do Innovation)

### 3.1 Tese
Pagamento agente→creator é **agent-to-agent commerce**. ERC-8004 dá ao agente XiaoLee uma
**identidade verificável on-chain** → o recibo PQC deixa de ser "uma assinatura solta" e passa a ser
"a assinatura **deste agente registrado**". PQC + ERC-8004 juntos = recibo atribuível e quantum-safe.
Casa direto com as RFBs 03 (Agent-to-Agent) e 02 (Selling Agent Services).

### 3.2 Escopo cirúrgico
- Registrar UMA identidade de agente ERC-8004 na testnet (Sepolia/Canteen).
- Incluir o `agent_id` ERC-8004 no payload assinado pelo recibo PQC (vínculo prova↔identidade).
- Endpoint/anexo no recibo expondo o registro on-chain.
- **Se D5 apertar, ERC-8004 é o que corta primeiro** — PQC é o core do diferencial; ERC-8004 é o
  multiplicador. PQC sozinho já entrega a metade de Innovation do f0ntz.

---

## 4. CCTP + ZK — explicitamente FORA da janela de nota

- **CCTP:** diferencial, não pré-requisito (já decidido na arquitetura). Só entra se sobrar tempo
  pós-freeze; não bloqueia demo nem move nota tanto quanto Circle-real + PQC.
- **ZK:** stretch atrás de flag, **só se core verde**. Não começar antes de PQC + Circle-real fechados.

---

## 5. "Colocado no mercado" — onde a faixa f0ntz vira nota

Cada peça técnica tem que aparecer onde o júri olha. Mapa:

| Peça f0ntz | Onde aparece (mercado/nota) | Prova mostrada |
|---|---|---|
| Pagamento USDC real (Circle, `ARC_SANDBOX=false`) | **Circle Tools 20% + Traction 30%** | tx hash real no Sepolia Etherscan |
| Recibo ML-DSA | **Innovation 20%** | demo do `verify-receipt`: válido → adultera → inválido |
| ERC-8004 | **Innovation 20% + RFB 02/03** | registro on-chain do agente |
| Verificação independente | **Innovation** (confiança sem custódia) | terceiro valida com a chave pública do repo |

**Beat do vídeo (≤3 min), parte f0ntz (~40s):** rodar campanha → agente paga 3 creators em USDC
real → abrir Etherscan (tx real) → abrir `verify-receipt` (recibo válido, ML-DSA-87) → adulterar
→ inválido. Narração: *"trilho Circle, prova pós-quântica, verificável por qualquer um."*

**Repo (D6):** README com camadas L0–L4, seção "Trust Layer" explicando PQC+ERC-8004,
chave pública publicada, badge de testes, link pro endpoint de verificação.

---

## 6. Ordem de execução (D5, faixa f0ntz)

1. Merge `feature/agent-brain-lead` → `develop`. **(desbloqueia tudo)**
2. Rotacionar segredos vazados + Circle vars reais + 1 pagamento real na Sepolia. **(Circle 20%)**
3. `pqc_receipt.py` + migração `receipt_pqc` + wire na tool + `verify-receipt`. **(Innovation core)**
4. e2e na Canteen/Sepolia: pagamento real → recibo assinado → verificação ok. **(freeze)**
5. ERC-8004 se a janela permitir. **(Innovation multiplicador)**
6. Publicar chave pública + escrever a seção Trust do README (insumo do vídeo D6).

> Regra do sprint: nada conta até passar na integração e2e do fim do dia, na Canteen.
> Demo > código bonito. PQC atrás de flag pra nunca derrubar o core.
