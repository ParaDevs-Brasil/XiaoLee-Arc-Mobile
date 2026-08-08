"""notification_events.delivered_at ganha timezone

Toda escrita em `delivered_at` (`notifications_routes.py::ack_notification`,
`helius_routes.py` nos dois canais de entrega) sempre gravou
`datetime.now(timezone.utc)` — aware, igual `UsedPayment.verified_at` e
`SettledPayment.settled_at`. A coluna nasceu `DateTime` puro (naive) por
descuido; em produção (Postgres/asyncpg) isso não é só inconsistência de
estilo, é erro em runtime: asyncpg recusa gravar um datetime aware num
`TIMESTAMP WITHOUT TIME ZONE` ("can't subtract offset-naive and
offset-aware datetimes"), e todo `POST /v1/notifications/{id}/ack` 500ava.

Revision ID: 20260807_notif_delivered_tz
Revises: 20260802_campaign_usdc
"""

from __future__ import annotations

from alembic import op

revision = "20260807_notif_delivered_tz"
down_revision = "20260802_campaign_usdc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite (dev local) não distingue TIMESTAMP WITH/WITHOUT TIME ZONE — o
    # valor é guardado como TEXT de qualquer forma, então não há coluna pra
    # migrar. Isso corrigia asyncpg/Postgres em produção; no-op em SQLite.
    if op.get_bind().dialect.name != "postgresql":
        return
    # Valores existentes já são instantes UTC (só nunca guardaram o offset) —
    # `AT TIME ZONE 'UTC'` reinterpreta o mesmo relógio como aware, sem
    # deslocar o horário.
    op.execute(
        "ALTER TABLE notification_events "
        "ALTER COLUMN delivered_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING delivered_at AT TIME ZONE 'UTC'"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        "ALTER TABLE notification_events "
        "ALTER COLUMN delivered_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING delivered_at AT TIME ZONE 'UTC'"
    )
