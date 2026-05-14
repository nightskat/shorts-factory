# thumbnail.py — extract thumbnail frame from rendered video
# If video is a placeholder (.txt), writes a placeholder file instead.
import os
import hashlib
import sqlite3
import subprocess
from typing import Any
from shorts.nodes import StepResult


def _get_rendered_video_path(job_id: str, db_conn: sqlite3.Connection) -> str | None:
    """Retrieve the output path of the successful render step for a given job."""
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT output_path FROM step_results WHERE job_id = ? AND step_name = ? AND status = 'done'",
        (job_id, "render")
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        return None
    return row[0]


def _calculate_checksum(file_path: str) -> str:
    """Calculate the SHA256 checksum of a file."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _generate_placeholder_thumbnail(job_id: str, tmp_path: str, final_path: str) -> StepResult:
    """Generate a placeholder text thumbnail for testing/placeholder videos."""
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(f"placeholder thumbnail for job {job_id}")
    os.replace(tmp_path, final_path)
    checksum = _calculate_checksum(final_path)
    return StepResult(status="done", output_path=final_path, output_checksum=checksum)


def _extract_frame_with_ffmpeg(video_path: str, tmp_path: str, final_path: str) -> StepResult:
    """Extract a single frame from the video using ffmpeg."""
    if not os.path.exists(video_path):
        return StepResult(status="error", error_msg=f"Video file not found at {video_path}")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", "00:00:01",
        "-vframes", "1",
        tmp_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            return StepResult(
                status="error",
                error_msg=f"ffmpeg thumbnail failed: {result.stderr.decode('utf-8', errors='replace')[:500]}"
            )
    except subprocess.TimeoutExpired:
        return StepResult(status="error", error_msg="ffmpeg thumbnail timed out")
    except FileNotFoundError:
        return StepResult(status="error", error_msg="ffmpeg not found")

    os.replace(tmp_path, final_path)
    checksum = _calculate_checksum(final_path)
    return StepResult(status="done", output_path=final_path, output_checksum=checksum)


def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    video_path = _get_rendered_video_path(job_id, db_conn)
    if not video_path:
        return StepResult(status="error", error_msg="Could not find successful render step output.")

    workspace_dir = execution_context.get("workspace_dir", os.getcwd())
    output_dir = os.path.join(workspace_dir, "data", "thumbnails")
    os.makedirs(output_dir, exist_ok=True)

    final_path = os.path.join(output_dir, f"{job_id}_thumb.jpg")
    tmp_path = final_path + ".tmp"

    if video_path.endswith(".txt"):
        return _generate_placeholder_thumbnail(job_id, tmp_path, final_path)

    return _extract_frame_with_ffmpeg(video_path, tmp_path, final_path)
