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
                # Upload file to OpenAI with metadata
                C = metadata.to_openai_metadata()

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

                # Attach file to vector store
                await self.client.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=uploaded_file.id,
                )

                # Note: OpenAI doesn't support custom metadata on vector store files yet
                # The metadata will need to be embedded in the document content itself
                # or managed separately

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

    async def upload_document_with_metadata_prefix(
        self,
        content: str,
        filename: str,
        metadata: CodeDocumentMetadata,
    ) -> str:
        """Upload a document with metadata embedded as a prefix.

        Since OpenAI doesn't support custom metadata on vector store files,
        we embed the metadata as a structured prefix in the document content.

        Args:
            content: Document text content
            filename: Name for the file
            metadata: Document metadata

        Returns:
            str: File ID
        """
        # Create metadata header
        metadata_lines = [
            "# Document Metadata",
            f"Jurisdiction: {metadata.jurisdiction_name}",
            f"Level: {metadata.jurisdiction_level.value}",
            f"Code Type: {metadata.code_type.value}",
        ]

        if metadata.city:
            metadata_lines.append(f"City: {metadata.city}")
        if metadata.county:
            metadata_lines.append(f"County: {metadata.county}")
        if metadata.state:
            metadata_lines.append(f"State: {metadata.state}")
        if metadata.document_title:
            metadata_lines.append(f"Title: {metadata.document_title}")
        if metadata.version:
            metadata_lines.append(f"Version: {metadata.version}")
        if metadata.code_section:
            metadata_lines.append(f"Section: {metadata.code_section}")
        if metadata.adopts_code:
            metadata_lines.append(f"Adopts: {metadata.adopts_code}")
        if metadata.source_url:
            metadata_lines.append(f"Source: {metadata.source_url}")

        metadata_lines.append("")  # Empty line
        metadata_lines.append("---")
        metadata_lines.append("")

        # Combine metadata header with content
        prefixed_content = "\n".join(metadata_lines) + "\n" + content

        return await self.upload_document(prefixed_content, filename, metadata)

    async def get_status(self) -> VectorStoreStatus:
        """Get status of the vector store.

        Returns:
            VectorStoreStatus: Current status
        """
        try:
            vector_store_id = await self.get_or_create_vector_store()

            # Get vector store details
            vector_store = await self.client.vector_stores.retrieve(
                vector_store_id
            )

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
