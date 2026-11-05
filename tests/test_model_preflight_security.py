from pathlib import Path
import os
import pickle
import zipfile

import pytest

from oneclick_cover.model_preflight import inspect_rvc_checkpoint


def make_checkpoint(path: Path, metadata: object) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("archive/data.pkl", pickle.dumps(metadata, protocol=4))
    return path


def test_preflight_reports_common_rvc_markers_without_loading(tmp_path):
    path = make_checkpoint(
        tmp_path / "candidate.pth",
        {
            "weight": {"emb_g.weight": "tensor-placeholder"},
            "config": ["config-placeholder"],
            "version": "v2",
            "f0": True,
        },
    )

    result = inspect_rvc_checkpoint(path)

    assert "PyTorch ZIP with data.pkl metadata" in result
    assert "weight, speaker_embedding, config, version, f0" in result
    assert "common RVC checkpoint marker strings are present" in result
    assert "does not read tensor shapes" in result
    assert "torch.load()" in result


def test_preflight_does_not_claim_compatibility_for_incomplete_markers(tmp_path):
    path = make_checkpoint(tmp_path / "unknown.pth", {"metadata": "unknown"})

    result = inspect_rvc_checkpoint(path)

    assert "marker strings are incomplete" in result
    assert "compatibility is unclear" in result


def test_preflight_rejects_non_pth_files(tmp_path):
    path = tmp_path / "model.bin"
    path.write_bytes(b"not a model")

    with pytest.raises(ValueError, match="Only .pth"):
        inspect_rvc_checkpoint(path)


def test_preflight_handles_non_zip_legacy_file_without_deserializing(tmp_path):
    path = tmp_path / "legacy.pth"
    path.write_bytes(b"legacy-checkpoint-placeholder")

    result = inspect_rvc_checkpoint(path)

    assert "not a recognized PyTorch ZIP" in result
    assert "No pickle or tensor data was loaded" in result


def test_preflight_rejects_oversized_metadata(tmp_path):
    path = tmp_path / "oversized.pth"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("data.pkl", b"x" * (16 * 1024 * 1024 + 1))

    with pytest.raises(ValueError, match="16 MiB"):
        inspect_rvc_checkpoint(path)


def test_preflight_does_not_execute_pickle_reduce_payload(tmp_path):
    marker = tmp_path / "pickle-executed.txt"

    class Payload:
        def __reduce__(self):
            return (os.system, (f"echo executed > \"{marker}\"",))

    path = make_checkpoint(tmp_path / "untrusted.pth", {"metadata": Payload()})

    report = inspect_rvc_checkpoint(path)

    assert "Static preflight" in report
    assert not marker.exists()
