"""rename_twilio_config_to_phone_numbers

Revision ID: rename_to_phone_numbers
Revises: a1b2c3d4e5f6
Create Date: 2025-11-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "rename_to_phone_numbers"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()
    
    # Step 1: Add user_id column (nullable initially)
    op.add_column(
        "organization_twilio_config",
        sa.Column(
            "user_id",
            sa.String(255),
            nullable=True,
            comment="User ID (will become primary key)",
        ),
    )
    
    # Step 2: Migrate data: for each config, pick the first user from that organization
    connection.execute(
        text("""
            UPDATE organization_twilio_config otc
            SET user_id = (
                SELECT u.id
                FROM users u
                WHERE u.organization_id = otc.organization_id
                LIMIT 1
            )
            WHERE user_id IS NULL
        """)
    )
    
    # Step 3: Check if any configs couldn't be migrated (orgs with no users)
    result = connection.execute(
        text("""
            SELECT COUNT(*) 
            FROM organization_twilio_config 
            WHERE user_id IS NULL
        """)
    )
    orphaned_count = result.scalar()
    if orphaned_count > 0:
        raise ValueError(
            f"Cannot migrate {orphaned_count} config(s): organization has no users. "
            "Please assign users to organizations before migrating."
        )
    
    # Step 4: Make user_id NOT NULL
    op.alter_column("organization_twilio_config", "user_id", nullable=False)
    
    # Step 5: Add foreign key constraint
    op.create_foreign_key(
        "fk_twilio_config_user_id",
        "organization_twilio_config",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    
    # Step 6: Rename table
    op.rename_table("organization_twilio_config", "user_phone_numbers")
    
    # Step 7: Drop old primary key (id) and its column
    op.drop_constraint(
        "organization_twilio_config_pkey",
        "user_phone_numbers",
        type_="primary",
    )
    op.drop_column("user_phone_numbers", "id")
    
    # Step 8: Drop old organization_id column and its unique index
    op.drop_index(
        op.f("ix_organization_twilio_config_organization_id"),
        table_name="user_phone_numbers",
    )
    op.drop_column("user_phone_numbers", "organization_id")
    
    # Step 9: Make user_id the primary key
    op.create_primary_key(
        "user_phone_numbers_pkey",
        "user_phone_numbers",
        ["user_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    
    # Step 1: Drop primary key on user_id
    op.drop_constraint(
        "user_phone_numbers_pkey",
        "user_phone_numbers",
        type_="primary",
    )
    
    # Step 2: Add organization_id column back
    op.add_column(
        "user_phone_numbers",
        sa.Column(
            "organization_id",
            sa.String(255),
            nullable=True,
        ),
    )
    
    # Step 3: Migrate data back: get organization_id from user
    connection.execute(
        text("""
            UPDATE user_phone_numbers upn
            SET organization_id = (
                SELECT u.organization_id
                FROM users u
                WHERE u.id = upn.user_id
            )
            WHERE organization_id IS NULL
        """)
    )
    
    # Step 4: Make organization_id NOT NULL
    op.alter_column("user_phone_numbers", "organization_id", nullable=False)
    
    # Step 5: Add id column back as primary key
    op.add_column(
        "user_phone_numbers",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
    )
    
    # Step 6: Create sequence and set default for id
    connection.execute(
        text("""
            CREATE SEQUENCE IF NOT EXISTS user_phone_numbers_id_seq;
            ALTER TABLE user_phone_numbers 
            ALTER COLUMN id SET DEFAULT nextval('user_phone_numbers_id_seq');
            SELECT setval('user_phone_numbers_id_seq', COALESCE(MAX(id), 1)) 
            FROM user_phone_numbers;
        """)
    )
    
    # Step 7: Make id the primary key
    op.create_primary_key(
        "organization_twilio_config_pkey",
        "user_phone_numbers",
        ["id"],
    )
    
    # Step 8: Add unique constraint and index on organization_id
    op.create_index(
        op.f("ix_organization_twilio_config_organization_id"),
        "user_phone_numbers",
        ["organization_id"],
        unique=True,
    )
    
    # Step 9: Add index on user_id
    op.create_index(
        op.f("ix_organization_twilio_config_user_id"),
        "user_phone_numbers",
        ["user_id"],
    )
    
    # Step 10: Drop foreign key constraint
    op.drop_constraint(
        "fk_twilio_config_user_id",
        "user_phone_numbers",
        type_="foreignkey",
    )
    
    # Step 11: Drop user_id column
    op.drop_column("user_phone_numbers", "user_id")
    
    # Step 12: Rename table back
    op.rename_table("user_phone_numbers", "organization_twilio_config")

