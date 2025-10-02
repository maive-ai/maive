"""
CRM integration constants and enums.

This module contains all constants, enums, and static values used
across the CRM integration system.
"""

from enum import Enum


class ProjectStatus(str, Enum):
    """Project status values across CRM systems."""

    HOLD = "hold"
    DISPATCHED = "dispatched"
    DONE = "done"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"
    WORKING = "working"

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
            "dispatched": cls.DISPATCHED,
            "working": cls.WORKING,
            "hold": cls.HOLD,
            "done": cls.DONE,
            "canceled": cls.CANCELLED,
        }
        return service_titan_mapping.get(status.lower(), cls.DISPATCHED)


class CRMProvider(str, Enum):
    """Available CRM providers."""

    SERVICE_TITAN = "service_titan"


class OwnerType(str, Enum):
    """Owner types for CRM entities."""

    JOB = "Job"
    CALL = "Call"
    CUSTOMER = "Customer"
    LOCATION = "Location"
    EQUIPMENT = "Equipment"
    TECHNICIAN = "Technician"
    JOB_APPOINTMENT = "JobAppointment"
    MEMBERSHIP = "Membership"
    TRUCK = "Truck"


class FormStatus(str, Enum):
    """Form submission status values."""

    STARTED = "Started"
    COMPLETED = "Completed"
    ANY = "Any"


class EstimateReviewStatus(str, Enum):
    """Estimate review status values."""

    NONE = "None"
    NEEDS_APPROVAL = "NeedsApproval"
    APPROVED = "Approved"
    NOT_APPROVED = "NotApproved"


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

    # Estimates endpoints
    ESTIMATES = "/sales/v2/tenant/{tenant_id}/estimates"
    ESTIMATE_BY_ID = "/sales/v2/tenant/{tenant_id}/estimates/{id}"
    ESTIMATE_ITEMS = "/sales/v2/tenant/{tenant_id}/estimates/items"

    # Form submissions endpoints
    FORM_SUBMISSIONS = "/forms/v2/tenant/{tenant_id}/submissions"
    FORM_SUBMISSIONS_BY_FORM_ID = "/forms/v2/tenant/{tenant_id}/forms/{form_id}/submissions"
