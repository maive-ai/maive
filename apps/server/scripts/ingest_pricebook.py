"""
Script to ingest pricebook items into OpenAI vector store.

This script loads pricebook items from the cleaned JSON file and uploads them
to an OpenAI vector store for RAG retrieval during discrepancy detection.

Usage (from apps/server directory with environment variables):
    cd apps/server

    # Ingest pricebook items:
    esc run maive/maive-infra/will-dev -- uv run python scripts/ingest_pricebook.py ingest

    # Show vector store status:
    esc run maive/maive-infra/will-dev -- uv run python scripts/ingest_pricebook.py status

    # Clear vector store:
    esc run maive/maive-infra/will-dev -- uv run python scripts/ingest_pricebook.py clear
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from openai import AsyncOpenAI

from src.ai.openai.config import get_openai_settings
from src.utils.logger import logger

# Pricebook vector store name
PRICEBOOK_VECTOR_STORE_NAME = "pricebook-items"


class PricebookVectorStoreService:
    """Service for managing pricebook items in OpenAI vector stores."""

    def __init__(self):
        """Initialize the vector store service."""
        self.settings = get_openai_settings()
        self.client = AsyncOpenAI(api_key=self.settings.api_key)
        self._vector_store_id: str | None = None

    async def get_or_create_vector_store(self) -> str:
        """Get existing vector store or create a new one.

        Returns:
            str: Vector store ID
        """
        if self._vector_store_id:
            return self._vector_store_id

        # Try to find existing vector store
        try:
            vector_stores = await self.client.vector_stores.list()
            for vs in vector_stores.data:
                if vs.name == PRICEBOOK_VECTOR_STORE_NAME:
                    self._vector_store_id = vs.id
                    logger.info("[PRICEBOOK] Found existing vector store", vector_store_id=vs.id)
                    return vs.id
        except Exception as e:
            logger.error("[PRICEBOOK] Error listing vector stores", error=str(e))

        # Create new vector store
        try:
            logger.info("[PRICEBOOK] Creating new vector store", name=PRICEBOOK_VECTOR_STORE_NAME)
            vector_store = await self.client.vector_stores.create(
                name=PRICEBOOK_VECTOR_STORE_NAME,
            )
            self._vector_store_id = vector_store.id
            logger.info("[PRICEBOOK] Created vector store", vector_store_id=vector_store.id)
            return vector_store.id
        except Exception as e:
            logger.error("[PRICEBOOK] Failed to create vector store", error=str(e))
            raise

    async def upload_pricebook_file(self, file_path: Path) -> str:
        """Upload pricebook JSON file to vector store.

        Args:
            file_path: Path to the pricebook JSON file

        Returns:
            str: File ID
        """
        try:
            vector_store_id = await self.get_or_create_vector_store()

            # Check for existing pricebook file and delete if found
            filename = "pricebook_items.json"
            existing_file_id = await self._find_file_by_name(vector_store_id, filename)

            if existing_file_id:
                logger.info("[PRICEBOOK] Found existing file, deleting", file_id=existing_file_id)
                await self._delete_file(existing_file_id)
                logger.info("[PRICEBOOK] Deleted old file", file_id=existing_file_id)

            # Upload new file
            logger.info("[PRICEBOOK] Uploading file", file_path=str(file_path))
            with open(file_path, "rb") as f:
                uploaded_file = await self.client.files.create(
                    file=(filename, f),
                    purpose="assistants",
                )

            logger.info("[PRICEBOOK] Uploaded file", file_id=uploaded_file.id, filename=filename)

            # Attach file to vector store
            await self.client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=uploaded_file.id,
            )

            logger.info("[PRICEBOOK] Attached file to vector store", file_id=uploaded_file.id, vector_store_id=vector_store_id)

            return uploaded_file.id

        except Exception as e:
            logger.error("[PRICEBOOK] Failed to upload pricebook file", error=str(e))
            raise

    async def _find_file_by_name(self, vector_store_id: str, filename: str) -> str | None:
        """Find a file in the vector store by name.

        Args:
            vector_store_id: Vector store ID
            filename: Filename to search for

        Returns:
            str | None: File ID if found, None otherwise
        """
        cursor: str | None = None

        while True:
            response = await self.client.vector_stores.files.list(
                vector_store_id=vector_store_id,
                limit=100,
                after=cursor,
            )

            for f in response.data or []:
                try:
                    file_obj = await self.client.files.retrieve(f.id)
                    if getattr(file_obj, "filename", None) == filename:
                        return f.id
                except Exception:
                    pass

            if not getattr(response, "has_more", False):
                break
            cursor = getattr(response, "last_id", None)

        return None

    async def _delete_file(self, file_id: str) -> bool:
        """Delete a file from the vector store.

        Args:
            file_id: ID of the file to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            vector_store_id = await self.get_or_create_vector_store()

            # Remove from vector store
            await self.client.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=file_id,
            )

            # Delete the actual file
            await self.client.files.delete(file_id)

            logger.info("[PRICEBOOK] Deleted file", file_id=file_id)
            return True

        except Exception as e:
            logger.error("[PRICEBOOK] Failed to delete file", file_id=file_id, error=str(e))
            return False

    async def get_status(self) -> dict:
        """Get status of the vector store.

        Returns:
            dict: Status information
        """
        try:
            vector_store_id = await self.get_or_create_vector_store()

            # Get vector store details
            vector_store = await self.client.vector_stores.retrieve(vector_store_id)

            # Get list of files
            files_response = await self.client.vector_stores.files.list(
                vector_store_id=vector_store_id, limit=100
            )

            file_count = len(files_response.data)
            total_size = sum(
                getattr(f, "size_bytes", 0) or 0 for f in files_response.data
            )

            status = {
                "vector_store_id": vector_store_id,
                "file_count": file_count,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / 1024 / 1024,
                "last_synced": datetime.fromtimestamp(vector_store.created_at)
                if vector_store.created_at
                else None,
                "is_ready": vector_store.status == "completed",
            }

            logger.info(
                "[PRICEBOOK] Vector store status",
                file_count=file_count,
                size_mb=round(total_size / 1024 / 1024, 2)
            )

            return status

        except Exception as e:
            logger.error("[PRICEBOOK] Failed to get vector store status", error=str(e))
            raise

    async def clear_all_files(self) -> int:
        """Delete all files from the vector store.

        Returns:
            int: Number of files deleted
        """
        vector_store_id = await self.get_or_create_vector_store()

        deleted_count = 0
        has_more = True
        cursor: str | None = None

        while has_more:
            response = await self.client.vector_stores.files.list(
                vector_store_id=vector_store_id,
                limit=100,
                after=cursor,
            )

            files = response.data or []
            if not files:
                break

            for f in files:
                try:
                    await self.client.vector_stores.files.delete(
                        vector_store_id=vector_store_id,
                        file_id=f.id,
                    )
                    await self.client.files.delete(f.id)
                    deleted_count += 1
                except Exception as e:
                    logger.warning("[PRICEBOOK] Failed deleting file", file_id=getattr(f, 'id', '?'), error=str(e))

            has_more = bool(getattr(response, "has_more", False))
            cursor = getattr(response, "last_id", None)

        logger.info(
            "[PRICEBOOK] Cleared files from vector store",
            deleted_count=deleted_count,
            vector_store_id=vector_store_id
        )
        return deleted_count


