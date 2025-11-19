"""add_transcript_to_calls

Revision ID: d50a3b7efc68
Revises: ba8c60a76780
Create Date: 2025-10-27 20:20:51.977556

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d50a3b7efc68"
down_revision: Union[str, Sequence[str], None] = "ba8c60a76780"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "calls",
        sa.Column(
            "transcript",
            sa.JSON(),
            nullable=True,
            comment="Transcript messages from the call",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("calls", "transcript")
