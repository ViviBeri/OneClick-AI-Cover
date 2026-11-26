"""Run a real local cover pipeline and capture timing plus sampled RSS metrics.

Install the optional memory sampler with:
    python -m pip install -e ".[benchmark]"
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import os
import tempfile
import threading
import time
from pathlib import Path
from uuid import uuid4
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oneclick_cover.pipeline import run_cover_pipeline


class ProcessTreeMemorySampler:
    """Sample aggregate RSS for this process and its descendants."""

    def __init__(self, interval_ms: int = 100) -> None:
        if interval_ms < 10:
            raise ValueError("Memory sampling interval must be at least 10 ms.")
        self.interval_ms = interval_ms
        self.interval_seconds = interval_ms / 1000.0
        self._psutil: Any = None
        self._process: Any = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._baseline: int | None = None
        self._peak: int | None = None
        self._samples = 0

        try:
            import psutil
        except ImportError:
            return
        self._psutil = psutil
        self._process = psutil.Process()

    def _read_process_tree_rss(self) -> int | None:
        if self._process is None:
            return None
        processes = [self._process]
        try:
            processes.extend(self._process.children(recursive=True))
        except self._psutil.Error:
            pass

        total = 0
        for process in processes:
            try:
                total += int(process.memory_info().rss)
            except self._psutil.Error:
                continue
        return total

    def _record_sample(self) -> None:
        value = self._read_process_tree_rss()
        if value is None:
            return
        if self._peak is None or value > self._peak:
            self._peak = value
        self._samples += 1

    def _sample_loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self._record_sample()

    def start(self) -> None:
        if self._process is None:
            return
        self._baseline = self._read_process_tree_rss()
        self._peak = self._baseline
        self._samples = 1 if self._baseline is not None else 0
        self._thread = threading.Thread(
            target=self._sample_loop,
            name="benchmark-memory-sampler",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(timeout=max(1.0, self.interval_seconds * 4))
        self._record_sample()

    def as_dict(self) -> dict[str, object]:
        if self._process is None:
            return {
                "available": False,
                "reason": 'psutil is not installed. Install the optional dependency with python -m pip install -e ".[benchmark]".',
            }
        return {
            "available": True,
            "scope": "sum of sampled RSS for the benchmark process and descendants",
            "sampling_interval_ms": self.interval_ms,
            "baseline_rss_bytes": self._baseline,
            "peak_sampled_rss_bytes": self._peak,
            "sample_count": self._samples,
            "limitation": (
                "This is a sampled process-tree RSS peak, not an exact physical-memory "
                "peak. Short spikes between samples may be missed, and summed RSS can "
                "count shared pages more than once."
            ),
        }


def _system_metadata() -> dict[str, object]:
    import torch

    metadata: dict[str, object] = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or None,
        "torch_version": str(torch.__version__),
        "cuda_available": bool(torch.cuda.is_available()),
        "gpu_name": (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        ),
    }
    try:
        import psutil
    except ImportError:
        metadata["total_ram_bytes"] = None
    else:
        metadata["total_ram_bytes"] = int(psutil.virtual_memory().total)
    return metadata


def _audio_duration(path: Path) -> float | None:
    try:
        import soundfile as sf

        return float(sf.info(str(path)).duration)
    except (OSError, RuntimeError, ValueError):
        return None


def _write_report(output_root: Path, report: dict[str, object]) -> Path:
    """Atomically write the benchmark report to a fixed output location."""
    root = output_root.resolve()
    path = root / "benchmark-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(".benchmark-report.json.tmp")
    try:
        temporary.write_text(
            json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark one local Demucs-to-RVC cover conversion."
    )
    parser.add_argument("--input", type=Path, required=True, help="Authorized source audio.")
    parser.add_argument("--model", type=Path, required=True, help="Authorized RVC .pth model.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--format", choices=("WAV", "MP3"), default="WAV")
    parser.add_argument("--pitch", type=int, default=0, help="RVC semitone shift.")
    parser.add_argument("--device", choices=("cpu", "auto", "cuda"), default="cpu")
    parser.add_argument("--demucs-segment", type=float, default=5.0)
    parser.add_argument("--demucs-timeout", type=float, default=1800.0)
    parser.add_argument("--sample-interval-ms", type=int, default=100)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input.is_file():
        raise SystemExit(f"Input audio does not exist: {args.input}")
    if not args.model.is_file():
        raise SystemExit(f"RVC model does not exist: {args.model}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_output_dir = args.output_dir.resolve() / f"run_{uuid4().hex}"
    run_output_dir.mkdir(parents=True, exist_ok=False)
    report_path = run_output_dir / "benchmark-report.json"
    timing_dir = run_output_dir / "diagnostics"
    duration = _audio_duration(args.input)
    system = _system_metadata()
    sampler = ProcessTreeMemorySampler(args.sample_interval_ms)
    exit_code = 0

    sampler.start()
    try:
        run_cover_pipeline(
            args.input,
            args.model,
            args.pitch,
            1.0,
            0.85,
            args.format,
            run_output_dir,
            demucs_device=args.device,
            demucs_segment=args.demucs_segment,
            demucs_timeout=args.demucs_timeout,
        )
    except Exception as exc:
        exit_code = 1
        print(
            f"Benchmark pipeline failed ({type(exc).__name__}): {exc}",
            file=sys.stderr,
        )
    finally:
        sampler.stop()

    timing_reports = sorted(timing_dir.glob("*.timings.json"))
    if len(timing_reports) == 1:
        report = json.loads(timing_reports[0].read_text(encoding="utf-8"))
        report["benchmark"] = {
            "system": system,
            "audio_duration_seconds": duration,
            "real_time_factor": (
                round(duration / report["total_wall_seconds"], 6)
                if duration is not None and report.get("total_wall_seconds", 0) > 0
                else None
            ),
            "memory": sampler.as_dict(),
        }
        report_path = _write_report(args.output_dir, report)
    else:
        print("Timing report was not created; inspect the pipeline error.", file=sys.stderr)
        return 1

    print(f"Benchmark report written: {report_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
