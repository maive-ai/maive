# CRM Integration Refactor - Implementation Plan

## Current Status (Completed)

✅ **Phase 1: Universal Schemas**
- Added `Job`, `JobList`, `Contact`, `ContactList`, `Note` to `schemas.py`
- All universal schemas use string IDs and ISO datetime strings
- Include `provider_data` dict for provider-specific fields

✅ **Phase 2: Provider Directory Structure**
```
providers/
├── service_titan/
│   ├── __init__.py
│   ├── provider.py (copied, needs import updates)
│   └── constants.py (extracted ST-specific constants)
├── job_nimbus/
│   ├── __init__.py
│   ├── provider.py (copied, needs import updates)
│   ├── schemas.py (moved from schemas_jobnimbus.py)
│   └── constants.py (extracted JN-specific constants)
└── mock_crm/
    ├── __init__.py
    └── provider.py (copied, needs import updates)
```

## Remaining Work - Detailed Steps

### Phase 3: Refactor base.py Interface

**File:** `src/integrations/crm/base.py`

**Changes:**
1. Remove all existing @abstractmethod decorators (12 methods)
2. Replace with 6 new universal abstract methods:

```python
from typing import Any
from abc import ABC, abstractmethod
from src.integrations.crm.schemas import Job, JobList, Contact, ContactList, Note

class CRMProvider(ABC):
    """Universal abstract interface for CRM providers."""

    @abstractmethod
    async def get_job(self, job_id: str) -> Job:
        """Get a specific job by ID."""
        pass

    @abstractmethod
    async def get_all_jobs(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> JobList:
        """Get all jobs with optional filtering and pagination."""
        pass

    @abstractmethod
    async def get_contact(self, contact_id: str) -> Contact:
        """Get a specific contact/customer by ID."""
        pass

    @abstractmethod
    async def get_all_contacts(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ContactList:
        """Get all contacts with optional filtering and pagination."""
        pass

    @abstractmethod
    async def add_note(
        self,
        entity_id: str,
        entity_type: str,
        text: str,
        **kwargs,
    ) -> Note:
        """Add a note/activity to an entity (job, contact, etc.)."""
        pass

    @abstractmethod
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs,
    ) -> None:
        """Update the status of a job."""
        pass


class CRMError(Exception):
    """Base exception for CRM-related errors."""
    # Keep as-is
```

### Phase 4: Create Service Titan Schemas File

**File:** `src/integrations/crm/providers/service_titan/schemas.py`

**Content:**
Extract all Service Titan-specific schemas from main `schemas.py`:
- `ServiceTitanJob` (rename from `JobResponse`)
- `ServiceTitanEstimate` (rename from `EstimateResponse`)
- `ServiceTitanEstimateItem` (rename from `EstimateItemResponse`)
- `ServiceTitanProject` (rename from `ProjectResponse`)
- `ServiceTitanJobNote` (rename from `JobNoteResponse`)
- All request models (EstimatesRequest, etc.)

Keep these in the main schemas.py only if used by router/service layer.

### Phase 5: Update ServiceTitanProvider

**File:** `src/integrations/crm/providers/service_titan/provider.py`

**Import Changes:**
```python
from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.config import get_crm_settings, ServiceTitanConfig
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum, Status
from src.integrations.crm.schemas import Job, JobList, Contact, ContactList, Note
from src.integrations.crm.providers.service_titan.constants import ServiceTitanEndpoints, SubStatus, JobHoldReasonId
from src.integrations.crm.providers.service_titan.schemas import ServiceTitanJob, ServiceTitanEstimate  # If created
```

**New Methods to Implement:**

1. **get_job(job_id: str) -> Job**
   - Call existing `get_job(int(job_id))`
   - Transform `ServiceTitanJob` → `Job` using helper

2. **get_all_jobs(...) -> JobList**
   - Call existing `get_all_project_statuses()`
   - Transform list to `JobList`

3. **get_contact(contact_id: str) -> Contact**
   - Service Titan doesn't have separate contacts
   - Raise `CRMError("Contacts not supported as separate entity in Service Titan", "NOT_SUPPORTED")`
   - Or extract customer from job if customer_id provided

4. **get_all_contacts(...) -> ContactList**
   - Raise `CRMError("Contacts not supported", "NOT_SUPPORTED")`

