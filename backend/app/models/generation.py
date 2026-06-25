"""
API request/response models for the generation pipeline.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict


class TaskModelConfig(BaseModel):
    """Per-task model configuration"""
    provider: str = "gemini"
    model: str = "gemini-2.5-pro"


class LLMConfig(BaseModel):
    """LLM provider configuration — supports per-task model routing."""
    default_provider: str = "gemini"
    default_model: str = "gemini-2.5-pro"
    tasks: Dict[str, TaskModelConfig] = {}


class GenerationRequest(BaseModel):
    application_id: str
    job_title: str
    company_name: str
    company_description: Optional[str] = None
    job_description: str
    selected_project_ids: List[str]
    tone: str = "professional"


class MatchRequest(BaseModel):
    job_title: str
    company_name: str
    job_description: str


class MatchResult(BaseModel):
    project_id: str
    project_name: str
    relevance_score: float
    reasoning: str


class PointsRegenerateRequest(BaseModel):
    application_id: str
    section_key: str
    custom_instructions: Optional[str] = None


class ResumeExportRequest(BaseModel):
    application_id: str


class SSEEvent(BaseModel):
    """Server-Sent Event payload for streaming generation progress."""
    event: str  # "stage" | "token" | "section_complete" | "error" | "complete"
    data: dict
