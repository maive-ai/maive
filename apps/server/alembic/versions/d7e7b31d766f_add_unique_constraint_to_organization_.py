"""add_unique_constraint_to_organization_name

Revision ID: d7e7b31d766f
Revises: e28f9d9b8c42
Create Date: 2025-11-17 09:52:25.752094

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7e7b31d766f"
down_revision: Union[str, Sequence[str], None] = "e28f9d9b8c42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add unique constraint on organization name
    op.create_unique_constraint("uq_organizations_name", "organizations", ["name"])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove unique constraint on organization name
    op.drop_constraint("uq_organizations_name", "organizations", type_="unique")
