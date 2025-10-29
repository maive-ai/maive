"""
Roofing Chat Service for AI-powered roofing expertise.

This service provides streaming chat capabilities with roofing domain knowledge,
loading context from document files and using AI providers with web search.
"""

from pathlib import Path
from typing import Any, AsyncGenerator

from pypdf import PdfReader

from src.ai.base import ChatMessage, ChatStreamChunk
from src.ai.openai.config import get_openai_settings
from src.ai.providers.factory import AIProviderType, create_ai_provider
from src.utils.logger import logger


class RoofingChatService:
    """Service for AI-powered roofing chat with document context."""

    def __init__(self):
        """Initialize the roofing chat service."""
        self.settings = get_openai_settings()
        self.provider = create_ai_provider(AIProviderType.OPENAI)
        self.documents_dir = Path(__file__).parent / "documents"
        self.system_prompt_file = Path(__file__).parent / "system_prompt.md"
        self.document_context = self._load_documents()
        self.system_prompt = self._build_system_prompt()

    def _load_documents(self) -> str:
        """
        Load all documents from the documents directory recursively.

        Supports .txt, .md, and .pdf files from any subdirectory.

        Returns:
            str: Combined document content
        """
        documents = []

        # Check if documents directory exists
        if not self.documents_dir.exists():
            logger.warning(f"Documents directory not found: {self.documents_dir}")
            return ""

        # Recursively load all .txt files
        for file_path in self.documents_dir.glob("**/*.txt"):
            try:
                content = file_path.read_text(encoding="utf-8")
                # Get relative path for better context
                relative_path = file_path.relative_to(self.documents_dir)
                documents.append(
                    f"## {file_path.stem} ({relative_path.parent})\n\n{content}\n\n"
                )
                logger.info(f"Loaded text document: {relative_path}")
            except Exception as e:
                logger.error(f"Failed to load document {file_path}: {e}")

        # Recursively load all .md files
        for file_path in self.documents_dir.glob("**/*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                relative_path = file_path.relative_to(self.documents_dir)
                documents.append(
                    f"## {file_path.stem} ({relative_path.parent})\n\n{content}\n\n"
                )
                logger.info(f"Loaded markdown document: {relative_path}")
            except Exception as e:
                logger.error(f"Failed to load document {file_path}: {e}")

        # Recursively load all .pdf files
        for file_path in self.documents_dir.glob("**/*.pdf"):
            try:
                reader = PdfReader(str(file_path))
                text_content = []
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(page_text)

                if text_content:
                    combined_text = "\n\n".join(text_content)
                    relative_path = file_path.relative_to(self.documents_dir)
                    documents.append(
                        f"## {file_path.stem} ({relative_path.parent})\n\n{combined_text}\n\n"
                    )
                    logger.info(
                        f"Loaded PDF document: {relative_path} ({len(reader.pages)} pages)"
                    )
                else:
                    logger.warning(f"PDF document {file_path.name} appears to be empty")
            except Exception as e:
                logger.error(f"Failed to load PDF document {file_path}: {e}")

        if not documents:
            logger.warning("No documents loaded from any subdirectory")
            return ""

        combined = "\n".join(documents)
        logger.info(
            f"Loaded {len(documents)} documents recursively, total length: {len(combined)}"
        )
        return combined

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt from file and append document context.

        Returns:
            str: System prompt for the AI
        """
        # Load base prompt from markdown file
        try:
            base_prompt = self.system_prompt_file.read_text(encoding="utf-8")
            logger.info(f"Loaded system prompt from {self.system_prompt_file.name}")
        except Exception as e:
            logger.error(f"Failed to load system prompt file: {e}")
            # Fallback to a minimal prompt
            base_prompt = "You are RoofGPT, an expert roofing consultant."

        # Append document context if available
        if self.document_context:
            return f"""{base_prompt}

---

# Available Reference Documents

{self.document_context}
"""
        else:
            logger.warning("No reference documents loaded")
            return base_prompt

    async def stream_chat_response(
        self,
        messages: list[dict[str, Any]],
    ) -> AsyncGenerator[ChatStreamChunk, None]:
        """
        Stream chat responses using AI provider with web search capabilities.

        Args:
            messages: List of chat messages

        Yields:
            ChatStreamChunk: Response chunks with content and optional citations
        """
        try:
            # Convert dict messages to ChatMessage objects
            chat_messages = [
                ChatMessage(role=msg["role"], content=msg["content"])
                for msg in messages
            ]

            logger.info(f"Streaming chat with {len(chat_messages)} messages")

            # Stream response from provider with web search enabled
            async for chunk in self.provider.stream_chat(
                messages=chat_messages,
                instructions=self.system_prompt,
                enable_web_search=True,
                model=self.settings.model_name,
                temperature=0.7,  # Slightly creative but focused
                max_tokens=2000,
            ):
                yield chunk

            logger.info("Chat stream completed successfully")

        except Exception as e:
            logger.error(f"Error streaming chat response: {e}")
            yield ChatStreamChunk(
                content=f"\n\nError: {str(e)}",
                citations=[],
                finish_reason="error",
            )
