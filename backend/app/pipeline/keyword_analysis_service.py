"""
Keyword Analysis Service — extracts structured keyword data from job descriptions
using LLM-powered analysis.
"""
import logging
from app.services.llm_service import LLMService
from app.services.prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class KeywordAnalysisService:
    """Extracts structured keywords from job descriptions using LLM."""

    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager):
        self.llm = llm_service
        self.prompts = prompt_manager

    async def analyze(
        self, job_title: str, company_name: str, job_description: str
    ) -> dict:
        """Analyze a job description and extract structured keyword data.
        
        Returns:
            Dict with keys: required_skills, preferred_skills, domains,
            action_verbs, technologies, seniority_level
        """
        context = {
            "job_title": job_title,
            "company_name": company_name,
            "job_description": job_description,
        }
        
        prompt = self.prompts.render("keyword_analysis", context)
        
        result = await self.llm.generate_structured(
            messages=[
                {"role": "system", "content": "You are a precise job description analyzer. Extract structured keyword data. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            task="keyword_analysis",
            temperature=0.2,  # Low temp for consistent structured output
        )
        
        return result

    def extract_keywords_text(self, analysis: dict) -> str:
        """Format keywords into a comma-separated string for prompt injection.
        
        Returns format: "required: Python, PyTorch, Docker | preferred: Kubernetes | domains: ML, CV"
        """
        parts = []
        
        if analysis.get("required_skills"):
            parts.append(f"required: {', '.join(analysis['required_skills'])}")
        
        if analysis.get("preferred_skills"):
            parts.append(f"preferred: {', '.join(analysis['preferred_skills'])}")
        
        if analysis.get("domains"):
            parts.append(f"domains: {', '.join(analysis['domains'])}")
        
        if analysis.get("technologies"):
            parts.append(f"technologies: {', '.join(analysis['technologies'])}")
        
        if analysis.get("action_verbs"):
            parts.append(f"verbs: {', '.join(analysis['action_verbs'][:5])}")
        
        return " | ".join(parts)
