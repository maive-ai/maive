"""
Database model for user phone number assignments.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base
from src.db.users.model import User


class UserPhoneNumber(Base):
    """Phone number assignment per user."""

    __tablename__ = "user_phone_numbers"

    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        comment="User ID (primary key)",
    )
    phone_number: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Twilio phone number (E.164 format)"
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationship to User model
    user: Mapped[User] = relationship("User", lazy="joined")
