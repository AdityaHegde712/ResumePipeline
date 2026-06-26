"""
Matching Service — scores project relevance against job descriptions using LLM.
"""
import logging
from typing import List
from app.services.llm_service import LLMService
from app.services.prompt_manager import PromptManager
from app.models.project import ProjectEntry
from app.models.generation import MatchResult

logger = logging.getLogger(__name__)


class MatchingService:
    """Scores project relevance against job descriptions."""

    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager):
        self.llm = llm_service
        self.prompts = prompt_manager

    async def match(
        self,
        job_title: str,
        company_name: str,
        job_description: str,
        projects: list[ProjectEntry],
        company_description: str = "",
    ) -> list[MatchResult]:
        """Score projects by relevance to a job description.
        
        Args:
            job_title: Target job title.
            company_name: Target company name.
            job_description: Full job description text.
            projects: List of all available projects.
            company_description: Optional company background.
            
        Returns:
            List of MatchResult sorted by relevance_score descending, max 8.
        """
        # Format projects for prompt (order by tech stack similarity heuristics)
        formatted_projects = self.format_projects_for_prompt(projects)
        
        context = {
            "job_title": job_title,
            "company_name": company_name,
            "company_description": company_description or "",
            "job_description": job_description,
            "projects": formatted_projects,
        }
        
        prompt = self.prompts.render("project_matching", context)
        
        results = await self.llm.generate_structured(
            messages=[
                {"role": "system", "content": "You are an expert resume consultant matching projects to job descriptions. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            task="matching",
            response_model=MatchResult,
            temperature=0.2,
        )
        
        # Validate and sort results
        validated = self._validate_results(results, projects)
        return validated[:8]  # Top 8 max

    def format_projects_for_prompt(self, projects: list[ProjectEntry]) -> list[dict]:
        """Format projects for prompt template with tech stack priming.
        
        Projects with more tech stack items are listed first (primacy effect
        for more complex, tool-heavy projects).
        """
        sorted_projects = sorted(
            projects, key=lambda p: len(p.tech_stack), reverse=True
        )
        return [
            {
                "id": p.id,
                "name": p.name,
                "type": p.type,
                "tech_stack": p.tech_stack,
                "summary": p.summary,
                "key_features": p.key_features,
                "resume_value_bullets": p.resume_value_bullets,
            }
            for p in sorted_projects
        ]

    def _validate_results(
        self, results: list[MatchResult], projects: list[ProjectEntry]
    ) -> list[MatchResult]:
        """Validate LLM results and enforce constraints."""
        valid_ids = {p.id for p in projects}
        validated = []
        
        for r in results:
            # Clamp score to 0-1
            r.relevance_score = max(0.0, min(1.0, r.relevance_score))
            
            # Only include projects that actually exist
            if r.project_id in valid_ids:
                validated.append(r)
            else:
                logger.warning(f"MatchResult referenced unknown project: {r.project_id}")
        
        # Sort by score descending
        validated.sort(key=lambda r: r.relevance_score, reverse=True)
        return validated