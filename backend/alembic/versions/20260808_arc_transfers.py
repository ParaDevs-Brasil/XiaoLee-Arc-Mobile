"""As transferências USDC que o usuário manda pelo chat ("send 5 usdc to...") são
relayadas por `POST /v1/arc/usdc/relay-authorization` e nunca ficavam gravadas —
a rota é pública (a assinatura autoriza, não uma sessão) e devolvia o tx_hash
direto para o cliente sem passar pelo banco. Resultado: a aba Transactions do
app (que só lê campaign claims + notificações do Helius) nunca sabia que essas
transferências existiam. `arc_transfers` dá a essas transferências um lugar
para morar, consultável por endereço de wallet.

Revision ID: 20260808_arc_transfers
Revises: 20260808_chat_sessions
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260808_arc_transfers"
down_revision = "20260808_chat_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "arc_transfers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("from_address", sa.String(length=42), nullable=False),
        sa.Column("to_address", sa.String(length=42), nullable=False),
        sa.Column("amount_usdc", sa.Numeric(20, 8), nullable=False),
        sa.Column("tx_hash", sa.String(length=66), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tx_hash"),
    )
    op.create_index(op.f("ix_arc_transfers_from_address"), "arc_transfers", ["from_address"], unique=False)
    op.create_index(op.f("ix_arc_transfers_to_address"), "arc_transfers", ["to_address"], unique=False)
    op.create_index(op.f("ix_arc_transfers_tx_hash"), "arc_transfers", ["tx_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_arc_transfers_tx_hash"), table_name="arc_transfers")
    op.drop_index(op.f("ix_arc_transfers_to_address"), table_name="arc_transfers")
    op.drop_index(op.f("ix_arc_transfers_from_address"), table_name="arc_transfers")
    op.drop_table("arc_transfers")
