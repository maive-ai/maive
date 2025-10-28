"""
SQLAlchemy model for call list items.

Stores user-specific call lists with project IDs and call completion status.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class CallListItem(Base):
    """
    Call list item model for tracking projects in a user's call queue.

    Each user can have multiple projects in their call list.
    Project details are fetched dynamically from CRM via React Query caching.
    """

    __tablename__ = "call_list_items"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User and project association
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="User ID (sub)"
    )
    project_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Project/Job ID from CRM"
    )

    # Call completion status
    call_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the call for this project has been completed",
    )

    # Ordering
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Position in the call list for ordering",
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

    # Constraints and indexes
    __table_args__ = (
        # Prevent duplicate projects in a user's call list
        UniqueConstraint("user_id", "project_id", name="uq_user_project"),
        # Find all items for a user, ordered by position
        Index("idx_user_position", "user_id", "position"),
    )

    def __repr__(self) -> str:
        return (
            f"<CallListItem(id={self.id}, user_id={self.user_id}, "
            f"project_id={self.project_id}, call_completed={self.call_completed}, "
            f"position={self.position})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model to dictionary representation.

        Returns:
            dict: Dictionary with all call list item data
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "call_completed": self.call_completed,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
