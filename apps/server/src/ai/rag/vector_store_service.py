"""Service for managing OpenAI vector stores for building codes."""

import tempfile
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from openai import AsyncOpenAI

from src.ai.openai.config import get_openai_settings
from src.ai.rag.metadata import CodeDocumentMetadata, VectorStoreStatus
from src.utils.logger import logger


class VectorStoreService:
    """Service for managing building code documents in OpenAI vector stores."""

    # Name of our single nationwide vector store
    VECTOR_STORE_NAME = "building-codes-nationwide"

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
                if vs.name == self.VECTOR_STORE_NAME:
                    self._vector_store_id = vs.id
                    logger.info(f"Found existing vector store: {vs.id}")
                    return vs.id
        except Exception as e:
            logger.error(f"Error listing vector stores: {e}")

        # Create new vector store
        try:
            logger.info(f"Creating new vector store: {self.VECTOR_STORE_NAME}")
            vector_store = await self.client.vector_stores.create(
                name=self.VECTOR_STORE_NAME,
            )
            self._vector_store_id = vector_store.id
            logger.info(f"Created vector store: {vector_store.id}")
            return vector_store.id
        except Exception as e:
            logger.error(f"Failed to create vector store: {e}")
            raise

    async def upload_document(
        self,
        content: str | BinaryIO,
        filename: str,
        metadata: CodeDocumentMetadata,
    ) -> str:
        """Upload a document to the vector store.

        Args:
            content: Document content (text string or file-like object)
            filename: Name for the file
            metadata: Document metadata

        Returns:
            str: File ID
        """
        try:
            vector_store_id = await self.get_or_create_vector_store()

            # Prepare metadata attributes
            attributes = metadata.to_openai_metadata()
            attributes["filename"] = filename

            # If content is a string, write to temp file
            if isinstance(content, str):
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=Path(filename).suffix or ".txt",
                    delete=False,
                    encoding="utf-8",
                )
                temp_file.write(content)
                temp_file.close()
                file_path = temp_file.name
                should_cleanup = True
            else:
                # Content is already a file-like object
                file_path = None
                file_obj = content
                should_cleanup = False

            try:
                if file_path:
                    with open(file_path, "rb") as f:
                        uploaded_file = await self.client.files.create(
                            file=f,
                            purpose="assistants",
                        )
                else:
                    uploaded_file = await self.client.files.create(
                        file=file_obj,
                        purpose="assistants",
                    )

                logger.info(
                    f"Uploaded file: {uploaded_file.id} ({filename}) "
                    f"for {metadata.jurisdiction_name}"
                )

                # Attach file to vector store with attributes
                await self.client.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=uploaded_file.id,
                    attributes=attributes,
                )

                logger.info(
                    f"Attached file {uploaded_file.id} to vector store {vector_store_id}"
                )

                return uploaded_file.id

            finally:
                # Clean up temp file if we created one
                if should_cleanup and file_path:
                    try:
                        Path(file_path).unlink()
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp file: {e}")

        except Exception as e:
            logger.error(f"Failed to upload document {filename}: {e}")
            raise

    async def _find_file_id_by_filename(
        self, vector_store_id: str, filename: str
    ) -> str | None:
        """Search the vector store for a file with the given filename.

        Strategy:
        1) Prefer matching on attributes.filename if present.
        2) Fallback to retrieving the OpenAI file object to compare its filename.

        Returns:
            str | None: The file ID if found, otherwise None.
        """
        cursor: str | None = None

        while True:
            response = await self.client.vector_stores.files.list(
                vector_store_id=vector_store_id,
                limit=100,
                after=cursor,
            )

            for f in response.data or []:
                # Try attribute match if the SDK surfaces attributes on the item
                attrs = getattr(f, "attributes", None) or {}
                if isinstance(attrs, dict) and attrs.get("filename") == filename:
                    return f.id

                # Fallback: check the underlying file's filename
                try:
                    file_obj = await self.client.files.retrieve(f.id)
                    if getattr(file_obj, "filename", None) == filename:
                        return f.id
                except Exception:
                    # Ignore retrieval failures and continue scanning
                    pass

            if not getattr(response, "has_more", False):
                break
            cursor = getattr(response, "last_id", None)

        return None

    async def get_status(self) -> VectorStoreStatus:
        """Get status of the vector store.

        Returns:
            VectorStoreStatus: Current status
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

            # Note: Without custom metadata support, we can't easily count
            # unique jurisdictions, cities, etc. without parsing all files.
            # For MVP, we'll just show file count.

            status = VectorStoreStatus(
                vector_store_id=vector_store_id,
                file_count=file_count,
                total_size_bytes=total_size,
                jurisdictions_count=0,  # Would need to parse files to determine
                cities_count=0,
                states_count=0,
                last_synced=datetime.fromtimestamp(vector_store.created_at)
                if vector_store.created_at
                else None,
                is_ready=vector_store.status == "completed",
            )

            logger.info(
                f"Vector store status: {file_count} files, "
                f"{total_size / 1024 / 1024:.2f} MB"
            )

            return status

        except Exception as e:
            logger.error(f"Failed to get vector store status: {e}")
            raise

    async def delete_file(self, file_id: str) -> bool:
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

            logger.info(f"Deleted file: {file_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    async def list_files(self, limit: int = 100) -> list[dict]:
        """List files in the vector store.

        Args:
            limit: Maximum number of files to return

        Returns:
            list[dict]: List of file information
        """
        try:
            vector_store_id = await self.get_or_create_vector_store()

            files_response = await self.client.vector_stores.files.list(
                vector_store_id=vector_store_id,
                limit=limit,
            )

            files = []
            for f in files_response.data:
                files.append(
                    {
                        "file_id": f.id,
                        "created_at": datetime.fromtimestamp(f.created_at),
                        "status": f.status,
                    }
                )

            return files

        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            raise

    async def clear_all_files(self) -> int:
        """Delete all files from the current vector store and OpenAI Files.

        Returns:
            int: Number of files deleted
        """
        vector_store_id = await self.get_or_create_vector_store()

        # Page through files until none remain
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
                    logger.warning(f"Failed deleting file {getattr(f, 'id', '?')}: {e}")

            has_more = bool(getattr(response, "has_more", False))
            cursor = getattr(response, "last_id", None)

        logger.info(
            f"Cleared {deleted_count} files from vector store {vector_store_id}"
        )
        return deleted_count
