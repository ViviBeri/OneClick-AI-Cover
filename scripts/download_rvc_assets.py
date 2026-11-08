"""Download the exact local HuBERT and RMVPE assets required by the pinned RVC CLI."""
from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

REPO_ID = "lj1995/VoiceConversionWebUI"
REVISION = "e6d0c1a17da07c33557852f9dfa2bd44cc75737d"
ASSETS = {
    "hubert_base/config.json": {
        "destination": Path("assets/hubert_base/config.json"),
        "size": 1492,
        "sha256": "0346950779dfb7f9316fa74ed846e2b8a22a08eedfdc5387b73f327cb1a4a7cf",
    },
    "hubert_base/preprocessor_config.json": {
        "destination": Path("assets/hubert_base/preprocessor_config.json"),
        "size": 225,
        "sha256": "7c1976a680fb7acc757cd36fb08eef878fa36c70b4c9d2d595df9c608bbbbf0e",
    },
    "hubert_base/pytorch_model.bin": {
        "destination": Path("assets/hubert_base/pytorch_model.bin"),
        "size": 189206711,
        "sha256": "cc8c20f4b90a520757260197a3ff2505705a7adbd20ad9eeaa4e1a9b38442ef5",
    },
    "rmvpe.pt": {
        "destination": Path("assets/rmvpe/rmvpe.pt"),
        "size": 181184272,
        "sha256": "6d62215f4306e3ca278246188607209f09af3dc77ed4232efdd069798c4ec193",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: Path, metadata: dict) -> bool:
    if not path.is_file() or path.stat().st_size != metadata["size"]:
        return False
    expected_hash = metadata.get("sha256")
    return expected_hash is None or sha256_file(path) == expected_hash


def download_rvc_assets(
    rvc_root: Path,
    downloader=hf_hub_download,
    api=None,
) -> list[Path]:
    """Fetch pinned public assets, verify them, and install them atomically."""
    root = Path(rvc_root).resolve()
    api = api or HfApi(token=False)
    info = api.model_info(REPO_ID, revision=REVISION, files_metadata=True, token=False)
    if bool(getattr(info, "gated", False)):
        raise RuntimeError(f"{REPO_ID}@{REVISION} is gated; anonymous download is unavailable.")

    siblings = {item.rfilename: item for item in (info.siblings or [])}
    # Validate the complete manifest before downloading anything. A partial Hub
    # revision must not leave a half-installed inference runtime behind.
    for filename, metadata in ASSETS.items():
        sibling = siblings.get(filename)
        if sibling is None:
            raise RuntimeError(f"Required inference asset is missing from pinned Hub revision: {filename}")
        remote_size = getattr(sibling, "size", None)
        if remote_size is not None and remote_size != metadata["size"]:
            raise RuntimeError(f"Hub metadata size changed for {filename}: {remote_size}")

    installed = []
    for filename, metadata in ASSETS.items():
        destination = root / metadata["destination"]
        if verify_file(destination, metadata):
            installed.append(destination)
            continue

        cached = Path(
            downloader(
                repo_id=REPO_ID,
                filename=filename,
                revision=REVISION,
                token=False,
            )
        )
        if not verify_file(cached, metadata):
            raise RuntimeError(f"Downloaded inference asset failed size/SHA-256 verification: {filename}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".download")
        try:
            shutil.copyfile(cached, temporary)
            if not verify_file(temporary, metadata):
                raise RuntimeError(f"Copied inference asset failed verification: {filename}")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        installed.append(destination)

    return installed


def missing_rvc_assets(rvc_root: Path) -> list[str]:
    """Return required backend-relative paths that are absent or fail integrity checks."""
    root = Path(rvc_root)
    return [
        metadata["destination"].as_posix()
        for metadata in ASSETS.values()
        if not verify_file(root / metadata["destination"], metadata)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rvc-root", required=True, type=Path)
    args = parser.parse_args()
    paths = download_rvc_assets(args.rvc_root)
    for path in paths:
        print(f"VERIFIED {path} ({path.stat().st_size:,} bytes; SHA-256 OK)")
    print("All four HuBERT and RMVPE inference assets passed SHA-256 verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
