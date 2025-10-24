"""Unit tests for JobNimbus provider universal interface."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.crm.base import CRMError
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.providers.job_nimbus.provider import JobNimbusProvider
from src.integrations.crm.providers.job_nimbus.schemas import (
    JobNimbusActivityResponse,
    JobNimbusContactResponse,
    JobNimbusContactsListResponse,
    JobNimbusJobResponse,
    JobNimbusJobsListResponse,
)


# Sample JobNimbus API responses
SAMPLE_JN_JOB = {
    "recid": 12345,
    "jnid": "test_job_123",
    "customer": "customer_456",
    "type": "job",
    "createdBy": "user_789",
    "createdByName": "John Doe",
    "dateCreated": int(time.time()),
    "dateUpdated": int(time.time()),
    "location": {
        "id": 111,
        "name": "Main Office"
    },
    "owners": [
        {
            "id": "user_789"
        }
    ],
    "isActive": True,
    "isArchived": False,
    "name": "Roof Repair - Smith Residence",
    "number": "JOB-2024-001",
    "recordType": 1,
    "recordTypeName": "Roof Repair",
    "status": 5,
    "statusName": "In Progress",
    "description": "Full roof replacement needed",
    "salesRep": "rep_999",
    "salesRepName": "Jane Sales",
    "source": 10,
    "sourceName": "Referral",
    "addressLine1": "123 Main St",
    "addressLine2": "Apt 4B",
    "city": "Austin",
    "stateText": "TX",
    "countryName": "USA",
    "zip": "78701",
    "geo": {
        "lat": 30.2672,
        "lon": -97.7431
    },
    "related": [
        {
            "id": "customer_456",
            "name": "John Smith",
            "type": "contact"
        }
    ],
    "primary": {
        "id": "customer_456",
        "name": "John Smith",
        "type": "contact"
    }
}

SAMPLE_JN_CONTACT = {
    "recid": 54321,
    "jnid": "contact_abc",
    "customer": "contact_abc",  # Required field
    "type": "contact",
    "createdBy": "user_789",
    "createdByName": "John Doe",
    "dateCreated": int(time.time()),
    "dateUpdated": int(time.time()),
    "location": {
        "id": 111,
        "name": "Main Office"
    },
    "owners": [],
    "isActive": True,
    "isArchived": False,
    "firstName": "Jane",
    "lastName": "Customer",
    "displayName": "Jane Customer",
    "companyName": "Customer Corp",
    "email": "jane@example.com",
    "phone": "+15125551234",
    "addressLine1": "456 Oak Ave",
    "city": "Dallas",
    "stateText": "TX",
    "zip": "75201",
    "contactType": "customer"
}

SAMPLE_JN_ACTIVITY = {
    "recid": 99999,
    "jnid": "activity_xyz",
    "type": "note",
    "createdBy": "user_789",
    "createdByName": "John Doe",
    "dateCreated": int(time.time()),
    "dateUpdated": int(time.time()),
    "body": "This is a test note",
    "related": ["test_job_123"]
}


@pytest.fixture
def job_nimbus_provider():
    """Create a JobNimbus provider instance with mocked config."""
    from src.integrations.crm.config import JobNimbusConfig

    with patch("src.integrations.crm.providers.job_nimbus.provider.get_crm_settings") as mock_settings:
        # Create a real JobNimbusConfig instance
        mock_jn_config = JobNimbusConfig(
            api_key="test_api_key",
            base_api_url="https://api.jobnimbus.com"
        )

        mock_config = MagicMock()
        mock_config.provider_config = mock_jn_config
        mock_config.request_timeout = 30.0
        mock_settings.return_value = mock_config

        provider = JobNimbusProvider()
        return provider


class TestJobNimbusUniversalInterface:
    """Test suite for JobNimbus universal interface methods."""

    @pytest.mark.asyncio
    async def test_get_job_success(self, job_nimbus_provider):
        """Test get_job returns universal Job schema."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_JN_JOB
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response):
            job = await job_nimbus_provider.get_job("test_job_123")

        # Verify universal schema fields
        assert job.id == "test_job_123"
        assert job.name == "Roof Repair - Smith Residence"
        assert job.number == "JOB-2024-001"
        assert job.status == "In Progress"
        assert job.status_id == "5"
        assert job.workflow_type == "Roof Repair"
        assert job.description == "Full roof replacement needed"
        assert job.customer_id == "customer_456"
        assert job.customer_name == "John Smith"
        assert job.address_line1 == "123 Main St"
        assert job.address_line2 == "Apt 4B"
        assert job.city == "Austin"
        assert job.state == "TX"
        assert job.postal_code == "78701"
        assert job.country == "USA"
        assert job.sales_rep_id == "rep_999"
        assert job.sales_rep_name == "Jane Sales"
        assert job.provider == CRMProviderEnum.JOB_NIMBUS
        assert job.created_at is not None
        assert job.updated_at is not None

        # Verify provider_data contains JobNimbus-specific fields
        assert job.provider_data is not None
        assert job.provider_data["recid"] == 12345
        assert job.provider_data["jnid"] == "test_job_123"
        assert job.provider_data["source"] == 10
        assert job.provider_data["source_name"] == "Referral"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, job_nimbus_provider):
        """Test get_job raises CRMError when job not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_http_error = httpx.HTTPStatusError(
            message="Not Found",
            request=MagicMock(),
            response=mock_response
        )

        with patch.object(job_nimbus_provider, "_make_request", side_effect=mock_http_error):
            with pytest.raises(CRMError) as exc_info:
                await job_nimbus_provider.get_job("nonexistent_job")

            assert exc_info.value.error_code == "NOT_FOUND"
            assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_all_jobs_success(self, job_nimbus_provider):
        """Test get_all_jobs returns paginated JobList."""
        mock_jobs_list = {
            "results": [SAMPLE_JN_JOB, {**SAMPLE_JN_JOB, "jnid": "test_job_456", "name": "Another Job"}],
            "meta": {
                "total": 2
            }
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_jobs_list
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response):
            job_list = await job_nimbus_provider.get_all_jobs(page=1, page_size=10)

        # Verify JobList structure
        assert len(job_list.jobs) == 2
        assert job_list.total_count == 2
        assert job_list.provider == CRMProviderEnum.JOB_NIMBUS
        assert job_list.page == 1
        assert job_list.page_size == 10
        assert job_list.has_more is False

        # Verify first job
        first_job = job_list.jobs[0]
        assert first_job.id == "test_job_123"
        assert first_job.name == "Roof Repair - Smith Residence"
        assert first_job.provider == CRMProviderEnum.JOB_NIMBUS

    @pytest.mark.asyncio
    async def test_get_all_jobs_pagination(self, job_nimbus_provider):
        """Test get_all_jobs pagination works correctly."""
        # Create 15 sample jobs
        jobs = [
            {**SAMPLE_JN_JOB, "jnid": f"job_{i}", "name": f"Job {i}"}
            for i in range(15)
        ]
        mock_jobs_list = {"results": jobs, "meta": {"total": 15}}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_jobs_list
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response):
            # Get page 2 with page_size=5
            job_list = await job_nimbus_provider.get_all_jobs(page=2, page_size=5)

        # Should return jobs 5-9 (indices 5-9)
        assert len(job_list.jobs) == 5
        assert job_list.total_count == 15
        assert job_list.page == 2
        assert job_list.page_size == 5
        assert job_list.has_more is True

        # Verify we got the right jobs (page 2 starts at index 5)
        assert job_list.jobs[0].id == "job_5"
        assert job_list.jobs[4].id == "job_9"

    @pytest.mark.asyncio
    async def test_get_project_success(self, job_nimbus_provider):
        """Test get_project returns universal Project schema (alias to job)."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_JN_JOB
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response):
            project = await job_nimbus_provider.get_project("test_job_123")

        # Verify universal Project schema fields
        assert project.id == "test_job_123"
        assert project.name == "Roof Repair - Smith Residence"
        assert project.number == "JOB-2024-001"
        assert project.status == "In Progress"
        assert project.workflow_type == "Roof Repair"
        assert project.provider == CRMProviderEnum.JOB_NIMBUS

    @pytest.mark.asyncio
    async def test_get_all_projects_success(self, job_nimbus_provider):
        """Test get_all_projects returns ProjectList (alias to jobs)."""
        mock_jobs_list = {
            "results": [SAMPLE_JN_JOB],
            "meta": {"total": 1}
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_jobs_list
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response):
            project_list = await job_nimbus_provider.get_all_projects(page=1, page_size=10)

        # Verify ProjectList structure
        assert len(project_list.projects) == 1
        assert project_list.total_count == 1
        assert project_list.provider == CRMProviderEnum.JOB_NIMBUS

        # Verify first project
        first_project = project_list.projects[0]
        assert first_project.id == "test_job_123"
        assert first_project.provider == CRMProviderEnum.JOB_NIMBUS

    @pytest.mark.asyncio
    async def test_get_contact_success(self, job_nimbus_provider):
        """Test get_contact returns universal Contact schema."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_JN_CONTACT
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response):
            contact = await job_nimbus_provider.get_contact("contact_abc")

        # Verify universal Contact schema fields
        assert contact.id == "contact_abc"
        assert contact.display_name == "Jane Customer"
        assert contact.first_name == "Jane"
        assert contact.last_name == "Customer"
        assert contact.email == "jane@example.com"
        assert contact.phone == "+15125551234"
        assert contact.company == "Customer Corp"
        assert contact.address_line1 == "456 Oak Ave"
        assert contact.city == "Dallas"
        assert contact.state == "TX"
        assert contact.postal_code == "75201"
        assert contact.provider == CRMProviderEnum.JOB_NIMBUS
        assert contact.created_at is not None
        assert contact.updated_at is not None

        # Verify provider_data
        assert contact.provider_data is not None
        assert contact.provider_data["recid"] == 54321
        assert contact.provider_data["jnid"] == "contact_abc"

    @pytest.mark.asyncio
    async def test_get_all_contacts_success(self, job_nimbus_provider):
        """Test get_all_contacts returns paginated ContactList."""
        mock_contacts_list = {
            "results": [SAMPLE_JN_CONTACT, {**SAMPLE_JN_CONTACT, "jnid": "contact_def", "displayName": "Bob User"}],
            "meta": {"total": 2}
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_contacts_list
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response):
            contact_list = await job_nimbus_provider.get_all_contacts(page=1, page_size=10)

        # Verify ContactList structure
        assert len(contact_list.contacts) == 2
        assert contact_list.total_count == 2
        assert contact_list.provider == CRMProviderEnum.JOB_NIMBUS
        assert contact_list.page == 1
        assert contact_list.page_size == 10
        assert contact_list.has_more is False

        # Verify first contact
        first_contact = contact_list.contacts[0]
        assert first_contact.id == "contact_abc"
        assert first_contact.display_name == "Jane Customer"

    @pytest.mark.asyncio
    async def test_add_note_success(self, job_nimbus_provider):
        """Test add_note creates activity and returns universal Note schema."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_JN_ACTIVITY
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response):
            note = await job_nimbus_provider.add_note(
                entity_id="test_job_123",
                entity_type="job",
                text="This is a test note"
            )

        # Verify universal Note schema
        assert note.id == "activity_xyz"
        assert note.text == "This is a test note"
        assert note.entity_id == "test_job_123"
        assert note.entity_type == "job"
        assert note.created_by_id == "user_789"
        assert note.created_by_name == "John Doe"
        assert note.is_pinned is False  # JobNimbus doesn't support pinning
        assert note.provider == CRMProviderEnum.JOB_NIMBUS
        assert note.created_at is not None

        # Verify provider_data
        assert note.provider_data is not None
        assert note.provider_data["activity_type"] == "note"
        assert note.provider_data["recid"] == 99999

    @pytest.mark.asyncio
    async def test_update_job_status_success(self, job_nimbus_provider):
        """Test update_job_status updates job via PATCH."""
        mock_response = MagicMock()
        mock_response.json.return_value = {**SAMPLE_JN_JOB, "status": 10, "statusName": "Completed"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response) as mock_request:
            await job_nimbus_provider.update_job_status(
                job_id="test_job_123",
                status="10"
            )

            # Verify PATCH request was made
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert args[0] == "PATCH"
            assert "test_job_123" in args[1]
            assert "json" in kwargs
            assert kwargs["json"]["status"] == "10"

    @pytest.mark.asyncio
    async def test_update_project_status_success(self, job_nimbus_provider):
        """Test update_project_status aliases to update_job_status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {**SAMPLE_JN_JOB, "status": 10}
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response) as mock_request:
            await job_nimbus_provider.update_project_status(
                project_id="test_job_123",
                status="10"
            )

            # Verify PATCH request was made (same as update_job_status)
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert args[0] == "PATCH"
            assert "test_job_123" in args[1]


class TestJobNimbusTransformations:
    """Test suite for JobNimbus transformation helpers."""

    @pytest.mark.asyncio
    async def test_unix_timestamp_conversion(self, job_nimbus_provider):
        """Test Unix timestamp to datetime conversion."""
        unix_ts = 1703001600  # 2023-12-19 16:00:00 UTC
        dt = job_nimbus_provider._unix_timestamp_to_datetime(unix_ts)

        assert dt.year == 2023
        assert dt.month == 12
        assert dt.day == 19

    @pytest.mark.asyncio
    async def test_job_transformation_with_minimal_data(self, job_nimbus_provider):
        """Test job transformation with minimal required fields."""
        minimal_job = {
            "jnid": "minimal_job",
            "customer": "customer_123",
            "type": "job",
            "createdBy": "user_1",
            "createdByName": "User One",
            "dateCreated": int(time.time()),
            "dateUpdated": int(time.time()),
            "owners": [],
            "isActive": True,
            "name": "Minimal Job",
            "recordType": 1,
            "recordTypeName": "Type A",
            # No status, description, address, etc.
        }

        mock_response = MagicMock()
        mock_response.json.return_value = minimal_job
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response):
            job = await job_nimbus_provider.get_job("minimal_job")

        # Should handle missing optional fields gracefully
        assert job.id == "minimal_job"
        assert job.name == "Minimal Job"
        assert job.status == "Unknown"
        assert job.status_id is None
        assert job.description is None
        assert job.address_line1 is None
        assert job.customer_id is None
        assert job.completed_at is None

    @pytest.mark.asyncio
    async def test_contact_transformation_with_minimal_data(self, job_nimbus_provider):
        """Test contact transformation with minimal required fields."""
        minimal_contact = {
            "jnid": "minimal_contact",
            "customer": "minimal_contact",  # Required field
            "type": "contact",
            "createdBy": "user_1",
            "createdByName": "User One",
            "dateCreated": int(time.time()),
            "dateUpdated": int(time.time()),
            "owners": [],
            "isActive": True,
            "displayName": "Minimal Contact",
            # No email, phone, address, etc.
        }

        mock_response = MagicMock()
        mock_response.json.return_value = minimal_contact
        mock_response.raise_for_status = MagicMock()

        with patch.object(job_nimbus_provider, "_make_request", return_value=mock_response):
            contact = await job_nimbus_provider.get_contact("minimal_contact")

        # Should handle missing optional fields gracefully
        assert contact.id == "minimal_contact"
        assert contact.display_name == "Minimal Contact"
        assert contact.email is None
        assert contact.phone is None
        assert contact.address_line1 is None


class TestJobNimbusErrorHandling:
    """Test suite for JobNimbus error handling."""

    @pytest.mark.asyncio
    async def test_http_error_handling(self, job_nimbus_provider):
        """Test HTTP error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_http_error = httpx.HTTPStatusError(
            message="Internal Server Error",
            request=MagicMock(),
            response=mock_response
        )

        with patch.object(job_nimbus_provider, "_make_request", side_effect=mock_http_error):
            with pytest.raises(CRMError) as exc_info:
                await job_nimbus_provider.get_job("test_job")

            assert exc_info.value.error_code == "HTTP_ERROR"

    @pytest.mark.asyncio
    async def test_generic_error_handling(self, job_nimbus_provider):
        """Test generic exception handling."""
        with patch.object(job_nimbus_provider, "_make_request", side_effect=Exception("Network error")):
            with pytest.raises(CRMError) as exc_info:
                await job_nimbus_provider.get_job("test_job")

            assert exc_info.value.error_code == "UNKNOWN_ERROR"
            assert "Network error" in str(exc_info.value)
