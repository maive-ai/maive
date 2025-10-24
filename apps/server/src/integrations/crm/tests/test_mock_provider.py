"""Tests for Mock provider."""

import pytest

from src.integrations.crm.constants import Status
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.providers.mock.provider import MockProvider


@pytest.fixture
def mock_provider():
    """Create a Mock provider instance."""
    return MockProvider()


class TestMockProvider:
    """Test suite for Mock provider."""

    @pytest.mark.asyncio
    async def test_get_all_project_statuses(self, mock_provider):
        """Test getting all project statuses returns correct data structure."""
        result = await mock_provider.get_all_project_statuses()

        # Check response structure
        assert result.total_count > 0
        assert result.provider == CRMProviderEnum.MOCK
        assert len(result.projects) == result.total_count
        assert len(result.projects) > 0

    @pytest.mark.asyncio
    async def test_project_has_provider_data(self, mock_provider):
        """Test that projects have provider_data with customer information."""
        result = await mock_provider.get_all_project_statuses()

        # Get first project
        first_project = result.projects[0]

        # Check project structure
        assert first_project.project_id is not None
        assert first_project.status in [s.value for s in Status]
        assert first_project.claim_status in [s.value for s in ClaimStatus]
        assert first_project.provider_data is not None
        assert isinstance(first_project.provider_data, dict)

        # Check provider_data has customer information
        provider_data = first_project.provider_data
        assert "customerName" in provider_data
        assert "address" in provider_data
        assert "phone" in provider_data

        # Verify data is not empty/default
        assert provider_data["customerName"] != ""
        assert provider_data["address"] != ""
        assert provider_data["phone"] != ""

        print(f"\n✓ First project ID: {first_project.project_id}")
        print(f"✓ Customer Name: {provider_data['customerName']}")
        print(f"✓ Address: {provider_data['address']}")
        print(f"✓ Phone: {provider_data['phone']}")

    @pytest.mark.asyncio
    async def test_get_single_project_status(self, mock_provider):
        """Test getting a single project by ID."""
        # Use a known project ID from mock data
        project_id = "st_001"

        result = await mock_provider.get_project_status(project_id)

        # Check response structure
        assert result.project_id == project_id
        assert result.status in [s.value for s in Status]
        assert result.provider == CRMProviderEnum.MOCK
        assert result.provider_data is not None

        # Check provider_data has customer information
        provider_data = result.provider_data
        assert "customerName" in provider_data
        assert "address" in provider_data
        assert "phone" in provider_data
        assert "email" in provider_data

        # Verify this is John Smith's project (from data.py)
        assert provider_data["customerName"] == "John Smith"
        assert "123 Main St" in provider_data["address"]

        print(f"\n✓ Single project retrieved: {project_id}")
        print(f"✓ Customer: {provider_data['customerName']}")
        print(f"✓ Address: {provider_data['address']}")

    @pytest.mark.asyncio
    async def test_all_projects_have_complete_provider_data(self, mock_provider):
        """Test that all projects have complete provider_data."""
        result = await mock_provider.get_all_project_statuses()

        projects_without_data = []
        projects_without_customer_name = []

        for project in result.projects:
            if not project.provider_data:
                projects_without_data.append(project.project_id)
            elif "customerName" not in project.provider_data:
                projects_without_customer_name.append(project.project_id)

        # All projects should have provider_data
        assert len(projects_without_data) == 0, (
            f"Projects without provider_data: {projects_without_data}"
        )

        # All projects should have customerName in provider_data
        assert len(projects_without_customer_name) == 0, (
            f"Projects without customerName: {projects_without_customer_name}"
        )

        print(f"\n✓ All {len(result.projects)} projects have complete provider_data")

    @pytest.mark.asyncio
    async def test_provider_data_contains_contact_info(self, mock_provider):
        """Test that provider_data contains contact information structures."""
        result = await mock_provider.get_all_project_statuses()

        # Find a project with insurance claim (should have contact info)
        project_with_claim = None
        for project in result.projects:
            if project.provider_data and project.provider_data.get("claimNumber"):
                project_with_claim = project
                break

        assert project_with_claim is not None, (
            "Should have at least one project with a claim"
        )

        provider_data = project_with_claim.provider_data

        # Check for insurance agency contact
        assert "insuranceAgency" in provider_data
        assert "insuranceAgencyContact" in provider_data

        if provider_data["insuranceAgencyContact"]:
            contact = provider_data["insuranceAgencyContact"]
            assert "name" in contact
            assert "phone" in contact
            assert "email" in contact

            print(
                f"\n✓ Project {project_with_claim.project_id} has complete contact info"
            )
            print(f"✓ Insurance Agency: {provider_data['insuranceAgency']}")
            print(f"✓ Contact: {contact['name']}")

    @pytest.mark.asyncio
    async def test_provider_data_json_serializable(self, mock_provider):
        """Test that provider_data can be JSON serialized (important for API responses)."""
        import json

        result = await mock_provider.get_all_project_statuses()
        first_project = result.projects[0]

        # Should not raise an exception
        try:
            json_str = json.dumps(first_project.provider_data)
            assert len(json_str) > 0

            # Should be able to parse it back
            parsed = json.loads(json_str)
            assert parsed["customerName"] == first_project.provider_data["customerName"]

            print("\n✓ provider_data is JSON serializable")
            print(f"✓ JSON length: {len(json_str)} bytes")
        except (TypeError, ValueError) as e:
            pytest.fail(f"provider_data is not JSON serializable: {e}")
