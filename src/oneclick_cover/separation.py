from __future__ import annotations

import math
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path


_PROGRESS_RE = re.compile(r"(\d{1,3})%")


def separate_vocals(
    input_wav: Path,
    job_dir: Path,
    progress=None,
    *,
    device: str = "cpu",
    segment: float = 5.0,
    timeout: float = 1800,
    shifts: int = 1,
) -> tuple[Path, Path]:
    """Separate vocals with streamed progress and a hard process timeout.

    progress is an optional callback receiving (fraction, message).
    CPU is the default to keep peak memory use predictable on low-spec PCs.
    """
    device = str(device).strip().lower()
    if device not in {"cpu", "auto", "cuda"}:
        raise ValueError("Demucs device must be one of: cpu, auto, cuda.")

    try:
        segment = float(segment)
    except (TypeError, ValueError) as exc:
        raise ValueError("Demucs segment size must be a number between 2.0 and 7.8 seconds.") from exc
    if not math.isfinite(segment) or not 2.0 <= segment <= 7.8:
        raise ValueError("Demucs segment size must be between 2.0 and 7.8 seconds.")

    if isinstance(shifts, bool) or not isinstance(shifts, int) or shifts < 0:
        raise ValueError("Demucs shifts must be a non-negative integer.")

    try:
        timeout = float(timeout)
    except (TypeError, ValueError) as exc:
        raise ValueError("Demucs timeout must be a positive number of seconds.") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Demucs timeout must be a positive number of seconds.")

    input_wav = Path(input_wav)
    job_dir = Path(job_dir)
    output_root = job_dir / "separated"
    output_root.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "demucs.separate",
        "--two-stems",
        "vocals",
        "-n",
        "htdemucs",
        "--segment",
        str(segment),
        "--shifts",
        str(shifts),
        "--out",
        str(output_root),
    ]
    if device != "auto":
        command.extend(["-d", device])
    command.append(str(input_wav))

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        raise RuntimeError(f"Could not start Demucs: {exc}") from exc

    events: queue.Queue[str | None] = queue.Queue()
    output_tail = ""
    deadline = time.monotonic() + timeout

    def read_output() -> None:
        # Demucs/tqdm commonly updates with carriage returns rather than newlines.
        # Read characters so those updates reach the UI while the process is running.
        try:
            if process.stdout is not None:
                chunk = ""
                while True:
                    char = process.stdout.read(1)
                    if not char:
                        break
                    if char in "\r\n":
                        if chunk:
                            events.put(chunk)
                            chunk = ""
                    else:
                        chunk += char
                if chunk:
                    events.put(chunk)
        finally:
            events.put(None)

    reader = threading.Thread(target=read_output, name="demucs-output-reader", daemon=True)
    reader.start()

    timed_out = False
    last_fraction = 0.0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        try:
            message = events.get(timeout=min(0.25, remaining))
        except queue.Empty:
            if process.poll() is not None and not reader.is_alive():
                break
            continue
        if message is None:
            break

        output_tail = (output_tail + message + "\n")[-4000:]
        matches = _PROGRESS_RE.findall(message)
        if progress is not None:
            try:
                if matches:
                    last_fraction = min(1.0, max(last_fraction, int(matches[-1]) / 100))
                progress(last_fraction, message.strip()[-160:])
            except Exception:
                # UI progress reporting must not interrupt the audio subprocess.
                pass

    if timed_out:
        process.kill()
        process.wait()
        reader.join(timeout=1)
        detail = output_tail.strip()[-1500:]
        suffix = f" Last output: {detail}" if detail else ""
        raise TimeoutError(
            f"Demucs separation exceeded the {int(timeout)}-second timeout and was stopped.{suffix}"
        )

    try:
        return_code = process.wait(timeout=max(0.01, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        reader.join(timeout=1)
        detail = output_tail.strip()[-1500:]
        suffix = f" Last output: {detail}" if detail else ""
        raise TimeoutError(
            f"Demucs separation exceeded the {int(timeout)}-second timeout and was stopped.{suffix}"
        )
    reader.join(timeout=1)
    if return_code:
        detail = output_tail.strip()[-4000:] or "No diagnostic output"
        raise RuntimeError(
            "Demucs separation failed. Confirm internet access for the first model download, "
            f"then retry. Details:\n{detail}"
        )

    candidates = list(output_root.rglob("vocals.wav"))
    if not candidates:
        raise RuntimeError("Demucs finished but its vocals.wav output was not found.")
    vocals = candidates[0]
    instrumental = vocals.with_name("no_vocals.wav")
    if not instrumental.exists():
        raise RuntimeError("Demucs did not produce no_vocals.wav.")
    return vocals, instrumental
