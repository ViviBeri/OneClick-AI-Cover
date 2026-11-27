"""Compare JCS conformance outputs produced by Python 3.11 and 3.12."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ARTIFACTS = Path("artifacts")


def load_manifest(python_minor: str) -> dict[str, object]:
    """Load the CI manifest produced by one Python matrix member."""
    path = ARTIFACTS / f"jcs-{python_minor}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    older = load_manifest("3.11")
    newer = load_manifest("3.12")
    old_identity = older["canonicalizer_identity"]
    new_identity = newer["canonicalizer_identity"]
    assert old_identity["library"] == new_identity["library"]
    assert old_identity["python"] == "3.11"
    assert new_identity["python"] == "3.12"

    old_entries = older["entries"]
    new_entries = newer["entries"]
    assert old_entries.keys() == new_entries.keys()

    for name in old_entries:
        old_entry = old_entries[name]
        new_entry = new_entries[name]
        assert old_entry["canonical_hex"] == new_entry["canonical_hex"], name
        assert old_entry["sha256"] == new_entry["sha256"], name
        canonical = bytes.fromhex(old_entry["canonical_hex"])
        assert hashlib.sha256(canonical).hexdigest() == old_entry["sha256"], name


if __name__ == "__main__":
    main()
