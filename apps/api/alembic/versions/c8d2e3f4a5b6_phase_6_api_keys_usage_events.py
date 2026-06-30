"""phase 6 api keys and usage events

Revision ID: c8d2e3f4a5b6
Revises: b7c1d2e3f4a5
Create Date: 2026-06-30 13:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d2e3f4a5b6'
down_revision: Union[str, None] = 'b7c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('key_prefix', sa.String(length=20), nullable=False),
        sa.Column('hashed_key', sa.String(length=64), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_api_keys_hashed_key'), 'api_keys', ['hashed_key'], unique=True)
    op.create_index(op.f('ix_api_keys_workspace_id'), 'api_keys', ['workspace_id'], unique=False)

    op.create_table(
        'usage_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('event_type', sa.Enum('question', 'document_processed', 'api_call', name='usage_event_type', native_enum=False, length=30), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=False),
        sa.Column('tokens_out', sa.Integer(), nullable=False),
        sa.Column('cost_estimate', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usage_events_created_at'), 'usage_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_usage_events_workspace_id'), 'usage_events', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_usage_events_workspace_id'), table_name='usage_events')
    op.drop_index(op.f('ix_usage_events_created_at'), table_name='usage_events')
    op.drop_table('usage_events')
    op.drop_index(op.f('ix_api_keys_workspace_id'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_hashed_key'), table_name='api_keys')
    op.drop_table('api_keys')
