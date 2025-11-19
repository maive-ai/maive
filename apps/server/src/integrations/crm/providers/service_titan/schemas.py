"""
Service Titan-specific Pydantic schemas.

This module contains all Pydantic models specific to Service Titan CRM,
including jobs, estimates, projects, and pricebook items.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.integrations.crm.constants import EstimateReviewStatus


# ============================================================================
# Service Titan Job Schemas
# ============================================================================


class ServiceTitanJob(BaseModel):
    """Service Titan job response model."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="ID of the job")
    job_number: str = Field(..., description="Job number", alias="jobNumber")
    project_id: int | None = Field(
        None, description="ID of the job's project", alias="projectId"
    )
    customer_id: int = Field(
        ..., description="ID of the job's customer", alias="customerId"
    )
    location_id: int = Field(
        ..., description="ID of the job's location", alias="locationId"
    )
    job_status: str = Field(..., description="Status of the job", alias="jobStatus")
    completed_on: datetime | None = Field(
        None,
        description="Date/time (in UTC) when the job was completed",
        alias="completedOn",
    )
    business_unit_id: int = Field(
        ..., description="ID of the job's business unit", alias="businessUnitId"
    )
    job_type_id: int = Field(..., description="ID of job type", alias="jobTypeId")
    priority: str = Field(..., description="Priority of the job")
    campaign_id: int = Field(
        ..., description="ID of the job's campaign", alias="campaignId"
    )
    appointment_count: int = Field(
        ..., description="Number of appointments on the job", alias="appointmentCount"
    )
    first_appointment_id: int = Field(
        ...,
        description="ID of the first appointment on the job",
        alias="firstAppointmentId",
    )
    last_appointment_id: int = Field(
        ...,
        description="ID of the last appointment on the job",
        alias="lastAppointmentId",
    )
    recall_for_id: int | None = Field(
        None,
        description="ID of the job for which this job is a recall",
        alias="recallForId",
    )
    warranty_id: int | None = Field(
        None,
        description="ID of the job for which this job is a warranty",
        alias="warrantyId",
    )
    no_charge: bool = Field(
        ..., description="Whether the job is a no-charge job", alias="noCharge"
    )
    notifications_enabled: bool = Field(
        ...,
        description="Whether notifications will be sent to customers",
        alias="notificationsEnabled",
    )
    created_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when the job was created",
        alias="createdOn",
    )
    created_by_id: int = Field(
        ..., description="ID of the user who created the job", alias="createdById"
    )
    modified_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when job was last modified",
        alias="modifiedOn",
    )
    tag_type_ids: list[int] = Field(
        ..., description="Tags on the job", alias="tagTypeIds"
    )
    customer_po: str | None = Field(None, description="Customer PO", alias="customerPo")
    invoice_id: int | None = Field(
        None,
        description="ID of the invoice associated with this job",
        alias="invoiceId",
    )
    total: float | None = Field(None, description="Total amount of the job")
    summary: str | None = Field(None, description="Job summary")


# ============================================================================
# Service Titan Estimate Schemas
# ============================================================================


class EstimateStatus(BaseModel):
    """Estimate status model with value and name."""

    value: int = Field(..., description="Status value")
    name: str = Field(..., description="Status name")


class ServiceTitanEstimate(BaseModel):
    """Service Titan estimate response model."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="ID of the estimate")
    job_id: int | None = Field(
        None, description="ID of the associated job", alias="jobId"
    )
    project_id: int | None = Field(
        None, description="ID of the associated project", alias="projectId"
    )
    location_id: int | None = Field(
        None, description="ID of the location", alias="locationId"
    )
    customer_id: int | None = Field(
        None, description="ID of the customer", alias="customerId"
    )
    name: str | None = Field(None, description="Name of the estimate")
    job_number: str | None = Field(None, description="Job number", alias="jobNumber")
    status: EstimateStatus | None = Field(None, description="Status of the estimate")
    review_status: EstimateReviewStatus = Field(
        ..., description="Review status of the estimate", alias="reviewStatus"
    )
    summary: str | None = Field(None, description="Summary of the estimate")
    created_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when the estimate was created",
        alias="createdOn",
    )
    modified_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when estimate was last modified",
        alias="modifiedOn",
    )
    sold_on: datetime | None = Field(
        None,
        description="Date/time (in UTC) when the estimate was sold",
        alias="soldOn",
    )
    sold_by: int | None = Field(
        None, description="ID of who sold the estimate", alias="soldBy"
    )
    active: bool = Field(..., description="Whether the estimate is active")
    subtotal: float = Field(..., description="Subtotal amount")
    tax: float = Field(..., description="Tax amount")
    business_unit_id: int | None = Field(
        None, description="ID of the business unit", alias="businessUnitId"
    )
    business_unit_name: str | None = Field(
        None, description="Name of the business unit", alias="businessUnitName"
    )
    is_recommended: bool = Field(
        ..., description="Whether this estimate is recommended", alias="isRecommended"
    )
    budget_code_id: int | None = Field(
        None, description="ID of the budget code", alias="budgetCodeId"
    )
    is_change_order: bool = Field(
        ...,
        description="Whether this estimate is a change order",
        alias="isChangeOrder",
    )


class SkuModel(BaseModel):
    """SKU model for estimate items."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="SKU ID")
    name: str = Field(..., description="SKU name")
    display_name: str = Field(..., description="Display name", alias="displayName")
    type: str = Field(..., description="SKU type")
    sold_hours: float = Field(..., description="Sold hours", alias="soldHours")
    general_ledger_account_id: int = Field(
        ..., description="General ledger account ID", alias="generalLedgerAccountId"
    )
    general_ledger_account_name: str = Field(
        ..., description="General ledger account name", alias="generalLedgerAccountName"
    )
    modified_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when SKU was last modified",
        alias="modifiedOn",
    )


