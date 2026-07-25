"""
rate_limiter.py — Rate limiting com Redis (sliding window) e fallback in-memory.

Estratégia:
    1. Tenta usar Redis como backend de rate limit (persistente entre restarts).
    2. Se Redis não estiver disponível, cai para in-memory (deque) — mesma lógica atual.
    3. O fallback garante que o servidor nunca quebra por falta de Redis.

Algoritmo: Sliding Window Counter
    - Janela de 60 segundos deslizante
    - Chave Redis: "xiaolee:rl:{key}" com TTL dinâmico
    - Atomic: usa pipeline Redis para garantir consistência

Variáveis de ambiente:
    REDIS_URL            — URL do Redis (ex: redis://localhost:6379/0)
                           Se não definida, usa in-memory como fallback.
    RATE_LIMIT_PER_MINUTE — Requests máximas por chave/minuto (default: 60)

Uso em FastAPI:
    limiter = get_rate_limiter()
    await limiter.check(key="user_123")  # lança HTTPException 429 se excedido
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict

from fastapi import HTTPException

LOG = logging.getLogger(__name__)

# Singleton do limiter (inicializado na primeira chamada)
_rate_limiter: "RateLimiter | None" = None


# ─── Interface base ────────────────────────────────────────────────────────────

class RateLimiter:
    """Interface comum para implementações de rate limiter."""

    async def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        """
        Verifica se a chave ultrapassou o limite.
        Lança HTTPException 429 se excedido.
        """
        raise NotImplementedError

    async def close(self) -> None:
        """Fecha conexões (se aplicável)."""
        pass


# ─── Implementação Redis ───────────────────────────────────────────────────────

class RedisRateLimiter(RateLimiter):
    """
    Rate limiter baseado em Redis com algoritmo sliding window.

    Algoritmo:
        1. ZADD key timestamp timestamp  (adiciona timestamp atual ao sorted set)
        2. ZREMRANGEBYSCORE key 0 window_start  (remove timestamps fora da janela)
        3. ZCARD key  (conta timestamps na janela)
        4. EXPIRE key window_seconds  (TTL automático)
    """

    def __init__(self, redis_url: str):
        import redis.asyncio as aioredis
        self._client = aioredis.from_url(redis_url, decode_responses=True)
        self._prefix = "xiaolee:rl:"
        LOG.info("[RedisRateLimiter] Initialized | url=%s", redis_url.split("@")[-1])

    async def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        redis_key = f"{self._prefix}{key}"
        now = datetime.now(timezone.utc)
        window_start = (now - timedelta(seconds=window_seconds)).timestamp()
        now_ts = now.timestamp()

        try:
            async with self._client.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(redis_key, 0, window_start)
                pipe.zadd(redis_key, {str(now_ts): now_ts})
                pipe.zcard(redis_key)
                pipe.expire(redis_key, window_seconds)
                results = await pipe.execute()

            count = results[2]
            if count > limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

        except HTTPException:
            raise
        except Exception as exc:
            # Redis indisponível: fail-open (não bloqueia o usuário)
            LOG.warning("[RedisRateLimiter] Redis error (fail-open) | key=%s | error=%s", key, exc)

    async def close(self) -> None:
        await self._client.aclose()
        LOG.info("[RedisRateLimiter] Connection closed")

    async def ping(self) -> bool:
        """Verifica conectividade com Redis."""
        try:
            return await self._client.ping()
        except Exception:
            return False


# ─── Fallback In-Memory ────────────────────────────────────────────────────────

class InMemoryRateLimiter(RateLimiter):
    """
    Rate limiter in-memory (fallback quando Redis não está disponível).
    Não persiste entre restarts — adequado para desenvolvimento e Devnet.
    """

    def __init__(self):
        self._hits: Dict[str, Deque[datetime]] = defaultdict(deque)
        LOG.warning("[InMemoryRateLimiter] Active — rate limits will reset on server restart")

    async def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)
        q = self._hits[key]

        # Remove timestamps fora da janela
        while q and q[0] < window_start:
            q.popleft()

        if len(q) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        q.append(now)

    def clear(self) -> None:
        """Limpa todos os contadores. Útil em testes."""
        self._hits.clear()


# ─── Factory ──────────────────────────────────────────────────────────────────

async def _try_redis(redis_url: str) -> RedisRateLimiter | None:
    """Tenta criar e pingar o Redis. Retorna None se falhar."""
    try:
        limiter = RedisRateLimiter(redis_url)
        if await limiter.ping():
            LOG.info("[RateLimiter] Redis conectado com sucesso")
            return limiter
        await limiter.close()
        LOG.warning("[RateLimiter] Redis ping falhou — usando in-memory")
    except Exception as exc:
        LOG.warning("[RateLimiter] Redis indisponível (%s) — usando in-memory", exc)
    return None


async def get_rate_limiter(redis_url: str | None = None) -> RateLimiter:
    """
    Retorna o limiter singleton (Redis se disponível, in-memory caso contrário).

    Chamado uma vez no startup da aplicação via lifespan.
    """
    global _rate_limiter

    if _rate_limiter is not None:
        return _rate_limiter

    import os
    url = redis_url or os.getenv("REDIS_URL", "")

    if url:
        redis_limiter = await _try_redis(url)
        if redis_limiter:
            _rate_limiter = redis_limiter
            return _rate_limiter

    _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


def reset_rate_limiter() -> None:
    """Reseta o singleton. Usado em testes."""
    global _rate_limiter
    _rate_limiter = None
