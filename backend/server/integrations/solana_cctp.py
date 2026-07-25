"""
solana_cctp.py — Circle CCTP V2 real em Solana (domain 5): TokenMessengerMinterV2 +
MessageTransmitterV2. Sem SDK Python oficial da Circle (só Anchor TS client) — instrução
construída manualmente via solders, mesmo padrão hand-rolled de anchor_client.py.

Contas, seeds de PDA e discriminadores extraídos do código-fonte real
(github.com/circlefin/solana-cctp-contracts, branch master, programs/v2/*) — não de
documentação de terceiros, que estava incompleta nesse nível de detalhe.

Program IDs (devnet == mainnet, confirmado em developers.circle.com):
    TokenMessengerMinterV2: CCTPV2vPZJS2u2BBsUoscuikbYjnpFmbFsvVuJdgUMQe
    MessageTransmitterV2:   CCTPV2Sm4AdWt5296sk4P66VBZ7bEhcARwFaaS9YPbeC

FLUXO BURN (Solana -> outra chain, ex: Solana -> Arc):
    deposit_for_burn (TokenMessengerMinterV2) -> CPI send_message (MessageTransmitterV2)
    -> emite MessageSent event -> attestation Circle -> receiveMessage no destino.

FLUXO MINT (outra chain -> Solana, ex: Arc -> Solana, o caminho usado pra pagar creators):
    receive_message (MessageTransmitterV2) -> CPI handle_receive_finalized_message
    (TokenMessengerMinterV2) -> credita recipient_token_account.

ATENÇÃO — peça que precisa de verificação contra devnet real antes de ir pra produção:
    as contas injetadas pelo macro #[event_cpi] da Anchor (event_authority + program,
    2 contas extras no fim de cada instrução anotada) foram derivadas pela convenção
    padrão da Anchor (seeds=[b"__event_authority"]), mas não foram testadas contra uma
    tx real ainda — ver TODO em `_event_cpi_accounts`.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Optional

import aiohttp

LOG = logging.getLogger(__name__)

# ── Program IDs reais da Circle (devnet == mainnet) ─────────────────────────────
TOKEN_MESSENGER_MINTER_V2 = "CCTPV2vPZJS2u2BBsUoscuikbYjnpFmbFsvVuJdgUMQe"
MESSAGE_TRANSMITTER_V2 = "CCTPV2Sm4AdWt5296sk4P66VBZ7bEhcARwFaaS9YPbeC"
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"

SOLANA_CCTP_DOMAIN = 5
USDC_DECIMALS_SOLANA = 6

# Seeds de PDA — extraídos de initialize.rs / add_remote_token_messenger.rs /
# deposit_for_burn.rs / handle_receive_finalized_message.rs no repo oficial.
_SEED_TOKEN_MESSENGER = b"token_messenger"
_SEED_TOKEN_MINTER = b"token_minter"
_SEED_MESSAGE_TRANSMITTER = b"message_transmitter"
_SEED_SENDER_AUTHORITY = b"sender_authority"
_SEED_MESSAGE_TRANSMITTER_AUTHORITY = b"message_transmitter_authority"
_SEED_REMOTE_TOKEN_MESSENGER = b"remote_token_messenger"
_SEED_LOCAL_TOKEN = b"local_token"
_SEED_DENYLIST_ACCOUNT = b"denylist_account"
_SEED_CUSTODY = b"custody"
_SEED_TOKEN_PAIR = b"token_pair"
_SEED_USED_NONCE = b"used_nonce"
_SEED_EVENT_AUTHORITY = b"__event_authority"  # convenção fixa do macro #[event_cpi] da Anchor

_TX_TIMEOUT_S = 120


def _import_solders():
    """Import lazy de solders — mesmo padrão de anchor_client.py."""
    try:
        from solders.pubkey import Pubkey
        from solders.keypair import Keypair
        from solders.transaction import Transaction
        from solders.instruction import Instruction, AccountMeta
        from solders.message import Message
        from solders.hash import Hash
        return Pubkey, Keypair, Transaction, Instruction, AccountMeta, Message, Hash
    except ImportError as exc:
        raise RuntimeError("solders não está instalado. Execute: pip install solders") from exc


def _anchor_discriminator(instruction_name: str) -> bytes:
    """Discriminador Anchor = primeiros 8 bytes de sha256('global:<nome_snake_case>').
    Confirmado no próprio source da Circle (receive_message.rs usa esse esquema
    explicitamente para montar a instrução CPI de handle_receive_*_message)."""
    return hashlib.sha256(f"global:{instruction_name}".encode()).digest()[:8]


def _borsh_u64(value: int) -> bytes:
    return value.to_bytes(8, "little")


def _borsh_u32(value: int) -> bytes:
    return value.to_bytes(4, "little")


def _borsh_bytes(value: bytes) -> bytes:
    """Vec<u8> Borsh = prefixo u32 LE com o tamanho + bytes crus."""
    return _borsh_u32(len(value)) + value


@dataclass
class TxResult:
    tx_hash: str
    confirmed: bool
    status: int = 0


class SolanaCCTPClient:
    """
    Cliente CCTP V2 real para Solana. Chave de tesouraria DEDICADA — nunca reaproveitar
    SOLANA_ADMIN_KEYPAIR_B58 (essa é só admin do programa xiaolee_core, não custodia
    fundos de CCTP).
    """

    def __init__(
        self,
        rpc_url: str = "",
        treasury_keypair_b58: str = "",
        usdc_mint: str = "",
        token_messenger_minter: str = "",
        message_transmitter: str = "",
        fee_recipient: str = "",
        sandbox: bool = True,
    ):
        self.rpc_url = rpc_url or os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
        self.treasury_keypair_b58 = treasury_keypair_b58 or os.getenv("SOLANA_TREASURY_KEYPAIR_B58", "")
        self.usdc_mint = usdc_mint or os.getenv("SOLANA_USDC_MINT", "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU")
        self.tmm_program = token_messenger_minter or os.getenv(
            "SOLANA_CCTP_TOKEN_MESSENGER_MINTER", TOKEN_MESSENGER_MINTER_V2
        )
        self.mt_program = message_transmitter or os.getenv(
            "SOLANA_CCTP_MESSAGE_TRANSMITTER", MESSAGE_TRANSMITTER_V2
        )
        # fee_recipient do TokenMessenger — dono do ATA que recebe a taxa de fast-transfer
        # no receive. Default = valor real observado on-chain na devnet em 03/07/2026
        # (tx 2ceBribvKk2LR4awVdBH3EGFjJo7AKuSq68AmLTkerVN5JbQZNHVD6UGQsrqgnbCVugr58DY7FsiumdaGyi6ejJA,
        # ATA 2cDia1Ga9XDBGWVyFmaqiE7FKMDEtcy3xoRCW7B7S4es reproduzida pela nossa derivação).
        # Em mainnet, sobrescrever via env — o fee_recipient é configurável pela Circle.
        self.fee_recipient = fee_recipient or os.getenv(
            "SOLANA_CCTP_FEE_RECIPIENT", "AYG63YgrKLbp9B23ntcRemU8kSD7rZ7cNFGDo8DbEfTd"
        )
        self.sandbox = sandbox
        self._timeout = aiohttp.ClientTimeout(total=_TX_TIMEOUT_S)

    @property
    def address(self) -> str:
        if self.sandbox or not self.treasury_keypair_b58:
            return "SANDBOX_SOLANA_CCTP_TREASURY"
        _, Keypair, *_ = _import_solders()
        return str(Keypair.from_base58_string(self.treasury_keypair_b58).pubkey())

    # ------------------------------------------------------------------
    # Derivação de PDAs (seeds confirmados no source oficial da Circle)
    # ------------------------------------------------------------------

    def _pda(self, seeds: list, program_id_str: str):
        Pubkey, *_ = _import_solders()
        program_id = Pubkey.from_string(program_id_str)
        pda, _bump = Pubkey.find_program_address(seeds, program_id)
        return pda

    def derive_token_messenger(self):
        return self._pda([_SEED_TOKEN_MESSENGER], self.tmm_program)

    def derive_token_minter(self):
        return self._pda([_SEED_TOKEN_MINTER], self.tmm_program)

    def derive_sender_authority(self):
        return self._pda([_SEED_SENDER_AUTHORITY], self.tmm_program)

    def derive_message_transmitter(self):
        return self._pda([_SEED_MESSAGE_TRANSMITTER], self.mt_program)

    def derive_message_transmitter_authority(self, receiver_program_id_str: str):
        Pubkey, *_ = _import_solders()
        receiver = Pubkey.from_string(receiver_program_id_str)
        return self._pda([_SEED_MESSAGE_TRANSMITTER_AUTHORITY, bytes(receiver)], self.mt_program)

    def derive_remote_token_messenger(self, domain: int):
        # Seed usa o domain como STRING decimal, não bytes de u32 (confirmado em
        # add_remote_token_messenger.rs: params.domain.to_string().as_bytes()).
        return self._pda([_SEED_REMOTE_TOKEN_MESSENGER, str(domain).encode()], self.tmm_program)

    def derive_local_token(self, mint_pubkey):
        return self._pda([_SEED_LOCAL_TOKEN, bytes(mint_pubkey)], self.tmm_program)

    def derive_denylist_account(self, owner_pubkey):
        return self._pda([_SEED_DENYLIST_ACCOUNT, bytes(owner_pubkey)], self.tmm_program)

    def derive_custody_token_account(self, mint_pubkey):
        return self._pda([_SEED_CUSTODY, bytes(mint_pubkey)], self.tmm_program)

    def derive_token_pair(self, remote_domain: int, burn_token_bytes_32: bytes):
        return self._pda(
            [_SEED_TOKEN_PAIR, str(remote_domain).encode(), burn_token_bytes_32],
            self.tmm_program,
        )

    def derive_used_nonce(self, nonce_seed_bytes: bytes):
        return self._pda([_SEED_USED_NONCE, nonce_seed_bytes], self.mt_program)

    def _event_cpi_accounts(self, program_id_str: str):
        """
        Contas injetadas pelo macro #[event_cpi] da Anchor em cada instrução anotada:
        event_authority (PDA, seeds=[b"__event_authority"]) + o próprio program_id.
        VALIDADO em 03/07/2026 contra deposit_for_burn real na devnet
        (tx 61gJyeUshdt3wB9KN3fMaewdikXDSGdQYzwnm99djNCRD72D5NdorRPtS2obhtYMmxxkSyqQZyXJuTUyFESz7yN3,
        destino domain 26/Arc): as 18 contas batem posição a posição com burn_usdc(),
        incluindo event_authority=6TCCnJ9R1m1RXFzyoH7GYH2J6NJDtZaUvfipPuLWxHNd.
        """
        Pubkey, *_, AccountMeta, _, _ = _import_solders()
        event_authority = self._pda([_SEED_EVENT_AUTHORITY], program_id_str)
        program_id = Pubkey.from_string(program_id_str)
        return [
            AccountMeta(pubkey=event_authority, is_signer=False, is_writable=False),
            AccountMeta(pubkey=program_id, is_signer=False, is_writable=False),
        ]

    def derive_associated_token_address(self, owner_pubkey, mint_pubkey):
        Pubkey, *_ = _import_solders()
        ata_program = Pubkey.from_string(ASSOCIATED_TOKEN_PROGRAM_ID)
        token_program = Pubkey.from_string(SPL_TOKEN_PROGRAM_ID)
        pda, _bump = Pubkey.find_program_address(
            [bytes(owner_pubkey), bytes(token_program), bytes(mint_pubkey)],
            ata_program,
        )
        return pda

    # ------------------------------------------------------------------
    # Burn — Solana como chain de origem (ex: Solana -> Arc)
    # ------------------------------------------------------------------

    async def burn_usdc(
        self,
        amount_usdc: float,
        destination_domain: int,
        mint_recipient_bytes32: bytes,
        destination_caller_bytes32: Optional[bytes] = None,
    ) -> TxResult:
        """
        depositForBurn real — queima USDC no Solana e emite MessageSent pro domain destino.
        mint_recipient_bytes32: endereço destino já em formato 32-byte (padded).
        min_finality_threshold=2000 = transferência "finalized" (padrão, sem taxa de
        fast-transfer) — max_fee=0 é válido nesse modo.
        """
        if self.sandbox:
            fake = f"sandbox_solana_burn_{destination_domain}_{amount_usdc}"
            LOG.info("[solana_cctp] SANDBOX burn %.4f USDC -> domain=%d | tx=%s", amount_usdc, destination_domain, fake)
            return TxResult(tx_hash=fake, confirmed=True, status=1)

        Pubkey, Keypair, Transaction, Instruction, AccountMeta, Message, Hash = _import_solders()

        if not self.treasury_keypair_b58:
            raise RuntimeError("[solana_cctp] SOLANA_TREASURY_KEYPAIR_B58 não configurado")

        treasury = Keypair.from_base58_string(self.treasury_keypair_b58)
        mint = Pubkey.from_string(self.usdc_mint)
        amount_raw = int(amount_usdc * 10 ** USDC_DECIMALS_SOLANA)
        dest_caller = destination_caller_bytes32 or bytes(32)

        burn_token_account = self.derive_associated_token_address(treasury.pubkey(), mint)
        remote_token_messenger = self.derive_remote_token_messenger(destination_domain)

        # Conta que armazena o evento MessageSent — precisa ser um keypair FRESCO que
        # também ASSINA a transação (Signer<'info> no Rust). Criar inline só pro
        # AccountMeta sem incluí-lo nos signers faz a assinatura falhar.
        message_sent_event_kp = Keypair()

        data = (
            _anchor_discriminator("deposit_for_burn")
            + _borsh_u64(amount_raw)
            + _borsh_u32(destination_domain)
            + bytes(mint_recipient_bytes32)
            + bytes(dest_caller)
            + _borsh_u64(0)      # max_fee
            + _borsh_u32(2000)   # min_finality_threshold (finalized)
        )

        accounts = [
            AccountMeta(pubkey=treasury.pubkey(), is_signer=True, is_writable=False),   # owner
            AccountMeta(pubkey=treasury.pubkey(), is_signer=True, is_writable=True),    # event_rent_payer
            AccountMeta(pubkey=self.derive_sender_authority(), is_signer=False, is_writable=False),
            AccountMeta(pubkey=burn_token_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.derive_denylist_account(treasury.pubkey()), is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.derive_message_transmitter(), is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.derive_token_messenger(), is_signer=False, is_writable=False),
            AccountMeta(pubkey=remote_token_messenger, is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.derive_token_minter(), is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.derive_local_token(mint), is_signer=False, is_writable=True),
            AccountMeta(pubkey=mint, is_signer=False, is_writable=True),
            AccountMeta(pubkey=message_sent_event_kp.pubkey(), is_signer=True, is_writable=True),  # message_sent_event_data
            AccountMeta(pubkey=Pubkey.from_string(self.mt_program), is_signer=False, is_writable=False),
            AccountMeta(pubkey=Pubkey.from_string(self.tmm_program), is_signer=False, is_writable=False),
            AccountMeta(pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID), is_signer=False, is_writable=False),
            AccountMeta(pubkey=Pubkey.from_string(SYSTEM_PROGRAM_ID), is_signer=False, is_writable=False),
        ] + self._event_cpi_accounts(self.tmm_program)

        instruction = Instruction(
            program_id=Pubkey.from_string(self.tmm_program),
            accounts=accounts,
            data=data,
        )

        tx_hash = await self._build_sign_send(instruction, [treasury, message_sent_event_kp])
        LOG.info("[solana_cctp] depositForBurn sent tx=%s amount=%.4f domain=%d", tx_hash, amount_usdc, destination_domain)
        return TxResult(tx_hash=tx_hash, confirmed=True, status=1)

    # ------------------------------------------------------------------
    # Mint — Solana como chain de destino (ex: Arc -> Solana, payout de creator)
    # ------------------------------------------------------------------

    async def receive_and_mint(
        self,
        raw_message: bytes,
        attestation: bytes,
        recipient_owner_b58: str,
        source_domain: int,
        burn_token_bytes_32: bytes,
    ) -> TxResult:
        """
        receiveMessage real — recebe attestation Circle e credita USDC via CPI no
        TokenMessengerMinterV2. recipient_owner_b58 = dono (não a ATA) da conta que recebe.

        Layout VALIDADO em 03/07/2026 contra receive_message real na devnet
        (tx 2ceBribvKk2LR4awVdBH3EGFjJo7AKuSq68AmLTkerVN5JbQZNHVD6UGQsrqgnbCVugr58DY7FsiumdaGyi6ejJA):
        20 contas batem posição a posição, incluindo used_nonce, os dois event_authority
        e custody_token_account.
        """
        if self.sandbox:
            fake = f"sandbox_solana_mint_{recipient_owner_b58[:8]}"
            LOG.info("[solana_cctp] SANDBOX receiveMessage -> %s | tx=%s", recipient_owner_b58, fake)
            return TxResult(tx_hash=fake, confirmed=True, status=1)

        Pubkey, Keypair, Transaction, Instruction, AccountMeta, Message, Hash = _import_solders()

        if not self.treasury_keypair_b58:
            raise RuntimeError("[solana_cctp] SOLANA_TREASURY_KEYPAIR_B58 não configurado")

        payer = Keypair.from_base58_string(self.treasury_keypair_b58)
        mint = Pubkey.from_string(self.usdc_mint)
        recipient_owner = Pubkey.from_string(recipient_owner_b58)
        recipient_token_account = self.derive_associated_token_address(recipient_owner, mint)
        fee_recipient_ata = self.derive_associated_token_address(
            Pubkey.from_string(self.fee_recipient), mint
        )
        tmm_program = Pubkey.from_string(self.tmm_program)

        # nonce usado como seed do used_nonce PDA — extraído do próprio raw_message
        # (Message::NONCE_INDEX..SENDER_INDEX no source da Circle, offsets fixos do
        # formato de mensagem CCTP v2: nonce é bytes[12:44] no header de 116 bytes).
        nonce_seed = raw_message[12:44]

        data = _anchor_discriminator("receive_message") + _borsh_bytes(raw_message) + _borsh_bytes(attestation)

        remaining_accounts = [
            AccountMeta(pubkey=self.derive_token_messenger(), is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.derive_remote_token_messenger(source_domain), is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.derive_token_minter(), is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.derive_local_token(mint), is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.derive_token_pair(source_domain, burn_token_bytes_32), is_signer=False, is_writable=False),
            AccountMeta(pubkey=fee_recipient_ata, is_signer=False, is_writable=True),
            AccountMeta(pubkey=recipient_token_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.derive_custody_token_account(mint), is_signer=False, is_writable=True),
            AccountMeta(pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID), is_signer=False, is_writable=False),
        ] + self._event_cpi_accounts(self.tmm_program)

        accounts = [
            AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=False),  # caller
            AccountMeta(
                pubkey=self.derive_message_transmitter_authority(self.tmm_program),
                is_signer=False, is_writable=False,
            ),
            AccountMeta(pubkey=self.derive_message_transmitter(), is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.derive_used_nonce(nonce_seed), is_signer=False, is_writable=True),
            AccountMeta(pubkey=tmm_program, is_signer=False, is_writable=False),  # receiver
            AccountMeta(pubkey=Pubkey.from_string(SYSTEM_PROGRAM_ID), is_signer=False, is_writable=False),
        ] + self._event_cpi_accounts(self.mt_program) + remaining_accounts

        instruction = Instruction(
            program_id=Pubkey.from_string(self.mt_program),
            accounts=accounts,
            data=data,
        )

        # ATA do destinatário criada em TX SEPARADA (CreateIdempotent) e só quando não
        # existe — creator novo recebe sem assinatura dele (só o pubkey). Não pode ir na
        # mesma tx do receive: a mensagem CCTP (~380B) + attestation (130B) + 20 contas
        # deixam a tx a ~100B do teto de 1232; as 3 contas únicas da criação de ATA
        # (mint, owner, ATA program) estouram o limite (visto no 1º payout live, 04/07 —
        # ontem passou porque o destinatário era a tesouraria e as contas deduplicavam).
        if not await self._account_exists(recipient_token_account):
            create_ata_ix = Instruction(
                program_id=Pubkey.from_string(ASSOCIATED_TOKEN_PROGRAM_ID),
                accounts=[
                    AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=True),
                    AccountMeta(pubkey=recipient_token_account, is_signer=False, is_writable=True),
                    AccountMeta(pubkey=recipient_owner, is_signer=False, is_writable=False),
                    AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
                    AccountMeta(pubkey=Pubkey.from_string(SYSTEM_PROGRAM_ID), is_signer=False, is_writable=False),
                    AccountMeta(pubkey=Pubkey.from_string(SPL_TOKEN_PROGRAM_ID), is_signer=False, is_writable=False),
                ],
                data=bytes([1]),  # 1 = CreateIdempotent
            )
            ata_tx = await self._build_sign_send([create_ata_ix], [payer])
            await self._confirm_signature(ata_tx)
            LOG.info("[solana_cctp] ATA criada pro destinatário tx=%s", ata_tx)

        tx_hash = await self._build_sign_send([instruction], [payer])
        await self._confirm_signature(tx_hash)
        LOG.info("[solana_cctp] receiveMessage confirmado tx=%s -> %s", tx_hash, recipient_owner_b58)
        return TxResult(tx_hash=tx_hash, confirmed=True, status=1)

    # ------------------------------------------------------------------
    # Saldo + healthcheck
    # ------------------------------------------------------------------

    async def _account_exists(self, pubkey) -> bool:
        """getAccountInfo != null — usado pra decidir se a ATA do destinatário precisa
        ser criada (em tx separada, ver receive_and_mint)."""
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(
                self.rpc_url,
                json={
                    "jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
                    "params": [str(pubkey), {"encoding": "base64"}],
                },
            ) as resp:
                data = await resp.json()
                return data.get("result", {}).get("value") is not None

    async def get_usdc_balance(self, owner_b58: Optional[str] = None) -> float:
        if self.sandbox:
            return 1000.0
        Pubkey, *_ = _import_solders()
        mint = Pubkey.from_string(self.usdc_mint)
        owner = Pubkey.from_string(owner_b58) if owner_b58 else self._treasury_pubkey()
        ata = self.derive_associated_token_address(owner, mint)
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(
                self.rpc_url,
                json={
                    "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountBalance",
                    "params": [str(ata)],
                },
            ) as resp:
                data = await resp.json()
                value = data.get("result", {}).get("value")
                if not value:
                    return 0.0
                return float(value["uiAmountString"])

    def _treasury_pubkey(self):
        _, Keypair, *_ = _import_solders()
        return Keypair.from_base58_string(self.treasury_keypair_b58).pubkey()

    async def healthcheck(self) -> dict:
        if self.sandbox:
            return {"ok": True, "sandbox": True, "address": self.address}
        try:
            balance = await self.get_usdc_balance()
            return {"ok": True, "sandbox": False, "address": self.address, "usdc_balance": balance}
        except Exception as exc:
            return {"ok": False, "sandbox": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # RPC — build/sign/send (mesmo padrão de anchor_client.py)
    # ------------------------------------------------------------------

    async def _get_latest_blockhash(self):
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(
                self.rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash", "params": [{"commitment": "confirmed"}]},
            ) as resp:
                data = await resp.json()
                return data["result"]["value"]["blockhash"]

    async def _send_transaction(self, tx_b64: str) -> dict:
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(
                self.rpc_url,
                json={
                    "jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
                    "params": [tx_b64, {"encoding": "base64", "preflightCommitment": "confirmed"}],
                },
            ) as resp:
                return await resp.json()

    async def _confirm_signature(self, signature: str, timeout_s: float = 60.0) -> None:
        """Poll getSignatureStatuses até confirmed/finalized — sendTransaction sozinho é
        fire-and-forget e tx subsequente que dependa do estado (ex: receive depois da
        criação de ATA) falha na simulação se enviada antes da anterior aterrissar."""
        deadline = asyncio.get_event_loop().time() + timeout_s
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            while asyncio.get_event_loop().time() < deadline:
                async with session.post(
                    self.rpc_url,
                    json={
                        "jsonrpc": "2.0", "id": 1, "method": "getSignatureStatuses",
                        "params": [[signature], {"searchTransactionHistory": False}],
                    },
                ) as resp:
                    data = await resp.json()
                value = (data.get("result", {}).get("value") or [None])[0]
                if value:
                    if value.get("err"):
                        raise RuntimeError(f"[solana_cctp] tx falhou on-chain: {value['err']} sig={signature}")
                    if value.get("confirmationStatus") in ("confirmed", "finalized"):
                        return
                await asyncio.sleep(1.5)
        raise TimeoutError(f"[solana_cctp] tx não confirmou em {timeout_s:.0f}s: {signature}")

    async def _build_sign_send(self, instructions, signers: list) -> str:
        import base64
        Pubkey, Keypair, Transaction, Instruction, AccountMeta, Message, Hash = _import_solders()

        if not isinstance(instructions, list):
            instructions = [instructions]
        blockhash_str = await self._get_latest_blockhash()
        recent_blockhash = Hash.from_string(blockhash_str)
        message = Message.new_with_blockhash(
            instructions=instructions,
            payer=signers[0].pubkey(),
            blockhash=recent_blockhash,
        )
        tx = Transaction(signers, message, recent_blockhash)
        tx_b64 = base64.b64encode(bytes(tx)).decode()
        rpc_response = await self._send_transaction(tx_b64)
        if "error" in rpc_response:
            raise RuntimeError(f"[solana_cctp] RPC error: {rpc_response['error']}")
        return rpc_response.get("result", "")
