from __future__ import annotations

import json
from pathlib import Path

import pytest

from oneclick_cover.pipeline import _write_timing_report, run_cover_pipeline


def _run_fake_pipeline(tmp_path: Path, report_path: Path, separate_fn=None) -> Path:
    output_dir = tmp_path / "outputs"
    output_dir.mkdir(exist_ok=True)
    source = tmp_path / "source.mp3"
    model = tmp_path / "authorized-model.pth"
    source.write_bytes(b"source fixture")
    model.write_bytes(b"model fixture")

    def transcode(_source: Path, destination: Path) -> None:
        destination.write_bytes(b"prepared audio")

    def separate(_audio: Path, job_dir: Path, **_kwargs):
        vocals = job_dir / "vocals.wav"
        instrumental = job_dir / "instrumental.wav"
        vocals.write_bytes(b"vocal stem")
        instrumental.write_bytes(b"instrumental stem")
        return vocals, instrumental

    def convert(_vocals: Path, destination: Path, _model: Path, _pitch: int) -> None:
        destination.write_bytes(b"converted vocal")

    def mix(_vocals: Path, _instrumental: Path, destination: Path, _vg: float, _ig: float):
        destination.write_bytes(b"mixed cover")

    return run_cover_pipeline(
        source,
        model,
        0,
        1.0,
        0.85,
        "WAV",
        output_dir,
        transcode_fn=transcode,
        separate_fn=separate_fn or separate,
        convert_fn=convert,
        match_sample_rate_fn=lambda converted, _reference, _destination: converted,
        mix_fn=mix,
        validate_audio_fn=lambda _path: None,
        validate_model_fn=lambda _path: None,
        timing_report_path=report_path,
    )


def test_pipeline_writes_path_free_stage_timing_report(tmp_path):
    report_path = tmp_path / "outputs" / "reports" / "timings.json"
    output = _run_fake_pipeline(tmp_path, report_path)

    assert output.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 1
    assert report["status"] == "completed"
    assert report["total_wall_seconds"] >= 0
    assert {
        "validate_audio",
        "validate_voice_model",
        "prepare_audio",
        "separate",
        "convert",
        "match_sample_rate",
        "mix",
        "validate_output",
    }.issubset(report["stages_seconds"])
    assert all(value >= 0 for value in report["stages_seconds"].values())
    serialized = json.dumps(report)
    assert str(tmp_path / "source.mp3") not in serialized
    assert str(tmp_path / "authorized-model.pth") not in serialized


def test_pipeline_preserves_failure_timing_report_after_job_cleanup(tmp_path):
    report_path = tmp_path / "outputs" / "reports" / "failed-run.json"

    def fail_separation(*_args, **_kwargs):
        raise RuntimeError("synthetic separation failure")

    with pytest.raises(RuntimeError, match="synthetic separation failure"):
        _run_fake_pipeline(tmp_path, report_path, separate_fn=fail_separation)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["failure_type"] == "RuntimeError"
    assert "separate" in report["stages_seconds"]
    assert not list((tmp_path / "outputs").glob("cover_*"))


def test_timing_report_rejects_paths_outside_output_directory(tmp_path):
    output_root = tmp_path / "outputs"
    outside_path = tmp_path / "outside" / "timings.json"

    with pytest.raises(ValueError, match="inside the output directory"):
        _write_timing_report(output_root, outside_path, {"schema_version": 1})

    assert not outside_path.exists()
