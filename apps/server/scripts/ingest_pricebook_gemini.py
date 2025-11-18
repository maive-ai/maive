"""
Script to ingest pricebook items into Google Gemini File Search store.

This script uploads the cleaned pricebook JSON file to a Gemini File Search store
for RAG retrieval during discrepancy detection.

Usage (from apps/server directory with environment variables):
    cd apps/server

    # Ingest pricebook items:
    esc run maive/maive-infra/will-dev -- uv run python scripts/ingest_pricebook_gemini.py ingest

    # Show File Search store status:
    esc run maive/maive-infra/will-dev -- uv run python scripts/ingest_pricebook_gemini.py status
"""

import argparse
import asyncio
import time
from pathlib import Path

from src.ai.gemini import get_gemini_client
from src.utils.logger import logger

# File Search store display name
PRICEBOOK_STORE_DISPLAY_NAME = "pricebook-items"

# Maximum wait time for upload operation (in seconds)
MAX_OPERATION_WAIT_TIME = 3600  # 1 hour


async def ingest_pricebook():
    """Ingest pricebook items from cleaned JSON file into Gemini File Search store."""
    client = get_gemini_client()

    # Path to cleaned pricebook file
    pricebook_path = Path("evals/estimate_deviation/output/pricebook_items_cleaned.json")

    if not pricebook_path.exists():
        logger.error("[PRICEBOOK] Pricebook file not found", path=str(pricebook_path))
        print(f"\n❌ Error: {pricebook_path} not found")
        print("Run scripts/clean_pricebook.py first to generate the cleaned file.")
        return

    logger.info("[PRICEBOOK] Starting ingestion")
    logger.info("[PRICEBOOK] File path", path=str(pricebook_path))

    file_size_mb = pricebook_path.stat().st_size / (1024 * 1024)
    logger.info("[PRICEBOOK] File size", size_mb=round(file_size_mb, 2))

    if file_size_mb > 100:
        logger.error("[PRICEBOOK] File too large", size_mb=round(file_size_mb, 2))
        print(f"\n❌ Error: File size ({file_size_mb:.2f} MB) exceeds Gemini limit (100 MB)")
        return

    try:
        # Get or create File Search store
        stores = await client.list_file_search_stores()
        store_name = None

        for store in stores:
            if store.get("display_name") == PRICEBOOK_STORE_DISPLAY_NAME:
                store_name = store["name"]
                logger.info("[PRICEBOOK] Found existing store", store_name=store_name)
                break

        if not store_name:
            logger.info("[PRICEBOOK] Creating new File Search store")
            store_name = await client.create_file_search_store(PRICEBOOK_STORE_DISPLAY_NAME)
            logger.info("[PRICEBOOK] Created store", store_name=store_name)

        # Upload file to store
        logger.info("[PRICEBOOK] Uploading file to store", store_name=store_name)
        operation = await client.upload_to_file_search_store(
            file_path=str(pricebook_path),
            store_name=store_name,
            display_name="pricebook_items.json",
        )

        # Poll operation until complete
        logger.info("[PRICEBOOK] Polling operation", operation_name=operation.name)
        start_time = time.time()
        poll_interval = 5  # seconds

        while True:
            operation = await client.get_operation(operation)

            if operation.done:
                logger.info("[PRICEBOOK] Upload operation completed", operation_name=operation.name)
                break

            elapsed = time.time() - start_time
            if elapsed > MAX_OPERATION_WAIT_TIME:
                logger.error(
                    "[PRICEBOOK] Operation timeout",
                    elapsed_seconds=elapsed,
                    max_wait=MAX_OPERATION_WAIT_TIME,
                )
                print(f"\n❌ Error: Operation timed out after {elapsed:.0f} seconds")
                return

            logger.info(
                "[PRICEBOOK] Operation in progress",
                elapsed_seconds=round(elapsed),
                operation_name=operation.name,
            )
            await asyncio.sleep(poll_interval)

        print("\n" + "=" * 60)
        print("INGESTION COMPLETE")
        print("=" * 60)
        print(f"✅ Uploaded pricebook file to Gemini File Search store")
        print(f"Store Name: {store_name}")
        print("\n💡 Copy the store name above and use it when calling GeminiProvider:")
        print(f'   file_search_store_names=["{store_name}"]')
        print("=" * 60)

    except Exception as e:
        logger.error("[PRICEBOOK] Failed to ingest pricebook", error=str(e))
        print(f"\n❌ Error: {e}")
        raise


async def show_status():
    """Show current File Search store status."""
    client = get_gemini_client()

    try:
        stores = await client.list_file_search_stores()

        # Find pricebook store
        pricebook_store = None
        for store in stores:
            if store.get("display_name") == PRICEBOOK_STORE_DISPLAY_NAME:
                pricebook_store = store
                break

        print("\n" + "=" * 60)
        print("PRICEBOOK FILE SEARCH STORE STATUS")
        print("=" * 60)

        if not pricebook_store:
            print("❌ No pricebook store found")
            print("Run 'ingest' command first to create and upload the store.")
        else:
            print(f"Store Name: {pricebook_store['name']}")
            print(f"Display Name: {pricebook_store.get('display_name', 'N/A')}")
            print("\n✅ Store exists and is ready for queries")
            print("\n💡 Use this store name in queries:")
            print(f'   file_search_store_names=["{pricebook_store["name"]}"]')

        print("=" * 60)

    except Exception as e:
        logger.error("[PRICEBOOK] Failed to get store status", error=str(e))
        print(f"\n❌ Error: {e}")
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest pricebook items into Gemini File Search store"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Ingest command
    subparsers.add_parser("ingest", help="Ingest pricebook items")

    # Show status
    subparsers.add_parser("status", help="Show File Search store status")

    args = parser.parse_args()

    # Run command
    if args.command == "ingest":
        asyncio.run(ingest_pricebook())
    elif args.command == "status":
        asyncio.run(show_status())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

