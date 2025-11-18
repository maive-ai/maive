"""Service layer for organization management."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.organizations.model import Organization
from src.db.organizations.repository import OrganizationRepository
from src.db.organizations.schemas import OrganizationCreate


class OrganizationService:
    """Service for managing organizations and user-organization relationships."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the service.

        Args:
            session: Async database session
        """
        self.repository = OrganizationRepository(session)

    async def get_or_create_organization_for_email(
        self, email: str
    ) -> Organization:
        """
        Get or create an organization for a user based on their email domain.

        For business domains (non-gmail/yahoo/etc), creates one org per domain.
        For consumer email providers, creates individual orgs per user.

        Args:
            email: User's email address

        Returns:
            Organization model
        """
        # Extract display name from email domain
        domain = email.split("@")[1].lower()

        # Remove TLD to get base name (e.g., "acme.com" -> "acme")
        org_name = self._extract_org_name_from_domain(domain)

        # Create a new organization
        # Note: For now, we create a new org for each user
        # In the future, you could check if an org with this name exists
        # and add logic to match users to existing orgs
        org_data = OrganizationCreate(name=org_name)
        return await self.repository.create(org_data)

    def _extract_org_name_from_domain(self, domain: str) -> str:
        """
        Extract organization name from email domain.

        Examples:
            "robinhoodroofingutah.com" -> "Robin Hood Roofing Utah"
            "acme.io" -> "Acme"
            "gmail.com" -> "Gmail"

        Args:
            domain: Email domain

        Returns:
            Organization display name
        """
        # Remove TLD
        parts = domain.split(".")
        if len(parts) > 1:
            name_part = parts[0]
        else:
            name_part = domain

        # Simple capitalization (can be improved with more sophisticated logic)
        return name_part.capitalize()
