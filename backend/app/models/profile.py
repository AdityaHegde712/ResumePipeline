"""
Profile data models — objective (profile.yaml) and subjective (profile.md).
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class Link(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None


class Education(BaseModel):
    school: str
    degree: str
    start_date: str
    end_date: str
    location: str
    gpa: Optional[str] = None
    coursework: List[str] = Field(default_factory=list)


class Experience(BaseModel):
    company: str
    role: str
    start_date: str
    end_date: str
    location: str
    description: str
    highlights: List[str] = Field(default_factory=list)


class PersonalProject(BaseModel):
    """Projects NOT in the sweep file (side projects, hackathons, etc.)"""
    name: str
    tech_stack: List[str] = Field(default_factory=list)
    description: str
    url: Optional[str] = None


class Publication(BaseModel):
    """Academic publications — rendered as static content."""
    title: str
    authors: str
    venue: str
    year: str
    url: Optional[str] = None
    description: Optional[str] = ""


class SkillSet(BaseModel):
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)


class Certificate(BaseModel):
    name: str
    issuer: str
    date: Optional[str] = None
    url: Optional[str] = None


class Leadership(BaseModel):
    organization: str
    role: str
    start_date: str
    end_date: str
    description: str


class CustomSection(BaseModel):
    title: str
    items: List[str] = Field(default_factory=list)


class UserProfile(BaseModel):
    """Complete user profile — both profile.yaml fields and subjective content."""
    # Identity
    name: str = "Aditya Hegde"
    email: str = ""
    phone: str = ""
    location: str = ""
    links: Link = Link()

    # Resume sections
    education: List[Education] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    personal_projects: List[PersonalProject] = Field(default_factory=list)
    publications: List[Publication] = Field(default_factory=list)
    skills: SkillSet = SkillSet()
    certifications: List[Certificate] = Field(default_factory=list)
    leadership: List[Leadership] = Field(default_factory=list)
    custom_sections: List[CustomSection] = Field(default_factory=list)

    # Section ordering (default: optimized for early-career with strong projects)
    section_order: List[str] = Field(default_factory=lambda: [
        "education",
        "skills",
        "projects",
        "experience",
        "publications",
        "leadership",
        "certifications",
    ])

    # Subjective/narrative profile (vNext: cover letter generation)
    subjective_profile_path: str = "data/subjective_profile.md"
    subjective_profile_content: str = ""
