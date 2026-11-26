from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import scripts.benchmark as benchmark
from scripts.benchmark import ProcessTreeMemorySampler, _write_report


def test_memory_sampler_degrades_when_psutil_is_not_installed(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", None)

    sampler = ProcessTreeMemorySampler()
    sampler.start()
    sampler.stop()

    result = sampler.as_dict()
    assert result["available"] is False
    assert "psutil" in result["reason"]


def test_memory_sampler_rejects_unreasonable_sampling_interval():
    with pytest.raises(ValueError, match="at least 10 ms"):
        ProcessTreeMemorySampler(interval_ms=5)


def test_benchmark_report_uses_fixed_output_location(tmp_path):
    report_path = _write_report(tmp_path / "outputs", {"schema_version": 1})

    assert report_path == (tmp_path / "outputs").resolve() / "benchmark-report.json"
    assert report_path.is_file()



def test_benchmark_main_reads_pipeline_timing_report_from_isolated_run_dir(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.wav"
    model = tmp_path / "authorized-model.pth"
    output_root = tmp_path / "benchmarks"
    source.write_bytes(b"audio")
    model.write_bytes(b"authorized model")

    class FakeSampler:
        def __init__(self, interval_ms):
            self.interval_ms = interval_ms

        def start(self):
            pass

        def stop(self):
            pass

        def as_dict(self):
            return {"available": False}

    def fake_pipeline(
        _source, _model, _pitch, _vocal, _instrumental, _format, output_dir, **_kwargs
    ):
        diagnostics = output_dir / "diagnostics"
        diagnostics.mkdir(parents=True)
        (diagnostics / "run.timings.json").write_text(
            json.dumps({"schema_version": 1, "total_wall_seconds": 2.0}),
            encoding="utf-8",
        )

    monkeypatch.setattr(benchmark, "ProcessTreeMemorySampler", FakeSampler)
    monkeypatch.setattr(benchmark, "_audio_duration", lambda _path: 4.0)
    monkeypatch.setattr(
        benchmark, "_system_metadata", lambda: {"python_version": "3.x"}
    )
    monkeypatch.setattr(benchmark, "run_cover_pipeline", fake_pipeline)

    result = benchmark.main(
        [
            "--input",
            str(source),
            "--model",
            str(model),
            "--output-dir",
            str(output_root),
        ]
    )
    assert result == 0

    run_dirs = list(output_root.glob("run_*"))
    assert len(run_dirs) == 1
    report_path = run_dirs[0] / "benchmark-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 1
    assert report["benchmark"]["audio_duration_seconds"] == 4.0
    assert report["benchmark"]["real_time_factor"] == 2.0
