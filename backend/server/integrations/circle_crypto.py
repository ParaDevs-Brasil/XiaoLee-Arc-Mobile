"""
circle_crypto.py — Geração do entitySecretCiphertext exigido pela Circle W3S.

Toda request que MUDA ESTADO numa developer-controlled wallet (criar walletSet,
criar wallet, transferir) precisa de um `entitySecretCiphertext`:

    RSA-OAEP-SHA256( entity_secret_32_bytes )  →  base64

Regras da Circle:
  - A chave pública da entity é estável (pode ser cacheada).
  - O ciphertext NÃO pode ser reutilizado: RSA-OAEP usa padding aleatório, então
    cada chamada gera um valor diferente, e a Circle invalida cada ciphertext após
    o primeiro uso. Por isso geramos um ciphertext NOVO a cada request.

Endpoint da chave pública:
    GET {base}/config/entity/publicKey   (base = .../v1/w3s)
"""

from __future__ import annotations

import base64
import logging

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

LOG = logging.getLogger(__name__)

# Cache da chave pública por base_url (sandbox vs live). A chave é estável.
_PUBLIC_KEY_CACHE: dict[str, str] = {}


async def fetch_entity_public_key(api_key: str, base_url: str) -> str:
    """Busca (e cacheia) a chave pública RSA da entity na Circle."""
    cached = _PUBLIC_KEY_CACHE.get(base_url)
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{base_url}/config/entity/publicKey",
            headers={"Authorization": f"Bearer {api_key}"},
        )
    if not resp.is_success:
        raise RuntimeError(
            f"[circle] entity publicKey error {resp.status_code}: {resp.text[:300]}"
        )

    pub = resp.json().get("data", {}).get("publicKey", "")
    if not pub:
        raise RuntimeError("[circle] entity publicKey ausente na resposta")

    _PUBLIC_KEY_CACHE[base_url] = pub
    LOG.info("[circle] entity publicKey carregada e cacheada | base=%s", base_url)
    return pub


def _encrypt(public_key_pem: str, entity_secret_hex: str) -> str:
    """RSA-OAEP-SHA256 do entity secret (32 bytes hex) → base64."""
    try:
        secret_bytes = bytes.fromhex(entity_secret_hex.strip())
    except ValueError as exc:
        raise ValueError("CIRCLE_ENTITY_SECRET não é hex válido") from exc

    if len(secret_bytes) != 32:
        raise ValueError(
            f"CIRCLE_ENTITY_SECRET deve ter 32 bytes (64 hex chars); "
            f"recebido {len(secret_bytes)} bytes"
        )

    public_key = serialization.load_pem_public_key(public_key_pem.encode())
    ciphertext = public_key.encrypt(
        secret_bytes,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(ciphertext).decode()


async def entity_secret_ciphertext(
    api_key: str,
    entity_secret_hex: str,
    base_url: str,
) -> str:
    """
    Gera um entitySecretCiphertext FRESCO para uma request Circle W3S.

    Chame uma vez por request que muda estado. Não reutilize o retorno.
    """
    if not entity_secret_hex:
        raise RuntimeError(
            "CIRCLE_ENTITY_SECRET não configurado — exigido para transações live. "
            "Gere em console.circle.com → Developer → Configurator e coloque no .env."
        )
    public_key = await fetch_entity_public_key(api_key, base_url)
    return _encrypt(public_key, entity_secret_hex)
