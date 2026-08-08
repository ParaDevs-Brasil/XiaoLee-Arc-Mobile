"""Chat da web ganha sessões — cada conversa vira uma thread própria em vez
de um log infinito por usuário. `chat_sessions` guarda o título/last-activity
de cada thread; as mensagens continuam em `dmlogs` (já tinha `session_id`,
só nunca era usado nem indexado), agora com `str(chat_sessions.id)` nele.

Revision ID: 20260808_chat_sessions
Revises: 20260807_notif_delivered_tz
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260808_chat_sessions"
down_revision = "20260807_notif_delivered_tz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_dmlogs_session_id"), "dmlogs", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dmlogs_session_id"), table_name="dmlogs")
    op.drop_index(op.f("ix_chat_sessions_user_id"), table_name="chat_sessions")
    op.drop_table("chat_sessions")
