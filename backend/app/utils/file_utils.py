from pathlib import Path
from typing import Optional


def resolve_path(path: str | Path, base_dir: Optional[Path] = None) -> Path:
    """Resolve a path relative to base_dir if it's not absolute.

    Args:
        path: The path to resolve.
        base_dir: Base directory for relative paths. Defaults to cwd.

    Returns:
        Resolved absolute Path.
    """
    p = Path(path)
    if not p.is_absolute() and base_dir:
        return (base_dir / p).resolve()
    return p.resolve()


def ensure_dir(path: str | Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path.

    Returns:
        The Path object for the directory.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
