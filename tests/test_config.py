from shorts.config import WEB_BIND, snapshot_execution_context, get_lease_owner
import json
import os

def test_config_defaults():
    assert WEB_BIND == "127.0.0.1"

def test_get_lease_owner():
    owner = get_lease_owner()
    assert "@" in owner
    assert str(os.getpid()) in owner

def test_snapshot_shape():
    # Set dummy env vars for test
    os.environ["LLM_PROVIDER"] = "test-llm"
    os.environ["TTS_PROVIDER"] = "test-tts"
    
    snapshot_raw = snapshot_execution_context("job-123")
    snapshot = json.loads(snapshot_raw)
    
    assert snapshot["job_id"] == "job-123"
    assert "env" in snapshot
    assert snapshot["env"]["LLM_PROVIDER"] == "test-llm"
    assert snapshot["env"]["TTS_PROVIDER"] == "test-tts"
    assert "lease_owner" in snapshot
