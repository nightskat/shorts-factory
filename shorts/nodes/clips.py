# clips.py — fetch or placeholder stock clips for each scene
# Reads scenes JSON, optionally downloads via pexels service, writes clips manifest.
import os
import json
import hashlib
import sqlite3
from typing import Any
from shorts.nodes import StepResult


def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT output_path FROM step_results WHERE job_id = ? AND step_name = ? AND status = 'done'",
        (job_id, "scenes")
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        return StepResult(
            status="error",
            error_msg="Could not find successful scenes step output for this job."
        )

    scenes_path = row[0]

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
    clip_manifest = []

    for i, scene in enumerate(scenes):
        description = scene.get("description", "")
        duration = scene.get("duration_seconds", 5)

        if pexels:
            result = pexels.search(description, per_page=1)
            video_url = result["videos"][0]["video_files"][0]["link"]
            clip_path = os.path.join(clips_dir, f"{job_id}_clip_{i}.mp4")
            import urllib.request
            urllib.request.urlretrieve(video_url, clip_path)
        else:
            clip_path = os.path.join(clips_dir, f"{job_id}_clip_{i}.txt")
            with open(clip_path, "w", encoding="utf-8") as f:
                f.write(description)

        clip_manifest.append({"clip_path": clip_path, "duration_seconds": duration})

    final_path = os.path.join(clips_dir, f"{job_id}_clips.json")
    tmp_path = final_path + ".tmp"

    encoded = json.dumps(clip_manifest, ensure_ascii=False, indent=2).encode("utf-8")

    with open(tmp_path, "wb") as f:
        f.write(encoded)

    os.replace(tmp_path, final_path)

    checksum = hashlib.sha256(encoded).hexdigest()

    return StepResult(
        status="done",
        output_path=final_path,
        output_checksum=checksum
    )
