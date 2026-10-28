from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:7860/"


def check_imports() -> None:
    modules = ("gradio", "demucs", "numpy", "soundfile", "imageio_ffmpeg")
    for name in modules:
        __import__(name)
        print(f"IMPORT OK: {name}", flush=True)


def wait_for_server(process: subprocess.Popen[str], timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: str | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"app.py exited early with code {process.returncode}. "
                "See captured app output in the CI logs."
            )
        try:
            request = urllib.request.Request(
                URL, headers={"User-Agent": "OneClick-AI-Cover-CI-Smoke-Test"}
            )
            with urllib.request.urlopen(request, timeout=2) as response:
                body = response.read(1_000_000).decode("utf-8", errors="replace")
                if response.status != 200:
                    raise RuntimeError(f"Unexpected HTTP status: {response.status}")
                if "OneClick-AI-Cover" not in body:
                    raise RuntimeError(
                        "The Gradio page returned HTTP 200 but did not contain "
                        "the expected app title."
                    )
                print(f"HTTP SMOKE TEST OK: {URL} (status {response.status})")
                return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
            time.sleep(1)
    raise TimeoutError(
        f"Gradio app did not become ready within {timeout:.0f}s. "
        f"Last connection error: {last_error}"
    )


def main() -> int:
    check_imports()
    env = os.environ.copy()
    env["GRADIO_ANALYTICS_ENABLED"] = "False"
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "app.py")],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_server(process)
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.stdout:
            output = process.stdout.read()
            if output.strip():
                print("--- app.py startup output ---")
                print(output[-12000:])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        raise
