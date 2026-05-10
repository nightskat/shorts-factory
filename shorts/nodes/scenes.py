# scenes.py — generate scene breakdown JSON from script via LLM
# Reads idea_gen output from step_results, calls LLM, writes scenes JSON.
import os
import json
import hashlib
import sqlite3
from typing import Any
from shorts.nodes import StepResult
from shorts.providers.llm.factory import get_llm_provider

_SYSTEM = (
    "You are a video scene planner. Return ONLY a JSON array. "
    "Each element: {\"description\": str, \"duration_seconds\": int}. No markdown fences."
)


def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    env = execution_context.get("env", {})

    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT output_path FROM step_results WHERE job_id = ? AND step_name = ? AND status = 'done'",
        (job_id, "idea_gen")
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        return StepResult(
            status="error",
            error_msg="Could not find successful idea_gen step output for this job."
        )

    script_path = row[0]

    if not os.path.exists(script_path):
        return StepResult(
            status="error",
            error_msg=f"Script file not found at {script_path}"
        )

    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()

    provider_name = env.get("LLM_PROVIDER", "openrouter")
    llm_provider = get_llm_provider(provider_name, env)

    user_prompt = f"Break this script into 3-6 short scenes for a YouTube Short:\n\n{script_content}"

    raw = llm_provider.generate(_SYSTEM, user_prompt)

    try:
        scenes = json.loads(raw)
    except json.JSONDecodeError as e:
        return StepResult(
            status="error",
            error_msg=f"LLM returned invalid JSON for scenes: {e}. Raw: {raw[:200]}"
        )

    workspace_dir = execution_context.get("workspace_dir", os.getcwd())
    output_dir = os.path.join(workspace_dir, "data", "scenes")
    os.makedirs(output_dir, exist_ok=True)

    final_path = os.path.join(output_dir, f"{job_id}_scenes.json")
    tmp_path = final_path + ".tmp"

    encoded = json.dumps(scenes, ensure_ascii=False, indent=2).encode("utf-8")

    with open(tmp_path, "wb") as f:
        f.write(encoded)

    os.replace(tmp_path, final_path)

    checksum = hashlib.sha256(encoded).hexdigest()

    return StepResult(
        status="done",
        output_path=final_path,
        output_checksum=checksum
    )
