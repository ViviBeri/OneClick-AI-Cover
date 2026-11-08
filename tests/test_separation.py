from __future__ import annotations

import io
import threading
from pathlib import Path

import pytest

from oneclick_cover import separation


class FakeProcess:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout = io.StringIO(stdout)
        self.returncode = returncode
        self.killed = False

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


def test_separate_vocals_streams_progress_and_uses_low_memory_options(monkeypatch, tmp_path):
    commands = []
    output_root = tmp_path / "job" / "separated"

    def fake_popen(command, **kwargs):
        commands.append(command)
        output_dir = Path(command[command.index("--out") + 1])
        result_dir = output_dir / "htdemucs" / "song"
        result_dir.mkdir(parents=True)
        (result_dir / "vocals.wav").write_bytes(b"vocals")
        (result_dir / "no_vocals.wav").write_bytes(b"instrumental")
        return FakeProcess("  25%|##\r 100%|########\rDone\n")

    monkeypatch.setattr(separation.subprocess, "Popen", fake_popen)
    updates = []

    vocals, instrumental = separation.separate_vocals(
        tmp_path / "song.wav",
        tmp_path / "job",
        progress=lambda fraction, message: updates.append((fraction, message)),
        device="cpu",
        segment=4,
        timeout=30,
        shifts=0,
    )

    assert vocals.read_bytes() == b"vocals"
    assert instrumental.read_bytes() == b"instrumental"
    command = commands[0]
    assert command[1].endswith("scripts/demucs_runner.py")
    assert command[command.index("--segment") + 1] == "4"
    assert command[command.index("--shifts") + 1] == "0"
    assert command[command.index("-d") + 1] == "cpu"
    assert command[-1] == str(tmp_path / "song.wav")
    assert any(fraction == 0.25 for fraction, _ in updates)
    assert any(fraction == 1.0 for fraction, _ in updates)


def test_separate_vocals_auto_device_leaves_device_selection_to_demucs(monkeypatch, tmp_path):
    commands = []

    def fake_popen(command, **kwargs):
        commands.append(command)
        output_dir = Path(command[command.index("--out") + 1])
        result_dir = output_dir / "htdemucs" / "song"
        result_dir.mkdir(parents=True)
        (result_dir / "vocals.wav").touch()
        (result_dir / "no_vocals.wav").touch()
        return FakeProcess("Done\n")

    monkeypatch.setattr(separation.subprocess, "Popen", fake_popen)
    separation.separate_vocals(tmp_path / "song.wav", tmp_path / "job", device="auto")
    assert "-d" not in commands[0]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"device": "tpu"}, "device must be one of"),
        ({"segment": 8.0}, "segment size must be between"),
        ({"segment": 4.5}, "segment size must be a whole number"),
        ({"segment": float("nan")}, "segment size must be between"),
        ({"timeout": 0}, "timeout must be a positive"),
        ({"shifts": -1}, "shifts must be a non-negative integer"),
        ({"shifts": True}, "shifts must be a non-negative integer"),
    ],
)
def test_separate_vocals_validates_performance_settings(tmp_path, kwargs, message):
    with pytest.raises(ValueError, match=message):
        separation.separate_vocals(tmp_path / "song.wav", tmp_path / "job", **kwargs)


def test_separate_vocals_reports_demucs_failure_output(monkeypatch, tmp_path):
    monkeypatch.setattr(
        separation.subprocess,
        "Popen",
        lambda *args, **kwargs: FakeProcess("model download failed\n", returncode=2),
    )
    with pytest.raises(RuntimeError, match="model download failed"):
        separation.separate_vocals(tmp_path / "song.wav", tmp_path / "job")


def test_separate_vocals_kills_process_when_timeout_expires(monkeypatch, tmp_path):
    released = threading.Event()

    class BlockingStdout:
        def read(self, size=1):
            released.wait(timeout=2)
            return ""

    class HangingProcess:
        stdout = BlockingStdout()
        killed = False

        def poll(self):
            return None if not self.killed else -9

        def kill(self):
            self.killed = True
            released.set()

        def wait(self, timeout=None):
            return -9

    process = HangingProcess()
    monkeypatch.setattr(separation.subprocess, "Popen", lambda *args, **kwargs: process)

    with pytest.raises(TimeoutError, match="exceeded the 0-second timeout"):
        separation.separate_vocals(
            tmp_path / "song.wav",
            tmp_path / "job",
            timeout=0.01,
        )
    assert process.killed