class ServiceTitanEstimateItem(BaseModel):
    """Service Titan estimate item response model."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="ID of the estimate item")
    sku: SkuModel = Field(..., description="SKU details")
    sku_account: str = Field(..., description="SKU account", alias="skuAccount")
    description: str = Field(..., description="Item description")
    membership_type_id: int | None = Field(
        None, description="Membership type ID", alias="membershipTypeId"
    )
    qty: float = Field(..., description="Quantity")
    unit_rate: float = Field(..., description="Unit rate", alias="unitRate")
    total: float = Field(..., description="Total amount")
    unit_cost: float = Field(..., description="Unit cost", alias="unitCost")
    total_cost: float = Field(..., description="Total cost", alias="totalCost")
    item_group_name: str | None = Field(
        None, description="Item group name", alias="itemGroupName"
    )
    item_group_root_id: int | None = Field(
        None, description="Item group root ID", alias="itemGroupRootId"
    )
    created_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when the item was created",
        alias="createdOn",
    )
    modified_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when the item was last modified",
        alias="modifiedOn",
    )
    chargeable: bool | None = Field(None, description="Whether the item is chargeable")
    invoice_item_id: int | None = Field(
        None,
        description="The invoice item which was created from this estimate item",
        alias="invoiceItemId",
    )
    budget_code_id: int | None = Field(
        None, description="Budget code ID", alias="budgetCodeId"
    )


# ============================================================================
# Service Titan Project Schemas
# ============================================================================


class ServiceTitanProject(BaseModel):
    """Service Titan project response model."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="ID of the project")
    number: str | None = Field(None, description="Project number")
    name: str | None = Field(None, description="Project name")
    status: str | None = Field(None, description="Project status name")
    status_id: int | None = Field(
        None, description="Project status ID", alias="statusId"
    )
    sub_status: str | None = Field(
        None, description="Project sub-status name", alias="subStatus"
    )
    sub_status_id: int | None = Field(
        None, description="Project sub-status ID", alias="subStatusId"
    )
    customer_id: int | None = Field(
        None, description="ID of the customer", alias="customerId"
    )
    location_id: int | None = Field(
        None, description="ID of the location", alias="locationId"
    )
    start_date: datetime | None = Field(
        None, description="Project start date", alias="startDate"
    )
    target_completion_date: datetime | None = Field(
        None, description="Target completion date", alias="targetCompletionDate"
    )
    actual_completion_date: datetime | None = Field(
        None, description="Actual completion date", alias="actualCompletionDate"
    )
    created_on: datetime = Field(
        ..., description="Date/time (in UTC) when created", alias="createdOn"
    )
    modified_on: datetime = Field(
        ..., description="Date/time (in UTC) when last modified", alias="modifiedOn"
    )


# ============================================================================
# Service Titan Note Schemas
# ============================================================================


class ServiceTitanJobNote(BaseModel):
    """Service Titan job note response model."""

    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(..., description="Text content of the note")
    is_pinned: bool = Field(
        ..., description="Whether the note is pinned to the top", alias="isPinned"
    )
    created_by_id: int = Field(
        ..., description="ID of user who created this note", alias="createdById"
    )
    created_on: datetime = Field(
        ..., description="Date/time (in UTC) the note was created", alias="createdOn"
    )
    modified_on: datetime | None = Field(
        None, description="Date/time (in UTC) when last modified", alias="modifiedOn"
    )


# ============================================================================
# Service Titan Pricebook Schemas
# ============================================================================


