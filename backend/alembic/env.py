"""
alembic/env.py — Configuração do ambiente de migração (async-compatible).

Suporta modo online (conexão real) e offline (geração de SQL sem conexão).
Usa asyncio para compatibilidade com SQLAlchemy async + asyncpg/aiosqlite.

Variáveis de ambiente:
    DATABASE_URL — URL de banco (ver database.py para regras de normalização).
"""

from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ─── Path setup ────────────────────────────────────────────────────────────────
# Adiciona o diretório backend ao sys.path para importar os modelos
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.base import Base  # noqa: E402 — importado após path setup
from database.database import _build_database_url  # noqa: E402

# Importa todos os modelos para que o metadata contenha todas as tabelas
import database.models  # noqa: E402, F401

# ─── Alembic config ────────────────────────────────────────────────────────────

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata alvo — contém todas as tabelas definidas nos modelos
target_metadata = Base.metadata

# URL dinâmica via env (DATABASE_URL)
database_url = _build_database_url()
config.set_main_option("sqlalchemy.url", database_url)


# ─── Modo offline ──────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Gera SQL de migração sem conexão real com o banco.
    Útil para revisar migrações antes de aplicar.

    Uso: alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ─── Modo online (async) ───────────────────────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Inclui esquema em nomes de tabela para PostgreSQL com schemas
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Executa migrações em modo async (asyncpg/aiosqlite)."""
    import sys
    import traceback

    db_url = config.get_main_option("sqlalchemy.url") or "NOT SET"
    safe_url = db_url.split("@")[-1] if "@" in db_url else db_url[:40]
    print(f"[alembic] Connecting to: {safe_url}", flush=True)

    try:
        connectable = async_engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()
        print("[alembic] Migrations completed successfully", flush=True)
    except Exception as exc:
        print(f"[alembic] Migration FAILED: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        raise


def run_migrations_online() -> None:
    """Entry point para modo online — executa via asyncio."""
    asyncio.run(run_async_migrations())


# ─── Dispatch ─────────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
