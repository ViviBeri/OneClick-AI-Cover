from __future__ import annotations

import sys

import pytest

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
