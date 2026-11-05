"""Static, non-deserializing inspection for PyTorch/RVC checkpoint containers.

This module reads only the ZIP member named data.pkl and walks pickle opcodes
with pickletools. It never calls pickle.load or torch.load. Results are hints,
not a compatibility or safety guarantee.
"""
from __future__ import annotations

import pickletools
import zipfile
from pathlib import Path

MAX_CHECKPOINT_BYTES = 2 * 1024 * 1024 * 1024
MAX_PICKLE_METADATA_BYTES = 16 * 1024 * 1024

_MARKERS = {
    "weight": "weight",
    "speaker_embedding": "emb_g.weight",
    "config": "config",
    "version": "version",
    "f0": "f0",
}


def inspect_rvc_checkpoint(path: Path) -> str:
    """Inspect ZIP/pickle metadata strings without executing pickle payloads."""
    source = Path(path)
    if not source.is_file():
        raise ValueError("Choose an existing checkpoint file.")
    if source.suffix.lower() != ".pth":
        raise ValueError("Only .pth checkpoint files can be inspected.")
    size = source.stat().st_size
    if size <= 0 or size > MAX_CHECKPOINT_BYTES:
        raise ValueError("Checkpoint is empty or exceeds the 2 GiB inspection limit.")

    try:
        with zipfile.ZipFile(source, "r") as archive:
            candidates = [
                item for item in archive.infolist()
                if item.filename == "data.pkl" or item.filename.endswith("/data.pkl")
            ]
            if len(candidates) != 1:
                return (
                    "Static preflight: inconclusive. Expected exactly one PyTorch "
                    "ZIP data.pkl metadata member. This may be a legacy or unsupported format. "
                    "No pickle or tensor data was loaded."
                )
            metadata = candidates[0]
            if metadata.file_size > MAX_PICKLE_METADATA_BYTES:
                raise ValueError("Checkpoint metadata exceeds the 16 MiB inspection limit.")
            raw = archive.read(metadata)
    except zipfile.BadZipFile:
        return (
            "Static preflight: inconclusive. This file is not a recognized PyTorch ZIP "
            "checkpoint container. No pickle or tensor data was loaded."
        )

    strings = set()
    try:
        for opcode, argument, _position in pickletools.genops(raw):
            if isinstance(argument, str):
                strings.add(argument)
    except (ValueError, IndexError, EOFError) as exc:
        raise ValueError(f"Checkpoint metadata could not be parsed safely: {exc}") from exc

    found = [label for label, marker in _MARKERS.items() if marker in strings]
    version_hint = next((value for value in ("v1", "v2") if value in strings), None)
    lines = [
        "STATIC PREFLIGHT — NOT A COMPATIBILITY CERTIFICATION",
        f"File: {source.name}",
        f"Size: {size:,} bytes",
        "Container: PyTorch ZIP with data.pkl metadata",
        "Metadata markers: " + (", ".join(found) if found else "none of the common RVC markers"),
        "Version string hint: " + (version_hint or "not identified"),
        "",
        "This scan only recognizes literal strings in pickle opcodes. It does not "
        "read tensor shapes, validate architecture dimensions, verify model quality, "
        "or prove that the file is safe.",
        "The RVC backend may use torch.load(), which can execute pickle payloads. "
        "Only load files from publishers you personally trust.",
    ]
    if {"weight", "speaker_embedding", "config", "version"}.issubset(found):
        lines.insert(
            5,
            "Assessment: common RVC checkpoint marker strings are present; this is only a weak structural hint.",
        )
    else:
        lines.insert(
            5,
            "Assessment: expected common RVC marker strings are incomplete; compatibility is unclear.",
        )
    return "\n".join(lines)
