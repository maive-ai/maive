"""
CRM-specific Pydantic schemas for request and response models.

This module contains all Pydantic models related to CRM operations,
project management, and status tracking across different CRM providers.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.integrations.crm.constants import CRMProvider, EstimateReviewStatus, Status


class ProjectStatusResponse(BaseModel):
    """Response model for project status information."""

    project_id: str = Field(..., description="Unique project identifier")
    status: Status = Field(..., description="Current project status")
    provider: CRMProvider = Field(..., description="CRM provider")
    updated_at: datetime | None = Field(None, description="Last status update timestamp")
    provider_data: dict[str, Any] | None = Field(None, description="Provider-specific data")


class ProjectStatusListResponse(BaseModel):
    """Response model for multiple project statuses."""

    projects: list[ProjectStatusResponse] = Field(..., description="List of project statuses")
    total_count: int = Field(..., description="Total number of projects")
    provider: CRMProvider = Field(..., description="CRM provider")


class JobRequest(BaseModel):
    """Request model for getting a specific job."""

    job_id: int = Field(..., description="ID of the job to retrieve")
    tenant: int = Field(..., description="Tenant ID")


class EstimateByIdRequest(BaseModel):
    """Request model for getting a specific estimate by ID."""

    tenant: int = Field(..., description="Tenant ID")
    estimate_id: int = Field(..., description="ID of the estimate to retrieve")


class EstimatesRequest(BaseModel):
    """Request model for getting estimates with filters."""

    tenant: int = Field(..., description="Tenant ID")
    job_id: int | None = Field(None, description="Job ID to filter estimates", alias="jobId")
    page: int | None = Field(None, description="Page number for pagination")
    page_size: int | None = Field(None, description="Page size for pagination (max 50)", le=50, alias="pageSize")
    ids: str | None = Field(None, description="Comma separated string of estimate IDs")


class EstimateStatus(BaseModel):
    """Estimate status model with value and name."""

    value: int = Field(..., description="Status value")
    name: str = Field(..., description="Status name")


class JobResponse(BaseModel):
    """Response model for Service Titan job information."""

    id: int = Field(..., description="ID of the job")
    job_number: str = Field(..., description="Job number", alias="jobNumber")
    project_id: int | None = Field(None, description="ID of the job's project", alias="projectId")
    customer_id: int = Field(..., description="ID of the job's customer", alias="customerId")
    location_id: int = Field(..., description="ID of the job's location", alias="locationId")
    job_status: str = Field(..., description="Status of the job", alias="jobStatus")
    completed_on: datetime | None = Field(None, description="Date/time (in UTC) when the job was completed", alias="completedOn")
    business_unit_id: int = Field(..., description="ID of the job's business unit", alias="businessUnitId")
    job_type_id: int = Field(..., description="ID of job type", alias="jobTypeId")
    priority: str = Field(..., description="Priority of the job")
    campaign_id: int = Field(..., description="ID of the job's campaign", alias="campaignId")
    appointment_count: int = Field(..., description="Number of appointments on the job", alias="appointmentCount")
    first_appointment_id: int = Field(..., description="ID of the first appointment on the job", alias="firstAppointmentId")
    last_appointment_id: int = Field(..., description="ID of the last appointment on the job", alias="lastAppointmentId")
    recall_for_id: int | None = Field(None, description="ID of the job for which this job is a recall", alias="recallForId")
    warranty_id: int | None = Field(None, description="ID of the job for which this job is a warranty", alias="warrantyId")
    no_charge: bool = Field(..., description="Whether the job is a no-charge job", alias="noCharge")
    notifications_enabled: bool = Field(..., description="Whether notifications will be sent to customers", alias="notificationsEnabled")
    created_on: datetime = Field(..., description="Date/time (in UTC) when the job was created", alias="createdOn")
    created_by_id: int = Field(..., description="ID of the user who created the job", alias="createdById")
    modified_on: datetime = Field(..., description="Date/time (in UTC) when job was last modified", alias="modifiedOn")
    tag_type_ids: list[int] = Field(..., description="Tags on the job", alias="tagTypeIds")
    customer_po: str | None = Field(None, description="Customer PO", alias="customerPo")
    invoice_id: int | None = Field(None, description="ID of the invoice associated with this job", alias="invoiceId")
    total: float | None = Field(None, description="Total amount of the job")
    summary: str | None = Field(None, description="Job summary")


class EstimateResponse(BaseModel):
    """Response model for Service Titan estimate information."""

    id: int = Field(..., description="ID of the estimate")
    job_id: int | None = Field(None, description="ID of the associated job", alias="jobId")
    project_id: int | None = Field(None, description="ID of the associated project", alias="projectId")
    location_id: int | None = Field(None, description="ID of the location", alias="locationId")
    customer_id: int | None = Field(None, description="ID of the customer", alias="customerId")
    name: str | None = Field(None, description="Name of the estimate")
    job_number: str | None = Field(None, description="Job number", alias="jobNumber")
    status: EstimateStatus | None = Field(None, description="Status of the estimate")
    review_status: EstimateReviewStatus = Field(..., description="Review status of the estimate", alias="reviewStatus")
    summary: str | None = Field(None, description="Summary of the estimate")
    created_on: datetime = Field(..., description="Date/time (in UTC) when the estimate was created", alias="createdOn")
    modified_on: datetime = Field(..., description="Date/time (in UTC) when estimate was last modified", alias="modifiedOn")
    sold_on: datetime | None = Field(None, description="Date/time (in UTC) when the estimate was sold", alias="soldOn")
    sold_by: int | None = Field(None, description="ID of who sold the estimate", alias="soldBy")
    active: bool = Field(..., description="Whether the estimate is active")
    subtotal: float = Field(..., description="Subtotal amount")
    tax: float = Field(..., description="Tax amount")
    business_unit_id: int | None = Field(None, description="ID of the business unit", alias="businessUnitId")
    business_unit_name: str | None = Field(None, description="Name of the business unit", alias="businessUnitName")
    is_recommended: bool = Field(..., description="Whether this estimate is recommended", alias="isRecommended")
    budget_code_id: int | None = Field(None, description="ID of the budget code", alias="budgetCodeId")
    is_change_order: bool = Field(..., description="Whether this estimate is a change order", alias="isChangeOrder")


class SkuModel(BaseModel):
    """SKU model for estimate items."""

    id: int = Field(..., description="SKU ID")
    name: str = Field(..., description="SKU name")
    display_name: str = Field(..., description="Display name", alias="displayName")
    type: str = Field(..., description="SKU type")
    sold_hours: float = Field(..., description="Sold hours", alias="soldHours")
    general_ledger_account_id: int = Field(..., description="General ledger account ID", alias="generalLedgerAccountId")
    general_ledger_account_name: str = Field(..., description="General ledger account name", alias="generalLedgerAccountName")
    modified_on: datetime = Field(..., description="Date/time (in UTC) when SKU was last modified", alias="modifiedOn")


class EstimateItemResponse(BaseModel):
    """Response model for estimate item information."""

    id: int = Field(..., description="ID of the estimate item")
    sku: SkuModel = Field(..., description="SKU details")
    sku_account: str = Field(..., description="SKU account", alias="skuAccount")
    description: str = Field(..., description="Item description")
    membership_type_id: int | None = Field(None, description="Membership type ID", alias="membershipTypeId")
    qty: float = Field(..., description="Quantity")
    unit_rate: float = Field(..., description="Unit rate", alias="unitRate")
    total: float = Field(..., description="Total amount")
    unit_cost: float = Field(..., description="Unit cost", alias="unitCost")
    total_cost: float = Field(..., description="Total cost", alias="totalCost")
    item_group_name: str | None = Field(None, description="Item group name", alias="itemGroupName")
    item_group_root_id: int | None = Field(None, description="Item group root ID", alias="itemGroupRootId")
    created_on: datetime = Field(..., description="Date/time (in UTC) when the item was created", alias="createdOn")
    modified_on: datetime = Field(..., description="Date/time (in UTC) when the item was last modified", alias="modifiedOn")
    chargeable: bool | None = Field(None, description="Whether the item is chargeable")
    invoice_item_id: int | None = Field(None, description="The invoice item which was created from this estimate item", alias="invoiceItemId")
    budget_code_id: int | None = Field(None, description="Budget code ID", alias="budgetCodeId")


class EstimatesListResponse(BaseModel):
    """Response model for estimates list."""

    estimates: list[EstimateResponse] = Field(..., description="List of estimates")
    total_count: int | None = Field(None, description="Total count of estimates (if requested)")
    page: int | None = Field(None, description="Current page number")
    page_size: int | None = Field(None, description="Page size")
    has_more: bool | None = Field(None, description="Whether there are more estimates")


class EstimateItemsRequest(BaseModel):
    """Request model for getting estimate items."""

    tenant: int = Field(..., description="Tenant ID")
    estimate_id: int | None = Field(None, description="Estimate ID to filter items", alias="estimateId")
    ids: str | None = Field(None, description="Comma separated string of item IDs (max 50)")
    active: str | None = Field(None, description="Filter by active status (True, False, Any)")
    page: int | None = Field(None, description="Page number for pagination")
    page_size: int | None = Field(None, description="Page size for pagination (default 50)", le=50, alias="pageSize")


class EstimateItemsResponse(BaseModel):
    """Response model for estimate items list."""

    items: list[EstimateItemResponse] = Field(..., description="List of estimate items")
    total_count: int | None = Field(None, description="Total count of items (if requested)")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    has_more: bool = Field(..., description="Whether there are more items")


class CRMErrorResponse(BaseModel):
    """Error response from CRM operations."""

    success: bool = Field(default=False, description="Operation success status")
    error: str = Field(..., description="Error message")
    error_code: str | None = Field(None, description="Provider-specific error code")
    provider: CRMProvider | None = Field(None, description="CRM provider")


class AddJobNoteRequest(BaseModel):
    """Request model for adding a note to a job."""

    tenant: int = Field(..., description="Tenant ID")
    job_id: int = Field(..., description="ID of the job to add note to", alias="jobId")
    text: str = Field(..., description="Text content of the note")
    pin_to_top: bool | None = Field(None, description="Whether to pin the note to the top", alias="pinToTop")


class JobNoteResponse(BaseModel):
    """Response model for job note."""

    text: str = Field(..., description="Text content of the note")
    is_pinned: bool = Field(..., description="Whether the note is pinned to the top", alias="isPinned")
    created_by_id: int = Field(..., description="ID of user who created this note", alias="createdById")
    created_on: datetime = Field(..., description="Date/time (in UTC) the note was created", alias="createdOn")
    modified_on: datetime = Field(..., description="Date/time (in UTC) the note was modified", alias="modifiedOn")


class JobHoldReasonResponse(BaseModel):
    """Response model for job hold reason."""

    id: int = Field(..., description="Job Hold Reason ID")
    name: str = Field(..., description="Job Hold Reason Name")
    active: bool = Field(..., description="Job Hold Reason Active Status")
    created_on: datetime = Field(..., description="Date/time (in UTC) when the reason was created", alias="createdOn")
    modified_on: datetime = Field(..., description="Date/time (in UTC) when reason was last modified", alias="modifiedOn")


class JobHoldReasonsListResponse(BaseModel):
    """Response model for paginated list of job hold reasons."""

    page: int = Field(..., description="From which page this output has started")
    page_size: int = Field(..., description="Page size for this query", alias="pageSize")
    has_more: bool = Field(..., description="True if there are more records", alias="hasMore")
    total_count: int | None = Field(None, description="Total count of records for this query", alias="totalCount")
    data: list[JobHoldReasonResponse] = Field(..., description="The collection of result items")


class HoldJobRequest(BaseModel):
    """Request model for putting a job on hold."""

    tenant: int = Field(..., description="Tenant ID")
    job_id: int = Field(..., description="ID of the job to put on hold", alias="jobId")
    reason_id: int = Field(..., description="ID of job hold reason", alias="reasonId")
    memo: str = Field(..., description="Memo of job hold reason")


class ProjectSubStatusResponse(BaseModel):
    """Response model for project sub status."""

    id: int = Field(..., description="ID of the project sub status")
    name: str = Field(..., description="Name of the project sub status")
    status_id: int = Field(..., description="Id of the parent status", alias="statusId")
    order: int = Field(..., description="Order of the project status")
    modified_on: datetime = Field(..., description="Date/time (in UTC) when project sub status was last modified", alias="modifiedOn")
    active: bool = Field(..., description="When true, project sub status is active")


class ProjectSubStatusListResponse(BaseModel):
    """Response model for paginated list of project sub statuses."""

    page: int = Field(..., description="From which page this output has started")
    page_size: int = Field(..., description="Page size for this query", alias="pageSize")
    has_more: bool = Field(..., description="True if there are more records", alias="hasMore")
    total_count: int | None = Field(None, description="Total count of records for this query", alias="totalCount")
    data: list[ProjectSubStatusResponse] = Field(..., description="The collection of result items")


class ExternalDataItem(BaseModel):
    """External data key-value pair."""

    key: str = Field(..., description="External data key")
    value: str | None = Field(None, description="External data value")


class UpdateProjectRequest(BaseModel):
    """Request model for updating a project."""

    model_config = {"populate_by_name": True}

    tenant: int = Field(..., description="Tenant ID")
    project_id: int = Field(..., description="ID of the project to update", alias="projectId")
    status_id: int | None = Field(None, description="Project status ID", alias="statusId")
    sub_status_id: int | None = Field(None, description="Project sub status ID", alias="subStatusId")
    name: str | None = Field(None, description="Project name")
    summary: str | None = Field(None, description="Project summary (HTML)")
    external_data: list[ExternalDataItem] | None = Field(None, description="External data to attach to project", alias="externalData")