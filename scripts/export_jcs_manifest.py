"""Export deterministic JCS outputs for cross-Python CI comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import rfc8785

from oneclick_cover.canonicalization import canonicalize

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "jcs"


def build_manifest() -> dict[str, object]:
    """Build a manifest of canonical bytes and content hashes for fixed vectors."""
    number_fixture = json.loads(
        (FIXTURES / "appendix_b_numbers.json").read_text(encoding="utf-8")
    )
    sample_fixture = json.loads(
        (FIXTURES / "canonicalization_sample.json").read_text(encoding="utf-8")
    )
    entries: dict[str, dict[str, str]] = {}

    for vector in number_fixture["vectors"]:
        value = struct.unpack(">d", bytes.fromhex(vector["ieee754"]))[0]
        canonical = canonicalize(value)
        entries[f"appendix_b:{vector['name']}"] = {
            "canonical_hex": canonical.hex(),
            "sha256": hashlib.sha256(canonical).hexdigest(),
        }

    canonical = canonicalize(sample_fixture["input"])
    entries["section_3:canonicalization_sample"] = {
        "canonical_hex": canonical.hex(),
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }
    return {
        "canonicalizer_identity": {
            "library": f"rfc8785@{rfc8785.__version__}",
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        },
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(build_manifest(), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
