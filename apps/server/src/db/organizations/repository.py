"""Repository for organization database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.organizations.model import Organization as OrganizationModel
from src.db.organizations.schemas import OrganizationCreate, OrganizationUpdate


class OrganizationRepository:
    """Repository for managing organizations in the database."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.

        Args:
            session: Async database session
        """
        self.session = session

    async def create(self, data: OrganizationCreate) -> OrganizationModel:
        """
        Create a new organization.

        Args:
            data: Organization creation data

        Returns:
            Created organization model
        """
        org = OrganizationModel(name=data.name)
        self.session.add(org)
        await self.session.flush()
        await self.session.refresh(org)
        return org

    async def get_by_id(self, org_id: str) -> OrganizationModel | None:
        """
        Get an organization by ID.

        Args:
            org_id: Organization UUID

        Returns:
            Organization model or None if not found
        """
        result = await self.session.execute(
            select(OrganizationModel).where(OrganizationModel.id == org_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, org_id: str, data: OrganizationUpdate
    ) -> OrganizationModel | None:
        """
        Update an organization.

        Args:
            org_id: Organization UUID
            data: Update data

        Returns:
            Updated organization or None if not found
        """
        org = await self.get_by_id(org_id)
        if not org:
            return None

        if data.name is not None:
            org.name = data.name

        await self.session.flush()
        await self.session.refresh(org)
        return org

    async def delete(self, org_id: str) -> bool:
        """
        Delete an organization.

        Args:
            org_id: Organization UUID

        Returns:
            True if deleted, False if not found
        """
        org = await self.get_by_id(org_id)
        if not org:
            return False

        await self.session.delete(org)
        await self.session.flush()
        return True

    async def list_all(
        self, limit: int = 100, offset: int = 0
    ) -> list[OrganizationModel]:
        """
        List all organizations with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of organization models
        """
        result = await self.session.execute(
            select(OrganizationModel).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
