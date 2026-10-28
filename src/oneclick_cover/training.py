from __future__ import annotations

import os
import subprocess
from pathlib import Path

from oneclick_cover.settings import RVC_ROOT


def launch_training_ui() -> str:
    """Launch the upstream RVC WebUI in a separate Windows console."""
    if os.name != "nt":
        raise RuntimeError(
            "The one-click launcher currently supports Windows only. "
            "Start the upstream RVC WebUI manually from the backend folder."
        )

    entrypoint = RVC_ROOT / "webui.py"
    python = RVC_ROOT / ".venv" / "Scripts" / "python.exe"

    if not entrypoint.is_file():
        raise RuntimeError(
            "The RVC WebUI entry point was not found. Run install.bat again "
            "and confirm the downloaded backend contains webui.py."
        )
    if not python.is_file():
        raise RuntimeError(
            "The RVC environment is missing. Run install.bat again before "
            "opening voice training."
        )

    try:
        subprocess.Popen(
            [str(python), str(entrypoint)],
            cwd=str(RVC_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            close_fds=True,
        )
    except OSError as exc:
        raise RuntimeError(f"Could not start the RVC training interface: {exc}") from exc

    return (
        "RVC is starting in a separate console window. Wait for it to print "
        "its local web address, then open that address in your browser. "
        "Keep the console open while training. This launches the upstream "
        "RVC interface; training steps are not yet automated by this app."
    )
