"""
SQLAlchemy model for organization CRM credentials.

Stores references to AWS Secrets Manager secrets for each organization's CRM integration.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class OrganizationCRMCredentials(Base):
    """
    Organization CRM credentials reference model.

    Stores metadata and AWS Secrets Manager references for CRM credentials.
    Actual credentials are stored in AWS Secrets Manager, not in the database.
    """

    __tablename__ = "organization_crm_credentials"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="Credential record UUID",
    )

    # Foreign key to organization
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Organization UUID",
    )

    # CRM provider type
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="CRM provider name (job_nimbus, service_titan)",
    )

    # AWS Secrets Manager reference
    secret_arn: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="AWS Secrets Manager ARN for credentials",
    )

    # Active status (only one active credential set per org)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this credential set is active",
    )

    # User who created the credentials
    created_by: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="User ID who configured credentials"
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
        # Index for common lookup pattern
        Index("idx_org_crm_active", "organization_id", "is_active"),
        # Partial unique index: only one active credential set per organization
        Index(
            "uq_org_active_credentials",
            "organization_id",
            unique=True,
            postgresql_where="is_active = true",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<OrganizationCRMCredentials(id={self.id}, "
            f"organization_id={self.organization_id}, provider={self.provider}, "
            f"is_active={self.is_active})>"
        )
