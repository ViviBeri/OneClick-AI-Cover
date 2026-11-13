from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import app


def make_job(index, *, status="completed", output_path=None, error=None):
    return SimpleNamespace(
        id=f"job-{index}",
        status=SimpleNamespace(value=status),
        progress=1.0 if status == "completed" else 0.4,
        message=f"Stage {index}",
        created_at=datetime(2026, 11, 13, tzinfo=timezone.utc),
        output_path=Path(output_path) if output_path else None,
        error=error,
    )


def test_job_history_is_newest_first_and_hides_full_output_paths():
    jobs = [
        make_job(1, output_path="/private/output/cover.wav"),
        make_job(2, status="failed", error="Conversion failed"),
    ]

    rows = app.format_job_history(jobs)

    assert [row[0] for row in rows] == ["job-2", "job-1"]
    assert rows[0][1] == "failed"
    assert rows[0][6] == "Conversion failed"
    assert rows[1][5] == "cover.wav"
    assert "/private/output" not in str(rows)


def test_job_history_limits_results_to_latest_100():
    rows = app.format_job_history([make_job(index) for index in range(125)])

    assert len(rows) == 100
    assert rows[0][0] == "job-124"
    assert rows[-1][0] == "job-25"


def test_refresh_job_history_is_empty_before_app_start(monkeypatch):
    monkeypatch.setattr(app, "_active_job_store", None)

    assert app.refresh_job_history() == []
