"""add_organization_twilio_config_table

Revision ID: f8a9c5b4d3e2
Revises: d7e7b31d766f
Create Date: 2025-11-18 20:57:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a9c5b4d3e2"
down_revision: Union[str, Sequence[str], None] = "d7e7b31d766f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create organization_twilio_config table
    op.create_table(
        "organization_twilio_config",
        sa.Column("id", sa.Integer(), nullable=False, comment="Primary key"),
        sa.Column(
            "organization_id",
            sa.String(length=255),
            nullable=False,
            comment="Organization identifier",
        ),
        sa.Column(
            "phone_number",
            sa.String(length=20),
            nullable=False,
            comment="Twilio phone number (E.164 format)",
        ),
        sa.Column(
            "created_by",
            sa.String(length=255),
            nullable=False,
            comment="User ID who configured phone number",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Record creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Record last update timestamp",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        op.f("ix_organization_twilio_config_organization_id"),
        "organization_twilio_config",
        ["organization_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_organization_twilio_config_organization_id"),
        table_name="organization_twilio_config",
    )
    op.drop_table("organization_twilio_config")
