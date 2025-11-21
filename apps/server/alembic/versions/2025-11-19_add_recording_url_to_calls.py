"""add_recording_url_to_calls

Revision ID: a1b2c3d4e5f6
Revises: b6c0b448deb6
Create Date: 2025-11-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = ("b6c0b448deb6", "f4d9791102c4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add recording_url column
    op.add_column(
        "calls",
        sa.Column(
            "recording_url",
            sa.Text(),
            nullable=True,
            comment="URL to the call recording",
        ),
    )

    # Migrate existing data from provider_data["recording_url"] to the new column
    # This handles cases where recording URLs were stored in provider_data
    connection = op.get_bind()
    connection.execute(
        text("""
            UPDATE calls
            SET recording_url = (provider_data::jsonb->>'recording_url')
            WHERE provider_data IS NOT NULL
            AND provider_data::jsonb->>'recording_url' IS NOT NULL
            AND recording_url IS NULL
        """)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Migrate data back to provider_data before dropping column
    # This preserves data if someone needs to rollback
    connection = op.get_bind()
    connection.execute(
        text("""
            UPDATE calls
            SET provider_data = jsonb_set(
                COALESCE(provider_data::jsonb, '{}'::jsonb),
                '{recording_url}',
                to_jsonb(recording_url)
            )
            WHERE recording_url IS NOT NULL
        """)
    )

    op.drop_column("calls", "recording_url")
