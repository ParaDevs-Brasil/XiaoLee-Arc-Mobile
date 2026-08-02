"""Campanhas passam a recompensar em USDC — o token $XLEE deixa de existir.

`_seed_default_campaigns` (campaigns_routes.py) só insere quando a tabela está
vazia, então trocar as constantes do seed não alcança nenhum banco que já rodou:
o Postgres do Railway e o SQLite de dev seguiriam servindo "$XLEE" para sempre.
Daí esta migração de dados.

As três campanhas semente ganham os valores novos por id. Qualquer outra linha
que ainda esteja em $XLEE cai no padrão do produto (1 USDC por participante) em
vez de herdar o número antigo: um reward de "250" fazia sentido como token de
airdrop e viraria 250 dólares por pessoa se só trocássemos o símbolo.

Revision ID: 20260802_campaign_usdc
Revises: 20260702_cctp_transfers
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision       = "20260802_campaign_usdc"
down_revision  = "20260702_cctp_transfers"
branch_labels  = None
depends_on     = None

# id → (reward_per_participant, reward_pool, description). O pool é
# reward * max_participants, a mesma conta que `create_campaign` faz para
# campanhas novas. A descrição entra aqui porque é ela que o card exibe: sem
# reescrever, o cartão diria "earn $XLEE tokens!" ao lado de "0.3 USDC". Os
# textos são os mesmos de DEFAULT_CAMPAIGNS em `server/campaigns_routes.py`.
_SEED_CAMPAIGNS = {
    1: (
        0.3, 300,
        "Be among the first to interact with XiaoLee and earn USDC! Follow our account, "
        "retweet our launch post and send a message to our bot.",
    ),
    2: (
        0.5, 250,
        "Execute your first swap via XiaoLee AI assistant and earn bonus USDC. Just ask "
        "XiaoLee to help you swap any token!",
    ),
    3: (
        1.0, 200,
        "Invite 3 friends to join XiaoLee and earn community rewards in USDC. Share your "
        "referral link and help grow the XiaoLee ecosystem.",
    ),
}


def upgrade() -> None:
    conn = op.get_bind()

    update = sa.text(
        "UPDATE campaigns SET reward_token = 'USDC', reward_per_participant = :reward, "
        "reward_pool = :pool, description = :description "
        "WHERE id = :id AND reward_token = '$XLEE'"
    )
    for campaign_id, (reward, pool, description) in _SEED_CAMPAIGNS.items():
        conn.execute(
            update,
            {"reward": reward, "pool": pool, "description": description, "id": campaign_id},
        )

    # Sobras: campanha criada à mão em $XLEE. Valor vai para o padrão seguro.
    #
    # A descrição NÃO é tocada de propósito. Ela é texto de terceiro e costuma
    # repetir o valor ("Ganhe 250 $XLEE por seguir a gente"); um REPLACE do
    # símbolo transformaria isso em "Ganhe 250 USDC" ao lado de um reward de 1
    # USDC — uma promessa de dinheiro falsa, pior do que uma frase visivelmente
    # desatualizada citando um token que não existe mais.
    conn.execute(
        sa.text(
            "UPDATE campaigns SET reward_token = 'USDC', reward_per_participant = 1, "
            "reward_pool = max_participants WHERE reward_token = '$XLEE'"
        )
    )


def downgrade() -> None:
    # Sem volta: os valores em $XLEE eram tokenomics e não sobrevivem à conversão
    # (0.3 USDC não tem preimagem em "50 XLEE"). Reverter só o símbolo deixaria o
    # banco pior do que os dois estados — 0.3 $XLEE não é nada.
    raise NotImplementedError("conversão de $XLEE para USDC não é reversível")
