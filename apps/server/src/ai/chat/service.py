"""
Roofing Chat Service for AI-powered roofing expertise.

This service provides streaming chat capabilities with roofing domain knowledge,
loading context from document files and using OpenAI for responses.
"""

import logging
from pathlib import Path
from typing import AsyncGenerator

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pypdf import PdfReader

from src.ai.openai.config import get_openai_settings

logger = logging.getLogger(__name__)


class RoofingChatService:
    """Service for AI-powered roofing chat with document context."""

    def __init__(self):
        """Initialize the roofing chat service."""
        self.settings = get_openai_settings()
        self.client = AsyncOpenAI(api_key=self.settings.api_key)
        self.documents_dir = Path(__file__).parent / "documents"
        self.document_context = self._load_documents()
        self.system_prompt = self._build_system_prompt()

    def _load_documents(self) -> str:
        """
        Load all documents from the documents directory.

        Supports .txt, .md, and .pdf files.

        Returns:
            str: Combined document content
        """
        documents = []

        # Check if documents directory exists
        if not self.documents_dir.exists():
            logger.warning(f"Documents directory not found: {self.documents_dir}")
            return ""

        # Load documents from each subdirectory
        for subdir in ["local_codes", "warranties", "system_booklets"]:
            subdir_path = self.documents_dir / subdir
            if not subdir_path.exists():
                logger.warning(f"Subdirectory not found: {subdir_path}")
                continue

            # Load all .txt files
            for file_path in subdir_path.glob("**/*.txt"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    documents.append(f"## {file_path.stem}\n\n{content}\n\n")
                    logger.info(f"Loaded text document: {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to load document {file_path}: {e}")

            # Load all .md files
            for file_path in subdir_path.glob("**/*.md"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    documents.append(f"## {file_path.stem}\n\n{content}\n\n")
                    logger.info(f"Loaded markdown document: {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to load document {file_path}: {e}")

            # Load all .pdf files
            for file_path in subdir_path.glob("**/*.pdf"):
                try:
                    reader = PdfReader(str(file_path))
                    text_content = []
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content.append(page_text)

                    if text_content:
                        combined_text = "\n\n".join(text_content)
                        documents.append(f"## {file_path.stem}\n\n{combined_text}\n\n")
                        logger.info(
                            f"Loaded PDF document: {file_path.name} ({len(reader.pages)} pages)"
                        )
                    else:
                        logger.warning(f"PDF document {file_path.name} appears to be empty")
                except Exception as e:
                    logger.error(f"Failed to load PDF document {file_path}: {e}")

        if not documents:
            logger.warning("No documents loaded")
            return ""

        combined = "\n".join(documents)
        logger.info(f"Loaded {len(documents)} documents, total length: {len(combined)}")
        return combined

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt with document context.

        Returns:
            str: System prompt for the AI
        """
        base_prompt = """You are RoofGPT, an expert roofing consultant with deep knowledge of:
- Local building codes and regulations
- Manufacturer warranties and specifications
- Roofing system design and installation
- Material selection and compatibility
- Safety standards and best practices
- Common roofing problems and solutions

You provide accurate, professional advice based on industry standards and the documentation provided to you.
When answering questions, cite specific codes, warranties, or standards when relevant.
If you're unsure about something, acknowledge the limits of your knowledge.

Be conversational and helpful, but maintain professional expertise.
"""

        if self.document_context:
            return f"""{base_prompt}

# Reference Documentation

You have access to the following reference materials:

{self.document_context}

Use this documentation to inform your answers. When citing specific information, mention the source document.
"""
        else:
            return f"""{base_prompt}

Note: No reference documents are currently loaded. Provide answers based on general roofing expertise.
"""

    async def stream_chat_response(
        self,
        messages: list[ChatCompletionMessageParam],
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat responses using OpenAI.

        Args:
            messages: List of chat messages in OpenAI format

        Yields:
            str: Response chunks as they arrive
        """
        try:
            # Prepend system prompt
            full_messages = [
                {"role": "system", "content": self.system_prompt},
                *messages,
            ]

            logger.info(f"Streaming chat with {len(messages)} messages")

            # Stream response from OpenAI
            stream = await self.client.chat.completions.create(
                model=self.settings.model_name,
                messages=full_messages,
                temperature=0.7,  # Slightly creative but focused
                max_tokens=2000,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    yield content

            logger.info("Chat stream completed successfully")

        except Exception as e:
            logger.error(f"Error streaming chat response: {e}")
            yield f"\n\nError: {str(e)}"
