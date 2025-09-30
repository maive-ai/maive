"""
CRM integration constants and enums.

This module contains all constants, enums, and static values used
across the CRM integration system.
"""

from enum import Enum


class ProjectStatus(str, Enum):
    """Project status values across CRM systems."""

    ON_HOLD = "on_hold"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"

    @classmethod
    def from_service_titan(cls, status: str) -> "ProjectStatus":
        """
        Convert Service Titan status to ProjectStatus enum.

        Args:
            status: Service Titan status string

        Returns:
            ProjectStatus: Mapped status enum value
        """
        service_titan_mapping = {
            "scheduled": cls.SCHEDULED,
            "dispatched": cls.ACTIVE,
            "working": cls.IN_PROGRESS,
            "hold": cls.ON_HOLD,
            "done": cls.COMPLETED,
            "canceled": cls.CANCELLED,
        }
        if status is None:
            return cls.ACTIVE
        return service_titan_mapping.get(status.lower(), cls.ACTIVE)


class CRMProvider(str, Enum):
    """Available CRM providers."""

    SERVICE_TITAN = "service_titan"


class ServiceTitanEndpoints:
    """Service Titan API endpoints."""

    # Projects endpoints
    PROJECTS = "/jpm/v2/tenant/{tenant_id}/projects"
    PROJECT_BY_ID = "/jpm/v2/tenant/{tenant_id}/projects/{id}"

    # Appointments endpoints
    APPOINTMENTS = "/jpm/v2/tenant/{tenant_id}/export/appointments"
    APPOINTMENT_BY_ID = "/jpm/v2/tenant/{tenant_id}/appointments/{id}"

    # Jobs endpoints
    JOBS = "/jpm/v2/tenant/{tenant_id}/jobs"
    JOB_BY_ID = "/jpm/v2/tenant/{tenant_id}/jobs/{id}"
