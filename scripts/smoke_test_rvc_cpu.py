"""Run a real 15-second RVC CPU inference smoke test with a user-supplied model."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

import soundfile as sf

from oneclick_cover.settings import RVC_ROOT

REQUIRED_ASSETS = (
    Path("assets/hubert_base/config.json"),
    Path("assets/hubert_base/preprocessor_config.json"),
    Path("assets/hubert_base/pytorch_model.bin"),
    Path("assets/rmvpe/rmvpe.pt"),
)


def run_cpu_smoke_test(input_path: Path, model_path: Path, output_path: Path) -> str:
    source = Path(input_path).resolve()
    model = Path(model_path).resolve()
    output = Path(output_path).resolve()

    if not source.is_file() or source.suffix.lower() != ".wav":
        raise ValueError("Provide an existing 15-second WAV vocal recording you are authorized to process.")
    if not model.is_file() or model.suffix.lower() != ".pth":
        raise ValueError("Provide an existing inference-ready .pth model you are authorized to use.")

    source_info = sf.info(str(source))
    if not 14.5 <= source_info.duration <= 15.5:
        raise ValueError(f"Input must be approximately 15 seconds; found {source_info.duration:.2f}s.")

    missing = [str(RVC_ROOT / item) for item in REQUIRED_ASSETS if not (RVC_ROOT / item).is_file()]
    if missing:
        raise RuntimeError(
            "Required RVC inference assets are missing. Run install.bat again. Missing: "
            + ", ".join(missing)
        )

    cli = RVC_ROOT / "infer" / "cli.py"
    backend_python = RVC_ROOT / ".venv" / "Scripts" / "python.exe"
    if not cli.is_file() or not backend_python.is_file():
        raise RuntimeError("The pinned RVC backend/runtime is missing. Run install.bat again.")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    command = [
        str(backend_python),
        str(cli),
        "--model", str(model),
        "--input", str(source),
        "--output", str(output),
        "--pitch", "0",
        "--f0-method", "rmvpe",
        "--index-rate", "0",
        "--overwrite",
    ]
    result = subprocess.run(
        command,
        cwd=str(RVC_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )
    diagnostic = (result.stdout or "") + "\n" + (result.stderr or "")
    if result.returncode:
        raise RuntimeError("RVC CPU smoke test failed:\n" + diagnostic[-8000:])
    if not re.search(r"(?:当前设备|current device)\s*[:：]\\s*cpu", diagnostic, re.IGNORECASE):
        raise RuntimeError(
            "RVC did not report CPU as its inference device. "
            "This test requires CPU execution. Backend output:\n" + diagnostic[-4000:]
        )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("RVC exited without producing an output file.")

    output_info = sf.info(str(output))
    if output_info.frames <= 0 or not 13.0 <= output_info.duration <= 17.0:
        raise RuntimeError(
            f"RVC output duration is invalid: {output_info.duration:.2f}s."
        )
    return (
        f"PASS: RVC CPU inference completed.\n"
        f"Input: {source_info.duration:.2f}s, {source_info.samplerate} Hz\n"
        f"Output: {output_info.duration:.2f}s, {output_info.samplerate} Hz\n"
        f"Output file: {output}\n"
        "This verifies one local model/backend combination only; it is not a general compatibility guarantee."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Authorized 15-second WAV vocal clip.")
    parser.add_argument("--model", required=True, type=Path, help="Trusted, authorized RVC inference .pth model.")
    parser.add_argument("--output", required=True, type=Path, help="Output WAV path.")
    args = parser.parse_args()
    print(run_cpu_smoke_test(args.input, args.model, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
