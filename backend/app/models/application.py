"""
Application / generation history models.
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class GenerationStatus(str, Enum):
    PENDING = "pending"
    MATCHING = "matching"
    GENERATING_POINTS = "generating_points"
    WRITING_RESUME = "writing_resume"
    RENDERING_LATEX = "rendering_latex"
    COMPLETED = "completed"
    FAILED = "failed"


class BulletPoint(BaseModel):
    id: str
    section: str
    text: str
    order: int = 0
    edited: bool = False


class SectionPoints(BaseModel):
    section_key: str
    section_title: str
    bullets: List[BulletPoint] = []


class GeneratedContent(BaseModel):
    resume_points: List[SectionPoints] = []
    resume_latex: Optional[str] = None
    model_used: str = ""


class Application(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    company_name: str
    company_description: Optional[str] = None
    job_title: str
    job_description: str
    selected_project_ids: List[str] = []
    generation_status: GenerationStatus = GenerationStatus.PENDING
    generated: Optional[GeneratedContent] = None
    error_message: Optional[str] = None
