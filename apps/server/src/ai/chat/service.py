"""
Roofing Chat Service for AI-powered roofing expertise.

This service provides streaming chat capabilities with roofing domain knowledge,
loading context from file search and using AI providers with web search.
"""

from pathlib import Path
from typing import Any, AsyncGenerator

from src.ai.base import ChatMessage, ChatStreamChunk
from src.ai.openai.config import get_openai_settings
from src.ai.providers.factory import AIProviderType, create_ai_provider
from src.ai.rag.service import VectorStoreService
from src.utils.logger import logger


class RoofingChatService:
    """Service for AI-powered roofing chat with document context."""

    def __init__(self):
        """Initialize the roofing chat service."""
        self.settings = get_openai_settings()
        self.provider = create_ai_provider(AIProviderType.OPENAI)
        self.system_prompt_file = Path(__file__).parent / "system_prompt.md"
        self.system_prompt = self._build_system_prompt()

        # Initialize vector store for RAG
        self._vector_store_id: str | None = None
        self._vector_store_service = VectorStoreService()

    async def _get_vector_store_id(self) -> str:
        """Get the vector store ID for RAG (lazy initialization).

        Returns:
            str: Vector store ID
        """
        if self._vector_store_id is None:
            self._vector_store_id = (
                await self._vector_store_service.get_or_create_vector_store()
            )
            logger.info("Initialized vector store for RAG", vector_store_id=self._vector_store_id)
        return self._vector_store_id

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt from file.

        Returns:
            str: System prompt for the AI
        """
        # Load base prompt from markdown file
        try:
            base_prompt = self.system_prompt_file.read_text(encoding="utf-8")
            logger.info("Loaded system prompt", file_name=self.system_prompt_file.name)
        except Exception as e:
            logger.error("Failed to load system prompt file", error=str(e))
            # Fallback to a minimal prompt
            base_prompt = "You are RoofGPT, an expert roofing consultant."

        return base_prompt

    async def stream_chat_response(
        self,
        messages: list[dict[str, Any]],
        user_auth_token: str | None = None,
    ) -> AsyncGenerator[ChatStreamChunk, None]:
        """
        Stream chat responses using AI provider with web search and RAG capabilities.

        Args:
            messages: List of chat messages
            user_auth_token: User's JWT token for MCP authentication (optional)

        Yields:
            ChatStreamChunk: Response chunks with content and optional citations
        """
        try:
            # Convert dict messages to ChatMessage objects
            chat_messages = [
                ChatMessage(role=msg["role"], content=msg["content"])
                for msg in messages
            ]

            # Get vector store ID for RAG
            vector_store_id = await self._get_vector_store_id()

            logger.info(
                "Streaming chat with RAG enabled",
                message_count=len(messages),
                vector_store_id=vector_store_id
            )

            # Stream response from provider with web search and file search
            async for chunk in self.provider.stream_chat(
                messages=chat_messages,
                instructions=self.system_prompt,
                enable_web_search=True,
                enable_crm_search=True,
                vector_store_ids=[vector_store_id],
                model=self.settings.model_name,
                temperature=0.7,  # Slightly creative but focused
                max_tokens=2000,
                user_auth_token=user_auth_token,  # Pass user's JWT for MCP auth
            ):
                yield chunk

            logger.info("Chat stream completed successfully")

        except Exception as e:
            logger.error("Error streaming chat response", error=str(e))
            yield ChatStreamChunk(
                content=f"\n\nError: {str(e)}",
                citations=[],
                finish_reason="error",
            )
