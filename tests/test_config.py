from shorts.config import WEB_BIND, snapshot_execution_context, get_lease_owner
import json
import os

def test_config_defaults():
    assert WEB_BIND == "127.0.0.1"

def test_get_lease_owner():
    owner = get_lease_owner()
    assert "@" in owner
    assert str(os.getpid()) in owner

def test_snapshot_shape(monkeypatch):
    # Set dummy env vars for test
    monkeypatch.setenv("LLM_PROVIDER", "test-llm")
    monkeypatch.setenv("TTS_PROVIDER", "test-tts")
    
    snapshot_raw = snapshot_execution_context("job-123")
    snapshot = json.loads(snapshot_raw)
    
    assert snapshot["job_id"] == "job-123"
    assert "env" in snapshot
    assert snapshot["env"]["LLM_PROVIDER"] == "test-llm"
    assert snapshot["env"]["TTS_PROVIDER"] == "test-tts"
    assert "lease_owner" in snapshot

def test_snapshot_masks_sensitive_env_vars(monkeypatch):
    # Set sensitive and non-sensitive env vars
    monkeypatch.setenv("LLM_API_KEY", "super_secret_key")
    monkeypatch.setenv("SHORTS_SECRET_TOKEN", "my_token")
    monkeypatch.setenv("TTS_PASSWORD", "password123")
    monkeypatch.setenv("SHORTS_DATA_DIR", "/tmp/data")
    monkeypatch.setenv("LLM_PROVIDER", "my-llm")

    snapshot_raw = snapshot_execution_context("job-456")
    snapshot = json.loads(snapshot_raw)

    assert "env" in snapshot
    env = snapshot["env"]

    # Sensitive should be masked
    assert env.get("LLM_API_KEY") == "***MASKED***"
    assert env.get("SHORTS_SECRET_TOKEN") == "***MASKED***"
    assert env.get("TTS_PASSWORD") == "***MASKED***"

    # Non-sensitive should be preserved
    assert env.get("SHORTS_DATA_DIR") == "/tmp/data"
    assert env.get("LLM_PROVIDER") == "my-llm"
