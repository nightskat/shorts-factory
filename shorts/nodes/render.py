# render.py — concatenate clips + add audio via ffmpeg
# Falls back to tts audio if bgm_mix was skipped.
# Uses placeholder path when clips are .txt (test environments without ffmpeg).
import os
import json
import hashlib
import sqlite3
import subprocess
from typing import Any
from shorts.nodes import StepResult


def _get_step_output(cursor, job_id: str, step_name: str):
    cursor.execute(
        "SELECT output_path, status FROM step_results WHERE job_id = ? AND step_name = ?",
        (job_id, step_name)
    )
    return cursor.fetchone()


def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    cursor = db_conn.cursor()

    clips_row = _get_step_output(cursor, job_id, "clips")
    if not clips_row or not clips_row[0]:
        return StepResult(status="error", error_msg="Could not find clips step output.")

    clips_path = clips_row[0]
    if not os.path.exists(clips_path):
        return StepResult(status="error", error_msg=f"Clips manifest not found at {clips_path}")

    with open(clips_path, "r", encoding="utf-8") as f:
        clip_manifest = json.load(f)

    # Resolve audio: prefer bgm_mix, fall back to tts
    audio_path = None
    bgm_row = _get_step_output(cursor, job_id, "bgm_mix")
    if bgm_row and bgm_row[1] == "done" and bgm_row[0]:
        audio_path = bgm_row[0]
    else:
        tts_row = _get_step_output(cursor, job_id, "tts")
        if tts_row and tts_row[0]:
            audio_path = tts_row[0]

    if not audio_path:
        return StepResult(status="error", error_msg="No audio source found (tts or bgm_mix).")

    workspace_dir = execution_context.get("workspace_dir", os.getcwd())
    output_dir = os.path.join(workspace_dir, "data", "video")
    os.makedirs(output_dir, exist_ok=True)

    final_path = os.path.join(output_dir, f"{job_id}_render.mp4")
    tmp_path = final_path + ".tmp"

    # If any clip is a placeholder (.txt), skip ffmpeg and write placeholder
    has_placeholder = any(c["clip_path"].endswith(".txt") for c in clip_manifest)

    if has_placeholder:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(f"placeholder render for job {job_id}")
        os.replace(tmp_path, final_path)
        with open(final_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        return StepResult(status="done", output_path=final_path, output_checksum=checksum)

    # Write ffmpeg concat file
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
