"""Tests for CRM API routes to verify correct serialization."""

import os

import pytest
from fastapi.testclient import TestClient

from src.auth.dependencies import get_current_user
from src.auth.schemas import Role, User
from src.main import app

# Set CRM provider to mock for tests
os.environ["CRM_PROVIDER"] = "mock"


def mock_get_current_user_func():
    """Mock function that returns a test user."""
    return User(id="test-user-123", email="test@example.com", role=Role.ADMIN)


@pytest.fixture
def client():
    """Create a test client with mocked authentication."""
    # Override the dependency
    app.dependency_overrides[get_current_user] = mock_get_current_user_func

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_auth_token():
    """Return a mock token (not actually validated)."""
    return "mock-token"


class TestCRMRoutes:
    """Test suite for CRM API routes."""

    def test_get_all_projects(self, client, mock_auth_token):
        """Test getting all projects returns correct structure."""
        response = client.get(
            "/api/crm/projects/status",
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "projects" in data
        assert "total_count" in data
        assert "provider" in data
        assert data["provider"] == "mock"
        assert data["total_count"] > 0

    def test_get_single_project_with_provider_data(self, client, mock_auth_token):
        """Test getting a single project returns provider_data correctly."""
        project_id = "st_001"
        response = client.get(
            f"/api/crm/projects/{project_id}/status",
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check basic structure
        assert data["project_id"] == project_id
        assert "status" in data
        assert "provider_data" in data
        assert data["provider_data"] is not None

        # Check provider_data has customer information
        provider_data = data["provider_data"]
        assert "customerName" in provider_data
        assert "address" in provider_data
        assert "phone" in provider_data

        # Verify data is not empty
        assert provider_data["customerName"] == "John Smith"
        assert "123 Main St" in provider_data["address"]

        print(f"\n✓ API returned correct provider_data for {project_id}")
        print(f"✓ Customer: {provider_data['customerName']}")
        print(f"✓ Address: {provider_data['address']}")

    def test_project_id_with_quotes_should_404(self, client, mock_auth_token):
        """Test that a project ID with quotes should return 404 (not found)."""
        # This simulates what might be happening in the frontend
        project_id_with_quotes = '"st_001"'  # Has quotes around it
        response = client.get(
            f"/api/crm/projects/{project_id_with_quotes}/status",
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        # Should return 404 because "st_001" with quotes doesn't match st_001
        assert response.status_code == 404

        print("\n✓ Project ID with quotes correctly returns 404")

    def test_all_projects_have_provider_data(self, client, mock_auth_token):
        """Test that all projects in the list have provider_data."""
        response = client.get(
            "/api/crm/projects/status",
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        projects_without_data = []
        projects_without_customer = []

        for project in data["projects"]:
            if not project.get("provider_data"):
                projects_without_data.append(project["project_id"])
            elif "customerName" not in project["provider_data"]:
                projects_without_customer.append(project["project_id"])

        assert len(projects_without_data) == 0, (
            f"Projects without provider_data: {projects_without_data}"
        )
        assert len(projects_without_customer) == 0, (
            f"Projects without customerName: {projects_without_customer}"
        )

        print(
            f"\n✓ All {len(data['projects'])} projects have provider_data with customerName"
        )
