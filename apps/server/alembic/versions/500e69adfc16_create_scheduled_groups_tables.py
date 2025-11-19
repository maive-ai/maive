"""create scheduled groups tables

Revision ID: 500e69adfc16
Revises: 82986719e63e
Create Date: 2025-11-12 17:46:13.556186

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "500e69adfc16"
down_revision: Union[str, Sequence[str], None] = "82986719e63e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create scheduled_groups table
    op.create_table(
        "scheduled_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "user_id", sa.String(length=255), nullable=False, comment="User ID (sub)"
        ),
        sa.Column(
            "name", sa.String(length=255), nullable=False, comment="Group display name"
        ),
        sa.Column(
            "frequency",
            sa.JSON(),
            nullable=False,
            comment="Days of week: ['monday', 'tuesday', etc.]",
        ),
        sa.Column(
            "time_of_day",
            sa.Time(),
            nullable=False,
            comment="Time of day to make calls",
        ),
        sa.Column(
            "goal_type",
            sa.String(length=50),
            nullable=False,
            comment="Goal type: status_check, locate_check, user_specified, ai_determined",
        ),
        sa.Column(
            "goal_description",
            sa.Text(),
            nullable=True,
            comment="User-specified goal description",
        ),
        sa.Column(
            "who_to_call",
            sa.String(length=50),
            nullable=False,
            comment="Who to call: adjuster, insurance_carrier, ai_determines",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether the group is currently active/running",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Record creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Record last update timestamp",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_scheduled_groups_user_active",
        "scheduled_groups",
        ["user_id", "is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_groups_user_id"),
        "scheduled_groups",
        ["user_id"],
        unique=False,
    )

    # Create scheduled_group_members table
    op.create_table(
        "scheduled_group_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "group_id",
            sa.Integer(),
            nullable=False,
            comment="Foreign key to scheduled_groups",
        ),
        sa.Column(
            "project_id",
            sa.String(length=255),
            nullable=False,
            comment="Project/Job ID from CRM",
        ),
        sa.Column(
            "goal_completed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether the goal has been completed for this project",
        ),
        sa.Column(
            "goal_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when goal was completed",
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the project was added to the group",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"], ["scheduled_groups.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "project_id", name="uq_group_project"),
    )
    op.create_index(
        "idx_group_completed",
        "scheduled_group_members",
        ["group_id", "goal_completed"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_group_members_group_id"),
        "scheduled_group_members",
        ["group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_group_members_project_id"),
        "scheduled_group_members",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_scheduled_group_members_project_id"),
        table_name="scheduled_group_members",
    )
    op.drop_index(
        op.f("ix_scheduled_group_members_group_id"),
        table_name="scheduled_group_members",
    )
    op.drop_index("idx_group_completed", table_name="scheduled_group_members")
    op.drop_table("scheduled_group_members")
    op.drop_index(op.f("ix_scheduled_groups_user_id"), table_name="scheduled_groups")
    op.drop_index("idx_scheduled_groups_user_active", table_name="scheduled_groups")
    op.drop_table("scheduled_groups")
