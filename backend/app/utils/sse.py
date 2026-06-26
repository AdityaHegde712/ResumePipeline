"""
SSE (Server-Sent Events) utilities for streaming generation progress.

Provides helpers to format SSE events and build standard event payloads
for the generation pipeline.
"""
import json
import logging
from typing import AsyncGenerator, AsyncIterator

logger = logging.getLogger(__name__)


def format_sse_event(event: str, data: dict) -> str:
    """Format an SSE event string.
    
    Format:
        event: {event}
        data: {json_data}
    
    Args:
        event: Event type string ("stage", "token", "section_complete", "error", "complete").
        data: Dict payload to serialize as JSON.
        
    Returns:
        Properly formatted SSE event string with double newline terminator.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class SSEEventBuilder:
    """Builder for standard SSE event payloads used in the generation pipeline."""

    # Stage names used in the generation pipeline
    STAGES = [
        "initializing",
        "loading_projects",
        "matching_projects",
        "analyzing_keywords",
        "generating_points",
        "writing_resume",
        "rendering_latex",
        "complete",
    ]

    @staticmethod
    def stage(stage: str, status: str, **extra) -> tuple[str, dict]:
        """Build a stage event payload.
        
        Args:
            stage: Stage name (e.g., "matching_projects", "generating_points").
            status: "start", "complete", or "error".
            **extra: Additional fields to include.
            
        Returns:
            Tuple of (event_type, data_dict).
        """
        return ("stage", {"stage": stage, "status": status, **extra})

    @staticmethod
    def token(section: str, token_text: str) -> tuple[str, dict]:
        """Build a token event payload.
        
        Args:
            section: Section key (e.g., "project:arvr", "experience:company-x").
            token_text: The generated token text.
            
        Returns:
            Tuple of (event_type, data_dict).
        """
        return ("token", {"section": section, "token": token_text})

    @staticmethod
    def section_complete(section: str, bullet_count: int) -> tuple[str, dict]:
        """Build a section_complete event payload.
        
        Args:
            section: Section key.
            bullet_count: Number of bullets generated for this section.
            
        Returns:
            Tuple of (event_type, data_dict).
        """
        return ("section_complete", {"section": section, "bullet_count": bullet_count})

    @staticmethod
    def error(stage: str, message: str, **extra) -> tuple[str, dict]:
        """Build an error event payload.
        
        Args:
            stage: The stage where the error occurred.
            message: Human-readable error message.
            **extra: Additional error context.
            
        Returns:
            Tuple of (event_type, data_dict).
        """
        return ("error", {"stage": stage, "message": message, **extra})

    @staticmethod
    def complete(application_id: str, **extra) -> tuple[str, dict]:
        """Build a pipeline complete event payload.
        
        Args:
            application_id: The completed application's ID.
            **extra: Additional completion data.
            
        Returns:
            Tuple of (event_type, data_dict).
        """
        return ("complete", {"application_id": application_id, **extra})


class SSEStream:
    """Wraps an async generator for SSE streaming from the orchestrator."""

    @staticmethod
    async def event_generator(
        emit_queue: AsyncIterator[tuple[str, dict]],
    ) -> AsyncGenerator[str, None]:
        """Convert (event, data) tuples into SSE-formatted strings.
        
        Args:
            emit_queue: Async iterator yielding (event_type, data_dict) tuples.
            
        Yields:
            SSE-formatted event strings.
        """
        async for event_type, data in emit_queue:
            yield format_sse_event(event_type, data)
