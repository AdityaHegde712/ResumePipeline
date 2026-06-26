"""
Resume Points Generator — generates ATS-optimized bullet points for
each project and experience section using LLM.
"""
import logging
import uuid
from typing import Callable, Awaitable, Optional
from app.services.llm_service import LLMService
from app.services.prompt_manager import PromptManager
from app.models.profile import UserProfile, Experience
from app.models.project import ProjectEntry
from app.models.application import SectionPoints, BulletPoint

logger = logging.getLogger(__name__)


class ResumePointsGenerator:
    """Generates bullet points for resume sections using LLM."""

    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager):
        self.llm = llm_service
        self.prompts = prompt_manager

    async def generate_all(
        self,
        job_title: str,
        company_name: str,
        job_description: str,
        jd_keywords: str,
        selected_projects: list[ProjectEntry],
        profile: UserProfile,
        tone: str = "professional",
        on_token: Optional[Callable[[str, str], Awaitable[None]]] = None,
        on_section_complete: Optional[Callable[[str, list[str]], Awaitable[None]]] = None,
    ) -> list[SectionPoints]:
        """Generate bullet points for all sections.
        
        Args:
            job_title: Target job title.
            company_name: Target company name.
            job_description: Full job description.
            jd_keywords: Extracted keywords string from KeywordAnalysisService.
            selected_projects: Projects selected by MatchingService.
            profile: User's profile (for experience sections).
            tone: "professional", "technical", or "balanced".
            on_token: Async callback (section_key, token_text) for streaming.
            on_section_complete: Async callback (section_key, bullets) per section.
            
        Returns:
            List of SectionPoints with generated bullets.
        """
        sections: list[SectionPoints] = []
        
        # Generate for each selected project
        for project in selected_projects:
            section_key = f"project:{project.id}"
            section_title = project.name
            
            section_details = self._format_project_details(project)
            
            bullets = await self.generate_for_section(
                section_type="Project",
                section_name=section_title,
                section_details=section_details,
                job_title=job_title,
                company_name=company_name,
                jd_keywords_text=jd_keywords,
                tone=tone,
                num_bullets=4,
                on_token=lambda token: on_token(section_key, token) if on_token else None,
            )
            
            section = SectionPoints(
                section_key=section_key,
                section_title=section_title,
                bullets=[
                    BulletPoint(id=str(uuid.uuid4()), section=section_key, text=b, order=i)
                    for i, b in enumerate(bullets)
                ],
            )
            sections.append(section)
            
            if on_section_complete:
                await on_section_complete(section_key, bullets)
        
        # Generate for each experience entry
        for exp in profile.experience:
            section_key = f"experience:{exp.company.lower().replace(' ', '-')}"
            section_title = f"{exp.role} @ {exp.company}"
            
            section_details = self._format_experience_details(exp)
            
            bullets = await self.generate_for_section(
                section_type="Experience",
                section_name=section_title,
                section_details=section_details,
                job_title=job_title,
                company_name=company_name,
                jd_keywords_text=jd_keywords,
                tone=tone,
                num_bullets=3,
                on_token=lambda token: on_token(section_key, token) if on_token else None,
            )
            
            section = SectionPoints(
                section_key=section_key,
                section_title=section_title,
                bullets=[
                    BulletPoint(id=str(uuid.uuid4()), section=section_key, text=b, order=i)
                    for i, b in enumerate(bullets)
                ],
            )
            sections.append(section)
            
            if on_section_complete:
                await on_section_complete(section_key, bullets)
        
        return sections

    async def generate_for_section(
        self,
        section_type: str,
        section_name: str,
        section_details: str,
        job_title: str,
        company_name: str,
        jd_keywords_text: str,
        tone: str = "professional",
        num_bullets: int = 4,
        on_token: Optional[Callable] = None,
    ) -> list[str]:
        """Generate bullet points for a single section."""
        context = {
            "section_type": section_type,
            "section_name": section_name,
            "section_details": section_details,
            "job_title": job_title,
            "company_name": company_name,
            "jd_keywords": jd_keywords_text,
            "tone": tone,
            "num_bullets": num_bullets,
        }
        
        prompt = self.prompts.render("resume_points", context)
        
        # Use streaming if callback provided
        if on_token:
            full_text = ""
            stream = await self.llm.generate(
                messages=[
                    {"role": "system", "content": "You are a technical resume writer. Generate ATS-optimized bullet points. Return ONLY a JSON array of strings."},
                    {"role": "user", "content": prompt},
                ],
                task="resume_points",
                temperature=0.3,
                stream=True,
            )
            async for token in stream:
                full_text += token
                await on_token(token)
            
            # Parse JSON from streamed response
            return self._parse_bullets(full_text)
        else:
            result = await self.llm.generate_structured(
                messages=[
                    {"role": "system", "content": "You are a technical resume writer. Generate ATS-optimized bullet points. Return ONLY a JSON array of strings."},
                    {"role": "user", "content": prompt},
                ],
                task="resume_points",
                temperature=0.3,
            )
            return result if isinstance(result, list) else [str(result)]

    async def regenerate_section(
        self,
        section_key: str,
        custom_instructions: str = "",
        previous_bullets: Optional[list[str]] = None,
    ) -> list[str]:
        """Regenerate bullets for a section with optional custom instructions."""
        # Similar to generate_for_section but includes context about previous attempt
        context = {}
        if previous_bullets:
            context["previous_bullets"] = previous_bullets
        if custom_instructions:
            context["custom_instructions"] = custom_instructions
        
        # Would call LLM with additional context
        raise NotImplementedError("Regeneration will be implemented with full context")

    def _format_project_details(self, project: ProjectEntry) -> str:
        """Format a project entry into a text block for the prompt."""
        parts = [
            f"Type: {project.type}",
            f"Tech Stack: {', '.join(project.tech_stack)}",
            f"Summary: {project.summary}",
        ]
        if project.key_features:
            parts.append(f"Key Features: {'; '.join(project.key_features)}")
        if project.resume_value_bullets:
            parts.append(f"Resume Value: {'; '.join(project.resume_value_bullets)}")
        if project.lines_of_code:
            parts.append(f"Scale: {project.lines_of_code:,} lines of code")
        return "\n".join(parts)

    def _format_experience_details(self, exp: Experience) -> str:
        """Format an experience entry into a text block for the prompt."""
        parts = [
            f"Company: {exp.company}",
            f"Role: {exp.role}",
            f"Dates: {exp.start_date} - {exp.end_date}",
            f"Location: {exp.location}",
            f"Description: {exp.description}",
        ]
        if exp.highlights:
            parts.append(f"Highlights: {'; '.join(exp.highlights)}")
        return "\n".join(parts)

    def _parse_bullets(self, text: str) -> list[str]:
        """Parse bullet points from LLM response text."""
        import json
        text = text.strip()
        if text.startswith("```"):
            start = text.find("\n") + 1
            end = text.rfind("```")
            if end > start:
                text = text[start:end].strip()
        if text.startswith("```json"):
            text = text[7:]
            end = text.rfind("```")
            if end > 0:
                text = text[:end].strip()
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(item) for item in data]
            return [str(data)]
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse bullets JSON, returning raw lines")
            return [line.strip("- ").strip() for line in text.split("\n") if line.strip()]
