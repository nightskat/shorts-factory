"""
shorts/web/auth.py — Authentication and CSRF utilities for the web UI.

Provides static-token auth (printed at startup), HttpOnly session cookie,
and CSRF token signing via itsdangerous. No user database — single-owner app.
"""

import os
import secrets
import hashlib
from fastapi import Request, HTTPException
from itsdangerous import URLSafeTimedSerializer, BadSignature

SECRET_KEY: str = os.environ.get("SECRET_KEY", secrets.token_hex(32))
_signer: URLSafeTimedSerializer = URLSafeTimedSerializer(SECRET_KEY)

# Set once at startup via generate_startup_token(); never mutated afterwards.
_AUTH_TOKEN: str = ""


def generate_startup_token() -> str:
    """Generate and store the single auth token; return it for printing at startup.

    Called once from the FastAPI lifespan context. The returned string should be
    printed to stdout so the operator can paste it into the /login form.
    """
    global _AUTH_TOKEN
    _AUTH_TOKEN = secrets.token_urlsafe(24)
    return _AUTH_TOKEN


def _session_value() -> str:
    """Return the expected session cookie value (sha256 of the auth token).

    Caveat: value depends on _AUTH_TOKEN being set; call only after
    generate_startup_token().
    """
    return hashlib.sha256(_AUTH_TOKEN.encode()).hexdigest()


def get_csrf_token(session_token: str) -> str:
    """Create a signed, time-limited CSRF token tied to the session.

    Args:
        session_token: The raw session cookie value (sha256 hex digest).

    Returns:
        A signed token string to embed as a hidden form field.
    """
    return _signer.dumps({"csrf": 1, "s": session_token[:8]})


def verify_csrf_token(token: str) -> bool:
    """Validate a CSRF token produced by get_csrf_token().

    Args:
        token: The token from the hidden form field.

    Returns:
        True when the signature is valid and the token is younger than 3600 s.
    """
    try:
        _signer.loads(token, max_age=3600)
        return True
    except BadSignature:
        return False


def require_auth(request: Request) -> str:
    """FastAPI dependency — raises HTTP 401 if the session cookie is missing or invalid.

    Usage::

        @app.get("/protected")
        async def handler(session: str = Depends(require_auth)):
            ...

    Returns:
        The raw session cookie value on success.

    Raises:
        HTTPException(401): When the cookie is absent or does not match the
        expected sha256 digest of the startup auth token.
    """
    session = request.cookies.get("session")
    if not session or session != _session_value():
        raise HTTPException(status_code=401, detail="Xác thực thất bại")
    return session
