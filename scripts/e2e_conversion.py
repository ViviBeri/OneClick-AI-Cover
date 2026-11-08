"""Opt-in real conversion check for the manual Windows workflow.

The selected .pth file is deserialized by the RVC backend. Only run this workflow
with a model publisher and checkpoint you explicitly trust. The rights checkbox
does not make an untrusted pickle safe.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

MAX_SAMPLE_BYTES = 50 * 1024 * 1024
MAX_MODEL_BYTES = 2 * 1024 * 1024 * 1024


def _download_sample(url: str, destination: Path) -> int:
    if not url.lower().startswith("https://"):
        raise ValueError("Sample URL must use https://")
    request = urllib.request.Request(url, headers={"User-Agent": "OneClick-AI-Cover-e2e"})
    total = 0
    with urllib.request.urlopen(request, timeout=60) as response:
        if not response.geturl().lower().startswith("https://"):
            raise ValueError("Sample download redirected away from HTTPS.")
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > MAX_SAMPLE_BYTES:
            raise ValueError("Sample exceeds the 50 MiB download limit.")
        with destination.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_SAMPLE_BYTES:
                    raise ValueError("Sample exceeds the 50 MiB download limit.")
                handle.write(chunk)
    if total == 0:
        raise ValueError("Downloaded sample is empty.")
    return total


def _download_model(repo_id: str, filename: str, destination_dir: Path) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repo_id):
        raise ValueError("Model repo must be an exact Hugging Face owner/repository ID.")
    relative = PurePosixPath(filename)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".pth":
        raise ValueError("Model filename must be a safe relative path ending in .pth.")

    from huggingface_hub import HfApi, hf_hub_download

    api = HfApi(token=False)
    info = api.model_info(repo_id, files_metadata=True, token=False)
    if bool(getattr(info, "gated", False)):
        raise ValueError("The selected model repository is gated and cannot be downloaded anonymously.")
    sibling = next((item for item in (info.siblings or []) if item.rfilename == filename), None)
    if sibling is None:
        raise ValueError("The exact .pth filename was not found in the selected model repository.")
    if sibling.size is not None and not 0 < sibling.size <= MAX_MODEL_BYTES:
        raise ValueError("The selected model file is empty or exceeds the 2 GiB limit.")

    downloaded = Path(
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            revision=info.sha,
            token=False,
        )
    )
    if not downloaded.is_file() or not 0 < downloaded.stat().st_size <= MAX_MODEL_BYTES:
        raise ValueError("Downloaded model failed the file-size check.")
    if sibling.size is not None and downloaded.stat().st_size != sibling.size:
        raise ValueError("Downloaded model size does not match Hugging Face metadata.")

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / downloaded.name
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite an existing model: {destination.name}")
    shutil.copy2(downloaded, destination)
    return destination


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-url", default=os.environ.get("SAMPLE_URL", ""))
    parser.add_argument("--model-repo", default=os.environ.get("MODEL_REPO_ID", ""))
    parser.add_argument("--model-file", default=os.environ.get("MODEL_FILENAME", ""))
    parser.add_argument("--seconds", type=float, default=float(os.environ.get("CLIP_SECONDS", "15") or 15))
    parser.add_argument("--out-dir", default=str(ROOT / "e2e-artifacts"))
    args = parser.parse_args()

    if os.environ.get("RIGHTS_CONFIRMED", "").lower() != "true":
        print("Refusing to run: confirm rights to use the sample and voice model.", file=sys.stderr)
        return 2
    if os.environ.get("MODEL_TRUST_CONFIRMED", "").lower() != "true":
        print(
            "Refusing to run: confirm that you trust the model publisher and .pth file. "
            "RVC may execute pickle payloads while loading it.",
            file=sys.stderr,
        )
        return 2
    if not (args.sample_url and args.model_repo and args.model_file):
        print("Sample URL, model repo, and model filename are all required.", file=sys.stderr)
        return 2
    if not 1 <= args.seconds <= 30:
        print("Clip length must be between 1 and 30 seconds.", file=sys.stderr)
        return 2

    from oneclick_cover.audio_utils import _ffmpeg_path
    from oneclick_cover.model_preflight import inspect_rvc_checkpoint
    from oneclick_cover.settings import VOICE_DIR
    from oneclick_cover.verify_output import verify_cover_audio

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "model_trust_confirmed": True,
        "rights_confirmed": True,
        "stages": {},
    }
    started = time.monotonic()
    model_path = None

    try:
        from scripts.download_rvc_assets import missing_rvc_assets

        missing = missing_rvc_assets(ROOT / "vendor" / "rvc")
        if missing:
            raise RuntimeError("RVC support files missing: " + ", ".join(missing))

        ffmpeg = _ffmpeg_path()
        if not ffmpeg:
            raise RuntimeError("FFmpeg is not available.")

        raw = out_dir / "sample-download"
        clip = out_dir / "sample.wav"
        stage_started = time.monotonic()
        sample_bytes = _download_sample(args.sample_url, raw)
        subprocess.run(
            [
                ffmpeg, "-y", "-i", str(raw), "-t", str(args.seconds),
                "-ac", "2", "-ar", "44100", str(clip),
            ],
            check=True,
            capture_output=True,
            timeout=180,
        )
        raw.unlink(missing_ok=True)
        import soundfile as sf

        clip_seconds = sf.info(str(clip)).duration
        if not 0 < clip_seconds <= args.seconds + 0.1:
            raise RuntimeError("FFmpeg produced an invalid or unexpectedly long test clip.")
        report["sample"] = {"bytes": sample_bytes, "duration_seconds": round(clip_seconds, 3)}
        report["stages"]["sample_prepare_seconds"] = round(time.monotonic() - stage_started, 1)

        stage_started = time.monotonic()
        model_path = _download_model(args.model_repo, args.model_file, VOICE_DIR)
        report["model"] = {
            "repo": args.model_repo,
            "file": args.model_file,
            "bytes": model_path.stat().st_size,
        }
        report["model_preflight"] = inspect_rvc_checkpoint(model_path)
        report["stages"]["model_download_seconds"] = round(time.monotonic() - stage_started, 1)

        import app

        stage_started = time.monotonic()
        cover_path, _status = app.generate(
            str(clip),
            model_path.name,
            0,
            1.0,
            0.85,
            "WAV",
            progress=lambda *args, **kwargs: None,
        )
        report["stages"]["generate_seconds"] = round(time.monotonic() - stage_started, 1)

        output_info = verify_cover_audio(Path(cover_path), expected_duration=clip_seconds)
        shutil.copy2(cover_path, out_dir / "cover.wav")
        report["output"] = output_info
        report["total_seconds"] = round(time.monotonic() - started, 1)
        report["result"] = "passed"
        print("E2E CHECK PASSED: audio sanity checks only; listen to cover.wav before judging quality.")
        return 0
    except Exception as exc:
        report["result"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"[-3000:]
        print(f"REAL CONVERSION CHECK FAILED: {report['error']}", file=sys.stderr)
        return 1
    finally:
        if model_path is not None:
            model_path.unlink(missing_ok=True)
        report["total_seconds"] = round(time.monotonic() - started, 1)
        (out_dir / "e2e-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
