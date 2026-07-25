"""add_cctp_transfers

Sprint Lepton (CCTP multi-chain): generaliza o mecanismo CCTP real (burn->attest->receive)
já usado no par Sepolia->Arc para qualquer domain suportado pela Circle, incluindo Solana
(domain 5) e Stellar (domain 27, contratos Soroban). Persiste o que hoje é um BridgeState
in-memory de cctp_client.py, permitindo recovery pós-crash entre burn e receive. Também
adiciona solana_wallet em campaign_participants (só existia stellar_wallet).

Revision ID: 20260702_cctp_transfers
Revises:     20260630_settled_payments
Create Date: 2026-07-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision       = "20260702_cctp_transfers"
down_revision  = "20260630_settled_payments"
branch_labels  = None
depends_on     = None


def upgrade() -> None:
    op.create_table(
        "cctp_transfers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("intent_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("source_domain", sa.Integer(), nullable=False),
        sa.Column("dest_domain", sa.Integer(), nullable=False),
        sa.Column("counterparty", sa.Text(), nullable=False),
        sa.Column("amount_usdc", sa.Numeric(20, 8), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("source_tx_hash", sa.Text(), nullable=True),
        sa.Column("message_hash", sa.Text(), nullable=True),
        sa.Column("dest_tx_hash", sa.Text(), nullable=True),
        sa.Column("receipt_pqc", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intent_id"),
    )
    op.create_index("ix_cctp_transfers_intent_id", "cctp_transfers", ["intent_id"])
    op.create_index("ix_cctp_transfers_campaign_id", "cctp_transfers", ["campaign_id"])

    op.add_column(
        "campaign_participants",
        sa.Column("solana_wallet", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_participants", "solana_wallet")
    op.drop_index("ix_cctp_transfers_campaign_id", table_name="cctp_transfers")
    op.drop_index("ix_cctp_transfers_intent_id", table_name="cctp_transfers")
    op.drop_table("cctp_transfers")
