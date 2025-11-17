"""Service layer for user management."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.organizations.model import Organization
from src.db.organizations.repository import OrganizationRepository
from src.db.organizations.schemas import OrganizationCreate
from src.db.users.model import User


class UserService:
    """Service for managing users and their organization relationships."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the service.

        Args:
            session: Async database session
        """
        self.session = session
        self.org_repository = OrganizationRepository(session)

    async def get_or_create_user(
        self, user_id: str, email: str | None = None
    ) -> tuple[User, Organization]:
        """
        Get or create a user and ensure they have an organization.

        This is the main entry point for user authentication flow.
        - If user exists, return their existing user and org
        - If user doesn't exist, create user and org

        Args:
            user_id: Cognito user ID (sub claim)
            email: User email address (required for new users, optional for existing)

        Returns:
            Tuple of (User model, Organization model)

        Raises:
            ValueError: If email is None and user doesn't exist
        """
        # Check if user already exists
        result = await self.session.execute(select(User).where(User.id == user_id))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # User exists, fetch their organization
            org_result = await self.session.execute(
                select(Organization).where(
                    Organization.id == existing_user.organization_id
                )
            )
            org = org_result.scalar_one()
            return existing_user, org

        # User doesn't exist, create user and org
        if not email:
            raise ValueError(f"Email required to create new user {user_id}")

        return await self._create_user_and_org(user_id, email)

    async def _create_user_and_org(
        self, user_id: str, email: str
    ) -> tuple[User, Organization]:
        """
        Create a new user and organization.

        Args:
            user_id: Cognito user ID
            email: User email address

        Returns:
            Tuple of (User model, Organization model)
        """
        # Extract org name from email domain
        domain = email.split("@")[1].lower()
        org_name = self._extract_org_name_from_domain(domain)

        # Create organization
        org_data = OrganizationCreate(name=org_name)
        org = await self.org_repository.create(org_data)

        # Create user
        user = User(
            id=user_id,
            email=email,
            organization_id=org.id,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        return user, org

    def _extract_org_name_from_domain(self, domain: str) -> str:
        """
        Extract organization name from email domain.

        Examples:
            "robinhoodroofingutah.com" -> "Robinhoodroofingutah"
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

        # Simple capitalization
        return name_part.capitalize()
