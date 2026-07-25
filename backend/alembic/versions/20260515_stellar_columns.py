"""stellar_columns

ADR-006: adiciona campos multi-chain para suporte Stellar.

- users.stellar_wallet
- campaign_participants.chain + stellar_wallet
- swaphistorys.chain + tx_hash

Revision ID: 20260515_stellar
Revises: 46a820fcb3c2
Create Date: 2026-05-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260515_stellar"
down_revision = "46a820fcb3c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.add_column(
        "users",
        sa.Column("stellar_wallet", sa.String(64), nullable=True),
    )
    op.create_index("ix_users_stellar_wallet", "users", ["stellar_wallet"], unique=False)

    # campaign_participants
    op.add_column(
        "campaign_participants",
        sa.Column("chain", sa.String(16), nullable=False, server_default="stellar"),
    )
    op.add_column(
        "campaign_participants",
        sa.Column("stellar_wallet", sa.String(64), nullable=True),
    )

    # swaphistorys
    op.add_column(
        "swaphistorys",
        sa.Column("chain", sa.String(16), nullable=False, server_default="stellar"),
    )
    op.add_column(
        "swaphistorys",
        sa.Column("tx_hash", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("swaphistorys", "tx_hash")
    op.drop_column("swaphistorys", "chain")
    op.drop_column("campaign_participants", "stellar_wallet")
    op.drop_column("campaign_participants", "chain")
    op.drop_index("ix_users_stellar_wallet", table_name="users")
    op.drop_column("users", "stellar_wallet")
