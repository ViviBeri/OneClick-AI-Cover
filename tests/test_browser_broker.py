from oneclick_cover.browser_broker import (
    BrowserSessionStore,
    validate_browser_request_boundary,
)


def test_session_requires_cookie_and_separate_csrf_for_mutations():
    store = BrowserSessionStore()
    session = store.create()

    assert store.validate(session.session_id)
    assert not store.validate(None)
    assert not store.validate(session.session_id, require_csrf=True)
    assert not store.validate(
        session.session_id, csrf_token="wrong", require_csrf=True
    )
    assert store.validate(
        session.session_id,
        csrf_token=session.csrf_token,
        require_csrf=True,
    )


def test_session_expires_and_can_be_revoked():
    now = [100.0]
    store = BrowserSessionStore(ttl_seconds=5, clock=lambda: now[0])
    session = store.create()
    assert store.validate(session.session_id)

    now[0] = 105.0
    assert not store.validate(session.session_id)

    active = store.create()
    store.revoke_all()
    assert not store.validate(active.session_id)


def test_session_store_rejects_non_positive_lifetime():
    import pytest

    with pytest.raises(ValueError, match="positive"):
        BrowserSessionStore(ttl_seconds=0)


def test_browser_boundary_requires_exact_host_and_origin_for_mutations():
    expected = {
        "host": "127.0.0.1:7860",
        "expected_host": "127.0.0.1:7860",
        "expected_origin": "http://127.0.0.1:7860",
    }
    assert validate_browser_request_boundary(
        **expected, origin="http://127.0.0.1:7860", state_changing=True
    )
    assert not validate_browser_request_boundary(
        **expected, origin="https://attacker.example", state_changing=True
    )
    assert not validate_browser_request_boundary(
        **expected, origin=None, state_changing=True
    )
    assert not validate_browser_request_boundary(
        **{**expected, "host": "attacker.example"},
        origin="http://127.0.0.1:7860",
        state_changing=False,
    )


def test_safe_same_origin_request_may_omit_origin():
    assert validate_browser_request_boundary(
        host="127.0.0.1:7860",
        origin=None,
        expected_host="127.0.0.1:7860",
        expected_origin="http://127.0.0.1:7860",
        state_changing=False,
    )
