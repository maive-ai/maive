"""JobNimbus MCP Server for CRM job search and retrieval."""

import textwrap
from io import BytesIO
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from src.ai.openai.exceptions import OpenAIError
from src.ai.providers.openai import OpenAIProvider
from src.config import get_app_settings
from src.integrations.crm.base import CRMError
from src.integrations.crm.providers.job_nimbus.provider import JobNimbusProvider
from src.utils.logger import logger

# Initialize JobNimbus provider directly (not through factory)
_provider = JobNimbusProvider()

# Initialize OpenAI provider for mini-agent file analysis
_openai_provider = OpenAIProvider()


async def _analyze_job_files_with_mini_agent(
    job_id: str,
    analysis_prompt: str,
    file_filter: str = "all",
    specific_file_id: str | None = None,
) -> str:
    """Execute file analysis mini-agent.

    Downloads files from JobNimbus, uploads to OpenAI, makes a separate detailed
    analysis API call, and returns the summary for the main agent to use.

    Args:
        job_id: JobNimbus job ID
        analysis_prompt: User's question about the files
        file_filter: Type filter - "all", "images", or "pdfs"
        specific_file_id: If provided, only analyze this specific file

    Returns:
        Detailed text analysis from mini-agent

    Raises:
        OpenAIError: If file analysis fails
    """
    try:
        logger.info(
            "[Mini-Agent] Analyzing files",
            file_filter=file_filter,
            job_id=job_id,
            specific_file_id=specific_file_id,
        )

        # Get files - either specific file or filtered list
        if specific_file_id:
            # Get specific file by ID
            file = await _provider.get_specific_job_file(job_id, specific_file_id)
            if not file:
                return f"File {specific_file_id} not found in job {job_id}"
            files = [file]
        else:
            # Get filtered files
            files = await _provider.get_job_files(job_id, file_filter)
            if not files:
                return f"No {file_filter} files found for job {job_id}"

        logger.info("[Mini-Agent] Found files to analyze", count=len(files))

        # Upload each file to OpenAI with appropriate purpose
        file_attachments = []  # List of (file_id, filename, is_image) tuples
        for file_meta in files:
            try:
                # Download from JobNimbus
                file_content, filename, content_type = await _provider.download_file(
                    file_meta.id,
                    filename=file_meta.filename,
                    content_type=file_meta.content_type,
                )

                # Determine if file is an image or document
                is_image = content_type.startswith("image/")
                purpose = "vision" if is_image else "user_data"

                # Upload to OpenAI with appropriate purpose
                file_handle = BytesIO(file_content)
                openai_file_id = await _openai_provider.upload_file_from_handle(
                    file_handle, filename, purpose=purpose
                )
                file_attachments.append((openai_file_id, filename, is_image))
                logger.info(
                    "[Mini-Agent] Uploaded file",
                    file_name=filename,
                    openai_file_id=openai_file_id,
                    purpose=purpose,
                )

            except Exception as e:
                logger.warning(
                    "[Mini-Agent] Failed to upload file",
                    file_name=file_meta.filename,
                    error=str(e),
                )
                continue

        if not file_attachments:
            return "Failed to upload any files for analysis"

        # Build detailed mini-agent prompt
        files_list = "\n".join([f"- {name}" for _, name, _ in file_attachments])
        detailed_prompt = textwrap.dedent(f"""
            You are analyzing files from a roofing job. Describe each file in detail:
            
            For images: Describe roof condition, visible damage, materials, colors, angles, weather conditions, etc.
            For PDFs: Summarize key information - totals, line items, terms, dates, signatures, etc.
            
            Files attached:
            {files_list}
            
            Question to answer: {analysis_prompt}
            
            Provide comprehensive detail about each file to help answer the question.
        """).strip()

        logger.info(
            "[Mini-Agent] Making analysis call", file_count=len(file_attachments)
        )

        # Make mini-agent API call with reasoning for faster analysis
        # Pass file attachments with type information (input_image vs input_file)
        result = await _openai_provider.generate_content(
            prompt=detailed_prompt,
            file_attachments=file_attachments,  # List of (file_id, filename, is_image)
            model=_openai_provider.settings.model_name,
        )

        logger.info("[Mini-Agent] Analysis complete", char_count=len(result.text))
        logger.info("[Mini-Agent] Analysis result", preview=result.text[:500])
        return result.text

    except Exception as e:
        logger.error("[Mini-Agent] File analysis failed", error=str(e))
        raise OpenAIError(f"File analysis failed: {e}")


# Create MCP server instance with optional auth
settings = get_app_settings()
auth = None
if settings.mcp_auth_token:
    # Use StaticTokenVerifier for simple bearer token authentication
    auth = StaticTokenVerifier(
        tokens={
            settings.mcp_auth_token: {
                "sub": "openai-integration",
                "aud": "maive-mcp-server",
                "client_id": "openai-client",
                "scopes": [],  # No scope restrictions
            }
        }
    )
