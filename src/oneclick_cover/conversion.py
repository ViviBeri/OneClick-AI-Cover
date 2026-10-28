from __future__ import annotations
import os, subprocess
from pathlib import Path
from oneclick_cover.settings import RVC_ROOT
def convert_voice(input_vocal: Path, output_vocal: Path, model_path: Path, pitch: int = 0) -> None:
    cli = RVC_ROOT / "infer" / "cli.py"
    if not cli.exists(): raise RuntimeError("RVC backend is missing. Run install.bat while connected to the internet, then retry.")
    backend_python = RVC_ROOT / ".venv" / "Scripts" / "python.exe"
    if not backend_python.exists(): raise RuntimeError("RVC runtime is not installed. Run install.bat again while connected to the internet.")
    command = [str(backend_python), str(cli), "--model", str(model_path.resolve()), "--input", str(input_vocal.resolve()), "--output", str(output_vocal.resolve()), "--pitch", str(int(pitch)), "--f0-method", "rmvpe", "--index-rate", "0", "--overwrite"]
    env = os.environ.copy(); env.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    result = subprocess.run(command, cwd=str(RVC_ROOT), env=env, capture_output=True, text=True, check=False)
    if result.returncode:
        details = (result.stderr or result.stdout or "No diagnostic output")[-5000:]
        raise RuntimeError("RVC voice conversion failed. Check model compatibility and HuBERT/RMVPE assets.\n\n" + details)
    if not output_vocal.exists() or output_vocal.stat().st_size == 0: raise RuntimeError("RVC exited successfully but did not create the converted vocal file.")
