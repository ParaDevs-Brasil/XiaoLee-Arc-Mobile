"""used_payments — SEC-001 replay attack prevention

Revision ID: 20260522_used_payments
Revises: 20260515_stellar
Create Date: 2026-05-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260522_used_payments"
down_revision = "20260515_stellar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "used_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tx_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("amount_xlm", sa.Numeric(20, 8), nullable=True),
        sa.Column("network", sa.String(16), nullable=False, server_default="testnet"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_used_payments_tx_hash", "used_payments", ["tx_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_used_payments_tx_hash", table_name="used_payments")
    op.drop_table("used_payments")