5. **add_note(entity_id, entity_type, text, **kwargs) -> Note**
   - If entity_type == "job": call existing `add_job_note()`
   - If entity_type == "project": call existing `add_project_note()`
   - Transform response to universal `Note`

6. **update_job_status(job_id, status, **kwargs) -> None**
   - Call existing `update_project()` with status change
   - Or implement new method if needed

**Helper Method:**
```python
def _transform_st_job_to_universal(self, st_job: ServiceTitanJob) -> Job:
    """Transform Service Titan job to universal Job schema."""
    return Job(
        id=str(st_job.id),
        name=st_job.job_number,  # Or construct from other fields
        number=st_job.job_number,
        status=st_job.job_status,
        status_id=None,  # ST doesn't expose status ID easily
        workflow_type=None,  # Could map from job_type_id
        description=st_job.summary,
        customer_id=str(st_job.customer_id) if st_job.customer_id else None,
        customer_name=None,  # Not in job response
        # ... map all other fields
        created_at=st_job.created_on.isoformat(),
        updated_at=st_job.modified_on.isoformat(),
        completed_at=st_job.completed_on.isoformat() if st_job.completed_on else None,
        provider=CRMProviderEnum.SERVICE_TITAN,
        provider_data={
            "job_type_id": st_job.job_type_id,
            "business_unit_id": st_job.business_unit_id,
            "project_id": st_job.project_id,
            "invoice_id": st_job.invoice_id,
            "total": st_job.total,
            # ... all ST-specific fields
        }
    )
```

**Keep Existing Methods:**
All existing Service Titan-specific methods remain as regular (non-abstract) instance methods:
- `get_estimate()`
- `get_estimates()`
- `get_estimate_items()`
- `get_project_by_id()`
- `update_project()`
- `hold_job()`
- `get_job_hold_reasons()`
- etc.

### Phase 6: Update JobNimbusProvider

**File:** `src/integrations/crm/providers/job_nimbus/provider.py`

**Import Changes:**
```python
from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.config import get_crm_settings, JobNimbusConfig
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.schemas import Job, JobList, Contact, ContactList, Note
from src.integrations.crm.providers.job_nimbus.constants import JobNimbusEndpoints
from src.integrations.crm.providers.job_nimbus.schemas import (
    JobNimbusJob,
    JobNimbusJobsList,
    JobNimbusContact,
    JobNimbusContactsList,
    JobNimbusActivity,
    # ... other schemas
)
```

**New Methods to Implement:**

1. **get_job(job_id: str) -> Job**
   - Keep existing implementation
   - Transform `JobNimbusJob` → `Job`

2. **get_all_jobs(...) -> JobList**
   - Keep existing implementation
   - Transform to `JobList`

3. **get_contact(contact_id: str) -> Contact**
   - Keep existing `get_contact()` implementation
   - Transform `JobNimbusContact` → `Contact`

4. **get_all_contacts(...) -> ContactList**
   - Keep existing implementation
   - Transform to `ContactList`

5. **add_note(entity_id, entity_type, text, **kwargs) -> Note**
   - Keep existing activity creation logic
   - Transform to universal `Note`

6. **update_job_status(job_id, status, **kwargs) -> None**
   - Implement using JobNimbus update job endpoint
   - Update `status_name` field

**Helper Method:**
```python
def _transform_jn_job_to_universal(self, jn_job: JobNimbusJob) -> Job:
    """Transform JobNimbus job to universal Job schema."""
    return Job(
        id=jn_job.jnid,
        name=jn_job.name,
        number=jn_job.number,
        status=jn_job.status_name or "Unknown",
        status_id=jn_job.status,
        workflow_type=jn_job.record_type_name,
        description=jn_job.description,
        customer_id=jn_job.primary.id if jn_job.primary else None,
        customer_name=jn_job.primary.name if jn_job.primary else None,
        address_line1=jn_job.address_line1,
        address_line2=jn_job.address_line2,
        city=jn_job.city,
        state=jn_job.state_text,
        postal_code=jn_job.zip,
        country=jn_job.country_name,
        created_at=datetime.fromtimestamp(jn_job.date_created, tz=UTC).isoformat(),
        updated_at=datetime.fromtimestamp(jn_job.date_updated, tz=UTC).isoformat(),
        completed_at=None,  # JN doesn't track completion
        sales_rep_id=jn_job.sales_rep,
        sales_rep_name=jn_job.sales_rep_name,
        provider=CRMProviderEnum.JOB_NIMBUS,
        provider_data={
            "recid": jn_job.recid,
            "related": jn_job.related,
            "owners": jn_job.owners,
            "source": jn_job.source,
            "source_name": jn_job.source_name,
            # ... all JN-specific fields
        }
    )
```

