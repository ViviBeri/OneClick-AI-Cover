from __future__ import annotations

import sys

import pytest

from scripts.benchmark import ProcessTreeMemorySampler, _resolve_report_path


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


def test_benchmark_report_path_is_confined_to_output_directory(tmp_path):
    output_root = tmp_path / "outputs"

    safe_path = _resolve_report_path(output_root, Path("reports/result.json"))
    assert safe_path == output_root.resolve() / "reports" / "result.json"

    with pytest.raises(ValueError, match="inside the output directory"):
        _resolve_report_path(output_root, Path("../outside.json"))
