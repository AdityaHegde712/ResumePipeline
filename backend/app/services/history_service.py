"""
History service — manages per-application JSON files in data/applications/.
"""
import asyncio
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from app.models.application import Application

logger = logging.getLogger(__name__)


class HistoryServiceError(Exception):
    """Base exception for history service errors."""


class HistoryService:
    """Manages per-application JSON files in data/applications/."""

    def __init__(self, data_dir: Path = Path("./data")):
        self.applications_dir = data_dir / "applications"
        self.applications_dir.mkdir(parents=True, exist_ok=True)

    def _generate_id(self) -> str:
        """Generate app-YYYYMMDD-NNN with zero-padded daily counter."""
        today = date.today()
        date_str = today.strftime("%Y%m%d")
        
        # Count existing applications for today
        prefix = f"app-{date_str}-"
        count = 0
        if self.applications_dir.exists():
            for f in self.applications_dir.iterdir():
                if f.name.startswith(prefix) and f.suffix == ".json":
                    count += 1
        
        # Next in sequence (1-indexed)
        return f"{prefix}{count + 1:03d}"

    def _write_json(self, file_path: Path, app: Application) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(app.model_dump(mode="json"), f, indent=2, default=str)

    def _read_json(self, file_path: Path) -> dict:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def create(self, app: Application) -> Application:
        """Create a new application record with auto-generated ID."""
        if not app.id:
            app.id = self._generate_id()
        now = datetime.now()
        app.created_at = now
        app.updated_at = now

        file_path = self.applications_dir / f"{app.id}.json"
        await asyncio.to_thread(self._write_json, file_path, app)

        logger.info(f"Created application: {app.id}")
        return app

    async def get(self, app_id: str) -> Optional[Application]:
        """Read and parse an application JSON file."""
        file_path = self.applications_dir / f"{app_id}.json"
        if not file_path.exists():
            return None

        try:
            data = await asyncio.to_thread(self._read_json, file_path)
            return Application(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            raise HistoryServiceError(f"Corrupt application file: {app_id}") from e

    async def list_all(self) -> list[dict]:
        """List all applications sorted by created_at desc (without full generated content)."""
        if not self.applications_dir.exists():
            return []

        apps = []
        for f in sorted(self.applications_dir.iterdir(), key=lambda x: x.name, reverse=True):
            if f.suffix != ".json":
                continue
            try:
                data = await asyncio.to_thread(self._read_json, f)
                # Return summary without generated content for performance
                apps.append({
                    "id": data.get("id"),
                    "company_name": data.get("company_name", ""),
                    "job_title": data.get("job_title", ""),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "generation_status": data.get("generation_status", "pending"),
                    "error_message": data.get("error_message"),
                })
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Skipping corrupt file {f.name}: {e}")
                continue

        return apps

    async def update(self, app: Application) -> Application:
        """Update an existing application record."""
        app.updated_at = datetime.now()

        file_path = self.applications_dir / f"{app.id}.json"
        await asyncio.to_thread(self._write_json, file_path, app)

        logger.info(f"Updated application: {app.id}")
        return app

    async def delete(self, app_id: str) -> bool:
        """Delete an application file. Returns True if existed."""
        file_path = self.applications_dir / f"{app_id}.json"
        if not file_path.exists():
            return False

        file_path.unlink()
        logger.info(f"Deleted application: {app_id}")
        return True

    async def count(self) -> int:
        """Count application JSON files."""
        if not self.applications_dir.exists():
            return 0
        return sum(1 for f in self.applications_dir.iterdir() if f.suffix == ".json")