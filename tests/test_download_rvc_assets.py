from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import download_rvc_assets as assets


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


def test_downloads_all_pinned_assets_and_verifies_large_file_hashes(tmp_path):
    downloaded = []

    def fake_download(repo_id, filename, revision, token):
        assert repo_id == assets.REPO_ID
        assert revision == assets.REVISION
        assert token is False
        path = tmp_path / "hub-cache" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * assets.ASSETS[filename]["size"])
        if "sha256" in assets.ASSETS[filename]:
            import hashlib
            path.write_bytes(b"")
            # Use a deterministic, correctly sized file only for the small unit test.
            payload = b"unit-test-asset"
            path.write_bytes(payload)
            meta = dict(assets.ASSETS[filename])
            meta["size"] = len(payload)
            meta["sha256"] = hashlib.sha256(payload).hexdigest()
            test_metadata[filename] = meta
        downloaded.append(filename)
        return path

    test_metadata = {name: dict(meta) for name, meta in assets.ASSETS.items()}
    for name, meta in test_metadata.items():
        if "sha256" in meta:
            payload = b"unit-test-asset"
            meta["size"] = len(payload)
            import hashlib
            meta["sha256"] = hashlib.sha256(payload).hexdigest()

    original_assets = assets.ASSETS
    assets.ASSETS = test_metadata
    try:
        installed = assets.download_rvc_assets(
            tmp_path / "rvc",
            downloader=fake_download,
            api=FakeApi(),
        )
    finally:
        assets.ASSETS = original_assets

    assert len(installed) == 4
    assert set(downloaded) == set(test_metadata)
    for name, meta in test_metadata.items():
        destination = tmp_path / "rvc" / meta["destination"]
        assert destination.is_file()
        assert destination.stat().st_size == meta["size"]


def test_rejects_gated_asset_repository(tmp_path):
    class GatedApi(FakeApi):
        def model_info(self, *args, **kwargs):
            return SimpleNamespace(gated=True, siblings=[])

    with pytest.raises(RuntimeError, match="gated"):
        assets.download_rvc_assets(tmp_path, downloader=lambda **kwargs: None, api=GatedApi())


def test_rejects_missing_required_hubert_or_rmvpe_file(tmp_path):
    class IncompleteApi(FakeApi):
        def model_info(self, *args, **kwargs):
            info = super().model_info(*args, **kwargs)
            info.siblings = info.siblings[:-1]
            return info

    with pytest.raises(RuntimeError, match="Required inference asset is missing"):
        assets.download_rvc_assets(tmp_path, downloader=lambda **kwargs: None, api=IncompleteApi())


def test_rejects_asset_with_changed_size_or_hash(tmp_path):
    class ChangedSizeApi(FakeApi):
        def model_info(self, *args, **kwargs):
            info = super().model_info(*args, **kwargs)
            info.siblings[0].size += 1
            return info

    with pytest.raises(RuntimeError, match="Hub metadata size changed"):
        assets.download_rvc_assets(tmp_path, downloader=lambda **kwargs: None, api=ChangedSizeApi())
