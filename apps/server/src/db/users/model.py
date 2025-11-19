"""
SQLAlchemy model for users.

Stores user-organization mapping. User authentication is handled by Cognito,
but organization assignment is stored here.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class User(Base):
    """
    User model for storing organization associations.

    Cognito manages authentication, but we store organization membership here
    since Cognito custom attributes can't be added to existing user pools.
    """

    __tablename__ = "users"

    # Primary key - Cognito user ID (sub claim from JWT)
    id: Mapped[str] = mapped_column(
        String(255), primary_key=True, comment="Cognito user ID (sub)"
    )

    # Email address (for reference and org creation)
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="User email address",
    )

    # Foreign key to organization
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Organization UUID",
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
        return f"<User(id={self.id}, email={self.email}, organization_id={self.organization_id})>"
