import os
import pytest
from oneclick_cover import training


def test_training_launcher_explains_platform_limit(monkeypatch):
    monkeypatch.setattr(training.os, "name", "posix")
    with pytest.raises(RuntimeError, match="supports Windows only"):
        training.launch_training_ui()


def test_training_launcher_checks_backend_files(monkeypatch, tmp_path):
    monkeypatch.setattr(training.os, "name", "nt")
    monkeypatch.setattr(training, "RVC_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="entry point was not found"):
        training.launch_training_ui()
