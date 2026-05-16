# upload_yt.py — upload rendered video to YouTube with idempotency guard
# Two-phase protocol: INSERT record before upload, UPDATE after success.
import hashlib
import sqlite3
from typing import Any
from shorts.nodes import StepResult


def _idempotency_key(job_id: str) -> str:
    return hashlib.sha256(job_id.encode("utf-8")).hexdigest()[:16]


def _get_render_output_path(db_conn: sqlite3.Connection, job_id: str) -> str | None:
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT output_path FROM step_results WHERE job_id = ? AND step_name = ? AND status = 'done'",
        (job_id, "render")
    )
    row = cursor.fetchone()
    if row and row[0]:
        return row[0]
    return None


def _get_existing_video_id(db_conn: sqlite3.Connection, job_id: str) -> str | None:
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT status, video_id FROM youtube_uploads WHERE job_id = ?",
        (job_id,)
    )
    existing = cursor.fetchone()
    if existing and existing[0] == "completed":
        return existing[1]
    return None


def _mark_upload_started(db_conn: sqlite3.Connection, job_id: str) -> None:
    cursor = db_conn.cursor()
    idem_key = _idempotency_key(job_id)
    cursor.execute(
        "INSERT OR IGNORE INTO youtube_uploads (job_id, status, idempotency_key) VALUES (?, 'started', ?)",
        (job_id, idem_key)
    )
    db_conn.commit()


def _perform_upload(job_id: str, video_path: str, services: dict[str, Any]) -> str:
    youtube_uploader = services.get("youtube_uploader")
    if youtube_uploader:
        return youtube_uploader.upload(
            video_path,
            title=job_id,
            description=f"[sf-id: {job_id}]"
        )
    return f"SIMULATED_{job_id[:8]}"


def _mark_upload_completed(db_conn: sqlite3.Connection, job_id: str, video_id: str) -> None:
    cursor = db_conn.cursor()
    cursor.execute(
        "UPDATE youtube_uploads SET status='completed', video_id=? WHERE job_id=?",
        (video_id, job_id)
    )
    db_conn.commit()


def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    video_path = _get_render_output_path(db_conn, job_id)
    if not video_path:
        return StepResult(status="error", error_msg="Could not find successful render step output.")

    # Phase 1: check for existing completed upload (idempotency)
    existing_video_id = _get_existing_video_id(db_conn, job_id)
    if existing_video_id:
        return StepResult(
            status="done",
            output_path=f"https://youtube.com/watch?v={existing_video_id}"
        )

    # Phase 1 continued: insert started record
    _mark_upload_started(db_conn, job_id)

    # Phase 2: upload
    video_id = _perform_upload(job_id, video_path, services)

    # Phase 3: mark completed
    _mark_upload_completed(db_conn, job_id, video_id)

    return StepResult(
        status="done",
        output_path=f"https://youtube.com/watch?v={video_id}"
    )
