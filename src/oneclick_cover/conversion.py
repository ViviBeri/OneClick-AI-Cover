from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import soundfile as sf

from oneclick_cover.settings import RVC_ROOT



def convert_voice_batch(
    input_vocals: list[Path],
    output_dir: Path,
    model_path: Path,
    pitch: int = 0,
    index_path: Path | None = None,
    index_rate: float = 0.0,
) -> dict[Path, Path]:
    """Convert a batch of vocals in one RVC process and reuse its loaded model."""
    inputs = [Path(path).resolve() for path in input_vocals]
    if not inputs:
        raise ValueError("At least one input vocal is required.")
    if any(not path.is_file() for path in inputs):
        missing = next(path for path in inputs if not path.is_file())
        raise RuntimeError(f"Input vocal file does not exist: {missing}")

    stems = [path.stem.casefold() for path in inputs]
    if len(stems) != len(set(stems)):
        raise ValueError("Batch input filenames must have unique stems.")

    cli = RVC_ROOT / "infer" / "cli.py"
    if not cli.is_file():
        raise RuntimeError(
            "RVC backend is missing. Run install.bat while connected to the internet, then retry."
        )
    backend_python = RVC_ROOT / ".venv" / "Scripts" / "python.exe"
    if not backend_python.is_file():
        raise RuntimeError(
            "RVC runtime is not installed. Run install.bat again while connected to the internet."
        )
    model = Path(model_path).resolve()
    if not model.is_file():
        raise RuntimeError(f"Voice model file does not exist: {model}")

    rate = float(index_rate)
    if not 0.0 <= rate <= 1.0:
        raise ValueError("RVC index rate must be between 0 and 1.")
    selected_index = Path(index_path).expanduser().resolve() if index_path else None
    if selected_index is not None and not selected_index.is_file():
        raise RuntimeError(f"RVC index file does not exist: {selected_index}")
    if selected_index is None:
        rate = 0.0

    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    outputs = {source: destination / f"{source.stem}.wav" for source in inputs}
    existing = [path for path in outputs.values() if path.exists()]
    if existing:
        raise FileExistsError(f"Batch output already exists: {existing[0]}")

    with tempfile.TemporaryDirectory(prefix=".rvc-batch-", dir=destination) as temp_name:
        input_dir = Path(temp_name)
        for source in inputs:
            shutil.copy2(source, input_dir / source.name)

        command = [
            str(backend_python),
            str(cli),
            "--model",
            str(model),
            "--input",
            str(input_dir),
            "--output",
            str(destination),
            "--pitch",
            str(int(pitch)),
            "--f0-method",
            "rmvpe",
            "--index-rate",
            str(rate),
            "--format",
            "wav",
        ]
        if selected_index is not None and rate > 0:
            command.extend(["--index", str(selected_index)])
        env = os.environ.copy()
        env.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        result = subprocess.run(
            command,
            cwd=str(RVC_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            details = (result.stderr or result.stdout or "No diagnostic output")[-5000:]
            raise RuntimeError(
                "RVC batch voice conversion failed. Check model compatibility and HuBERT/RMVPE assets.\\n\\n"
                + details
            )

    for source, output in outputs.items():
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(
                f"RVC batch completed without a usable output for {source.name}."
            )
        try:
            info = sf.info(str(output))
            if info.frames <= 0 or info.samplerate <= 0 or info.channels <= 0:
                raise RuntimeError("Invalid audio stream metadata.")
        except Exception as exc:
            raise RuntimeError(
                f"RVC batch created an unreadable output for {source.name}."
            ) from exc
    return outputs


def convert_voice(
    input_vocal: Path,
    output_vocal: Path,
    model_path: Path,
    pitch: int = 0,
    index_path: Path | None = None,
    index_rate: float = 0.0,
) -> None:
    cli = RVC_ROOT / "infer" / "cli.py"
    if not cli.exists():
        raise RuntimeError(
            "RVC backend is missing. Run install.bat while connected to the internet, then retry."
        )

    backend_python = RVC_ROOT / ".venv" / "Scripts" / "python.exe"
    if not backend_python.exists():
        raise RuntimeError(
            "RVC runtime is not installed. Run install.bat again while connected to the internet."
        )

    if not input_vocal.is_file():
        raise RuntimeError(f"Input vocal file does not exist: {input_vocal}")
    if not model_path.is_file():
        raise RuntimeError(f"Voice model file does not exist: {model_path}")

    rate = float(index_rate)
    if not 0.0 <= rate <= 1.0:
        raise ValueError("RVC index rate must be between 0 and 1.")
    selected_index = Path(index_path).expanduser().resolve() if index_path else None
    if selected_index is not None and not selected_index.is_file():
        raise RuntimeError(f"RVC index file does not exist: {selected_index}")
    if selected_index is None:
        rate = 0.0

    command = [
        str(backend_python),
        str(cli),
        "--model",
        str(model_path.resolve()),
        "--input",
        str(input_vocal.resolve()),
        "--output",
        str(output_vocal.resolve()),
        "--pitch",
        str(int(pitch)),
        "--f0-method",
        "rmvpe",
        "--index-rate",
        str(rate),
        "--overwrite",
    ]
    if selected_index is not None and rate > 0:
        command.extend(["--index", str(selected_index)])
    # Remove any stale file so a backend that exits 0 without writing cannot pass the output check.
    output_vocal.parent.mkdir(parents=True, exist_ok=True)
    output_vocal.unlink(missing_ok=True)

    env = os.environ.copy()
    env.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    result = subprocess.run(
        command,
        cwd=str(RVC_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        details = (result.stderr or result.stdout or "No diagnostic output")[-5000:]
        raise RuntimeError(
            "RVC voice conversion failed. Check model compatibility and HuBERT/RMVPE assets.\n\n"
            + details
        )

    if not output_vocal.exists() or output_vocal.stat().st_size == 0:
        raise RuntimeError(
            "RVC exited successfully but did not create the converted vocal file."
        )

    # A non-empty file can still be stale, truncated, or not audio at all.
    try:
        info = sf.info(str(output_vocal))
        if info.frames <= 0 or info.samplerate <= 0 or info.channels <= 0:
            raise RuntimeError("The converted audio has invalid stream metadata.")
    except Exception as exc:
        raise RuntimeError(
            "RVC created an output file, but it is not a readable audio file. "
            "Check the RVC backend logs and model compatibility."
        ) from exc
