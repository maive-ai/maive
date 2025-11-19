"""create_users_table

Revision ID: e28f9d9b8c42
Revises: ecfad63f38d7
Create Date: 2025-11-16 13:29:33.742208

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e28f9d9b8c42"
down_revision: Union[str, Sequence[str], None] = "ecfad63f38d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        "users",
        sa.Column(
            "id", sa.String(length=255), nullable=False, comment="Cognito user ID (sub)"
        ),
        sa.Column(
            "email", sa.String(length=255), nullable=False, comment="User email address"
        ),
        sa.Column(
            "organization_id",
            sa.String(length=36),
            nullable=False,
            comment="Organization UUID",
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
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # Create indexes
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(
        op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_users_organization_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
