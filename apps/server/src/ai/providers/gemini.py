"""Gemini provider implementation."""

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from src.ai.base import (
    AIProvider,
    AudioAnalysisRequest,
    ContentAnalysisRequest,
    ContentGenerationResult,
    FileMetadata,
    TranscriptionResult,
)
from src.ai.gemini import get_gemini_client
from src.ai.gemini.schemas import (
    FileUploadRequest,
    GenerateContentRequest,
    GenerateStructuredContentRequest,
)
from src.utils.logger import logger

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(AIProvider):
    """Gemini provider implementation.

    Uses Google's Gemini API for audio processing, transcription, and content generation.
    Gemini supports native multimodal input including audio files.
    """

    def __init__(self):
        """Initialize Gemini provider."""
        self.client = get_gemini_client()

    async def upload_file(self, file_path: str, **kwargs) -> FileMetadata:
        """Upload a file to Gemini Files API.

        Args:
            file_path: Path to the file to upload
            **kwargs: Additional options (display_name, mime_type)

        Returns:
            FileMetadata: Metadata of the uploaded file
        """
        try:
            request = FileUploadRequest(
                file_path=file_path,
                display_name=kwargs.get("display_name"),
                mime_type=kwargs.get("mime_type"),
            )
            result = await self.client.upload_file(request)

            # Convert Gemini's FileMetadata to our generic format
            return FileMetadata(
                id=result.name,
                name=result.display_name or Path(file_path).name,
                mime_type=result.mime_type,
                size_bytes=result.size_bytes,
            )
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Gemini Files API.

        Args:
            file_id: ID (name) of the file to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            result = await self.client.delete_file(file_id)
            return result.success
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    async def transcribe_audio(self, audio_path: str, **kwargs) -> TranscriptionResult:
        """Transcribe audio using Gemini.

        Note: Gemini doesn't have a dedicated transcription API like Whisper.
        This method processes the audio and extracts text via content generation.

        Args:
            audio_path: Path to the audio file
            **kwargs: Additional options (language, prompt, etc.)

        Returns:
            TranscriptionResult: Transcription result
        """
        try:
            logger.info(f"Transcribing audio with Gemini: {audio_path}")

            # Upload audio file
            file_metadata = await self.upload_file(audio_path)

            # Use content generation to transcribe
            prompt = kwargs.get(
                "prompt",
                "Please transcribe the audio. Provide only the transcription text, no additional commentary.",
            )

            request = GenerateContentRequest(
                prompt=prompt,
                files=[file_metadata.id],
                temperature=kwargs.get("temperature", 0.0),
            )

            response = await self.client.generate_content(request)

            # Clean up uploaded file
            await self.delete_file(file_metadata.id)

            return TranscriptionResult(
                text=response.text,
                language=kwargs.get("language"),
            )
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    async def generate_content(
        self,
        prompt: str,
        file_ids: list[str] | None = None,
        **kwargs,
    ) -> ContentGenerationResult:
        """Generate text content using Gemini.

        Args:
            prompt: Text prompt
            file_ids: Optional list of file IDs (names) to include
            **kwargs: Additional options (temperature, max_tokens, model, etc.)

        Returns:
            ContentGenerationResult: Generated content
        """
        try:
            request = GenerateContentRequest(
                prompt=prompt,
                files=file_ids or [],
                temperature=kwargs.get("temperature"),
                model_name=kwargs.get("model"),
            )

            response = await self.client.generate_content(request)

            return ContentGenerationResult(
                text=response.text,
                usage=response.usage,
                finish_reason=response.finish_reason,
            )
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise

    async def generate_structured_content(
        self,
        prompt: str,
        response_model: type[T],
        file_ids: list[str] | None = None,
        **kwargs,
    ) -> T:
        """Generate structured content using a Pydantic model.

        Args:
            prompt: Text prompt
            response_model: Pydantic model for structured output
            file_ids: Optional list of file IDs
            **kwargs: Additional options

        Returns:
            Instance of response_model with generated data
        """
        try:
            request = GenerateStructuredContentRequest(
                prompt=prompt,
                response_model=response_model,
                files=file_ids or [],
                temperature=kwargs.get("temperature"),
                model_name=kwargs.get("model"),
            )

            result = await self.client.generate_structured_content(request)
            return result
        except Exception as e:
            logger.error(f"Structured content generation failed: {e}")
            raise

    async def analyze_audio_with_context(
        self,
        request: AudioAnalysisRequest,
    ) -> ContentGenerationResult:
        """Analyze audio with contextual information using Gemini.

        Gemini supports native multimodal input, so we can send audio files directly.

        Args:
            request: Audio analysis request

        Returns:
            ContentGenerationResult: Analysis result
        """
        try:
            logger.info(f"Analyzing audio with Gemini: {request.audio_path}")

            # Upload audio file
            file_metadata = await self.upload_file(request.audio_path)

            # Build prompt with context
            full_prompt = request.prompt
            if request.context_data:
                context_text = (
                    f"\n\nContext Data:\n{json.dumps(request.context_data, indent=2)}"
                )
                full_prompt += context_text

            # Generate analysis
            gen_request = GenerateContentRequest(
                prompt=full_prompt,
                files=[file_metadata.id],
                temperature=request.temperature,
            )

            response = await self.client.generate_content(gen_request)

            # Clean up uploaded file
            await self.delete_file(file_metadata.id)

            return ContentGenerationResult(
                text=response.text,
                usage=response.usage,
                finish_reason=response.finish_reason,
            )
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}")
            raise

    async def analyze_audio_with_structured_output(
        self,
        request: AudioAnalysisRequest,
        response_model: type[T],
    ) -> T:
        """Analyze audio and return structured output using Gemini.

        Args:
            request: Audio analysis request
            response_model: Pydantic model for structured output

        Returns:
            Instance of response_model with analysis results
        """
        try:
            logger.info(
                f"Analyzing audio with structured output (Gemini): {request.audio_path}"
            )

            # Upload audio file
            file_metadata = await self.upload_file(request.audio_path)
            logger.info("Uploaded file to Files API!")

            # Build prompt with context
            full_prompt = request.prompt
            if request.context_data:
                context_text = (
                    f"\n\nContext Data:\n{json.dumps(request.context_data, indent=2)}"
                )
                full_prompt += context_text

            # Generate structured analysis
            gen_request = GenerateStructuredContentRequest(
                prompt=full_prompt,
                response_model=response_model,
                files=[file_metadata.id],
                temperature=request.temperature,
            )

            result = await self.client.generate_structured_content(gen_request)

            # Clean up uploaded file
            await self.delete_file(file_metadata.id)

            return result
        except Exception as e:
            logger.error(f"Structured audio analysis failed: {e}")
            raise

    async def analyze_content_with_structured_output(
        self,
        request: ContentAnalysisRequest,
        response_model: type[T],
    ) -> T:
        """Analyze content (audio, transcript, or both) and return structured output.

        Args:
            request: Content analysis request
            response_model: Pydantic model for structured output

        Returns:
            Instance of response_model with analysis results
        """
        try:
            logger.info("Analyzing content with structured output")

            # Build prompt (includes transcript if provided)
            full_prompt = request.prompt
            if request.transcript_text:
                full_prompt = f"{request.prompt}\n\n**Conversation Transcript:**\n{request.transcript_text}"

            if request.context_data:
                context_text = (
                    f"\n\nContext Data:\n{json.dumps(request.context_data, indent=2)}"
                )
                full_prompt += context_text

            # Handle audio file if provided
            file_ids = []
            file_metadata = None
            if request.audio_path:
                logger.info(f"Uploading audio file: {request.audio_path}")
                file_metadata = await self.upload_file(request.audio_path)
                file_ids = [file_metadata.id]

            # Generate structured analysis
            gen_request = GenerateStructuredContentRequest(
                prompt=full_prompt,
                response_model=response_model,
                files=file_ids,
                temperature=request.temperature,
            )

            result = await self.client.generate_structured_content(gen_request)

            # Clean up uploaded file if any
            if file_metadata:
                await self.delete_file(file_metadata.id)

            return result
        except Exception as e:
            logger.error(f"Structured content analysis failed: {e}")
            raise
