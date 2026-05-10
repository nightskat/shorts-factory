# upload_yt.py — upload rendered video to YouTube with idempotency guard
# Two-phase protocol: INSERT record before upload, UPDATE after success.
import hashlib
import sqlite3
from typing import Any
from shorts.nodes import StepResult


def _idempotency_key(job_id: str) -> str:
    return hashlib.sha256(job_id.encode("utf-8")).hexdigest()[:16]


def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    cursor = db_conn.cursor()

    cursor.execute(
        "SELECT output_path FROM step_results WHERE job_id = ? AND step_name = ? AND status = 'done'",
        (job_id, "render")
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        return StepResult(status="error", error_msg="Could not find successful render step output.")

    video_path = row[0]

    idem_key = _idempotency_key(job_id)

    # Phase 1: check for existing completed upload (idempotency)
    cursor.execute(
        "SELECT status, video_id FROM youtube_uploads WHERE job_id = ?",
        (job_id,)
    )
    existing = cursor.fetchone()
    if existing and existing[0] == "completed":
        video_id = existing[1]
        return StepResult(
            status="done",
            output_path=f"https://youtube.com/watch?v={video_id}"
        )

    # Phase 1 continued: insert started record
    cursor.execute(
        "INSERT OR IGNORE INTO youtube_uploads (job_id, status, idempotency_key) VALUES (?, 'started', ?)",
        (job_id, idem_key)
    )
    db_conn.commit()

    # Phase 2: upload
    youtube_uploader = services.get("youtube_uploader")
    if youtube_uploader:
        video_id = youtube_uploader.upload(
            video_path,
            title=job_id,
            description=f"[sf-id: {job_id}]"
        )
    else:
        video_id = f"SIMULATED_{job_id[:8]}"

    # Phase 3: mark completed
    cursor.execute(
        "UPDATE youtube_uploads SET status='completed', video_id=? WHERE job_id=?",
        (video_id, job_id)
    )
    db_conn.commit()

    return StepResult(
        status="done",
        output_path=f"https://youtube.com/watch?v={video_id}"
    )
