# clips.py — fetch or placeholder stock clips for each scene
# Reads scenes JSON, optionally downloads via pexels service, writes clips manifest.
import os
import json
import hashlib
import sqlite3
import urllib.request
import concurrent.futures
import tempfile
from typing import Any, Optional, Tuple
from shorts.nodes import StepResult


def _process_scene(i: int, scene: dict, job_id: str, clips_dir: str, pexels: Any) -> dict:
    description = scene.get("description", "")
    duration = scene.get("duration_seconds", 5)

    if pexels:
        results = pexels.search(description, per_page=1)
        # The PexelsClipsProvider returns a list of dicts, each with a 'url' key
        video_url = results[0]["url"]
        clip_path = os.path.join(clips_dir, f"{job_id}_clip_{i}.mp4")
        urllib.request.urlretrieve(video_url, clip_path)
    else:
        clip_path = os.path.join(clips_dir, f"{job_id}_clip_{i}.txt")
        with open(clip_path, "w", encoding="utf-8") as f:
            f.write(description)

    return {"clip_path": clip_path, "duration_seconds": duration}


def _get_scenes_path(db_conn: sqlite3.Connection, job_id: str) -> Optional[str]:
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT output_path FROM step_results WHERE job_id = ? AND step_name = ? AND status = 'done'",
        (job_id, "scenes")
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        return None
    return row[0]

def _save_manifest(clip_manifest: list[dict], job_id: str, clips_dir: str) -> Tuple[str, str]:
    final_path = os.path.join(clips_dir, f"{job_id}_clips.json")

    encoded = json.dumps(clip_manifest, ensure_ascii=False, indent=2).encode("utf-8")

    fd, unique_tmp_path = tempfile.mkstemp(dir=clips_dir, prefix=f"{job_id}_clips_", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        os.replace(unique_tmp_path, final_path)
    except Exception:
        if os.path.exists(unique_tmp_path):
            os.unlink(unique_tmp_path)
        raise

    checksum = hashlib.sha256(encoded).hexdigest()
    return final_path, checksum

def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    scenes_path = _get_scenes_path(db_conn, job_id)
    if not scenes_path:
        return StepResult(
            status="error",
            error_msg="Could not find successful scenes step output for this job."
        )

    if not os.path.exists(scenes_path):
        return StepResult(
            status="error",
            error_msg=f"Scenes file not found at {scenes_path}"
        )

    with open(scenes_path, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    workspace_dir = execution_context.get("workspace_dir", os.getcwd())
    clips_dir = os.path.join(workspace_dir, "data", "clips")
    os.makedirs(clips_dir, exist_ok=True)

    pexels = services.get("pexels")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(_process_scene, i, scene, job_id, clips_dir, pexels)
            for i, scene in enumerate(scenes)
        ]
        clip_manifest = [f.result() for f in futures]

    final_path, checksum = _save_manifest(clip_manifest, job_id, clips_dir)

    return StepResult(
        status="done",
        output_path=final_path,
        output_checksum=checksum
    )
