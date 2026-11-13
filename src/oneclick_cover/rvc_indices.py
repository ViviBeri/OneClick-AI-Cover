"""Local management helpers for RVC retrieval index files."""

from __future__ import annotations

import shutil
from pathlib import Path

from oneclick_cover.settings import INDEX_DIR


def list_rvc_indices(directory: Path = INDEX_DIR) -> list[str]:
    """Return available index filenames in stable order."""
    root = Path(directory)
    if not root.is_dir():
        return []
    return sorted(
        path.name for path in root.glob("*.index")
        if path.is_file() and path.stat().st_size > 0
    )


def import_rvc_index(source: Path, directory: Path = INDEX_DIR) -> Path:
    """Copy one explicitly selected, non-empty .index file into local storage."""
    source = Path(source)
    if not source.is_file():
        raise ValueError("Choose an existing RVC .index file.")
    if source.suffix.lower() != ".index":
        raise ValueError("RVC retrieval index files must use the .index extension.")
    if source.stat().st_size == 0:
        raise ValueError("The selected RVC index file is empty.")

    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = (root / source.name.replace("/", "_").replace("\\\\", "_")).resolve()
    if destination.parent != root:
        raise ValueError("Invalid index filename.")
    if source.resolve() != destination and destination.exists():
        raise ValueError(f"An index named {destination.name} already exists.")
    if source.resolve() != destination:
        shutil.copy2(source, destination)
    return destination
