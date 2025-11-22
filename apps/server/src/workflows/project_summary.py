"""
Project summary generation workflow.

This workflow generates AI-powered summaries of projects based on their notes.
"""

import textwrap

from src.ai.providers.factory import AIProviderType, create_ai_provider
from src.integrations.crm.schemas import CRMErrorResponse
from src.integrations.crm.service import CRMService
from src.utils.logger import logger
from src.workflows.schemas import ProjectSummary


class ProjectSummaryWorkflow:
    """Workflow for generating project summaries using AI."""

    def __init__(self, crm_service: CRMService):
        """
        Initialize the project summary workflow.

        Args:
            crm_service: CRM service instance for fetching project data
        """
        self.crm_service = crm_service

    async def generate_project_summary(
        self, project_id: str
    ) -> ProjectSummary | CRMErrorResponse:
        """
        Generate an AI summary for a project based on its notes.

        This workflow:
        1. Fetches the project with notes from CRM
        2. Analyzes notes using AI (OpenAI gpt-4o-mini)
        3. Returns a structured summary with:
           - Brief project status summary
           - Recent actions taken
           - Next steps

        Args:
            project_id: The project identifier

        Returns:
            ProjectSummary or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info("Generating project summary", project_id=project_id)

            # Fetch project with notes
            project_result = await self.crm_service.get_project(project_id)

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
            prompt = textwrap.dedent(f"""\
                Analyze these project notes and provide a concise summary:

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

                Be concise and focus on the most important information.\
            """).strip()

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
                    provider=getattr(
                        self.crm_service.crm_provider, "provider_name", None
                    ),
                )

            logger.info("Successfully generated project summary", project_id=project_id)
            return summary_result

        except Exception as e:
            logger.error(
                "Unexpected error generating project summary",
                project_id=project_id,
                error=str(e),
            )
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_service.crm_provider, "provider_name", None),
            )
