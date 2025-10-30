"""Service for ingesting building code documents from Apify."""

import re
from datetime import datetime
from typing import Any

from src.ai.rag.metadata import CodeDocumentMetadata, CodeType, JurisdictionLevel
from src.ai.rag.vector_store_service import VectorStoreService
from src.utils.logger import logger


class IngestionService:
    """Service for processing and ingesting building code documents."""

    def __init__(self):
        """Initialize the ingestion service."""
        self.vector_store = VectorStoreService()

    async def ingest_from_apify_results(
        self,
        apify_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Ingest building codes from Apify scraping results.

        Args:
            apify_results: List of scraped results from Apify
                Expected format: [
                    {
                        "url": "https://...",
                        "title": "...",
                        "content": "...",  # HTML or text content
                        "metadata": {...}  # Optional metadata from scraper
                    },
                    ...
                ]

        Returns:
            dict: Ingestion summary with counts and any errors
        """
        summary = {
            "total_documents": len(apify_results),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "file_ids": [],
        }

        logger.info(f"Starting ingestion of {len(apify_results)} documents from Apify")

        for idx, result in enumerate(apify_results):
            try:
                # Extract basic info
                url = result.get("url", "")
                title = result.get("title", "")
                # Try multiple common field names for content
                content = result.get("content") or result.get("text") or result.get("html") or result.get("pageContent") or ""
                apify_metadata = result.get("metadata", {})

                if not content:
                    logger.warning(f"Skipping document {idx}: no content (tried: content, text, html, pageContent)")
                    summary["failed"] += 1
                    summary["errors"].append(
                        {"index": idx, "url": url, "error": "No content"}
                    )
                    continue

                # Parse metadata from the result
                metadata = self._parse_metadata(url, title, content, apify_metadata)

                # Clean and prepare content
                cleaned_content = self._clean_content(content)

                # Generate filename
                filename = self._generate_filename(metadata)

                # Upload to vector store with metadata prefix
                file_id = await self.vector_store.upload_document_with_metadata_prefix(
                    content=cleaned_content,
                    filename=filename,
                    metadata=metadata,
                )

                summary["successful"] += 1
                summary["file_ids"].append(file_id)

                logger.info(
                    f"Ingested document {idx + 1}/{len(apify_results)}: "
                    f"{metadata.jurisdiction_name} ({file_id})"
                )

            except Exception as e:
                logger.error(f"Failed to ingest document {idx}: {e}")
                summary["failed"] += 1
                summary["errors"].append(
                    {"index": idx, "url": result.get("url", ""), "error": str(e)}
                )

        logger.info(
            f"Ingestion complete: {summary['successful']}/{summary['total_documents']} successful"
        )

        return summary

    def _parse_metadata(
        self,
        url: str,
        title: str,
        content: str,
        apify_metadata: dict[str, Any],
    ) -> CodeDocumentMetadata:
        """Parse metadata from scraped document.

        This does basic parsing - we don't try to understand relationships
        between codes yet. Just extract what we can identify.

        Args:
            url: Source URL
            title: Document title
            content: Document content
            apify_metadata: Additional metadata from Apify scraper

        Returns:
            CodeDocumentMetadata: Parsed metadata
        """
        # Try to extract jurisdiction info from URL and title
        jurisdiction_info = self._extract_jurisdiction_info(url, title, content)

        # Try to detect code type
        code_type = self._detect_code_type(title, content)

        # Try to extract version/year
        version = self._extract_version(title, content)

        # Build metadata
        metadata = CodeDocumentMetadata(
            jurisdiction_name=jurisdiction_info["name"],
            jurisdiction_level=jurisdiction_info["level"],
            city=jurisdiction_info.get("city"),
            county=jurisdiction_info.get("county"),
            state=jurisdiction_info.get("state"),
            code_type=code_type,
            document_title=title if title else None,
            source_url=url if url else None,
            version=version,
            scrape_date=datetime.utcnow(),
            # Add any metadata passed from Apify scraper
            notes=apify_metadata.get("notes"),
        )

        return metadata

    def _extract_jurisdiction_info(
        self, url: str, title: str, content: str
    ) -> dict[str, Any]:
        """Extract jurisdiction information from URL, title, and content.

        Args:
            url: Source URL
            title: Document title
            content: Document content (first part)

        Returns:
            dict: Jurisdiction info with name, level, city, state, etc.
        """
        # Common city/state patterns
        us_states = {
            "kansas": "KS",
            "missouri": "MO",
            "california": "CA",
            "texas": "TX",
            "florida": "FL",
            "new york": "NY",
            # Add more as needed
        }

        text_to_search = f"{url} {title} {content[:1000]}".lower()

        # Check for international codes
        if any(
            keyword in text_to_search
            for keyword in ["international building code", "ibc", "international code"]
        ):
            return {
                "name": "International Building Code (IBC)",
                "level": JurisdictionLevel.INTERNATIONAL,
            }

        # Check for national codes
        if any(
            keyword in text_to_search
            for keyword in ["national building code", "federal code"]
        ):
            return {
                "name": "National Building Code",
                "level": JurisdictionLevel.NATIONAL,
            }

        # Try to extract city and state
        city = None
        state = None
        state_abbrev = None

        # Look for state names
        for state_name, abbrev in us_states.items():
            if state_name in text_to_search:
                state = state_name.title()
                state_abbrev = abbrev
                break

        # Common city patterns in URLs: city.state.gov, cityofXXX.gov
        city_patterns = [
            r"city[_\s]of[_\s]([a-z]+)",
            r"([a-z]+)[_\.](?:ks|mo|ca|tx|fl|ny)\.gov",
            r"/([a-z]+)/building",
        ]

        for pattern in city_patterns:
            match = re.search(pattern, url.lower())
            if match:
                city = match.group(1).title()
                break

        # If no city from URL, try title
        if not city:
            city_match = re.search(r"(?:city of |^)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", title)
            if city_match:
                city = city_match.group(1)

        # Determine jurisdiction level and name
        if city:
            return {
                "name": f"{city}" + (f", {state}" if state else ""),
                "level": JurisdictionLevel.CITY,
                "city": city,
                "state": state_abbrev or state,
            }
        elif state:
            return {
                "name": state,
                "level": JurisdictionLevel.STATE,
                "state": state_abbrev or state,
            }
        else:
            # Unknown jurisdiction
            return {
                "name": title or "Unknown Jurisdiction",
                "level": JurisdictionLevel.UNKNOWN,
            }

    def _detect_code_type(self, title: str, content: str) -> CodeType:
        """Detect the type of building code.

        Args:
            title: Document title
            content: Document content (first part)

        Returns:
            CodeType: Detected code type
        """
        text = f"{title} {content[:2000]}".lower()

        # Check for specific code types
        if any(keyword in text for keyword in ["roof", "shingle", "flashing", "eave"]):
            return CodeType.ROOFING

        if any(keyword in text for keyword in ["structural", "load", "foundation"]):
            return CodeType.STRUCTURAL

        if any(keyword in text for keyword in ["fire", "flame", "sprinkler"]):
            return CodeType.FIRE

        if any(keyword in text for keyword in ["electrical", "wiring", "circuit"]):
            return CodeType.ELECTRICAL

        if any(keyword in text for keyword in ["plumbing", "pipe", "drain", "water"]):
            return CodeType.PLUMBING

        if any(keyword in text for keyword in ["hvac", "mechanical", "ventilation"]):
            return CodeType.MECHANICAL

        return CodeType.GENERAL

    def _extract_version(self, title: str, content: str) -> str | None:
        """Extract version or year from title or content.

        Args:
            title: Document title
            content: Document content (first part)

        Returns:
            str | None: Version string or None
        """
        text = f"{title} {content[:1000]}"

        # Look for year patterns (2018, 2021, etc.)
        year_match = re.search(r"\b(20\d{2})\b", text)
        if year_match:
            return year_match.group(1)

        # Look for version patterns (v1.0, version 2.3, etc.)
        version_match = re.search(r"(?:version|v\.?)\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if version_match:
            return f"v{version_match.group(1)}"

        return None

    def _clean_content(self, content: str) -> str:
        """Clean HTML and format content for vector storage.

        Args:
            content: Raw content from scraper

        Returns:
            str: Cleaned content
        """
        # Remove HTML tags (basic cleaning)
        cleaned = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
        cleaned = re.sub(r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)

        # Decode HTML entities
        cleaned = cleaned.replace("&nbsp;", " ")
        cleaned = cleaned.replace("&amp;", "&")
        cleaned = cleaned.replace("&lt;", "<")
        cleaned = cleaned.replace("&gt;", ">")
        cleaned = cleaned.replace("&quot;", '"')

        # Normalize whitespace
        cleaned = re.sub(r"\n\s*\n", "\n\n", cleaned)
        cleaned = re.sub(r" +", " ", cleaned)

        return cleaned.strip()

    def _generate_filename(self, metadata: CodeDocumentMetadata) -> str:
        """Generate a filename for the document.

        Args:
            metadata: Document metadata

        Returns:
            str: Generated filename
        """
        # Create a safe filename
        parts = [metadata.jurisdiction_name.replace(" ", "_").replace(",", "")]

        if metadata.code_type != CodeType.GENERAL:
            parts.append(metadata.code_type.value)

        if metadata.version:
            parts.append(metadata.version.replace(" ", "_"))

        filename = "_".join(parts).lower()

        # Remove special characters
        filename = re.sub(r"[^\w\-_.]", "", filename)

        return f"{filename}.txt"
