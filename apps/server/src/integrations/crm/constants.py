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
    MOCK_CRM = "mock_crm"


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


class JobStatus(str, Enum):
    """Job status values for Service Titan jobs."""

    SCHEDULED = "Scheduled"
    DISPATCHED = "Dispatched"
    IN_PROGRESS = "InProgress"
    HOLD = "Hold"
    COMPLETED = "Completed"
    CANCELED = "Canceled"


class JobHoldReasonId(int, Enum):
    """Job hold reason IDs for Service Titan."""

    WAITING_FOR_MATERIALS = 1265
    WAITING_FOR_PERMIT = 1266
    RAIN_NEEDS_RESCHEDULE = 1267
    CUSTOMER_REQUESTED_RESCHEDULE = 5051140
    REPAIR_NEED_DIFFERENT_MATERIALS = 5051141
    DID_NOT_FINISH_NEED_ANOTHER_APPOINTMENT = 5051142
    SECOND_LOOK_NEEDED = 9862708
    SUPPLY_RUN = 9862709


# Mapping of hold reason IDs to their names
JOB_HOLD_REASON_NAMES = {
    JobHoldReasonId.WAITING_FOR_MATERIALS: "Waiting for materials",
    JobHoldReasonId.WAITING_FOR_PERMIT: "Waiting for permit",
    JobHoldReasonId.RAIN_NEEDS_RESCHEDULE: "Rain - Needs Reschedule",
    JobHoldReasonId.CUSTOMER_REQUESTED_RESCHEDULE: "Customer requested to reschedule, awaiting new date",
    JobHoldReasonId.REPAIR_NEED_DIFFERENT_MATERIALS: "Repair - need different materials",
    JobHoldReasonId.DID_NOT_FINISH_NEED_ANOTHER_APPOINTMENT: "Did not finish work > Need another appointment",
    JobHoldReasonId.SECOND_LOOK_NEEDED: "2nd Look Needed",
    JobHoldReasonId.SUPPLY_RUN: "Supply Run",
}


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
    JOB_NOTES = "/jpm/v2/tenant/{tenant_id}/jobs/{id}/notes"
    JOB_HOLD = "/jpm/v2/tenant/{tenant_id}/jobs/{id}/hold"
    JOB_HOLD_REASONS = "/jpm/v2/tenant/{tenant_id}/job-hold-reasons"
    JOB_REMOVE_CANCELLATION = "/jpm/v2/tenant/{tenant_id}/jobs/{id}/remove-cancellation"

    # Estimates endpoints
    ESTIMATES = "/sales/v2/tenant/{tenant_id}/estimates"
    ESTIMATE_BY_ID = "/sales/v2/tenant/{tenant_id}/estimates/{id}"
    ESTIMATE_ITEMS = "/sales/v2/tenant/{tenant_id}/estimates/items"

    # Form submissions endpoints
    FORM_SUBMISSIONS = "/forms/v2/tenant/{tenant_id}/submissions"
    FORM_SUBMISSIONS_BY_FORM_ID = "/forms/v2/tenant/{tenant_id}/forms/{form_id}/submissions"
