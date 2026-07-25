# XiaoLee Smart Contract — Documentação On-chain

> Atualizado em: **2026-04-24** | Sprint 7 concluída.
> Program ID: `Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM`
> Cluster atual: **Devnet**

> **Escopo (reconciliado 2026-05-30):** este documento cobre **apenas a track Solana (Anchor)**.
> A XiaoLee é multi-chain. O contrato **Stellar (Soroban) `xiaolee_core`** está especificado em
> [`RT_XIAOLEE_STELLAR.md`](RT_XIAOLEE_STELLAR.md) seção 10 e **ainda não foi escrito** (nenhum
> crate Soroban no repositório). Status consolidado em [`MAINNET_READINESS.md`](MAINNET_READINESS.md) (Gates 1A/1B).

---

## 1. Visão Geral do Programa

O programa `xiaolee_core` é um smart contract Anchor (Rust/Solana) responsável por:

- **Registrar swaps on-chain** de forma auditável (`record_swap`).
- **Gerenciar estado global do protocolo** (`GlobalConfig` PDA).
- **Manter estado por usuário** (`UserState` PDA por `twitter_id`).
- **Controle de emergência** — pausar/retomar todas as operações (`pause_protocol` / `unpause_protocol`).
- **Transferência de autoridade** para multisig Gnosis Safe (`transfer_admin`).

---

## 2. Instruções do Programa

### `initialize_global`
> **Chamada:** Uma vez pelo admin no deploy. Inicializa o `GlobalConfig`.

| Campo | Tipo | Descrição |
|---|---|---|
| — | — | Sem parâmetros |

**Contas:**
- `global_config` (PDA, init) — `seeds = [b"global_config"]`
- `admin` (Signer, mut)
- `system_program`

**Eventos emitidos:** `GlobalInitialized { admin, version }`

---

### `initialize_user`
> **Chamada:** Pelo próprio usuário ao entrar no protocolo. Cria a `UserState` PDA.

| Parâmetro | Tipo | Validação |
|---|---|---|
| `twitter_id` | `String` | len ≤ 50 chars |

**Contas:**
- `global_config` (PDA, read) — verifica se protocolo não está pausado
- `user_state` (PDA, init) — `seeds = [b"user", twitter_id.as_bytes()]`
- `user` (Signer, mut)
- `system_program`

**Rejeita se:** `global_config.paused == true` → `ErrorCode::ProtocolPaused`

---

### `record_swap`
> **Chamada:** Exclusivamente pelo admin (backend via `AnchorClient`). Registra volume de swap.

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `volume` | `u64` | Volume do swap em lamports |

**Contas:**
- `global_config` (PDA, mut) — `has_one = admin` (garante autoria do admin)
- `user_state` (PDA, mut)
- `admin` (Signer, mut)

**Rejeita se:** `global_config.paused == true` → `ErrorCode::ProtocolPaused`
**Rejeita se:** signer ≠ `global_config.admin` → `ErrorCode::Unauthorized`
**Aritmética segura:** `checked_add` em `swap_count` e `total_volume`.

**Eventos emitidos:** `SwapRecorded { twitter_id, swap_count, volume, total_volume }`

---

### `pause_protocol` [ATENCAO] Emergency Control
> **Chamada:** Pelo admin em situação de emergência.

Quando pausado:
- `record_swap` → `ErrorCode::ProtocolPaused`
- `initialize_user` → `ErrorCode::ProtocolPaused`

**Contas:**
- `global_config` (PDA, mut) — `has_one = admin`
- `admin` (Signer)

**Eventos emitidos:** `ProtocolPaused { admin, timestamp }`

---

### `unpause_protocol`
> **Chamada:** Pelo admin para retomar operações após resolução da emergência.

**Eventos emitidos:** `ProtocolUnpaused { admin, timestamp }`

---

### `transfer_admin`
> **Chamada:** Para migrar autoridade para multisig Gnosis Safe antes do mainnet.

| Parâmetro | Tipo | Validação |
|---|---|---|
| `new_admin` | `Pubkey` | ≠ `Pubkey::default()` |

**Eventos emitidos:** `AdminTransferred { old_admin, new_admin, timestamp }`

---

## 3. Contas (PDAs)

### `GlobalConfig`

