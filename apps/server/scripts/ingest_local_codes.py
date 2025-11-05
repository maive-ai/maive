"""
Script for ingesting locally scraped building codes into the vector store.

This script reads JSON files from scripts/scraping/output/codes and ingests them
into OpenAI's vector store for RAG retrieval.

Usage (from apps/server directory with environment variables):
    cd apps/server

    # Ingest all codes from all states:
    esc run maive/maive-infra/david-dev -- uv run python scripts/ingest_local_codes.py ingest

    # Ingest codes from specific state:
    esc run maive/maive-infra/david-dev -- uv run python scripts/ingest_local_codes.py ingest --state ut

    # Ingest a specific city:
    esc run maive/maive-infra/david-dev -- uv run python scripts/ingest_local_codes.py ingest --state ut --city huntington

    # Show vector store status:
    esc run maive/maive-infra/david-dev -- uv run python scripts/ingest_local_codes.py status

    # Clear vector store:
    esc run maive/maive-infra/david-dev -- uv run python scripts/ingest_local_codes.py clear

    # Dry run (show what would be ingested without uploading):
    esc run maive/maive-infra/david-dev -- uv run python scripts/ingest_local_codes.py ingest --dry-run --state ut

Note: Replace 'david-dev' with your environment name (e.g., 'staging', 'prod')
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
# _project_root is apps/server
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

# _repo_root is /maive
_repo_root = _project_root.parent.parent

# _codes_dir is /maive/scripts/scraping/output/codes -> this is the database of codes
_codes_dir = _repo_root / "scripts" / "scraping" / "output" / "codes"


from pydantic import BaseModel, Field  # noqa: E402

from src.ai.rag.schemas import CodeDocumentMetadata, CodeType, JurisdictionLevel  # noqa: E402
from src.ai.rag.service import VectorStoreService  # noqa: E402
from src.utils.logger import logger  # noqa: E402


class ScrapedCodeMetadata(BaseModel):
    """Metadata from the scraped code JSON file."""

    scraped_at: str = Field(..., description="ISO timestamp when code was scraped")
    city_slug: str = Field(..., description="Slug identifier for the city")
    source_url: str | None = Field(None, description="Source URL of the code")
    scraper: str | None = Field(None, description="Name of scraper used")
    scraper_version: str | None = Field(None, description="Version of scraper")


class ScrapedCodeSection(BaseModel):
    """A section from the scraped code document."""

    value: str = Field(..., description="Section title/value")
    path: list[str] = Field(..., description="Hierarchical path to this section")
    url: str | None = Field(None, description="URL to this section if available")
    depth: int = Field(..., description="Depth in the hierarchy")
    has_children: bool = Field(..., description="Whether this section has children")
    html: str | None = Field(None, description="HTML content of the section")


class ScrapedCodeFile(BaseModel):
    """Structure of a scraped building code JSON file."""

    metadata: ScrapedCodeMetadata = Field(..., description="Metadata about the scrape")
    sections: list[ScrapedCodeSection] = Field(..., description="Code sections")


class IngestionError(BaseModel):
    """Error details for a failed document ingestion."""

    file: str = Field(..., description="Path to the file that failed")
    error: str = Field(..., description="Error message")


class IngestionSummary(BaseModel):
    """Summary of document ingestion results."""

    total_documents: int = Field(..., description="Total number of documents processed")
    successful: int = Field(default=0, description="Number of successfully ingested documents")
    failed: int = Field(default=0, description="Number of failed documents")
    errors: list[IngestionError] = Field(default_factory=list, description="List of errors")
    file_ids: list[str] = Field(default_factory=list, description="List of uploaded file IDs")


class LocalCodeIngestionService:
    """Service for ingesting locally scraped building codes."""

    def __init__(self):
        """Initialize the ingestion service."""
        self.vector_store = VectorStoreService()
        self.codes_dir = _codes_dir

    async def ingest_all_codes(
        self,
        state_filter: str | None = None,
        city_filter: str | None = None,
        dry_run: bool = False,
    ) -> IngestionSummary:
        """Ingest all building codes from the local directory.

        Args:
            state_filter: Optional state code to filter (e.g., "ut", "ks")
            city_filter: Optional city slug to filter (e.g., "huntington")
            dry_run: If True, parse and validate but don't upload

        Returns:
            IngestionSummary: Ingestion summary with counts and any errors
        """
        if not self.codes_dir.exists():
            logger.error(f"Codes directory not found: {self.codes_dir}")
            return IngestionSummary(
                total_documents=0,
                errors=[IngestionError(file="", error="Codes directory not found")],
            )

        # Find all JSON files
        json_files = self._find_json_files(state_filter, city_filter)

        if not json_files:
            logger.warning(
                f"No JSON files found in {self.codes_dir} "
                f"(state={state_filter}, city={city_filter})"
            )
            return IngestionSummary(total_documents=0)

        logger.info(f"Found {len(json_files)} code files to ingest")
        if dry_run:
            logger.info("DRY RUN MODE - No files will be uploaded")

        summary = IngestionSummary(total_documents=len(json_files))

        # Process each file
        for idx, json_file in enumerate(json_files, 1):
            logger.info(f"Processing {idx}/{len(json_files)}: {json_file.name}")
            try:
                # Parse the JSON file
                code_data = self._parse_code_file(json_file)

                # Extract metadata
                metadata = self._extract_metadata(code_data, json_file)

                # Convert sections to clean text
                content = self._sections_to_text(code_data.sections)

                # Generate filename
                filename = self._generate_filename(metadata)

                if dry_run:
                    # Check if file already exists (for informational purposes)
                    vector_store_id = await self.vector_store.get_or_create_vector_store()
                    existing_file_id = await self.vector_store.find_file_id_by_filename(
                        vector_store_id=vector_store_id,
                        filename=filename,
                    )
                    
                    action = "Replace" if existing_file_id else "Upload"
                    logger.info(
                        f"[DRY RUN] Would {action.lower()}: {metadata.jurisdiction_name} "
                        f"({len(content)} chars) as {filename}"
                    )
                    if existing_file_id:
                        logger.info(f"[DRY RUN] Would delete existing file {existing_file_id}")
                    
                    summary.successful += 1
                else:
                    # Check for existing file and delete if found
                    vector_store_id = await self.vector_store.get_or_create_vector_store()
                    existing_file_id = await self.vector_store.find_file_id_by_filename(
                        vector_store_id=vector_store_id,
                        filename=filename,
                    )

                    if existing_file_id:
                        logger.info(
                            f"Found existing file {existing_file_id} for {filename}, deleting..."
                        )
                        await self.vector_store.delete_file(existing_file_id)
                        logger.info(f"Deleted old file {existing_file_id}")

                    # Upload to vector store
                    file_id = await self.vector_store.upload_document(
                        content=content,
                        filename=filename,
                        metadata=metadata,
                    )

                    summary.successful += 1
                    summary.file_ids.append(file_id)

                    logger.info(
                        f"Ingested: {metadata.jurisdiction_name} ({file_id})"
                    )
                    
                    # Add delay between uploads to avoid rate limiting
                    if idx < len(json_files):  # Don't delay after last file
                        await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Failed to ingest {json_file.name}: {e}")
                summary.failed += 1
                summary.errors.append(
                    IngestionError(
                        file=str(json_file),
                        error=str(e),
                    )
                )

        logger.info(
            f"Ingestion {'simulation' if dry_run else 'complete'}: "
            f"{summary.successful}/{summary.total_documents} successful"
        )

        return summary

    def _find_json_files(
        self, state_filter: str | None, city_filter: str | None
    ) -> list[Path]:
        """Find all JSON files matching the filters.

        Args:
            state_filter: Optional state code to filter
            city_filter: Optional city slug to filter

        Returns:
            list[Path]: List of JSON file paths
        """
        json_files = []

        # If state filter provided, only search that directory
        if state_filter:
            state_dir = self.codes_dir / state_filter.lower()
            if not state_dir.exists():
                logger.warning(f"State directory not found: {state_dir}")
                return []

            state_dirs = [state_dir]
        else:
            # Search all state directories
            state_dirs = [d for d in self.codes_dir.iterdir() if d.is_dir()]

        for state_dir in state_dirs:
            for json_file in state_dir.glob("*.json"):
                # Skip if city filter doesn't match
                if city_filter:
                    # Load file to check city_slug from metadata
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        
                        file_city_slug = data.get("metadata", {}).get("city_slug", "")
                        
                        if file_city_slug != city_filter:
                            continue
                    except (json.JSONDecodeError, KeyError):
                        # If we can't parse, fall back to filename matching
                        logger.error(f"Failed to parse {json_file.name}, skipping file")
                        continue

                json_files.append(json_file)

        return sorted(json_files)

    def _parse_code_file(self, json_file: Path) -> ScrapedCodeFile:
        """Parse a JSON code file.

        Args:
            json_file: Path to JSON file

        Returns:
            ScrapedCodeFile: Parsed and validated code data

        Raises:
            ValueError: If file is invalid
        """
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse and validate with Pydantic
            return ScrapedCodeFile.model_validate(data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def _extract_metadata(
        self, code_data: ScrapedCodeFile, json_file: Path
    ) -> CodeDocumentMetadata:
        """Extract metadata from code data.

        Args:
            code_data: Parsed code data
            json_file: Path to the source file (for state extraction)

        Returns:
            CodeDocumentMetadata: Metadata for the document
        """
        # Get state from parent directory name
        state_abbrev = json_file.parent.name.upper()

        # Get city name from slug (clean it up)
        city_slug = code_data.metadata.city_slug
        city_name = self._slug_to_title(city_slug)

        # Determine jurisdiction level (city or county)
        is_county = "county" in city_slug.lower()
        jurisdiction_level = (
            JurisdictionLevel.COUNTY if is_county else JurisdictionLevel.CITY
        )

        # Parse scrape date
        scrape_date = None
        try:
            scrape_date = datetime.fromisoformat(code_data.metadata.scraped_at)
        except (ValueError, AttributeError):
            scrape_date = datetime.utcnow()

        # Build jurisdiction name
        jurisdiction_name = f"{city_name}, {state_abbrev}"

        # Create metadata
        metadata = CodeDocumentMetadata(
            jurisdiction_name=jurisdiction_name,
            jurisdiction_level=jurisdiction_level,
            city=city_name if not is_county else None,
            county=city_name if is_county else None,
            state=state_abbrev,
            code_type=CodeType.GENERAL,  # Could enhance to detect specific types
            document_title=f"{city_name} Municipal Code",
            source_url=code_data.metadata.source_url,
            scrape_date=scrape_date or datetime.utcnow(),
            notes=f"Scraped with {code_data.metadata.scraper or 'unknown scraper'}",
        )

        return metadata

    def _slug_to_title(self, slug: str) -> str:
        """Convert a slug to a title.

        Args:
            slug: Slug string (e.g., "salt-lake-city")

        Returns:
            str: Title case string (e.g., "Salt Lake City")
        """
        # Replace hyphens/underscores with spaces and title case
        title = slug.replace("-", " ").replace("_", " ").title()

        # Handle special cases
        title = title.replace(" Ks ", " KS ")
        title = title.replace(" Ut ", " UT ")
        title = title.replace("M-I-D-A", "MIDA")

        return title

    def _sections_to_text(self, sections: list[ScrapedCodeSection]) -> str:
        """Convert hierarchical sections to clean text.

        Args:
            sections: List of section objects

        Returns:
            str: Clean text content
        """
        text_parts = []

        for section in sections:
            # Add section heading with appropriate formatting
            if section.value:
                # Add indentation based on depth
                indent = "  " * section.depth
                text_parts.append(f"{indent}{section.value}")
                text_parts.append("")  # Empty line after heading

            # If section has HTML content, extract and clean it
            if section.html and not section.has_children:
                cleaned = self._clean_html(section.html)
                if cleaned:
                    # Indent content slightly more than heading
                    indent = "  " * (section.depth + 1)
                    indented_content = "\n".join(
                        f"{indent}{line}" for line in cleaned.split("\n") if line.strip()
                    )
                    text_parts.append(indented_content)
                    text_parts.append("")  # Empty line after content

        return "\n".join(text_parts).strip()

    def _clean_html(self, html: str) -> str:
        """Clean HTML content to plain text.

        Args:
            html: Raw HTML content

        Returns:
            str: Cleaned text
        """
        # Remove script and style tags
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)

        # Remove HTML tags but preserve line breaks
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"</p>", "\n\n", text)
        text = re.sub(r"</div>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")

        # Normalize whitespace
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # Max 2 newlines
        text = re.sub(r" +", " ", text)  # Multiple spaces to single
        text = re.sub(r"\t+", " ", text)  # Tabs to spaces

        return text.strip()

    def _generate_filename(self, metadata: CodeDocumentMetadata) -> str:
        """Generate a filename for the document.

        Args:
            metadata: Document metadata

        Returns:
            str: Generated filename
        """
        # Create a safe filename from jurisdiction name
        parts = [metadata.jurisdiction_name.replace(" ", "_").replace(",", "")]

        if metadata.code_type != CodeType.GENERAL:
            parts.append(metadata.code_type.value)

        filename = "_".join(parts).lower()

        # Remove special characters
        filename = re.sub(r"[^\w\-_.]", "", filename)

        return f"{filename}_municipal_code.txt"


async def ingest_codes(
    state: str | None = None,
    city: str | None = None,
    dry_run: bool = False,
):
    """Ingest building codes from local files.

    Args:
        state: Optional state code filter
        city: Optional city slug filter
        dry_run: If True, validate but don't upload
    """
    service = LocalCodeIngestionService()
    summary = await service.ingest_all_codes(
        state_filter=state,
        city_filter=city,
        dry_run=dry_run,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"Total documents: {summary.total_documents}")
    print(f"Successful: {summary.successful}")
    print(f"Failed: {summary.failed}")

    if summary.errors:
        print("\nErrors:")
        for error in summary.errors[:10]:  # Show first 10
            if error.file:
                print(f"  - {error.file}: {error.error}")
            else:
                print(f"  - {error.error}")
        if len(summary.errors) > 10:
            print(f"  ... and {len(summary.errors) - 10} more errors")

    if summary.file_ids:
        print(f"\nUploaded {len(summary.file_ids)} files")
        print("First 10 file IDs:")
        for file_id in summary.file_ids[:10]:
            print(f"  - {file_id}")
        if len(summary.file_ids) > 10:
            print(f"  ... and {len(summary.file_ids) - 10} more")

    print("=" * 60)


async def show_status():
    """Show current vector store status."""
    vector_store_service = VectorStoreService()
    status = await vector_store_service.get_status()

    print("\n" + "=" * 60)
    print("VECTOR STORE STATUS")
    print("=" * 60)
    print(f"Vector Store ID: {status.vector_store_id}")
    print(f"File Count: {status.file_count}")
    print(f"Total Size: {status.total_size_bytes / 1024 / 1024:.2f} MB")
    print(f"Ready: {status.is_ready}")
    if status.last_synced:
        print(f"Last Synced: {status.last_synced}")
    print("=" * 60)


async def clear_vector_store():
    """Clear all files from the vector store."""
    vector_store_service = VectorStoreService()
    deleted = await vector_store_service.clear_all_files()
    status = await vector_store_service.get_status()

    print("\n" + "=" * 60)
    print("VECTOR STORE CLEARED")
    print("=" * 60)
    print(f"Deleted files: {deleted}")
    print("=" * 60)
    print(f"Vector Store ID: {status.vector_store_id}")
    print(f"File Count: {status.file_count}")
    print(f"Total Size: {status.total_size_bytes / 1024 / 1024:.2f} MB")
    print(f"Ready: {status.is_ready}")
    if status.last_synced:
        print(f"Last Synced: {status.last_synced}")
    print("=" * 60)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest locally scraped building codes into vector store"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest building codes")
    ingest_parser.add_argument(
        "--state",
        help="State code to filter (e.g., 'ut', 'ks')",
    )
    ingest_parser.add_argument(
        "--city",
        help="City slug to filter (e.g., 'huntington')",
    )
    ingest_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate files without uploading",
    )

    # Show status
    subparsers.add_parser("status", help="Show vector store status")

    # Clear
    subparsers.add_parser("clear", help="Delete all files from vector store")

    args = parser.parse_args()

    # Run command
    if args.command == "ingest":
        asyncio.run(
            ingest_codes(
                state=args.state,
                city=args.city,
                dry_run=args.dry_run,
            )
        )
    elif args.command == "status":
        asyncio.run(show_status())
    elif args.command == "clear":
        asyncio.run(clear_vector_store())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

