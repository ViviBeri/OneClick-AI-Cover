"""Optional anonymous Hugging Face Hub discovery and explicit public .pth downloads.

This module never loads model weights. RVC .pth files are untrusted pickle-based
artifacts; loading is deferred to the selected local RVC backend after user consent.
"""
from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import GatedRepoError, HfHubHTTPError

MAX_MODEL_BYTES = 2 * 1024 * 1024 * 1024
_REPO_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")


def search_public_rvc_models(query: str = "", limit: int = 10) -> str:
    """Return concise public Hub search results without reading a saved token."""
    term = (query or "").strip()
    if len(term) > 80:
        raise ValueError("Search text must be 80 characters or fewer.")
    if not 1 <= int(limit) <= 20:
        raise ValueError("Result limit must be between 1 and 20.")
    api = HfApi(token=False)
    models = api.list_models(
        search=term or "RVC",
        limit=int(limit),
        sort="downloads",
        direction=-1,
        cardData=True,
        token=False,
    )
    lines = []
    for item in models:
        repo_id = getattr(item, "id", None)
        if not repo_id:
            continue
        gated = bool(getattr(item, "gated", False))
        card = getattr(item, "card_data", None)
        license_name = None
        if card is not None:
            license_name = getattr(card, "license", None)
            if isinstance(card, dict):
                license_name = card.get("license", license_name)
        lines.append(
            f"Repository: {repo_id}\\n"
            f"Public access: {'gated - not downloadable anonymously' if gated else 'listed; verify public files'}\\n"
            f"License metadata: {license_name or 'not declared - review model card'}\\n"
            f"Model card: https://huggingface.co/{repo_id}\\n"
        )
    return "\\n".join(lines) if lines else "No matching public model repositories were found."


def download_public_pth_model(
    repo_id: str,
    filename: str,
    destination_dir: Path,
    confirmed: bool,
) -> str:
    """Download one explicitly selected public .pth file without authentication."""
    repo_id = (repo_id or "").strip()
    filename = (filename or "").strip().replace("\\\\", "/")
    if not confirmed:
        raise ValueError("Confirm that you reviewed the model card, license, and voice permissions.")
    if not _REPO_ID.fullmatch(repo_id):
        raise ValueError("Enter a valid Hugging Face repository ID in owner/repository format.")
    if not filename.lower().endswith(".pth") or filename.startswith("/") or ".." in Path(filename).parts:
        raise ValueError("Enter the exact relative path of a .pth file in the repository.")
    api = HfApi(token=False)
    try:
        info = api.model_info(repo_id, files_metadata=True, token=False)
    except GatedRepoError as exc:
        raise ValueError("This model is gated. Anonymous free downloads are not available; use a local model instead.") from exc
    except HfHubHTTPError as exc:
        raise ValueError(f"Could not access the public model repository: {exc}") from exc
    if bool(getattr(info, "gated", False)):
        raise ValueError("This model is gated. Choose a public model that does not require authentication.")
    siblings = getattr(info, "siblings", []) or []
    selected = next((item for item in siblings if getattr(item, "rfilename", None) == filename), None)
    if selected is None:
        raise ValueError("That exact .pth filename was not found in the repository.")
    size = getattr(selected, "size", None)
    if size is not None and (size <= 0 or size > MAX_MODEL_BYTES):
        raise ValueError("The selected model is empty or exceeds the 2 GiB download safety limit.")
    destination_dir = Path(destination_dir).resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name
    destination = destination_dir / safe_name
    if destination.exists():
        raise ValueError(f"A model named {safe_name} already exists. Rename or remove it before downloading.")
    temp_root = Path(tempfile.mkdtemp(prefix="hf_model_"))
    try:
        downloaded = Path(
            hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                repo_type="model",
                token=False,
                local_dir=str(temp_root / "download"),
            )
        )
        actual_size = downloaded.stat().st_size
        if actual_size <= 0 or actual_size > MAX_MODEL_BYTES:
            raise ValueError("Downloaded file is empty or exceeds the 2 GiB safety limit.")
        if size is not None and actual_size != size:
            raise ValueError("Downloaded file size does not match the Hub metadata.")
        shutil.copy2(downloaded, destination)
        return (
            f"Downloaded {safe_name} ({actual_size:,} bytes) to {destination}. "
            "The file has not been loaded or proven compatible; review its model card and use only trusted weights."
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
