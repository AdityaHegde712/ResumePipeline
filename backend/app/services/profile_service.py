"""
Profile management service — handles two-profile model:
1. profile.yaml (structured YAML for objective data)
2. subjective_profile.md (free-form narrative for vNext cover letters)
"""
import yaml
from pathlib import Path
from typing import Optional
from app.models.profile import UserProfile


class ProfileValidationError(Exception):
    """Raised when profile YAML is invalid."""
    def __init__(self, message: str, line: Optional[int] = None):
        self.line = line
        super().__init__(message)


class ProfileService:
    """Manages the two-profile model: objective YAML + subjective markdown."""

    def __init__(self, data_dir: Path = Path("./data")):
        self.data_dir = data_dir
        self._profile_path = data_dir / "profile.yaml"
        self._subjective_path = data_dir / "subjective_profile.md"

    async def load(self) -> UserProfile:
        """
        1. Read profile.yaml → parse YAML → validate → UserProfile
        2. Read subjective_profile.md → raw text → set subjective_profile_content
        3. If either file missing, return defaults (empty profile + empty narrative)
        """
        profile = UserProfile()

        # Load objective profile
        if self._profile_path.exists():
            try:
                with open(self._profile_path, "r", encoding="utf-8") as f:
                    raw = f.read()
                data = yaml.safe_load(raw)
                if data is None:
                    data = {}
                # Validate required fields exist
                profile = UserProfile(**data)
            except yaml.YAMLError as e:
                line = getattr(e, "problem_mark", None)
                line_num = line.line + 1 if line else None
                raise ProfileValidationError(
                    f"Invalid YAML in {self._profile_path}: {e}",
                    line=line_num,
                )

        # Load subjective profile
        profile.subjective_profile_content = await self.load_subjective()

        return profile

    async def save(self, profile: UserProfile) -> UserProfile:
        """
        1. Serialize objective fields → YAML → write to profile.yaml
        2. Serialize subjective_profile_content → write to subjective_profile.md
        3. Create data/ dir if missing
        """
        # Ensure data dir exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Save objective profile (exclude subjective fields)
        profile_dict = profile.model_dump(exclude={"subjective_profile_path", "subjective_profile_content"}, by_alias=True)
        
        # Convert to ordered dict to maintain field order in YAML
        with open(self._profile_path, "w", encoding="utf-8") as f:
            yaml.dump(
                profile_dict,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        # Save subjective profile
        if profile.subjective_profile_content:
            with open(self._subjective_path, "w", encoding="utf-8") as f:
                f.write(profile.subjective_profile_content)

        return profile

    async def exists(self) -> bool:
        """Check if profile.yaml exists with required fields (name, email)."""
        if not self._profile_path.exists():
            return False
        try:
            profile = await self.load()
            return bool(profile.name)  # name is the minimum required field
        except ProfileValidationError:
            return False

    async def load_subjective(self) -> str:
        """Load subjective_profile.md as raw text, return empty string if missing."""
        if not self._subjective_path.exists():
            return ""
        with open(self._subjective_path, "r", encoding="utf-8") as f:
            return f.read()