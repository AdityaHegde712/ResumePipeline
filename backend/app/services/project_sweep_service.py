"""
Service for parsing and indexing PROJECT_SWEEP_SUMMARIES.md.
"""
import os
import re
import logging
from pathlib import Path
from typing import Optional
from app.models.project import ProjectEntry

logger = logging.getLogger(__name__)

# Domain inference mapping
TECH_TO_DOMAIN = {
    "react": "Web Development",
    "typescript": "Web Development",
    "javascript": "Web Development",
    "node": "Web Development",
    "flask": "Web Development",
    "fastapi": "Web Development",
    "docker": "DevOps",
    "kubernetes": "DevOps",
    "aws": "DevOps",
    "ci/cd": "DevOps",
    "github actions": "DevOps",
    "pytorch": "Machine Learning",
    "tensorflow": "Machine Learning",
    "transformers": "Machine Learning",
    "llm": "Machine Learning",
    "langchain": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Machine Learning",
    "opencv": "Computer Vision",
    "yolo": "Computer Vision",
    "computer vision": "Computer Vision",
    "c++": "Systems Programming",
    "cuda": "GPU Programming",
    "qt": "Desktop Development",
    "arduino": "Embedded Systems",
    "unity": "Game Development",
    "mongodb": "Database",
    "postgresql": "Database",
    "redis": "Database",
    "graphql": "API Development",
    "grpc": "API Development",
    "websocket": "Real-time Systems",
    "webrtc": "Real-time Systems",
}