| Campo | Tipo | Descrição |
|---|---|---|
| `admin` | `Pubkey` | Admin atual (deve ser multisig em mainnet) |
| `bump` | `u8` | Bump seed |
| `paused` | `bool` | Estado de pausa emergencial |
| `version` | `u8` | Versão do protocolo (atual: 1) |
| `total_swaps_recorded` | `u64` | Total de swaps gravados |

**Derivação:** `Pubkey::find_program_address([b"global_config"], program_id)`

### `UserState`

| Campo | Tipo | Descrição |
|---|---|---|
| `twitter_id` | `String` (max 50) | Identificador único do usuário |
| `swap_count` | `u64` | Número de swaps registrados |
| `total_volume` | `u64` | Volume total em lamports |
| `bump` | `u8` | Bump seed |

**Derivação:** `Pubkey::find_program_address([b"user", twitter_id.as_bytes()], program_id)`

---

## 4. Eventos On-chain (Indexação)

| Evento | Campos | Quando |
|---|---|---|
| `GlobalInitialized` | `admin`, `version` | Deploy inicial |
| `SwapRecorded` | `twitter_id`, `swap_count`, `volume`, `total_volume` | Cada swap confirmado |
| `ProtocolPaused` | `admin`, `timestamp` | Pausa de emergência |
| `ProtocolUnpaused` | `admin`, `timestamp` | Retomada |
| `AdminTransferred` | `old_admin`, `new_admin`, `timestamp` | Mudança de admin |

> Todos os eventos são indexáveis via The Graph ou Helius Webhook para dashboards off-chain.

---

## 5. Códigos de Erro

| Código | Mensagem | Causa |
|---|---|---|
| `MathOverflow` | Math operation overflow | `swap_count` ou `total_volume` atingiu u64::MAX |
| `StringTooLong` | String length exceeds 50 | `twitter_id` > 50 caracteres |
| `Unauthorized` | Not the protocol admin | Signer não é `global_config.admin` |
| `ProtocolPaused` | Protocol is paused | Operação rejeitada durante pausa |
| `AlreadyPaused` | Protocol is already paused | Tentativa de pausar protocolo já pausado |
| `NotPaused` | Protocol is not paused | Tentativa de retomar protocolo ativo |
| `InvalidAdminAddress` | Invalid admin address | `new_admin == Pubkey::default()` |

---

## 6. Integração Backend (AnchorClient)

O backend Python utiliza `solders` para interagir com o programa:

```python
from server.integrations.anchor_client import AnchorClient

client = AnchorClient(
rpc_url="https://api.devnet.solana.com",
admin_keypair_b58=os.getenv("SOLANA_ADMIN_KEYPAIR_B58"),
)

# Deriva PDA do usuário
user_pda = client.derive_user_state_pda("@usuario_twitter")

# Registra swap (dry_run=True se keypair não configurada)
result = await client.record_swap(
twitter_id="@usuario_twitter",
volume_lamports=1_000_000_000,
signature="helius_tx_sig",
)
```

**Discriminador `record_swap`:** `[164, 158, 148, 54, 167, 137, 171, 59]`
**Serialização:** `discriminator (8 bytes) + volume (u64 little-endian, 8 bytes)`

---

## 7. Segurança e Pré-requisitos de Mainnet

| Item | Status |
|---|---|
| `has_one = admin` constraint (anti-unauthorized) | Concluido |
| `checked_add` (anti-overflow) | Concluido |
| `len() <= 50` em `twitter_id` (anti-DoS) | Concluido |
| Emergency pause on-chain | Concluido |
| Transfer admin para multisig | Concluido |
| Eventos on-chain para auditoria | Concluido |
| Auditoria externa independente | Pendente Pendente |
| Admin substituído por multisig Gnosis Safe | Pendente Pendente |
| Deploy em mainnet-beta | Pendente Pendente |

---

## 8. Comandos de Desenvolvimento

```bash
# Compilar o programa
make anchor-build

# Executar testes Anchor
make anchor-test

# Deploy em devnet
make anchor-deploy-devnet

# Sincronizar IDL com frontend após rebuild
make anchor-idl-sync
```

---

## 9. Histórico de Versões

| Versão | Data | Mudanças |
|---|---|---|
| v0.1 | 2026-04-22 | Estrutura inicial: initialize_global, initialize_user, record_swap |
| v0.2 | 2026-04-23 | Fixes de segurança: has_one, checked_add, input sanitization |
| v1.0 | 2026-04-24 | Emergency pause, transfer_admin, eventos on-chain, GlobalConfig expandido |