mcp = FastMCP(name="JobNimbus CRM", auth=auth)


@mcp.tool
async def get_job(job_id: str) -> dict[str, Any]:
    """Get a specific job by ID from JobNimbus.

    Args:
        job_id: The JobNimbus job ID (JNID) to retrieve

    Returns:
        Dictionary with job details and notes. Key fields include:
        - id (str): Job identifier
        - name (str): Job name/title
        - number (str): Job number
        - status (str): Current status (e.g., "Writing Estimate", "In Progress")
        - workflow_type (str): Job type (e.g., "Retail", "Insurance")
        - description (str): Job description/details
        - customer_id (str): Customer contact ID
        - customer_name (str): Customer name
        - address_line1, address_line2, city, state, postal_code, country (str): Job location
        - created_at, updated_at (str): Timestamps in ISO format
        - sales_rep_id, sales_rep_name (str): Sales representative info
        - notes (list[dict]): List of notes/activities, each containing:
            - id (str): Note identifier
            - text (str): Note content
            - created_by_name (str): Author name
            - created_at (str): Creation timestamp
            - updated_at (str): Update timestamp
        - provider_data (dict): Additional provider-specific fields like claim_number,
          insurance_company, related contacts, geo coordinates, etc.

    Raises:
        Exception: If the job is not found or an error occurs
    """
    try:
        logger.info("[MCP JobNimbus] Getting job", job_id=job_id)
        job = await _provider.get_job(job_id)

        result = job.model_dump()
        logger.info("[MCP JobNimbus] Successfully retrieved job", job_id=job_id)
        return result

    except CRMError as e:
        logger.error(
            "[MCP JobNimbus] CRM error getting job",
            job_id=job_id,
            error_message=e.message,
        )
        raise Exception(f"Failed to get job: {e.message}")
    except Exception as e:
        logger.error(
            "[MCP JobNimbus] Unexpected error getting job", job_id=job_id, error=str(e)
        )
        raise Exception(f"Failed to get job: {str(e)}")


