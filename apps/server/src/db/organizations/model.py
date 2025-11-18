"""
SQLAlchemy model for organizations.

Organizations represent tenant boundaries for multi-tenant CRM credential management.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class Organization(Base):
    """
    Organization model for multi-tenant support.

    Each organization represents a separate tenant with their own CRM credentials.
    Users belong to exactly one organization.
    """

    __tablename__ = "organizations"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="Organization UUID",
    )

    # Display name (customizable by users, unique to prevent duplicate orgs)
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, comment="Organization display name"
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

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name})>"
