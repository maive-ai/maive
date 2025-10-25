"""Create calls table

Revision ID: ba8c60a76780
Revises: 
Create Date: 2025-10-24 15:05:39.061013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba8c60a76780'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create calls table
    op.create_table(
        'calls',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.String(length=255), nullable=False, comment='Cognito user ID (sub)'),
        sa.Column('project_id', sa.String(length=255), nullable=False, comment='Project/Job ID'),
        sa.Column('call_id', sa.String(length=255), nullable=False, comment='Provider call ID'),
        sa.Column('provider', sa.String(length=50), nullable=False, comment='Voice AI provider (vapi, etc.)'),
        sa.Column('status', sa.String(length=50), nullable=False, comment='Current call status'),
        sa.Column('phone_number', sa.String(length=20), nullable=False, comment='Phone number called'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Whether this is currently an active call'),
        sa.Column('listen_url', sa.Text(), nullable=True, comment='WebSocket URL for listening to call'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, comment='Call start timestamp'),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True, comment='Call end timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Record last update timestamp'),
        sa.Column('provider_data', sa.JSON(), nullable=True, comment='Raw provider response data'),
        sa.Column('analysis_data', sa.JSON(), nullable=True, comment='Structured analysis data from call (claims, payments, etc.)'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('call_id')
    )

    # Create indexes
    op.create_index('idx_user_active', 'calls', ['user_id', 'is_active'], unique=False)
    op.create_index('idx_project_started', 'calls', ['project_id', 'started_at'], unique=False)
    op.create_index('idx_user_started', 'calls', ['user_id', 'started_at'], unique=False)
    op.create_index(op.f('ix_calls_user_id'), 'calls', ['user_id'], unique=False)
    op.create_index(op.f('ix_calls_project_id'), 'calls', ['project_id'], unique=False)
    op.create_index(op.f('ix_calls_call_id'), 'calls', ['call_id'], unique=False)
    op.create_index(op.f('ix_calls_status'), 'calls', ['status'], unique=False)
    op.create_index(op.f('ix_calls_is_active'), 'calls', ['is_active'], unique=False)
    op.create_index(op.f('ix_calls_started_at'), 'calls', ['started_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_calls_started_at'), table_name='calls')
    op.drop_index(op.f('ix_calls_is_active'), table_name='calls')
    op.drop_index(op.f('ix_calls_status'), table_name='calls')
    op.drop_index(op.f('ix_calls_call_id'), table_name='calls')
    op.drop_index(op.f('ix_calls_project_id'), table_name='calls')
    op.drop_index(op.f('ix_calls_user_id'), table_name='calls')
    op.drop_index('idx_user_started', table_name='calls')
    op.drop_index('idx_project_started', table_name='calls')
    op.drop_index('idx_user_active', table_name='calls')
    op.drop_table('calls')
