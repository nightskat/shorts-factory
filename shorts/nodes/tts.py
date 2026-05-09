import os
import sqlite3
import hashlib
from typing import Any
from shorts.nodes import StepResult
from shorts.providers.tts.factory import get_tts_provider

def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    # 1. Query db_conn to find the output_path of the idea_gen step for this job_id
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT output_path FROM steps WHERE job_id = ? AND step_name = ? AND status = 'done'",
        (job_id, "idea_gen")
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        return StepResult(
            status="error",
            error_msg="Could not find successful idea_gen step output for this job."
        )
    
    script_path = row[0]
    
    # 2. Read the script content from that output_path
    if not os.path.exists(script_path):
        return StepResult(
            status="error",
            error_msg=f"Script file not found at {script_path}"
        )
        
    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()
        
    # 3. Read TTS settings from execution_context["env"]
    env = execution_context.get("env", {})
    provider_name = env.get("TTS_PROVIDER", "edge-tts")
    voice = env.get("TTS_VOICE")
    rate = env.get("TTS_RATE")
    
    # 4. Instantiate the TTS provider
    provider = get_tts_provider(provider_name, env)
    
    # 5. Define output path
    workspace_dir = execution_context.get("workspace_dir", os.getcwd())
    output_dir = os.path.join(workspace_dir, "data", "audio")
    os.makedirs(output_dir, exist_ok=True)
    
    final_path = os.path.join(output_dir, f"{job_id}_tts.mp3")
    tmp_path = final_path + ".tmp"
    
    # 6. Synthesize
    kwargs = {}
    if voice:
        kwargs["voice"] = voice
    if rate:
        kwargs["rate"] = rate
        
    try:
        provider.synthesize(text=script_content, output_path=tmp_path, **kwargs)
        os.replace(tmp_path, final_path)
    except Exception as e:
        return StepResult(
            status="error",
            error_msg=f"TTS synthesis failed: {str(e)}"
        )
        
    # 7. Calculate checksum
    with open(final_path, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
        
    return StepResult(
        status="done",
        output_path=final_path,
        output_checksum=checksum
    )
