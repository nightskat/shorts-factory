import os
import hashlib
import sqlite3
from typing import Any
from shorts.nodes import StepResult
from shorts.providers.llm.factory import get_llm_provider
from shorts.voice.injector import inject_voice_into_system_prompt

def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    env = execution_context.get("env", {})
    provider_name = env.get("LLM_PROVIDER", "openrouter")
    
    system_prompt = execution_context["system_prompt"]
    user_prompt = execution_context["user_prompt"]
    
    few_shot_data = execution_context.get("few_shot_data")
    if few_shot_data:
        system_prompt = inject_voice_into_system_prompt(system_prompt, few_shot_data)
        
    llm_provider = get_llm_provider(provider_name, env)
    
    script_content = llm_provider.generate(system_prompt, user_prompt)
    
    workspace_dir = execution_context.get("workspace_dir", os.getcwd())
    output_dir = os.path.join(workspace_dir, "data", "scripts")
    os.makedirs(output_dir, exist_ok=True)
    
    final_path = os.path.join(output_dir, f"{job_id}_script.txt")
    tmp_path = final_path + ".tmp"
    
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(script_content)
        
    os.replace(tmp_path, final_path)
    
    checksum = hashlib.sha256(script_content.encode("utf-8")).hexdigest()
    
    return StepResult(
        status="done",
        output_path=final_path,
        output_checksum=checksum
    )