class ProjectSweepService:
    """Parses PROJECT_SWEEP_SUMMARIES.md into structured ProjectEntry objects."""

    def __init__(self, sweep_file_path: Optional[Path] = None):
        if sweep_file_path is None:
            # Default: look in project root
            sweep_file_path = Path("../../PROJECT_SWEEP_SUMMARIES.md")
        self.sweep_file_path = sweep_file_path
        self._projects: list[ProjectEntry] = []
        self._last_parsed_mtime: float = 0.0
        self._domain_index: dict[str, set[str]] = {}
        self._tech_index: dict[str, set[str]] = {}

    def parse(self) -> list[ProjectEntry]:
        """Parse the sweep file from scratch."""
        if not self.sweep_file_path.exists():
            logger.warning(f"Sweep file not found: {self.sweep_file_path}")
            return []

        # Try UTF-8 first, fall back to system encoding for Windows cp1252 files
        try:
            with open(self.sweep_file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(self.sweep_file_path, "r", encoding="cp1252") as f:
                content = f.read()

        projects = []
        sections = re.split(r'\n(?=## )', content)

        for section in sections:
            if not section.strip() or section.startswith("# "):
                continue
            project = self._parse_section(section)
            if project:
                projects.append(project)

        self._projects = projects
        self._last_parsed_mtime = os.path.getmtime(self.sweep_file_path)
        self._rebuild_indexes()

        logger.info(f"Parsed {len(projects)} projects from sweep file")
        return projects

    def _parse_section(self, section: str) -> Optional[ProjectEntry]:
        """Parse a single section into a ProjectEntry."""
        lines = section.strip().split('\n')
        if not lines:
            return None

        header = lines[0].strip()
        header = re.sub(r'^##\s+', '', header)

        # Extract project name: "N. Project Name — Description"
        name_match = re.match(r'\d+\.\s+(.+?)(?:\s*[—–-]\s*|$)', header)
        if not name_match:
            return None

        project_name = name_match.group(1).strip()
        project_id = self._make_id(project_name)

        # Extract Type
        project_type = ""
        type_match = re.search(r'\*\*Type:\*\*\s*(.+)', section, re.IGNORECASE)
        if type_match:
            project_type = type_match.group(1).strip()

        # Extract Tech Stack
        tech_stack = []
        tech_match = re.search(
            r'\*\*Tech Stack(?:\s*&\s*Architecture)?\*\*:\*\*\s*(.+)',
            section, re.IGNORECASE | re.DOTALL
        )
        if tech_match:
            tech_text = tech_match.group(1).strip()
            tech_stack = [t.strip().strip('`') for t in tech_text.split(',') if t.strip()]
        else:
            tech_match = re.search(r'\*\*Tech Stack:\*\*\s*(.+)', section, re.IGNORECASE)
            if tech_match:
                tech_text = tech_match.group(1).strip()
                tech_stack = [t.strip().strip('`') for t in tech_text.split(',') if t.strip()]

        # Extract Summary
        summary = ""
        overview_match = re.search(
            r'### (?:Project\s+)?Overview\s*\n(.+?)(?:\n###\s|\Z)',
            section, re.DOTALL
        )
        if overview_match:
            summary = overview_match.group(1).strip()
        summary = re.sub(r'^- ', '', summary, flags=re.MULTILINE)

        # Extract Key Features
        key_features = []
        in_key_features = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('### Key Features'):
                in_key_features = True
                continue
            if in_key_features:
                if stripped.startswith('### '):
                    break
                if stripped.startswith('- ') or stripped.startswith('* '):
                    feature = re.sub(r'^\-\s+\*\*(.+?)\*\*.*', r'\1', stripped)
                    if feature == stripped:
                        feature = stripped.lstrip('-* ').strip()
                    key_features.append(feature)

        # Extract Resume Value Bullets
        resume_value_bullets = []
        in_resume_value = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('### Resume Value'):
                in_resume_value = True
                continue
            if in_resume_value:
                if stripped.startswith('### '):
                    break
                if stripped.startswith('- ') or stripped.startswith('* '):
                    bullet = re.sub(r'^\-\s+', '', stripped)
                    resume_value_bullets.append(bullet)

        # Extract Lines of Code
        lines_of_code = None
        loc_match = re.search(
            r'\*\*Scale:\*\*\s*(?:(\d[\d,]*)\s*lines)', section, re.IGNORECASE
        )
        if loc_match:
            lines_of_code = int(loc_match.group(1).replace(',', ''))

        source_section = f"section-{len(self._projects) + 1}"

        return ProjectEntry(
            id=project_id,
            name=project_name,
            type=project_type,
            summary=summary,
            tech_stack=tech_stack,
            key_features=key_features,
            resume_value_bullets=resume_value_bullets,
            domains=self._infer_domains(project_type, tech_stack),
            lines_of_code=lines_of_code,
            source_section=source_section,
        )

    def _make_id(self, name: str) -> str:
        name = name.strip().lower()
        name = re.sub(r'[^a-z0-9\s-]', '', name)
        name = re.sub(r'\s+', '-', name.strip())
        return name[:40]

    def _infer_domains(self, project_type: str, tech_stack: list[str]) -> list[str]:
        domains = set()
        type_lower = project_type.lower()
        if 'ml' in type_lower or 'machine learning' in type_lower:
            domains.add('Machine Learning')
        if 'web' in type_lower or 'full-stack' in type_lower:
            domains.add('Web Development')
        if 'research' in type_lower:
            domains.add('Research')
        if 'devops' in type_lower or 'infrastructure' in type_lower:
            domains.add('DevOps')

        for tech in tech_stack:
            tech_lower = tech.strip().lower()
            if tech_lower in TECH_TO_DOMAIN:
                domains.add(TECH_TO_DOMAIN[tech_lower])

        return sorted(domains) if domains else ["General"]

    def _rebuild_indexes(self):
        self._domain_index = {}
        self._tech_index = {}
        for project in self._projects:
            for domain in project.domains:
                if domain not in self._domain_index:
                    self._domain_index[domain] = set()
                self._domain_index[domain].add(project.id)
            for tech in project.tech_stack:
                tech_lower = tech.strip().lower()
                if tech_lower not in self._tech_index:
                    self._tech_index[tech_lower] = set()
                self._tech_index[tech_lower].add(project.id)

    def get_all(self) -> list[ProjectEntry]:
        if self.is_stale() or not self._projects:
            self.parse()
        return list(self._projects)

    def refresh(self) -> list[ProjectEntry]:
        return self.parse()

    def get_by_id(self, project_id: str) -> Optional[ProjectEntry]:
        self.get_all()
        for project in self._projects:
            if project.id == project_id:
                return project
        return None

    def get_by_domain(self, domain: str) -> list[ProjectEntry]:
        self.get_all()
        domain_lower = domain.lower()
        matching_ids = set()
        for d, ids in self._domain_index.items():
            if d.lower() == domain_lower:
                matching_ids.update(ids)
        return [p for p in self._projects if p.id in matching_ids]

    def get_by_tech(self, tech: str) -> list[ProjectEntry]:
        self.get_all()
        tech_lower = tech.strip().lower()
        matching_ids = self._tech_index.get(tech_lower, set())
        return [p for p in self._projects if p.id in matching_ids]

    def search(self, keyword: str) -> list[ProjectEntry]:
        self.get_all()
        keyword_lower = keyword.lower()
        results = []
        for project in self._projects:
            if (keyword_lower in project.name.lower() or
                keyword_lower in project.summary.lower() or
                any(keyword_lower in t.lower() for t in project.tech_stack) or
                any(keyword_lower in d.lower() for d in project.domains)):
                results.append(project)
        return results

    def is_stale(self) -> bool:
        if not self.sweep_file_path.exists():
            return False
        current_mtime = os.path.getmtime(self.sweep_file_path)
        return current_mtime > self._last_parsed_mtime