@mcp.tool
async def get_all_jobs(
    customer_name: str | None = None,
    job_id: str | None = None,
    address: str | None = None,
    claim_number: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Search for jobs in JobNimbus with various filters.

    Use this tool to find jobs based on customer information, job details, or status.
    You can combine multiple search criteria to narrow down results.

    Args:
        customer_name: Search by customer name (partial match, case-insensitive)
        job_id: Search by exact job ID
        address: Search by address (partial match)
        claim_number: Search by insurance claim number (exact match)
        status: Filter by job status (e.g., "In Progress", "Scheduled", "Completed")
        page: Page number for pagination (default: 1)
        page_size: Number of results per page (default: 10, max: 50)

    Returns:
        Dictionary containing:
        - jobs (list[dict]): List of matching jobs, each with same structure as get_job()
          (includes id, name, number, status, customer info, address, dates, notes, etc.)
        - total_count (int): Total number of matching jobs
        - page (int): Current page number
        - page_size (int): Number of results per page
        - has_more (bool): Whether there are more results available

    Examples:
        - Search by customer name: search_jobs(customer_name="John Smith")
        - Search by job ID: search_jobs(job_id="jn_12345")
        - Search by status: search_jobs(status="In Progress")
        - Combine filters: search_jobs(customer_name="Smith", status="Completed")
    """
    try:
        logger.info(
            "[MCP JobNimbus] Searching jobs with filters",
            customer_name=customer_name,
            job_id=job_id,
            address=address,
            claim_number=claim_number,
            status=status,
        )

        # Build filters dict for provider
        filters = {}
        if customer_name:
            filters["customer_name"] = customer_name
        if job_id:
            filters["job_id"] = job_id
        if address:
            filters["address"] = address
        if claim_number:
            filters["claim_number"] = claim_number
        if status:
            filters["status"] = status

        # Delegate to provider (handles all filtering logic)
        job_list = await _provider.get_all_jobs(
            filters=filters if filters else None,
            page=page,
            page_size=page_size,
        )

        # Convert to dict format for MCP response
        result = {
            "jobs": [job.model_dump() for job in job_list.jobs],
            "total_count": job_list.total_count,
            "page": job_list.page,
            "page_size": job_list.page_size,
            "has_more": job_list.has_more,
        }

        logger.info(
            "[MCP JobNimbus] Search returned jobs",
            returned_count=len(job_list.jobs),
            total_count=job_list.total_count,
        )
        return result

    except CRMError as e:
        logger.error(
            "[MCP JobNimbus] CRM error searching jobs", error_message=e.message
        )
        raise Exception(f"Failed to search jobs: {e.message}")
    except Exception as e:
        logger.error("[MCP JobNimbus] Unexpected error searching jobs", error=str(e))
        raise Exception(f"Failed to search jobs: {str(e)}")


@mcp.tool
async def list_job_files(job_id: str) -> dict[str, Any]:
    """List all files attached to a job without uploading them.

    Returns file metadata including IDs, names, types, sizes, and descriptions.

    File types you'll typically see:
    - Images (JPEG, PNG): Roof inspection photos, damage photos, before/after photos
    - PDFs: Estimates, invoices, contracts, work orders, insurance documents
    - Other documents: Material orders, agreements, specifications

    Use this tool first to see what files are available for a job, then use
    analyze_job_files to upload specific files or file types to OpenAI
    for detailed analysis.

    Args:
        job_id: The JobNimbus job ID (JNID)

    Returns:
        Dictionary containing:
        - count (int): Number of files
        - files (list[dict]): Array of file metadata objects, each with:
            - id (str): File identifier (use this with analyze_job_files)
            - filename (str): File name (e.g., "roof_estimate.pdf", "damage_photo.jpg")
            - content_type (str): MIME type (e.g., "application/pdf", "image/jpeg")
            - size (int): File size in bytes
            - record_type_name (str): File type category
            - description (str): File description if available
            - date_created (int): Creation timestamp
            - created_by_name (str): Uploader name
            - is_private (bool): Privacy flag

    Example:
        list_job_files(job_id="mhdn17a1ssizgvz8fo0h66r")
    """
    try:
        logger.info("[MCP JobNimbus] Listing files for job", job_id=job_id)
        files = await _provider.get_job_files(job_id)

        result = {
            "count": len(files),
            "files": [
                {
                    "id": f.id,
                    "filename": f.filename,
                    "content_type": f.content_type,
                    "size": f.size,
                    "record_type_name": f.record_type_name,
                    "description": f.description,
                    "date_created": f.date_created,
                    "created_by_name": f.created_by_name,
                    "is_private": f.is_private,
                }
                for f in files
            ],
        }

        logger.info(
            "[MCP JobNimbus] Found files for job", count=len(files), job_id=job_id
        )
        return result

    except CRMError as e:
        logger.error(
            "[MCP JobNimbus] CRM error listing files for job",
            job_id=job_id,
            error_message=e.message,
        )
        raise Exception(f"Failed to list files: {e.message}")
    except Exception as e:
        logger.error(
            "[MCP JobNimbus] Unexpected error listing files for job",
            job_id=job_id,
            error=str(e),
        )
        raise Exception(f"Failed to list files: {str(e)}")


@mcp.tool
async def analyze_job_files(
    job_id: str,
    analysis_prompt: str,
    file_filter: str = "all",
    specific_file_id: str | None = None,
) -> str:
    """Analyze files from a roofing job using specialized AI agent.

    This tool downloads files from JobNimbus, uploads them to OpenAI, and uses a
    specialized mini-agent to provide detailed analysis of the files. The mini-agent
    is instructed to describe images (roof photos) and PDFs (estimates, invoices) in
    comprehensive detail.

    IMPORTANT: Use specific_file_id when analyzing a single file. Use file_filter only
    when analyzing multiple files by type. Call list_job_files first to get file IDs.

    Args:
        job_id: The JobNimbus job ID (JNID)
        analysis_prompt: Specific question about the files (e.g., "What damage is visible?")
        file_filter: Filter by type - "all", "images", or "pdfs" (default: "all"). Ignored if specific_file_id provided.
        specific_file_id: If provided, only analyze this specific file by its ID (get from list_job_files)

    Returns:
        Detailed text analysis from the mini-agent describing each file and answering
        the question. Typically 1000-5000 characters of comprehensive detail.

    Examples:
        - Analyze specific file: analyze_job_files(job_id="mha5p15...", specific_file_id="mhb14k...", analysis_prompt="What are the contract terms?")
        - Analyze all images: analyze_job_files(job_id="mha5p15...", analysis_prompt="What roof damage is visible?", file_filter="images")
        - Analyze all PDFs: analyze_job_files(job_id="mha5p15...", analysis_prompt="What is the total cost?", file_filter="pdfs")
    """
    try:
        if specific_file_id:
            logger.info(
                "[MCP JobNimbus] Analyzing specific file for job",
                specific_file_id=specific_file_id,
                job_id=job_id,
            )
        else:
            logger.info(
                "[MCP JobNimbus] Analyzing files for job",
                file_filter=file_filter,
                job_id=job_id,
                analysis_prompt=analysis_prompt,
            )

        # Call local mini-agent handler
        result = await _analyze_job_files_with_mini_agent(
            job_id=job_id,
            analysis_prompt=analysis_prompt,
            file_filter=file_filter,
            specific_file_id=specific_file_id,
        )

        logger.info("[MCP JobNimbus] Analysis complete", char_count=len(result))
        return result

    except Exception as e:
        logger.error("[MCP JobNimbus] Error analyzing files", error=str(e))
        raise Exception(f"Failed to analyze files: {str(e)}")
