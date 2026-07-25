"""initial_schema

Revision ID: 46a820fcb3c2
Revises:
Create Date: 2026-04-24 16:54:56.475821+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '46a820fcb3c2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('twitter_handle', sa.String(255), nullable=False),
        sa.Column('twitter_user_id', sa.Text(), nullable=False),
        sa.Column('telegram_chat_id', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('twitter_handle'),
        sa.UniqueConstraint('twitter_user_id'),
        sa.UniqueConstraint('telegram_chat_id'),
    )

    op.create_table('wallets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('address', sa.String(255), nullable=False),
        sa.Column('private_key_encrypted', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('address'),
    )

    op.create_table('tokenbalances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('token_symbol', sa.String(10), nullable=False),
        sa.Column('balance', sa.Numeric(20, 8), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('tokenprices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.Text(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('price_usd', sa.Numeric(20, 8), nullable=False),
        sa.Column('decimals', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol'),
    )

    op.create_table('swaphistorys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('from_token', sa.String(255), nullable=False),
        sa.Column('to_token', sa.String(255), nullable=False),
        sa.Column('from_amount', sa.Numeric(20, 8), nullable=False),
        sa.Column('to_amount', sa.Numeric(20, 8), nullable=False),
        sa.Column('exchange_rate', sa.Numeric(20, 8), nullable=False),
        sa.Column('value_usd', sa.Numeric(20, 8), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('transactionhistorys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(255), nullable=False),
        sa.Column('token_symbol', sa.String(255), nullable=False),
        sa.Column('amount', sa.Numeric(20, 8), nullable=False),
        sa.Column('tx_hash', sa.Text(), nullable=True),
        sa.Column('to_address', sa.String(255), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('confirmation_blocks', sa.Integer(), nullable=True),
        sa.Column('gas_used', sa.Integer(), nullable=True),
        sa.Column('gas_price', sa.Numeric(20, 8), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sender_twitter_handle', sa.String(255), nullable=True),
        sa.Column('recipient_twitter_handle', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('dmlogs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('message_type', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('twitter_message_id', sa.Text(), nullable=True),
        sa.Column('conversation_id', sa.String(255), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('request_id', sa.String(255), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_occurred', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dmlogs_request_id', 'dmlogs', ['request_id'])

    op.create_table('auth_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('twitter_user_id', sa.Text(), nullable=True),
        sa.Column('twitter_handle', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index('ix_auth_tokens_token', 'auth_tokens', ['token'])

    op.create_table('pending_transfers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_twitter_user_id', sa.Text(), nullable=False),
        sa.Column('from_twitter_handle', sa.Text(), nullable=False),
        sa.Column('recipient_twitter_handle', sa.Text(), nullable=False),
        sa.Column('token_symbol', sa.Text(), nullable=False),
        sa.Column('amount', sa.Numeric(20, 8), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('claimed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pending_transfers_recipient', 'pending_transfers', ['recipient_twitter_handle'])

    op.create_table('campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('creator_twitter_user_id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('campaign_type', sa.Text(), nullable=True),
        sa.Column('reward_token', sa.Text(), nullable=False),
        sa.Column('reward_per_participant', sa.Numeric(20, 8), nullable=False),
        sa.Column('max_participants', sa.Integer(), nullable=False),
        sa.Column('reward_pool', sa.Numeric(20, 8), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('creation_step', sa.Text(), nullable=True),
        sa.Column('profile_to_follow', sa.Text(), nullable=True),
        sa.Column('tweet_id_to_engage', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_campaigns_name', 'campaigns', ['name'])

    op.create_table('campaign_participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('has_followed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_replied', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_retweeted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_quoted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tasks_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('claim_receipt_id', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id', 'user_id', name='uq_participant_campaign_user'),
    )
    op.create_index('ix_campaign_participants_campaign_id', 'campaign_participants', ['campaign_id'])
    op.create_index('ix_campaign_participants_user_id', 'campaign_participants', ['user_id'])

    op.create_table('web_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(128), nullable=False),
        sa.Column('twitter_user_id', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id'),
    )
    op.create_index('ix_web_sessions_session_id', 'web_sessions', ['session_id'])

    op.create_table('processed_dms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('twitter_message_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('twitter_message_id'),
    )

    op.create_table('onchain_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('signature', sa.String(255), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('raw_payload', sa.Text(), nullable=False),
        sa.Column('tx_hash', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('signature'),
    )
    op.create_index('ix_onchain_events_signature', 'onchain_events', ['signature'])
    op.create_index('ix_onchain_events_event_type', 'onchain_events', ['event_type'])

    op.create_table('notification_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('related_signature', sa.String(255), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_events_user_id', 'notification_events', ['user_id'])
    op.create_index('ix_notification_events_related_signature', 'notification_events', ['related_signature'])


def downgrade() -> None:
    op.drop_table('notification_events')
    op.drop_table('onchain_events')
    op.drop_table('processed_dms')
    op.drop_table('web_sessions')
    op.drop_table('campaign_participants')
    op.drop_table('campaigns')
    op.drop_table('pending_transfers')
    op.drop_table('auth_tokens')
    op.drop_table('dmlogs')
    op.drop_table('transactionhistorys')
    op.drop_table('swaphistorys')
    op.drop_table('tokenprices')
    op.drop_table('tokenbalances')
    op.drop_table('wallets')
    op.drop_table('users')
