"""
shorts/web/app.py — FastAPI web application for Shorts Factory UI.

Provides a single-owner, token-authenticated web interface for managing
pipeline jobs, viewing results, and seeding voice examples. All UI state
is stored in the SQLite database at DB_PATH. Uses HttpOnly session cookie
and signed CSRF tokens (itsdangerous) for security.
"""

import asyncio
import json
import sqlite3
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from shorts.config import DB_PATH
from shorts.db import init_db
from shorts.web.auth import (
    generate_startup_token,
    get_csrf_token,
    require_auth,
    verify_csrf_token,
)

TEMPLATES_DIR: Path = Path(__file__).parent / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and print startup auth token before serving requests."""
    init_db(str(DB_PATH))
    generate_startup_token()
    import shorts.web.auth as _auth_mod

    print(f"\n[Shorts Factory] Auth token: {_auth_mod._AUTH_TOKEN}")
    print("[Shorts Factory] Login at: http://127.0.0.1:8765/login\n")
    yield


app = FastAPI(title="Shorts Factory", lifespan=lifespan)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login form."""
    csrf = get_csrf_token("login")
    return templates.TemplateResponse(request, "login.html", {"csrf_token": csrf})


@app.post("/login")
async def login_post(request: Request, token: str = Form(...)):
    """Validate token, set session cookie, redirect to /ideas.

    Caveat: reads _AUTH_TOKEN at call time (after lifespan sets it).
    """
    import shorts.web.auth as _auth_mod
    import hashlib
    import secrets

    # Security: Use secrets.compare_digest to prevent timing attacks on login token validation
    if not secrets.compare_digest(token, _auth_mod._AUTH_TOKEN):
        csrf = get_csrf_token("login")
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Token không hợp lệ", "csrf_token": csrf},
            status_code=401,
        )

    session_value = hashlib.sha256(_auth_mod._AUTH_TOKEN.encode()).hexdigest()
    response = RedirectResponse(url="/ideas", status_code=302)
    response.set_cookie(
        key="session",
        value=session_value,
        httponly=True,
        samesite="lax",
    )
    return response


# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    """Redirect root to /ideas."""
    return RedirectResponse(url="/ideas", status_code=302)


# ---------------------------------------------------------------------------
# Ideas
# ---------------------------------------------------------------------------


@app.get("/ideas", response_class=HTMLResponse)
def ideas_get(request: Request, session: str = Depends(require_auth)):
    """List all jobs.

    ⚡ Bolt: Changed to `def` so FastAPI automatically offloads blocking SQLite
    operations to its threadpool, preventing asyncio event loop blocking.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, title, status, created_at FROM jobs ORDER BY created_at DESC"
        ).fetchall()
        jobs = [dict(r) for r in rows]
    finally:
        conn.close()

    csrf = get_csrf_token(session)
    return templates.TemplateResponse(
        request, "ideas.html", {"jobs": jobs, "csrf_token": csrf, "active": "ideas"}
    )


@app.post("/ideas")
def ideas_post(
    request: Request,
    session: str = Depends(require_auth),
    title: str = Form(...),
    csrf_token: str = Form(...),
):
    """Create a new job with status=draft.

    Raises HTTP 400 if CSRF token is invalid.

    ⚡ Bolt: Changed to `def` so FastAPI automatically offloads blocking SQLite
    operations to its threadpool, preventing asyncio event loop blocking.
    """
    if not verify_csrf_token(csrf_token, session):
        raise HTTPException(status_code=400, detail="CSRF token không hợp lệ")

    job_id = str(uuid.uuid4())
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            "INSERT INTO jobs (id, title, status, execution_context) VALUES (?, ?, 'draft', ?)",
            (job_id, title, "{}"),
        )
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(url="/ideas", status_code=302)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


@app.get("/pipeline", response_class=HTMLResponse)
def pipeline_get(request: Request, session: str = Depends(require_auth)):
    """Show pipeline status for all jobs.

    ⚡ Bolt: Changed to `def` so FastAPI automatically offloads blocking SQLite
    operations to its threadpool, preventing asyncio event loop blocking.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        jobs = [
            dict(r)
            for r in conn.execute(
                "SELECT id, title, status, created_at FROM jobs ORDER BY created_at DESC"
            ).fetchall()
        ]
        step_results = [
            dict(r)
            for r in conn.execute(
                "SELECT job_id, step_name, status, output_path FROM step_results"
            ).fetchall()
        ]
    finally:
        conn.close()

    csrf = get_csrf_token(session)
    return templates.TemplateResponse(
        request,
        "pipeline.html",
        {
            "jobs": jobs,
            "step_results": step_results,
            "csrf_token": csrf,
            "active": "pipeline",
        },
    )


