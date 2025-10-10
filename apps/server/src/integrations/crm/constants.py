"""
CRM integration constants and enums.

This module contains all constants, enums, and static values used
across the CRM integration system.
"""

from enum import Enum


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


class Status(str, Enum):
    """Status values for Service Titan jobs and projects."""

    SCHEDULED = "Scheduled"
    DISPATCHED = "Dispatched"
    IN_PROGRESS = "In Progress"
    HOLD = "Hold"
    COMPLETED = "Completed"
    CANCELED = "Canceled"


class SubStatus(int, Enum):
    """SubStatus IDs for Service Titan projects."""

    # Status ID 379 - Sold substatuses
    ADMIN_READY_FOR_PRODUCTION = 19567820
    ADMIN_PENDING_SCHEDULING = 19567821
    ADMIN_READY_FOR_ORDER_BUILDING = 19567822
    ADMIN_PRODUCTION_HOLD = 95116604
    ADMIN_PENDING_MATERIALS = 106033909
    ADMIN_PENDING_PERMIT = 106033910
    ADMIN_HOA_HOLD = 139645442
    ADMIN_SALES_HOLD = 200206332

    # Status ID 380 - In Production substatuses
    ADMIN_PENDING_MATERIALS_RECEIPT = 19567823
    IM_WAITING_FOR_INSTALL = 19567824

    # Status ID 381 - Work Started substatuses
    IM_WORK_STARTED = 19567825
    IM_WAITING_FOR_OTHER_TRADES = 106033911

    # Status ID 382 - Ready for Final substatuses
    ADMIN_READY_FOR_ADMIN = 19567827
    OPS_PENDING_READY_TO_COLLECT = 19567828
    FINANCE_READY_TO_INVOICE = 19567829
    IM_WAITING_TO_RESOLVE_ISSUES = 19567830
    SA_INVOICE_PAID_READY_FOR_COMMISSION = 19567831
    GM_REVIEW = 139645443
    JOB_CLOSED = 139645444

    # Status ID 383 - Ready for Invoicing substatuses
    PENDING_APPROVAL = 19567832
    FINANCE_WORKING = 19567833
    FINANCE_READY_FOR_REVIEW = 19567834
    ADMIN_PENDING_INSURANCE = 19567835
    SALES_SALES_HOLD = 97988111

    # Status ID 384 - Cancelled substatuses
    FINANCE_DECLINE = 19567837
    CUSTOMER_CANCELLATION = 19567838
    REFUND_REQUIRED = 139645445
    DUPLICATE = 200206333


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

    # Project endpoints
    PROJECT_SUBSTATUSES = "/jpm/v2/tenant/{tenant_id}/project-substatuses"
    PROJECT_UPDATE = "/jpm/v2/tenant/{tenant_id}/projects/{id}"
    PROJECT_NOTES = "/jpm/v2/tenant/{tenant_id}/projects/{id}/notes"

    # Estimates endpoints
    ESTIMATES = "/sales/v2/tenant/{tenant_id}/estimates"
    ESTIMATE_BY_ID = "/sales/v2/tenant/{tenant_id}/estimates/{id}"
    ESTIMATE_ITEMS = "/sales/v2/tenant/{tenant_id}/estimates/items"

    # Form submissions endpoints
    FORM_SUBMISSIONS = "/forms/v2/tenant/{tenant_id}/submissions"
    FORM_SUBMISSIONS_BY_FORM_ID = (
        "/forms/v2/tenant/{tenant_id}/forms/{form_id}/submissions"
    )
