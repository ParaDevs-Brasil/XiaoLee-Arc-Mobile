"""add_payment_intents

Sprint Lepton (Arc/Circle): tabela de intent log durável para pagamentos USDC.
Anti-replay via intent_id (UUID v4). Garante idempotência em restart do agente.

Revision ID: 20260622_payment_intents
Revises: 20260515_stellar
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260622_payment_intents"
down_revision = "20260522_used_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_intents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("intent_id", sa.String(36), nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("creator_id", sa.Text(), nullable=False),
        sa.Column("amount_usdc", sa.Numeric(20, 8), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("arc_tx_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intent_id"),
    )
    op.create_index("ix_payment_intents_intent_id", "payment_intents", ["intent_id"])
    op.create_index("ix_payment_intents_campaign_id", "payment_intents", ["campaign_id"])
    op.create_index("ix_payment_intents_creator_id", "payment_intents", ["creator_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_intents_creator_id", table_name="payment_intents")
    op.drop_index("ix_payment_intents_campaign_id", table_name="payment_intents")
    op.drop_index("ix_payment_intents_intent_id", table_name="payment_intents")
    op.drop_table("payment_intents")
