import os
import json
import hashlib
import sqlite3
import subprocess
from typing import Any
from shorts.nodes import StepResult

def _get_step_output(cursor: sqlite3.Cursor, job_id: str, step_name: str):
    cursor.execute(
        "SELECT output_path, status FROM step_results WHERE job_id = ? AND step_name = ?",
        (job_id, step_name)
    )
    return cursor.fetchone()

def _resolve_audio_path(cursor: sqlite3.Cursor, job_id: str) -> str | None:
    """Resolve audio: prefer bgm_mix, fall back to tts."""
    bgm_row = _get_step_output(cursor, job_id, "bgm_mix")
    if bgm_row and bgm_row[1] == "done" and bgm_row[0]:
        return bgm_row[0]

    tts_row = _get_step_output(cursor, job_id, "tts")
    if tts_row and tts_row[0]:
        return tts_row[0]

    return None

def _render_placeholder(job_id: str, final_path: str) -> StepResult:
    """Create a placeholder render for testing."""
    tmp_path = final_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(f"placeholder render for job {job_id}")
    os.replace(tmp_path, final_path)

    with open(final_path, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()

    return StepResult(status="done", output_path=final_path, output_checksum=checksum)

def _render_ffmpeg(job_id: str, clip_manifest: list[dict], audio_path: str, output_dir: str, final_path: str) -> StepResult:
    """Render the final video using ffmpeg."""
    tmp_path = final_path + ".tmp"
    concat_path = os.path.join(output_dir, f"{job_id}_concat.txt")

    with open(concat_path, "w", encoding="utf-8") as f:
        for clip in clip_manifest:
            f.write(f"file '{clip['clip_path']}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_path,
        "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-shortest",
        tmp_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            return StepResult(
                status="error",
                error_msg=f"ffmpeg render failed: {result.stderr.decode('utf-8', errors='replace')[:500]}"
            )
    except subprocess.TimeoutExpired:
        return StepResult(status="error", error_msg="ffmpeg render timed out")
    except FileNotFoundError:
        return StepResult(status="error", error_msg="ffmpeg not found")

    os.replace(tmp_path, final_path)

    with open(final_path, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()

    return StepResult(status="done", output_path=final_path, output_checksum=checksum)

def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    cursor = db_conn.cursor()

    clips_row = _get_step_output(cursor, job_id, "clips")
    if not clips_row or not clips_row[0]:
        return StepResult(status="error", error_msg="Could not find clips step output.")

    clips_path = clips_row[0]
    if not os.path.exists(clips_path):
        return StepResult(status="error", error_msg=f"Clips manifest not found at {clips_path}")

    try:
        with open(clips_path, "r", encoding="utf-8") as f:
            clip_manifest = json.load(f)

        if not isinstance(clip_manifest, list):
            return StepResult(status="error", error_msg="Invalid manifest JSON: must be a list")

        for idx, clip in enumerate(clip_manifest):
            if not isinstance(clip, dict):
                return StepResult(status="error", error_msg=f"Invalid manifest JSON: item {idx} is not a dictionary")
            if "clip_path" not in clip:
                return StepResult(status="error", error_msg=f"Invalid manifest JSON: item {idx} missing 'clip_path'")

    except json.JSONDecodeError:
        return StepResult(status="error", error_msg="Invalid manifest JSON")

    audio_path = _resolve_audio_path(cursor, job_id)
    if not audio_path:
        return StepResult(status="error", error_msg="No audio source found (tts or bgm_mix).")

    workspace_dir = execution_context.get("workspace_dir", os.getcwd())
    output_dir = os.path.join(workspace_dir, "data", "video")
    os.makedirs(output_dir, exist_ok=True)

    final_path = os.path.join(output_dir, f"{job_id}_render.mp4")

    # If any clip is a placeholder (.txt), skip ffmpeg and write placeholder
    has_placeholder = any(c["clip_path"].endswith(".txt") for c in clip_manifest)

    if has_placeholder:
        return _render_placeholder(job_id, final_path)

    return _render_ffmpeg(job_id, clip_manifest, audio_path, output_dir, final_path)
