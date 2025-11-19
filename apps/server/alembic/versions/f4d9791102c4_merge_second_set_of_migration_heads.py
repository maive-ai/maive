"""merge second set of migration heads

Revision ID: f4d9791102c4
Revises: 500e69adfc16, d7e7b31d766f
Create Date: 2025-11-19 11:50:33.525854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4d9791102c4'
down_revision: Union[str, Sequence[str], None] = ('500e69adfc16', 'd7e7b31d766f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