async def ingest_pricebook():
    """Ingest pricebook items from cleaned JSON file."""
    service = PricebookVectorStoreService()

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

    try:
        file_id = await service.upload_pricebook_file(pricebook_path)

        print("\n" + "=" * 60)
        print("INGESTION COMPLETE")
        print("=" * 60)
        print(f"✅ Uploaded pricebook file")
        print(f"File ID: {file_id}")
        print("=" * 60)

    except Exception as e:
        logger.error("[PRICEBOOK] Failed to ingest pricebook", error=str(e))
        print(f"\n❌ Error: {e}")
        raise


async def show_status():
    """Show current vector store status."""
    service = PricebookVectorStoreService()
    status = await service.get_status()

    print("\n" + "=" * 60)
    print("PRICEBOOK VECTOR STORE STATUS")
    print("=" * 60)
    print(f"Vector Store ID: {status['vector_store_id']}")
    print(f"File Count: {status['file_count']}")
    print(f"Total Size: {status['total_size_mb']:.2f} MB")
    print(f"Ready: {status['is_ready']}")
    if status['last_synced']:
        print(f"Last Synced: {status['last_synced']}")
    print("=" * 60)


async def clear_vector_store():
    """Clear all files from the vector store."""
    service = PricebookVectorStoreService()
    deleted = await service.clear_all_files()
    status = await service.get_status()

    print("\n" + "=" * 60)
    print("VECTOR STORE CLEARED")
    print("=" * 60)
    print(f"Deleted files: {deleted}")
    print("=" * 60)
    print(f"Vector Store ID: {status['vector_store_id']}")
    print(f"File Count: {status['file_count']}")
    print(f"Total Size: {status['total_size_mb']:.2f} MB")
    print(f"Ready: {status['is_ready']}")
    print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest pricebook items into OpenAI vector store"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Ingest command
    subparsers.add_parser("ingest", help="Ingest pricebook items")

    # Show status
    subparsers.add_parser("status", help="Show vector store status")

    # Clear
    subparsers.add_parser("clear", help="Delete all files from vector store")

    args = parser.parse_args()

    # Run command
    if args.command == "ingest":
        asyncio.run(ingest_pricebook())
    elif args.command == "status":
        asyncio.run(show_status())
    elif args.command == "clear":
        asyncio.run(clear_vector_store())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
