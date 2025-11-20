"""
SQLAlchemy model for call records.

Stores both active calls and call history in a single table.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.ai.voice_ai.constants import CallStatus, VoiceAIProvider
from src.db.database import Base


class Call(Base):
    """
    Call record model for tracking voice AI calls.

    This table stores both active calls and historical call data.
    Active calls can be identified by is_active=True or ended_at=NULL.
    """

    __tablename__ = "calls"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User and project association
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Cognito user ID (sub)"
    )
    project_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Project/Job ID"
    )

    # Call identification
    call_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True, comment="Provider call ID"
    )

    # Call metadata
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Voice AI provider (vapi, etc.)"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="Current call status"
    )
    phone_number: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Phone number called"
    )

    # Active call state
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this is currently an active call",
    )
    listen_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="WebSocket URL for listening to call"
    )
    recording_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="URL to the call recording"
    )

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Call start timestamp",
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Call end timestamp"
    )
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

    # Provider-specific data (flexible JSON storage)
    provider_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Raw provider response data"
    )

    # Analysis results (flexible JSON storage for structured data)
    analysis_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Structured analysis data from call (claims, payments, etc.)",
    )

    # Transcript messages (flexible JSON storage for conversation)
    transcript: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Transcript messages from the call",
    )

    # Composite indexes for common queries
    __table_args__ = (
        # Find active call for a user
        Index("idx_user_active", "user_id", "is_active"),
        # Find calls by project
        Index("idx_project_started", "project_id", "started_at"),
        # Find calls by user and date range
        Index("idx_user_started", "user_id", "started_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Call(id={self.id}, call_id={self.call_id}, "
            f"user_id={self.user_id}, status={self.status}, "
            f"is_active={self.is_active})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model to dictionary representation.

        Returns:
            dict: Dictionary with all call data
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "call_id": self.call_id,
            "provider": self.provider,
            "status": self.status,
            "phone_number": self.phone_number,
            "is_active": self.is_active,
            "listen_url": self.listen_url,
            "recording_url": self.recording_url,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "provider_data": self.provider_data,
            "analysis_data": self.analysis_data,
            "transcript": self.transcript,
        }

    @staticmethod
    def from_active_call_state(
        user_id: str,
        call_id: str,
        project_id: str,
        status: CallStatus,
        provider: VoiceAIProvider,
        phone_number: str,
        started_at: datetime,
        listen_url: str | None = None,
        provider_data: dict[str, Any] | None = None,
    ) -> "Call":
        """
        Create a Call instance from active call state parameters.

        Args:
            user_id: Cognito user ID
            call_id: Provider call ID
            project_id: Project/Job ID
            status: Call status
            provider: Voice AI provider
            phone_number: Phone number called
            started_at: Call start timestamp
            listen_url: WebSocket URL for listening
            provider_data: Raw provider data

        Returns:
            Call: New Call instance
        """
        return Call(
            user_id=user_id,
            call_id=call_id,
            project_id=project_id,
            status=status.value,
            provider=provider.value,
            phone_number=phone_number,
            started_at=started_at,
            listen_url=listen_url,
            provider_data=provider_data,
            is_active=True,
        )
