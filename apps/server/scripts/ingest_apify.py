"""
Script for ingesting building codes from Apify into the vector store.

This script can:
1. Fetch results from an existing Apify actor run
2. Trigger a new Apify actor run and ingest results
3. Show vector store status

Requires APIFY_API_TOKEN environment variable to be set.

Usage:
    # Fetch and ingest from existing run:
    uv run python scripts/ingest_building_codes.py fetch-run --run-id <run_id>

    # Trigger new actor run and ingest:
    uv run python scripts/ingest_building_codes.py run-actor --actor-id <actor_id> [--input input.json]

    # Show vector store status:
    uv run python scripts/ingest_building_codes.py status

    # Manually upload a single document:
    uv run python scripts/ingest_building_codes.py upload \
        --content "$(cat building_code.txt)" \
        --jurisdiction "Leawood" \
        --level city \
        --state KS
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
from datetime import datetime
from typing import Any

import httpx
from tqdm import tqdm

from src.ai.rag.schemas import CodeDocumentMetadata, CodeType, JurisdictionLevel
from src.ai.rag.service import VectorStoreService
from src.utils.logger import logger


class ApifyClient:
    """Simple client for Apify API."""

    def __init__(self, api_token: str):
        """Initialize Apify client.

        Args:
            api_token: Apify API token
        """
        self.api_token = api_token
        self.base_url = "https://api.apify.com/v2"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_run_dataset(self, run_id: str) -> list[dict]:
        """Fetch dataset from an actor run.

        Args:
            run_id: Apify run ID

        Returns:
            list[dict]: List of scraped items
        """
        logger.info(f"Fetching dataset for run: {run_id}")

        # Get run details to find dataset ID
        url = f"{self.base_url}/actor-runs/{run_id}?token={self.api_token}"
        response = await self.client.get(url)
        response.raise_for_status()

        run_data = response.json()
        dataset_id = run_data["data"]["defaultDatasetId"]

        logger.info(f"Found dataset: {dataset_id}")

        # Fetch dataset items
        dataset_url = (
            f"{self.base_url}/datasets/{dataset_id}/items?token={self.api_token}"
        )
        response = await self.client.get(dataset_url)
        response.raise_for_status()

        items = response.json()
        logger.info(f"Retrieved {len(items)} items from dataset")

        return items

    async def run_actor(
        self, actor_id: str, input_data: dict | None = None, wait: bool = True
    ) -> tuple[str, list[dict] | None]:
        """Run an Apify actor and optionally wait for results.

        Args:
            actor_id: Apify actor ID (e.g., "apify/web-scraper")
            input_data: Input configuration for the actor
            wait: Whether to wait for the run to complete

        Returns:
            tuple: (run_id, results) - results is None if wait=False
        """
        logger.info(f"Starting actor: {actor_id}")

        # Start actor run
        url = f"{self.base_url}/acts/{actor_id}/runs?token={self.api_token}"
        response = await self.client.post(url, json=input_data or {})
        response.raise_for_status()

        run_data = response.json()
        run_id = run_data["data"]["id"]

        logger.info(f"Actor run started: {run_id}")

        if not wait:
            return run_id, None

        # Wait for run to complete
        logger.info("Waiting for actor run to complete...")
        max_wait = 600  # 10 minutes
        elapsed = 0
        poll_interval = 5

        while elapsed < max_wait:
            status_url = f"{self.base_url}/actor-runs/{run_id}?token={self.api_token}"
            response = await self.client.get(status_url)
            response.raise_for_status()

            status_data = response.json()
            status = status_data["data"]["status"]

            logger.info(f"Run status: {status}")

            if status == "SUCCEEDED":
                logger.info("Actor run completed successfully")
                results = await self.get_run_dataset(run_id)
                return run_id, results
            elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                logger.error(f"Actor run failed with status: {status}")
                raise Exception(f"Actor run {status}")

            time.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Actor run did not complete within {max_wait} seconds")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


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

        # Process documents sequentially with progress bar
        for idx, result in tqdm(
            enumerate(apify_results),
            total=len(apify_results),
            desc="Ingesting documents",
        ):
            try:
                # Extract basic info
                url = result.get("url", "")
                title = result.get("title", "")
                # Try multiple common field names for content
                content = (
                    result.get("content")
                    or result.get("text")
                    or result.get("html")
                    or result.get("pageContent")
                    or ""
                )
                apify_metadata = result.get("metadata", {})

                if not content:
                    logger.warning(
                        f"Skipping document {idx}: no content (tried: content, text, html, pageContent)"
                    )
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
                file_id = await self.vector_store.upload_document(
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
            city_match = re.search(
                r"(?:city of |^)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", title
            )
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
        version_match = re.search(
            r"(?:version|v\.?)\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE
        )
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


async def fetch_and_ingest_run(run_id: str, api_token: str):
    """Fetch results from an Apify run and ingest them.

    Args:
        run_id: Apify run ID
        api_token: Apify API token
    """
    apify_client = ApifyClient(api_token)

    try:
        # Fetch dataset
        items = await apify_client.get_run_dataset(run_id)

        if not items:
            logger.warning("No items found in dataset")
            return

        # Ingest documents
        ingestion_service = IngestionService()
        summary = await ingestion_service.ingest_from_apify_results(items)

        # Print summary
        print_ingestion_summary(summary)

    finally:
        await apify_client.close()


async def run_actor_and_ingest(actor_id: str, input_file: str | None, api_token: str):
    """Run an Apify actor and ingest the results.

    Args:
        actor_id: Apify actor ID
        input_file: Optional path to JSON file with actor input
        api_token: Apify API token
    """
    apify_client = ApifyClient(api_token)

    try:
        # Load input if provided
        input_data = None
        if input_file:
            logger.info(f"Loading actor input from: {input_file}")
            with open(input_file, "r", encoding="utf-8") as f:
                input_data = json.load(f)

        # Run actor
        run_id, items = await apify_client.run_actor(
            actor_id, input_data=input_data, wait=True
        )

        logger.info(f"Actor run completed: {run_id}")

        if not items:
            logger.warning("No items returned from actor run")
            return

        # Ingest documents
        ingestion_service = IngestionService()
        summary = await ingestion_service.ingest_from_apify_results(items)

        # Print summary
        print_ingestion_summary(summary)

    finally:
        await apify_client.close()


def print_ingestion_summary(summary: dict):
    """Print ingestion summary.

    Args:
        summary: Ingestion summary dict
    """
    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"Total documents: {summary['total_documents']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")

    if summary["errors"]:
        print("\nErrors:")
        for error in summary["errors"][:10]:  # Show first 10
            print(f"  - Document {error['index']}: {error['error']}")
            if error.get("url"):
                print(f"    URL: {error['url']}")
        if len(summary["errors"]) > 10:
            print(f"  ... and {len(summary['errors']) - 10} more errors")

    if summary["file_ids"]:
        print(f"\nUploaded {len(summary['file_ids'])} files")
        print("First 10 file IDs:")
        for file_id in summary["file_ids"][:10]:
            print(f"  - {file_id}")
        if len(summary["file_ids"]) > 10:
            print(f"  ... and {len(summary['file_ids']) - 10} more")

    print("=" * 60)


async def upload_single_document(
    content: str,
    jurisdiction: str,
    level: str,
    city: str | None = None,
    state: str | None = None,
    code_type: str = "general",
    title: str | None = None,
    url: str | None = None,
):
    """Manually upload a single document.

    Args:
        content: Document text content
        jurisdiction: Jurisdiction name
        level: Jurisdiction level
        city: City name
        state: State name or abbreviation
        code_type: Code type
        title: Document title
        url: Source URL
    """
    logger.info(f"Uploading document for {jurisdiction}")

    # Create metadata
    try:
        jurisdiction_level = JurisdictionLevel(level)
    except ValueError:
        logger.error(f"Invalid jurisdiction level: {level}")
        logger.info(f"Valid levels: {[e.value for e in JurisdictionLevel]}")
        return

    try:
        code_type_enum = CodeType(code_type)
    except ValueError:
        logger.error(f"Invalid code type: {code_type}")
        logger.info(f"Valid types: {[e.value for e in CodeType]}")
        return

    metadata = CodeDocumentMetadata(
        jurisdiction_name=jurisdiction,
        jurisdiction_level=jurisdiction_level,
        city=city,
        state=state,
        code_type=code_type_enum,
        document_title=title,
        source_url=url,
    )

    # Upload document
    vector_store_service = VectorStoreService()
    ingestion_service = IngestionService()

    # Clean content
    cleaned_content = ingestion_service._clean_content(content)

    # Generate filename
    filename = ingestion_service._generate_filename(metadata)

    # Upload
    file_id = await vector_store_service.upload_document(
        content=cleaned_content,
        filename=filename,
        metadata=metadata,
    )

    print("\n" + "=" * 60)
    print("UPLOAD SUCCESSFUL")
    print("=" * 60)
    print(f"File ID: {file_id}")
    print(f"Filename: {filename}")
    print(f"Jurisdiction: {jurisdiction} ({level})")
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
        description="Ingest building codes from Apify into vector store"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Fetch from existing run
    fetch_parser = subparsers.add_parser(
        "fetch-run", help="Fetch and ingest from existing Apify run"
    )
    fetch_parser.add_argument("--run-id", required=True, help="Apify run ID")

    # Run actor and ingest
    run_parser = subparsers.add_parser(
        "run-actor", help="Run Apify actor and ingest results"
    )
    run_parser.add_argument(
        "--actor-id",
        required=True,
        help="Apify actor ID (e.g., 'apify/web-scraper' or 'your_username/actor_name')",
    )
    run_parser.add_argument(
        "--input", help="Path to JSON file with actor input configuration"
    )

    # Upload single document
    upload_parser = subparsers.add_parser("upload", help="Upload a single document")
    upload_parser.add_argument("--content", required=True, help="Document content")
    upload_parser.add_argument(
        "--jurisdiction", required=True, help="Jurisdiction name"
    )
    upload_parser.add_argument(
        "--level",
        required=True,
        choices=["international", "national", "state", "county", "city", "unknown"],
        help="Jurisdiction level",
    )
    upload_parser.add_argument("--city", help="City name")
    upload_parser.add_argument("--state", help="State name or abbreviation")
    upload_parser.add_argument(
        "--code-type",
        default="general",
        choices=[
            "roofing",
            "structural",
            "fire",
            "electrical",
            "plumbing",
            "mechanical",
            "general",
            "other",
        ],
        help="Code type",
    )
    upload_parser.add_argument("--title", help="Document title")
    upload_parser.add_argument("--url", help="Source URL")

    # Show status
    subparsers.add_parser("status", help="Show vector store status")

    # Clear
    subparsers.add_parser("clear", help="Delete all files from vector store")

    args = parser.parse_args()

    # Check for API token if needed
    if args.command in ["fetch-run", "run-actor"]:
        api_token = os.getenv("APIFY_API_TOKEN")
        if not api_token:
            logger.error("APIFY_API_TOKEN environment variable not set")
            logger.info(
                "Get your token from: https://console.apify.com/account/integrations"
            )
            sys.exit(1)

    # Run command
    if args.command == "fetch-run":
        asyncio.run(fetch_and_ingest_run(args.run_id, api_token))
    elif args.command == "run-actor":
        asyncio.run(run_actor_and_ingest(args.actor_id, args.input, api_token))
    elif args.command == "upload":
        asyncio.run(
            upload_single_document(
                content=args.content,
                jurisdiction=args.jurisdiction,
                level=args.level,
                city=args.city,
                state=args.state,
                code_type=args.code_type,
                title=args.title,
                url=args.url,
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
