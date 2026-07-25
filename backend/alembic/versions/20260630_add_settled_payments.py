"""add_settled_payments

Sprint Lepton: persiste o feed de tração (POST /v1/payments/settled). Hoje vivia 100%
in-memory em server/metrics.py — qualquer restart do backend zerava o dashboard que o
júri vê, mesmo com transações reais confirmadas on-chain. Hidratado no lifespan do app.py.

Revision ID: 20260630_settled_payments
Revises:     20260624_receipt_pqc
Create Date: 2026-06-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision       = "20260630_settled_payments"
down_revision  = "20260624_receipt_pqc"
branch_labels  = None
depends_on     = None


def upgrade() -> None:
    op.create_table(
        "settled_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("intent_id", sa.Text(), nullable=False),
        sa.Column("creator_handle", sa.Text(), nullable=False),
        sa.Column("amount_usdc", sa.Numeric(20, 8), nullable=False),
        sa.Column("tx", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intent_id"),
    )
    op.create_index("ix_settled_payments_intent_id", "settled_payments", ["intent_id"])
    op.create_index("ix_settled_payments_creator_handle", "settled_payments", ["creator_handle"])


def downgrade() -> None:
    op.drop_index("ix_settled_payments_creator_handle", table_name="settled_payments")
    op.drop_index("ix_settled_payments_intent_id", table_name="settled_payments")
    op.drop_table("settled_payments")