@app.post("/pipeline/run")
async def pipeline_run(
    request: Request,
    session: str = Depends(require_auth),
):
    """Trigger a single pipeline step for a job.

    Expects JSON body: {job_id: str, step_name: str, csrf_token: str}.
    Returns JSON with status, step, and output path.
    """
    body = await request.json()
    csrf_token = body.get("csrf_token", "")
    if not verify_csrf_token(csrf_token, session):
        raise HTTPException(status_code=400, detail="CSRF token không hợp lệ")

    job_id = body.get("job_id")
    step_name = body.get("step_name")
    if not job_id or not step_name:
        raise HTTPException(status_code=400, detail="Thiếu job_id hoặc step_name")

    # ⚡ Bolt: Offloading synchronous blocking operations to threadpool
    # because this endpoint must remain `async def` to use `await request.json()`
    def _run_step_blocking():
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            return _run_step(job_id, step_name, conn)
        finally:
            conn.close()

    result = await asyncio.to_thread(_run_step_blocking)

    return JSONResponse(result)


def _run_step(job_id: str, step_name: str, db_conn: sqlite3.Connection) -> dict:
    """Import and execute a node module for one pipeline step.

    Args:
        job_id: The job to run the step for.
        step_name: Module name under shorts.nodes (e.g. "idea_gen").
        db_conn: Open SQLite connection (caller owns lifecycle).

    Returns:
        Dict with keys: status, step, output.
    """
    import importlib

    ALLOWED_STEPS = {
        "idea_gen",
        "tts",
        "bgm_mix",
        "scenes",
        "clips",
        "render",
        "thumbnail",
        "qa_check",
        "upload_yt",
    }
    if step_name not in ALLOWED_STEPS:
        return {"status": "error", "msg": "Invalid step_name"}

    node = importlib.import_module(f"shorts.nodes.{step_name}")
    row = db_conn.execute(
        "SELECT execution_context FROM jobs WHERE id=?", (job_id,)
    ).fetchone()
    if not row:
        return {"status": "error", "msg": "Không tìm thấy job"}

    ctx = json.loads(row[0] or "{}")
    result = node.run(job_id, ctx, db_conn, {})
    db_conn.execute(
        "INSERT OR REPLACE INTO step_results "
        "(job_id, step_name, status, output_path, output_checksum) VALUES (?,?,?,?,?)",
        (job_id, step_name, result.status, result.output_path, result.output_checksum),
    )
    db_conn.commit()
    return {"status": result.status, "step": step_name, "output": result.output_path}


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------


@app.get("/voice", response_class=HTMLResponse)
def voice_get(request: Request, session: str = Depends(require_auth)):
    """Show approved voice scripts.

    ⚡ Bolt: Changed to `def` so FastAPI automatically offloads blocking SQLite
    operations to its threadpool, preventing asyncio event loop blocking.
    This also removes the need for manual `asyncio.to_thread` boilerplate.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        approved_scripts = [
            dict(r)
            for r in conn.execute(
                "SELECT id, script_body, approved_at FROM approved_scripts ORDER BY approved_at DESC"
            ).fetchall()
        ]
    finally:
        conn.close()

    csrf = get_csrf_token(session)
    return templates.TemplateResponse(
        request,
        "voice.html",
        {"approved_scripts": approved_scripts, "csrf_token": csrf, "active": "voice"},
    )


@app.post("/voice")
def voice_post(
    request: Request,
    session: str = Depends(require_auth),
    script_body: str = Form(...),
    csrf_token: str = Form(...),
):
    """Add a new approved voice script.

    Raises HTTP 400 if CSRF token is invalid.

    ⚡ Bolt: Changed to `def` so FastAPI automatically offloads blocking SQLite
    operations to its threadpool, preventing asyncio event loop blocking.
    """
    if not verify_csrf_token(csrf_token, session):
        raise HTTPException(status_code=400, detail="CSRF token không hợp lệ")

    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            "INSERT INTO approved_scripts (script_body) VALUES (?)", (script_body,)
        )
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(url="/voice", status_code=302)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@app.get("/config", response_class=HTMLResponse)
async def config_get(request: Request, session: str = Depends(require_auth)):
    """Show masked environment variable values relevant to Shorts Factory."""
    import os

    env_vars = {}
    for key, val in os.environ.items():
        if any(
            key.startswith(prefix)
            for prefix in (
                "SHORTS_",
                "LLM_",
                "TTS_",
                "OPENAI_",
                "ANTHROPIC_",
                "GOOGLE_",
            )
        ):
            masked = val[:4] + "****" if len(val) > 4 else "****"
            env_vars[key] = masked

    csrf = get_csrf_token(session)
    return templates.TemplateResponse(
        request,
        "config.html",
        {"env_vars": env_vars, "csrf_token": csrf, "active": "config"},
    )
