"""
SQLAlchemy models for scheduled groups.

Stores user-specific scheduled groups with automated calling schedules.
"""

from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Time as SQLTime,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


class ScheduledGroup(Base):
    """
    Scheduled group model for tracking groups of projects with automated calling schedules.

    Each user can create multiple groups with different schedules and goals.
    """

    __tablename__ = "scheduled_groups"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User association
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="User ID (sub)"
    )

    # Group details
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Group display name"
    )

    # Schedule configuration
    frequency: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, comment="Days of week: ['monday', 'tuesday', etc.]"
    )
    time_of_day: Mapped[time] = mapped_column(
        SQLTime, nullable=False, comment="Time of day to make calls"
    )

    # Goal configuration
    goal_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Goal type: status_check, locate_check, user_specified, ai_determined",
    )
    goal_description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="User-specified goal description"
    )
    who_to_call: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Who to call: adjuster, insurance_carrier, ai_determines",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the group is currently active/running",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="Record last update timestamp",
    )

    # Relationships
    members: Mapped[list["ScheduledGroupMember"]] = relationship(
        "ScheduledGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
    )

    # Constraints and indexes
    __table_args__ = (
        # Find all groups for a user
        Index("idx_scheduled_groups_user_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<ScheduledGroup(id={self.id}, user_id={self.user_id}, "
            f"name={self.name}, is_active={self.is_active})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model to dictionary representation.

        Returns:
            dict: Dictionary with all scheduled group data
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "frequency": self.frequency,
            "time_of_day": self.time_of_day.isoformat() if self.time_of_day else None,
            "goal_type": self.goal_type,
            "goal_description": self.goal_description,
            "who_to_call": self.who_to_call,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ScheduledGroupMember(Base):
    """
    Scheduled group member model for tracking projects in a scheduled group.

    Links projects to groups and tracks goal completion status.
    """

    __tablename__ = "scheduled_group_members"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Group association
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("scheduled_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to scheduled_groups",
    )

    # Project association
    project_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Project/Job ID from CRM",
    )

    # Goal tracking
    goal_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the goal has been completed for this project",
    )
    goal_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when goal was completed",
    )

    # Timestamps
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="When the project was added to the group",
    )

    # Relationships
    group: Mapped["ScheduledGroup"] = relationship(
        "ScheduledGroup", back_populates="members"
    )

    # Constraints and indexes
    __table_args__ = (
        # Prevent duplicate projects in a group
        UniqueConstraint("group_id", "project_id", name="uq_group_project"),
        # Find all members for a group
        Index("idx_group_completed", "group_id", "goal_completed"),
    )

    def __repr__(self) -> str:
        return (
            f"<ScheduledGroupMember(id={self.id}, group_id={self.group_id}, "
            f"project_id={self.project_id}, goal_completed={self.goal_completed})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model to dictionary representation.

        Returns:
            dict: Dictionary with all member data
        """
        return {
            "id": self.id,
            "group_id": self.group_id,
            "project_id": self.project_id,
            "goal_completed": self.goal_completed,
            "goal_completed_at": (
                self.goal_completed_at.isoformat() if self.goal_completed_at else None
            ),
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }

