import json
import os
from shorts.utils.rollout import log_checkpoint
from shorts import config

def test_log_checkpoint(tmp_path, monkeypatch):
    # Setup temporary file
    test_jsonl = tmp_path / "test-rollout.jsonl"
    monkeypatch.setattr(config, "ROLLOUT_JSONL", test_jsonl)
    
    # Log a checkpoint
    log_checkpoint("test_task", "success", {"extra": "data"})
    
    # Verify file exists
    assert test_jsonl.exists()
    
    # Read and verify content
    with open(test_jsonl, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["name"] == "test_task"
        assert entry["status"] == "success"
        assert entry["type"] == "checkpoint"
        assert entry["extra"] == "data"
        assert "ts" in entry

def test_log_checkpoint_multiple_entries(tmp_path, monkeypatch):
    test_jsonl = tmp_path / "test-rollout-multiple.jsonl"
    monkeypatch.setattr(config, "ROLLOUT_JSONL", test_jsonl)
    
    log_checkpoint("step1", "started")
    log_checkpoint("step1", "completed", {"duration": 1.5})
    
    with open(test_jsonl, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        
        entry1 = json.loads(lines[0])
        assert entry1["name"] == "step1"
        assert entry1["status"] == "started"
        
        entry2 = json.loads(lines[1])
        assert entry2["name"] == "step1"
        assert entry2["status"] == "completed"
        assert entry2["duration"] == 1.5
