"""merge migration heads

Revision ID: 82986719e63e
Revises: d1589b6ca2c7, d50a3b7efc68
Create Date: 2025-11-07 18:29:44.905119

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "82986719e63e"
down_revision: Union[str, Sequence[str], None] = ("d1589b6ca2c7", "d50a3b7efc68")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
