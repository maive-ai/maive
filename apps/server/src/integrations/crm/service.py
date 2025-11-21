"""
CRM service layer for business logic.

This module provides the business logic layer for CRM operations using
the universal interface that works across all CRM providers.
"""

from typing import Any

from src.ai.providers.factory import AIProviderType, create_ai_provider
from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.schemas import (
    Contact,
    ContactList,
    CRMErrorResponse,
    Job,
    JobList,
    Note,
    Project,
    ProjectList,
    ProjectSummary,
)
from src.utils.logger import logger


class CRMService:
    """Service class for CRM operations using the universal interface."""

    def __init__(self, crm_provider: CRMProvider):
        """
        Initialize the CRM service.

        Args:
            crm_provider: The CRM provider to use
        """
        self.crm_provider = crm_provider

    # ========================================================================
    # Job Methods
    # ========================================================================

    async def get_job(self, job_id: str) -> Job | CRMErrorResponse:
        """
        Get a specific job by ID.

        Args:
            job_id: The job identifier (string format)

        Returns:
            Job or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info("Getting job", job_id=job_id)
            result = await self.crm_provider.get_job(job_id)
            logger.info("Successfully retrieved job", job_id=job_id)
            return result
        except CRMError as e:
            logger.error(
                "CRM error getting job", job_id=job_id, error_message=e.message
            )
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error("Unexpected error getting job", job_id=job_id, error=str(e))
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, "provider_name", None),
            )

    async def get_all_jobs(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> JobList | CRMErrorResponse:
        """
        Get all jobs with optional filtering and pagination.

        Args:
            filters: Optional provider-specific filters
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            JobList or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info("Getting all jobs", page=page, page_size=page_size)
            result = await self.crm_provider.get_all_jobs(
                filters=filters,
                page=page,
                page_size=page_size,
            )
            logger.info("Successfully retrieved jobs", count=len(result.jobs))
            return result
        except CRMError as e:
            logger.error("CRM error getting all jobs", error_message=e.message)
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error("Unexpected error getting all jobs", error=str(e))
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, "provider_name", None),
            )

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs: Any,
    ) -> None | CRMErrorResponse:
        """
        Update the status of a job.

        Args:
            job_id: The job identifier
            status: The new status value
            **kwargs: Provider-specific optional parameters

        Returns:
            None on success, CRMErrorResponse on error
        """
        try:
            logger.info("Updating status for job", job_id=job_id, status=status)
            await self.crm_provider.update_job_status(
                job_id=job_id,
                status=status,
                **kwargs,
            )
            logger.info("Successfully updated status for job", job_id=job_id)
            return None
        except CRMError as e:
            logger.error(
                "CRM error updating job status", job_id=job_id, error_message=e.message
            )
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error(
                "Unexpected error updating job status", job_id=job_id, error=str(e)
            )
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, "provider_name", None),
            )

    # ========================================================================
    # Project Methods
    # ========================================================================

    async def get_project(self, project_id: str) -> Project | CRMErrorResponse:
        """
        Get a specific project by ID.

        Args:
            project_id: The project identifier (string format)

        Returns:
            Project or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info("Getting project", project_id=project_id)
            result = await self.crm_provider.get_project(project_id)
            logger.info("Successfully retrieved project", project_id=project_id)
            return result
        except CRMError as e:
            logger.error(
                "CRM error getting project",
                project_id=project_id,
                error_message=e.message,
            )
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error(
                "Unexpected error getting project", project_id=project_id, error=str(e)
            )
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, "provider_name", None),
            )

    async def get_all_projects(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ProjectList | CRMErrorResponse:
        """
        Get all projects with optional filtering and pagination.

        Args:
            filters: Optional provider-specific filters
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            ProjectList or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info("Getting all projects", page=page, page_size=page_size)
            result = await self.crm_provider.get_all_projects(
                filters=filters,
                page=page,
                page_size=page_size,
            )
            logger.info("Successfully retrieved projects", count=len(result.projects))
            return result
        except CRMError as e:
            logger.error("CRM error getting all projects", error_message=e.message)
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error("Unexpected error getting all projects", error=str(e))
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, "provider_name", None),
            )

    async def update_project_status(
        self,
        project_id: str,
        status: str,
        **kwargs: Any,
    ) -> None | CRMErrorResponse:
        """
        Update the status of a project.

        Args:
            project_id: The project identifier
            status: The new status value
            **kwargs: Provider-specific optional parameters

        Returns:
            None on success, CRMErrorResponse on error
        """
        try:
            logger.info(
                "Updating status for project", project_id=project_id, status=status
            )
            await self.crm_provider.update_project_status(
                project_id=project_id,
                status=status,
                **kwargs,
            )
            logger.info(
                "Successfully updated status for project", project_id=project_id
            )
            return None
        except CRMError as e:
            logger.error(
                "CRM error updating project status",
                project_id=project_id,
                error_message=e.message,
            )
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error(
                "Unexpected error updating project status",
                project_id=project_id,
                error=str(e),
            )
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, "provider_name", None),
            )

    async def generate_project_summary(
        self, project_id: str
    ) -> ProjectSummary | CRMErrorResponse:
        """
        Generate an AI summary for a project based on its notes.

        This method:
        1. Fetches the project with notes
        2. Analyzes notes using AI (OpenAI gpt-4o-mini via AIProvider)
        3. Returns a structured summary with:
           - Brief project status summary
           - Recent actions taken (2-3 bullet points)
           - Next steps (2-3 bullet points)

        Args:
            project_id: The project identifier

        Returns:
            ProjectSummary or CRMErrorResponse: The result of the operation
        """

        try:
            logger.info("Generating project summary", project_id=project_id)

            # Fetch project with notes
            project_result = await self.get_project(project_id)

            if isinstance(project_result, CRMErrorResponse):
                return project_result

            project = project_result

            # Check if project has notes
            if not project.notes or len(project.notes) == 0:
                logger.info(
                    "No notes available for project, returning empty summary",
                    project_id=project_id,
                )
                return ProjectSummary(
                    summary="No notes available for this project.",
                    recent_actions=[],
                    next_steps=["Add project notes to track progress."],
                )

            # Build notes context for AI (sort by created_at descending, most recent first)
            sorted_notes = sorted(
                project.notes, key=lambda n: n.created_at, reverse=True
            )
            notes_text = "\n".join(
                [
                    f"- {note.text} (created: {note.created_at})"
                    for note in sorted_notes[:10]  # Limit to 10 most recent notes
                ]
            )

            # Build prompt
            prompt = f"""Analyze these project notes and provide a concise summary:

Project: {project.name or "Unknown"}
Status: {project.status}
Claim Number: {project.claim_number or "N/A"}
Customer: {project.customer_name or "Unknown"}

Recent Notes (most recent first):
{notes_text}

Provide:
1. A very concise one-sentence summary of the current project status
2. Max 2 recent actions taken (as bullet points, sorted by most recent first). Lead each bullet point with a date if available.
3. Single bullet point next step or recommendation

Be concise and focus on the most important information."""

            # Generate structured summary using AI provider
            ai_provider = create_ai_provider(provider_type=AIProviderType.OPENAI)
            summary_result = await ai_provider.generate_structured_content(
                prompt=prompt,
                response_schema=ProjectSummary,
                model="gpt-4o-mini",
                temperature=0.7,
                max_output_tokens=500,
            )

            if summary_result is None:
                logger.error(
                    "AI provider returned None for project summary",
                    project_id=project_id,
                )
                return CRMErrorResponse(
                    error="Failed to generate project summary",
                    error_code="AI_GENERATION_ERROR",
                    provider=getattr(self.crm_provider, "provider_name", None),
                )

            logger.info("Successfully generated project summary", project_id=project_id)
            return summary_result

        except CRMError as e:
            logger.error(
                "CRM error generating project summary",
                project_id=project_id,
                error_message=e.message,
            )
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error(
                "Unexpected error generating project summary",
                project_id=project_id,
                error=str(e),
            )
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, "provider_name", None),
            )

    # ========================================================================
    # Contact Methods
    # ========================================================================

    async def get_contact(self, contact_id: str) -> Contact | CRMErrorResponse:
        """
        Get a specific contact by ID.

        Args:
            contact_id: The contact identifier (string format)

        Returns:
            Contact or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info("Getting contact", contact_id=contact_id)
            result = await self.crm_provider.get_contact(contact_id)
            logger.info("Successfully retrieved contact", contact_id=contact_id)
            return result
        except CRMError as e:
            logger.error(
                "CRM error getting contact",
                contact_id=contact_id,
                error_message=e.message,
            )
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error(
                "Unexpected error getting contact", contact_id=contact_id, error=str(e)
            )
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, "provider_name", None),
            )

    async def get_all_contacts(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ContactList | CRMErrorResponse:
        """
        Get all contacts with optional filtering and pagination.

        Args:
            filters: Optional provider-specific filters
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            ContactList or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info("Getting all contacts", page=page, page_size=page_size)
            result = await self.crm_provider.get_all_contacts(
                filters=filters,
                page=page,
                page_size=page_size,
            )
            logger.info("Successfully retrieved contacts", count=len(result.contacts))
            return result
        except CRMError as e:
            logger.error("CRM error getting all contacts", error_message=e.message)
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error("Unexpected error getting all contacts", error=str(e))
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, "provider_name", None),
            )

    # ========================================================================
    # Note Methods
    # ========================================================================

    async def add_note(
        self,
        entity_id: str,
        entity_type: str,
        text: str,
        **kwargs: Any,
    ) -> Note | CRMErrorResponse:
        """
        Add a note to an entity (job, contact, project, etc.).

        Args:
            entity_id: The entity identifier
            entity_type: The type of entity (e.g., "job", "contact", "project")
            text: The text content of the note
            **kwargs: Provider-specific optional parameters (e.g., pin_to_top)

        Returns:
            Note or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info("Adding note", entity_type=entity_type, entity_id=entity_id)
            result = await self.crm_provider.add_note(
                entity_id=entity_id,
                entity_type=entity_type,
                text=text,
                **kwargs,
            )
            logger.info(
                "Successfully added note", entity_type=entity_type, entity_id=entity_id
            )
            return result
        except CRMError as e:
            logger.error(
                "CRM error adding note",
                entity_type=entity_type,
                entity_id=entity_id,
                error_message=e.message,
            )
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error(
                "Unexpected error adding note",
                entity_type=entity_type,
                entity_id=entity_id,
                error=str(e),
            )
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, "provider_name", None),
            )
