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

import httpx

from src.ai.rag.ingestion_service import IngestionService
from src.ai.rag.metadata import CodeDocumentMetadata, CodeType, JurisdictionLevel
from src.ai.rag.vector_store_service import VectorStoreService
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
