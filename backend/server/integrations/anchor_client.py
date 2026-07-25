"""
anchor_client.py — Interface Python para o programa XiaoLee Core (Anchor/Solana).

Sprint 6: implementação completa com solders para:
    - Derivação real de PDAs (Ed25519/SHA256)
    - Serialização Borsh da instrução record_swap
    - Build e assinatura da transação com admin keypair
    - Submit via RPC sendTransaction

Arquitetura de autorização:
    - `record_swap` exige a chave privada do admin como signer.
    - Configurada via SOLANA_ADMIN_KEYPAIR_B58 (base58).
    - Sem keypair: dry_run=True (Devnet/testes — loga sem submeter).

Program ID: Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM
IDL: frontend/src/idl/xiaolee_core.json
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import struct
from typing import Any

import aiohttp

LOG = logging.getLogger(__name__)

# ─── Constantes do programa ────────────────────────────────────────────────────

XIAOLEE_PROGRAM_ID = "Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM"

# Discriminadores extraídos do IDL (8 bytes únicos por instrução — hash Anchor)
RECORD_SWAP_DISCRIMINATOR = bytes([164, 158, 148, 54, 167, 137, 171, 59])
INITIALIZE_USER_DISCRIMINATOR = bytes([111, 17, 185, 250, 60, 122, 38, 254])
INITIALIZE_GLOBAL_DISCRIMINATOR = bytes([47, 225, 15, 112, 86, 51, 190, 231])

# Seeds para derivação de PDAs (alinhadas com lib.rs)
SEED_GLOBAL_CONFIG = b"global_config"
SEED_USER = b"user"

# Solana System Program ID
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"


def _import_solders():
    """Import lazy de solders — evita erro de import se não instalado."""
    try:
        from solders.pubkey import Pubkey
        from solders.keypair import Keypair
        from solders.transaction import Transaction
        from solders.instruction import Instruction, AccountMeta
        from solders.message import Message
        from solders.hash import Hash
        return Pubkey, Keypair, Transaction, Instruction, AccountMeta, Message, Hash
    except ImportError as exc:
        raise RuntimeError(
            "solders não está instalado. Execute: pip install solders"
        ) from exc


class AnchorClient:
    """
    Cliente Python para interagir com o programa XiaoLee Core on-chain.

    Modos de operação:
        dry_run=True  — loga instrução sem submeter (sem keypair configurada)
        dry_run=False — deriva PDAs reais, constrói, assina e submete transação
    """

    def __init__(
        self,
        rpc_url: str,
        admin_keypair_b58: str | None = None,
        timeout_seconds: int = 15,
    ):
        self.rpc_url = rpc_url
        self._keypair_b58 = admin_keypair_b58 or os.getenv("SOLANA_ADMIN_KEYPAIR_B58", "")
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.dry_run = not bool(self._keypair_b58)

        if self.dry_run:
            LOG.warning(
                "[AnchorClient] dry_run=True — SOLANA_ADMIN_KEYPAIR_B58 não configurada. "
                "record_swap será simulado sem submissão on-chain."
            )

    @property
    def enabled(self) -> bool:
        return bool(self.rpc_url)

    # ─── PDA Derivation (solders) ──────────────────────────────────────────────

    def derive_user_state_pda(self, twitter_id: str) -> str:
        """
        Deriva o endereço PDA de UserState para um twitter_id.
        Seeds: [b"user", twitter_id.encode()]
        """
        Pubkey, *_ = _import_solders()
        program_id = Pubkey.from_string(XIAOLEE_PROGRAM_ID)
        pda, bump = Pubkey.find_program_address(
            [SEED_USER, twitter_id.encode()],
            program_id,
        )
        LOG.debug("[AnchorClient] UserState PDA | twitter_id=%s | pda=%s | bump=%d",
                  twitter_id, pda, bump)
        return str(pda)

    def derive_global_config_pda(self) -> str:
        """
        Deriva o endereço PDA de GlobalConfig.
        Seeds: [b"global_config"]
        """
        Pubkey, *_ = _import_solders()
        program_id = Pubkey.from_string(XIAOLEE_PROGRAM_ID)
        pda, bump = Pubkey.find_program_address([SEED_GLOBAL_CONFIG], program_id)
        LOG.debug("[AnchorClient] GlobalConfig PDA | pda=%s | bump=%d", pda, bump)
        return str(pda)

    # ─── Instrução record_swap ─────────────────────────────────────────────────

    def _build_record_swap_instruction_data(self, volume_lamports: int) -> bytes:
        """
        Serializa a instrução record_swap no formato Anchor/Borsh:
            [discriminator: 8 bytes] + [volume: u64 little-endian 8 bytes]
        """
        volume_bytes = struct.pack("<Q", volume_lamports)
        return RECORD_SWAP_DISCRIMINATOR + volume_bytes

    # ─── Submit via RPC ───────────────────────────────────────────────────────

    async def _get_latest_blockhash(self) -> str:
        """Obtém o blockhash mais recente do RPC."""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                self.rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash",
                      "params": [{"commitment": "confirmed"}]},
            ) as resp:
                data = await resp.json()
                return data["result"]["value"]["blockhash"]

    async def _send_transaction(self, tx_b64: str) -> dict[str, Any]:
        """Envia uma transação serializada em base64 para o RPC."""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                self.rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [tx_b64, {"encoding": "base64", "preflightCommitment": "confirmed"}],
                },
            ) as resp:
                return await resp.json()

    # ─── record_swap (main) ───────────────────────────────────────────────────

    async def record_swap(
        self,
        twitter_id: str,
        volume_lamports: int,
        signature: str | None = None,
    ) -> dict[str, Any]:
        """
        Chama `record_swap` on-chain para registrar um swap confirmado.

        Args:
            twitter_id:      Twitter ID do usuário (seed da UserState PDA).
            volume_lamports: Volume do swap em lamports (u64).
            signature:       Assinatura Helius original para rastreabilidade.

        Returns:
            dict com status, tx_signature (se submetida), dry_run e metadados.
        """
        LOG.info(
            "[AnchorClient] record_swap | twitter_id=%s | vol=%d | sig=%s | dry_run=%s",
            twitter_id, volume_lamports, signature, self.dry_run,
        )

        if not self.enabled:
            return {"status": "skipped", "reason": "rpc_url not configured", "dry_run": True}

        # Serializa a instrução independente do modo
        instruction_data = self._build_record_swap_instruction_data(volume_lamports)

        if self.dry_run:
            return {
                "status": "dry_run",
                "reason": "SOLANA_ADMIN_KEYPAIR_B58 not configured",
                "twitter_id": twitter_id,
                "volume_lamports": volume_lamports,
                "instruction_data_hex": instruction_data.hex(),
                "helius_signature": signature,
                "dry_run": True,
            }

        # ── Submit real com solders ───────────────────────────────────────────
        try:
            Pubkey, Keypair, Transaction, Instruction, AccountMeta, Message, Hash = _import_solders()

            # 1. Carrega o admin keypair
            admin_keypair = Keypair.from_base58_string(self._keypair_b58)
            admin_pubkey = admin_keypair.pubkey()

            # 2. Deriva PDAs
            program_id = Pubkey.from_string(XIAOLEE_PROGRAM_ID)
            global_config_pda_str = self.derive_global_config_pda()
            user_state_pda_str = self.derive_user_state_pda(twitter_id)
            global_config_pda = Pubkey.from_string(global_config_pda_str)
            user_state_pda = Pubkey.from_string(user_state_pda_str)

            # 3. Constrói a instrução record_swap
            # Contas: global_config (read), user_state (write), admin (signer+write)
            accounts = [
                AccountMeta(pubkey=global_config_pda, is_signer=False, is_writable=False),
                AccountMeta(pubkey=user_state_pda, is_signer=False, is_writable=True),
                AccountMeta(pubkey=admin_pubkey, is_signer=True, is_writable=True),
            ]
            instruction = Instruction(
                program_id=program_id,
                accounts=accounts,
                data=instruction_data,
            )

            # 4. Obtém blockhash recente
            blockhash_str = await self._get_latest_blockhash()
            recent_blockhash = Hash.from_string(blockhash_str)

            # 5. Constrói e assina a transação
            message = Message.new_with_blockhash(
                instructions=[instruction],
                payer=admin_pubkey,
                blockhash=recent_blockhash,
            )
            tx = Transaction([admin_keypair], message, recent_blockhash)

            # 6. Serializa e envia
            tx_bytes = bytes(tx)
            tx_b64 = base64.b64encode(tx_bytes).decode()
            rpc_response = await self._send_transaction(tx_b64)

            if "error" in rpc_response:
                LOG.error("[AnchorClient] RPC error | %s", rpc_response["error"])
                return {
                    "status": "error",
                    "rpc_error": rpc_response["error"],
                    "twitter_id": twitter_id,
                    "dry_run": False,
                }

            tx_signature = rpc_response.get("result")
            LOG.info("[AnchorClient] record_swap submitted | tx=%s", tx_signature)

            return {
                "status": "submitted",
                "tx_signature": tx_signature,
                "twitter_id": twitter_id,
                "volume_lamports": volume_lamports,
                "global_config_pda": global_config_pda_str,
                "user_state_pda": user_state_pda_str,
                "helius_signature": signature,
                "dry_run": False,
            }

        except Exception as exc:
            LOG.error("[AnchorClient] Falha ao submeter record_swap | error=%s", exc)
            return {
                "status": "error",
                "reason": str(exc),
                "twitter_id": twitter_id,
                "dry_run": False,
            }

    # ─── Health check ─────────────────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Verifica conectividade com o RPC Solana."""
        if not self.enabled:
            return {"status": "disabled"}
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    self.rpc_url,
                    json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                ) as resp:
                    data = await resp.json()
                    return {
                        "status": "ok" if data.get("result") == "ok" else "degraded",
                        "dry_run": self.dry_run,
                        "has_admin_keypair": not self.dry_run,
                    }
        except asyncio.TimeoutError:
            return {"status": "timeout", "dry_run": self.dry_run}
        except Exception as exc:
            return {"status": "error", "reason": str(exc), "dry_run": self.dry_run}
