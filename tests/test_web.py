"""
tests/test_web.py — FastAPI web UI integration tests.

Uses TestClient with a temporary SQLite DB (monkeypatched via shorts.config.DB_PATH).
Auth token is monkeypatched to a known value to avoid startup-lifespan dependency.
"""

import hashlib
import sqlite3
from importlib import reload

import pytest
import shorts.web.auth as auth_module


def _make_session_cookie(token: str) -> str:
    """Return the expected session cookie value for a given auth token."""
    return hashlib.sha256(token.encode()).hexdigest()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with isolated tmp DB and known auth token.

    We monkeypatch generate_startup_token so that the lifespan does NOT
    overwrite our pre-set _AUTH_TOKEN; then we set _AUTH_TOKEN directly.
    """
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("shorts.config.DB_PATH", db_path)

    KNOWN_TOKEN = "test-token-123"

    # Patch generate_startup_token so lifespan sets our known token
    def _fixed_generate():
        auth_module._AUTH_TOKEN = KNOWN_TOKEN
        return KNOWN_TOKEN

    monkeypatch.setattr(auth_module, "generate_startup_token", _fixed_generate)
    monkeypatch.setattr(auth_module, "_AUTH_TOKEN", KNOWN_TOKEN)

    # Re-import app module so it picks up the patched DB_PATH
    import shorts.web.app as app_module

    reload(app_module)

    from fastapi.testclient import TestClient
    from shorts.web.app import app

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


def test_security_headers(client):
    """GET /login must include security headers."""
    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert resp.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_unauthenticated_ideas_returns_401(client):
    """GET /ideas without session cookie must return 401."""
    resp = client.get("/ideas", follow_redirects=False)
    assert resp.status_code == 401


def test_login_correct_token(client):
    """POST /login with correct token sets session cookie and redirects."""
    resp = client.post(
        "/login",
        data={"token": "test-token-123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "session" in resp.cookies
    expected = _make_session_cookie("test-token-123")
    assert resp.cookies["session"] == expected


def test_login_wrong_token(client):
    """POST /login with wrong token must NOT set session cookie."""
    resp = client.post(
        "/login",
        data={"token": "wrong-token"},
        follow_redirects=False,
    )
    # Either 401 or a redirect back to login without setting the session cookie
    if resp.status_code == 302:
        assert "session" not in resp.cookies
    else:
        assert resp.status_code in (401, 200)
        assert "session" not in resp.cookies


# ---------------------------------------------------------------------------
# CSRF and job creation tests
# ---------------------------------------------------------------------------


def _authenticated_client(client):
    """Helper: log in and return the session cookie value."""
    resp = client.post(
        "/login",
        data={"token": "test-token-123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    return resp.cookies["session"]


def test_ideas_post_requires_csrf(client):
    """POST /ideas with auth but missing/invalid csrf_token must return 400."""
    _authenticated_client(client)  # sets cookie on the client jar

    resp = client.post(
        "/ideas",
        data={"title": "test title", "csrf_token": "invalid-token"},
        follow_redirects=False,
    )
    assert resp.status_code == 400


def test_ideas_post_creates_job(client, tmp_path, monkeypatch):
    """POST /ideas with valid auth + CSRF creates a job row in the DB."""
    # The fixture already patched DB_PATH; we just need the path to read from
    # Re-read where the DB is
    import shorts.config as cfg_mod

    db = str(cfg_mod.DB_PATH)

    _authenticated_client(client)

    # Get a valid CSRF token from the GET /ideas page
    resp = client.get("/ideas")
    assert resp.status_code == 200

    # Extract csrf_token from the form (hidden input in HTML)
    body = resp.text
    # Parse it from the HTML — find value="{{ csrf_token }}" rendered value
    import re

    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', body)
    assert match, "CSRF token not found in /ideas HTML"
    csrf = match.group(1)

    resp2 = client.post(
        "/ideas",
        data={"title": "My video idea", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert resp2.status_code == 302

    # Verify DB has the job
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT title, status FROM jobs").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == "My video idea"
    assert rows[0][1] == "draft"

# ---------------------------------------------------------------------------
# Voice tests
# ---------------------------------------------------------------------------

def test_voice_get_unauthenticated(client):
    """GET /voice without session cookie must return 401."""
    resp = client.get("/voice", follow_redirects=False)
    assert resp.status_code == 401

def test_voice_get_authenticated(client, tmp_path):
    """GET /voice with valid auth returns 200 and renders the voice page."""
    _authenticated_client(client)
    resp = client.get("/voice")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "csrf_token" in resp.text

def test_voice_post_requires_csrf(client):
    """POST /voice with missing/invalid csrf_token must return 400."""
    _authenticated_client(client)
    resp = client.post(
        "/voice",
        data={"script_body": "test script", "csrf_token": "invalid-token"},
        follow_redirects=False,
    )
    assert resp.status_code == 400

def test_voice_post_creates_script(client, tmp_path, monkeypatch):
    """POST /voice with valid auth + CSRF creates a script in the DB."""
    import shorts.config as cfg_mod
    db = str(cfg_mod.DB_PATH)

    _authenticated_client(client)

    # Get a valid CSRF token
    resp = client.get("/voice")
    assert resp.status_code == 200

    import re
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    assert match, "CSRF token not found in /voice HTML"
    csrf = match.group(1)

    # Post the script
    resp2 = client.post(
        "/voice",
        data={"script_body": "My awesome voice script", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert resp2.status_code == 302
    assert resp2.headers["location"] == "/voice"

    # Verify DB has the script
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT script_body FROM approved_scripts").fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0][0] == "My awesome voice script"
