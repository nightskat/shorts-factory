# bgm_mix.py — mix TTS audio with background music via ffmpeg
# Reads tts output_path from step_results, mixes BGM at 0.15 volume.
import os
import hashlib
import sqlite3
import subprocess
from typing import Any
from shorts.nodes import StepResult


def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    env = execution_context.get("env", {})

    bgm_path = env.get("BGM_PATH")
    if not bgm_path:
        return StepResult(status="skipped")

    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT output_path FROM step_results WHERE job_id = ? AND step_name = ? AND status = 'done'",
        (job_id, "tts")
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        return StepResult(
            status="error",
            error_msg="Could not find successful tts step output for this job."
        )

    tts_path = row[0]

    if not os.path.exists(tts_path):
        return StepResult(
            status="error",
            error_msg=f"TTS file not found at {tts_path}"
        )

    workspace_dir = execution_context.get("workspace_dir", os.getcwd())
    output_dir = os.path.join(workspace_dir, "data", "audio")
    os.makedirs(output_dir, exist_ok=True)

    final_path = os.path.join(output_dir, f"{job_id}_mixed.mp3")
    tmp_path = final_path + ".tmp"

    cmd = [
        "ffmpeg", "-y",
        "-i", tts_path,
        "-stream_loop", "-1",
        "-i", bgm_path,
        "-filter_complex", "[1:a]volume=0.15[bgm];[0:a][bgm]amix=inputs=2:duration=first[out]",
        "-map", "[out]",
        tmp_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            return StepResult(
                status="error",
                error_msg=f"ffmpeg bgm_mix failed: {result.stderr.decode('utf-8', errors='replace')[:500]}"
            )
    except subprocess.TimeoutExpired:
        return StepResult(status="error", error_msg="ffmpeg bgm_mix timed out")
    except FileNotFoundError:
        return StepResult(status="error", error_msg="ffmpeg not found")

    os.replace(tmp_path, final_path)

    with open(final_path, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()

    return StepResult(
        status="done",
        output_path=final_path,
        output_checksum=checksum
    )