### Phase 7: Update MockCRMProvider

**File:** `src/integrations/crm/providers/mock_crm/provider.py`

**Changes:**
- Update imports to use new universal schemas
- Implement the 6 universal methods
- Keep existing mock data logic

### Phase 8: Update Factory

**File:** `src/integrations/crm/providers/factory.py`

**Changes:**
```python
from src.integrations.crm.base import CRMProvider
from src.integrations.crm.config import get_crm_settings
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.providers.service_titan import ServiceTitanProvider
from src.integrations.crm.providers.job_nimbus import JobNimbusProvider
from src.integrations.crm.providers.mock_crm import MockCRMProvider
from src.utils.logger import logger

# Rest stays the same
```

### Phase 9: Update Service Layer

**File:** `src/integrations/crm/service.py`

**Major Changes:**

1. **Replace Methods:**
   - `get_project_status()` → `get_job()`
   - `get_all_project_statuses()` → `get_all_jobs()`
   - `add_job_note()` → `add_note(entity_id, entity_type="job", ...)`
   - Add new: `get_contact()`, `get_all_contacts()`

2. **New Method Signatures:**
```python
async def get_job(self, job_id: str) -> Job | CRMErrorResponse:
    """Get a specific job by ID."""
    try:
        logger.info(f"Getting job: {job_id}")
        result = await self.crm_provider.get_job(job_id)
        logger.info(f"Successfully retrieved job {job_id}")
        return result
    except CRMError as e:
        # ... error handling
        return CRMErrorResponse(...)

async def get_all_jobs(
    self,
    filters: dict | None = None,
    page: int = 1,
    page_size: int = 50
) -> JobList | CRMErrorResponse:
    """Get all jobs with optional filtering."""
    # ...

async def get_contact(self, contact_id: str) -> Contact | CRMErrorResponse:
    """Get a specific contact by ID."""
    # ...

async def get_all_contacts(...) -> ContactList | CRMErrorResponse:
    """Get all contacts with optional filtering."""
    # ...

async def add_note(
    self,
    entity_id: str,
    entity_type: str,
    text: str,
    **kwargs
) -> Note | CRMErrorResponse:
    """Add a note to any entity."""
    # ...
```

3. **Keep Compatibility Methods (Optional):**
```python
# Deprecated - for backward compatibility
async def get_project_status(self, project_id: str):
    """Deprecated: Use get_job() instead."""
    logger.warning("get_project_status() is deprecated, use get_job()")
    return await self.get_job(project_id)
```

### Phase 10: Update Router

**File:** `src/integrations/crm/router.py`

**Import Changes:**
```python
from src.integrations.crm.schemas import (
    Job,
    JobList,
    Contact,
    ContactList,
    Note,
    CRMErrorResponse,
    # Keep legacy schemas temporarily if needed
)
```

**New Endpoints:**

```python
@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> Job:
    """Get a specific job by ID."""
    result = await crm_service.get_job(job_id)
    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)
    return result


@router.get("/jobs", response_model=JobList)
async def get_all_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> JobList:
    """Get all jobs with pagination."""
    result = await crm_service.get_all_jobs(page=page, page_size=page_size)
    if isinstance(result, CRMErrorResponse):
        raise HTTPException(status_code=500, detail=result.error)
    return result


@router.get("/contacts/{contact_id}", response_model=Contact)
async def get_contact(
    contact_id: str,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> Contact:
    """Get a specific contact by ID."""
    # ...


@router.get("/contacts", response_model=ContactList)
async def get_all_contacts(...) -> ContactList:
    """Get all contacts with pagination."""
    # ...


@router.post("/jobs/{job_id}/notes", response_model=Note)
async def add_job_note(
    job_id: str,
    text: str = Body(...),
    pin_to_top: bool = Body(False),
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> Note:
    """Add a note to a job."""
    result = await crm_service.add_note(
        entity_id=job_id,
        entity_type="job",
        text=text,
        pin_to_top=pin_to_top,
    )
    # ...


@router.post("/contacts/{contact_id}/notes", response_model=Note)
async def add_contact_note(...) -> Note:
    """Add a note to a contact."""
    # ...
```

