import pytest

from oneclick_cover.separation_backends import DemucsBackend, get_separation_backend


def test_demucs_is_the_default_available_backend():
    backend = get_separation_backend("demucs")
    assert isinstance(backend, DemucsBackend)
    assert backend.name == "demucs"


def test_backend_lookup_is_case_insensitive_and_trims_whitespace():
    assert get_separation_backend(" Demucs ").name == "demucs"


@pytest.mark.parametrize("name", ["", "mdx", "roformer", "../demucs"])
def test_unavailable_backend_fails_without_loading_optional_dependencies(name):
    with pytest.raises(ValueError, match="Unsupported separation backend|Choose"):
        get_separation_backend(name)


def test_demucs_backend_delegates_to_existing_separator(monkeypatch, tmp_path):
    import oneclick_cover.separation_backends as backends

    expected = (tmp_path / "vocals.wav", tmp_path / "instrumental.wav")
    calls = []

    def fake_separate(input_wav, job_dir, **kwargs):
        calls.append((input_wav, job_dir, kwargs))
        return expected

    monkeypatch.setattr(backends, "separate_vocals", fake_separate)
    result = backends.DemucsBackend().separate(
        tmp_path / "input.wav", tmp_path, device="cpu", segment=4, timeout=60
    )

    assert result == expected
    assert calls[0][2]["device"] == "cpu"
    assert calls[0][2]["segment"] == 4
    assert calls[0][2]["timeout"] == 60
