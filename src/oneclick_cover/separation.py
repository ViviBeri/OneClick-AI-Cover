from __future__ import annotations
import subprocess, sys
from pathlib import Path
def separate_vocals(input_wav: Path, job_dir: Path, progress=None) -> tuple[Path, Path]:
    output_root = job_dir / "separated"
    command = [sys.executable, "-m", "demucs.separate", "--two-stems", "vocals", "-n", "htdemucs", "--out", str(output_root), str(input_wav)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout or "No diagnostic output")[-4000:]
        raise RuntimeError("Demucs separation failed. Confirm internet access for the first model download, then retry. Details:\n" + detail)
    candidates = list(output_root.rglob("vocals.wav"))
    if not candidates: raise RuntimeError("Demucs finished but its vocals.wav output was not found.")
    vocals = candidates[0]; instrumental = vocals.with_name("no_vocals.wav")
    if not instrumental.exists(): raise RuntimeError("Demucs did not produce no_vocals.wav.")
    return vocals, instrumental
