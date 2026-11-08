from pathlib import Path
from types import SimpleNamespace
import hashlib

import pytest

from scripts import download_rvc_assets as assets


def test_downloads_all_pinned_assets_and_verifies_checksums(tmp_path, monkeypatch):
    payloads = {
        name: (b"unit-test-asset-" + name.encode("utf-8"))
        for name in assets.ASSETS
    }
    manifest = {}
    for name, original in assets.ASSETS.items():
        metadata = dict(original)
        metadata["size"] = len(payloads[name])
        metadata["sha256"] = hashlib.sha256(payloads[name]).hexdigest()
        manifest[name] = metadata
    monkeypatch.setattr(assets, "ASSETS", manifest)

    class FakeApi:
        def __init__(self, token=False):
            assert token is False

        def model_info(self, repo_id, revision, files_metadata, token):
            assert repo_id == assets.REPO_ID
            assert revision == assets.REVISION
            assert files_metadata is True
            assert token is False
            return SimpleNamespace(
                gated=False,
                siblings=[
                    SimpleNamespace(rfilename=name, size=meta["size"])
                    for name, meta in assets.ASSETS.items()
                ],
            )

    downloaded = []

    def fake_download(repo_id, filename, revision, token):
        assert repo_id == assets.REPO_ID
        assert revision == assets.REVISION
        assert token is False
        path = tmp_path / "hub-cache" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payloads[filename])
        downloaded.append(filename)
        return path

    installed = assets.download_rvc_assets(
        tmp_path / "rvc",
        downloader=fake_download,
        api=FakeApi(),
    )

    assert len(installed) == 4
    assert set(downloaded) == set(manifest)
    for name, meta in manifest.items():
        destination = tmp_path / "rvc" / meta["destination"]
        assert destination.read_bytes() == payloads[name]


def test_rejects_gated_asset_repository(tmp_path):
    class GatedApi:
        def __init__(self, token=False):
            assert token is False

        def model_info(self, *args, **kwargs):
            return SimpleNamespace(gated=True, siblings=[])

    with pytest.raises(RuntimeError, match="gated"):
        assets.download_rvc_assets(tmp_path, downloader=lambda **kwargs: None, api=GatedApi())


def test_rejects_missing_required_hubert_or_rmvpe_file(tmp_path):
    class IncompleteApi:
        def __init__(self, token=False):
            assert token is False

        def model_info(self, *args, **kwargs):
            return SimpleNamespace(
                gated=False,
                siblings=[
                    SimpleNamespace(rfilename=name, size=meta["size"])
                    for name, meta in list(assets.ASSETS.items())[:-1]
                ],
            )

    with pytest.raises(RuntimeError, match="Required inference asset is missing"):
        assets.download_rvc_assets(tmp_path, downloader=lambda **kwargs: None, api=IncompleteApi())


def test_rejects_asset_with_changed_remote_size(tmp_path):
    class ChangedSizeApi:
        def __init__(self, token=False):
            assert token is False

        def model_info(self, *args, **kwargs):
            siblings = [
                SimpleNamespace(rfilename=name, size=meta["size"])
                for name, meta in assets.ASSETS.items()
            ]
            siblings[0].size += 1
            return SimpleNamespace(gated=False, siblings=siblings)

    with pytest.raises(RuntimeError, match="Hub metadata size changed"):
        assets.download_rvc_assets(tmp_path, downloader=lambda **kwargs: None, api=ChangedSizeApi())


def test_rejects_download_with_invalid_sha256(tmp_path, monkeypatch):
    class FakeApi:
        def __init__(self, token=False):
            pass

        def model_info(self, *args, **kwargs):
            return SimpleNamespace(
                gated=False,
                siblings=[
                    SimpleNamespace(rfilename=name, size=meta["size"])
                    for name, meta in assets.ASSETS.items()
                ],
            )

    filename, metadata = next(
        (name, meta) for name, meta in assets.ASSETS.items() if "sha256" in meta
    )
    bad_file = tmp_path / "bad.pth"
    bad_file.write_bytes(b"bad content")

    with pytest.raises(RuntimeError, match="SHA-256 verification"):
        assets.download_rvc_assets(
            tmp_path / "rvc",
            downloader=lambda **kwargs: bad_file,
            api=FakeApi(),
        )
