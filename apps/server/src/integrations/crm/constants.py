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


class CRMProvider(str, Enum):
    """Available CRM providers."""

    SERVICE_TITAN = "service_titan"


class ServiceTitanEndpoints:
    """Service Titan API endpoints."""

    BASE_URL = "https://api.servicetitan.io"
    PROJECTS = "/tenant/{tenant_id}/jpm/v2/jobs"
    PROJECT_BY_ID = "/tenant/{tenant_id}/jpm/v2/jobs/{job_id}"