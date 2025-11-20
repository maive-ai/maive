"""add_threads_and_messages_tables

Revision ID: af7b2a60dd99
Revises: f4d9791102c4
Create Date: 2025-11-20 11:26:43.689308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'af7b2a60dd99'
down_revision: Union[str, Sequence[str], None] = 'f4d9791102c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create threads table
    op.create_table('threads',
    sa.Column('id', sa.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False, comment='Thread UUID'),
    sa.Column('user_id', sa.String(length=255), nullable=False, comment='User ID (Cognito sub)'),
    sa.Column('title', sa.Text(), nullable=False, comment='Thread display title'),
    sa.Column('archived', sa.Boolean(), nullable=False, comment='Whether thread is archived'),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='Record creation timestamp'),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, comment='Record last update timestamp'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_threads_user_archived', 'threads', ['user_id', 'archived'], unique=False)
    op.create_index('idx_threads_user_updated', 'threads', ['user_id', 'updated_at'], unique=False)
    op.create_index(op.f('ix_threads_user_id'), 'threads', ['user_id'], unique=False)

    # Create messages table
    op.create_table('messages',
    sa.Column('id', sa.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False, comment='Message UUID'),
    sa.Column('thread_id', sa.UUID(as_uuid=False), nullable=False, comment='Thread UUID'),
    sa.Column('role', sa.String(length=20), nullable=False, comment='Message role: user, assistant, or system'),
    sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Message content as JSON (ThreadMessage format)'),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='Record creation timestamp'),
    sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_messages_thread_created', 'messages', ['thread_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_messages_thread_id'), 'messages', ['thread_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop messages table (foreign key dependent on threads)
    op.drop_index(op.f('ix_messages_thread_id'), table_name='messages')
    op.drop_index('idx_messages_thread_created', table_name='messages')
    op.drop_table('messages')

    # Drop threads table
    op.drop_index(op.f('ix_threads_user_id'), table_name='threads')
    op.drop_index('idx_threads_user_updated', table_name='threads')
    op.drop_index('idx_threads_user_archived', table_name='threads')
    op.drop_table('threads')
