from shorts.config import BASE_DIR, DATA_DIR, DB_PATH, ROLLOUT_JSONL, WEB_BIND, WEB_PORT, LEASE_HEARTBEAT_SEC, LEASE_STALE_SEC
from pathlib import Path

def test_config_defaults():
    assert isinstance(BASE_DIR, Path)
    assert BASE_DIR.name == "shorts-factory"
    assert DATA_DIR == BASE_DIR / "data"
    assert DB_PATH == DATA_DIR / "shorts.db"
    assert ROLLOUT_JSONL == DATA_DIR / "rollouts" / "build-cycle.jsonl"
    assert WEB_BIND == "127.0.0.1"
    assert WEB_PORT == 8765
    assert LEASE_HEARTBEAT_SEC == 30
    assert LEASE_STALE_SEC == 120

def test_snapshot_execution_context():
    import json
    from shorts.config import snapshot_execution_context
    job_id = "test-job-123"
    extra = {"foo": "bar"}
    snapshot_str = snapshot_execution_context(job_id, extra)
    snapshot = json.loads(snapshot_str)
    
    assert snapshot["job_id"] == job_id
    assert "timestamp" in snapshot
    assert snapshot["env"]["llm_provider"] == "openrouter"
    assert snapshot["env"]["tts_provider"] == "edge-tts"
    assert snapshot["foo"] == "bar"
