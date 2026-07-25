"""add_receipt_pqc

Sprint Lepton (PQC): coluna receipt_pqc na tabela payment_intents.
Armazena a assinatura ML-DSA-87 (FIPS 204) do recibo de pagamento.
Formato: "<sig_b64>.<payload_b64>" — verificável com a public key pública.

Revision ID: 20260624_receipt_pqc
Revises:     20260622_payment_intents
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision       = "20260624_receipt_pqc"
down_revision  = "20260622_payment_intents"
branch_labels  = None
depends_on     = None


def upgrade() -> None:
    op.add_column(
        "payment_intents",
        sa.Column("receipt_pqc", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment_intents", "receipt_pqc")
