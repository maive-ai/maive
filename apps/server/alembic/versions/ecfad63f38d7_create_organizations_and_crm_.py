"""create_organizations_and_crm_credentials_tables

Revision ID: ecfad63f38d7
Revises: 82986719e63e
Create Date: 2025-11-14 17:28:59.688762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecfad63f38d7'
down_revision: Union[str, Sequence[str], None] = '82986719e63e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=36), nullable=False, comment='Organization UUID'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Organization display name'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Record last update timestamp'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create organization_crm_credentials table
    op.create_table(
        'organization_crm_credentials',
        sa.Column('id', sa.String(length=36), nullable=False, comment='Credential record UUID'),
        sa.Column('organization_id', sa.String(length=36), nullable=False, comment='Organization UUID'),
        sa.Column('provider', sa.String(length=50), nullable=False, comment='CRM provider name (job_nimbus, service_titan)'),
        sa.Column('secret_arn', sa.String(length=512), nullable=False, comment='AWS Secrets Manager ARN for credentials'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Whether this credential set is active'),
        sa.Column('created_by', sa.String(length=255), nullable=False, comment='User ID who configured credentials'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Record last update timestamp'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_organization_crm_credentials_organization_id'), 'organization_crm_credentials', ['organization_id'], unique=False)
    op.create_index(op.f('ix_organization_crm_credentials_is_active'), 'organization_crm_credentials', ['is_active'], unique=False)
    op.create_index('idx_org_crm_active', 'organization_crm_credentials', ['organization_id', 'is_active'], unique=False)
    # Partial unique index: only one active credential set per organization
    op.create_index('uq_org_active_credentials', 'organization_crm_credentials', ['organization_id'], unique=True, postgresql_where=sa.text('is_active = true'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_org_active_credentials', table_name='organization_crm_credentials')
    op.drop_index('idx_org_crm_active', table_name='organization_crm_credentials')
    op.drop_index(op.f('ix_organization_crm_credentials_is_active'), table_name='organization_crm_credentials')
    op.drop_index(op.f('ix_organization_crm_credentials_organization_id'), table_name='organization_crm_credentials')
    op.drop_table('organization_crm_credentials')
    op.drop_table('organizations')
