"""
Project entry model — parsed from PROJECT_SWEEP_SUMMARIES.md.
"""
from pydantic import BaseModel
from typing import List, Optional


class ProjectEntry(BaseModel):
    id: str
    name: str
    type: str
    summary: str
    tech_stack: List[str] = []
    key_features: List[str] = []
    resume_value_bullets: List[str] = []
    domains: List[str] = []
    lines_of_code: Optional[int] = None
    source_section: str = ""
