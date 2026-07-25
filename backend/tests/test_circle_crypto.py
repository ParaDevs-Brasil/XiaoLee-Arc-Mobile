"""
Testes do entitySecretCiphertext (Circle W3S) — gate do Arc live.

Cobre o contrato que a Circle exige:
  - ciphertext é base64 válido
  - é FRESCO a cada chamada (RSA-OAEP usa padding aleatório)
  - rejeita entity secret que não tem 32 bytes
  - exige CIRCLE_ENTITY_SECRET configurado
"""

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from server.integrations import circle_crypto
from server.integrations.circle_crypto import _encrypt, entity_secret_ciphertext


def _test_public_key_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def test_encrypt_returns_valid_base64():
    pem = _test_public_key_pem()
    ct = _encrypt(pem, "00" * 32)
    # decodifica sem erro e tem o tamanho de um bloco RSA-2048 (256 bytes)
    assert len(base64.b64decode(ct)) == 256


def test_ciphertext_is_fresh_each_call():
    """Circle invalida cada ciphertext após o uso — nunca pode repetir."""
    pem = _test_public_key_pem()
    secret = "ab" * 32
    assert _encrypt(pem, secret) != _encrypt(pem, secret)


def test_rejects_non_32_byte_secret():
    pem = _test_public_key_pem()
    with pytest.raises(ValueError, match="32 bytes"):
        _encrypt(pem, "00" * 16)  # só 16 bytes


def test_rejects_non_hex_secret():
    pem = _test_public_key_pem()
    with pytest.raises(ValueError, match="hex"):
        _encrypt(pem, "zz" * 32)


@pytest.mark.asyncio
async def test_requires_entity_secret_configured():
    with pytest.raises(RuntimeError, match="CIRCLE_ENTITY_SECRET"):
        await entity_secret_ciphertext("api_key", "", "https://api.circle.com/v1/w3s")


@pytest.mark.asyncio
async def test_uses_cached_public_key_without_network(monkeypatch):
    """Com a chave pública cacheada, gera o ciphertext sem tocar a rede."""
    base = "https://test.circle/v1/w3s"
    monkeypatch.setitem(circle_crypto._PUBLIC_KEY_CACHE, base, _test_public_key_pem())

    class _BoomClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k):
            raise AssertionError("não deveria chamar a rede — chave pública cacheada")

    monkeypatch.setattr(circle_crypto.httpx, "AsyncClient", _BoomClient)
    ct = await entity_secret_ciphertext("api_key", "cd" * 32, base)
    assert len(base64.b64decode(ct)) == 256