**Legacy Endpoints (Backward Compatible):**
```python
# Keep these temporarily, just delegate to new methods
@router.get("/projects/{project_id}/status", response_model=Job)
async def get_project_status_legacy(project_id: str, ...):
    """Legacy endpoint - use /jobs/{job_id} instead."""
    return await get_job(project_id, ...)
```

### Phase 11: Update Provider __init__.py

**File:** `src/integrations/crm/providers/__init__.py`

```python
"""CRM provider implementations."""

from src.integrations.crm.providers.factory import (
    create_crm_provider,
    get_crm_provider,
    set_crm_provider,
)
from src.integrations.crm.providers.service_titan import ServiceTitanProvider
from src.integrations.crm.providers.job_nimbus import JobNimbusProvider
from src.integrations.crm.providers.mock_crm import MockCRMProvider

__all__ = [
    "create_crm_provider",
    "get_crm_provider",
    "set_crm_provider",
    "ServiceTitanProvider",
    "JobNimbusProvider",
    "MockCRMProvider",
]
```

### Phase 12: Cleanup

**Files to Delete:**
- `src/integrations/crm/providers/service_titan.py` (old location)
- `src/integrations/crm/providers/job_nimbus.py` (old location)
- `src/integrations/crm/providers/mock_crm.py` (old location)
- `src/integrations/crm/schemas_jobnimbus.py` (moved to providers/job_nimbus/schemas.py)

**Update top-level constants.py:**
- Remove ServiceTitanEndpoints, JobNimbusEndpoints, SubStatus, JobHoldReasonId
- Keep only universal constants (CRMProvider enum, Status, ClaimStatus, etc.)

### Phase 13: Testing

**Test Checklist:**

1. **Type Checking:**
   ```bash
   cd apps/server
   uv run mypy src/integrations/crm
   ```

2. **Linting:**
   ```bash
   uv run ruff check src/integrations/crm
   ```

3. **Import Validation:**
   ```bash
   uv run python -c "from src.integrations.crm.providers import ServiceTitanProvider, JobNimbusProvider"
   ```

4. **Manual Testing:**
   - Set `CRM_PROVIDER=service_titan` and test Service Titan endpoints
   - Set `CRM_PROVIDER=job_nimbus` and test JobNimbus endpoints
   - Test new `/jobs` and `/contacts` endpoints
   - Verify legacy `/projects` endpoints still work

5. **API Testing:**
   ```bash
   # Start server
   cd apps/server
   esc run <env> -- uv run fastapi dev --app app src/main.py --port 8080

   # Test endpoints
   curl http://localhost:8080/crm/jobs/{job_id}
   curl http://localhost:8080/crm/contacts/{contact_id}
   ```

## Migration Strategy

### For Existing Code:
1. Update all imports throughout codebase
2. Replace calls to `get_project_status()` with `get_job()`
3. Replace calls to `add_job_note()` with `add_note(entity_id, entity_type="job", ...)`
4. Update any code expecting `ProjectStatusResponse` to handle `Job` schema

### Breaking Changes:
1. ✅ API endpoints changed (`/projects` → `/jobs`)
2. ✅ Response schemas changed (`ProjectStatusResponse` → `Job`)
3. ✅ Method signatures changed (int job_id → str job_id)
4. ✅ Service layer method names changed

### Compatibility Layer (Optional):
Keep old endpoints/methods temporarily with deprecation warnings to ease migration.

## Estimated Effort

- **Phase 3-7:** 2-3 hours (Interface refactor + provider updates)
- **Phase 8-10:** 1-2 hours (Factory, service, router updates)
- **Phase 11-12:** 30 minutes (Cleanup and final imports)
- **Phase 13:** 1 hour (Testing and fixes)

**Total:** 4-6 hours of focused development work

## Risk Areas

1. **Import Errors:** Lots of file movements and import updates - easy to miss one
2. **Type Mismatches:** int vs str for IDs - need careful conversion
3. **Missing Transformations:** Forgetting to map a field in universal schema converters
4. **Service Titan Testing:** Need actual ST credentials to test transformations
5. **JobNimbus Testing:** Need actual JN credentials to test transformations

## Next Steps

Once you've reviewed this plan:
1. Test the current state (directories created, files copied)
2. Decide if you want to proceed with full implementation
3. Consider doing this in smaller PRs if preferred
4. Let me know if any part of the plan needs adjustment
