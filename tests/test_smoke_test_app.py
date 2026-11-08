import pytest

from scripts.smoke_test_app import validate_page


def test_gradio_smoke_check_accepts_page_with_system_check_tab():
    validate_page(200, "<title>OneClick-AI-Cover</title><div>System Check</div>")


def test_gradio_smoke_check_rejects_page_when_system_check_tab_is_missing():
    with pytest.raises(RuntimeError, match="System Check tab was not present"):
        validate_page(200, "<title>OneClick-AI-Cover</title><div>Settings</div>")


def test_gradio_smoke_check_rejects_non_success_status():
    with pytest.raises(RuntimeError, match="Unexpected HTTP status: 503"):
        validate_page(503, "<title>OneClick-AI-Cover</title><div>System Check</div>")
