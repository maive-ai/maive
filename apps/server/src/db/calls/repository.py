"""
Repository for call database operations.

Provides CRUD operations for Call records using SQLAlchemy async sessions.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.voice_ai.constants import CallStatus, VoiceAIProvider
from src.db.calls.model import Call
from src.utils.logger import logger


class CallRepository:
    """Repository for managing call records in the database."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create_call(
        self,
        user_id: str,
        call_id: str,
        project_id: str,
        status: CallStatus,
        provider: VoiceAIProvider,
        phone_number: str,
        started_at: datetime,
        listen_url: str | None = None,
        provider_data: dict[str, Any] | None = None,
        transcript: list[dict[str, Any]] | None = None,
    ) -> Call:
        """
        Create a new call record.

        Args:
            user_id: Cognito user ID
            call_id: Provider call ID
            project_id: Project/Job ID
            status: Initial call status
            provider: Voice AI provider
            phone_number: Phone number called
            started_at: Call start timestamp
            listen_url: WebSocket URL for listening (optional)
            provider_data: Raw provider data (optional)
            transcript: Initial transcript messages (optional)

        Returns:
            Call: Created call record

        Raises:
            Exception: If creation fails
        """
        call = Call.from_active_call_state(
            user_id=user_id,
            call_id=call_id,
            project_id=project_id,
            status=status,
            provider=provider,
            phone_number=phone_number,
            started_at=started_at,
            listen_url=listen_url,
            provider_data=provider_data,
        )

        if transcript is not None:
            call.transcript = transcript

        self.session.add(call)
        await self.session.flush()  # Get the ID without committing
        await self.session.refresh(call)

        logger.info(
            f"[CallRepository] Created call record: id={call.id}, call_id={call_id}, user_id={user_id}"
        )
        return call

    async def get_active_call(self, user_id: str) -> Call | None:
        """
        Get the active call for a user.

        Args:
            user_id: Cognito user ID

        Returns:
            Call | None: Active call record if exists, None otherwise
        """
        stmt = (
            select(Call)
            .where(Call.user_id == user_id)
            .where(Call.is_active == True)  # noqa: E712
            .order_by(desc(Call.started_at))
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_call_by_call_id(self, call_id: str) -> Call | None:
        """
        Get a call by its provider call ID.

        Args:
            call_id: Provider call ID

        Returns:
            Call | None: Call record if found, None otherwise
        """
        stmt = select(Call).where(Call.call_id == call_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_call_status(
        self,
        call_id: str,
        status: CallStatus,
        provider_data: dict[str, Any] | None = None,
    ) -> Call | None:
        """
        Update the status of a call.

        Args:
            call_id: Provider call ID
            status: New call status
            provider_data: Updated provider data (optional)

        Returns:
            Call | None: Updated call record if found, None otherwise
        """
        call = await self.get_call_by_call_id(call_id)
        if not call:
            logger.warning(
                f"[CallRepository] Cannot update status: call {call_id} not found"
            )
            return None

        call.status = status.value
        call.updated_at = datetime.now(UTC)

        if provider_data is not None:
            call.provider_data = provider_data

        await self.session.flush()
        await self.session.refresh(call)

        logger.info(
            f"[CallRepository] Updated call status: call_id={call_id}, status={status.value}"
        )
        return call

    async def end_call(
        self,
        call_id: str,
        final_status: CallStatus,
        ended_at: datetime | None = None,
        provider_data: dict[str, Any] | None = None,
        analysis_data: dict[str, Any] | None = None,
        transcript: list[dict[str, Any]] | None = None,
    ) -> Call | None:
        """
        Mark a call as ended and inactive.

        Args:
            call_id: Provider call ID
            final_status: Final call status
            ended_at: Call end timestamp (defaults to now)
            provider_data: Final provider data (optional)
            analysis_data: Structured analysis results (optional)
            transcript: Final transcript messages (optional)

        Returns:
            Call | None: Updated call record if found, None otherwise
        """
        call = await self.get_call_by_call_id(call_id)
        if not call:
            logger.warning(
                f"[CallRepository] Cannot end call: call {call_id} not found"
            )
            return None

        call.status = final_status.value
        call.is_active = False
        call.ended_at = ended_at or datetime.now(UTC)
        call.updated_at = datetime.now(UTC)

        if provider_data is not None:
            call.provider_data = provider_data

        if analysis_data is not None:
            call.analysis_data = analysis_data

        if transcript is not None:
            call.transcript = transcript

        await self.session.flush()
        await self.session.refresh(call)

        logger.info(
            f"[CallRepository] Ended call: call_id={call_id}, status={final_status.value}"
        )
        return call

    async def remove_active_call(self, user_id: str) -> bool:
        """
        Remove active status from user's current call.

        This marks the user's active call as inactive without setting ended_at.
        Useful for cleanup when call state is uncertain.

        Args:
            user_id: Cognito user ID

        Returns:
            bool: True if a call was updated, False otherwise
        """
        stmt = (
            update(Call)
            .where(Call.user_id == user_id)
            .where(Call.is_active == True)  # noqa: E712
            .values(is_active=False, updated_at=datetime.now(UTC))
        )

        result = await self.session.execute(stmt)
        updated_count = result.rowcount

        if updated_count > 0:
            logger.info(
                f"[CallRepository] Removed active call for user {user_id} ({updated_count} records)"
            )
            return True

        logger.debug(f"[CallRepository] No active call found for user {user_id}")
        return False

    async def get_call_history(
        self,
        user_id: str | None = None,
        project_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Call]:
        """
        Get call history with optional filtering.

        Args:
            user_id: Filter by user ID (optional)
            project_id: Filter by project ID (optional)
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            list[Call]: List of call records, ordered by start time (newest first)
        """
        stmt = select(Call).order_by(desc(Call.started_at))

        if user_id:
            stmt = stmt.where(Call.user_id == user_id)
        if project_id:
            stmt = stmt.where(Call.project_id == project_id)

        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        calls = list(result.scalars().all())

        logger.debug(
            f"[CallRepository] Retrieved {len(calls)} call records "
            f"(user_id={user_id}, project_id={project_id})"
        )
        return calls

    async def get_project_calls(self, project_id: str, limit: int = 50) -> list[Call]:
        """
        Get all calls for a specific project.

        Args:
            project_id: Project/Job ID
            limit: Maximum number of records to return

        Returns:
            list[Call]: List of call records for the project
        """
        return await self.get_call_history(project_id=project_id, limit=limit)
