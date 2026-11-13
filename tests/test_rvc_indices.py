from pathlib import Path

import pytest

from oneclick_cover.rvc_indices import import_rvc_index, list_rvc_indices


def test_imports_and_lists_nonempty_index_files(tmp_path):
    source = tmp_path / "voice.index"
    source.write_bytes(b"index data")

    imported = import_rvc_index(source, tmp_path / "indices")

    assert imported == (tmp_path / "indices" / "voice.index").resolve()
    assert list_rvc_indices(tmp_path / "indices") == ["voice.index"]


def test_rejects_missing_wrong_type_and_empty_index(tmp_path):
    with pytest.raises(ValueError, match="existing RVC"):
        import_rvc_index(tmp_path / "missing.index", tmp_path / "indices")

    wrong_type = tmp_path / "voice.bin"
    wrong_type.write_bytes(b"data")
    with pytest.raises(ValueError, match=r"\.index extension"):
        import_rvc_index(wrong_type, tmp_path / "indices")

    empty = tmp_path / "empty.index"
    empty.touch()
    with pytest.raises(ValueError, match="empty"):
        import_rvc_index(empty, tmp_path / "indices")


def test_rejects_duplicate_index_without_overwriting(tmp_path):
    source = tmp_path / "voice.index"
    source.write_bytes(b"new")
    destination_dir = tmp_path / "indices"
    destination_dir.mkdir()
    (destination_dir / "voice.index").write_bytes(b"existing")

    with pytest.raises(ValueError, match="already exists"):
        import_rvc_index(source, destination_dir)

    assert (destination_dir / "voice.index").read_bytes() == b"existing"


def test_listing_ignores_empty_and_non_index_files(tmp_path):
    (tmp_path / "valid.index").write_bytes(b"valid")
    (tmp_path / "empty.index").touch()
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    assert list_rvc_indices(tmp_path) == ["valid.index"]
