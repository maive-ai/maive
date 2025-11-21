"""merge_twilio_config_migration

Revision ID: b6c0b448deb6
Revises: 500e69adfc16, f8a9c5b4d3e2
Create Date: 2025-11-18 22:05:17.403384

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6c0b448deb6"
down_revision: Union[str, Sequence[str], None] = ("500e69adfc16", "f8a9c5b4d3e2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
