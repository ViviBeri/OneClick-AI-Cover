"""Optional python-audio-separator adapter using an isolated Python runtime."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ProgressCallback = Callable[[float, str], None]
_WORKER = Path(__file__).with_name("audio_separator_worker.py")


@dataclass(frozen=True)
class AudioSeparatorBackend:
    """Run MDX/RoFormer separation without changing the core Python environment."""

    name: str = "audio-separator"

    def separate(
        self,
        input_wav: Path,
        job_dir: Path,
        progress: ProgressCallback | None = None,
        *,
        device: str = "cpu",
        segment: float = 5,
        timeout: float = 1800,
    ) -> tuple[Path, Path]:
        del device, segment  # Device and architecture tuning belong to the isolated runtime.
        python_executable = os.environ.get("ONECLICK_AUDIO_SEPARATOR_PYTHON")
        model_value = os.environ.get("ONECLICK_AUDIO_SEPARATOR_MODEL_PATH")
        if not python_executable or not model_value:
            raise RuntimeError(
                "Optional Audio Separator is not configured. Set "
                "ONECLICK_AUDIO_SEPARATOR_PYTHON and ONECLICK_AUDIO_SEPARATOR_MODEL_PATH."
            )

        executable = Path(python_executable).expanduser()
        model_path = Path(model_value).expanduser().resolve()
        source = Path(input_wav).resolve()
        workspace = Path(job_dir).resolve()
        if not executable.is_file():
            raise RuntimeError(f"Audio Separator Python runtime was not found: {executable}")
        if not model_path.is_file():
            raise RuntimeError(
                f"Audio Separator model was not found: {model_path}. "
                "Model downloads are explicit and are never started by this backend."
            )
        if not source.is_file():
            raise FileNotFoundError(f"Input audio was not found: {source}")

        workspace.mkdir(parents=True, exist_ok=True)
        if progress is not None:
            progress(0.05, "Starting optional MDX/RoFormer separation")

        command = [
            str(executable),
            str(_WORKER),
            str(source),
            str(workspace),
            str(model_path),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=max(1.0, float(timeout)),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("Audio Separator exceeded the configured processing timeout.") from exc
        except OSError as exc:
            raise RuntimeError(f"Could not start the Audio Separator runtime: {exc}") from exc

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-4000:]
            raise RuntimeError(
                "Audio Separator failed"
                + (f": {detail}" if detail else f" (exit code {completed.returncode}).")
            )

        try:
            result = json.loads(completed.stdout.strip().splitlines()[-1])
            vocals = Path(result["vocals"]).resolve()
            instrumental = Path(result["instrumental"]).resolve()
        except (IndexError, KeyError, json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError("Audio Separator returned an invalid result.") from exc

        for output in (vocals, instrumental):
            if output.parent != workspace or not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError("Audio Separator returned an invalid or empty stem path.")

        if progress is not None:
            progress(1.0, "Advanced separation complete")
        return vocals, instrumental