class ServiceTitanMaterial(BaseModel):
    """Service Titan material from pricebook."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Material ID")
    code: str = Field(..., description="Material code/SKU")
    display_name: str = Field(..., description="Display name", alias="displayName")
    description: str | None = Field(None, description="Material description")
    cost: float | None = Field(None, description="Material cost")
    price: float | None = Field(None, description="Material price")
    member_price: float | None = Field(
        None, description="Member price", alias="memberPrice"
    )
    add_on_price: float | None = Field(
        None, description="Add-on price", alias="addOnPrice"
    )
    add_on_member_price: float | None = Field(
        None, description="Add-on member price", alias="addOnMemberPrice"
    )
    active: bool = Field(..., description="Whether the material is active")
    manufacturer: str | None = Field(None, description="Manufacturer name")
    manufacturer_number: str | None = Field(
        None, description="Manufacturer part number", alias="manufacturerNumber"
    )


class ServiceTitanService(BaseModel):
    """Service Titan service from pricebook."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Service ID")
    code: str = Field(..., description="Service code/SKU")
    display_name: str = Field(..., description="Display name", alias="displayName")
    description: str | None = Field(None, description="Service description")
    price: float | None = Field(None, description="Service price")
    member_price: float | None = Field(
        None, description="Member price", alias="memberPrice"
    )
    add_on_price: float | None = Field(
        None, description="Add-on price", alias="addOnPrice"
    )
    add_on_member_price: float | None = Field(
        None, description="Add-on member price", alias="addOnMemberPrice"
    )
    active: bool = Field(..., description="Whether the service is active")
    hours: float | None = Field(None, description="Service hours")


class ServiceTitanEquipment(BaseModel):
    """Service Titan equipment from pricebook."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Equipment ID")
    code: str = Field(..., description="Equipment code/SKU")
    display_name: str = Field(..., description="Display name", alias="displayName")
    description: str | None = Field(None, description="Equipment description")
    cost: float | None = Field(None, description="Equipment cost")
    price: float | None = Field(None, description="Equipment price")
    member_price: float | None = Field(
        None, description="Member price", alias="memberPrice"
    )
    add_on_price: float | None = Field(
        None, description="Add-on price", alias="addOnPrice"
    )
    add_on_member_price: float | None = Field(
        None, description="Add-on member price", alias="addOnMemberPrice"
    )
    active: bool = Field(..., description="Whether the equipment is active")
    manufacturer: str | None = Field(None, description="Manufacturer name")
    manufacturer_number: str | None = Field(
        None, description="Manufacturer part number", alias="manufacturerNumber"
    )


# ============================================================================
# Service Titan Request Models
# ============================================================================


class ServiceTitanJobRequest(BaseModel):
    """Request model for getting a specific Service Titan job."""

    job_id: int = Field(..., description="ID of the job to retrieve")
    tenant: int = Field(..., description="Tenant ID")


class ServiceTitanEstimateRequest(BaseModel):
    """Request model for getting Service Titan estimates with filters."""

    model_config = ConfigDict(populate_by_name=True)

    tenant: int = Field(..., description="Tenant ID")
    job_id: int | None = Field(
        None, description="Job ID to filter estimates", alias="jobId"
    )
    project_id: int | None = Field(
        None, description="Project ID to filter estimates", alias="projectId"
    )
    page: int | None = Field(None, description="Page number for pagination")
    page_size: int | None = Field(
        None, description="Page size for pagination (max 50)", le=50, alias="pageSize"
    )
    ids: str | None = Field(None, description="Comma separated string of estimate IDs")


class ServiceTitanEstimateItemsRequest(BaseModel):
    """Request model for getting Service Titan estimate items."""

    model_config = ConfigDict(populate_by_name=True)

    tenant: int = Field(..., description="Tenant ID")
    estimate_id: int = Field(..., description="ID of the estimate", alias="estimateId")


class ServiceTitanHoldJobRequest(BaseModel):
    """Request model for holding a Service Titan job."""

    model_config = ConfigDict(populate_by_name=True)

    tenant: int = Field(..., description="Tenant ID")
    job_id: int = Field(..., description="ID of the job", alias="jobId")
    reason_id: int = Field(..., description="ID of the hold reason", alias="reasonId")


class ServiceTitanUpdateProjectRequest(BaseModel):
    """Request model for updating a Service Titan project."""

    model_config = ConfigDict(populate_by_name=True)

    tenant: int = Field(..., description="Tenant ID")
    project_id: int = Field(
        ..., description="ID of the project to update", alias="projectId"
    )
    status_id: int | None = Field(
        None, description="Project status ID", alias="statusId"
    )
    sub_status_id: int | None = Field(
        None, description="Project sub status ID", alias="subStatusId"
    )
