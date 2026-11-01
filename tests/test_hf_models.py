from pathlib import Path

import pytest

from oneclick_cover import hf_models


def test_download_requires_explicit_confirmation(tmp_path):
    with pytest.raises(ValueError, match="Confirm"):
        hf_models.download_public_pth_model("owner/model", "voice.pth", tmp_path, False)


@pytest.mark.parametrize(
    "repo_id,filename",
    [
        ("not-a-repo-id", "voice.pth"),
        ("owner/model", "../voice.pth"),
        ("owner/model", "weights.bin"),
    ],
)
def test_download_rejects_invalid_identifiers(tmp_path, repo_id, filename):
    with pytest.raises(ValueError):
        hf_models.download_public_pth_model(repo_id, filename, tmp_path, True)


def test_search_rejects_long_query():
    with pytest.raises(ValueError, match="80 characters"):
        hf_models.search_public_rvc_models("x" * 81)


def test_search_rejects_invalid_limit():
    with pytest.raises(ValueError, match="between 1 and 20"):
        hf_models.search_public_rvc_models("", 21)


def test_download_requires_exact_file_in_public_repo(tmp_path, monkeypatch):
    class Sibling:
        rfilename = "voice.pth"
        size = 2048

    class Info:
        gated = False
        siblings = [Sibling()]

    class FakeApi:
        def __init__(self, token=False):
            assert token is False

        def model_info(self, repo_id, files_metadata=True, token=False):
            assert token is False
            return Info()

    monkeypatch.setattr(hf_models, "HfApi", FakeApi)
    with pytest.raises(ValueError, match="exact .pth filename"):
        hf_models.download_public_pth_model(
            "owner/model", "missing.pth", tmp_path, True
        )


def test_download_rejects_oversized_model_before_transfer(tmp_path, monkeypatch):
    class Sibling:
        rfilename = "voice.pth"
        size = hf_models.MAX_MODEL_BYTES + 1

    class Info:
        gated = False
        siblings = [Sibling()]

    class FakeApi:
        def __init__(self, token=False):
            assert token is False

        def model_info(self, repo_id, files_metadata=True, token=False):
            assert token is False
            return Info()

    monkeypatch.setattr(hf_models, "HfApi", FakeApi)
    with pytest.raises(ValueError, match="2 GiB"):
        hf_models.download_public_pth_model(
            "owner/model", "voice.pth", tmp_path, True
        )
